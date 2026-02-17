"""
Reddit scraper using public JSON endpoints (no API key required)

Uses old.reddit.com/{subreddit}.json which returns public data without authentication.
Rate limited to ~30 requests/minute with proper User-Agent.
"""
import requests
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from agents.scrapers.base_agent import BaseScraper
from db.models import Discussion, SourceType
from config import config_loader
import logging

logger = logging.getLogger(__name__)


class RedditScraper(BaseScraper):
    """Scrapes Reddit for problem discussions using public JSON endpoints"""

    BASE_URL = "https://old.reddit.com"

    def __init__(self, db: Session):
        super().__init__(db, SourceType.REDDIT, "reddit")

        # Load configuration
        self.reddit_config = config_loader.get_reddit_config()
        self.subreddits = self.reddit_config.get('subreddits', [])
        self.problem_indicators = self.reddit_config.get('problem_indicators', [])
        self.history_cooldown_hours = int(self.reddit_config.get('history_cooldown_hours', 24))

        # Session with proper headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'StartupIdeasCollector/1.0 (research bot; educational project)',
            'Accept': 'application/json',
        })

        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 2.0  # 2 seconds between requests

    def _rate_limit(self):
        """Respect Reddit rate limits"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _fetch_json(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Fetch JSON from Reddit with rate limiting"""
        self._rate_limit()

        try:
            response = self.session.get(url, params=params, timeout=15)

            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
                response = self.session.get(url, params=params, timeout=15)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Reddit returned {response.status_code} for {url}")
                return None

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and decode entities"""
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', ' ', text)
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&#x27;', "'")
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the keywords"""
        if not text:
            return False
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in keywords)

    def _looks_like_problem_post(self, title: str, body: str, comments_count: int, score: int) -> bool:
        """
        Heuristic fallback for problem-like posts to increase recall.
        """
        text = f"{title} {body}".lower()
        patterns = [
            "how do i",
            "how can i",
            "anyone else",
            "struggling",
            "can't",
            "cannot",
            "doesn't work",
            "no way to",
            "looking for",
            "is there a",
        ]
        pattern_match = any(p in text for p in patterns)
        engagement_signal = comments_count >= 25 or score >= 80
        return pattern_match or engagement_signal

    def _fetch_comments(self, subreddit: str, post_id: str, max_comments: int = 15) -> str:
        """Fetch top comments for a post"""
        url = f"{self.BASE_URL}/r/{subreddit}/comments/{post_id}.json"
        data = self._fetch_json(url, params={'limit': max_comments, 'sort': 'top'})

        if not data or not isinstance(data, list) or len(data) < 2:
            return ""

        comments = []
        comment_listing = data[1].get('data', {}).get('children', [])

        for child in comment_listing:
            if child.get('kind') != 't1':
                continue

            comment = child.get('data', {})
            body = self._clean_html(comment.get('body', ''))
            score = comment.get('score', 0)

            if not body or len(body) < 20:
                continue

            comments.append(f"Comment (↑{score}): {body[:500]}")

            if len(comments) >= max_comments:
                break

        return "\n\n".join(comments)

    def _scrape_subreddit(self, sub_config: Dict) -> List[Discussion]:
        """Scrape a single subreddit for problem discussions"""
        name = sub_config['name']
        keywords = sub_config.get('keywords', [])
        min_upvotes = sub_config.get('min_upvotes', 10)
        max_posts = sub_config.get('max_posts', 15)
        effective_min_upvotes = max(5, int(min_upvotes * 0.6))

        # Combine subreddit-specific keywords with global problem indicators
        all_keywords = keywords + self.problem_indicators

        logger.info(f"Scraping r/{name} (min_upvotes={min_upvotes}, max_posts={max_posts})")
        discussions = []

        # Scrape top posts from the week and hot posts
        for sort_type in ['top', 'hot', 'new']:
            if len(discussions) >= max_posts:
                break

            url = f"{self.BASE_URL}/r/{name}/{sort_type}.json"
            params = {'limit': 50 if sort_type != 'new' else 30}
            if sort_type == 'top':
                params['t'] = 'month'

            data = self._fetch_json(url, params)
            if not data:
                continue

            posts = data.get('data', {}).get('children', [])
            logger.info(f"  r/{name}/{sort_type}: {len(posts)} posts fetched")

            for child in posts:
                if len(discussions) >= max_posts:
                    break

                post = child.get('data', {})

                # Skip stickied, removed, deleted
                if post.get('stickied') or post.get('removed_by_category') or post.get('selftext') == '[removed]':
                    continue

                title = post.get('title', '')
                selftext = self._clean_html(post.get('selftext', ''))
                score = post.get('score', 0)
                num_comments = post.get('num_comments', 0)

                # Filter by upvotes (relaxed threshold for better recall)
                if score < effective_min_upvotes:
                    continue

                # Check for problem keywords in title or content
                full_text = f"{title} {selftext}"
                keyword_match = self._contains_keywords(full_text, all_keywords)
                heuristic_match = self._looks_like_problem_post(title, selftext, num_comments, score)
                if not keyword_match and not heuristic_match:
                    continue

                # Get post ID
                post_id = post.get('id', '')
                post_url = f"https://reddit.com{post.get('permalink', '')}"

                # Skip if the same thread was recently scanned
                if self._track_thread_and_should_skip(
                    external_id=f"reddit_{post_id}",
                    url=post_url,
                    cooldown_hours=self.history_cooldown_hours,
                ):
                    continue

                # Fetch top comments for context
                comments_text = ""
                if num_comments > 0:
                    comments_text = self._fetch_comments(name, post_id, max_comments=10)

                # Build full content
                content = title
                if selftext:
                    content += f"\n\n{selftext}"
                if comments_text:
                    content += f"\n\n--- Top Comments ---\n{comments_text}"

                # Save discussion
                posted_at = datetime.fromtimestamp(post.get('created_utc', 0))

                discussion = self._save_discussion(
                    url=post_url,
                    external_id=f"reddit_{post_id}",
                    title=title,
                    content=content,
                    author=post.get('author', '[deleted]'),
                    upvotes=score,
                    comments_count=num_comments,
                    posted_at=posted_at
                )

                if discussion:
                    discussions.append(discussion)

        logger.info(f"  r/{name}: saved {len(discussions)} discussions")
        return discussions

    def _scrape_search(self, subreddit: str, query: str, min_upvotes: int = 10, limit: int = 10) -> List[Discussion]:
        """Search a subreddit for specific problem phrases"""
        url = f"{self.BASE_URL}/r/{subreddit}/search.json"
        params = {
            'q': query,
            'restrict_sr': 'on',
            'sort': 'top',
            't': 'month',
            'limit': limit
        }

        data = self._fetch_json(url, params)
        if not data:
            return []

        discussions = []
        posts = data.get('data', {}).get('children', [])

        for child in posts:
            post = child.get('data', {})
            score = post.get('score', 0)

            if score < min_upvotes:
                continue

            if post.get('stickied') or post.get('selftext') == '[removed]':
                continue

            title = post.get('title', '')
            selftext = self._clean_html(post.get('selftext', ''))
            post_id = post.get('id', '')
            post_url = f"https://reddit.com{post.get('permalink', '')}"
            num_comments = post.get('num_comments', 0)

            if self._track_thread_and_should_skip(
                external_id=f"reddit_{post_id}",
                url=post_url,
                cooldown_hours=self.history_cooldown_hours,
            ):
                continue

            # Fetch comments for high-engagement posts
            comments_text = ""
            if num_comments > 2:
                subreddit_name = post.get('subreddit', subreddit)
                comments_text = self._fetch_comments(subreddit_name, post_id, max_comments=8)

            content = title
            if selftext:
                content += f"\n\n{selftext}"
            if comments_text:
                content += f"\n\n--- Top Comments ---\n{comments_text}"

            posted_at = datetime.fromtimestamp(post.get('created_utc', 0))

            discussion = self._save_discussion(
                url=post_url,
                external_id=f"reddit_{post_id}",
                title=title,
                content=content,
                author=post.get('author', '[deleted]'),
                upvotes=score,
                comments_count=num_comments,
                posted_at=posted_at
            )

            if discussion:
                discussions.append(discussion)

        return discussions

    def scrape(self, limit_per_subreddit: Optional[int] = None) -> List[Discussion]:
        """Scrape all configured subreddits for problem discussions."""
        all_discussions = []

        # Scrape configured subreddits
        for sub_config in self.subreddits:
            try:
                effective_config = dict(sub_config)
                if limit_per_subreddit is not None:
                    configured_max = effective_config.get('max_posts', limit_per_subreddit)
                    effective_config['max_posts'] = min(configured_max, limit_per_subreddit)

                discussions = self._scrape_subreddit(effective_config)
                all_discussions.extend(discussions)
            except Exception as e:
                logger.error(f"Error scraping r/{sub_config['name']}: {e}")
                continue

        # Also search for specific problem phrases across key subreddits
        search_phrases = ["I wish there was", "why is there no", "wish someone would make"]
        search_subreddits = ["AskReddit", "technology", "productivity"]

        for subreddit in search_subreddits:
            for phrase in search_phrases:
                try:
                    found = self._scrape_search(
                        subreddit=subreddit,
                        query=f'"{phrase}"',
                        min_upvotes=20,
                        limit=5
                    )
                    all_discussions.extend(found)
                except Exception as e:
                    logger.error(f"Error searching r/{subreddit} for '{phrase}': {e}")
                    continue

        logger.info(f"Total Reddit discussions saved: {len(all_discussions)}")
        return all_discussions


def main():
    """Test Reddit scraper"""
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        scraper = RedditScraper(db)
        result = scraper.run()
        print(f"\nScrape results: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
