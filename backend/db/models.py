"""
SQLAlchemy models for Startup Ideas Collector database
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    Enum,
    Boolean,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class SourceType(str, enum.Enum):
    """Types of content sources"""
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    TWITTER = "twitter"
    PRODUCTHUNT = "producthunt"
    INDIEHACKERS = "indiehackers"
    QUORA = "quora"
    YOUTUBE = "youtube"
    MEDIUM = "medium"
    DISCOURSE = "discourse"
    TAVILY = "tavily"
    APPSTORE = "appstore"
    G2 = "g2"


class AnalysisTier(str, enum.Enum):
    """Tiers of AI analysis depth"""
    NONE = "none"  # Not yet analyzed
    BASIC = "basic"  # Tier 2: Problem + Marketing only
    DEEP = "deep"  # Tier 3: All 6 agents


class CardStatus(str, enum.Enum):
    """Card workflow statuses"""
    NEW = "new"
    VIEWED = "viewed"
    IN_REVIEW = "in_review"
    VERIFIED = "verified"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class TrendDirection(str, enum.Enum):
    """Google Trends direction"""
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class Source(Base):
    """Content sources being monitored"""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)  # e.g., "reddit_freelance"
    type = Column(Enum(SourceType), nullable=False)
    config = Column(JSON, nullable=True)  # Source-specific configuration
    last_scraped = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    discussions = relationship("Discussion", back_populates="source", cascade="all, delete-orphan")
    thread_history = relationship("ScrapeThreadHistory", back_populates="source", cascade="all, delete-orphan")


class Discussion(Base):
    """Raw discussions scraped from sources"""
    __tablename__ = "discussions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)

    # Source metadata
    url = Column(String(500), unique=True, nullable=False)
    external_id = Column(String(200), nullable=True)  # Reddit ID, HN ID, etc.
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)  # Post + top comments
    author = Column(String(200), nullable=True)

    # Engagement metrics
    upvotes = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)

    # Timing
    posted_at = Column(DateTime, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    # Processing
    is_analyzed = Column(Boolean, default=False)
    passed_filter = Column(Boolean, default=False)  # Haiku filter result

    # Relationships
    source = relationship("Source", back_populates="discussions")
    problems = relationship("Problem", back_populates="discussion", cascade="all, delete-orphan")


class Problem(Base):
    """Problems extracted from discussions"""
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    discussion_id = Column(Integer, ForeignKey("discussions.id"), nullable=False)

    # Problem details
    problem_statement = Column(Text, nullable=False)
    severity = Column(Integer, nullable=True)  # 1-10
    target_audience = Column(Text, nullable=True)
    audience_type = Column(String(20), default="unknown", server_default="unknown")
    current_solutions = Column(Text, nullable=True)
    why_they_fail = Column(Text, nullable=True)

    # Analysis tier tracking
    analysis_tier = Column(Enum(AnalysisTier), default=AnalysisTier.NONE)

    # Metadata
    extracted_at = Column(DateTime, default=datetime.utcnow)

    # --- Card management fields ---
    card_status = Column(String(20), default="new", server_default="new")
    first_viewed_at = Column(DateTime, nullable=True)
    last_viewed_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    view_count = Column(Integer, default=0, server_default="0")
    is_starred = Column(Boolean, default=False, server_default="0")
    user_notes = Column(Text, nullable=True)
    user_tags = Column(JSON, nullable=True)

    # Relationships
    discussion = relationship("Discussion", back_populates="problems")
    startup_ideas = relationship("StartupIdea", back_populates="problem", cascade="all, delete-orphan")
    marketing_analysis = relationship("MarketingAnalysis", back_populates="problem", uselist=False, cascade="all, delete-orphan")
    design_analysis = relationship("DesignAnalysis", back_populates="problem", uselist=False, cascade="all, delete-orphan")
    tech_analysis = relationship("TechAnalysis", back_populates="problem", uselist=False, cascade="all, delete-orphan")
    validation_analysis = relationship("ValidationAnalysis", back_populates="problem", uselist=False, cascade="all, delete-orphan")
    trend_analysis = relationship("TrendAnalysis", back_populates="problem", uselist=False, cascade="all, delete-orphan")
    overall_scores = relationship("OverallScores", back_populates="problem", uselist=False, cascade="all, delete-orphan")


class StartupIdea(Base):
    """Startup ideas generated from problems"""
    __tablename__ = "startup_ideas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)

    # Idea details
    idea_title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    approach = Column(String(100), nullable=True)  # SaaS, marketplace, tool, API, mobile_app, community, browser_extension
    business_model = Column(String(200), nullable=True)  # B2C subscription, B2B SaaS, freemium, etc.
    value_proposition = Column(Text, nullable=True)
    core_features = Column(JSON, nullable=True)  # List of features
    monetization = Column(Text, nullable=True)  # Specific monetization details
    tags = Column(JSON, nullable=True)  # Categorization tags

    # Metadata
    generated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    problem = relationship("Problem", back_populates="startup_ideas")


class MarketingAnalysis(Base):
    """Marketing research and GTM strategy"""
    __tablename__ = "marketing_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False, unique=True)

    # Market sizing
    tam = Column(String(200), nullable=True)  # Total Addressable Market
    sam = Column(String(200), nullable=True)  # Serviceable Addressable Market
    som = Column(String(200), nullable=True)  # Serviceable Obtainable Market
    market_description = Column(Text, nullable=True)  # Market landscape description

    # Competitive analysis
    competitors_json = Column(JSON, nullable=True)  # List of competitors with details
    positioning_gaps = Column(Text, nullable=True)
    differentiation = Column(Text, nullable=True)
    competitive_moat = Column(Text, nullable=True)  # Sustainable advantage

    # GTM strategy
    gtm_strategy = Column(Text, nullable=True)
    gtm_channels = Column(JSON, nullable=True)  # Marketing channels
    gtm_messaging = Column(Text, nullable=True)  # Key messaging
    early_adopters = Column(Text, nullable=True)  # Who to target first
    acquisition_channels = Column(JSON, nullable=True)  # Alternative name for gtm_channels
    positioning = Column(Text, nullable=True)
    pricing_model = Column(String(100), nullable=True)
    target_segments = Column(JSON, nullable=True)

    # Score
    market_score = Column(Integer, nullable=True)  # 0-100
    score_reasoning = Column(Text, nullable=True)  # Why this score

    # Metadata
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    problem = relationship("Problem", back_populates="marketing_analysis")


class DesignAnalysis(Base):
    """UX concept and user experience planning"""
    __tablename__ = "design_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False, unique=True)

    # UX concept
    ux_concept = Column(Text, nullable=True)
    user_flow = Column(Text, nullable=True)
    key_screens_json = Column(JSON, nullable=True)  # List of key screens
    design_principles = Column(Text, nullable=True)

    # Inspiration and style
    inspiration = Column(Text, nullable=True)
    design_style = Column(String(100), nullable=True)

    # Score
    design_score = Column(Integer, nullable=True)  # 0-100

    # Metadata
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    problem = relationship("Problem", back_populates="design_analysis")


class TechAnalysis(Base):
    """Technical feasibility and implementation planning"""
    __tablename__ = "tech_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False, unique=True)

    # Complexity assessment
    complexity_score = Column(Integer, nullable=True)  # 1-10
    expertise_level = Column(String(100), nullable=True)
    infrastructure_needs = Column(Text, nullable=True)

    # Tech stack
    tech_stack_json = Column(JSON, nullable=True)  # Frontend, backend, database, services

    # Timeline
    time_to_mvp_weeks = Column(Integer, nullable=True)
    time_to_market_weeks = Column(Integer, nullable=True)
    team_size = Column(Integer, nullable=True)

    # Risks and integrations
    risks_json = Column(JSON, nullable=True)
    integrations_json = Column(JSON, nullable=True)

    # Score
    tech_score = Column(Integer, nullable=True)  # 0-100

    # Metadata
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    problem = relationship("Problem", back_populates="tech_analysis")


class ValidationAnalysis(Base):
    """Existing solutions research and validation"""
    __tablename__ = "validation_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False, unique=True)

    # Existing solutions
    existing_solutions_json = Column(JSON, nullable=True)  # List of existing products
    gap_analysis = Column(Text, nullable=True)
    whitespace_opportunities = Column(Text, nullable=True)

    # Success and failure stories
    success_stories_json = Column(JSON, nullable=True)
    failure_analysis = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)

    # Validation signals
    validation_sources_json = Column(JSON, nullable=True)  # Where validation came from
    people_count = Column(Integer, nullable=True)  # How many people express this problem

    # Score
    validation_score = Column(Integer, nullable=True)  # 0-100

    # Metadata
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    problem = relationship("Problem", back_populates="validation_analysis")


class TrendAnalysis(Base):
    """Google Trends and momentum analysis"""
    __tablename__ = "trend_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False, unique=True)

    # Trends data
    keywords_json = Column(JSON, nullable=True)  # Keywords analyzed
    trend_direction = Column(Enum(TrendDirection), nullable=True)
    yoy_growth = Column(Float, nullable=True)  # Year-over-year growth percentage

    # Momentum and seasonality
    momentum_score = Column(Integer, nullable=True)  # 0-100
    seasonality_json = Column(JSON, nullable=True)
    peak_periods = Column(String(200), nullable=True)

    # Related trends
    related_trends_json = Column(JSON, nullable=True)

    # Score
    trend_score = Column(Integer, nullable=True)  # 0-100

    # Metadata
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    problem = relationship("Problem", back_populates="trend_analysis")


class ScrapeLog(Base):
    """Log of scraping runs"""
    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)
    status = Column(String(20), default="running")  # running, completed, failed
    discussions_found = Column(Integer, default=0)
    problems_created = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    triggered_by = Column(String(20), default="manual")  # manual, schedule


class ScrapeThreadHistory(Base):
    """
    History of scanned threads/topics to avoid re-crawling the same content too often.
    """
    __tablename__ = "scrape_thread_history"
    __table_args__ = (
        UniqueConstraint("source_id", "thread_key", name="uq_thread_history_source_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    thread_key = Column(String(300), nullable=False)  # external_id or canonical URL
    external_id = Column(String(200), nullable=True)
    url = Column(String(500), nullable=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    seen_count = Column(Integer, default=1, nullable=False)

    source = relationship("Source", back_populates="thread_history")


class OverallScores(Base):
    """Aggregated scores and overall confidence"""
    __tablename__ = "overall_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False, unique=True)

    # Individual scores
    market_score = Column(Integer, nullable=True)  # 0-100
    design_score = Column(Integer, nullable=True)  # 0-100
    tech_score = Column(Integer, nullable=True)  # 0-100
    validation_score = Column(Integer, nullable=True)  # 0-100
    trend_score = Column(Integer, nullable=True)  # 0-100

    # Overall confidence
    overall_confidence_score = Column(Integer, nullable=True)  # 0-100
    # Formula: Market×0.25 + Design×0.15 + Tech×0.20 + Validation×0.25 + Trend×0.15

    # Analysis tier
    analysis_tier = Column(Enum(AnalysisTier), default=AnalysisTier.NONE)

    # Metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    problem = relationship("Problem", back_populates="overall_scores")
