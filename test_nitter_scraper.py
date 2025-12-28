#!/usr/bin/env python3
"""
Test script for Nitter scraper
"""
import asyncio
import sys
import os
import aiohttp

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.nitter_scraper import NitterScraper
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def test_manual_scrape():
    """Test manual scraping of a few accounts"""
    
    # Create queue for output
    queue = asyncio.Queue(maxsize=100)
    
    # Create scraper
    scraper = NitterScraper(queue)
    
    logger.info("Starting test scrape (checking if Nitter instances are available)")
    
    # First check if instances are available
    instance_available = False
    for instance in NitterScraper.INSTANCES:
        try:
            if not scraper.session:
                scraper.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=5)
                )
            
            async with scraper.session.get(instance, timeout=5) as resp:
                if resp.status == 200:
                    logger.info(f"Nitter instance {instance} is available")
                    instance_available = True
                    break
        except:
            continue
    
    if not instance_available:
        logger.warning("No Nitter instances available - skipping manual scrape test")
        logger.warning("Start Nitter instances with: docker-compose up -d")
        if scraper.session:
            await scraper.session.close()
        return
    
    # Test a few accounts
    test_accounts = ["elonmusk", "VitalikButerin", "Polymarket"]
    
    for account in test_accounts:
        try:
            logger.info(f"Testing account: @{account}")
            tweets = await scraper.manual_scrape(account, limit=5)
            
            logger.info(
                f"Scraped @{account}",
                tweets_found=len(tweets)
            )
            
            # Print sample tweets
            for i, tweet in enumerate(tweets[:2]):
                logger.info(
                    f"Tweet {i+1} from @{account}",
                    content=tweet.get('content', '')[:100] + '...',
                    url=tweet.get('url', 'N/A'),
                    timestamp=tweet.get('published_at', 'N/A')
                )
            
            # Small delay between accounts
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Failed to scrape @{account}", error=str(e))
    
    logger.info("Test scrape completed")
    
    # Check queue contents
    queue_size = queue.qsize()
    logger.info(f"Queue contains {queue_size} items")
    
    # Peek at a few items
    for _ in range(min(5, queue_size)):
        try:
            item = await asyncio.wait_for(queue.get(), timeout=0.1)
            logger.info(
                "Queued item",
                source=item.source,
                account=item.source_account,
                content_preview=item.content[:80] + '...',
                url=item.url
            )
        except asyncio.TimeoutError:
            break


async def test_html_parsing():
    """Test HTML parsing with mock data"""
    logger.info("Testing HTML parsing")
    
    queue = asyncio.Queue(maxsize=100)
    scraper = NitterScraper(queue)
    
    # Mock HTML with different Nitter formats
    mock_html_samples = [
        # Format 1: Standard Nitter
        """
        <div class="timeline-item">
            <div class="tweet-content">
                This is a test tweet
            </div>
            <span class="tweet-date" title="Dec 28, 2025 · 8:00 PM UTC">2h</span>
            <a class="tweet-link" href="/elonmusk/status/1234567890">View</a>
        </div>
        """,
        
        # Format 2: Alternative classes
        """
        <div class="tweet" data-tweet-id="1234567891">
            <p class="tweet-text">Another test tweet</p>
            <time datetime="2025-12-28T20:00:00Z">2h</time>
            <a href="/status/1234567891">Link</a>
        </div>
        """,
    ]
    
    for i, html in enumerate(mock_html_samples, 1):
        tweets = scraper._parse_html(html, "testuser")
        logger.info(
            f"Parsed mock HTML sample {i}",
            tweets_found=len(tweets)
        )
        
        for tweet in tweets:
            logger.info(
                f"Tweet from sample {i}",
                content=tweet.get('content'),
                url=tweet.get('url'),
                timestamp=tweet.get('published_at')
            )


async def test_account_list():
    """Test the account list"""
    logger.info("Testing account list")
    
    accounts = NitterScraper.ACCOUNTS
    logger.info(
        "Account list",
        total=len(accounts),
        accounts=accounts
    )
    
    # Check for duplicates
    unique_accounts = set(accounts)
    if len(accounts) != len(unique_accounts):
        logger.warning(
            "Duplicate accounts found",
            total=len(accounts),
            unique=len(unique_accounts),
            duplicates=set([a for a in accounts if accounts.count(a) > 1])
        )
    else:
        logger.info("No duplicate accounts found")


async def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("Starting Nitter Scraper Tests")
    logger.info("=" * 60)
    
    # Test 1: Account list
    logger.info("\n" + "=" * 60)
    logger.info("Test 1: Account List")
    logger.info("=" * 60)
    await test_account_list()
    
    # Test 2: HTML parsing
    logger.info("\n" + "=" * 60)
    logger.info("Test 2: HTML Parsing")
    logger.info("=" * 60)
    await test_html_parsing()
    
    # Test 3: Manual scrape (only if Nitter instances are running)
    logger.info("\n" + "=" * 60)
    logger.info("Test 3: Manual Scrape (requires Nitter instances)")
    logger.info("=" * 60)
    
    try:
        await test_manual_scrape()
    except Exception as e:
        logger.error(
            "Manual scrape failed (this is expected if Nitter instances are not running)",
            error=str(e)
        )
    
    logger.info("\n" + "=" * 60)
    logger.info("All tests completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
