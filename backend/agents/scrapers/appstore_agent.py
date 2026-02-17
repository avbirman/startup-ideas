"""
App Store Reviews Scraper - fetches 1-2 star reviews from Apple App Store

Uses the free iTunes Search API + App Store RSS feeds (no auth required).
1-2 star reviews = real pain points = startup opportunities.
"""
import requests
import time
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from agents.scrapers.base_agent import BaseScraper
from db.models import Discussion, SourceType
from config import config_loader
import logging

logger = logging.getLogger(__name__)


class AppStoreScraper(BaseScraper):
    """Scrapes 1-2 star App Store reviews as problem signal"""

    ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
    REVIEWS_RSS_URL = "https://itunes.apple.com/us/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"

    def __init__(self, db: Session):
        super().__init__(db, SourceType.APPSTORE, "appstore")

        self.app_config = config_loader.get('appstore', {})
        self.cooldown_hours = int(self.app_config.get('history_cooldown_hours', 48))
        self.max_apps = int(self.app_config.get('max_apps_per_category', 10))
        self.max_reviews = int(self.app_config.get('max_reviews_per_app', 20))
        self.min_rating = int(self.app_config.get('min_rating', 2))
        self.categories = self.app_config.get('categories', [
            {'id': '6007', 'name': 'Productivity'},
            {'id': '6000', 'name': 'Business'},
            {'id': '6015', 'name': 'Finance'},
        ])

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'StartupIdeasCollector/1.0',
            'Accept': 'application/json',
        })

    def _search_apps(self, category_id: str, limit: int = 10) -> List[dict]:
        """Search top apps in a category using iTunes Search API"""
        try:
            params = {
                'entity': 'software',
                'genreId': category_id,
                'limit': limit,
                'country': 'us',
                'lang': 'en_us',
            }
            resp = self.session.get(self.ITUNES_SEARCH_URL, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return data.get('results', [])
        except Exception as e:
            logger.error(f"Error searching App Store category {category_id}: {e}")
        return []

    def _fetch_reviews(self, app_id: str, app_name: str) -> List[Discussion]:
        """Fetch low-rating reviews for an app via RSS feed"""
        discussions = []
        url = self.REVIEWS_RSS_URL.format(app_id=app_id)

        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return []

            data = resp.json()
            feed = data.get('feed', {})
            entries = feed.get('entry', [])

            # First entry is app metadata, skip it
            if entries and isinstance(entries[0], dict) and 'im:name' in entries[0]:
                entries = entries[1:]

            count = 0
            for entry in entries:
                if count >= self.max_reviews:
                    break

                try:
                    rating_val = int(entry.get('im:rating', {}).get('label', '5'))
                except (ValueError, AttributeError):
                    continue

                # Only keep low-rating reviews (complaints = pain points)
                if rating_val > self.min_rating:
                    continue

                title = entry.get('title', {}).get('label', '')
                content = entry.get('content', {}).get('label', '')
                author = entry.get('author', {}).get('name', {}).get('label', 'anonymous')
                review_id = entry.get('id', {}).get('label', '')
                updated = entry.get('updated', {}).get('label', '')

                if not content or len(content) < 30:
                    continue

                full_content = (
                    f"App: {app_name}\n"
                    f"Rating: {'⭐' * rating_val} ({rating_val}/5)\n"
                    f"Review Title: {title}\n\n"
                    f"{content}"
                )
                review_url = f"https://apps.apple.com/us/app/id{app_id}"
                external_id = f"appstore_{app_id}_{hash(content) % 10**8}"

                if self._track_thread_and_should_skip(
                    external_id=external_id,
                    url=review_url + f"#{hash(content) % 10**8}",
                    cooldown_hours=self.cooldown_hours,
                ):
                    continue

                try:
                    posted_at = datetime.fromisoformat(updated.replace('Z', '+00:00')) if updated else datetime.utcnow()
                    posted_at = posted_at.replace(tzinfo=None)
                except Exception:
                    posted_at = datetime.utcnow()

                discussion = self._save_discussion(
                    url=review_url + f"#review-{hash(content) % 10**8}",
                    external_id=external_id,
                    title=f"[App Store {rating_val}★] {app_name}: {title[:100]}",
                    content=full_content,
                    author=author,
                    upvotes=0,
                    comments_count=0,
                    posted_at=posted_at,
                )
                if discussion:
                    discussions.append(discussion)
                    count += 1

        except Exception as e:
            logger.error(f"Error fetching reviews for app {app_id}: {e}")

        return discussions

    def scrape(self, limit: Optional[int] = None) -> List[Discussion]:
        """Scrape low-rating reviews from top apps across configured categories"""
        all_discussions = []

        for category in self.categories:
            cat_id = category.get('id', '')
            cat_name = category.get('name', cat_id)
            max_apps = limit or self.max_apps

            logger.info(f"App Store: fetching top {max_apps} apps in {cat_name}...")
            apps = self._search_apps(cat_id, limit=max_apps)

            for app in apps:
                app_id = str(app.get('trackId', ''))
                app_name = app.get('trackName', 'Unknown')
                if not app_id:
                    continue

                logger.info(f"  Fetching reviews for: {app_name} (id={app_id})")
                reviews = self._fetch_reviews(app_id, app_name)
                all_discussions.extend(reviews)
                time.sleep(0.5)

        logger.info(f"App Store: {len(all_discussions)} low-rating reviews saved")
        return all_discussions
