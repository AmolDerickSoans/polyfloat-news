import aiosqlite
import asyncio
from datetime import datetime
from pathlib import Path

DB_PATH = "news_api.db"


async def init_database():
    """Initialize SQLite database with schema"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Enable WAL mode for concurrency
        await db.execute("PRAGMA journal_mode = WAL")
        await db.execute("PRAGMA synchronous = NORMAL")
        await db.execute("PRAGMA cache_size = -64000")
        await db.execute("PRAGMA temp_store = MEMORY")

        # Create news_items table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS news_items (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                source_account TEXT,
                title TEXT,
                content TEXT NOT NULL,
                url TEXT NOT NULL,
                published_at REAL NOT NULL,

                impact_score REAL DEFAULT 0.0,
                relevance_score REAL DEFAULT 0.0,

                tickers TEXT DEFAULT '[]',
                people TEXT DEFAULT '[]',
                prediction_markets TEXT DEFAULT '[]',
                category TEXT,
                tags TEXT DEFAULT '[]',

                is_duplicate INTEGER DEFAULT 0,
                duplicate_of TEXT,
                is_curated INTEGER DEFAULT 0,
                is_high_signal INTEGER DEFAULT 0,

                created_at REAL NOT NULL
            )
        """)

        # Create indexes
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_published
            ON news_items(published_at DESC)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_impact
            ON news_items(impact_score DESC)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_category
            ON news_items(category)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_source
            ON news_items(source)
        """)

        # Create user_subscriptions table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                user_id TEXT PRIMARY KEY,
                nitter_accounts TEXT DEFAULT '[]',
                rss_feeds TEXT DEFAULT '[]',
                categories TEXT DEFAULT '[]',
                keywords TEXT DEFAULT '[]',
                impact_threshold INTEGER DEFAULT 70,
                alert_channels TEXT DEFAULT '["terminal"]',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        # Create stats table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at REAL NOT NULL
            )
        """)

        await db.commit()
        print(f"Database initialized at {DB_PATH}")


async def cleanup_old_news(days: int = 30):
    """Delete news items older than specified days"""
    import time
    cutoff = datetime.now().timestamp() - (days * 24 * 3600)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM news_items WHERE published_at < ?",
            (cutoff,)
        )
        await db.commit()
        print(f"Cleaned up news items older than {days} days")


if __name__ == "__main__":
    asyncio.run(init_database())
