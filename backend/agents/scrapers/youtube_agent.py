"""
YouTube scraper using official YouTube Data API v3

Searches for videos and extracts comments discussing problems
"""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from agents.scrapers.base_agent import BaseScraper
from db.models import Discussion, SourceType
from config import settings, config_loader
import logging
import time

logger = logging.getLogger(__name__)


class YouTubeScraper(BaseScraper):
    """Scrapes YouTube comments for problem discussions"""

    def __init__(self, db: Session):
        super().__init__(db, SourceType.YOUTUBE, "youtube")

        # Load configuration
        self.config = config_loader.get_youtube_config()
        self.api_key = settings.youtube_api_key if hasattr(settings, 'youtube_api_key') else None

        if not self.api_key:
            logger.error("YouTube API key not configured")
            self.api_key = None

        self.api_base = "https://www.googleapis.com/youtube/v3"
        self.search_queries = self.config.get('search_queries', [])
        self.max_videos = self.config.get('max_videos', 10)
        self.max_comments_per_video = self.config.get('max_comments_per_video', 20)
        self.history_cooldown_hours = int(self.config.get('history_cooldown_hours', 48))

    def _search_videos(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for videos using YouTube Data API
        """
        if not self.api_key:
            logger.error("YouTube API key not available")
            return []

        videos = []

        try:
            # Search endpoint
            url = f"{self.api_base}/search"

            # Calculate date for recent videos (last 30 days)
            published_after = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'

            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'order': 'relevance',
                'maxResults': max_results,
                'publishedAfter': published_after,
                'key': self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            for item in data.get('items', []):
                snippet = item.get('snippet', {})
                video_id = item.get('id', {}).get('videoId')

                if not video_id:
                    continue

                videos.append({
                    'video_id': video_id,
                    'title': snippet.get('title', ''),
                    'description': snippet.get('description', ''),
                    'channel': snippet.get('channelTitle', ''),
                    'published_at': snippet.get('publishedAt', ''),
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                })

            logger.info(f"Found {len(videos)} videos for query: {query}")

        except requests.RequestException as e:
            logger.error(f"YouTube API error for query '{query}': {e}")
        except Exception as e:
            logger.error(f"Error searching videos: {e}")

        return videos

    def _get_video_comments(self, video_id: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Get comments for a specific video
        """
        if not self.api_key:
            return []

        comments = []

        try:
            url = f"{self.api_base}/commentThreads"

            params = {
                'part': 'snippet',
                'videoId': video_id,
                'order': 'relevance',  # Get most relevant comments
                'maxResults': max_results,
                'textFormat': 'plainText',
                'key': self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            for item in data.get('items', []):
                snippet = item.get('snippet', {}).get('topLevelComment', {}).get('snippet', {})

                comment_text = snippet.get('textDisplay', '')
                if not comment_text:
                    continue

                comments.append({
                    'text': comment_text,
                    'author': snippet.get('authorDisplayName', 'unknown'),
                    'likes': snippet.get('likeCount', 0),
                    'published_at': snippet.get('publishedAt', '')
                })

        except requests.RequestException as e:
            logger.error(f"Failed to get comments for video {video_id}: {e}")
        except Exception as e:
            logger.error(f"Error parsing comments: {e}")

        return comments

    def scrape(self) -> List[Discussion]:
        """
        Scrape YouTube comments for problem discussions
        """
        logger.info("Starting YouTube scraping...")
        all_discussions = []

        if not self.api_key:
            logger.error("YouTube API key not configured - cannot scrape")
            return all_discussions

        for search_query in self.search_queries:
            query = search_query.get('query', '')
            label = search_query.get('label', 'general')
            min_engagement = search_query.get('min_engagement', 5)

            logger.info(f"Searching YouTube: {label} - '{query}'")

            videos = self._search_videos(query, max_results=self.max_videos)

            for video_data in videos:
                if self._track_thread_and_should_skip(
                    external_id=video_data['video_id'],
                    url=video_data['url'],
                    cooldown_hours=self.history_cooldown_hours,
                ):
                    continue

                # Rate limiting - YouTube API has quotas
                time.sleep(1)

                # Get comments
                comments = self._get_video_comments(
                    video_data['video_id'],
                    max_results=self.max_comments_per_video
                )

                # Filter comments that mention problems
                problem_keywords = self.config.get('problem_keywords', [])
                problem_comments = []

                for comment in comments:
                    # Check if comment discusses a problem
                    if any(kw.lower() in comment['text'].lower() for kw in problem_keywords):
                        if comment['likes'] >= min_engagement:
                            problem_comments.append(comment)

                # Skip videos with no relevant comments
                if not problem_comments:
                    continue

                # Build content
                content_parts = [
                    f"Video: {video_data['title']}",
                    f"Channel: {video_data['channel']}",
                    f"\nDescription: {video_data['description'][:300]}...",
                    "\n\n--- Comments with Problems ---"
                ]

                for comment in problem_comments[:10]:  # Limit to top 10
                    content_parts.append(
                        f"\n• {comment['author']} ({comment['likes']} likes): {comment['text']}"
                    )

                content = '\n'.join(content_parts)

                # Calculate engagement score
                total_likes = sum(c['likes'] for c in problem_comments)

                # Save discussion
                discussion = self._save_discussion(
                    url=video_data['url'],
                    external_id=video_data['video_id'],
                    title=f"YouTube: {video_data['title']}",
                    content=content,
                    author=video_data['channel'],
                    upvotes=total_likes,
                    comments_count=len(problem_comments),
                    posted_at=datetime.fromisoformat(video_data['published_at'].replace('Z', '+00:00'))
                )

                if discussion:
                    all_discussions.append(discussion)

            logger.info(f"Found {len(all_discussions)} discussions for '{label}'")

        logger.info(f"YouTube scraping complete: {len(all_discussions)} total discussions")
        return all_discussions


def main():
    """Test YouTube scraper"""
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        scraper = YouTubeScraper(db)
        result = scraper.run()
        print(f"\nScrape results: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
