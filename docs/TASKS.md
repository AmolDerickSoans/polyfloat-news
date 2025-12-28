# Polyfloat News - Task List

> **Last Updated**: 2025-12-28
> **Status**: 🚧 In Development - Phase 1 MVP

## Phase 1: Foundation (Weeks 1-4)

**Goal**: MVP with Nitter scraping + basic delivery

### Week 1: Project Setup & Infrastructure

- [ ] **1.1 Project Structure**
  - [ ] Create directory structure (docs, src, tests, scripts)
  - [ ] Initialize git repository
  - [ ] Create README.md with overview
  - [ ] Create documentation files (OVERVIEW.md, TASKS.md, API.md, DEPLOYMENT.md)
  - [ ] Set up TODO tracking system

- [ ] **1.2 Environment Setup**
  - [ ] Create requirements.txt (minimal dependencies)
  - [ ] Set up Python virtual environment
  - [ ] Create .env.example template
  - [ ] Set up Docker Compose for Nitter instances
  - [ ] Configure systemd service template

- [ ] **1.3 Database Schema**
  - [ ] Design SQLite schema (news_items, user_subscriptions, stats)
  - [ ] Create database initialization script
  - [ ] Configure WAL mode for concurrency
  - [ ] Add indexes for performance

**Status**: ✅ Done (Project structure created)

---

### Week 2: Core Services - Nitter Scraper

- [ ] **2.1 Nitter Infrastructure**
  - [ ] Deploy 3 Nitter containers (Docker Compose)
  - [ ] Configure health check endpoint
  - [ ] Set up resource limits (CPU: 0.5, RAM: 512MB)
  - [ ] Verify instances are accessible

- [ ] **2.2 Nitter Scraper Service**
  - [ ] Implement NitterScraper class
  - [ ] Add round-robin instance selection
  - [ ] Implement failover logic
  - [ ] Add rate limiting (2 seconds per account)
  - [ ] Create 50 account list for scraping
  - [ ] Parse HTML with BeautifulSoup
  - [ ] Push raw tweets to asyncio.Queue

- [ ] **2.3 Integration Testing**
  - [ ] Test single account scraping
  - [ ] Test multi-account scraping
  - [ ] Verify failover between instances
  - [ ] Test rate limiting
  - [ ] Check health monitoring

**Status**: ⏳ Pending

---

### Week 3: Core Services - RSS & Processing

- [ ] **3.1 RSS Fetcher Service**
  - [ ] Implement RSSFetcher class
  - [ ] Configure 5 RSS feeds (Reuters, WSJ, Bloomberg, CNBC, AP)
  - [ ] Implement feedparser integration
  - [ ] Fetch top 20 items per feed
  - [ ] Push raw items to asyncio.Queue
  - [ ] Add error handling and retry logic

- [ ] **3.2 News Processor**
  - [ ] Implement NewsProcessor class
  - [ ] Consume from raw news queue
  - [ ] Implement entity extraction (people, tickers, keywords)
  - [ ] Implement URL-based deduplication
  - [ ] Create rule-based impact scoring
  - [ ] Store news in SQLite
  - [ ] Publish to output queues

- [ ] **3.3 Entity Extractor**
  - [ ] Implement EntityExtractor class
  - [ ] Extract people (simple NER or keyword matching)
  - [ ] Extract tickers (crypto, stock symbols)
  - [ ] Extract keywords (relevant to prediction markets)
  - [ ] Tag news with category

**Status**: ⏳ Pending

---

### Week 4: API & WebSocket

- [ ] **4.1 FastAPI Application**
  - [ ] Create FastAPI app structure
  - [ ] Implement lifespan context manager
  - [ ] Add CORS middleware
  - [ ] Configure single Uvicorn worker

- [ ] **4.2 REST API Endpoints**
  - [ ] GET /api/v1/news (query recent news)
  - [ ] POST /api/v1/subscriptions (create subscription)
  - [ ] GET /api/v1/subscriptions/{user_id}
  - [ ] GET /api/v1/stats (system stats)
  - [ ] GET /health (health check)

- [ ] **4.3 WebSocket Handler**
  - [ ] Implement ConnectionManager class
  - [ ] Add connect/disconnect handlers
  - [ ] Implement broadcast with user filtering
  - [ ] Add WS /ws/news endpoint
  - [ ] Test with 100+ concurrent connections

- [ ] **4.4 Integration**
  - [ ] Connect scraper, fetcher, processor to API
  - [ ] Start all background tasks
  - [ ] Test end-to-end flow
  - [ ] Verify SQLite persistence
  - [ ] Test WebSocket delivery

**Status**: ⏳ Pending

---

## Phase 2: Polish & Testing (Weeks 5-6)

### Week 5: Testing & Quality Assurance

- [ ] **5.1 Unit Tests**
  - [ ] Test entity extraction logic
  - [ ] Test deduplication algorithm
  - [ ] Test impact scoring rules
  - [ ] Test API endpoint validation
  - [ ] Test database operations (CRUD)

- [ ] **5.2 Integration Tests**
  - [ ] Test full Nitter scraping pipeline
  - [ ] Test RSS fetching pipeline
  - [ ] Test news processing flow
  - [ ] Test WebSocket connection lifecycle
  - [ ] Test database persistence

- [ ] **5.3 Load Testing**
  - [ ] Test 500 concurrent WebSocket connections
  - [ ] Test 1000 concurrent WebSocket connections
  - [ ] Test database query performance
  - [ ] Test scraper throughput under load
  - [ ] Identify bottlenecks

**Status**: ⏳ Pending

---

### Week 6: Deployment & Documentation

