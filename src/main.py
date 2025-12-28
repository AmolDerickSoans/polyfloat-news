import asyncio
import time
import json
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path as PathLib

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    status,
    Query,
    Body,
    Path,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import aiosqlite
import structlog

from .models import (
    HealthStatus,
    SystemStats,
    NewsItem,
    UserSubscription,
    UserSubscriptionCreate,
    NewsListResponse,
    SubscriptionResponse,
)
from .services.nitter_scraper import NitterScraper
from .services.rss_fetcher import RSSFetcher
from .services.news_processor import NewsProcessor
from .websocket_manager import ConnectionManager, WebSocketBroadcaster

logger = structlog.get_logger()

BASE_DIR = PathLib(__file__).resolve().parent.parent
DB_PATH = str(BASE_DIR / "news_api.db")
START_TIME = time.time()

app_state: Dict[str, Any] = {
    "db": None,
    "nitter_scraper": None,
    "rss_fetcher": None,
    "news_processor": None,
    "raw_news_queue": None,
    "websocket_queue": None,
    "active_connections": 0,
    "connection_manager": None,
    "broadcaster": None,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    logger.info("Starting Polyfloat News API")

    try:
        await startup()
        yield
        await shutdown()
    except Exception as e:
        logger.error("Fatal error during lifespan", error=str(e))
        raise


async def startup():
    """Startup tasks"""
    logger.info("Initializing database connection")
    app_state["db"] = await aiosqlite.connect(DB_PATH)
    await app_state["db"].execute("PRAGMA journal_mode = WAL")
    await app_state["db"].execute("PRAGMA synchronous = NORMAL")
    await app_state["db"].execute("PRAGMA foreign_keys = ON")

    await app_state["db"].executescript(
        """
        CREATE TABLE IF NOT EXISTS user_subscriptions (
            user_id TEXT PRIMARY KEY,
            nitter_accounts TEXT,
            rss_feeds TEXT,
            categories TEXT,
            keywords TEXT,
            impact_threshold INTEGER DEFAULT 70,
            alert_channels TEXT,
            created_at REAL,
            updated_at REAL
        );

        CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
    """
    )
    await app_state["db"].commit()

    logger.info("Creating queues")
    app_state["raw_news_queue"] = asyncio.Queue(maxsize=10000)
    app_state["websocket_queue"] = asyncio.Queue(maxsize=10000)

    logger.info("Starting background services")
    app_state["nitter_scraper"] = NitterScraper(app_state["raw_news_queue"])
    await app_state["nitter_scraper"].start()

    app_state["rss_fetcher"] = RSSFetcher(app_state["raw_news_queue"])
    await app_state["rss_fetcher"].start()

    app_state["news_processor"] = NewsProcessor(
        app_state["raw_news_queue"], app_state["websocket_queue"], DB_PATH
    )
    await app_state["news_processor"].start()

    logger.info("Initializing WebSocket manager")
    app_state["connection_manager"] = ConnectionManager()
    app_state["broadcaster"] = WebSocketBroadcaster(
        app_state["websocket_queue"], app_state["connection_manager"], DB_PATH
    )
    await app_state["broadcaster"].start()

    logger.info("Polyfloat News API started successfully")


async def shutdown():
    """Shutdown tasks"""
    logger.info("Stopping Polyfloat News API")

    if app_state.get("broadcaster"):
        await app_state["broadcaster"].stop()
        logger.info("WebSocket broadcaster stopped")

    if app_state.get("nitter_scraper"):
        await app_state["nitter_scraper"].stop()
        logger.info("Nitter scraper stopped")

    if app_state.get("rss_fetcher"):
        await app_state["rss_fetcher"].stop()
        logger.info("RSS fetcher stopped")

    if app_state.get("news_processor"):
        await app_state["news_processor"].stop()
        logger.info("News processor stopped")

    if app_state.get("db"):
        await app_state["db"].close()
        logger.info("Database connection closed")

    logger.info("Polyfloat News API stopped successfully")


app = FastAPI(
    title="Polyfloat News API",
    description="Real-time news aggregation from Nitter and RSS sources",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get("/health", response_model=HealthStatus, tags=["health"])
async def health_check():
    """Health check endpoint"""
    db_status = "disconnected"
    nitter_status = {}

    try:
        if app_state.get("db"):
            await app_state["db"].execute("SELECT 1")
            db_status = "connected"

        if app_state.get("nitter_scraper"):
            nitter_status = {
                f"nitter-{i+1}": "healthy" for i in range(len(NitterScraper.INSTANCES))
            }

        return HealthStatus(
            status="healthy" if db_status == "connected" else "unhealthy",
            database=db_status,
            nitter_instances=nitter_status,
            timestamp=time.time(),
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthStatus(
            status="unhealthy",
            database=db_status,
            nitter_instances=nitter_status,
            timestamp=time.time(),
        )


@app.get("/api/v1/stats", response_model=SystemStats, tags=["stats"])
async def get_system_stats():
    """Get system statistics"""
    try:
        active_connections = 0
        if app_state.get("connection_manager"):
            active_connections = await app_state[
                "connection_manager"
            ].get_connection_count()

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM news_items")
            total_count = (await cursor.fetchone())[0]

            cursor = await db.execute(
                "SELECT COUNT(*) FROM news_items WHERE published_at > ?",
                (time.time() - 86400,),
            )
            last_24h = (await cursor.fetchone())[0]

            cursor = await db.execute(
                "SELECT AVG(impact_score) FROM news_items WHERE impact_score > 0"
            )
            avg_impact = (await cursor.fetchone())[0] or 0.0

        return SystemStats(
            total_news_items=total_count,
            items_last_24h=last_24h,
            average_impact=round(avg_impact, 2),
            active_connections=active_connections,
            nitter_instances={
                "total": len(NitterScraper.INSTANCES),
                "healthy": len(NitterScraper.INSTANCES),
            },
            rss_feeds={"total": len(RSSFetcher.FEEDS), "active": len(RSSFetcher.FEEDS)},
            uptime_seconds=round(time.time() - START_TIME, 2),
            version="0.1.0",
        )
    except Exception as e:
        logger.error("Failed to get system stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics",
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Polyfloat News API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


async def get_news_items(
    limit: int = 20,
    offset: int = 0,
    source: Optional[str] = None,
    category: Optional[str] = None,
    min_impact: Optional[float] = None,
    ticker: Optional[str] = None,
    person: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
) -> NewsListResponse:
    """Query news items from database with filters

    Args:
        limit: Number of items to return (max 100)
        offset: Number of items to skip (max 1000)
        source: Filter by source type (nitter, rss)
        category: Filter by category
        min_impact: Filter by minimum impact score
        ticker: Filter by ticker symbol
        person: Filter by person name
        start_time: Filter news after this timestamp
        end_time: Filter news before this timestamp

    Returns:
        NewsListResponse with filtered items
    """
    query = "SELECT * FROM news_items WHERE 1=1"
    params = []

    if source:
        query += " AND source = ?"
        params.append(source)

    if category:
        query += " AND category = ?"
        params.append(category)

    if min_impact is not None:
        query += " AND impact_score >= ?"
        params.append(min_impact)

    if ticker:
        query += " AND tickers LIKE ?"
        params.append(f'%"{ticker}"%')

    if person:
        query += " AND people LIKE ?"
        params.append(f'%"{person}"%')

    if start_time is not None:
        query += " AND published_at >= ?"
        params.append(start_time)

    if end_time is not None:
        query += " AND published_at <= ?"
        params.append(end_time)

    query += " ORDER BY published_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        count_query = "SELECT COUNT(*) FROM news_items WHERE 1=1"
        count_params = []
        if source:
            count_query += " AND source = ?"
            count_params.append(source)
        if category:
            count_query += " AND category = ?"
            count_params.append(category)
        if min_impact is not None:
            count_query += " AND impact_score >= ?"
            count_params.append(min_impact)
        if ticker:
            count_query += " AND tickers LIKE ?"
            count_params.append(f'%"{ticker}"%')
        if person:
            count_query += " AND people LIKE ?"
            count_params.append(f'%"{person}"%')
        if start_time is not None:
            count_query += " AND published_at >= ?"
            count_params.append(start_time)
        if end_time is not None:
            count_query += " AND published_at <= ?"
            count_params.append(end_time)

        count_cursor = await db.execute(count_query, count_params)
        total = (await count_cursor.fetchone())[0]

    items = []
    for row in rows:
        try:
            items.append(
                NewsItem(
                    id=row[0],
                    source=row[1],
                    source_account=row[2],
                    title=row[3],
                    content=row[4],
                    url=row[5],
                    published_at=row[6],
                    impact_score=row[7],
                    relevance_score=row[8],
                    tickers=json.loads(row[9]) if row[9] else [],
                    people=json.loads(row[10]) if row[10] else [],
                    prediction_markets=json.loads(row[11]) if row[11] else [],
                    category=row[12],
                    tags=json.loads(row[13]) if row[13] else [],
                    is_duplicate=bool(row[14]),
                    duplicate_of=row[15],
                    is_high_signal=bool(row[17]),
                )
            )
        except Exception as e:
            logger.warning("Failed to parse news item", id=row[0], error=str(e))
            continue

    return NewsListResponse(items=items, total=total, limit=limit, offset=offset)


async def create_subscription(subscription: UserSubscriptionCreate) -> UserSubscription:
    """Create or update user subscription

    Validates subscription data and stores in database.
    If user_id already exists, updates the existing subscription.

    Args:
        subscription: User subscription data to create/update

    Returns:
        Created or updated UserSubscription

    Raises:
        HTTPException: If validation fails or database error occurs
    """
    now = time.time()

    if not subscription.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required",
        )

    if subscription.impact_threshold < 0 or subscription.impact_threshold > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="impact_threshold must be between 0 and 100",
        )

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_subscriptions (
                user_id, nitter_accounts, rss_feeds, categories, keywords,
                impact_threshold, alert_channels, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                nitter_accounts = excluded.nitter_accounts,
                rss_feeds = excluded.rss_feeds,
                categories = excluded.categories,
                keywords = excluded.keywords,
                impact_threshold = excluded.impact_threshold,
                alert_channels = excluded.alert_channels,
                updated_at = excluded.updated_at
        """,
            (
                subscription.user_id,
                json.dumps(subscription.nitter_accounts),
                json.dumps(subscription.rss_feeds),
                json.dumps(subscription.categories),
                json.dumps(subscription.keywords),
                subscription.impact_threshold,
                json.dumps(subscription.alert_channels),
                now,
                now,
            ),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM user_subscriptions WHERE user_id = ?",
            (subscription.user_id,),
        )
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription",
        )

    return UserSubscription(
        user_id=row[0],
        nitter_accounts=json.loads(row[1]) if row[1] else [],
        rss_feeds=json.loads(row[2]) if row[2] else [],
        categories=json.loads(row[3]) if row[3] else [],
        keywords=json.loads(row[4]) if row[4] else [],
        impact_threshold=row[5],
        alert_channels=json.loads(row[6]) if row[6] else [],
        created_at=row[7],
        updated_at=row[8],
    )


async def get_subscriptions(user_id: str) -> List[UserSubscription]:
    """Get subscriptions for a user"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT * FROM user_subscriptions WHERE user_id = ?", (user_id,)
        )
        rows = await cursor.fetchall()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User subscription '{user_id}' not found",
        )

    subscriptions = []
    for row in rows:
        try:
            subscriptions.append(
                UserSubscription(
                    user_id=row[0],
                    nitter_accounts=json.loads(row[1]) if row[1] else [],
                    rss_feeds=json.loads(row[2]) if row[2] else [],
                    categories=json.loads(row[3]) if row[3] else [],
                    keywords=json.loads(row[4]) if row[4] else [],
                    impact_threshold=row[5],
                    alert_channels=json.loads(row[6]) if row[6] else [],
                    created_at=row[7],
                    updated_at=row[8],
                )
            )
        except Exception as e:
            logger.warning("Failed to parse subscription", user_id=row[0], error=str(e))
            continue

    return subscriptions


async def delete_subscription(user_id: str) -> bool:
    """Delete entire user subscription

    Args:
        user_id: User identifier

    Returns:
        True if deletion was successful

    Raises:
        HTTPException: If user subscription not found (404)
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id FROM user_subscriptions WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User subscription '{user_id}' not found",
            )

        await db.execute(
            "DELETE FROM user_subscriptions WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()

    return True


@app.get(
    "/api/v1/news",
    response_model=NewsListResponse,
    tags=["news"],
    responses={
        400: {"description": "Invalid query parameters"},
        500: {"description": "Internal server error"},
    },
)
async def get_news(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of items to return (max 100)",
        example=20,
    ),
    offset: int = Query(
        default=0,
        ge=0,
        le=1000,
        description="Number of items to skip (max 1000)",
        example=0,
    ),
    source: Optional[str] = Query(
        default=None,
        description="Filter by source (nitter, rss)",
        example="nitter",
    ),
    category: Optional[str] = Query(
        default=None,
        description="Filter by category (politics, crypto, economics, sports, other)",
        example="politics",
    ),
    min_score: Optional[float] = Query(
        default=None,
        ge=0.0,
        le=100.0,
        description="Filter by minimum impact score (0-100)",
        example=70.0,
    ),
    start_time: Optional[float] = Query(
        default=None,
        description="Filter news after this timestamp (Unix timestamp)",
        example=1735444800.0,
    ),
    end_time: Optional[float] = Query(
        default=None,
        description="Filter news before this timestamp (Unix timestamp)",
        example=1735531200.0,
    ),
    ticker: Optional[str] = Query(
        default=None,
        description="Filter by ticker symbol",
        example="BTC",
    ),
    person: Optional[str] = Query(
        default=None,
        description="Filter by person name",
        example="trump",
    ),
):
    """Get recent news items with optional filtering

    Returns a paginated list of news items. All query parameters are optional.
    If no filters are provided, returns the most recent news items.

    Query Parameters:
        limit: Number of items to return (1-100, default: 20)
        offset: Number of items to skip (0-1000, default: 0)
        source: Filter by source type (nitter, rss)
        category: Filter by category (politics, crypto, economics, sports, other)
        min_score: Minimum impact score (0-100)
        start_time: Unix timestamp - only return news after this time
        end_time: Unix timestamp - only return news before this time
        ticker: Filter by ticker symbol (e.g., BTC, ETH)
        person: Filter by person name (e.g., trump, elon)

    Returns:
        NewsListResponse with items, total count, limit, and offset
    """
    try:
        result = await get_news_items(
            limit=limit,
            offset=offset,
            source=source,
            category=category,
            min_impact=min_score,
            ticker=ticker,
            person=person,
            start_time=start_time,
            end_time=end_time,
        )

        return result
    except ValueError as e:
        logger.warning("Invalid query parameters", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid query parameters: {str(e)}",
        )
    except Exception as e:
        logger.error("Failed to get news items", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve news items",
        )


@app.post(
    "/api/v1/subscriptions",
    response_model=SubscriptionResponse,
    tags=["subscriptions"],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Subscription created successfully"},
        400: {"description": "Invalid request body"},
        500: {"description": "Internal server error"},
    },
)
async def create_user_subscription(
    subscription: UserSubscriptionCreate = Body(
        ..., description="Subscription details"
    ),
):
    """Create or update a user subscription

    Creates a new subscription or updates an existing one for the specified user.
    If the user_id already exists, all settings will be replaced with the new values.

    Request Body:
        user_id: Unique user identifier (required)
        nitter_accounts: List of Nitter accounts to follow (e.g., ["@elonmusk"])
        rss_feeds: List of RSS feed sources
        categories: List of categories to filter (e.g., ["politics", "crypto"])
        keywords: List of keywords to track
        impact_threshold: Minimum impact score for alerts (0-100, default: 70)
        alert_channels: List of alert channels (default: ["terminal"])

    Returns:
        SubscriptionResponse with status, user_id, and created_at timestamp

    Raises:
        HTTPException: If validation fails or database error occurs
    """
    try:
        result = await create_subscription(subscription)
        return SubscriptionResponse(
            status="created",
            user_id=result.user_id,
            created_at=result.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create subscription",
            user_id=subscription.user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription",
        )
    except Exception as e:
        logger.error(
            "Failed to create subscription", user_id=subscription.user_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription",
        )


@app.get(
    "/api/v1/subscriptions/{user_id}",
    response_model=List[UserSubscription],
    tags=["subscriptions"],
    responses={
        200: {"description": "Subscriptions retrieved successfully"},
        404: {"description": "User not found"},
    },
)
async def get_user_subscriptions(
    user_id: str = Path(..., description="User identifier", example="user123"),
):
    """Get subscription settings for a user"""
    try:
        subscriptions = await get_subscriptions(user_id)
        return subscriptions
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get subscriptions", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscriptions",
        )


@app.delete(
    "/api/v1/subscriptions/{user_id}",
    tags=["subscriptions"],
    responses={
        200: {"description": "Subscription deleted successfully"},
        404: {"description": "Subscription not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_user_subscription(
    user_id: str = Path(..., description="User identifier", example="user123"),
):
    """Delete a user's entire subscription

    Removes all subscription settings for the specified user.
    This cannot be undone.

    Path Parameters:
        user_id: Unique user identifier

    Returns:
        JSON response with status and user_id
    """
    try:
        await delete_subscription(user_id)
        return {"status": "deleted", "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete subscription", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete subscription",
        )


@app.websocket("/ws/news")
async def websocket_news_endpoint(
    websocket: WebSocket, user_id: str = Query(..., description="User identifier")
):
    """WebSocket endpoint for real-time news updates"""
    connection_manager = app_state.get("connection_manager")
    if not connection_manager:
        await websocket.close(
            code=status.WS_1013_TRY_AGAIN_LATER, reason="Service not ready"
        )
        return

    await websocket.accept()

    connected = await connection_manager.connect(user_id, websocket)
    if not connected:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="User already connected"
        )
        return

    logger.info(f"WebSocket connection established for user: {user_id}")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                logger.debug(f"Received message from user {user_id}", message=message)

                if message.get("type") == "ping":
                    await connection_manager.send_to_user(
                        user_id, {"type": "pong", "timestamp": time.time()}
                    )
                elif message.get("type") == "subscribe":
                    logger.info(
                        f"User {user_id} updated filters",
                        filters=message.get("filters"),
                    )

            except json.JSONDecodeError:
                logger.warning(f"Received invalid JSON from user {user_id}")
                await connection_manager.send_to_user(
                    user_id, {"type": "error", "message": "Invalid JSON"}
                )
            except Exception as e:
                logger.error(
                    f"Error processing message from user {user_id}", error=str(e)
                )
                await connection_manager.send_to_user(
                    user_id, {"type": "error", "message": "Internal server error"}
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user: {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}", exc_info=True)
    finally:
        await connection_manager.disconnect(user_id)
        logger.info(f"Cleaned up connection for user: {user_id}")
