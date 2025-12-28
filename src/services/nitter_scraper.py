import asyncio
import aiohttp
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Set
from bs4 import BeautifulSoup
import structlog
import time
from urllib.parse import urljoin

from ..models import RawNewsItem

logger = structlog.get_logger()


class NitterScraper:
    """
    Ultra-lightweight Nitter scraper
    - 50 accounts
    - 3 Nitter instances with round-robin failover
    - Rate limiting (2 seconds per account)
    - Health checking
    - Retry logic with exponential backoff
    """

    INSTANCES = [
        "http://localhost:8081",
        "http://localhost:8082",
        "http://localhost:8083",
    ]

    RATE_LIMIT_DELAY = 2.0  # seconds between requests
    MAX_RETRIES = 3
    RETRY_BACKOFF = 2.0  # exponential backoff multiplier
    SCRAPE_INTERVAL = 60  # seconds between full scrape cycles

    # 50 prediction-market-relevant accounts
    ACCOUNTS = [
        # Tech/Twitter Leadership (5)
        "elonmusk",
        "balajis",
        "paulg",
        "naval",
        "sama",
        # Crypto Founders/VIPs (4)
        "VitalikButerin",
        "cz_binance",
        "michael_saylor",
        "SBF_FTX",
        # Crypto Exchanges (3)
        "coinbase",
        "krakenfx",
        "Binance",
        # Major News (US) (10)
        "WSJ",
        "Reuters",
        "CNBC",
        "Bloomberg",
        "AP",
        "nytimes",
        "BBCWorld",
        "FT",
        "TheEconomist",
        "CNN",
        # Tech News (4)
        "TechCrunch",
        "axios",
        "Politico",
        "verge",
        # Finance Markets (5)
        "WSJmarkets",
        "ReutersBiz",
        "FinancialTimes",
        "MarketWatch",
        "YahooFinance",
        # Crypto News (5)
        "CoinDesk",
        "Cointelegraph",
        "decryptmedia",
        "MessariCrypto",
        "glassnode",
        # Crypto Traders/Analysts (5)
        "jchancerkin",
        "ManganDan",
        "zachxbt",
        "scottmelker",
        "woonomic",
        # Government/Regulatory (3)
        "federalreserve",
        "SEC_News",
        "CFTC",
        # Prediction Markets (2)
        "Polymarket",
        "KalshiMarkets",
        # Additional High-Impact Accounts (4)
        "jack",
        "david_sacks",
        "cdixon",
        "aantonop",
    ]

    def __init__(self, output_queue: asyncio.Queue):
        self.output_queue = output_queue
        self.session: Optional[aiohttp.ClientSession] = None
        self.current_instance = 0
        self.running = False
        self.processed_urls: Set[str] = set()
        self.last_scrape_time: Dict[str, float] = {}

    async def start(self):
        """Start Nitter scraper"""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        self.running = True
        asyncio.create_task(self._scrape_loop())
        asyncio.create_task(self._health_check_loop())
        logger.info(
            "Nitter scraper started",
            instances=len(self.INSTANCES),
            accounts=len(self.ACCOUNTS),
        )

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
        """Scrape user timeline with failover and retry logic"""
        tweets = []
        attempts = 0
        max_attempts = len(self.INSTANCES) * self.MAX_RETRIES

        while attempts < max_attempts:
            instance = self._get_instance()
            url = f"{instance}/{username}"

            try:
                async with self.session.get(url) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        parsed_tweets = self._parse_html(html, username)

                        # Filter out already processed tweets
                        new_tweets = [
                            t
                            for t in parsed_tweets
                            if t["url"] not in self.processed_urls
                        ]

                        # Mark tweets as processed
                        for tweet in new_tweets:
                            self.processed_urls.add(tweet["url"])

                        tweets.extend(new_tweets)
                        return tweets[:limit]

                    elif resp.status == 429:
                        logger.warning(
                            f"Rate limited on {instance} for @{username}",
                            status=resp.status,
                        )
                        await asyncio.sleep(self.RATE_LIMIT_DELAY * 2)
                    else:
                        logger.warning(
                            f"Instance {instance} returned {resp.status} for @{username}"
                        )

            except asyncio.TimeoutError:
                logger.warning(
                    f"Timeout on {instance} for @{username}", attempt=attempts + 1
                )
            except aiohttp.ClientError as e:
                logger.warning(
                    f"Client error on {instance} for @{username}",
                    error=str(e),
                    attempt=attempts + 1,
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error scraping @{username}",
                    error=str(e),
                    instance=instance,
                    attempt=attempts + 1,
                )

            attempts += 1
            # Exponential backoff
            backoff_time = self.RATE_LIMIT_DELAY * (
                self.RETRY_BACKOFF ** min(attempts, 3)
            )
            await asyncio.sleep(backoff_time)

        logger.error(f"Failed to scrape @{username} after {max_attempts} attempts")
        return []

    def _parse_html(self, html: str, username: str) -> List[Dict]:
        """Parse Nitter HTML - supports multiple Nitter class name formats"""
        tweets = []
        soup = BeautifulSoup(html, "html.parser")

        # Try multiple possible tweet container selectors
        tweet_selectors = [
            "div.timeline-item",
            "div.tweet",
            "article.tweet",
            "div[data-tweet-id]",
        ]

        tweet_elements = []
        for selector in tweet_selectors:
            tweet_elements = soup.select(selector)
            if tweet_elements:
                logger.debug(f"Found tweets using selector: {selector}")
                break

        if not tweet_elements:
            logger.debug(f"No tweet elements found for @{username}")
            return tweets

        for tweet in tweet_elements:
            try:
                # Extract text content
                text = self._extract_tweet_text(tweet)
                if not text:
                    continue

                # Extract timestamp
                timestamp = self._extract_timestamp(tweet, username)
                if not timestamp:
                    continue

                # Extract URL
                url = self._extract_url(tweet, username)
                if not url:
                    continue

                # Extract images
                images = self._extract_images(tweet)

                tweet_data = {
                    "source": "nitter",
                    "source_account": f"@{username}",
                    "title": None,
                    "content": text,
                    "url": url,
                    "published_at": timestamp,
                }

                tweets.append(tweet_data)

            except Exception as e:
                logger.debug(f"Failed to parse tweet from @{username}: {e}")
                continue

        logger.info(f"Parsed {len(tweets)} tweets from @{username}")
        return tweets

    def _extract_tweet_text(self, tweet) -> Optional[str]:
        """Extract tweet text content"""
        # Try multiple possible selectors
        text_selectors = [
            "div.tweet-content",
            "div.tweet-text",
            "p.tweet-text",
            'div[class*="content"]',
            'div[class*="text"]',
        ]

        for selector in text_selectors:
            element = tweet.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text[:500]  # Limit length

        # Fallback: try to find any text
        for element in tweet.find_all(text=True):
            parent = element.parent
            if parent and parent.name not in ["script", "style", "link"]:
                text = element.strip()
                if text and len(text) > 20:  # Only substantial text
                    return text[:500]

        return None

    def _extract_timestamp(self, tweet, username: str) -> Optional[str]:
        """Extract tweet timestamp"""
        # Try multiple timestamp selectors
        time_selectors = [
            "span.tweet-date",
            "span.tweet-time",
            'a[class*="time"]',
            "time",
            'span[class*="date"]',
        ]

        for selector in time_selectors:
            time_element = tweet.select_one(selector)
            if time_element:
                # Try title attribute first
                timestamp = time_element.get("title")
                if timestamp:
                    return timestamp

                # Try datetime attribute
                timestamp = time_element.get("datetime")
                if timestamp:
                    return timestamp

                # Fall back to text content
                text = time_element.get_text(strip=True)
                if text:
                    return text

        # Fallback to current time
        logger.debug(
            f"No timestamp found for tweet from @{username}, using current time"
        )
        return datetime.utcnow().strftime("%b %d, %Y · %I:%M %p UTC")

    def _extract_url(self, tweet, username: str) -> Optional[str]:
        """Extract tweet URL"""
        # Try multiple link selectors
        link_selectors = [
            "a.tweet-link",
            'a[class*="permalink"]',
            'a[href*="/status/"]',
            'a[href*="status"]',
        ]

        for selector in link_selectors:
            link_element = tweet.select_one(selector)
            if link_element:
                href = link_element.get("href", "")
                if href:
                    # Convert relative URLs to absolute
                    if href.startswith("/"):
                        return f"https://x.com{href}"
                    elif "twitter.com" in href or "x.com" in href:
                        return href
                    elif href.startswith("http"):
                        return f"https://x.com{href.split('status/')[1] if 'status/' in href else href}"

        # Fallback: construct URL from tweet ID
        tweet_id = tweet.get("data-tweet-id")
        if tweet_id:
            return f"https://x.com/{username}/status/{tweet_id}"

        # Fallback: construct URL with current timestamp
        timestamp = int(time.time())
        return f"https://x.com/{username}/status/{timestamp}"

    def _extract_images(self, tweet) -> List[str]:
        """Extract image URLs from tweet"""
        images = []

        # Try multiple image selectors
        img_selectors = [
            "img.tweet-image",
            'img[class*="media"]',
            'img[class*="image"]',
            'a[href*="photo"] img',
            'div[class*="media"] img',
        ]

        for selector in img_selectors:
            img_elements = tweet.select(selector)
            for img in img_elements:
                src = img.get("src") or img.get("data-src")
                if src and src.startswith(("http://", "https://")):
                    images.append(src)
                elif src and src.startswith("//"):
                    images.append(f"https:{src}")

        return images[:4]  # Limit to 4 images

    async def _scrape_loop(self):
        """Main scraping loop - scrape all accounts every SCRAPE_INTERVAL seconds"""
        while self.running:
            cycle_start = time.time()

            logger.info(
                "Starting scrape cycle",
                accounts=len(self.ACCOUNTS),
                interval_seconds=self.SCRAPE_INTERVAL,
            )

            total_tweets = 0
            successful_accounts = 0
            failed_accounts = 0

            for account in self.ACCOUNTS:
                if not self.running:
                    break

                try:
                    tweets = await self._scrape_user(account, limit=20)
                    total_tweets += len(tweets)
                    successful_accounts += 1

                    logger.info("Scraped account", account=account, tweets=len(tweets))

                    # Push tweets to queue
                    for tweet in tweets:
                        try:
                            await self.output_queue.put(RawNewsItem(**tweet))
                        except Exception as e:
                            logger.error(
                                "Failed to queue tweet",
                                error=str(e),
                                url=tweet.get("url"),
                            )

                except Exception as e:
                    failed_accounts += 1
                    logger.error(
                        "Failed to scrape account", account=account, error=str(e)
                    )

                # Rate limiting
                await asyncio.sleep(self.RATE_LIMIT_DELAY)

            cycle_elapsed = time.time() - cycle_start

            logger.info(
                "Scrape cycle completed",
                tweets_collected=total_tweets,
                successful_accounts=successful_accounts,
                failed_accounts=failed_accounts,
                duration_seconds=round(cycle_elapsed, 2),
            )

            # Wait to maintain interval
            if cycle_elapsed < self.SCRAPE_INTERVAL:
                wait_time = self.SCRAPE_INTERVAL - cycle_elapsed
                logger.debug(f"Waiting {wait_time:.2f}s until next cycle")
                await asyncio.sleep(wait_time)

    async def _health_check_loop(self):
        """Check instance health every 30 seconds"""
        while self.running:
            healthy_count = 0
            unhealthy_instances = []

            for instance in self.INSTANCES:
                try:
                    async with self.session.get(
                        instance, timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            healthy_count += 1
                        else:
                            unhealthy_instances.append(
                                f"{instance} (status: {resp.status})"
                            )
                except asyncio.TimeoutError:
                    unhealthy_instances.append(f"{instance} (timeout)")
                except Exception as e:
                    unhealthy_instances.append(f"{instance} ({str(e)})")

            logger.info(
                "Nitter health check",
                healthy=f"{healthy_count}/{len(self.INSTANCES)}",
                unhealthy=unhealthy_instances if unhealthy_instances else None,
            )

            await asyncio.sleep(30)

    async def manual_scrape(self, username: str, limit: int = 20) -> List[Dict]:
        """Manually scrape a specific user (for testing)"""
        logger.info(f"Manual scrape requested for @{username}")

        # Ensure session is initialized
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )

        try:
            tweets = await self._scrape_user(username, limit=limit)
            logger.info(f"Manual scrape completed: {len(tweets)} tweets found")
            return tweets
        finally:
            # Close session if it was created just for this scrape
            if not self.running and self.session:
                await self.session.close()
                self.session = None
