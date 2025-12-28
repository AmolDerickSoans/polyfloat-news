# Polyfloat News - TODO List

> **Last Updated**: 2025-12-28

## Phase 1: Foundation (Weeks 1-4)

### ✅ Completed
- [x] 1.1 Project structure created
- [x] 1.2 Documentation (README, OVERVIEW, TASKS, API, DEPLOYMENT)
- [x] 1.3 Data models created
- [x] 1.4 Requirements.txt defined
- [x] 1.5 Docker Compose for Nitter
- [x] 1.6 Git repository initialized and pushed to GitHub
- [x] 1.7 Database initialization script created

### ✅ Completed
- [x] 1.8 Install dependencies and test imports
- [x] 1.9 Complete Nitter scraper implementation
- [x] 1.10 Complete RSS fetcher implementation
- [x] 1.11 Implement entity extractor service
- [x] 1.12 Implement news processor service
- [x] 1.13 Create FastAPI application structure
- [x] 1.14 Implement REST API endpoints
- [x] 1.15 Implement WebSocket handler
- [x] 1.17 Test end-to-end pipeline

### 🔒 Blocked
- None

---

## Immediate Tasks (This Week)

1. **Fix Import Errors** - Install dependencies to resolve import errors
2. **Complete Nitter Scraper** - Implement full scraping logic with HTML parsing
3. **Complete RSS Fetcher** - Test with 5 RSS feeds
4. **Entity Extractor** - Create service to extract people, tickers, keywords
5. **News Processor** - Implement deduplication, impact scoring, storage
6. **FastAPI Skeleton** - Create main.py with basic app structure

---

## Component Status

| Component | Status | Progress |
|-----------|--------|----------|
| Project Setup | ✅ Complete | 100% |
| Documentation | ✅ Complete | 100% |
| Data Models | ✅ Complete | 100% |
| Database Schema | ✅ Complete | 100% |
| Nitter Scraper | ✅ Complete | 100% |
| RSS Fetcher | ✅ Complete | 100% |
| Entity Extractor | ✅ Complete | 100% |
| News Processor | ✅ Complete | 100% |
| FastAPI App | ✅ Complete | 100% |
| REST API | ✅ Complete | 100% |
| WebSocket Handler | ✅ Complete | 100% |
| End-to-End Tests | ✅ Complete | 100% |
| Deployment | ⏸️ Not Started | 0% |
| Integration | ⏸️ Not Started | 0% |

---

## Known Issues

**RESOLVED** ✅
1. ~~Import Errors~~ - Dependencies installed and all imports fixed
2. ~~Nitter HTML Parsing~~ - Implemented with multiple selector support
3. ~~Timestamp Parsing~~ - Robust parser implemented

**CURRENT ISSUES** ⚠️
None - All components working correctly!

---

## Known Issues

1. **Import Errors** - Dependencies not installed (aiosqlite, aiohttp, bs4, feedparser)
   - **Resolution**: Run `pip install -r requirements.txt`
   - **Status**: Pending

2. **Nitter HTML Parsing** - Nitter HTML structure may vary
   - **Resolution**: Test with actual Nitter instances and adjust parsing logic
   - **Status**: Blocked by #1

3. **Timestamp Parsing** - Different date formats from sources
   - **Resolution**: Create robust timestamp parser
   - **Status**: Blocked by #1

---

## Decisions Made

1. **No ML/AI** - Removed sentiment analysis per user requirements
2. **SQLite with WAL** - Chosen for cost-efficiency and simplicity
3. **In-Memory Queue** - No Redis for MVP
4. **Single Uvicorn Worker** - Async handles 5000+ connections
5. **Systemd Service** - Native init system for production

---

## Next Steps

### COMPLETED (2025-12-28) ✅
1. [x] Install Python dependencies
2. [x] Fix import errors in service files
3. [x] Test database initialization
4. [x] Test Nitter container startup
5. [x] Complete Nitter scraper
6. [x] Complete RSS fetcher
7. [x] Create entity extractor
8. [x] Create news processor
9. [x] Build FastAPI application
10. [x] Implement REST endpoints
11. [x] Implement WebSocket handler
12. [x] Test end-to-end pipeline

