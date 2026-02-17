"""
Tavily Active Search Agent - actively searches the web for problem discussions

Uses Tavily API to find complaints, frustrations and pain points across the web,
including Reddit, G2, Trustpilot, forums, and review sites.
"""
import time
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from agents.scrapers.base_agent import BaseScraper
from db.models import Discussion, SourceType
from config import settings, config_loader
import logging

logger = logging.getLogger(__name__)

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False


class TavilySearchScraper(BaseScraper):
    """Uses Tavily to actively search for problem discussions across the web"""

    def __init__(self, db: Session):
        super().__init__(db, SourceType.TAVILY, "tavily")

        self.tavily_config = config_loader.get_tavily_config()
        self.max_results = self.tavily_config.get('max_results_per_query', 5)
        self.search_depth = self.tavily_config.get('search_depth', 'basic')
        self.search_queries = self.tavily_config.get('search_queries', [])

        self.client = None
        if TAVILY_AVAILABLE and settings.tavily_api_key:
            try:
                self.client = TavilyClient(api_key=settings.tavily_api_key)
                logger.info("Tavily client initialized for active search")
            except Exception as e:
                logger.warning(f"Failed to initialize Tavily client: {e}")

    def _search_and_save(self, query: str, label: str) -> List[Discussion]:
        """Run a Tavily search and save results as discussions"""
        if not self.client:
            return []

        try:
            logger.info(f"Tavily search [{label}]: {query[:80]}...")
            response = self.client.search(
                query=query,
                search_depth=self.search_depth,
                max_results=self.max_results,
                include_answer=True,
            )
        except Exception as e:
            logger.error(f"Tavily search failed for '{label}': {e}")
            return []

        discussions = []
        results = response.get('results', [])

        # Also use the synthesized answer if available
        answer = response.get('answer', '')
        if answer and len(answer) > 100:
            thread_key = f"tavily_answer_{label}"
            if not self._track_thread_and_should_skip(
                external_id=thread_key,
                url=f"tavily://answer/{label}",
                cooldown_hours=12,
            ):
                discussion = self._save_discussion(
                    url=f"tavily://answer/{label}/{int(time.time())}",
                    external_id=thread_key,
                    title=f"[Tavily Search] {label.replace('_', ' ').title()}: {query[:80]}",
                    content=f"Search Query: {query}\n\nSynthesized Answer:\n{answer}\n\n"
                            + "\n\n".join(
                                f"Source: {r.get('title', '')}\nURL: {r.get('url', '')}\n{r.get('content', '')[:400]}"
                                for r in results[:3]
                            ),
                    author="tavily_search",
                    upvotes=10,
                    comments_count=len(results),
                    posted_at=datetime.utcnow(),
                )
                if discussion:
                    discussions.append(discussion)

        # Save individual high-quality results
        for result in results:
            url = result.get('url', '')
            title = result.get('title', '')
            content = result.get('content', '')
            score = result.get('score', 0)

            if not url or not title or len(content) < 100:
                continue

            # Only save results with decent relevance score
            if score < 0.3:
                continue

            external_id = f"tavily_{hash(url) % 10**10}"

            if self._track_thread_and_should_skip(
                external_id=external_id,
                url=url,
                cooldown_hours=48,
            ):
                continue

            full_content = f"[Found via Tavily search: {query}]\n\n{title}\n\n{content}"

            discussion = self._save_discussion(
                url=url,
                external_id=external_id,
                title=f"[Web] {title[:200]}",
                content=full_content,
                author="tavily_search",
                upvotes=max(5, int(score * 20)),
                comments_count=0,
                posted_at=datetime.utcnow(),
            )
            if discussion:
                discussions.append(discussion)

        return discussions

    def scrape(self, limit: Optional[int] = None) -> List[Discussion]:
        """Run all configured search queries"""
        if not self.client:
            logger.warning("Tavily client not available — skipping")
            return []

        all_discussions = []
        queries = self.search_queries
        if limit:
            queries = queries[:limit]

        for query_cfg in queries:
            query = query_cfg.get('query', '')
            label = query_cfg.get('label', 'search')
            if not query:
                continue

            found = self._search_and_save(query, label)
            all_discussions.extend(found)
            time.sleep(1)  # Rate limiting between queries

        logger.info(f"Tavily search: {len(all_discussions)} discussions saved")
        return all_discussions
