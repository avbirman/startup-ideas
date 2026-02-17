"""
Quora scraper

Scrapes questions and answers from Quora
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from agents.scrapers.base_agent import BaseScraper
from db.models import Discussion, SourceType
from config import config_loader
import logging
import time

logger = logging.getLogger(__name__)


class QuoraScraper(BaseScraper):
    """Scrapes Quora for problem discussions"""

    def __init__(self, db: Session):
        super().__init__(db, SourceType.QUORA, "quora")

        # Load configuration
        self.config = config_loader.get_quora_config()
        self.topics = self.config.get('topics', [])
        self.max_questions = self.config.get('max_questions', 20)
        self.min_upvotes = self.config.get('min_upvotes', 5)

        # Headers to mimic browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        }

    def _fetch_topic_questions(self, topic: str) -> List[Dict[str, Any]]:
        """
        Fetch questions from a specific Quora topic
        """
        questions_data = []

        try:
            # Quora topic URL format
            url = f"https://www.quora.com/topic/{topic}"
            logger.info(f"Fetching Quora questions from topic: {topic}")

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find question links
            # Note: Quora's HTML structure changes frequently
            question_links = soup.find_all('a', limit=self.max_questions)

            for link in question_links:
                href = link.get('href', '')

                # Filter for question URLs
                if not href or not ('/' in href and len(href) > 10):
                    continue

                # Get question text from link
                question_text = link.get_text(strip=True)
                if not question_text or len(question_text) < 10:
                    continue

                # Build full URL
                question_url = href if href.startswith('http') else f"https://www.quora.com{href}"

                # Check if it looks like a question
                if any(q in question_text.lower() for q in ['how', 'what', 'why', 'which', 'where', 'when', 'who', 'can', 'should', 'is', 'are', 'does']):
                    questions_data.append({
                        'question': question_text,
                        'url': question_url,
                        'topic': topic
                    })

            logger.info(f"Found {len(questions_data)} questions in topic '{topic}'")

        except requests.RequestException as e:
            logger.error(f"Failed to fetch Quora topic '{topic}': {e}")
        except Exception as e:
            logger.error(f"Error parsing Quora topic '{topic}': {e}")

        return questions_data

    def _fetch_question_details(self, question_url: str) -> Dict[str, Any]:
        """
        Fetch full question details and top answers
        """
        try:
            response = requests.get(question_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Get question description if available
            description = ""
            desc_elem = soup.find('div', class_='q-text')
            if desc_elem:
                description = desc_elem.get_text(strip=True)

            # Get top answers (limit to 3)
            answers = []
            answer_elems = soup.find_all('div', class_='Answer', limit=3)

            if not answer_elems:
                # Try alternative selector
                answer_elems = soup.find_all('div', attrs={'data-test-id': 'answer'}, limit=3)

            for answer in answer_elems:
                answer_text = answer.get_text(strip=True)
                if answer_text and len(answer_text) > 20:
                    answers.append(answer_text[:500])  # Limit length

            # Try to get upvote count (difficult without API)
            upvotes = 0

            return {
                'description': description,
                'answers': answers,
                'upvotes': upvotes
            }

        except Exception as e:
            logger.warning(f"Failed to fetch question details from {question_url}: {e}")
            return {'description': '', 'answers': [], 'upvotes': 0}

    def scrape(self) -> List[Discussion]:
        """
        Scrape Quora for problem discussions
        """
        logger.info("Starting Quora scraping...")
        all_discussions = []

        for topic in self.topics:
            logger.info(f"Processing topic: {topic}")

            questions = self._fetch_topic_questions(topic)

            for q_data in questions:
                # Filter by problem keywords
                keywords = self.config.get('problem_keywords', [])
                if keywords and not any(kw.lower() in q_data['question'].lower() for kw in keywords):
                    continue

                # Fetch question details
                time.sleep(1)  # Be polite to Quora
                details = self._fetch_question_details(q_data['url'])

                # Build content
                content_parts = [
                    f"Question: {q_data['question']}",
                ]

                if details['description']:
                    content_parts.append(f"\nDescription: {details['description']}")

                if details['answers']:
                    content_parts.append("\n\n--- Top Answers ---")
                    for i, answer in enumerate(details['answers'], 1):
                        content_parts.append(f"\nAnswer {i}: {answer}")

                content = '\n'.join(content_parts)

                # Extract question ID from URL
                external_id = q_data['url'].split('/')[-1] if q_data['url'] else str(hash(q_data['question']))

                # Save discussion
                discussion = self._save_discussion(
                    url=q_data['url'],
                    external_id=external_id,
                    title=q_data['question'],
                    content=content,
                    author="quora_user",  # Can't easily get author without API
                    upvotes=details['upvotes'],
                    comments_count=len(details['answers']),
                    posted_at=datetime.utcnow()
                )

                if discussion:
                    all_discussions.append(discussion)

            logger.info(f"Found {len(all_discussions)} discussions from topic '{topic}'")

            # Rate limiting between topics
            time.sleep(2)

        logger.info(f"Quora scraping complete: {len(all_discussions)} total discussions")
        return all_discussions


def main():
    """Test Quora scraper"""
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        scraper = QuoraScraper(db)
        result = scraper.run()
        print(f"\nScrape results: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
