"""
Configuration management for Startup Ideas Collector
"""
import os
from pathlib import Path
from typing import List, Dict, Any
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")

    # Reddit API (optional)
    reddit_client_id: str = Field(default="", alias="REDDIT_CLIENT_ID")
    reddit_client_secret: str = Field(default="", alias="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field(
        default="startup-ideas-collector/1.0",
        alias="REDDIT_USER_AGENT"
    )

    # Twitter/X API
    twitter_bearer_token: str = Field(default="", alias="TWITTER_BEARER_TOKEN")

    # Product Hunt API (optional)
    producthunt_api_token: str = Field(default="", alias="PRODUCTHUNT_API_TOKEN")

    # YouTube Data API
    youtube_api_key: str = Field(default="", alias="YOUTUBE_API_KEY")

    # Database
    database_path: str = Field(
        default="/data/startup_ideas.db",
        alias="DATABASE_PATH"
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    # AI Models
    filter_model: str = Field(
        default="claude-3-haiku-20240307",
        alias="FILTER_MODEL"
    )
    analysis_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        alias="ANALYSIS_MODEL"
    )

    # Cost Optimization
    min_confidence_to_store: int = Field(default=5, alias="MIN_CONFIDENCE_TO_STORE")
    auto_deep_analysis_threshold: int = Field(
        default=70,
        alias="AUTO_DEEP_ANALYSIS_THRESHOLD"
    )


class ConfigLoader:
    """Load configuration from config.yaml"""

    def __init__(self, config_path: str = "config.yaml"):
        # Support both "config.yaml" (when running from backend/) and "backend/config.yaml" (when running from root)
        config_path_obj = Path(config_path)
        if not config_path_obj.exists() and not config_path_obj.is_absolute():
            # Try alternative path
            alt_path = Path("backend") / config_path
            if alt_path.exists():
                config_path_obj = alt_path
        self.config_path = config_path_obj
        self._config = None

    @property
    def config(self) -> Dict[str, Any]:
        """Load and cache configuration"""
        if self._config is None:
            self._load_config()
        return self._config

    def _load_config(self):
        """Load YAML configuration file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            self._config = yaml.safe_load(f)

    def get_reddit_config(self) -> Dict[str, Any]:
        """Get Reddit scraper configuration"""
        return self.config.get('reddit', {})

    def get_hackernews_config(self) -> Dict[str, Any]:
        """Get Hacker News scraper configuration"""
        return self.config.get('hackernews', {})

    def get_twitter_config(self) -> Dict[str, Any]:
        """Get Twitter scraper configuration"""
        return self.config.get('twitter', {})

    def get_indiehackers_config(self) -> Dict[str, Any]:
        """Get Indie Hackers scraper configuration"""
        return self.config.get('indiehackers', {})

    def get_producthunt_config(self) -> Dict[str, Any]:
        """Get Product Hunt scraper configuration"""
        return self.config.get('producthunt', {})

    def get_quora_config(self) -> Dict[str, Any]:
        """Get Quora scraper configuration"""
        return self.config.get('quora', {})

    def get_youtube_config(self) -> Dict[str, Any]:
        """Get YouTube scraper configuration"""
        return self.config.get('youtube', {})

    def get_medium_config(self) -> Dict[str, Any]:
        """Get Medium scraper configuration"""
        return self.config.get('medium', {})

    def get_discourse_config(self) -> Dict[str, Any]:
        """Get Discourse scraper configuration"""
        return self.config.get('discourse', {})

    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration"""
        return self.config.get('ai', {})

    def get_scheduler_config(self) -> Dict[str, Any]:
        """Get scheduler configuration"""
        return self.config.get('scheduler', {})

    def get_subreddits(self) -> List[Dict[str, Any]]:
        """Get list of subreddits to monitor"""
        reddit_config = self.get_reddit_config()
        return reddit_config.get('subreddits', [])

    def get_problem_indicators(self) -> List[str]:
        """Get global problem indicator keywords"""
        reddit_config = self.get_reddit_config()
        return reddit_config.get('problem_indicators', [])


# Global instances
settings = Settings()
config_loader = ConfigLoader()
