from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    NITTER = "nitter"
    RSS = "rss"


class CategoryType(str, Enum):
    POLITICS = "politics"
    CRYPTO = "crypto"
    ECONOMICS = "economics"
    SPORTS = "sports"
    OTHER = "other"


class NewsItem(BaseModel):
    id: str
    source: SourceType
    source_account: Optional[str] = None
    title: Optional[str] = None
    content: str
    url: str
    published_at: float

    # Analysis (no ML)
    impact_score: float = Field(default=0.0, ge=0.0, le=100.0)
    relevance_score: float = Field(default=0.0, ge=0.0, le=100.0)

    # Entities
    tickers: List[str] = Field(default_factory=list)
    people: List[str] = Field(default_factory=list)
    prediction_markets: List[Dict[str, Any]] = Field(default_factory=list)
    category: Optional[CategoryType] = None
    tags: List[str] = Field(default_factory=list)

    # Processing
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    is_high_signal: bool = False


class RawNewsItem(BaseModel):
    """Raw item from scraper before processing"""
    source: str
    source_account: Optional[str] = None
    title: Optional[str] = None
    content: str
    url: str
    published_at: str
    author: Optional[str] = None
    summary: Optional[str] = None


class UserSubscription(BaseModel):
    user_id: str
    nitter_accounts: List[str] = Field(default_factory=list)
    rss_feeds: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    impact_threshold: int = Field(default=70, ge=0, le=100)
    alert_channels: List[str] = Field(default=["terminal"])
    created_at: Optional[float] = None
    updated_at: Optional[float] = None


class UserSubscriptionCreate(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    nitter_accounts: List[str] = Field(default_factory=list, description="List of Nitter accounts to follow (with @)")
    rss_feeds: List[str] = Field(default_factory=list, description="List of RSS feed sources")
    categories: List[str] = Field(default_factory=list, description="List of categories to filter")
    keywords: List[str] = Field(default_factory=list, description="List of keywords to track")
    impact_threshold: int = Field(default=70, ge=0, le=100, description="Minimum impact score for alerts (0-100)")
    alert_channels: List[str] = Field(default=["terminal"], description="Alert channels")


class NewsListResponse(BaseModel):
    items: List[NewsItem]
    total: int
    limit: int
    offset: int


class SubscriptionResponse(BaseModel):
    status: str
    user_id: str
    created_at: Optional[float] = None


class SystemStats(BaseModel):
    total_news_items: int = 0
    items_last_24h: int = 0
    average_impact: float = 0.0
    active_connections: int = 0
    nitter_instances: Dict[str, Any] = Field(default_factory=dict)
    rss_feeds: Dict[str, Any] = Field(default_factory=dict)
    uptime_seconds: float = 0.0
    version: str = "0.1.0"


class HealthStatus(BaseModel):
    status: str
    database: str
    nitter_instances: Dict[str, str] = Field(default_factory=dict)
    timestamp: float
