"""
Problems API routes

Endpoints for browsing, filtering, and managing problem cards
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from db.database import SessionLocal
from db.models import (
    Problem, StartupIdea, Discussion, MarketingAnalysis,
    OverallScores, AnalysisTier, CardStatus, Source, SourceType
)

router = APIRouter()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Pydantic Schemas ───────────────────────────────────────────

class DiscussionSummary(BaseModel):
    id: int
    url: str
    title: str
    upvotes: int
    comments_count: int
    source_name: str

    class Config:
        from_attributes = True


class StartupIdeaSummary(BaseModel):
    id: int
    idea_title: str
    description: str
    approach: Optional[str]
    value_proposition: Optional[str]
    core_features: List[str]

    class Config:
        from_attributes = True


class ProblemListItem(BaseModel):
    id: int
    problem_statement: str
    severity: Optional[int]
    target_audience: Optional[str]
    audience_type: str
    overall_score: Optional[int]
    market_score: Optional[int]
    analysis_tier: str
    ideas_count: int
    discussion: DiscussionSummary
    extracted_at: datetime
    # Card management fields
    card_status: str
    is_starred: bool
    view_count: int
    user_tags: List[str]
    first_viewed_at: Optional[datetime]
    last_viewed_at: Optional[datetime]

    class Config:
        from_attributes = True


class MarketingAnalysisSummary(BaseModel):
    tam: Optional[str]
    sam: Optional[str]
    som: Optional[str]
    market_description: Optional[str]
    positioning: Optional[str]
    pricing_model: Optional[str]
    target_segments: List[str]
    gtm_channels: List[str]
    competitive_moat: Optional[str]
    market_score: Optional[int]
    score_reasoning: Optional[str]
    competitors_count: int

    class Config:
        from_attributes = True


class ProblemDetail(BaseModel):
    id: int
    problem_statement: str
    severity: Optional[int]
    target_audience: Optional[str]
    audience_type: str
    current_solutions: Optional[str]
    why_they_fail: Optional[str]
    analysis_tier: str
    overall_score: Optional[int]
    market_score: Optional[int]
    discussion: DiscussionSummary
    startup_ideas: List[StartupIdeaSummary]
    marketing_analysis: Optional[MarketingAnalysisSummary]
    extracted_at: datetime
    # Card management fields
    card_status: str
    is_starred: bool
    view_count: int
    user_tags: List[str]
    user_notes: Optional[str]
    first_viewed_at: Optional[datetime]
    last_viewed_at: Optional[datetime]
    archived_at: Optional[datetime]
    verified_at: Optional[datetime]

    class Config:
        from_attributes = True


# Request schemas for PATCH endpoints
class CardStatusUpdate(BaseModel):
    status: str

class StarToggle(BaseModel):
    is_starred: bool

class NotesUpdate(BaseModel):
    user_notes: str

class TagsUpdate(BaseModel):
    user_tags: List[str]


# ─── Helper Functions ───────────────────────────────────────────

def _format_problem_list_item(problem: Problem, db: Session) -> dict:
    """Format a Problem for list responses"""
    scores = db.query(OverallScores).filter(OverallScores.problem_id == problem.id).first()

    return {
        "id": problem.id,
        "problem_statement": problem.problem_statement,
        "severity": problem.severity,
        "target_audience": problem.target_audience,
        "audience_type": problem.audience_type or "unknown",
        "overall_score": scores.overall_confidence_score if scores else None,
        "market_score": scores.market_score if scores else None,
        "analysis_tier": problem.analysis_tier.value if problem.analysis_tier else "none",
        "ideas_count": len(problem.startup_ideas),
        "discussion": {
            "id": problem.discussion.id,
            "url": problem.discussion.url,
            "title": problem.discussion.title,
            "upvotes": problem.discussion.upvotes,
            "comments_count": problem.discussion.comments_count,
            "source_name": problem.discussion.source.name
        },
        "extracted_at": problem.extracted_at,
        "card_status": problem.card_status or "new",
        "is_starred": problem.is_starred or False,
        "view_count": problem.view_count or 0,
        "user_tags": problem.user_tags or [],
        "first_viewed_at": problem.first_viewed_at,
        "last_viewed_at": problem.last_viewed_at,
    }


# ─── Routes ─────────────────────────────────────────────────────

# IMPORTANT: /problems/archive MUST be before /problems/{problem_id}

@router.get("/problems/archive")
async def list_archived_problems(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List archived and rejected cards"""
    query = db.query(Problem).join(Discussion).outerjoin(OverallScores)
    query = query.filter(Problem.card_status.in_(["archived", "rejected"]))
    query = query.order_by(desc(Problem.archived_at))

    problems = query.offset(skip).limit(limit).all()
    return [_format_problem_list_item(p, db) for p in problems]


