# News Processor Service - Implementation Summary

## Overview
Created `src/services/news_processor.py` - the central news processing pipeline for Polyfloat News.

## Architecture
```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Nitter        │     │       RSS        │     │              │
│   Scraper       │────▶│    Fetcher       │────▶│   News       │
│                 │     │                  │     │  Processor   │
└─────────────────┘     └──────────────────┘     │              │
                                                 ▶│  Database    │
┌─────────────────┐                            │              │
│   WebSocket     │◀───────────────────────────│              │
│   Subscribers   │                            └──────────────┘
└─────────────────┘
```

## Key Components

### 1. EntityExtractor Integration
- Imports `EntityExtractor` from `services.entity_extractor`
- Calls `extract_entities()` on each news item
- Extracts: tickers, people, prediction_markets, category, tags

### 2. Deduplication
- Uses URL as unique identifier
- Checks database before processing new items
- Skips duplicates, processes only new URLs
- Uses SQLite UNIQUE constraint on `url` column

### 3. Impact Scoring System

#### Scoring Components (Weighted Average)
```
Final Score = (Source × 0.2) + (Entity × 0.3) + (Keyword × 0.3) + (Recency × 0.2)
```

#### Source Authority Scores
| Source | Score |
|--------|-------|
| Reuters, AP, Associated Press | 10 |
| WSJ, Wall Street Journal, Bloomberg | 8 |
| CNBC | 6 |
| Nitter, Twitter, X.com | 5 |
| Other | 5 |

#### Entity Importance Scores
| Entity | Score |
|--------|-------|
| Fed Chair, Fed Chairman, Jerome Powell | 10 |
| Joe Biden, President Biden | 10 |
| Donald Trump, President Trump | 10 |
| Elon Musk, Michael Saylor, Balaji Srinivasan, Vitalik Buterin | 8 |
| Gary Gensler, Jamie Dimon, Larry Fink, Warren Buffett, Janet Yellen | 8 |
| Other | 5 |

#### Keyword Relevance Scores
| Keyword | Score |
|---------|-------|
| breaking, urgent, alert | 10 |
| major, significant, important, update, exclusive | 8 |
| report, news, announcement | 5 |
| None | 5 |

#### Recency Scores
| Age | Score |
|-----|-------|
| < 1 hour | 10 |
| < 6 hours | 8 |
| < 24 hours | 5 |
| < 48 hours | 3 |
| > 48 hours | 1 |

### 4. Database Operations
- Uses `aiosqlite` for async operations
- WAL mode enabled for concurrency
- Proper indexes on: `url`, `published_at`, `impact_score`, `category`
- Prepared statements for performance
- Handles connection errors gracefully

### 5. Queue Operations
- Consumes from `raw news queue` (from scraper/fetcher)
- Publishes to `WebSocket queue` for real-time delivery
- Handles queue errors with logging

### 6. Error Handling
- Database connection errors
- Queue errors
- Malformed news items
- All errors logged with `structlog`
- Retry logic for transient failures

### 7. Periodic Cleanup
- Runs every 24 hours
- Deletes news items older than 7 days
- Keeps database size manageable
- Runs in background task

## Database Schema

```sql
CREATE TABLE news (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_account TEXT,
    title TEXT,
    content TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    published_at REAL NOT NULL,
    impact_score REAL DEFAULT 0,
    relevance_score REAL DEFAULT 0,
    tickers TEXT,              -- JSON array
    people TEXT,               -- JSON array
    prediction_markets TEXT,   -- JSON array
    category TEXT,
    tags TEXT,                 -- JSON array
    is_duplicate INTEGER DEFAULT 0,
    duplicate_of TEXT,
    is_high_signal INTEGER DEFAULT 0,
    created_at REAL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX idx_news_url ON news(url);
CREATE INDEX idx_news_published_at ON news(published_at DESC);
CREATE INDEX idx_news_impact_score ON news(impact_score DESC);
CREATE INDEX idx_news_category ON news(category);
```

## Test Results

All 6 tests passed successfully:

1. ✓ Deduplication - Correctly prevents duplicate URLs
2. ✓ High Impact Scoring - Scored 10.0 for Fed emergency news
3. ✓ Entity Extraction - Extracted BTC, ETH from crypto news
4. ✓ WebSocket Publishing - Published items to output queue
5. ✓ Low Impact Scoring - Scored 4.2 for old, low-relevance news
6. ✓ Malformed Item Handling - Gracefully handled incomplete items

**Total news items in database: 6**

## Integration Status

✅ **READY FOR INTEGRATION**

The processor is fully functional and ready to be integrated with:
- NitterScraper (already outputs to correct queue format)
- RSSFetcher (already outputs to correct queue format)
- WebSocket API (can consume from websocket_queue)
- Main application orchestration

## Usage Example

```python
import asyncio
from services.news_processor import NewsProcessor

async def main():
    input_queue = asyncio.Queue()
    websocket_queue = asyncio.Queue()

    processor = NewsProcessor(
        input_queue=input_queue,
        websocket_queue=websocket_queue,
        db_path="news_api.db"
    )

    await processor.start()

    try:
        # Processor runs in background, consuming from input_queue
        # and publishing to websocket_queue
        while True:
            await asyncio.sleep(1)
    finally:
        await processor.stop()
```

## Files Created

1. `/Users/amoldericksoans/Documents/polyfloat-news/src/services/entity_extractor.py` - Lightweight entity extraction
2. `/Users/amoldericksoans/Documents/polyfloat-news/src/services/news_processor.py` - Central processing pipeline
3. `/Users/amoldericksoans/Documents/polyfloat-news/tests/test_news_processor.py` - Comprehensive test suite

## Dependencies

- `aiosqlite==0.19.0` - Async SQLite operations
- `structlog==23.2.0` - Structured logging
- `asyncio` - Async operations (built-in)
- `json` - JSON serialization (built-in)

## Performance Considerations

- **Deduplication**: O(1) lookup via indexed URL
- **Entity Extraction**: O(n) where n = text length
- **Impact Scoring**: O(1) dictionary lookups
- **Database Insert**: Batched with WAL mode
- **Queue Operations**: O(1) put/get operations

## Next Steps for Integration

1. Create main orchestration script that:
   - Initializes all queues
   - Starts NitterScraper, RSSFetcher, and NewsProcessor
   - Manages WebSocket server consuming from websocket_queue

2. Add monitoring/metrics:
   - Track processing rates
   - Monitor queue depths
   - Alert on high error rates

3. Add configuration:
   - Configurable impact thresholds
   - Configurable cleanup intervals
   - Configurable scoring weights

4. Add unit tests for:
   - Each scoring component individually
   - Error recovery scenarios
   - Database connection failures
