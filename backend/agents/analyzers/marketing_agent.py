"""
Marketing Agent - market research and go-to-market strategy analysis

Uses Tavily API for real-time competitor research and Claude for strategic analysis
"""
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from agents.analyzers.base_analyzer import BaseAnalyzer
from db.models import Problem, MarketingAnalysis
from config import settings
import logging

# Tavily API import
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    logging.warning("Tavily not available - competitor search will be limited")

logger = logging.getLogger(__name__)


class MarketingAgent(BaseAnalyzer):
    """Analyzes market opportunity and competitive landscape"""

    def __init__(self, db: Session):
        super().__init__()
        self.db = db

        # Initialize Tavily client if available
        self.tavily_client = None
        if TAVILY_AVAILABLE and settings.tavily_api_key:
            try:
                self.tavily_client = TavilyClient(api_key=settings.tavily_api_key)
                logger.info("Tavily API client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Tavily client: {e}")

    def _search_competitors(self, problem_statement: str, target_audience: str) -> List[Dict[str, Any]]:
        """
        Search for competitors using Tavily API
        Returns list of competitor information
        """
        competitors = []

        if not self.tavily_client:
            logger.warning("Tavily client not available, skipping competitor search")
            return competitors

        try:
            # Search query 1: Direct competitors
            search_query_1 = f"best software tools for {problem_statement[:100]}"
            logger.info(f"Searching competitors: {search_query_1}")

            response_1 = self.tavily_client.search(
                query=search_query_1,
                search_depth="basic",
                max_results=5
            )

            # Search query 2: Alternative solutions
            search_query_2 = f"{target_audience} solutions for {problem_statement[:100]}"
            logger.info(f"Searching alternatives: {search_query_2}")

            response_2 = self.tavily_client.search(
                query=search_query_2,
                search_depth="basic",
                max_results=5
            )

            # Process results
            for result in response_1.get('results', []) + response_2.get('results', []):
                competitor_info = {
                    'name': result.get('title', ''),
                    'url': result.get('url', ''),
                    'description': result.get('content', '')[:300]  # Limit description length
                }
                competitors.append(competitor_info)

            logger.info(f"Found {len(competitors)} potential competitors")

        except Exception as e:
            logger.error(f"Error searching for competitors: {e}")

        return competitors[:10]  # Limit to top 10

    def analyze_market(self, problem: Problem) -> Optional[MarketingAnalysis]:
        """
        Perform comprehensive market analysis
        Returns MarketingAnalysis object if successful
        """
        logger.info(f"Analyzing market for problem: {problem.problem_statement[:50]}...")

        # Step 1: Search for competitors
        competitors = self._search_competitors(
            problem.problem_statement,
            problem.target_audience or "general users"
        )

        # Step 2: Prepare competitor context for Claude
        competitor_context = "\n".join([
            f"- {c['name']}: {c['description']}"
            for c in competitors[:5]
        ]) if competitors else "No competitors found via search"

        # Step 3: Deep analysis with Claude
        analysis_prompt = f"""Analyze the market opportunity for this problem and generate a comprehensive market analysis.

IMPORTANT: Provide ALL output in Russian language (market_description, positioning, pricing_model, target_segments, gtm_strategy fields, etc.)

**Problem Statement:** {problem.problem_statement}

**Target Audience:** {problem.target_audience or "Not specified"}

**Problem Severity:** {problem.severity}/10

**Existing Solutions Found:**
{competitor_context}

**Your Current Solutions Analysis:**
{problem.current_solutions or "Not specified"}

**Why Current Solutions Fail:**
{problem.why_they_fail or "Not specified"}

Provide your analysis in this EXACT JSON format (all text fields in Russian):
{{
    "tam": "Total Addressable Market estimate with reasoning (e.g., '$5.2B - global invoicing software market')",
    "sam": "Serviceable Addressable Market estimate (e.g., '$580M - freelancer segment')",
    "som": "Serviceable Obtainable Market estimate (e.g., '$29M - achievable in 3 years at 5% market share')",
    "market_description": "2-3 sentence description of the market landscape",
    "positioning": "How to position this product vs competitors (1 sentence)",
    "pricing_model": "Recommended pricing model with rationale (freemium/subscription/pay-per-use/etc)",
    "target_segments": ["Segment 1", "Segment 2", "Segment 3"],
    "gtm_strategy": {{
        "primary_channel": "Main acquisition channel",
        "secondary_channels": ["Channel 2", "Channel 3"],
        "key_messaging": "Core value proposition message",
        "early_adopters": "Who to target first"
    }},
    "competitive_moat": "What sustainable advantage could be built",
    "market_score": 75,
    "score_reasoning": "Brief explanation of why this score (2-3 sentences)"
}}

**Scoring Guidelines (0-100):**
- 90-100: Huge market, weak competition, clear gap, strong demand signals
- 70-89: Large market, some competition, clear differentiation opportunity
- 50-69: Medium market, competitive, but specific niche opportunity
- 30-49: Small market or crowded space, limited differentiation
- 0-29: Tiny market or perfectly solved already

Be realistic and data-driven. Consider:
- Market size and growth potential
- Competitive intensity
- Differentiation opportunities
- Monetization potential
- Go-to-market feasibility

Return ONLY valid JSON, no markdown or extra text."""

        system_prompt = """You are an expert startup market analyst and business strategist. Your role is to:
1. Assess market size and growth potential realistically
2. Identify competitive gaps and positioning opportunities
3. Recommend practical go-to-market strategies
4. Evaluate monetization models
5. Provide honest, data-driven market scores

Be specific, realistic, and honest about market potential.

IMPORTANT: Always provide your analysis in Russian language."""

        try:
            response = self._deep_analysis(
                analysis_prompt,
                max_tokens=2000,
                system=system_prompt
            )

            # Parse JSON response
            import re
            response = re.sub(r'```json\s*', '', response)
            response = re.sub(r'```\s*$', '', response)
            response = response.strip()

            data = json.loads(response)

            # Extract GTM strategy
            gtm_data = data.get('gtm_strategy', {})
            gtm_channels = [gtm_data.get('primary_channel', '')] + gtm_data.get('secondary_channels', [])

            # Create MarketingAnalysis record
            marketing_analysis = MarketingAnalysis(
                problem_id=problem.id,
                tam=data.get('tam'),
                sam=data.get('sam'),
                som=data.get('som'),
                market_description=data.get('market_description'),
                competitors_json=competitors if competitors else None,
                positioning=data.get('positioning'),
                pricing_model=data.get('pricing_model'),
                target_segments=data.get('target_segments', []),
                gtm_channels=gtm_channels,
                gtm_messaging=gtm_data.get('key_messaging'),
                early_adopters=gtm_data.get('early_adopters'),
                competitive_moat=data.get('competitive_moat'),
                market_score=data.get('market_score'),
                score_reasoning=data.get('score_reasoning')
            )

            self.db.add(marketing_analysis)
            self.db.commit()
            self.db.refresh(marketing_analysis)

            logger.info(f"Market analysis complete. Score: {marketing_analysis.market_score}/100")
            logger.info(f"TAM: {marketing_analysis.tam}")
            logger.info(f"Found {len(competitors)} competitors")

            return marketing_analysis

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            logger.error(f"Response was: {response[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error in analyze_market: {e}")
            return None

    def analyze(self, problem: Problem) -> Dict[str, Any]:
        """
        Main entry point for marketing analysis
        """
        result = {
            "problem_id": problem.id,
            "analysis_complete": False,
            "market_score": None
        }

        marketing_analysis = self.analyze_market(problem)

        if marketing_analysis:
            result["analysis_complete"] = True
            result["market_score"] = marketing_analysis.market_score
            result["tam"] = marketing_analysis.tam
            result["competitors_found"] = len(marketing_analysis.competitors_json) if marketing_analysis.competitors_json else 0

        return result


def main():
    """Test Marketing Agent"""
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        # Get a problem to analyze
        from db.models import Problem
        problem = db.query(Problem).first()

        if not problem:
            print("No problems found in database. Run problem analyzer first.")
            return

        print(f"\nAnalyzing market for problem: {problem.problem_statement[:80]}...\n")

        agent = MarketingAgent(db)
        result = agent.analyze(problem)

        print(f"\nMarketing Analysis Results:")
        print(json.dumps(result, indent=2))

    finally:
        db.close()


if __name__ == "__main__":
    main()