@router.get("/problems")
async def list_problems(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    analysis_tier: Optional[str] = Query(None),
    sort_by: str = Query("score"),
    # Card management filters
    status: Optional[str] = Query(None, description="Filter by card_status"),
    is_starred: Optional[bool] = Query(None),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    source_type: Optional[str] = Query(None),
    audience_type: Optional[str] = Query(None, description="consumers|entrepreneurs|mixed|unknown"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    db: Session = Depends(get_db)
):
    """List problems with filtering and card management"""
    query = db.query(Problem).join(Discussion).join(Source).outerjoin(OverallScores)

    # Card status filter
    valid_statuses = {"new", "viewed", "in_review", "verified", "archived", "rejected"}
    if status and status in valid_statuses:
        query = query.filter(Problem.card_status == status)
    elif not include_archived:
        # By default, hide archived and rejected
        query = query.filter(
            ~Problem.card_status.in_(["archived", "rejected"])
        )

    # Score filter
    if min_score is not None:
        query = query.filter(OverallScores.overall_confidence_score >= min_score)

    # Analysis tier filter
    if analysis_tier:
        tier_enum = AnalysisTier.BASIC if analysis_tier.lower() == "basic" else AnalysisTier.DEEP
        query = query.filter(Problem.analysis_tier == tier_enum)

    # Starred filter
    if is_starred is not None:
        query = query.filter(Problem.is_starred == is_starred)

    # Tags filter (LIKE-based for SQLite JSON compatibility)
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        for tag in tag_list:
            query = query.filter(Problem.user_tags.like(f'%"{tag}"%'))

    # Source type filter
    if source_type:
        try:
            source_enum = SourceType(source_type)
            query = query.filter(Source.type == source_enum)
        except ValueError:
            pass

    # Audience type filter
    valid_audience_types = {"consumers", "entrepreneurs", "mixed", "unknown"}
    if audience_type in valid_audience_types:
        query = query.filter(Problem.audience_type == audience_type)

    # Date range filters
    if date_from:
        try:
            query = query.filter(Problem.extracted_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(Problem.extracted_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    # Sorting
    if sort_by == "score":
        query = query.order_by(desc(OverallScores.overall_confidence_score))
    elif sort_by == "date":
        query = query.order_by(desc(Problem.extracted_at))
    elif sort_by == "severity":
        query = query.order_by(desc(Problem.severity))
    elif sort_by == "engagement":
        query = query.order_by(desc(Discussion.upvotes))

    problems = query.offset(skip).limit(limit).all()
    return [_format_problem_list_item(p, db) for p in problems]


@router.get("/problems/{problem_id}")
async def get_problem_detail(
    problem_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed problem info. Auto-records view and transitions NEW → VIEWED."""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()

    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # --- Record view ---
    now = datetime.utcnow()
    problem.view_count = (problem.view_count or 0) + 1
    problem.last_viewed_at = now
    if problem.first_viewed_at is None:
        problem.first_viewed_at = now
    if problem.card_status == "new" or problem.card_status is None:
        problem.card_status = "viewed"
    db.commit()
    db.refresh(problem)

    # Get related data
    scores = db.query(OverallScores).filter(OverallScores.problem_id == problem_id).first()
    marketing = db.query(MarketingAnalysis).filter(MarketingAnalysis.problem_id == problem_id).first()

    marketing_data = None
    if marketing:
        marketing_data = {
            "tam": marketing.tam,
            "sam": marketing.sam,
            "som": marketing.som,
            "market_description": marketing.market_description,
            "positioning": marketing.positioning,
            "pricing_model": marketing.pricing_model,
            "target_segments": marketing.target_segments or [],
            "gtm_channels": marketing.gtm_channels or [],
            "competitive_moat": marketing.competitive_moat,
            "market_score": marketing.market_score,
            "score_reasoning": marketing.score_reasoning,
            "competitors_count": len(marketing.competitors_json) if marketing.competitors_json else 0
        }

    return {
        "id": problem.id,
        "problem_statement": problem.problem_statement,
        "severity": problem.severity,
        "target_audience": problem.target_audience,
        "audience_type": problem.audience_type or "unknown",
        "current_solutions": problem.current_solutions,
        "why_they_fail": problem.why_they_fail,
        "analysis_tier": problem.analysis_tier.value if problem.analysis_tier else "none",
        "overall_score": scores.overall_confidence_score if scores else None,
        "market_score": scores.market_score if scores else None,
        "discussion": {
            "id": problem.discussion.id,
            "url": problem.discussion.url,
            "title": problem.discussion.title,
            "upvotes": problem.discussion.upvotes,
            "comments_count": problem.discussion.comments_count,
            "source_name": problem.discussion.source.name
        },
        "startup_ideas": [
            {
                "id": idea.id,
                "idea_title": idea.idea_title,
                "description": idea.description,
                "approach": idea.approach,
                "value_proposition": idea.value_proposition,
                "core_features": idea.core_features or []
            }
            for idea in problem.startup_ideas
        ],
        "marketing_analysis": marketing_data,
        "extracted_at": problem.extracted_at,
        # Card management
        "card_status": problem.card_status or "new",
        "is_starred": problem.is_starred or False,
        "view_count": problem.view_count or 0,
        "user_tags": problem.user_tags or [],
        "user_notes": problem.user_notes,
        "first_viewed_at": problem.first_viewed_at,
        "last_viewed_at": problem.last_viewed_at,
        "archived_at": problem.archived_at,
        "verified_at": problem.verified_at,
    }


@router.patch("/problems/{problem_id}/status")
async def update_card_status(
    problem_id: int,
    body: CardStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update card status"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    valid_statuses = {"new", "viewed", "in_review", "verified", "archived", "rejected"}
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")

    now = datetime.utcnow()
    problem.card_status = body.status

    if body.status == "archived":
        problem.archived_at = now
    elif body.status == "verified":
        problem.verified_at = now

    db.commit()
    return {"id": problem_id, "card_status": body.status}


@router.patch("/problems/{problem_id}/star")
async def toggle_star(
    problem_id: int,
    body: StarToggle,
    db: Session = Depends(get_db)
):
    """Toggle starred status"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    problem.is_starred = body.is_starred
    db.commit()
    return {"id": problem_id, "is_starred": problem.is_starred}


@router.patch("/problems/{problem_id}/notes")
async def update_notes(
    problem_id: int,
    body: NotesUpdate,
    db: Session = Depends(get_db)
):
    """Update user notes"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    problem.user_notes = body.user_notes
    db.commit()
    return {"id": problem_id, "user_notes": problem.user_notes}


@router.patch("/problems/{problem_id}/tags")
async def update_tags(
    problem_id: int,
    body: TagsUpdate,
    db: Session = Depends(get_db)
):
    """Update user tags"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    problem.user_tags = body.user_tags
    db.commit()
    return {"id": problem_id, "user_tags": problem.user_tags}


@router.get("/problems/{problem_id}/competitors")
async def get_competitors(
    problem_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed competitor information for a problem"""
    marketing = db.query(MarketingAnalysis).filter(
        MarketingAnalysis.problem_id == problem_id
    ).first()

    if not marketing:
        raise HTTPException(status_code=404, detail="Marketing analysis not found")

    if not marketing.competitors_json:
        return {"competitors": [], "count": 0}

    return {
        "competitors": marketing.competitors_json,
        "count": len(marketing.competitors_json)
    }
