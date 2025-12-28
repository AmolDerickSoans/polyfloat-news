import asyncio
import aiohttp
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import structlog

from models import RawNewsItem

logger = structlog.get_logger()


class NitterScraper:
    """
    Ultra-lightweight Nitter scraper
    - 50 accounts
    - 3 Nitter instances with round-robin failover
    - Rate limiting
    - Health checking
    """

    INSTANCES = [
        "http://localhost:8081",
        "http://localhost:8082",
        "http://localhost:8083"
    ]

    # 50 prediction-market-relevant accounts
    ACCOUNTS = [
        # Politics
        "trumpwarroom", "POTUS", "WhiteHouse",
        "PressSec", "VP", "FBI",

        # Crypto
        "elonmusk", "michael_saylor", "balajis",
        "VitalikButerin", "cb_doge", "saylor",

        # Finance/Markets
        "WSJmarkets", "ReutersBiz", "Bloomberg",
        "CNBC", "FinancialTimes",

        # Prediction Markets
        "Polymarket", "KalshiMarkets",

        # More accounts to reach 50
        "NBCNews", "CNN", "FoxNews",
        "business", "nytimesbusiness", "economist",
        "federalreserve", "SEC_News", "CFTC",
        "CoinDesk", "Cointelegraph", "decryptmedia",
        "MessariCrypto", "glassnode", "intotheblock",
        "jchancerkin", "ManganDan", "zachxbt",
        "trader_xavis", "Byzgeneral", "Tier10k",
        "scottmelker", "woonomic", "DocumentingBTC",
        "AP", "AP_Politics", "BBCNews",
        "CNBCi", "CNBCNOW", "TheStreet",
        "MarketWatch", "YahooFinance", "IBDinvestors"
    ]

    def __init__(self, output_queue: asyncio.Queue):
        self.output_queue = output_queue
        self.session = None
        self.current_instance = 0
        self.running = False

    async def start(self):
        """Start Nitter scraper"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
        self.running = True
        asyncio.create_task(self._scrape_loop())
        asyncio.create_task(self._health_check_loop())
        logger.info("Nitter scraper started")

    async def stop(self):
        """Stop Nitter scraper"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("Nitter scraper stopped")

    def _get_instance(self) -> str:
        """Round-robin instance selection"""
        instance = self.INSTANCES[self.current_instance]
        self.current_instance = (self.current_instance + 1) % len(self.INSTANCES)
        return instance

    async def _scrape_user(self, username: str, limit: int = 20) -> List[Dict]:
        """Scrape user timeline with failover"""
        attempts = 0
        max_attempts = len(self.INSTANCES)

        while attempts < max_attempts:
            instance = self._get_instance()
            url = f"{instance}/{username}"

            try:
                async with self.session.get(url) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        tweets = self._parse_html(html, username)
                        return tweets[:limit]
            except Exception as e:
                logger.warning(f"Instance {instance} failed for @{username}: {e}")
                attempts += 1
                await asyncio.sleep(1)

        return []

    def _parse_html(self, html: str, username: str) -> List[Dict]:
        """Parse Nitter HTML"""
        tweets = []
        soup = BeautifulSoup(html, 'html.parser')

        # Look for tweet items
        for tweet in soup.find_all('div', class_='timeline-item'):
            try:
                # Extract text content
                content_div = tweet.find('div', class_='tweet-content')
                if not content_div:
                    continue
                text = content_div.get_text(strip=True)

                # Extract timestamp
                time_span = tweet.find('span', class_='tweet-date')
                if not time_span:
                    continue

                # Try to get timestamp from title attribute
                published_at = time_span.get('title', '')
                if not published_at:
                    published_at = datetime.now().strftime('%b %d, %Y · %I:%M %p UTC')

                # Extract link
                link_tag = tweet.find('a', class_='tweet-link')
                if not link_tag:
                    continue
                url = link_tag.get('href', '')
                if url and url.startswith('/'):
                    url = f"https://x.com{url}"

                tweets.append({
                    'source': 'nitter',
                    'source_account': f'@{username}',
                    'content': text,
                    'url': url,
                    'published_at': published_at
                })

            except Exception as e:
                logger.debug(f"Failed to parse tweet: {e}")
                continue

        return tweets

    async def _scrape_loop(self):
        """Main scraping loop - scrape all accounts every 60 seconds"""
        while self.running:
            start_time = asyncio.get_event_loop().time()

            logger.info(f"Starting scrape cycle for {len(self.ACCOUNTS)} accounts")

            for account in self.ACCOUNTS:
                if not self.running:
                    break

                try:
                    tweets = await self._scrape_user(account, limit=20)
                    logger.info(f"Scraped {len(tweets)} tweets from @{account}")

                    for tweet in tweets:
                        await self.output_queue.put(RawNewsItem(**tweet))

                except Exception as e:
                    logger.error(f"Failed to scrape @{account}: {e}")

                # Rate limiting - 1.5 seconds between accounts
                await asyncio.sleep(1.5)

            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(f"Scrape cycle completed in {elapsed:.2f}s")

            # Wait to maintain 60-second interval
            if elapsed < 60:
                await asyncio.sleep(60 - elapsed)

    async def _health_check_loop(self):
        """Check instance health every 30 seconds"""
        while self.running:
            healthy_count = 0

            for instance in self.INSTANCES:
                try:
                    async with self.session.get(instance, timeout=5) as resp:
                        if resp.status == 200:
                            healthy_count += 1
                        else:
                            logger.warning(f"Instance {instance} unhealthy (status: {resp.status})")
                except Exception as e:
                    logger.warning(f"Instance {instance} unreachable: {e}")

            logger.info(f"Nitter health: {healthy_count}/{len(self.INSTANCES)} instances healthy")
            await asyncio.sleep(30)
