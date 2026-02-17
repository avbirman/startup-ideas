"""
Twitter/X scraper using tweepy library

Searches for tweets discussing problems and frustrations
"""
import tweepy
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from agents.scrapers.base_agent import BaseScraper
from db.models import Discussion, SourceType
from config import settings, config_loader
import logging

logger = logging.getLogger(__name__)


class TwitterScraper(BaseScraper):
    """Scrapes Twitter/X for problem discussions"""

    def __init__(self, db: Session):
        super().__init__(db, SourceType.TWITTER, "twitter")

        # Initialize Twitter API client
        try:
            self.client = tweepy.Client(
                bearer_token=settings.twitter_bearer_token,
                wait_on_rate_limit=True
            )
            logger.info("Twitter API client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {e}")
            self.client = None

        # Load configuration
        self.config = config_loader.get_twitter_config()
        self.search_queries = self.config.get('search_queries', [])
        self.max_results = self.config.get('max_results_per_query', 10)

    def _search_tweets(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search tweets by query
        Returns list of tweet data
        """
        if not self.client:
            logger.error("Twitter client not initialized")
            return []

        tweets_data = []

        try:
            # Search recent tweets
            # Free tier: last 7 days, max 10 per request
            response = self.client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=['created_at', 'public_metrics', 'author_id', 'conversation_id'],
                expansions=['author_id'],
                user_fields=['username', 'name']
            )

            if not response.data:
                logger.info(f"No tweets found for query: {query}")
                return tweets_data

            # Create user lookup
            users = {}
            if response.includes and 'users' in response.includes:
                for user in response.includes['users']:
                    users[user.id] = user.username

            for tweet in response.data:
                tweet_data = {
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at,
                    'author': users.get(tweet.author_id, 'unknown'),
                    'likes': tweet.public_metrics.get('like_count', 0),
                    'retweets': tweet.public_metrics.get('retweet_count', 0),
                    'replies': tweet.public_metrics.get('reply_count', 0),
                    'url': f"https://twitter.com/i/web/status/{tweet.id}"
                }
                tweets_data.append(tweet_data)

        except tweepy.errors.TweepyException as e:
            logger.error(f"Twitter API error for query '{query}': {e}")
        except Exception as e:
            logger.error(f"Error searching tweets: {e}")

        return tweets_data

    def _get_thread_context(self, tweet_id: str, max_replies: int = 5) -> str:
        """
        Get conversation thread for context
        Note: This requires higher API tier, so we skip for free tier
        """
        # For free tier, we just return the original tweet
        # Upgrade to Basic tier to get full conversations
        return ""

    def scrape(self) -> List[Discussion]:
        """
        Scrape Twitter for problem discussions
        """
        logger.info("Starting Twitter scraping...")
        all_discussions = []

        if not self.client:
            logger.error("Twitter client not available - check API credentials")
            return all_discussions

        for search_query in self.search_queries:
            query = search_query.get('query', '')
            label = search_query.get('label', 'general')
            min_engagement = search_query.get('min_engagement', 5)

            logger.info(f"Searching Twitter: {label} - '{query}'")

            tweets = self._search_tweets(query, max_results=self.max_results)

            for tweet_data in tweets:
                # Calculate total engagement
                engagement = (
                    tweet_data['likes'] +
                    tweet_data['retweets'] * 2 +  # Retweets count more
                    tweet_data['replies'] * 3      # Replies count most
                )

                # Filter by engagement
                if engagement < min_engagement:
                    continue

                # Build content
                content = tweet_data['text']

                # Could add thread context here if we had higher API tier
                thread_context = self._get_thread_context(tweet_data['id'])
                if thread_context:
                    content += f"\n\n--- Thread Context ---\n{thread_context}"

                # Save discussion
                discussion = self._save_discussion(
                    url=tweet_data['url'],
                    external_id=str(tweet_data['id']),
                    title=tweet_data['text'][:100] + "..." if len(tweet_data['text']) > 100 else tweet_data['text'],
                    content=content,
                    author=tweet_data['author'],
                    upvotes=engagement,  # Use total engagement as "upvotes"
                    comments_count=tweet_data['replies'],
                    posted_at=tweet_data['created_at']
                )

                if discussion:
                    all_discussions.append(discussion)

            logger.info(f"Found {len(all_discussions)} discussions for '{label}'")

        logger.info(f"Twitter scraping complete: {len(all_discussions)} total discussions")
        return all_discussions


def main():
    """Test Twitter scraper"""
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        scraper = TwitterScraper(db)
        result = scraper.run()
        print(f"\nScrape results: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
