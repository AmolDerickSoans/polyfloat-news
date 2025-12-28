import asyncio
import aiohttp
import feedparser
from typing import List, Dict, Optional
import structlog
import time
from datetime import datetime

from ..models import RawNewsItem

logger = structlog.get_logger()


class RSSFetcher:
    """
    Ultra-lightweight RSS fetcher
    - 5 feeds
    - No Redis (in-memory queue)
    """

    FEEDS = [
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://feeds.bbci.co.uk/news/rss.xml",
    ]

    def __init__(self, output_queue: asyncio.Queue):
        self.output_queue = output_queue
        self.session = None
        self.running = False

    async def start(self):
        """Start RSS fetcher"""
        self.session = aiohttp.ClientSession()
        self.running = True

        async def run_fetch_loop():
            try:
                await self._fetch_loop()
            except Exception as e:
                logger.exception("fetch_loop_exception", error=str(e))

        asyncio.create_task(run_fetch_loop())
        logger.info("RSS fetcher started")

    async def stop(self):
        """Stop RSS fetcher"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("RSS fetcher stopped")

    async def _fetch_feed(self, url: str, max_retries: int = 3) -> List[Dict]:
        """Fetch single RSS feed with retry logic"""
        retry_count = 0
        base_delay = 1

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; NewsRSS/1.0; +https://example.com/news)"
        }

        while retry_count < max_retries:
            try:
                async with self.session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        xml = await resp.text()
                        feed = feedparser.parse(xml)

                        if feed.bozo:
                            logger.warning(
                                "feed_malformed",
                                url=url,
                                error=str(feed.bozo_exception),
                            )

                        items = []
                        for entry in feed.entries[:20]:
                            content = ""
                            if "content" in entry and entry.content:
                                content = entry.content[0].get("value", "")
                            elif "summary" in entry:
                                content = entry.summary

                            author = entry.get("author", None)
                            if not author and feed.feed and "author" in feed.feed:
                                author = feed.feed.author

                            published = entry.get("published", "")
                            if not published and "published_parsed" in entry:
                                try:
                                    published = datetime.fromtimestamp(
                                        time.mktime(entry.published_parsed)
                                    ).isoformat()
                                except:
                                    pass

                            items.append(
                                {
                                    "source": "rss",
                                    "source_account": feed.feed.get("title", "Unknown")
                                    if feed.feed
                                    else "Unknown",
                                    "title": entry.get("title", ""),
                                    "content": content,
                                    "url": entry.get("link", ""),
                                    "published_at": published,
                                    "author": author,
                                    "summary": entry.get("summary", ""),
                                }
                            )

                        logger.info(
                            "fetch_success",
                            url=url,
                            items_count=len(items),
                            feed_title=feed.feed.get("title", "Unknown")
                            if feed.feed
                            else "Unknown",
                        )
                        return items
                    else:
                        logger.warning("fetch_http_error", url=url, status=resp.status)

            except asyncio.TimeoutError:
                logger.warning("fetch_timeout", url=url, retry=retry_count + 1)
            except aiohttp.ClientError as e:
                logger.warning(
                    "fetch_client_error", url=url, error=str(e), retry=retry_count + 1
                )
            except Exception as e:
                logger.error(
                    "fetch_unexpected_error",
                    url=url,
                    error=str(e),
                    retry=retry_count + 1,
                )

            retry_count += 1
            if retry_count < max_retries:
                delay = base_delay * (2**retry_count)
                logger.info(
                    "fetch_retry", url=url, retry=retry_count + 1, delay_seconds=delay
                )
                await asyncio.sleep(delay)

        logger.error("fetch_failed_max_retries", url=url, max_retries=max_retries)
        return []

    async def _fetch_loop(self):
        """Main fetching loop - every 2 minutes"""
        while self.running:
            start_time = asyncio.get_event_loop().time()

            logger.info(f"Starting fetch cycle for {len(self.FEEDS)} feeds")

            tasks = [self._fetch_feed(url) for url in self.FEEDS]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_items = 0
            for result in results:
                if isinstance(result, Exception):
                    logger.error("fetch_exception", error=str(result))
                    continue

                if result and isinstance(result, list):
                    for item in result:
                        try:
                            await self.output_queue.put(RawNewsItem(**item))
                            total_items += 1
                        except Exception as e:
                            logger.error(
                                "queue_put_error", error=str(e), item=str(item)[:100]
                            )

            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(
                "fetch_cycle_completed",
                elapsed_seconds=f"{elapsed:.2f}",
                total_items=total_items,
            )

            # Wait to maintain 120-second interval
            if elapsed < 120:
                await asyncio.sleep(120 - elapsed)
