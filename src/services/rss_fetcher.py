import asyncio
import aiohttp
import feedparser
from typing import List
import structlog

from models import RawNewsItem

logger = structlog.get_logger()


class RSSFetcher:
    """
    Ultra-lightweight RSS fetcher
    - 5 feeds
    - No Redis (in-memory queue)
    """

    FEEDS = [
        "https://www.reutersagency.com/feed/?best=topnews",
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://apnews.com/rss/world-news"
    ]

    def __init__(self, output_queue: asyncio.Queue):
        self.output_queue = output_queue
        self.session = None
        self.running = False

    async def start(self):
        """Start RSS fetcher"""
        self.session = aiohttp.ClientSession()
        self.running = True
        asyncio.create_task(self._fetch_loop())
        logger.info("RSS fetcher started")

    async def stop(self):
        """Stop RSS fetcher"""
        self.running = False
        await self.session.close()
        logger.info("RSS fetcher stopped")

    async def _fetch_feed(self, url: str) -> List[Dict]:
        """Fetch single RSS feed"""
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    xml = await resp.text()
                    feed = feedparser.parse(xml)

                    items = []
                    for entry in feed.entries[:20]:
                        items.append({
                            'source': 'rss',
                            'source_account': feed.feed.get('title', 'Unknown'),
                            'title': entry.get('title', ''),
                            'content': entry.get('description', ''),
                            'url': entry.get('link', ''),
                            'published_at': entry.get('published', '')
                        })

                    logger.info(f"Fetched {len(items)} items from {url}")
                    return items
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")

        return []

    async def _fetch_loop(self):
        """Main fetching loop - every 2 minutes"""
        while self.running:
            start_time = asyncio.get_event_loop().time()

            logger.info(f"Starting fetch cycle for {len(self.FEEDS)} feeds")

            tasks = [self._fetch_feed(url) for url in self.FEEDS]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Fetch failed: {result}")
                    continue

                if result:
                    for item in result:
                        await self.output_queue.put(RawNewsItem(**item))

            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(f"Fetch cycle completed in {elapsed:.2f}s")

            # Wait to maintain 120-second interval
            if elapsed < 120:
                await asyncio.sleep(120 - elapsed)
