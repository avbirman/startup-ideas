"""
Indie Hackers scraper

Scrapes posts and discussions from Indie Hackers community
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from agents.scrapers.base_agent import BaseScraper
from db.models import Discussion, SourceType
from config import config_loader
import logging
import time

logger = logging.getLogger(__name__)


class IndieHackersScraper(BaseScraper):
    """Scrapes Indie Hackers for problem discussions"""

    def __init__(self, db: Session):
        super().__init__(db, SourceType.INDIEHACKERS, "indiehackers")

        # Load configuration
        self.config = config_loader.get_indiehackers_config()
        self.base_url = "https://www.indiehackers.com"
        self.max_posts = self.config.get('max_posts', 20)
        self.min_upvotes = self.config.get('min_upvotes', 5)

        # Headers to mimic browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def _fetch_posts(self, section: str = "newest") -> List[Dict[str, Any]]:
        """
        Fetch posts from Indie Hackers
        Sections: 'newest', 'popular', 'top'
        """
        posts_data = []

        try:
            url = f"{self.base_url}/posts/{section}"
            logger.info(f"Fetching Indie Hackers posts from: {url}")

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find post cards (Indie Hackers uses specific class names)
            # Note: This is fragile and may break if they change their HTML structure
            posts = soup.find_all('div', class_='post', limit=self.max_posts)

            if not posts:
                # Try alternative selector
                posts = soup.find_all('article', limit=self.max_posts)

            logger.info(f"Found {len(posts)} posts on the page")

            for post in posts:
                try:
                    # Extract post data
                    title_elem = post.find('h3') or post.find('h2')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)

                    # Get link
                    link_elem = title_elem.find('a') if title_elem.find('a') else post.find('a')
                    if not link_elem:
                        continue

                    post_url = link_elem.get('href', '')
                    if post_url and not post_url.startswith('http'):
                        post_url = self.base_url + post_url

                    # Get snippet/content
                    content_elem = post.find('p')
                    content = content_elem.get_text(strip=True) if content_elem else ""

                    # Get metadata (upvotes, comments)
                    upvotes = 0
                    comments_count = 0

                    # Try to find upvote count
                    upvote_elem = post.find(text=lambda x: x and 'upvote' in x.lower())
                    if upvote_elem:
                        try:
                            upvotes = int(''.join(filter(str.isdigit, upvote_elem)))
                        except:
                            pass

                    # Try to find comment count
                    comment_elem = post.find(text=lambda x: x and 'comment' in x.lower())
                    if comment_elem:
                        try:
                            comments_count = int(''.join(filter(str.isdigit, comment_elem)))
                        except:
                            pass

                    # Get author
                    author_elem = post.find('a', class_='user') or post.find(text=lambda x: x and '@' in str(x))
                    author = author_elem.get_text(strip=True) if author_elem else "unknown"

                    post_data = {
                        'title': title,
                        'url': post_url,
                        'content': content,
                        'author': author,
                        'upvotes': upvotes,
                        'comments_count': comments_count,
                        'posted_at': datetime.utcnow()  # IH doesn't show exact dates easily
                    }

                    posts_data.append(post_data)

                except Exception as e:
                    logger.warning(f"Failed to parse post: {e}")
                    continue

        except requests.RequestException as e:
            logger.error(f"Failed to fetch Indie Hackers posts: {e}")
        except Exception as e:
            logger.error(f"Error parsing Indie Hackers: {e}")

        return posts_data

    def _fetch_post_details(self, post_url: str) -> str:
        """
        Fetch full post content and comments
        """
        try:
            response = requests.get(post_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Get main post content
            content_parts = []

            # Post body
            body = soup.find('div', class_='post-body') or soup.find('article')
            if body:
                content_parts.append(body.get_text(strip=True))

            # Top comments (limit to first 5)
            comments = soup.find_all('div', class_='comment', limit=5)
            if comments:
                content_parts.append("\n\n--- Top Comments ---")
                for comment in comments:
                    comment_text = comment.get_text(strip=True)
                    if comment_text:
                        content_parts.append(f"\n- {comment_text}")

            return '\n'.join(content_parts)

        except Exception as e:
            logger.warning(f"Failed to fetch post details from {post_url}: {e}")
            return ""

    def scrape(self) -> List[Discussion]:
        """
        Scrape Indie Hackers for problem discussions
        """
        logger.info("Starting Indie Hackers scraping...")
        all_discussions = []

        sections = self.config.get('sections', ['newest'])

        for section in sections:
            logger.info(f"Scraping {section} posts...")

            posts = self._fetch_posts(section)

            for post_data in posts:
                # Filter by upvotes
                if post_data['upvotes'] < self.min_upvotes:
                    continue

                # Check if contains problem keywords
                keywords = self.config.get('problem_keywords', [])
                text_to_check = f"{post_data['title']} {post_data['content']}".lower()

                if keywords and not any(kw.lower() in text_to_check for kw in keywords):
                    continue

                # Fetch full content
                full_content = post_data['content']
                if post_data['url']:
                    time.sleep(1)  # Be polite
                    detailed_content = self._fetch_post_details(post_data['url'])
                    if detailed_content:
                        full_content = detailed_content

                # Extract post ID from URL
                external_id = post_data['url'].split('/')[-1] if post_data['url'] else str(hash(post_data['title']))

                # Save discussion
                discussion = self._save_discussion(
                    url=post_data['url'],
                    external_id=external_id,
                    title=post_data['title'],
                    content=full_content,
                    author=post_data['author'],
                    upvotes=post_data['upvotes'],
                    comments_count=post_data['comments_count'],
                    posted_at=post_data['posted_at']
                )

                if discussion:
                    all_discussions.append(discussion)

            logger.info(f"Found {len(all_discussions)} discussions from {section}")

            # Rate limiting between sections
            time.sleep(2)

        logger.info(f"Indie Hackers scraping complete: {len(all_discussions)} total discussions")
        return all_discussions


def main():
    """Test Indie Hackers scraper"""
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        scraper = IndieHackersScraper(db)
        result = scraper.run()
        print(f"\nScrape results: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
