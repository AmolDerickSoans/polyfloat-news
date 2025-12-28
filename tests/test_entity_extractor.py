import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.entity_extractor import EntityExtractor
from models import NewsItem, CategoryType


def test_people_extraction():
    print("\n=== Testing People Extraction ===")
    extractor = EntityExtractor()

    test_cases = [
        {
            "text": "President Biden announced new policies today",
            "expected_any": ["Biden", "President Biden"],
        },
        {
            "text": "Elon Musk announced new Tesla features",
            "expected_any": ["Elon Musk", "Musk"],
        },
        {
            "text": "Jerome Powell discussed interest rates",
            "expected_any": ["Jerome Powell", "Powell"],
        },
        {
            "text": "Vitalik Buterin spoke about Ethereum upgrades",
            "expected_any": ["Vitalik Buterin", "Vitalik"],
        },
        {
            "text": "Trump and Harris debate tonight",
            "expected_any": ["Trump", "Harris", "Donald Trump", "Kamala Harris"],
        },
        {
            "text": "Sam Altman's OpenAI releases new model",
            "expected_any": ["Sam Altman", "Altman"],
        },
    ]

    for i, test in enumerate(test_cases, 1):
        result = extractor.extract_people(test["text"])
        print(f"\nTest {i}: {test['text']}")
        print(f"  Expected any of: {test['expected_any']}")
        print(f"  Got: {result}")
        if any(exp in result for exp in test['expected_any']):
            print("  ✓ PASSED")
        else:
            print("  ✗ FAILED")


def test_ticker_extraction():
    print("\n=== Testing Ticker Extraction ===")
    extractor = EntityExtractor()

    test_cases = [
        {
            "text": "Bitcoin $BTC reaches new highs",
            "expected": ["BTC"],
        },
        {
            "text": "$ETH $SOL $ADA all showing gains",
            "expected": ["ADA", "ETH", "SOL"],
        },
        {
            "text": "Stocks AAPL MSFT NVDA rally",
            "expected": ["AAPL", "MSFT", "NVDA"],
        },
        {
            "text": "$TSLA shares surge on earnings",
            "expected": ["TSLA"],
        },
        {
            "text": "Crypto market: $DOGE $SHIB meme coins pumping",
            "expected": ["DOGE", "SHIB"],
        },
    ]

    for i, test in enumerate(test_cases, 1):
        result = extractor.extract_tickers(test["text"])
        print(f"\nTest {i}: {test['text']}")
        print(f"  Expected: {sorted(test['expected'])}")
        print(f"  Got: {result}")
        if set(result) == set(test['expected']):
            print("  ✓ PASSED")
        else:
            print("  ✗ FAILED")


def test_keyword_extraction():
    print("\n=== Testing Keyword Extraction ===")
    extractor = EntityExtractor()

    test_cases = [
        {
            "text": "Federal Reserve raises interest rates to combat inflation",
            "expected": ["inflation", "interest rate", "federal reserve", "fed"],
        },
        {
            "text": "Bitcoin and Ethereum lead crypto market rally",
            "expected": ["bitcoin", "ethereum", "crypto", "market"],
        },
        {
            "text": "President Biden campaigns for re-election",
            "expected": ["election", "campaign", "president"],
        },
    ]

    for i, test in enumerate(test_cases, 1):
        result = extractor.extract_keywords(test["text"])
        print(f"\nTest {i}: {test['text']}")
        print(f"  Expected (subset): {test['expected']}")
        print(f"  Got: {result[:10]}")
        found = any(kw in result for kw in test['expected'])
        if found:
            print("  ✓ PASSED")
        else:
            print("  ✗ FAILED")


