"""
Base class for all scraper agents
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from db.models import Source, Discussion, SourceType, ScrapeThreadHistory
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all content scrapers"""

    def __init__(self, db: Session, source_type: SourceType, source_name: str):
        self.db = db
        self.source_type = source_type
        self.source_name = source_name
        self.source = self._get_or_create_source()

    def _get_or_create_source(self) -> Source:
        """Get or create source record in database"""
        source = self.db.query(Source).filter(Source.name == self.source_name).first()

        if not source:
            logger.info(f"Creating new source: {self.source_name}")
            source = Source(
                name=self.source_name,
                type=self.source_type,
                is_active=True
            )
            self.db.add(source)
            self.db.commit()
            self.db.refresh(source)

        return source

    def _save_discussion(
        self,
        url: str,
        external_id: str,
        title: str,
        content: str,
        author: Optional[str] = None,
        upvotes: int = 0,
        comments_count: int = 0,
        posted_at: Optional[datetime] = None
    ) -> Optional[Discussion]:
        """
        Save discussion to database if it doesn't exist
        Returns Discussion object or None if already exists
        """
        # Check if discussion already exists
        existing = self.db.query(Discussion).filter(Discussion.url == url).first()
        if existing:
            logger.debug(f"Discussion already exists: {url}")
            return None

        discussion = Discussion(
            source_id=self.source.id,
            url=url,
            external_id=external_id,
            title=title,
            content=content,
            author=author,
            upvotes=upvotes,
            comments_count=comments_count,
            posted_at=posted_at,
            scraped_at=datetime.utcnow()
        )

        self.db.add(discussion)
        self.db.commit()
        self.db.refresh(discussion)

        logger.info(f"Saved new discussion: {title[:50]}... (upvotes: {upvotes})")
        return discussion

    def _update_source_timestamp(self):
        """Update last_scraped timestamp for source"""
        self.source.last_scraped = datetime.utcnow()
        self.db.commit()

    def _track_thread_and_should_skip(
        self,
        *,
        external_id: Optional[str],
        url: Optional[str],
        cooldown_hours: int = 24
    ) -> bool:
        """
        Track thread in history and decide whether to skip expensive re-crawl.

        Returns:
          True  -> skip this thread (seen recently)
          False -> process this thread now
        """
        thread_key = (external_id or url or "").strip()
        if not thread_key:
            return False

        now = datetime.utcnow()
        record = (
            self.db.query(ScrapeThreadHistory)
            .filter(
                ScrapeThreadHistory.source_id == self.source.id,
                ScrapeThreadHistory.thread_key == thread_key
            )
            .first()
        )

        if not record:
            record = ScrapeThreadHistory(
                source_id=self.source.id,
                thread_key=thread_key,
                external_id=external_id,
                url=url,
                first_seen_at=now,
                last_seen_at=now,
                seen_count=1,
            )
            self.db.add(record)
            self.db.commit()
            return False

        should_skip = False
        if cooldown_hours > 0 and record.last_seen_at:
            elapsed_seconds = (now - record.last_seen_at).total_seconds()
            should_skip = elapsed_seconds < cooldown_hours * 3600

        record.last_seen_at = now
        record.seen_count = (record.seen_count or 0) + 1
        if external_id:
            record.external_id = external_id
        if url:
            record.url = url
        self.db.commit()

        return should_skip

    @abstractmethod
    def scrape(self, **kwargs) -> List[Discussion]:
        """
        Scrape content from source
        Must be implemented by child classes
        Returns list of newly created Discussion objects
        """
        pass

    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Main entry point - scrape and return results summary
        """
        logger.info(f"Starting scrape for: {self.source_name}")
        start_time = datetime.utcnow()

        try:
            discussions = self.scrape(**kwargs)
            self._update_source_timestamp()

            duration = (datetime.utcnow() - start_time).total_seconds()

            result = {
                "source": self.source_name,
                "success": True,
                "discussions_count": len(discussions),
                "duration_seconds": duration,
                "timestamp": datetime.utcnow().isoformat()
            }

            logger.info(f"Scrape completed: {len(discussions)} new discussions in {duration:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Scrape failed for {self.source_name}: {e}")
            duration = (datetime.utcnow() - start_time).total_seconds()

            return {
                "source": self.source_name,
                "success": False,
                "error": str(e),
                "duration_seconds": duration,
                "timestamp": datetime.utcnow().isoformat()
            }