### Upcoming (Week 2-3)
1. [ ] Deploy to VPS (Hetzner/DigitalOcean)
2. [ ] Test with ngrok for external access
3. [ ] Create systemd service template
4. [ ] Polyfloat terminal integration (news pane, CLI commands)
5. [ ] Agent triggers (Tier 1 market linking)

---

## Testing Checklist

### Unit Tests
- [ ] Test entity extraction logic
- [ ] Test deduplication algorithm
- [ ] Test impact scoring rules
- [ ] Test database CRUD operations
- [ ] Test API endpoint validation

### Integration Tests
- [ ] Test full Nitter scraping pipeline
- [ ] Test RSS fetching pipeline
- [ ] Test news processing flow
- [ ] Test WebSocket connection lifecycle
- [ ] Test database persistence

### Load Tests
- [ ] Test 500 concurrent WebSocket connections
- [ ] Test 1000 concurrent WebSocket connections
- [ ] Test database query performance
- [ ] Test scraper throughput

---

## Deployment Checklist

### Local Development
- [ ] All services running locally
- [ ] Database initialized
- [ ] Nitter containers running
- [ ] API accessible on localhost:8000
- [ ] WebSocket connection working

### Staging VPS
- [ ] VPS provisioned (Hetzner/DigitalOcean)
- [ ] Dependencies installed
- [ ] Code deployed
- [ ] Systemd service configured
- [ ] Services running
- [ ] Accessible via ngrok

### Production
- [ ] Domain configured
- [ ] SSL certificate installed
- [ ] Nginx reverse proxy configured
- [ ] Monitoring setup
- [ ] Backup strategy implemented
- [ ] Load tested

---

## Notes for Developers

### Environment Setup

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Nitter containers
docker-compose up -d

# Initialize database
python scripts/init_db.py

# Start API (development)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing with ngrok

```bash
# In another terminal
ngrok http 8000

# Test WebSocket
wscat -c ws://your-ngrok-url.ngrok-free.app/ws/news?user_id=test123

# Test REST API
curl http://your-ngrok-url.ngrok-free.app/api/v1/news
```

### Code Style

- **Python**: 3.11+
- **Type hints**: Required (use pydantic models)
- **Logging**: Use `structlog`
- **Async/Await**: Use `asyncio` for all I/O operations
- **Error handling**: Try/except with proper logging

---

## References

- [Main README](README.md)
- [System Overview](docs/OVERVIEW.md)
- [Task List](docs/TASKS.md)
- [API Reference](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [GitHub Repository](https://github.com/AmolDerickSoans/polyfloat-news)

---

## Questions & Answers

### Q: Why no sentiment analysis?
**A**: Per user requirements, sentiment analysis and ML models are disabled. System uses rule-based impact scoring instead.

### Q: Why SQLite instead of PostgreSQL?
**A**: SQLite with WAL mode is sufficient for 1000-5000 users and eliminates infrastructure cost ($0 vs $30+/month).

### Q: How do I add more Nitter accounts?
**A**: Edit `src/services/nitter_scraper.py` and add accounts to the `ACCOUNTS` list.

### Q: How do I add more RSS feeds?
**A**: Edit `src/services/rss_fetcher.py` and add feeds to the `FEEDS` list.

### Q: How do I test locally without a domain?
**A**: Use `ngrok http 8000` to expose localhost to the internet for testing.

---

## Progress Tracking

### Week 1 (Dec 23-29)
- **Goal**: Project setup and foundation
- **Progress**: 70% complete
- **Status**: On track

### Week 2 (Dec 30 - Jan 5)
- **Goal**: Core services (Nitter, RSS, Processor)
- **Status**: Not started

### Week 3 (Jan 6-12)
- **Goal**: API and WebSocket implementation
- **Status**: Not started

### Week 4 (Jan 13-19)
- **Goal**: Testing and deployment
- **Status**: Not started

---

**Maintained by**: PolyCLI Team
**Last Updated**: 2025-12-28
