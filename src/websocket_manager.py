import asyncio
import json
import time
from typing import Dict, List, Set, Optional
import structlog

from fastapi import WebSocket, WebSocketDisconnect, status

logger = structlog.get_logger()


class ConnectionManager:
    """
    Manages WebSocket connections with thread-safe operations
    """

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> bool:
        """
        Register a new WebSocket connection for a user

        Args:
            user_id: User identifier
            websocket: WebSocket connection

        Returns:
            True if connected successfully, False if user already connected
        """
        async with self._lock:
            if user_id in self.active_connections:
                logger.warning(f"User {user_id} already has an active connection")
                return False

            self.active_connections[user_id] = websocket
            logger.info(
                f"User {user_id} connected",
                active_connections=len(self.active_connections),
            )
            return True

    async def disconnect(self, user_id: str):
        """
        Remove a user's WebSocket connection

        Args:
            user_id: User identifier
        """
        async with self._lock:
            if user_id in self.active_connections:
                del self.active_connections[user_id]
                logger.info(
                    f"User {user_id} disconnected",
                    active_connections=len(self.active_connections),
                )

    async def send_to_user(self, user_id: str, message: dict) -> bool:
        """
        Send a message to a specific user

        Args:
            user_id: User identifier
            message: Message to send (will be JSON serialized)

        Returns:
            True if sent successfully, False if user not connected or send failed
        """
        async with self._lock:
            if user_id not in self.active_connections:
                return False

            websocket = self.active_connections[user_id]

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send to user {user_id}: {e}")
            await self.disconnect(user_id)
            return False

    async def broadcast(self, message: dict, user_ids: Optional[List[str]] = None):
        """
        Broadcast a message to multiple users

        Args:
            message: Message to send (will be JSON serialized)
            user_ids: List of user IDs to send to. If None, sends to all connected users
        """
        async with self._lock:
            if user_ids:
                target_users = [
                    uid for uid in user_ids if uid in self.active_connections
                ]
            else:
                target_users = list(self.active_connections.keys())

        tasks = []
        for user_id in target_users:
            task = self.send_to_user(user_id, message)
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_connected_users(self) -> Set[str]:
        """
        Get set of currently connected user IDs

        Returns:
            Set of user IDs
        """
        return set(self.active_connections.keys())

    async def get_connection_count(self) -> int:
        """
        Get number of active connections

        Returns:
            Number of active connections
        """
        async with self._lock:
            return len(self.active_connections)

    async def send_ping_to_user(self, user_id: str) -> bool:
        """
        Send a ping frame to keep connection alive

        Args:
            user_id: User identifier

        Returns:
            True if sent successfully
        """
        return await self.send_to_user(
            user_id, {"type": "keep_alive", "timestamp": time.time()}
        )

    async def send_keepalive_to_all(self):
        """
        Send keepalive message to all connected users
        """
        message = {"type": "keep_alive", "timestamp": time.time()}
        await self.broadcast(message)


class WebSocketBroadcaster:
    """
    Background task that consumes from WebSocket queue and broadcasts to connected users
    """

    def __init__(
        self,
        websocket_queue: asyncio.Queue,
        connection_manager: ConnectionManager,
        db_path: str,
    ):
        self.websocket_queue = websocket_queue
        self.connection_manager = connection_manager
        self.db_path = db_path
        self.running = False

    async def start(self):
        """Start the broadcaster"""
        self.running = True
        asyncio.create_task(self._broadcast_loop())
        logger.info("WebSocket broadcaster started")

    async def stop(self):
        """Stop the broadcaster"""
        self.running = False
        logger.info("WebSocket broadcaster stopped")

    async def _broadcast_loop(self):
        """Main broadcast loop"""
        while self.running:
            try:
                news_item = await self.websocket_queue.get()

                if isinstance(news_item, Exception):
                    logger.error(f"Received error from WebSocket queue: {news_item}")
                    continue

                await self._process_news_item(news_item)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _process_news_item(self, news_item: dict):
        """
        Process a news item and send to matching users

        Args:
            news_item: News item dictionary
        """
        connected_users = self.connection_manager.get_connected_users()

        if not connected_users:
            return

        matched_users = []

        for user_id in connected_users:
            try:
                if await self._matches_user_subscription(user_id, news_item):
                    matched_users.append(user_id)
            except Exception as e:
                logger.error(f"Error checking subscription for user {user_id}: {e}")
                continue

        if matched_users:
            message = {"type": "news_item", "data": news_item, "timestamp": time.time()}

            await self.connection_manager.broadcast(message, matched_users)
            logger.info(
                f"Broadcast news to {len(matched_users)} users",
                news_id=news_item.get("id"),
                matched_users=matched_users,
            )

    async def _matches_user_subscription(self, user_id: str, news_item: dict) -> bool:
        """
        Check if a news item matches a user's subscription

        Args:
            user_id: User identifier
            news_item: News item dictionary

        Returns:
            True if matches, False otherwise
        """
        import aiosqlite

        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM user_subscriptions WHERE user_id = ?", (user_id,)
                )
                row = await cursor.fetchone()

                if not row:
                    return True

                return self._check_filters(row, news_item)

        except aiosqlite.OperationalError:
            return True
        except Exception as e:
            logger.error(f"Error checking subscription: {e}")
            return True

    def _check_filters(self, subscription_row: tuple, news_item: dict) -> bool:
        """
        Check if news item passes subscription filters

        Args:
            subscription_row: Database row for subscription
            news_item: News item dictionary

        Returns:
            True if passes filters
        """
        try:
            news_category = news_item.get("category")
            news_source = news_item.get("source")
            news_source_account = news_item.get("source_account")
            news_impact = news_item.get("impact_score", 0)
            news_tickers = news_item.get("tickers", [])
            news_content = (
                f"{news_item.get('title', '')} {news_item.get('content', '')}"
            )

            nitter_accounts = (
                json.loads(subscription_row[1]) if subscription_row[1] else []
            )
            rss_feeds = json.loads(subscription_row[2]) if subscription_row[2] else []
            categories = json.loads(subscription_row[3]) if subscription_row[3] else []
            keywords = json.loads(subscription_row[4]) if subscription_row[4] else []
            impact_threshold = subscription_row[5]

            if impact_threshold and news_impact < impact_threshold:
                return False

            if categories and news_category not in categories:
                return False

            if nitter_accounts and news_source == "nitter":
                if not any(
                    account.lower() in (news_source_account or "").lower()
                    for account in nitter_accounts
                ):
                    return False

            if rss_feeds and news_source == "rss":
                if not any(
                    feed.lower() in (news_source_account or "").lower()
                    for feed in rss_feeds
                ):
                    return False

            if keywords:
                keyword_lower = [k.lower() for k in keywords]
                content_lower = news_content.lower()
                ticker_lower = [t.lower() for t in news_tickers]

                has_keyword_match = any(kw in content_lower for kw in keyword_lower)
                has_ticker_match = any(
                    ticker in ticker_lower for ticker in keyword_lower
                )

                if not (has_keyword_match or has_ticker_match):
                    return False

            return True

        except Exception as e:
            logger.error(f"Error checking filters: {e}")
            return True
