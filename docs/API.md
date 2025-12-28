# Polyfloat News - API Reference

## Base URL

**Development**: `http://localhost:8000`
**Testing**: `https://your-ngrok-url.ngrok-free.app`
**Production**: `https://news.polyfloat.com` (future)

## Authentication

Currently **no authentication** required. Future versions will add API keys.

## REST API Endpoints

### 1. Get Recent News

**Endpoint**: `GET /api/v1/news`

**Description**: Retrieve recent news items with optional filtering

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|-------|-----------|----------|-------------|
| `limit` | int | No | 50 | Number of items to return (max 500) |
| `category` | string | No | None | Filter by category (`politics`, `crypto`, `economics`, `sports`) |
| `min_impact` | float | No | None | Minimum impact score (0-100) |
| `source` | string | No | None | Filter by source (`nitter`, `rss`) |
| `user_id` | string | No | None | Filter by user subscriptions |

**Example Request**:
```bash
curl "http://localhost:8000/api/v1/news?limit=20&category=politics&min_impact=70"
```

**Example Response**:
```json
{
  "items": [
    {
      "id": "news_abc123",
      "source": "nitter",
      "source_account": "@trumpwarroom",
      "title": "BREAKING: Trump leads in Pennsylvania by 2%",
      "content": "Latest polls show Trump leading in key swing state...",
      "url": "https://x.com/trumpwarroom/status/123456789",
      "published_at": 1735444800,

      "impact_score": 85.5,
      "relevance_score": 75.0,

      "tickers": [],
      "people": ["trump", "pennsylvania"],
      "prediction_markets": [],
      "category": "politics",
      "tags": ["election", "trump", "swing-state"],

      "is_duplicate": false,
      "is_high_signal": true
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20
}
```

**Error Responses**:
- `400 Bad Request`: Invalid query parameters
- `500 Internal Server Error`: Database error

---

### 2. Create Subscription

**Endpoint**: `POST /api/v1/subscriptions`

**Description**: Create or update user subscription preferences

**Request Body**:
```json
{
  "user_id": "user123",
  "nitter_accounts": ["@elonmusk", "@trumpwarroom"],
  "rss_feeds": ["reuters", "wsj"],
  "categories": ["politics", "crypto"],
  "keywords": ["fed", "trump", "btc"],
  "impact_threshold": 70,
  "alert_channels": ["terminal"]
}
```

**Fields**:
| Field | Type | Required | Description |
|-------|-------|-----------|-------------|
| `user_id` | string | Yes | Unique user identifier |
| `nitter_accounts` | array | No | List of Nitter accounts to follow (with @) |
| `rss_feeds` | array | No | List of RSS feed sources |
| `categories` | array | No | List of categories to filter |
| `keywords` | array | No | List of keywords to track |
| `impact_threshold` | int | No | Minimum impact score for alerts (0-100, default: 70) |
| `alert_channels` | array | No | Alert channels (default: `["terminal"]`) |

**Example Response**:
```json
{
  "status": "created",
  "user_id": "user123",
  "created_at": 1735444800
}
```

**Error Responses**:
- `400 Bad Request`: Invalid JSON or missing required fields
- `500 Internal Server Error`: Database error

---

### 3. Get Subscription

**Endpoint**: `GET /api/v1/subscriptions/{user_id}`

**Description**: Retrieve user subscription settings

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|-------|-----------|-------------|
| `user_id` | string | Yes | User identifier |

**Example Request**:
```bash
curl "http://localhost:8000/api/v1/subscriptions/user123"
```

**Example Response**:
```json
{
  "user_id": "user123",
  "nitter_accounts": ["@elonmusk", "@trumpwarroom"],
  "rss_feeds": ["reuters", "wsj"],
  "categories": ["politics", "crypto"],
  "keywords": ["fed", "trump", "btc"],
  "impact_threshold": 70,
  "alert_channels": ["terminal"],
  "created_at": 1735444800,
  "updated_at": 1735448400
}
```

**Error Responses**:
- `404 Not Found`: User subscription not found
- `500 Internal Server Error`: Database error

---

### 4. Delete Subscription

**Endpoint**: `DELETE /api/v1/subscriptions/{user_id}`

**Description**: Delete user subscription

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|-------|-----------|-------------|
| `user_id` | string | Yes | User identifier |

**Example Request**:
```bash
curl -X DELETE "http://localhost:8000/api/v1/subscriptions/user123"
```

**Example Response**:
```json
{
  "status": "deleted",
  "user_id": "user123"
}
```

**Error Responses**:
- `404 Not Found`: User subscription not found
- `500 Internal Server Error`: Database error

---

### 5. Get System Stats

**Endpoint**: `GET /api/v1/stats`

**Description**: Retrieve system statistics

**Example Request**:
```bash
curl "http://localhost:8000/api/v1/stats"
```

**Example Response**:
```json
{
  "total_news_items": 15420,
  "items_last_24h": 850,
  "average_impact": 65.5,
  "active_connections": 1523,
  "nitter_instances": {
    "total": 3,
    "healthy": 2,
    "unhealthy": 1
  },
  "rss_feeds": {
    "total": 5,
    "active": 5
  },
  "uptime_seconds": 86400,
  "version": "0.1.0"
}
```

**Error Responses**:
- `500 Internal Server Error`: Statistics collection failed

---

### 6. Health Check

**Endpoint**: `GET /health`

**Description**: Health check endpoint for monitoring

**Example Request**:
```bash
curl "http://localhost:8000/health"
```

