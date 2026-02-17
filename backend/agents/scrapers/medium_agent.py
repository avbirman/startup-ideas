"""
Medium scraper using RSS feeds

Scrapes articles from Medium tags via RSS
"""
import requests
import feedparser
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from agents.scrapers.base_agent import BaseScraper
from db.models import Discussion, SourceType
from config import config_loader
import logging
import time

logger = logging.getLogger(__name__)


class MediumScraper(BaseScraper):
    """Scrapes Medium articles for problem discussions"""

    def __init__(self, db: Session):
        super().__init__(db, SourceType.MEDIUM, "medium")

        # Load configuration
        self.config = config_loader.get_medium_config()
        self.tags = self.config.get('tags', [])
        self.max_articles = self.config.get('max_articles', 20)
        self.history_cooldown_hours = int(self.config.get('history_cooldown_hours', 48))

    def _fetch_tag_articles(self, tag: str) -> List[Dict[str, Any]]:
        """
        Fetch articles from Medium tag via RSS feed
        Medium RSS format: https://medium.com/feed/tag/{tag}
        """
        articles = []

        try:
            # Medium RSS feed URL
            rss_url = f"https://medium.com/feed/tag/{tag}"
            logger.info(f"Fetching Medium articles from tag: {tag}")

            # Parse RSS feed
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                logger.warning(f"No articles found for tag '{tag}'")
                return articles

            for entry in feed.entries[:self.max_articles]:
                try:
                    # Extract article data
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    summary = entry.get('summary', '')

                    # Get author
                    author = entry.get('author', 'unknown')

                    # Get published date
                    published = entry.get('published_parsed')
                    if published:
                        published_at = datetime(*published[:6])
                    else:
                        published_at = datetime.utcnow()

                    # Clean up summary (remove HTML tags)
                    from bs4 import BeautifulSoup
                    summary_clean = BeautifulSoup(summary, 'html.parser').get_text(strip=True)

                    articles.append({
                        'title': title,
                        'url': link,
                        'summary': summary_clean[:500],  # Limit length
                        'author': author,
                        'published_at': published_at,
                        'tag': tag
                    })

                except Exception as e:
                    logger.warning(f"Failed to parse article: {e}")
                    continue

            logger.info(f"Found {len(articles)} articles for tag '{tag}'")

        except Exception as e:
            logger.error(f"Failed to fetch Medium tag '{tag}': {e}")

        return articles

    def _fetch_article_content(self, url: str) -> str:
        """
        Attempt to fetch full article content
        Note: Medium often requires JavaScript, so this may not work well
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Try to find article content
            article = soup.find('article')
            if article:
                paragraphs = article.find_all('p')
                content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs[:10]])
                return content

        except Exception as e:
            logger.debug(f"Could not fetch full content from {url}: {e}")

        return ""

    def scrape(self) -> List[Discussion]:
        """
        Scrape Medium articles for problem discussions
        """
        logger.info("Starting Medium scraping...")
        all_discussions = []

        for tag in self.tags:
            logger.info(f"Processing tag: {tag}")

            articles = self._fetch_tag_articles(tag)

            for article_data in articles:
                article_url = article_data['url']
                external_id = article_url.split('/')[-1].split('-')[-1] if article_url else str(hash(article_data['title']))
                if self._track_thread_and_should_skip(
                    external_id=external_id,
                    url=article_url,
                    cooldown_hours=self.history_cooldown_hours,
                ):
                    continue

                # Filter by problem keywords
                keywords = self.config.get('problem_keywords', [])
                text_to_check = f"{article_data['title']} {article_data['summary']}".lower()

                if keywords and not any(kw.lower() in text_to_check for kw in keywords):
                    continue

                # Use summary as content (fetching full content often fails due to JS)
                content = f"{article_data['summary']}"

                # Optionally try to fetch more content
                if self.config.get('fetch_full_content', False):
                    time.sleep(1)
                    full_content = self._fetch_article_content(article_data['url'])
                    if full_content:
                        content = full_content

                # Extract article ID from URL
                # Save discussion
                discussion = self._save_discussion(
                    url=article_url,
                    external_id=external_id,
                    title=article_data['title'],
                    content=content,
                    author=article_data['author'],
                    upvotes=0,  # RSS doesn't provide clap counts
                    comments_count=0,
                    posted_at=article_data['published_at']
                )

                if discussion:
                    all_discussions.append(discussion)

            logger.info(f"Found {len(all_discussions)} discussions from tag '{tag}'")

            # Rate limiting between tags
            time.sleep(2)

        logger.info(f"Medium scraping complete: {len(all_discussions)} total discussions")
        return all_discussions


def main():
    """Test Medium scraper"""
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        scraper = MediumScraper(db)
        result = scraper.run()
        print(f"\nScrape results: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
