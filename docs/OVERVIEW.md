# Polyfloat News - Comprehensive Overview

## System Purpose

Polyfloat News is a **separate, decoupled news API** that provides a curated feed of high-signal news specifically designed for prediction market traders. It aggregates news from Nitter (Twitter/X) and RSS feeds, performs entity extraction, and delivers real-time updates via WebSocket to Polyfloat terminals.

## Design Principles

1. **Ultra-Lightweight**: Single binary, minimal dependencies, low overhead
2. **Cost-Efficient**: $5-15/month infrastructure on a single VPS
3. **Decoupled**: Independent from Polyfloat terminal, accessible via clean API
4. **Scalable**: Supports 1000-5000 concurrent users with minimal resources
5. **No ML/AI**: Sentiment analysis and ML models disabled per requirements

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    POLYFLOAT NEWS SYSTEM                   │
│                                                           │
│  ┌────────────────────────────────────────────────────┐    │
│  │           Single VPS ($5-15/month)              │    │
│  │                                                   │    │
│  │  ┌────────────────────────────────────────┐       │    │
│  │  │       Systemd Services (All-in-One)    │       │    │
│  │  │                                       │       │    │
│  │  │  ┌──────────────┐  ┌──────────────┐  │       │    │
│  │  │  │ Nitter x3     │  │ News API     │  │       │    │
│  │  │  │ (Containers)  │  │ (FastAPI)    │  │       │    │
│  │  │  │ Port: 8081   │  │ Port: 8000   │  │       │    │
│  │  │  │ 8082, 8083   │  │              │  │       │    │
│  │  │  └──────────────┘  └──────┬───────┘  │       │    │
│  │  │                           │           │       │    │
│  │  │  ┌──────────────┐         │           │       │    │
│  │  │  │ Scraper      │         │           │       │    │
│  │  │  │ (Background) │         │           │       │    │
│  │  │  │ - Nitter     │         │           │       │    │
│  │  │  │ - RSS        │         │           │       │    │
│  │  │  └──────────────┘         │           │       │    │
│  │  │                           │           │       │    │
│  │  │  ┌──────────────┐         │           │       │    │
│  │  │  │ Processor    │         │           │       │    │
│  │  │  │ (Entity Ext.)│         │           │       │    │
│  │  │  │ - Dedup      │         │           │       │    │
│  │  │  │ - Impact     │         │           │       │    │
│  │  │  └──────────────┘         │           │       │    │
│  │  │                           │           │       │    │
│  │  │  ┌──────────────┐         │           │       │    │
│  │  │  │ SQLite DB    │         │           │       │    │
│  │  │  │ (WAL Mode)   │         │           │       │    │
│  │  │  └──────────────┘         │           │       │    │
│  │  └─────────────────────────────┼───────────┘       │    │
│  │                            │                   │       │    │
│  │                            │                   │       │    │
│  │  ┌─────────────────────────┴───────────┐     │    │
│  │  │       WebSocket Manager               │     │    │
│  │  │       - 5000+ connections           │     │    │
│  │  │       - In-memory state             │     │    │
│  │  └──────────────────────────────────────┘     │    │
│  │                                                   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                           │
└─────────────────────────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────────────────────────┐
│              POLYFLOAT TERMINAL (External)                │
│                                                           │
│  WebSocket → Receive News → Display in TUI → Trigger Agents │
│                                                           │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Nitter Instance (8081-8083)
    ↓ (scrape every 60s)
Nitter Scraper (aiohttp + BeautifulSoup)
    ↓ (push to queue)
Raw News Queue (asyncio.Queue)
    ↓ (entity extraction, dedup, impact scoring)
News Processor
    ↓ (store & publish)
SQLite DB (WAL mode) + WebSocket Clients
```

```
RSS Feeds (5 sources)
    ↓ (fetch every 120s)
RSS Fetcher (feedparser)
    ↓ (push to queue)
Raw News Queue (asyncio.Queue)
    ↓ (entity extraction, dedup, impact scoring)
