"""
Hacker News scraper using the official HN API
"""
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from agents.scrapers.base_agent import BaseScraper
from db.models import Discussion, SourceType
from config import config_loader
import logging
import time

logger = logging.getLogger(__name__)


class HackerNewsScraper(BaseScraper):
    """Scrapes Hacker News for problem discussions"""

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(self, db: Session):
        super().__init__(db, SourceType.HACKERNEWS, "hackernews")

        # Load configuration
        self.config = config_loader.get_hackernews_config()
        self.min_score = self.config.get('min_score', 10)
        self.max_items = self.config.get('max_items', 30)
        self.keywords = self.config.get('keywords', [])
        self.history_cooldown_hours = int(self.config.get('history_cooldown_hours', 24))

    def _fetch_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single item from HN API"""
        try:
            response = requests.get(f"{self.BASE_URL}/item/{item_id}.json", timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching HN item {item_id}: {e}")
        return None

    def _contains_keywords(self, text: str) -> bool:
        """Check if text contains any of the problem keywords"""
        if not text:
            return False

        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.keywords)

    def _looks_like_problem_story(self, title: str, text: str, comments_count: int, score: int) -> bool:
        combined = f"{title} {text}".lower()
        patterns = [
            "ask hn:",
            "how do you",
            "how can i",
            "struggling",
            "pain",
            "problem",
            "is there a tool",
            "any recommendations",
            "looking for",
        ]
        pattern_match = any(p in combined for p in patterns)
        engagement_match = comments_count >= 20 or score >= 80
        return pattern_match or engagement_match

    def _fetch_comments(self, item_ids: List[int], max_comments: int = 20) -> str:
        """Fetch and format comments"""
        comments = []

        for comment_id in item_ids[:max_comments]:
            comment_data = self._fetch_item(comment_id)

            if not comment_data or comment_data.get('deleted') or comment_data.get('dead'):
                continue

            text = comment_data.get('text', '')
            if not text or len(text) < 20:
                continue

            score = comment_data.get('score', 0)

            # Include comment if it has good score or contains problem keywords
            if score >= 3 or self._contains_keywords(text):
                # Clean up HTML
                clean_text = text.replace('<p>', '\n').replace('</p>', '')
                clean_text = clean_text.replace('&#x27;', "'").replace('&quot;', '"')
                comments.append(f"Comment (↑{score}): {clean_text[:500]}")  # Limit length

            if len(comments) >= max_comments:
                break

            time.sleep(0.1)  # Rate limiting

        return "\n\n".join(comments) if comments else ""

    def _scrape_ask_hn(self, limit: int = 15) -> List[Discussion]:
        """Scrape Ask HN posts"""
        logger.info("Scraping Ask HN posts...")
        discussions = []

        try:
            # Get Ask HN stories
            response = requests.get(f"{self.BASE_URL}/askstories.json", timeout=10)
            if response.status_code != 200:
                return discussions

            item_ids = response.json()[:limit * 2]  # Fetch more than needed for filtering

            for item_id in item_ids:
                item = self._fetch_item(item_id)

                if not item or item.get('type') != 'story':
                    continue

                title = item.get('title', '')
                text = item.get('text', '')
                score = item.get('score', 0)

                # Filter by score (slightly relaxed for better recall)
                effective_min_score = max(5, int(self.min_score * 0.6))
                if score < effective_min_score:
                    continue

                # Check for problem keywords in title or text
                comments_count = item.get('descendants', 0)
                if not (
                    self._contains_keywords(title)
                    or self._contains_keywords(text)
                    or self._looks_like_problem_story(title, text, comments_count, score)
                ):
                    continue

                thread_url = f"https://news.ycombinator.com/item?id={item_id}"
                if self._track_thread_and_should_skip(
                    external_id=str(item_id),
                    url=thread_url,
                    cooldown_hours=self.history_cooldown_hours,
                ):
                    continue

                # Fetch comments
                comment_ids = item.get('kids', [])
                comments_text = self._fetch_comments(comment_ids, max_comments=15) if comment_ids else ""

                # Build full content
                full_content = title
                if text:
                    full_content += f"\n\n{text}"
                if comments_text:
                    full_content += f"\n\n--- Comments ---\n{comments_text}"

                # Save discussion
                discussion = self._save_discussion(
                    url=thread_url,
                    external_id=str(item_id),
                    title=title,
                    content=full_content,
                    author=item.get('by', 'unknown'),
                    upvotes=score,
                    comments_count=item.get('descendants', 0),
                    posted_at=datetime.fromtimestamp(item.get('time', 0))
                )

                if discussion:
                    discussions.append(discussion)

                if len(discussions) >= limit:
                    break

                time.sleep(0.2)  # Rate limiting

        except Exception as e:
            logger.error(f"Error scraping Ask HN: {e}")

        logger.info(f"Found {len(discussions)} Ask HN discussions")
        return discussions

    def _scrape_show_hn(self, limit: int = 10) -> List[Discussion]:
        """Scrape Show HN posts with critical feedback"""
        logger.info("Scraping Show HN posts...")
        discussions = []

        try:
            response = requests.get(f"{self.BASE_URL}/showstories.json", timeout=10)
            if response.status_code != 200:
                return discussions

            item_ids = response.json()[:limit * 2]

            for item_id in item_ids:
                item = self._fetch_item(item_id)

                if not item or item.get('type') != 'story':
                    continue

                score = item.get('score', 0)
                effective_min_score = max(5, int(self.min_score * 0.6))
                if score < effective_min_score:
                    continue

                # For Show HN, we want posts with critical comments
                comment_ids = item.get('kids', [])
                if not comment_ids or len(comment_ids) < 3:  # Need some discussion
                    continue

                thread_url = f"https://news.ycombinator.com/item?id={item_id}"
                if self._track_thread_and_should_skip(
                    external_id=str(item_id),
                    url=thread_url,
                    cooldown_hours=self.history_cooldown_hours,
                ):
                    continue

                comments_text = self._fetch_comments(comment_ids, max_comments=10)

                # Check if comments contain problem keywords (critical feedback)
                if not self._contains_keywords(comments_text):
                    # Fallback: include high-engagement feedback threads even without exact keywords
                    descendants = item.get('descendants', 0)
                    if descendants < 25 and score < 60:
                        continue

                if not comments_text:
                    continue

                title = item.get('title', '')
                text = item.get('text', '')

                full_content = title
                if text:
                    full_content += f"\n\n{text}"
                full_content += f"\n\n--- Critical Feedback ---\n{comments_text}"

                discussion = self._save_discussion(
                    url=thread_url,
                    external_id=str(item_id),
                    title=title,
                    content=full_content,
                    author=item.get('by', 'unknown'),
                    upvotes=score,
                    comments_count=item.get('descendants', 0),
                    posted_at=datetime.fromtimestamp(item.get('time', 0))
                )

                if discussion:
                    discussions.append(discussion)

                if len(discussions) >= limit:
                    break

                time.sleep(0.2)

        except Exception as e:
            logger.error(f"Error scraping Show HN: {e}")

        logger.info(f"Found {len(discussions)} Show HN discussions")
        return discussions

    def scrape(self) -> List[Discussion]:
        """Scrape Hacker News for problem discussions"""
        all_discussions = []

        # Scrape Ask HN (60% of quota)
        ask_limit = int(self.max_items * 0.6)
        ask_discussions = self._scrape_ask_hn(limit=ask_limit)
        all_discussions.extend(ask_discussions)

        # Scrape Show HN (40% of quota)
        show_limit = self.max_items - len(all_discussions)
        if show_limit > 0:
            show_discussions = self._scrape_show_hn(limit=show_limit)
            all_discussions.extend(show_discussions)

        return all_discussions


def main():
    """Test Hacker News scraper"""
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        scraper = HackerNewsScraper(db)
        result = scraper.run()
        print(f"\nScrape results: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
