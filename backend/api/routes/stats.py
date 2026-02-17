"""
Statistics API routes

Dashboard and analytics endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import Dict, Any

from db.database import SessionLocal
from db.models import (
    Discussion, Problem, StartupIdea, OverallScores,
    AnalysisTier, Source, SourceType, CardStatus
)

router = APIRouter()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Get statistics for dashboard

    Returns:
    - Total counts (discussions, problems, ideas)
    - Today's activity
    - Score distribution
    - Top problems
    - Source breakdown
    """

    # Total counts
    total_discussions = db.query(func.count(Discussion.id)).scalar()
    total_problems = db.query(func.count(Problem.id)).scalar()
    total_ideas = db.query(func.count(StartupIdea.id)).scalar()

    # Today's activity
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())

    discussions_today = db.query(func.count(Discussion.id)).filter(
        Discussion.scraped_at >= today_start
    ).scalar()

    problems_today = db.query(func.count(Problem.id)).filter(
        Problem.extracted_at >= today_start
    ).scalar()

    # Analysis tier breakdown
    basic_count = db.query(func.count(Problem.id)).filter(
        Problem.analysis_tier == AnalysisTier.BASIC
    ).scalar()

    deep_count = db.query(func.count(Problem.id)).filter(
        Problem.analysis_tier == AnalysisTier.DEEP
    ).scalar()

    # Score distribution
    score_ranges = {
        "90-100": 0,
        "70-89": 0,
        "50-69": 0,
        "30-49": 0,
        "0-29": 0
    }

    scores = db.query(OverallScores.overall_confidence_score).all()
    for (score,) in scores:
        if score is not None:
            if score >= 90:
                score_ranges["90-100"] += 1
            elif score >= 70:
                score_ranges["70-89"] += 1
            elif score >= 50:
                score_ranges["50-69"] += 1
            elif score >= 30:
                score_ranges["30-49"] += 1
            else:
                score_ranges["0-29"] += 1

    # Top problems by score
    top_problems_query = db.query(
        Problem.id,
        Problem.problem_statement,
        OverallScores.overall_confidence_score,
        Discussion.upvotes
    ).join(OverallScores).join(Discussion).filter(
        OverallScores.overall_confidence_score.isnot(None)
    ).order_by(
        desc(OverallScores.overall_confidence_score)
    ).limit(5)

    top_problems = [
        {
            "id": p_id,
            "problem_statement": statement[:100] + "..." if len(statement) > 100 else statement,
            "score": score,
            "upvotes": upvotes
        }
        for p_id, statement, score, upvotes in top_problems_query
    ]

    # Source breakdown
    source_stats = []
    sources = db.query(Source).all()

    for source in sources:
        discussions_count = db.query(func.count(Discussion.id)).filter(
            Discussion.source_id == source.id
        ).scalar()

        source_stats.append({
            "name": source.name,
            "type": source.type.value,
            "discussions_count": discussions_count,
            "last_scraped": source.last_scraped.isoformat() if source.last_scraped else None,
            "is_active": source.is_active
        })

    # Average scores
    avg_score = db.query(func.avg(OverallScores.overall_confidence_score)).scalar()
    avg_market_score = db.query(func.avg(OverallScores.market_score)).scalar()

    return {
        "totals": {
            "discussions": total_discussions,
            "problems": total_problems,
            "ideas": total_ideas
        },
        "today": {
            "discussions": discussions_today,
            "problems": problems_today
        },
        "analysis_tiers": {
            "basic": basic_count,
            "deep": deep_count
        },
        "score_distribution": score_ranges,
        "average_scores": {
            "overall": round(avg_score, 1) if avg_score else 0,
            "market": round(avg_market_score, 1) if avg_market_score else 0
        },
        "top_problems": top_problems,
        "sources": source_stats,
        # Card management stats
        "card_statuses": {
            s: db.query(func.count(Problem.id)).filter(
                Problem.card_status == s
            ).scalar() or 0
            for s in ["new", "viewed", "in_review", "verified", "archived", "rejected"]
        },
        "starred_count": db.query(func.count(Problem.id)).filter(
            Problem.is_starred == True
        ).scalar() or 0,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/stats/recent-activity")
async def get_recent_activity(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get activity over the last N days

    Shows daily breakdown of discussions scraped and problems analyzed
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Discussions per day
    discussions_by_day = db.query(
        func.date(Discussion.scraped_at).label('date'),
        func.count(Discussion.id).label('count')
    ).filter(
        Discussion.scraped_at >= cutoff_date
    ).group_by(
        func.date(Discussion.scraped_at)
    ).order_by('date').all()

    # Problems per day
    problems_by_day = db.query(
        func.date(Problem.extracted_at).label('date'),
        func.count(Problem.id).label('count')
    ).filter(
        Problem.extracted_at >= cutoff_date
    ).group_by(
        func.date(Problem.extracted_at)
    ).order_by('date').all()

    return {
        "period_days": days,
        "discussions_by_day": [
            {"date": date.isoformat(), "count": count}
            for date, count in discussions_by_day
        ],
        "problems_by_day": [
            {"date": date.isoformat(), "count": count}
            for date, count in problems_by_day
        ]
    }
