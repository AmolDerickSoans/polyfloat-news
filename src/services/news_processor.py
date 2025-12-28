import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import aiosqlite
import structlog

from ..models import NewsItem, RawNewsItem, SourceType
from .entity_extractor import EntityExtractor

logger = structlog.get_logger()


class NewsProcessor:
    """
    Central news processing pipeline
    - Consumes raw news from scraper/fetcher
    - Deduplicates based on URL
    - Extracts entities
    - Scores impact using rules
    - Stores in SQLite database
    - Publishes to WebSocket queue
    """

    SOURCE_AUTHORITY_SCORES = {
        "reuters": 10,
        "ap": 10,
        "associated press": 10,
        "wsj": 8,
        "wall street journal": 8,
        "bloomberg": 8,
        "cnbc": 6,
        "nitter": 5,
        "twitter": 5,
        "x.com": 5,
    }

    ENTITY_IMPORTANCE_SCORES = {
        "Fed Chair": 10,
        "Fed Chairman": 10,
        "Jerome Powell": 10,
        "Joe Biden": 10,
        "President Biden": 10,
        "Donald Trump": 10,
        "President Trump": 10,
        "Elon Musk": 8,
        "Michael Saylor": 8,
        "Balaji Srinivasan": 8,
        "Vitalik Buterin": 8,
        "Gary Gensler": 8,
        "Jamie Dimon": 8,
        "Larry Fink": 8,
        "Warren Buffett": 8,
        "Janet Yellen": 8,
    }

    KEYWORD_RELEVANCE_SCORES = {
        "breaking": 10,
        "urgent": 10,
        "alert": 10,
        "major": 8,
        "significant": 8,
        "important": 8,
        "update": 8,
        "exclusive": 8,
        "report": 5,
        "news": 5,
        "announcement": 5,
    }

    def __init__(
        self,
        input_queue: asyncio.Queue,
        websocket_queue: asyncio.Queue,
        db_path: str = "news_api.db",
    ):
        self.input_queue = input_queue
        self.websocket_queue = websocket_queue
        self.db_path = db_path
        self.entity_extractor = EntityExtractor()
        self.running = False
        self.db_conn = None

    async def start(self):
        """Start the news processor"""
        await self._init_database()
        self.running = True
        asyncio.create_task(self._process_loop())
        asyncio.create_task(self._cleanup_loop())
        logger.info("News processor started")

    async def stop(self):
        """Stop the news processor"""
        self.running = False
        if self.db_conn:
            await self.db_conn.close()
        logger.info("News processor stopped")

    async def _init_database(self):
        """Initialize database schema"""
        self.db_conn = await aiosqlite.connect(self.db_path)
        await self.db_conn.execute("PRAGMA journal_mode=WAL")
        await self.db_conn.execute("PRAGMA foreign_keys=ON")

        await self.db_conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS news (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                source_account TEXT,
                title TEXT,
                content TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                published_at REAL NOT NULL,
                impact_score REAL DEFAULT 0,
                relevance_score REAL DEFAULT 0,
                tickers TEXT,
                people TEXT,
                prediction_markets TEXT,
                category TEXT,
                tags TEXT,
                is_duplicate INTEGER DEFAULT 0,
                duplicate_of TEXT,
                is_high_signal INTEGER DEFAULT 0,
                created_at REAL DEFAULT (strftime('%s', 'now'))
            );

            CREATE INDEX IF NOT EXISTS idx_news_url ON news(url);
            CREATE INDEX IF NOT EXISTS idx_news_published_at ON news(published_at DESC);
            CREATE INDEX IF NOT EXISTS idx_news_impact_score ON news(impact_score DESC);
            CREATE INDEX IF NOT EXISTS idx_news_category ON news(category);
        """
        )

        await self.db_conn.commit()
        logger.info("Database initialized")

    async def _process_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                raw_item = await self.input_queue.get()

                if isinstance(raw_item, Exception):
                    logger.error(f"Received error from input queue: {raw_item}")
                    continue

                await self._process_item(raw_item)

            except Exception as e:
                logger.error(f"Error in process loop: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _process_item(self, raw_item: RawNewsItem):
        """Process a single news item"""
        try:
            news_item = await self._convert_to_news_item(raw_item)

            if await self._is_duplicate(news_item.url):
                logger.debug(f"Duplicate URL: {news_item.url}")
                return

            news_item = self.entity_extractor.extract_entities(news_item)
            news_item.impact_score = self._calculate_impact_score(news_item)

            await self._store_news_item(news_item)
            await self._publish_to_websocket(news_item)

            logger.info(
                "Processed news item",
                id=news_item.id,
                url=news_item.url,
                impact_score=news_item.impact_score,
                category=news_item.category,
            )

        except Exception as e:
            logger.error(f"Failed to process item: {e}", exc_info=True)

    async def _convert_to_news_item(self, raw_item: RawNewsItem) -> NewsItem:
        """Convert RawNewsItem to NewsItem"""
        url_hash = hashlib.md5(raw_item.url.encode()).hexdigest()

        published_at = raw_item.published_at
        if isinstance(published_at, str):
            try:
                dt = datetime.strptime(published_at, "%a, %d %b %Y %H:%M:%S %z")
                published_at = dt.timestamp()
            except ValueError:
                try:
                    dt = datetime.strptime(published_at, "%b %d, %Y · %I:%M %p UTC")
                    published_at = dt.timestamp()
                except ValueError:
                    published_at = datetime.now().timestamp()

        return NewsItem(
            id=f"{raw_item.source}_{url_hash[:12]}",
            source=SourceType(raw_item.source),
            source_account=raw_item.source_account,
            title=raw_item.title,
            content=raw_item.content,
            url=raw_item.url,
            published_at=published_at,
        )

    async def _is_duplicate(self, url: str) -> bool:
        """Check if URL already exists in database"""
        try:
            async with self.db_conn.execute(
                "SELECT 1 FROM news WHERE url = ? LIMIT 1", (url,)
            ) as cursor:
                result = await cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Failed to check duplicate: {e}")
            return False

    def _calculate_impact_score(self, news_item: NewsItem) -> float:
        """Calculate impact score using rule-based scoring"""
        source_score = self._score_source(news_item)
        entity_score = self._score_entities(news_item)
        keyword_score = self._score_keywords(news_item)
        recency_score = self._score_recency(news_item)

        weights = {"source": 0.2, "entity": 0.3, "keyword": 0.3, "recency": 0.2}

        final_score = (
            source_score * weights["source"]
            + entity_score * weights["entity"]
            + keyword_score * weights["keyword"]
            + recency_score * weights["recency"]
        )

        return min(max(final_score, 0), 100)

    def _score_source(self, news_item: NewsItem) -> float:
        """Score based on source authority"""
        source_lower = news_item.source.value.lower()
        account_lower = (news_item.source_account or "").lower()

        for source, score in self.SOURCE_AUTHORITY_SCORES.items():
            if source in source_lower or source in account_lower:
                return float(score)

        return 5.0

    def _score_entities(self, news_item: NewsItem) -> float:
        """Score based on entity importance"""
        if not news_item.people:
            return 5.0

        max_score = 0
        for person in news_item.people:
            for entity, score in self.ENTITY_IMPORTANCE_SCORES.items():
                if entity.lower() in person.lower():
                    max_score = max(max_score, score)

        return float(max_score) if max_score > 0 else 5.0

    def _score_keywords(self, news_item: NewsItem) -> float:
        """Score based on keyword relevance"""
        text = f"{news_item.title or ''} {news_item.content}".lower()

        max_score = 0
        for keyword, score in self.KEYWORD_RELEVANCE_SCORES.items():
            if keyword in text:
                max_score = max(max_score, score)

        return float(max_score) if max_score > 0 else 5.0

    def _score_recency(self, news_item: NewsItem) -> float:
        """Score based on recency"""
        now = datetime.now().timestamp()
        age_hours = (now - news_item.published_at) / 3600

        if age_hours < 1:
            return 10.0
        elif age_hours < 6:
            return 8.0
        elif age_hours < 24:
            return 5.0
        elif age_hours < 48:
            return 3.0
        else:
            return 1.0

    async def _store_news_item(self, news_item: NewsItem):
        """Store news item in database"""
        try:
            await self.db_conn.execute(
                """INSERT INTO news (
                    id, source, source_account, title, content, url, published_at,
                    impact_score, relevance_score, tickers, people, prediction_markets,
                    category, tags, is_duplicate, duplicate_of, is_high_signal
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    news_item.id,
                    news_item.source.value,
                    news_item.source_account,
                    news_item.title,
                    news_item.content,
                    news_item.url,
                    news_item.published_at,
                    news_item.impact_score,
                    news_item.relevance_score,
                    json.dumps(news_item.tickers),
                    json.dumps(news_item.people),
                    json.dumps(news_item.prediction_markets),
                    news_item.category.value if news_item.category else None,
                    json.dumps(news_item.tags),
                    int(news_item.is_duplicate),
                    news_item.duplicate_of,
                    int(news_item.is_high_signal),
                ),
            )
            await self.db_conn.commit()
        except aiosqlite.IntegrityError:
            logger.warning(f"Duplicate URL during insert: {news_item.url}")
        except Exception as e:
            logger.error(f"Failed to store news item: {e}", exc_info=True)

    async def _publish_to_websocket(self, news_item: NewsItem):
        """Publish news item to WebSocket queue"""
        try:
            item_dict = news_item.model_dump()
            await self.websocket_queue.put(item_dict)
        except Exception as e:
            logger.error(f"Failed to publish to WebSocket: {e}")

    async def _cleanup_loop(self):
        """Periodic cleanup of old news items"""
        while self.running:
            try:
                await asyncio.sleep(86400)
                await self._cleanup_old_items()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_old_items(self):
        """Delete news items older than 7 days"""
        try:
            cutoff = datetime.now() - timedelta(days=7)
            cutoff_timestamp = cutoff.timestamp()

            cursor = await self.db_conn.execute(
                "DELETE FROM news WHERE published_at < ?", (cutoff_timestamp,)
            )
            deleted_count = cursor.rowcount
            await self.db_conn.commit()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old news items")

        except Exception as e:
            logger.error(f"Failed to cleanup old items: {e}")