**Example Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "nitter_instances": {
    "nitter-1": "healthy",
    "nitter-2": "healthy",
    "nitter-3": "healthy"
  },
  "timestamp": 1735444800
}
```

---

## WebSocket API

### Connection

**Endpoint**: `WS /ws/news`

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|-------|-----------|-------------|
| `user_id` | string | Yes | User identifier |
| `filters` | string | No | JSON-encoded filters (e.g., `{"impact_threshold": 70}`) |

**Example Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/news?user_id=user123');

ws.onopen = () => {
  console.log('Connected to news stream');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('News received:', data);
};

ws.onclose = () => {
  console.log('Disconnected from news stream');
};
```

---

### WebSocket Messages

#### Client → Server: Subscribe (Optional)

```json
{
  "type": "subscribe",
  "filters": {
    "impact_threshold": 70,
    "categories": ["politics", "crypto"],
    "min_impact": 75
  }
}
```

#### Server → Client: News Item

```json
{
  "type": "news_item",
  "data": {
    "id": "news_abc123",
    "source": "nitter",
    "source_account": "@elonmusk",
    "title": "BTC breaks $100k!",
    "content": "Bitcoin has surpassed $100,000 for the first time...",
    "url": "https://x.com/elonmusk/status/123456789",
    "published_at": 1735444800,

    "impact_score": 90.0,
    "relevance_score": 85.0,

    "tickers": ["BTC"],
    "people": [],
    "prediction_markets": [],
    "category": "crypto",
    "tags": ["btc", "milestone", "all-time-high"],

    "is_duplicate": false,
    "is_high_signal": true
  },
  "timestamp": 1735444801
}
```

#### Server → Client: Keep-Alive

```json
{
  "type": "keep_alive",
  "timestamp": 1735444900
}
```

#### Server → Client: Error

```json
{
  "type": "error",
  "message": "Invalid filters",
  "timestamp": 1735444800
}
```

---

## Filtering & Pagination

### Filtering

You can filter news items by:

1. **Category**: `politics`, `crypto`, `economics`, `sports`, `other`
2. **Impact Score**: Minimum impact threshold (0-100)
3. **Source**: `nitter`, `rss`
4. **User Subscriptions**: Filter by user's nitter_accounts, rss_feeds, categories, keywords

**Example**:
```bash
# Politics news with impact > 70
curl "http://localhost:8000/api/v1/news?category=politics&min_impact=70"

# User-specific news
curl "http://localhost:8000/api/v1/news?user_id=user123"
```

### Pagination

Currently implemented via `limit` parameter. Future versions will add `offset` and `page` parameters.

---

## Rate Limiting

Current limits (when Nginx is configured):

- API requests: 10 requests/second per IP
- WebSocket connections: 5000 concurrent

Headers will be added in future versions:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 8
X-RateLimit-Reset: 1735444900
```

---

## Error Codes

| Code | Description |
|------|-------------|
| `400` | Bad Request - Invalid parameters or JSON |
| `404` | Not Found - Resource not found |
| `500` | Internal Server Error - Server error |
| `503` | Service Unavailable - Maintenance or overload |

---

## Data Types

### NewsItem

```json
{
  "id": "string",              // Unique identifier
  "source": "nitter|rss",     // Source type
  "source_account": "string",   // @handle or publication name
  "title": "string",           // Headline (RSS only)
  "content": "string",         // News content
  "url": "string",            // Original URL
  "published_at": "number",    // Unix timestamp

  // Analysis (no ML)
  "impact_score": "number",     // 0-100
  "relevance_score": "number",  // 0-100

  // Entities
  "tickers": ["string"],        // Crypto/stock symbols
  "people": ["string"],        // Named people
  "prediction_markets": [],     // To be linked (Tier 2)
  "category": "string",        // Category
  "tags": ["string"],          // Extracted tags

  // Processing
  "is_duplicate": "boolean",
  "is_high_signal": "boolean"  // if impact > 70
}
```

### UserSubscription

```json
{
  "user_id": "string",
  "nitter_accounts": ["string"],
  "rss_feeds": ["string"],
  "categories": ["string"],
  "keywords": ["string"],
  "impact_threshold": "number",
  "alert_channels": ["string"],
  "created_at": "number",
  "updated_at": "number"
}
```

---

## SDK Examples

### Python

```python
import aiohttp
import asyncio
import json

async def get_news(category="politics", limit=20):
    async with aiohttp.ClientSession() as session:
        url = f"http://localhost:8000/api/v1/news"
        params = {"category": category, "limit": limit}

        async with session.get(url, params=params) as resp:
            data = await resp.json()
            return data["items"]

async def websocket_news(user_id):
    import websockets

    uri = f"ws://localhost:8000/ws/news?user_id={user_id}"
    async with websockets.connect(uri) as ws:
        while True:
            message = await ws.recv()
            data = json.loads(message)
            if data["type"] == "news_item":
                print(f"News: {data['data']['title']}")

asyncio.run(websocket_news("user123"))
```

### JavaScript

```javascript
// Fetch news
async function getNews(category = 'politics', limit = 20) {
  const url = `http://localhost:8000/api/v1/news`;
  const params = new URLSearchParams({
    category,
    limit: limit.toString()
  });

  const response = await fetch(`${url}?${params}`);
  const data = await response.json();
  return data.items;
}

// WebSocket connection
const ws = new WebSocket('ws://localhost:8000/ws/news?user_id=user123');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'news_item') {
    console.log('News:', data.data.title);
  }
};
```

---

## OpenAPI/Swagger

Interactive API documentation available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## Changelog

### Version 0.1.0 (MVP)
- Initial release
- Nitter + RSS aggregation
- Entity extraction (no ML)
- Rule-based impact scoring
- WebSocket streaming
- SQLite persistence
