# Polyfloat News

High-signal news API for prediction market traders. Ultra-lightweight, cost-efficient system aggregating news from Nitter (Twitter/X) and RSS feeds.

## Philosophy

**"Single binary + minimal services = $5-15/month infrastructure"**

## Key Features

- **Multi-source aggregation**: 50 Nitter accounts + 5 RSS feeds
- **Real-time delivery**: WebSocket streaming to 5000+ concurrent users
- **Prediction market focused**: Entity extraction (people, tickers, markets)
- **Ultra-lightweight**: Single VPS deployment
- **Decoupled**: Separate from polyfloat, accessible via API/WebSocket

## Tech Stack

| Component | Technology |
|-----------|------------|
| **API Server** | FastAPI + Uvicorn |
| **Persistence** | SQLite (WAL mode) |
| **Cache/Queue** | In-memory (asyncio.Queue) |
| **Scraping** | aiohttp + BeautifulSoup (Nitter), feedparser (RSS) |
| **Deployment** | Systemd + Docker Compose |
| **Testing** | ngrok (no domain yet) |

## Architecture

```
┌─────────────────────────────────────────────┐
│     Single VPS ($5-15/month)            │
│                                         │
│  ┌────────────────────────────┐          │
│  │   Systemd Services        │          │
│  │                           │          │
│  │  ┌────────────┐         │          │
│  │  │ Nitter x3   │         │          │
│  │  │ (Docker)    │         │          │
│  │  └────────────┘         │          │
│  │                          │          │
│  │  ┌────────────┐         │          │
│  │  │ FastAPI     │         │          │
│  │  │ :8000       │         │          │
│  │  └────────────┘         │          │
│  │     ↕                   │          │
│  │  ┌────────────┐         │          │
│  │  │ SQLite DB   │         │          │
│  │  └────────────┘         │          │
│  └────────────────────────────┘          │
│              ↕                          │
│  ┌────────────────────────────┐          │
│  │   Nginx (optional)       │          │
│  │   - SSL termination       │          │
│  │   - Reverse proxy         │          │
│  └────────────────────────────┘          │
│                                         │
│  Testing: ngrok → localhost:8000        │
└─────────────────────────────────────────────┘
```

## Integration with Polyfloat

```python
# Polyfloat Terminal → Polyfloat News API

1. WebSocket connection to /ws/news
2. Receive real-time news items
3. Filter by user subscriptions
4. Display in TUI News Pane
5. Trigger agents on high-impact news
```

## Market Linking Strategy

**Tier 1: Simple Entity Tagging** (MVP)
- News API extracts entities (people, tickers, keywords)
- Terminal queries markets by entity
- Keeps systems decoupled

**Tier 2: Pre-Matched Market Hints** (Future)
- News API maintains cache of active markets
- Tags news with related markets
- Better UX, slight coupling

## Configuration

- **50 Nitter accounts**: Prediction-market-relevant Twitter/X handles
- **5 RSS feeds**: Reuters, WSJ, Bloomberg, CNBC, AP
- **Sentiment analysis**: DISABLED (per user request)
- **ML models**: DISABLED (per user request)
- **Database**: SQLite with WAL mode for concurrency
- **Deployment**: Single binary on VPS

## Performance Targets

| Metric | Target |
|--------|---------|
| Concurrent users | 1000-5000 |
| Latency (source → terminal) | 10-30 seconds |
| News throughput | 1000-2000/day |
| Memory usage | ~500MB - 1GB |
| CPU usage | 20-40% |
| Monthly cost | $5-15 |

## Documentation

- [Overview](docs/OVERVIEW.md) - System architecture and design
- [Task List](docs/TASKS.md) - Implementation tasks and progress
- [API Reference](docs/API.md) - API endpoints and WebSocket protocol
- [Deployment Guide](docs/DEPLOYMENT.md) - Setup and deployment instructions
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions

## Repository

https://github.com/AmolDerickSoans/polyfloat-news

## Status

🚧 **In Development** - MVP Phase 1

### Quick Start

```bash
# Clone repository
git clone https://github.com/AmolDerickSoans/polyfloat-news.git
cd polyfloat-news

# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start Nitter containers
docker-compose up -d

# Initialize database
python scripts/init_db.py

# Start API
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## License

MIT
