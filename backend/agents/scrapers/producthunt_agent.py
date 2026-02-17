"""
Product Hunt scraper

Scrapes products and comments from Product Hunt
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


class ProductHuntScraper(BaseScraper):
    """Scrapes Product Hunt for problem discussions"""

    def __init__(self, db: Session):
        super().__init__(db, SourceType.PRODUCTHUNT, "producthunt")

        # Load configuration
        self.config = config_loader.get_producthunt_config()
        self.api_token = settings.producthunt_api_token if hasattr(settings, 'producthunt_api_token') else None
        self.max_products = self.config.get('max_products', 20)
        self.min_upvotes = self.config.get('min_upvotes', 10)

        # API endpoints
        self.graphql_url = "https://api.producthunt.com/v2/api/graphql"
        self.rest_url = "https://api.producthunt.com/v1"

        # Headers
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'StartupIdeasCollector/1.0'
        }

        if self.api_token:
            self.headers['Authorization'] = f'Bearer {self.api_token}'
            logger.info("Product Hunt API token configured")
        else:
            logger.warning("No Product Hunt API token - will use public scraping")

    def _graphql_query(self, query: str, variables: Optional[Dict] = None) -> Optional[Dict]:
        """
        Execute GraphQL query
        """
        if not self.api_token:
            logger.warning("GraphQL requires API token")
            return None

        try:
            response = requests.post(
                self.graphql_url,
                json={'query': query, 'variables': variables or {}},
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"GraphQL request failed: {e}")
            return None

    def _fetch_daily_posts(self, days_ago: int = 0) -> List[Dict[str, Any]]:
        """
        Fetch posts from specific day using GraphQL
        """
        if not self.api_token:
            return self._scrape_public_posts()

        # Calculate date
        target_date = (datetime.utcnow() - timedelta(days=days_ago)).strftime('%Y-%m-%d')

        query = """
        query($date: String!) {
          posts(order: VOTES, postedAfter: $date, postedBefore: $date) {
            edges {
              node {
                id
                name
                tagline
                description
                votesCount
                commentsCount
                url
                website
                createdAt
                user {
                  username
                }
                topics {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """

        result = self._graphql_query(query, {'date': target_date})
        if not result or 'data' not in result:
            return []

        posts_data = []
        posts = result['data'].get('posts', {}).get('edges', [])

        for edge in posts[:self.max_products]:
            post = edge['node']
            posts_data.append({
                'id': post['id'],
                'name': post['name'],
                'tagline': post['tagline'],
                'description': post.get('description', ''),
                'url': post['url'],
                'website': post.get('website', ''),
                'upvotes': post['votesCount'],
                'comments_count': post['commentsCount'],
                'author': post['user']['username'],
                'posted_at': datetime.fromisoformat(post['createdAt'].replace('Z', '+00:00'))
            })

        return posts_data

    def _fetch_post_comments(self, post_id: str) -> List[Dict[str, Any]]:
        """
        Fetch comments for a specific post
        """
        if not self.api_token:
            return []

        query = """
        query($postId: ID!) {
          post(id: $postId) {
            comments(first: 10) {
              edges {
                node {
                  id
                  body
                  votesCount
                  user {
                    username
                  }
                  createdAt
                }
              }
            }
          }
        }
        """

        result = self._graphql_query(query, {'postId': post_id})
        if not result or 'data' not in result:
            return []

        comments_data = []
        comments = result['data'].get('post', {}).get('comments', {}).get('edges', [])

        for edge in comments:
            comment = edge['node']
            comments_data.append({
                'body': comment['body'],
                'author': comment['user']['username'],
                'upvotes': comment['votesCount']
            })

        return comments_data

    def _scrape_public_posts(self) -> List[Dict[str, Any]]:
        """
        Scrape public Product Hunt page (fallback when no API token)
        """
        logger.info("Scraping Product Hunt public page...")
        posts_data = []

        try:
            from bs4 import BeautifulSoup

            url = "https://www.producthunt.com/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find product cards
            # Note: PH structure changes frequently, this is fragile
            products = soup.find_all('div', attrs={'data-test': 'post-item'}, limit=self.max_products)

            if not products:
                # Try alternative selector
                products = soup.find_all('article', limit=self.max_products)

            logger.info(f"Found {len(products)} products")

            for product in products:
                try:
                    title_elem = product.find('h3') or product.find('h2')
                    if not title_elem:
                        continue

                    name = title_elem.get_text(strip=True)

                    # Get link
                    link = product.find('a')
                    product_url = link.get('href', '') if link else ''
                    if product_url and not product_url.startswith('http'):
                        product_url = 'https://www.producthunt.com' + product_url

                    # Get tagline
                    tagline_elem = product.find('p')
                    tagline = tagline_elem.get_text(strip=True) if tagline_elem else ""

                    # Extract upvotes (usually in a span or button)
                    upvotes = 0
                    upvote_elem = product.find(text=lambda x: x and x.isdigit())
                    if upvote_elem:
                        try:
                            upvotes = int(upvote_elem)
                        except:
                            pass

                    posts_data.append({
                        'id': product_url.split('/')[-1] if product_url else str(hash(name)),
                        'name': name,
                        'tagline': tagline,
                        'description': tagline,
                        'url': product_url,
                        'upvotes': upvotes,
                        'comments_count': 0,
                        'author': 'unknown',
                        'posted_at': datetime.utcnow()
                    })

                except Exception as e:
                    logger.warning(f"Failed to parse product: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to scrape Product Hunt: {e}")

        return posts_data

    def scrape(self) -> List[Discussion]:
        """
        Scrape Product Hunt for problem discussions
        """
        logger.info("Starting Product Hunt scraping...")
        all_discussions = []

        # Fetch posts from today and yesterday
        days_to_check = self.config.get('days_to_check', 2)

        for day in range(days_to_check):
            logger.info(f"Fetching posts from {day} days ago...")

            posts = self._fetch_daily_posts(days_ago=day)

            for post_data in posts:
                # Filter by upvotes
                if post_data['upvotes'] < self.min_upvotes:
                    continue

                # Build content from product description
                content_parts = [
                    f"Product: {post_data['name']}",
                    f"Tagline: {post_data['tagline']}",
                ]

                if post_data.get('description'):
                    content_parts.append(f"\nDescription: {post_data['description']}")

                # Fetch comments if API token available
                if self.api_token and post_data.get('comments_count', 0) > 0:
                    time.sleep(0.5)  # Rate limiting
                    comments = self._fetch_post_comments(post_data['id'])

                    if comments:
                        content_parts.append("\n\n--- Comments (Problems & Feedback) ---")
                        for comment in comments:
                            # Only include comments that mention problems
                            if any(kw in comment['body'].lower() for kw in ['problem', 'issue', 'missing', 'wish', 'need', 'lack']):
                                content_parts.append(f"\n- {comment['author']}: {comment['body']}")

                content = '\n'.join(content_parts)

                # Check for problem keywords
                keywords = self.config.get('problem_keywords', [])
                if keywords and not any(kw.lower() in content.lower() for kw in keywords):
                    continue

                # Save discussion
                discussion = self._save_discussion(
                    url=post_data['url'],
                    external_id=post_data['id'],
                    title=f"{post_data['name']}: {post_data['tagline']}",
                    content=content,
                    author=post_data['author'],
                    upvotes=post_data['upvotes'],
                    comments_count=post_data.get('comments_count', 0),
                    posted_at=post_data['posted_at']
                )

                if discussion:
                    all_discussions.append(discussion)

            logger.info(f"Found {len(all_discussions)} discussions from day {day}")

            # Rate limiting between days
            time.sleep(1)

        logger.info(f"Product Hunt scraping complete: {len(all_discussions)} total discussions")
        return all_discussions


def main():
    """Test Product Hunt scraper"""
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        scraper = ProductHuntScraper(db)
        result = scraper.run()
        print(f"\nScrape results: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