- [ ] **6.1 Deployment Setup**
  - [ ] Set up VPS (Hetzner or DigitalOcean)
  - [ ] Install dependencies (Python, Docker, Nginx)
  - [ ] Deploy Nitter containers
  - [ ] Deploy FastAPI service (systemd)
  - [ ] Configure Nginx reverse proxy (optional)

- [ ] **6.2 Testing Infrastructure**
  - [ ] Set up ngrok for external testing
  - [ ] Test WebSocket connections via ngrok
  - [ ] Test API endpoints via ngrok
  - [ ] Verify Nitter scraper works on VPS
  - [ ] Monitor resource usage

- [ ] **6.3 Documentation**
  - [ ] Complete API.md (endpoint details)
  - [ ] Complete DEPLOYMENT.md (setup instructions)
  - [ ] Complete TROUBLESHOOTING.md (common issues)
  - [ ] Update README.md with deployment instructions
  - [ ] Create configuration guide

**Status**: ⏳ Pending

---

## Phase 3: Polyfloat Integration (Weeks 7-8)

### Week 7: Polyfloat Terminal Integration

- [ ] **7.1 Polyfloat News Pane**
  - [ ] Create NewsPane widget for Polyfloat TUI
  - [ ] Implement WebSocket client
  - [ ] Display news items with formatting
  - [ ] Add impact score visualization
  - [ ] Add source indicator

- [ ] **7.2 CLI Commands**
  - [ ] Add `/news` command to view news
  - [ ] Add `/subscribe` command to manage subscriptions
  - [ ] Add `/unfollow` command to remove sources
  - [ ] Add `/news config` for settings

- [ ] **7.3 Agent Triggers (Tier 1)**
  - [ ] Create NewsAgentTrigger class
  - [ ] Subscribe to high-signal news
  - [ ] Identify related markets (entity-based)
  - [ ] Trigger agent workflows on news
  - [ ] Log news-triggered trades

**Status**: ⏳ Pending

---

### Week 8: Testing & Optimization

- [ ] **8.1 End-to-End Testing**
  - [ ] Test news flow from Nitter → Terminal
  - [ ] Test RSS feed flow → Terminal
  - [ ] Test agent triggers on high-impact news
  - [ ] Test subscription management
  - [ ] Test WebSocket reconnection

- [ ] **8.2 Performance Tuning**
  - [ ] Optimize database queries
  - [ ] Tune WebSocket connection handling
  - [ ] Optimize scraper performance
  - [ ] Reduce memory footprint
  - [ ] Profile CPU usage

- [ ] **8.3 Monitoring Setup**
  - [ ] Add metrics endpoint (/metrics)
  - [ ] Implement structured logging
  - [ ] Set up log rotation
  - [ ] Create monitoring dashboard (basic)
  - [ ] Add alerting (critical errors)

**Status**: ⏳ Pending

---

## Phase 4: Advanced Features (Future)

### Future Enhancements

- [ ] **Tier 2 Market Linking**
  - [ ] Periodic sync with Polyfloat markets
  - [ ] Cache active markets in SQLite
  - [ ] Pre-match news to markets
  - [ ] Add related_markets field to news items

- [ ] **Advanced Curation**
  - [ ] User preference learning
  - [ ] Personalized news ranking
  - [ ] Keyword-based filtering
  - [ ] Source-based weighting

- [ ] **Alert System**
  - [ ] Email notifications
  - [ ] Slack webhook integration
  - [ ] Mobile push notifications
  - [ ] Custom alert rules

- [ ] **Historical Analytics**
  - [ ] News trend analysis
  - [ ] Entity frequency tracking
  - [ ] Impact score distribution
  - [ ] Volume analysis

- [ ] **Scaling**
  - [ ] Add Redis for pub/sub
  - [ ] Migrate to PostgreSQL
  - [ ] Horizontal scraper scaling
  - [ ] Load balancer setup

**Status**: ⏸️ Not Started (Future)

---

## Progress Summary

### Completed
- ✅ 1.1 Project Structure

### In Progress
- ⏳ None

### Blocked
- 🔒 None

### Not Started
- ⏸️ All other tasks

---

## Notes

### Configuration
- **50 Nitter accounts**: To be populated
- **5 RSS feeds**: Reuters, WSJ, Bloomberg, CNBC, AP
- **No sentiment analysis**: Removed per requirements
- **No ML models**: Rule-based scoring only
- **Testing**: ngrok (no domain yet)
- **Deployment**: Separate VPS, single binary

### Key Decisions
1. **SQLite**: WAL mode for concurrency, no external DB
2. **In-Memory Queue**: No Redis for MVP
3. **Single Worker**: Uvicorn handles 5000+ connections
4. **Systemd**: Native init system, auto-restart
5. **Docker Compose**: Only for Nitter instances

### Risks & Mitigations
| Risk | Status | Mitigation |
|------|--------|------------|
| Nitter instances blocked | Monitor | 3-instance pool + RSS fallback |
| SQLite concurrency limits | Low risk | WAL mode, regular cleanup |
| VPS resource limits | Low risk | Monitor usage, upgrade if needed |
| WebSocket overload | Low risk | Rate limiting, connection limits |

---

## Next Steps

1. **Immediate**: Complete 1.2 Environment Setup
2. **This Week**: Start 2.1 Nitter Infrastructure
3. **Next Week**: Complete Nitter Scraper (2.2, 2.3)
4. **Month Goal**: Phase 1 MVP complete

---

## Contributors

- PolyCLI Team

## References

- [Overview](OVERVIEW.md) - System architecture
- [API Reference](API.md) - Endpoint details
- [Deployment Guide](DEPLOYMENT.md) - Setup instructions
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues
