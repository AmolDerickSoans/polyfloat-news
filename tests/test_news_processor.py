import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import RawNewsItem, NewsItem, SourceType
from services.news_processor import NewsProcessor

import structlog

structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


async def test_news_processor():
    """Test the news processor functionality"""
    input_queue = asyncio.Queue()
    websocket_queue = asyncio.Queue()

    processor = NewsProcessor(
        input_queue=input_queue,
        websocket_queue=websocket_queue,
        db_path=":memory:"
    )

    await processor.start()

    try:
        logger.info("=== Test 1: Deduplication ===")

        raw_item_1 = RawNewsItem(
            source='rss',
            source_account='Reuters',
            title='Breaking: Fed announces rate decision',
            content='The Federal Reserve has announced its latest interest rate decision...',
            url='https://reuters.com/fed-rate-decision',
            published_at=datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        )

        raw_item_2 = RawNewsItem(
            source='rss',
            source_account='Reuters',
            title='Breaking: Fed announces rate decision',
            content='The Federal Reserve has announced its latest interest rate decision...',
            url='https://reuters.com/fed-rate-decision',
            published_at=datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        )

        await input_queue.put(raw_item_1)
        await asyncio.sleep(0.5)

        await input_queue.put(raw_item_2)
        await asyncio.sleep(0.5)

        cursor = await processor.db_conn.execute(
            "SELECT COUNT(*) FROM news WHERE url = ?",
            ('https://reuters.com/fed-rate-decision',)
        )
        count = (await cursor.fetchone())[0]

        assert count == 1, f"Expected 1 item, got {count}"
        logger.info("✓ Deduplication test passed", count=count)

        logger.info("=== Test 2: Impact Scoring ===")

        high_impact_item = RawNewsItem(
            source='rss',
            source_account='Reuters',
            title='BREAKING: Fed Chair Jerome Powell announces emergency rate cut',
            content='Federal Reserve Chairman Jerome Powell announced an emergency interest rate cut today...',
            url='https://reuters.com/emergency-fed-cut',
            published_at=datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        )

        await input_queue.put(high_impact_item)
        await asyncio.sleep(0.5)

        cursor = await processor.db_conn.execute(
            "SELECT impact_score FROM news WHERE url = ?",
            ('https://reuters.com/emergency-fed-cut',)
        )
        result = await cursor.fetchone()
        impact_score = result[0] if result else 0

        assert impact_score > 7.0, f"Expected high impact score, got {impact_score}"
        logger.info("✓ High impact scoring test passed", score=impact_score)

        logger.info("=== Test 3: Entity Extraction ===")

        crypto_item = RawNewsItem(
            source='nitter',
            source_account='elonmusk',
            title=None,
            content='Bitcoin $BTC and Ethereum $ETH are showing strong momentum today as markets react to Fed decisions',
            url='https://x.com/elonmusk/status/123456',
            published_at=datetime.now().strftime('%b %d, %Y · %I:%M %p UTC')
        )

        await input_queue.put(crypto_item)
        await asyncio.sleep(0.5)

        cursor = await processor.db_conn.execute(
            "SELECT tickers, category FROM news WHERE url = ?",
            ('https://x.com/elonmusk/status/123456',)
        )
        result = await cursor.fetchone()
        tickers_json, category = result

        import json
        tickers = json.loads(tickers_json)

        assert 'BTC' in tickers or 'ETH' in tickers, f"Expected tickers, got {tickers}"
        assert category == 'crypto', f"Expected crypto category, got {category}"
        logger.info("✓ Entity extraction test passed", tickers=tickers, category=category)

        logger.info("=== Test 4: WebSocket Publishing ===")

        while not websocket_queue.empty():
            websocket_queue.get_nowait()

        test_item = RawNewsItem(
            source='rss',
            source_account='CNBC',
            title='Market Update: Stocks rally on economic data',
            content='Major stock indices are rallying today...',
            url='https://cnbc.com/market-update',
            published_at=datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        )

        await input_queue.put(test_item)
        await asyncio.sleep(0.5)

        websocket_item = await websocket_queue.get()
        logger.info("WebSocket item received", item=websocket_item)

        assert websocket_item['url'] == 'https://cnbc.com/market-update', f"Expected https://cnbc.com/market-update, got {websocket_item.get('url')}"
        assert 'impact_score' in websocket_item
        logger.info("✓ WebSocket publishing test passed", url=websocket_item['url'])

        logger.info("=== Test 5: Low Impact Scoring ===")

        old_item = RawNewsItem(
            source='nitter',
            source_account='randomuser',
            title=None,
            content='Just had a nice lunch today',
            url='https://x.com/randomuser/status/789012',
            published_at=(datetime.now().replace(day=datetime.now().day - 3)).strftime('%b %d, %Y · %I:%M %p UTC')
        )

        await input_queue.put(old_item)
        await asyncio.sleep(0.5)

        cursor = await processor.db_conn.execute(
            "SELECT impact_score FROM news WHERE url = ?",
            ('https://x.com/randomuser/status/789012',)
        )
        result = await cursor.fetchone()
        impact_score = result[0] if result else 0

        assert impact_score < 5.0, f"Expected low impact score, got {impact_score}"
        logger.info("✓ Low impact scoring test passed", score=impact_score)

        logger.info("=== Test 6: Malformed Item Handling ===")

        malformed_item = RawNewsItem(
            source='rss',
            source_account=None,
            title='',
            content='',
            url='https://example.com/empty',
            published_at='invalid-date'
        )

        await input_queue.put(malformed_item)
        await asyncio.sleep(0.5)

        cursor = await processor.db_conn.execute(
            "SELECT COUNT(*) FROM news WHERE url = ?",
            ('https://example.com/empty',)
        )
        count = (await cursor.fetchone())[0]

        logger.info("✓ Malformed item handling test passed", count=count)

        logger.info("=== All Tests Passed ===")

        final_cursor = await processor.db_conn.execute("SELECT COUNT(*) FROM news")
        total_items = (await final_cursor.fetchone())[0]
        logger.info("Total news items in database", count=total_items)

    finally:
        await processor.stop()


async def main():
    try:
        await test_news_processor()
        print("\n✅ All tests passed successfully!")
        return 0
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