def test_category_classification():
    print("\n=== Testing Category Classification ===")
    extractor = EntityExtractor()

    test_cases = [
        {
            "text": "President Biden campaigns for re-election in 2024",
            "expected": CategoryType.POLITICS,
        },
        {
            "text": "Bitcoin and Ethereum surge as crypto market rallies",
            "expected": CategoryType.CRYPTO,
        },
        {
            "text": "Federal Reserve raises interest rates to fight inflation",
            "expected": CategoryType.ECONOMICS,
        },
        {
            "text": "Super Bowl game highlights from Sunday",
            "expected": CategoryType.SPORTS,
        },
        {
            "text": "Random news story about weather",
            "expected": CategoryType.OTHER,
        },
    ]

    for i, test in enumerate(test_cases, 1):
        result = extractor.classify_category(test["text"])
        print(f"\nTest {i}: {test['text']}")
        print(f"  Expected: {test['expected']}")
        print(f"  Got: {result}")
        if result == test['expected']:
            print("  ✓ PASSED")
        else:
            print("  ✗ FAILED")


def test_full_entity_extraction():
    print("\n=== Testing Full Entity Extraction ===")
    extractor = EntityExtractor()

    news_item = NewsItem(
        id="test-1",
        source="nitter",
        source_account="crypto_news",
        title="Bitcoin surges as Fed announces rate decision",
        content="Bitcoin $BTC and Ethereum $ETH surge following Federal Reserve Chair Jerome Powell's announcement on interest rates. The crypto market shows bullish sentiment.",
        url="https://example.com/news/1",
        published_at=1703424000.0,
    )

    result = extractor.extract_entities(news_item)

    print("\nInput News Item:")
    print(f"  Title: {news_item.title}")
    print(f"  Content: {news_item.content[:100]}...")

    print("\nExtracted Entities:")
    print(f"  People: {result.people}")
    print(f"  Tickers: {result.tickers}")
    print(f"  Category: {result.category}")
    print(f"  Tags: {result.tags}")
    print(f"  Prediction Markets: {result.prediction_markets}")

    print("\nValidation:")
    assert "Jerome Powell" in result.people, "Failed to extract person"
    assert "BTC" in result.tickers, "Failed to extract BTC ticker"
    assert "ETH" in result.tickers, "Failed to extract ETH ticker"
    assert result.category in [CategoryType.CRYPTO, CategoryType.ECONOMICS], "Category classification failed"
    print("  ✓ All validations passed!")


def test_lists_summary():
    print("\n=== Entity Lists Summary ===")
    extractor = EntityExtractor()

    print(f"\nTotal People Tracked: {len(extractor.all_people)}")
    print(f"  - Politicians: {len(extractor.politicians)}")
    print(f"  - Tech Leaders: {len(extractor.tech_leaders)}")
    print(f"  - Crypto Leaders: {len(extractor.crypto_leaders)}")
    print(f"  - Finance Leaders: {len(extractor.finance_leaders)}")

    print(f"\nTotal Tickers Tracked: {len(extractor.all_tickers)}")
    print(f"  - Crypto Tickers: {len(extractor.crypto_tickers)}")
    print(f"  - Stock Tickers: {len(extractor.stock_tickers)}")

    print(f"\nKeywords by Category:")
    for category, keywords in extractor.category_keywords.items():
        print(f"  - {category}: {len(keywords)} keywords")

    print("\nSample People:")
    print(f"  Politicians: {list(extractor.politicians)[:5]}")
    print(f"  Tech Leaders: {list(extractor.tech_leaders)[:5]}")
    print(f"  Crypto Leaders: {list(extractor.crypto_leaders)[:5]}")
    print(f"  Finance Leaders: {list(extractor.finance_leaders)[:5]}")

    print("\nSample Tickers:")
    print(f"  Crypto: {sorted(list(extractor.crypto_tickers))[:10]}")
    print(f"  Stocks: {sorted(list(extractor.stock_tickers))[:10]}")

    print("\nSample Keywords:")
    for category, keywords in extractor.category_keywords.items():
        print(f"  {category}: {sorted(list(keywords))[:5]}")


def main():
    print("=" * 80)
    print("POLYFLOAT NEWS - ENTITY EXTRACTOR TESTS")
    print("=" * 80)

    try:
        test_people_extraction()
        test_ticker_extraction()
        test_keyword_extraction()
        test_category_classification()
        test_full_entity_extraction()
        test_lists_summary()

        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETED")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
