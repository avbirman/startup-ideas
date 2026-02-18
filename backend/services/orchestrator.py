"""
Orchestrator - coordinates all AI agents and computes final scores

For Weekend MVP (Tier 2):
- Problem Analyzer (filter + analysis)
- Marketing Agent
- Computes basic confidence score

Future: Add Design, Tech, Validator, Trend agents for Tier 3 (deep analysis)
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from db.models import Discussion, Problem, AnalysisTier, OverallScores
from agents.analyzers.problem_analyzer import ProblemAnalyzer
from agents.analyzers.marketing_agent import MarketingAgent

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates all AI agents and manages analysis workflow"""

    def __init__(self, db: Session):
        self.db = db
        try:
            self.problem_analyzer = ProblemAnalyzer(db)
            self.marketing_agent = MarketingAgent(db)
        except ValueError as e:
            logger.error(f"Failed to initialize analyzers: {e}")
            raise

    def analyze_discussion(self, discussion: Discussion) -> Dict[str, Any]:
        """
        Analyze a single discussion through all stages

        Weekend MVP flow (Tier 2):
        1. Problem Analyzer: filter + deep analysis
        2. Marketing Agent: market research
        3. Compute basic confidence score

        Returns analysis results
        """
        logger.info(f"Orchestrating analysis for discussion: {discussion.title[:60]}...")

        result = {
            "discussion_id": discussion.id,
            "passed_filter": False,
            "problem_created": False,
            "marketing_complete": False,
            "overall_score": None,
            "analysis_tier": AnalysisTier.NONE
        }

        # Stage 1: Problem Analysis (Haiku filter + Sonnet deep analysis)
        logger.info("Stage 1: Problem Analyzer")
        problem_result = self.problem_analyzer.analyze(discussion)

        result["passed_filter"] = problem_result["passed_filter"]

        if not problem_result["passed_filter"]:
            logger.info("Discussion filtered out - not a real problem")
            return result

        if not problem_result["problem_created"]:
            logger.warning("Problem analysis failed")
            return result

        # Get the created problem
        problem = self.db.query(Problem).get(problem_result["problem_id"])
        result["problem_created"] = True
        result["problem_id"] = problem.id
        result["ideas_generated"] = problem_result["ideas_generated"]
        result["problem_severity"] = problem_result["severity"]

        # Stage 2: Marketing Analysis
        logger.info("Stage 2: Marketing Agent")
        try:
            marketing_result = self.marketing_agent.analyze(problem)

            if marketing_result["analysis_complete"]:
                result["marketing_complete"] = True
                result["market_score"] = marketing_result["market_score"]
                result["tam"] = marketing_result.get("tam")
                result["competitors_found"] = marketing_result.get("competitors_found", 0)

                # Update problem tier to BASIC (Tier 2 complete)
                problem.analysis_tier = AnalysisTier.BASIC
                self.db.commit()

                # Stage 3: Compute Overall Score (for Tier 2, just use market score as base)
                overall_score = self._compute_tier2_score(problem, marketing_result["market_score"])
                result["overall_score"] = overall_score
                result["analysis_tier"] = AnalysisTier.BASIC

                # Save overall score
                self._save_overall_score(problem.id, market_score=marketing_result["market_score"], overall_score=overall_score)

                logger.info(f"✅ Analysis complete! Overall score: {overall_score}/100")

            else:
                logger.warning("Marketing analysis failed")

        except Exception as e:
            logger.error(f"Error in marketing analysis: {e}")

        return result

    def _compute_tier2_score(self, problem: Problem, market_score: int) -> int:
        """
        Compute overall confidence score for Tier 2 (Basic) analysis

        For Weekend MVP, we only have:
        - Problem severity (1-10)
        - Market score (0-100)

        Formula:
        Overall = (Market Score × 0.7) + (Problem Severity × 10 × 0.3)

        This gives more weight to market analysis while factoring in problem severity
        """
        if not market_score:
            return 0

        # Normalize problem severity to 0-100 scale
        severity_score = (problem.severity or 5) * 10  # Default to 50 if not set

        # Weighted combination
        overall = int((market_score * 0.7) + (severity_score * 0.3))

        logger.info(f"Score calculation: Market({market_score}) × 0.7 + Severity({severity_score}) × 0.3 = {overall}")

        return min(100, max(0, overall))  # Clamp to 0-100

    def _compute_tier3_score(
        self,
        market_score: int,
        design_score: int,
        tech_score: int,
        validation_score: int,
        trend_score: int
    ) -> int:
        """
        Compute overall confidence score for Tier 3 (Deep) analysis

        Formula from plan:
        Overall = (Market×0.25 + Design×0.15 + Tech×0.20 + Validation×0.25 + Trend×0.15)

        This will be used in future when all 6 agents are implemented
        """
        overall = int(
            market_score * 0.25 +
            design_score * 0.15 +
            tech_score * 0.20 +
            validation_score * 0.25 +
            trend_score * 0.15
        )

        logger.info(f"Tier 3 score: M({market_score})×0.25 + D({design_score})×0.15 + "
                   f"T({tech_score})×0.20 + V({validation_score})×0.25 + "
                   f"Tr({trend_score})×0.15 = {overall}")

        return min(100, max(0, overall))

    def _save_overall_score(
        self,
        problem_id: int,
        market_score: int,
        overall_score: int,
        design_score: Optional[int] = None,
        tech_score: Optional[int] = None,
        validation_score: Optional[int] = None,
        trend_score: Optional[int] = None
    ):
        """Save overall scores to database"""
        try:
            # Check if score already exists
            existing_score = self.db.query(OverallScores).filter(
                OverallScores.problem_id == problem_id
            ).first()

            if existing_score:
                # Update existing
                existing_score.market_score = market_score
                existing_score.design_score = design_score
                existing_score.tech_score = tech_score
                existing_score.validation_score = validation_score
                existing_score.trend_score = trend_score
                existing_score.overall_confidence_score = overall_score
                existing_score.analysis_tier = AnalysisTier.DEEP if all([design_score, tech_score, validation_score, trend_score]) else AnalysisTier.BASIC
            else:
                # Create new
                score_record = OverallScores(
                    problem_id=problem_id,
                    market_score=market_score,
                    design_score=design_score,
                    tech_score=tech_score,
                    validation_score=validation_score,
                    trend_score=trend_score,
                    overall_confidence_score=overall_score,
                    analysis_tier=AnalysisTier.DEEP if all([design_score, tech_score, validation_score, trend_score]) else AnalysisTier.BASIC
                )
                self.db.add(score_record)

            self.db.commit()
            logger.info(f"Overall score saved: {overall_score}/100")

        except Exception as e:
            logger.error(f"Error saving overall score: {e}")
            self.db.rollback()

    def batch_analyze(self, limit: int = 20) -> Dict[str, Any]:
        """
        Analyze multiple unanalyzed discussions in batch

        For Weekend MVP, processes up to `limit` discussions through Tier 2 analysis
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
            "total_processed": 0,
            "passed_filter": 0,
            "problems_created": 0,
            "marketing_complete": 0,
            "failed": 0,
            "average_score": 0,
            "high_confidence_count": 0  # Score >= 70
        }

        scores = []

        for discussion in discussions:
            try:
                result = self.analyze_discussion(discussion)

                results["total_processed"] += 1

                if result["passed_filter"]:
                    results["passed_filter"] += 1

                if result["problem_created"]:
                    results["problems_created"] += 1

                if result["marketing_complete"]:
                    results["marketing_complete"] += 1

                    if result["overall_score"]:
                        scores.append(result["overall_score"])
                        if result["overall_score"] >= 70:
                            results["high_confidence_count"] += 1

                # Mark as analyzed
                discussion.is_analyzed = True
                self.db.commit()

            except Exception as e:
                logger.error(f"Failed to analyze discussion {discussion.id}: {e}")
                results["failed"] += 1
                self.db.rollback()
                continue

        # Compute average score
        if scores:
            results["average_score"] = int(sum(scores) / len(scores))

        logger.info(f"Batch analysis complete: {results}")
        return results


def main():
    """Test Orchestrator with batch analysis"""
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        orchestrator = Orchestrator(db)

        # Run batch analysis on small set for testing
        results = orchestrator.batch_analyze(limit=5)

        print("\n" + "="*60)
        print("BATCH ANALYSIS RESULTS")
        print("="*60)
        print(f"Total processed: {results['total_processed']}")
        print(f"Passed filter: {results['passed_filter']}")
        print(f"Problems created: {results['problems_created']}")
        print(f"Marketing complete: {results['marketing_complete']}")
        print(f"Failed: {results['failed']}")
        print(f"Average score: {results['average_score']}/100")
        print(f"High confidence (>=70): {results['high_confidence_count']}")
        print("="*60)

    finally:
        db.close()


if __name__ == "__main__":
    main()
