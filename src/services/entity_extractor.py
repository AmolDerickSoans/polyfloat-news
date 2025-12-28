import re
import unicodedata
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import Counter

import structlog

from ..models import CategoryType


logger = structlog.get_logger(__name__)


class EntityExtractor:
    """
    Lightweight entity extraction without ML
    - Uses regex patterns and keyword matching
    - Extracts tickers, people, categories, tags
    - No dependencies on external ML models
    """

    def __init__(self):
        self._initialize_people()
        self._initialize_tickers()
        self._initialize_keywords()
        self.ticker_pattern = re.compile(r"\$([A-Z]{1,10})\b")
        logger.info(
            "entity_extractor_initialized",
            people_count=len(self.all_people),
            tickers_count=len(self.all_tickers),
            keywords_count=sum(len(kws) for kws in self.category_keywords.values()),
        )

    def _initialize_people(self) -> None:
        self.politicians = [
            "joe biden",
            "biden",
            "president biden",
            "donald trump",
            "trump",
            "president trump",
            "kamala harris",
            "harris",
            "barack obama",
            "obama",
            "president obama",
            "mike pence",
            "ron desantis",
            "desantis",
            "nikki haley",
            "haley",
            "tim walz",
            "walz",
            "j.d. vance",
            "vance",
            "nancy pelosi",
            "pelosi",
            "chuck schumer",
            "schumer",
            "mitch mcconnell",
            "mcconnell",
            "kevin mccarthy",
            "mccarthy",
            "hakeem jeffries",
            "jeffries",
            "elizabeth warren",
            "warren",
            "bernie sanders",
            "sanders",
            "aoc",
            "alexandria ocasio-cortez",
            "ted cruz",
            "cruz",
            "josh hawley",
            "hawley",
            "lindsey graham",
            "graham",
            "mitt romney",
            "romney",
            "christie noem",
            "greg abbott",
            "gavin newsom",
            "gretchen whitmer",
            "mike pompeo",
            "pompeo",
            "chris christie",
            "robert kennedy",
            "rfk",
            "jimmy carter",
            "carter",
            "bill clinton",
            "clinton",
            "hillary clinton",
            "george bush",
            "bush",
            "dick cheney",
            "vladimir putin",
            "putin",
            "xi jinping",
            "kim jong un",
            "emanuel macron",
            "olaf scholz",
            "boris johnson",
            "rishisunak",
            "benjamin netanyahu",
            "volodymyr zelenskyy",
            "jair bolsonaro",
            "justin trudeau",
            "jens stoltenberg",
        ]

        self.tech_leaders = [
            "elon musk",
            "musk",
            "mark zuckerberg",
            "zuckerberg",
            "sam altman",
            "altman",
            "satya nadella",
            "sundar pichai",
            "tim cook",
            "jeff bezos",
            "bezos",
            "andy jassy",
            "jen-hsun huang",
            "jensen huang",
            "mark benioff",
            "david soloff",
            "sheryl sandberg",
            "bill gates",
            "gates",
            "steve jobs",
            "steve ballmer",
            "jack dorsey",
            "daniel ek",
            "evan spiegel",
            "patrick collision",
            "john collision",
            "reed hastings",
            "brian chesky",
            "dara khosrowshahi",
            "doug mcfillon",
            "jamie dimon",
            "dimon",
            "david solomon",
            "larry fink",
            "fink",
            "warren buffett",
            "buffett",
            "charlie munger",
        ]

        self.crypto_leaders = [
            "vitalik buterin",
            "vitalik",
            "cz",
            "changpeng zhao",
            "sbf",
            "sam bankman-fried",
            "andrew forrest",
            "dan larimer",
            "charles hoskinson",
            "roger ver",
            "barry silbert",
            "mike novogratz",
            "tyler winklevoss",
            "cameron winklevoss",
            "brian armstrong",
            "fred ehrsam",
            "hayden adams",
            "stani kulechov",
            "kain warwick",
            "defi",
            "andre cronje",
            "satoshi nakamoto",
            "satoshi",
            "hal finney",
            "nick szabo",
            "adam back",
            "pieter wuille",
            "gregory maxwell",
            "luke dashjr",
            "gavin andresen",
        ]

        self.finance_leaders = [
            "jerome powell",
            "powell",
            "janet yellen",
            "yellen",
            "christine lagarde",
            "jim bullard",
            "larry summers",
            "gary gensler",
            "michael barr",
            "neel kashkari",
            "mary daly",
            "lael brainard",
            "phil jefferson",
            "john williams",
            "paul krugman",
            "ken french",
            "eugene fama",
            "robert shiller",
            "nouriel roubini",
            "peter schiff",
            "jim grant",
            "stan druckenmiller",
            "ray dalio",
            "bill gross",
            "jeff gundlach",
        ]

        self.all_people = set(
            self.politicians
            + self.tech_leaders
            + self.crypto_leaders
            + self.finance_leaders
        )

    def _initialize_tickers(self) -> None:
        self.crypto_tickers = {
            "BTC",
            "ETH",
            "BNB",
            "XRP",
            "ADA",
            "DOGE",
            "SOL",
            "DOT",
            "MATIC",
            "SHIB",
            "TRX",
            "AVAX",
            "LTC",
            "LINK",
            "UNI",
            "ATOM",
            "XMR",
            "ETC",
            "XLM",
            "ALGO",
            "VET",
            "FIL",
            "NEAR",
            "AAVE",
            "APE",
            "MKR",
            "COMP",
            "GRT",
            "THETA",
            "SAND",
            "MANA",
            "AXS",
            "CRV",
            "CVX",
            "GMX",
            "RUNE",
            "LDO",
            "AR",
            "QNT",
            "INJ",
            "KAVA",
            "ROSE",
            "STX",
            "ICP",
            "HBAR",
            "NEO",
            "EGLD",
            "EOS",
            "BTG",
            "FTM",
            "CELO",
            "KCS",
            "CAKE",
            "BCH",
            "BSV",
            "XEM",
            "ZEC",
            "DCR",
            "DASH",
            "NEXO",
            "WAVES",
            "SCRT",
            "IOST",
            "RVN",
            "ONT",
            "GNO",
            "LRC",
            "ZRX",
            "ENJ",
            "KSM",
            "MASK",
            "CELR",
            "BAKE",
            "1INCH",
            "CHR",
            "BAND",
            "ANKR",
            "SKL",
            "REP",
            "SNX",
            "YFI",
            "SRM",
            "JUP",
            "ORCA",
            "RAY",
            "BONK",
            "WIF",
            "PEPE",
            "FLOKI",
            "MOG",
            "WEN",
            "MEME",
            "COQ",
        }

        self.stock_tickers = {
            "AAPL",
            "MSFT",
            "GOOGL",
            "GOOG",
            "AMZN",
            "NVDA",
            "META",
            "TSLA",
            "BRK.B",
            "JPM",
            "V",
            "JNJ",
            "WMT",
            "PG",
            "MA",
            "UNH",
            "HD",
            "BAC",
            "XOM",
            "CVX",
            "KO",
            "PEP",
            "MRK",
            "LLY",
            "ABBV",
            "PFE",
            "TMO",
            "AVGO",
            "COST",
            "ORCL",
            "CSCO",
            "ADBE",
            "CRM",
            "NFLX",
            "INTC",
            "AMD",
            "ABT",
            "QCOM",
            "ACN",
            "DHR",
            "LIN",
            "IBM",
            "MCD",
            "NKE",
            "TXN",
            "NOW",
            "UPS",
            "CAT",
            "INTU",
            "BLK",
            "GE",
            "PLD",
            "HON",
            "LMT",
            "SPGI",
            "AMGN",
            "SCHW",
            "CB",
            "AXP",
            "C",
            "GS",
            "MS",
            "VRTX",
            "SYK",
            "CI",
            "ISRG",
            "MDT",
            "AMT",
            "REGN",
            "EL",
            "GILD",
            "MU",
            "ADP",
            "BKNG",
            "MMC",
            "PGR",
            "T",
            "LHX",
            "AON",
            "CME",
            "PANW",
            "ADI",
            "APD",
            "EQIX",
            "EW",
            "IDXX",
            "ICE",
            "ILMN",
        }

        self.all_tickers = self.crypto_tickers | self.stock_tickers

    def _initialize_keywords(self) -> None:
        self.category_keywords: Dict[CategoryType, Set[str]] = {
            CategoryType.POLITICS: {
                "election",
                "vote",
                "voting",
                "ballot",
                "poll",
                "candidate",
                "congress",
                "senate",
                "house",
                "representative",
                "senator",
                "president",
                "governor",
                "mayor",
                "legislation",
                "bill",
                "law",
                "democrat",
                "republican",
                "campaign",
                "debate",
                "primary",
                "administration",
                "policy",
                "government",
                "impeachment",
                "scandal",
                "rally",
                "convention",
                "caucus",
                "referendum",
                "midterm",
            },
            CategoryType.CRYPTO: {
                "bitcoin",
                "ethereum",
                "crypto",
                "cryptocurrency",
                "blockchain",
                "defi",
                "nft",
                "web3",
                "token",
                "coin",
                "altcoin",
                "wallet",
                "exchange",
                "binance",
                "coinbase",
                "kraken",
                "mining",
                "hash",
                "fork",
                "airdrop",
                "whale",
                "bull",
                "bear",
                "bullish",
                "bearish",
                "hodl",
                "gas",
                "fees",
                "transaction",
                "block",
                "smart contract",
                "dapp",
                "dao",
                "stablecoin",
                "usdt",
                "usdc",
                "decentralized",
                "metamask",
                "ledger",
                "trezor",
                "private key",
                "cold storage",
            },
            CategoryType.ECONOMICS: {
                "inflation",
                "recession",
                "gdp",
                "interest rate",
                "federal reserve",
                "fed",
                "economy",
                "economic",
                "market",
                "markets",
                "stock",
                "bond",
                "treasury",
                "yield",
                "rate hike",
                "cut",
                "monetary policy",
                "fiscal",
                "stimulus",
                "unemployment",
                "jobs",
                "employment",
                "wages",
                "consumer price index",
                "cpi",
                "pce",
                "growth",
                "contraction",
                "debt",
                "deficit",
                "surplus",
                "tax",
                "trade",
                "exports",
                "imports",
                "supply chain",
                "consumer",
                "spending",
                "retail",
                "durable goods",
            },
            CategoryType.SPORTS: {
                "nfl",
                "nba",
                "mlb",
                "nhl",
                "soccer",
                "football",
                "basketball",
                "baseball",
                "hockey",
                "tennis",
                "golf",
                "olympics",
                "world cup",
                "super bowl",
                "world series",
                "playoffs",
                "championship",
                "finals",
                "athlete",
                "player",
                "team",
                "coach",
                "manager",
                "score",
                "win",
                "loss",
                "game",
                "match",
                "tournament",
                "league",
                "season",
                "draft",
                "trade",
                "free agent",
                "injury",
                "suspension",
                "contract",
            },
            CategoryType.OTHER: {
                "news",
                "update",
                "breaking",
                "report",
                "article",
                "story",
                "announced",
                "released",
                "launched",
                "happened",
                "today",
            },
        }

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        text = (
            unicodedata.normalize("NFKD", text)
            .encode("ASCII", "ignore")
            .decode("ASCII")
        )
        return text.lower().strip()

    def extract_entities(self, news_item) -> Any:
        """Extract all entities from a news item"""
        try:
            text = f"{news_item.title or ''} {news_item.content}"

            news_item.tickers = self.extract_tickers(text)
            news_item.people = self.extract_people(text)
            news_item.category = self.classify_category(text)
            news_item.tags = self.extract_tags(text)
            news_item.prediction_markets = self._extract_prediction_markets(
                text, news_item
            )

            logger.debug(
                "entities_extracted",
                id=news_item.id,
                tickers=news_item.tickers,
                people=news_item.people,
                category=news_item.category,
            )

        except Exception as e:
            logger.error("entity_extraction_failed", id=news_item.id, error=str(e))

        return news_item

    def extract_people(self, text: str) -> List[str]:
        if not text:
            return []

        try:
            normalized_text = self._normalize_text(text)
            found_people = []

            for person in self.all_people:
                if person in normalized_text:
                    found_people.append(person.title())

            if found_people:
                logger.debug(
                    "people_extracted", count=len(found_people), people=found_people
                )

            return list(set(found_people))

        except Exception as e:
            logger.error("people_extraction_failed", error=str(e))
            return []

    def extract_tickers(self, text: str) -> List[str]:
        if not text:
            return []

        try:
            found_tickers = set()

            for match in self.ticker_pattern.finditer(text):
                ticker = match.group(1).upper()
                if ticker in self.all_tickers:
                    found_tickers.add(ticker)

            pattern = r"\b([A-Z]{2,5})\b"
            words = re.findall(pattern, text)
            for word in words:
                if word.upper() in self.all_tickers:
                    context = text.lower()
                    ticker = word.upper()
                    context_keywords = [
                        "stock",
                        "shares",
                        "ticker",
                        "trading",
                        "market",
                    ]
                    if any(kw in context for kw in context_keywords):
                        found_tickers.add(ticker)

            if found_tickers:
                logger.debug(
                    "tickers_extracted",
                    count=len(found_tickers),
                    tickers=sorted(found_tickers),
                )

            return sorted(found_tickers)

        except Exception as e:
            logger.error("tickers_extraction_failed", error=str(e))
            return []

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        if not text:
            return []

        try:
            normalized_text = self._normalize_text(text)
            words = re.findall(r"\b[a-z]{3,}\b", normalized_text)
            stop_words = {
                "the",
                "and",
                "for",
                "are",
                "but",
                "not",
                "you",
                "all",
                "can",
                "her",
                "was",
                "one",
                "our",
                "out",
                "day",
                "get",
                "has",
                "him",
                "his",
                "how",
                "its",
                "may",
                "new",
                "now",
                "old",
                "see",
                "two",
                "way",
                "who",
                "boy",
                "did",
                "let",
                "put",
                "say",
                "she",
                "too",
                "use",
                "dad",
                "mom",
                "act",
                "add",
                "age",
                "ago",
                "air",
                "art",
                "ask",
                "bad",
                "bag",
                "bed",
                "big",
                "box",
                "bus",
                "car",
                "cat",
                "cut",
                "dog",
                "eat",
                "end",
                "eye",
                "far",
                "few",
                "fly",
                "fun",
                "gas",
                "god",
                "got",
                "guy",
                "hot",
                "ice",
                "ill",
                "job",
                "joy",
                "key",
                "kid",
                "law",
                "lay",
                "lie",
                "low",
                "man",
                "map",
                "mix",
                "net",
                "off",
                "oil",
                "own",
                "pay",
                "per",
                "pic",
                "pig",
                "pot",
                "red",
                "run",
                "sad",
                "sat",
                "sea",
                "set",
                "sit",
                "six",
                "sky",
                "son",
                "sun",
                "tax",
                "tea",
                "ten",
                "tie",
                "top",
                "toy",
                "try",
                "van",
                "war",
                "win",
                "yes",
                "yet",
                "able",
                "about",
                "above",
                "after",
                "again",
                "against",
                "before",
                "being",
                "below",
                "between",
                "both",
                "came",
                "come",
                "could",
                "does",
                "done",
                "down",
                "during",
                "each",
                "even",
                "every",
                "find",
                "first",
                "from",
                "going",
                "good",
                "great",
                "have",
                "having",
                "here",
                "into",
                "just",
                "keep",
                "know",
                "last",
                "least",
                "life",
                "like",
                "live",
                "long",
                "made",
                "make",
                "many",
                "might",
                "more",
                "most",
                "much",
                "must",
                "name",
                "need",
                "never",
                "next",
                "night",
                "only",
                "over",
                "part",
                "place",
                "play",
                "point",
                "real",
                "right",
                "said",
                "same",
                "seem",
                "shall",
                "should",
                "since",
                "some",
                "such",
                "take",
                "than",
                "that",
                "their",
                "them",
                "then",
                "there",
                "these",
                "think",
                "this",
                "those",
                "three",
                "through",
                "time",
                "told",
                "under",
                "until",
                "very",
                "want",
                "well",
                "were",
                "what",
                "when",
                "where",
                "which",
                "while",
                "will",
                "with",
                "would",
                "year",
                "your",
                "this",
                "that",
                "these",
                "those",
                "been",
                "were",
                "was",
                "will",
                "would",
                "should",
                "could",
                "might",
                "must",
                "shall",
                "upon",
                "also",
            }

            filtered_words = [w for w in words if w not in stop_words]

            all_keywords = set()
            for category, keywords in self.category_keywords.items():
                for keyword in keywords:
                    if keyword in normalized_text:
                        all_keywords.add(keyword)

            word_counts = Counter(filtered_words)
            top_words = [word for word, count in word_counts.most_common(max_keywords)]

            keywords = list(all_keywords) + top_words
            keywords = list(dict.fromkeys(keywords))[:max_keywords]

            if keywords:
                logger.debug(
                    "keywords_extracted", count=len(keywords), keywords=keywords
                )

            return keywords

        except Exception as e:
            logger.error("keywords_extraction_failed", error=str(e))
            return []

    def classify_category(self, text: str) -> CategoryType:
        if not text:
            return CategoryType.OTHER

        try:
            normalized_text = self._normalize_text(text)
            category_scores = {category: 0 for category in CategoryType}

            for category, keywords in self.category_keywords.items():
                for keyword in keywords:
                    if keyword in normalized_text:
                        category_scores[category] += 1

            best_category = max(category_scores.items(), key=lambda x: x[1])

            if best_category[1] == 0:
                return CategoryType.OTHER

            logger.debug(
                "category_classified",
                category=best_category[0],
                score=best_category[1],
            )

            return best_category[0]

        except Exception as e:
            logger.error("category_classification_failed", error=str(e))
            return CategoryType.OTHER

    def extract_tags(self, text: str) -> List[str]:
        """Extract relevant tags from text"""
        try:
            tags = []
            text_lower = text.lower()

            if "breaking" in text_lower or "urgent" in text_lower:
                tags.append("breaking")

            if "update" in text_lower:
                tags.append("update")

            if "exclusive" in text_lower:
                tags.append("exclusive")

            if "analysis" in text_lower or "opinion" in text_lower:
                tags.append("analysis")

            return tags

        except Exception as e:
            logger.error("tags_extraction_failed", error=str(e))
            return []

    def _extract_prediction_markets(self, text: str, news_item) -> List[Dict[str, Any]]:
        """Extract prediction market related information"""
        try:
            markets = []

            platform_keywords = ["polymarket", "kalshi", "predictit", "manifold"]
            if any(kw in text.lower() for kw in platform_keywords):
                markets.append(
                    {
                        "type": "prediction_market_related",
                        "platforms": self._extract_platforms(text),
                        "entities": news_item.tickers + news_item.people,
                    }
                )

            return markets

        except Exception as e:
            logger.error("prediction_markets_extraction_failed", error=str(e))
            return []

    def _extract_platforms(self, text: str) -> List[str]:
        """Extract prediction market platform names"""
        try:
            platforms = []
            text_lower = text.lower()

            if "polymarket" in text_lower:
                platforms.append("Polymarket")

            if "kalshi" in text_lower:
                platforms.append("Kalshi")

            if "predictit" in text_lower:
                platforms.append("PredictIt")

            if "manifold" in text_lower:
                platforms.append("Manifold")

            return platforms

        except Exception as e:
            logger.error("platforms_extraction_failed", error=str(e))
            return []