News Processor
    ↓ (store & publish)
SQLite DB (WAL mode) + WebSocket Clients
```

## Core Components

### 1. Nitter Scraper Service
- Scrapes 50 Twitter/X accounts via 3 Nitter instances
- Round-robin load balancing with failover
- Rate limiting (2 seconds between accounts)
- Health checking every 30 seconds
- Pushes raw tweets to shared queue

### 2. RSS Fetcher Service
- Fetches from 5 RSS feeds every 2 minutes
- Top 20 items per feed
- Pushes raw items to shared queue

### 3. News Processor Service
- Consumes from raw news queue
- **Entity Extraction**: People, tickers, keywords
- **Deduplication**: URL hash-based duplicate detection
- **Impact Scoring**: Rule-based (no ML)
- Stores in SQLite (WAL mode for concurrency)
- Publishes to WebSocket clients

### 4. WebSocket Manager
- In-memory connection tracking
- Supports 5000+ concurrent connections
- User-specific filtering (impact threshold)
- Broadcast optimization

### 5. API Endpoints (FastAPI)
- `GET /api/v1/news` - Query recent news
- `POST /api/v1/subscriptions` - Manage subscriptions
- `GET /api/v1/stats` - System statistics
- `WS /ws/news` - Real-time news stream

## Data Models

### NewsItem
```python
{
    "id": "news_abc123",
    "source": "nitter" | "rss",
    "source_account": "@elonmusk" | "Reuters",
    "title": "...",
    "content": "...",
    "url": "https://x.com/...",
    "published_at": 1735444800,

    # Analysis (no ML)
    "impact_score": 85.5,  # 0-100
    "relevance_score": 75.0,  # 0-100

    # Entities
    "tickers": ["BTC", "ETH"],
    "people": ["powell", "trump"],
    "prediction_markets": [],  # To be linked later
    "category": "crypto" | "politics" | "economics",
    "tags": ["fed", "rate-hike"],

    # Processing
    "is_duplicate": false,
    "is_high_signal": true  # if impact > 70
}
```

### UserSubscription
```python
{
    "user_id": "user123",
    "nitter_accounts": ["@elonmusk", "@trump"],
    "rss_feeds": ["reuters"],
    "categories": ["politics", "crypto"],
    "keywords": ["fed", "trump", "btc"],
    "impact_threshold": 70,
    "alert_channels": ["terminal"]
}
```

## Tech Stack Justification

### Why SQLite?
- Zero overhead (no separate DB server)
- WAL mode supports concurrent reads/writes
- Sufficient for 1000-5000 users
- Easy backup (single file)
- **Cost: $0**

### Why In-Memory Queue?
- No Redis needed for MVP
- asyncio.Queue is built-in and efficient
- Single process = no distributed complexity
- **Cost: $0**

### Why FastAPI?
- Asynchronous by default
- WebSocket support built-in
- Automatic API docs (Swagger UI)
- Type hints for better code quality
- **Cost: $0**

### Why Docker Compose for Nitter?
- Nitter instances need isolation
- Easy to scale up/down
- Health checks built-in
- **Cost: $0** (within VPS limits)

### Why Systemd?
- Native Linux init system
- Auto-restart on failure
- No supervisor/docker for main service
- **Cost: $0**

## Market Linking Strategy

### Tier 1: Simple Entity Tagging (MVP - Phase 1)
- News API extracts entities (people, tickers, keywords)
- Terminal queries markets by entity
- **Pros**: Simple, no coupling, easy to evolve
- **Cons**: Terminal makes N queries, more roundtrips

### Tier 2: Pre-Matched Market Hints (Phase 2)
- News API maintains cache of active markets (periodic sync)
- Tags news with `related_markets: ["poly:12345", "kalshi:67890"]`
- **Pros**: Instant lookup, better UX
- **Cons**: Slight coupling, cache invalidation complexity

**Recommendation: Start with Tier 1, add Tier 2 in Phase 2**

## Performance Optimization

### Database
- **WAL Mode**: Write-Ahead Logging for concurrency
- **64MB Cache**: In-memory cache for hot data
- **Memory temp store**: Temporary tables in RAM
- **Indexes**: On published_at, impact_score, category
- **Cleanup**: Delete items older than 30 days

### API
- **Single Worker**: Uvicorn handles 5000+ connections via async
- **Connection Pooling**: aiohttp session reuse
- **Rate Limiting**: Nginx prevents abuse
- **No Access Logs**: Reduce I/O overhead

### Scraping
- **Round-Robin**: Load balance across Nitter instances
- **Failover**: Skip unhealthy instances
- **Rate Limiting**: Respect platform limits
- **Health Checks**: Monitor instance availability

## Testing Strategy

### Unit Tests
- Entity extraction logic
- Deduplication algorithm
- Impact scoring rules
- API endpoint validation

### Integration Tests
- Full scraping pipeline
- WebSocket connection lifecycle
- Database operations (CRUD)
- End-to-end news delivery

### Load Tests
- 5000 concurrent WebSocket connections
- Database query performance
- Scraper throughput under load

## Deployment Strategy

### Phase 1: Local Development (Week 1)
- Local Nitter containers
- FastAPI dev server
- ngrok for external testing

### Phase 2: Staging VPS (Week 2)
- Deploy to small VPS (Hetzner/DigitalOcean)
- Systemd service setup
- Basic monitoring

### Phase 3: Production (Week 3-4)
- Nginx reverse proxy
- SSL certificate (when domain ready)
- Backup strategy
- Performance tuning

## Monitoring & Observability

### Metrics (No External Services)
- News items processed per minute
- Active WebSocket connections
- Scraper success/failure rate
- Database query latency
- Memory usage

### Logging
- Structured logging with structlog
- Log levels: INFO, WARNING, ERROR
- Log rotation (keep last 7 days)
- No external logging service (keep local)

### Health Checks
- `/health` endpoint
- Database connectivity
- Nitter instance status
- WebSocket connection count

## Scalability Path

### From 5000 to 50000 Users
- Add more VPS instances
- Redis Cluster for pub/sub
- Load balancer (Nginx)
- PostgreSQL instead of SQLite
- Distributed scraping

### From 50 to 500 Accounts
- Horizontal scraper scaling
- Multiple scraper processes
- Database sharding
- Queue partitioning

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Nitter shutdown** | High | 3-instance pool + RSS fallback |
| **X blocks Nitter** | Critical | Plan B: SociaVault integration |
| **SQLite limits** | Medium | WAL mode, regular cleanup, migrate to PostgreSQL if needed |
| **VPS failure** | High | Regular backups, quick redeploy scripts |
| **WebSocket overload** | Medium | Rate limiting, connection limits |
| **Memory leaks** | Medium | Resource monitoring, auto-restart |

## Success Metrics

### Technical KPIs
- News latency: < 30 seconds from source to terminal
- WebSocket uptime: > 99.9%
- Nitter scraper success rate: > 95%
- API response time: < 100ms (p95)

### Product KPIs
- Active daily users: 100+ (Month 1), 1000+ (Month 6)
- News items processed: 1000+ per day
- WebSocket connections: 5000+ concurrent
- User engagement: > 5 news views per session

## Known Limitations

1. **No Sentiment Analysis**: Removed per user requirements
2. **No ML Models**: Rule-based scoring only
3. **Single VPS**: No high availability (can be added later)
4. **No Domain**: Using ngrok for testing
5. **In-Memory State**: WebSocket state lost on restart
6. **SQLite**: Limited write concurrency (but sufficient for use case)

## Future Enhancements

1. **Tier 2 Market Linking**: Pre-match markets to news
2. **Full Text Search**: Integrate search service
4. **User Preferences**: Advanced filtering and customization
5. **Push Notifications**: Mobile alerts
6. **Historical Analytics**: News trend analysis
7. **Multi-Language Support**: International news sources
