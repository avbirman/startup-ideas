"""
Problem Analyzer Agent - filters and analyzes discussions for startup opportunities

Tier 1: Quick Filter (Haiku) - Is this a real, solvable problem?
Tier 2: Deep Analysis (Sonnet) - Problem details + idea generation
"""
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from agents.analyzers.base_analyzer import BaseAnalyzer
from db.models import Discussion, Problem, StartupIdea, AnalysisTier
import logging
import re

logger = logging.getLogger(__name__)


class ProblemAnalyzer(BaseAnalyzer):
    """Analyzes discussions to extract problems and generate startup ideas"""

    def __init__(self, db: Session):
        super().__init__()
        self.db = db

    @staticmethod
    def _normalize_audience_type(value: Optional[str]) -> str:
        if not value:
            return "unknown"
        v = value.strip().lower()
        if v in {"consumers", "consumer", "b2c", "простые_люди", "простые люди"}:
            return "consumers"
        if v in {"entrepreneurs", "entrepreneur", "b2b", "предприниматели", "business"}:
            return "entrepreneurs"
        if v in {"mixed", "hybrid"}:
            return "mixed"
        return "unknown"

    @staticmethod
    def _infer_audience_type(target_audience: Optional[str], problem_statement: Optional[str]) -> str:
        text = f"{target_audience or ''} {problem_statement or ''}".lower()

        business_signals = [
            "business", "бизнес", "основател", "founder", "saas", "компан", "предприним",
            "фриланс", "agency", "crm", "sales", "маркетинг", "small business",
        ]
        consumer_signals = [
            "люди", "пользовател", "consumer", "b2c", "родител", "student", "студент",
            "household", "семь", "everyday", "обыч", "дом", "личн", "person", "любой",
        ]

        business_hits = sum(1 for s in business_signals if s in text)
        consumer_hits = sum(1 for s in consumer_signals if s in text)

        if business_hits and consumer_hits:
            return "mixed"
        if business_hits:
            return "entrepreneurs"
        if consumer_hits:
            return "consumers"
        return "unknown"

    def filter_discussion(self, discussion: Discussion) -> bool:
        """
        Stage 1: Quick filter using Haiku
        Returns True if discussion contains a real, solvable problem
        """
        logger.info(f"Filtering discussion: {discussion.title[:50]}...")

        filter_prompt = f"""Analyze this discussion and determine if it contains a REAL, SOLVABLE problem that could be a startup opportunity.

Title: {discussion.title}

Content:
{discussion.content[:2000]}

Answer with ONLY "YES" or "NO" followed by a brief reason (max 20 words).

YES if:
- Real frustration or pain point expressed
- Multiple people might have this problem
- Could be solved with technology/software
- Not just a joke, sarcasm, or temporary complaint
- Prefer recurring everyday pain points that can scale to mass B2C audiences

NO if:
- Sarcasm, joke, or exaggeration
- Unsolvable problem (fundamental physics, human nature)
- Too specific/niche (only 1 person would care)
- Already perfectly solved

Format: YES/NO: [reason]"""

        system_prompt = "You are a startup idea validator. Your job is to quickly identify if discussions contain real, solvable problems."

        try:
            response = self._quick_filter(filter_prompt, system=system_prompt)

            # Parse response
            response_upper = response.strip().upper()
            is_valid = response_upper.startswith('YES')

            logger.info(f"Filter result: {response.strip()}")

            # Update discussion in database
            discussion.passed_filter = is_valid
            self.db.commit()

            return is_valid

        except Exception as e:
            logger.error(f"Error in filter_discussion: {e}")
            return False

    def analyze_problem(self, discussion: Discussion) -> Optional[Problem]:
        """
        Stage 2: Deep analysis using Sonnet
        Extracts problem details and generates startup ideas
        Returns Problem object if successful
        """
        logger.info(f"Analyzing problem: {discussion.title[:50]}...")

        analysis_prompt = f"""Analyze this discussion to extract the core problem and generate startup ideas.

IMPORTANT: Provide ALL output in Russian language (problem_statement, target_audience, current_solutions, why_they_fail, startup idea titles and descriptions, etc.)

Title: {discussion.title}
Upvotes: {discussion.upvotes}
Comments: {discussion.comments_count}

Content:
{discussion.content[:3000]}

Provide your analysis in this EXACT JSON format (all text fields in Russian):
{{
    "problem_statement": "Clear 1-2 sentence description of the core problem",
    "severity": 7,
    "target_audience": "Who experiences this problem (be specific)",
    "audience_type": "consumers|entrepreneurs|mixed|unknown",
    "current_solutions": "What solutions exist today?",
    "why_they_fail": "Why do current solutions fail to solve this?",
    "startup_ideas": [
        {{
            "title": "Idea name",
            "description": "What the startup does (2-3 sentences)",
            "approach": "SaaS/marketplace/tool/API/mobile_app/community/browser_extension",
            "business_model": "B2C subscription/B2B SaaS/freemium/marketplace commission/one-time purchase/API usage",
            "value_proposition": "Why would people pay for this?",
            "core_features": ["Feature 1", "Feature 2", "Feature 3"],
            "monetization": "How exactly does it make money? (e.g. $9/mo per user, 5% commission, $99 one-time)"
        }}
    ]
}}

Guidelines:
- Severity: 1-10 scale (1=minor annoyance, 10=critical business problem)
- Generate 5-7 different startup ideas, each with a DIFFERENT approach and business model
- Cover at least 3 different approaches: e.g. SaaS + mobile_app + browser_extension + marketplace + API
- Be specific and realistic about monetization
- Prioritize mass-market B2C opportunities where possible (everyday users, frequent pain)
- audience_type:
  - consumers: ordinary people / household / personal day-to-day problems
  - entrepreneurs: founders, freelancers, small-business operators
  - mixed: both groups clearly affected

Return ONLY valid JSON, no markdown or extra text."""

        system_prompt = """You are an expert startup advisor and problem analyst. Your role is to:
1. Extract the core problem from discussions
2. Assess market potential and severity
3. Generate practical, fundable startup ideas
4. Be realistic about what can be built and sold

IMPORTANT: Always provide your analysis in Russian language."""

        try:
            response = self._deep_analysis(
                analysis_prompt,
                max_tokens=2500,
                system=system_prompt
            )

            # Parse JSON response
            # Remove markdown code blocks if present
            response = re.sub(r'```json\s*', '', response)
            response = re.sub(r'```\s*$', '', response)
            response = response.strip()

            data = json.loads(response)

            audience_type = self._normalize_audience_type(data.get('audience_type'))
            if audience_type == "unknown":
                audience_type = self._infer_audience_type(
                    data.get('target_audience'),
                    data.get('problem_statement')
                )

            # Create Problem record
            problem = Problem(
                discussion_id=discussion.id,
                problem_statement=data.get('problem_statement', ''),
                severity=data.get('severity'),
                target_audience=data.get('target_audience'),
                audience_type=audience_type,
                current_solutions=data.get('current_solutions'),
                why_they_fail=data.get('why_they_fail'),
                analysis_tier=AnalysisTier.NONE  # Will be updated by orchestrator
            )

            self.db.add(problem)
            self.db.commit()
            self.db.refresh(problem)

            # Create StartupIdea records
            ideas_data = data.get('startup_ideas', [])
            for idea_data in ideas_data:
                idea = StartupIdea(
                    problem_id=problem.id,
                    idea_title=idea_data.get('title', ''),
                    description=idea_data.get('description', ''),
                    approach=idea_data.get('approach'),
                    business_model=idea_data.get('business_model'),
                    value_proposition=idea_data.get('value_proposition'),
                    core_features=idea_data.get('core_features', []),
                    monetization=idea_data.get('monetization'),
                )
                self.db.add(idea)

            self.db.commit()

            logger.info(f"Problem analyzed successfully: {problem.problem_statement[:50]}...")
            logger.info(f"Generated {len(ideas_data)} startup ideas")

            return problem

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            logger.error(f"Response was: {response[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error in analyze_problem: {e}")
            return None

    def analyze(self, discussion: Discussion) -> Dict[str, Any]:
        """
        Main entry point: filter → analyze → generate ideas
        """
        result = {
            "discussion_id": discussion.id,
            "passed_filter": False,
            "problem_created": False,
            "ideas_generated": 0
        }

        # Stage 1: Filter
        if not self.filter_discussion(discussion):
            logger.info("Discussion filtered out (not a real problem)")
            return result

        result["passed_filter"] = True

        # Stage 2: Deep analysis
        problem = self.analyze_problem(discussion)

        if problem:
            result["problem_created"] = True
            result["problem_id"] = problem.id
            result["ideas_generated"] = len(problem.startup_ideas)
            result["severity"] = problem.severity

        return result

    def batch_analyze(self, limit: int = 50) -> Dict[str, Any]:
        """
        Analyze unanalyzed discussions in batch
        """
        logger.info(f"Starting batch analysis (limit: {limit})")

        # Get unanalyzed discussions
        discussions = self.db.query(Discussion).filter(
            Discussion.is_analyzed == False
        ).order_by(
            Discussion.upvotes.desc()  # Prioritize high-engagement discussions
        ).limit(limit).all()

        logger.info(f"Found {len(discussions)} unanalyzed discussions")

        results = {
            "total_analyzed": 0,
            "passed_filter": 0,
            "problems_created": 0,
            "ideas_generated": 0,
            "failed": 0
        }

        for discussion in discussions:
            try:
                result = self.analyze(discussion)

                results["total_analyzed"] += 1
                if result["passed_filter"]:
                    results["passed_filter"] += 1
                if result["problem_created"]:
                    results["problems_created"] += 1
                    results["ideas_generated"] += result["ideas_generated"]

                # Mark as analyzed
                discussion.is_analyzed = True
                self.db.commit()

            except Exception as e:
                logger.error(f"Failed to analyze discussion {discussion.id}: {e}")
                results["failed"] += 1
                continue

        logger.info(f"Batch analysis complete: {results}")
        return results


def main():
    """Test Problem Analyzer"""
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        analyzer = ProblemAnalyzer(db)
        results = analyzer.batch_analyze(limit=10)
        print(f"\nAnalysis results: {json.dumps(results, indent=2)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
