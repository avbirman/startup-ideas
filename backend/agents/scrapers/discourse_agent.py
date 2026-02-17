"""
Discourse scraper

Scrapes posts from Discourse forums (many sites use this platform)
Discourse has a standard JSON API that works across all instances
"""
import requests
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from agents.scrapers.base_agent import BaseScraper
from db.models import Discussion, SourceType
from config import config_loader
import logging
import time

logger = logging.getLogger(__name__)


class DiscourseScraper(BaseScraper):
    """Scrapes Discourse forums for problem discussions"""

    def __init__(self, db: Session):
        super().__init__(db, SourceType.DISCOURSE, "discourse")

        # Load configuration
        self.config = config_loader.get_discourse_config()
        self.forums = self.config.get('forums', [])
        self.max_topics = self.config.get('max_topics', 20)
        self.min_likes = self.config.get('min_likes', 2)

        self.headers = {
            'Accept': 'application/json',
            'User-Agent': 'StartupIdeasCollector/1.0'
        }

    def _fetch_latest_topics(self, forum_url: str, category_id: str = None) -> List[Dict[str, Any]]:
        """
        Fetch latest topics from Discourse forum
        Discourse API: {forum_url}/latest.json
        """
        topics = []

        try:
            # Discourse standard endpoint
            endpoint = f"{forum_url}/latest.json"
            logger.info(f"Fetching topics from: {endpoint}")

            params = {}
            if category_id:
                params['category'] = category_id

            response = requests.get(endpoint, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Get topic list
            topic_list = data.get('topic_list', {}).get('topics', [])

            for topic in topic_list[:self.max_topics]:
                topics.append({
                    'id': topic.get('id'),
                    'title': topic.get('title', ''),
                    'slug': topic.get('slug', ''),
                    'posts_count': topic.get('posts_count', 0),
                    'like_count': topic.get('like_count', 0),
                    'views': topic.get('views', 0),
                    'created_at': topic.get('created_at', ''),
                    'category_id': topic.get('category_id')
                })

            logger.info(f"Found {len(topics)} topics")

        except requests.RequestException as e:
            logger.error(f"Failed to fetch topics from {forum_url}: {e}")
        except Exception as e:
            logger.error(f"Error parsing topics: {e}")

        return topics

    def _fetch_topic_posts(self, forum_url: str, topic_id: int) -> Dict[str, Any]:
        """
        Fetch posts from a specific topic
        Discourse API: {forum_url}/t/{topic_id}.json
        """
        try:
            endpoint = f"{forum_url}/t/{topic_id}.json"

            response = requests.get(endpoint, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Get original post
            post_stream = data.get('post_stream', {})
            posts = post_stream.get('posts', [])

            if not posts:
                return {}

            # Get first post (original)
            first_post = posts[0]

            # Get top replies (max 5)
            replies = []
            for post in posts[1:6]:  # Skip first, get next 5
                if post.get('cooked'):  # HTML content
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(post['cooked'], 'html.parser')
                    text = soup.get_text(strip=True)
                    if text:
                        replies.append({
                            'text': text[:300],
                            'author': post.get('username', 'unknown'),
                            'likes': post.get('like_count', 0)
                        })

            # Parse first post content
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(first_post.get('cooked', ''), 'html.parser')
            content = soup.get_text(strip=True)

            return {
                'content': content,
                'author': first_post.get('username', 'unknown'),
                'created_at': first_post.get('created_at', ''),
                'likes': first_post.get('like_count', 0),
                'replies': replies
            }

        except Exception as e:
            logger.warning(f"Failed to fetch topic {topic_id}: {e}")
            return {}

    def scrape(self) -> List[Discussion]:
        """
        Scrape Discourse forums for problem discussions
        """
        logger.info("Starting Discourse scraping...")
        all_discussions = []

        for forum in self.forums:
            forum_url = forum.get('url', '').rstrip('/')
            forum_name = forum.get('name', forum_url)
            category_id = forum.get('category_id')

            logger.info(f"Processing forum: {forum_name}")

            topics = self._fetch_latest_topics(forum_url, category_id)

            for topic_data in topics:
                # Filter by likes
                if topic_data['like_count'] < self.min_likes:
                    continue

                # Check for problem keywords in title
                keywords = self.config.get('problem_keywords', [])
                if keywords and not any(kw.lower() in topic_data['title'].lower() for kw in keywords):
                    continue

                # Fetch full topic content
                time.sleep(0.5)  # Rate limiting
                post_data = self._fetch_topic_posts(forum_url, topic_data['id'])

                if not post_data:
                    continue

                # Build content
                content_parts = [
                    post_data['content']
                ]

                if post_data['replies']:
                    content_parts.append("\n\n--- Top Replies ---")
                    for reply in post_data['replies']:
                        content_parts.append(f"\n• {reply['author']}: {reply['text']}")

                content = '\n'.join(content_parts)

                # Build URL
                topic_url = f"{forum_url}/t/{topic_data['slug']}/{topic_data['id']}"

                # Save discussion
                discussion = self._save_discussion(
                    url=topic_url,
                    external_id=f"{forum_name}_{topic_data['id']}",
                    title=topic_data['title'],
                    content=content,
                    author=post_data['author'],
                    upvotes=topic_data['like_count'],
                    comments_count=topic_data['posts_count'] - 1,  # Exclude original post
                    posted_at=datetime.fromisoformat(post_data['created_at'].replace('Z', '+00:00'))
                )

                if discussion:
                    all_discussions.append(discussion)

            logger.info(f"Found {len(all_discussions)} discussions from {forum_name}")

            # Rate limiting between forums
            time.sleep(2)

        logger.info(f"Discourse scraping complete: {len(all_discussions)} total discussions")
        return all_discussions


def main():
    """Test Discourse scraper"""
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        scraper = DiscourseScraper(db)
        result = scraper.run()
        print(f"\nScrape results: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
