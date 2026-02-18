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
from config import settings

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


@router.get("/stats/filter-test")
async def test_filter(db: Session = Depends(get_db)):
    """Test the Haiku filter on one unanalyzed discussion to debug why 0 problems are created."""
    import os
    from config import settings as s

    # Get one unanalyzed discussion
    discussion = db.query(Discussion).filter(
        Discussion.is_analyzed == False
    ).first()

    if not discussion:
        # Try any discussion
        discussion = db.query(Discussion).first()
        if not discussion:
            return {"error": "No discussions in database"}

    filter_prompt = f"""Analyze this discussion and determine if it contains a REAL, SOLVABLE problem that could be a startup opportunity.

Title: {discussion.title}

Content:
{(discussion.content or '')[:2000]}

Answer with ONLY "YES" or "NO" followed by a brief reason (max 20 words).

YES if:
- Real frustration or pain point expressed
- Multiple people might have this problem
- Could be solved with technology/software

NO if:
- Sarcasm, joke, or exaggeration
- Unsolvable problem
- Too specific/niche
- Already perfectly solved

Format: YES/NO: [reason]"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=s.anthropic_api_key)
        msg = client.messages.create(
            model=s.filter_model,
            max_tokens=100,
            temperature=0.3,
            system="You are a startup idea validator.",
            messages=[{"role": "user", "content": filter_prompt}]
        )
        response = msg.content[0].text
        return {
            "discussion_id": discussion.id,
            "discussion_title": discussion.title[:100],
            "discussion_source": discussion.source.name if discussion.source else "?",
            "discussion_upvotes": discussion.upvotes,
            "is_analyzed": discussion.is_analyzed,
            "filter_response": response,
            "would_pass": response.strip().upper().startswith("YES"),
            "filter_model": s.filter_model,
        }
    except Exception as e:
        return {"error": str(e), "discussion_title": discussion.title[:100]}


@router.get("/stats/discussions-sample")
async def discussions_sample(db: Session = Depends(get_db)):
    """Show sample of discussions to understand data quality."""
    from sqlalchemy import func as _f
    unanalyzed = db.query(Discussion).filter(
        Discussion.is_analyzed == False
    ).order_by(_f.random()).limit(10).all()
    analyzed = db.query(Discussion).filter(
        Discussion.is_analyzed == True
    ).order_by(Discussion.id.desc()).limit(5).all()
    return {
        "unanalyzed_sample": [{"id": d.id, "title": d.title[:80], "upvotes": d.upvotes,
                                "source": d.source.name if d.source else "?",
                                "passed_filter": d.passed_filter} for d in unanalyzed],
        "recently_analyzed": [{"id": d.id, "title": d.title[:80], "upvotes": d.upvotes,
                               "passed_filter": d.passed_filter} for d in analyzed],
    }


@router.get("/stats/analyze-one")
async def analyze_one_sync(db: Session = Depends(get_db)):
    """Synchronously run full analysis on ONE discussion and return all intermediate results."""
    import anthropic as _anthropic
    from config import settings as s

    # Get an unanalyzed discussion - prefer ones with decent upvotes
    discussion = db.query(Discussion).filter(
        Discussion.is_analyzed == False,
        Discussion.upvotes < 5000  # avoid viral meme posts
    ).order_by(Discussion.upvotes.desc()).first()

    if not discussion:
        discussion = db.query(Discussion).filter(Discussion.is_analyzed == False).first()
    if not discussion:
        return {"error": "No unanalyzed discussions available"}

    client = _anthropic.Anthropic(api_key=s.anthropic_api_key)
    result = {"discussion_id": discussion.id, "title": discussion.title[:100],
              "upvotes": discussion.upvotes, "source": discussion.source.name if discussion.source else "?"}

    # Stage 1: Haiku filter
    filter_prompt = f"""Title: {discussion.title}\n\nContent:\n{(discussion.content or '')[:1500]}\n\nDoes this contain a REAL, SOLVABLE startup problem? Answer YES or NO with brief reason."""
    try:
        msg = client.messages.create(model=s.filter_model, max_tokens=100, temperature=0.3,
            system="You are a startup validator. Answer YES or NO.",
            messages=[{"role": "user", "content": filter_prompt}])
        filter_response = msg.content[0].text
        result["filter_response"] = filter_response
        result["filter_passed"] = filter_response.strip().upper().startswith("YES")
    except Exception as e:
        result["filter_error"] = str(e)
        return result

    if not result["filter_passed"]:
        return result

    # Stage 2: Sonnet analysis
    analysis_prompt = f"""Analyze this discussion and return JSON with problem_statement, severity (1-10), target_audience, startup_ideas (array with title, description, approach).

Title: {discussion.title}
Content: {(discussion.content or '')[:2000]}

Return ONLY valid JSON, no markdown."""
    try:
        msg2 = client.messages.create(model=s.analysis_model, max_tokens=1500, temperature=0.7,
            system="You are a startup analyst. Return JSON only.",
            messages=[{"role": "user", "content": analysis_prompt}])
        analysis_response = msg2.content[0].text
        result["analysis_response_preview"] = analysis_response[:500]
        import json as _json, re as _re
        cleaned = _re.sub(r'```json\s*', '', analysis_response)
        cleaned = _re.sub(r'```\s*$', '', cleaned).strip()
        parsed = _json.loads(cleaned)
        result["analysis_parsed_ok"] = True
        result["problem_statement"] = parsed.get("problem_statement", "")[:100]
        result["ideas_count"] = len(parsed.get("startup_ideas", []))
    except _json.JSONDecodeError as e:
        result["analysis_json_error"] = str(e)
        result["analysis_response_preview"] = analysis_response[:500] if 'analysis_response' in dir() else "no response"
    except Exception as e:
        result["analysis_error"] = str(e)

    return result


@router.get("/stats/sonnet-test")
async def test_sonnet_analysis(db: Session = Depends(get_db)):
    """Test Sonnet analysis stage directly on a discussion that already passed the filter."""
    import anthropic as _anthropic
    from config import settings as s
    import json as _json, re as _re

    # Find a discussion that passed the filter (regardless of is_analyzed)
    discussion = db.query(Discussion).filter(
        Discussion.passed_filter == True
    ).first()

    if not discussion:
        return {"error": "No discussions with passed_filter=True found. Run filter-test first."}

    client = _anthropic.Anthropic(api_key=s.anthropic_api_key)
    result = {
        "discussion_id": discussion.id,
        "title": discussion.title[:100],
        "upvotes": discussion.upvotes,
        "passed_filter": discussion.passed_filter,
        "is_analyzed": discussion.is_analyzed,
    }

    analysis_prompt = f"""Analyze this discussion and return JSON with problem_statement, severity (1-10), target_audience, startup_ideas (array with title, description, approach).

Title: {discussion.title}
Content: {(discussion.content or '')[:2000]}

Return ONLY valid JSON, no markdown."""
    try:
        msg = client.messages.create(
            model=s.analysis_model, max_tokens=1500, temperature=0.7,
            system="You are a startup analyst. Return JSON only.",
            messages=[{"role": "user", "content": analysis_prompt}]
        )
        raw = msg.content[0].text
        result["raw_response_preview"] = raw[:800]
        cleaned = _re.sub(r'```json\s*', '', raw)
        cleaned = _re.sub(r'```\s*$', '', cleaned).strip()
        parsed = _json.loads(cleaned)
        result["parsed_ok"] = True
        result["problem_statement"] = parsed.get("problem_statement", "")[:200]
        result["ideas_count"] = len(parsed.get("startup_ideas", []))
    except _json.JSONDecodeError as e:
        result["json_error"] = str(e)
        result["raw_response_preview"] = raw[:800] if 'raw' in dir() else "no response"
    except Exception as e:
        result["error"] = str(e)

    return result


@router.get("/stats/analyze-real")
async def analyze_real(db: Session = Depends(get_db)):
    """Run the real analyze_problem prompt inline and expose raw response + errors."""
    import anthropic as _anthropic
    import json as _json, re as _re, traceback as _tb
    from config import settings as s
    from db.models import Problem
    from sqlalchemy import exists as _exists

    discussion = db.query(Discussion).filter(
        Discussion.passed_filter == True,
        ~_exists().where(Problem.discussion_id == Discussion.id)
    ).first()
    if not discussion:
        discussion = db.query(Discussion).filter(Discussion.passed_filter == True).first()
    if not discussion:
        return {"error": "No discussions with passed_filter=True found"}

    result = {
        "discussion_id": discussion.id,
        "title": discussion.title[:100],
        "upvotes": discussion.upvotes,
    }

    # Use the SAME prompt as analyze_problem in problem_analyzer.py
    analysis_prompt = f"""Analyze this discussion to extract the core problem and generate startup ideas.

IMPORTANT: Provide ALL output in Russian language (problem_statement, target_audience, current_solutions, why_they_fail, startup idea titles and descriptions, etc.)

Title: {discussion.title}
Upvotes: {discussion.upvotes}
Comments: {discussion.comments_count}

Content:
{(discussion.content or '')[:3000]}

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

Return ONLY valid JSON, no markdown or extra text."""

    try:
        client = _anthropic.Anthropic(api_key=s.anthropic_api_key)
        msg = client.messages.create(
            model=s.analysis_model,
            max_tokens=2500,
            temperature=0.7,
            system="You are an expert startup advisor. Return JSON only.",
            messages=[{"role": "user", "content": analysis_prompt}]
        )
        raw = msg.content[0].text
        result["raw_length"] = len(raw)
        result["raw_preview"] = raw[:1000]
        result["raw_tail"] = raw[-200:]  # Check if JSON is truncated
        result["stop_reason"] = msg.stop_reason

        cleaned = _re.sub(r'```json\s*', '', raw)
        cleaned = _re.sub(r'```\s*$', '', cleaned).strip()
        try:
            parsed = _json.loads(cleaned)
            result["json_parsed_ok"] = True
            result["ideas_count"] = len(parsed.get("startup_ideas", []))
            result["problem_statement"] = parsed.get("problem_statement", "")[:200]
        except _json.JSONDecodeError as e:
            result["json_error"] = str(e)
            result["json_parsed_ok"] = False
            return result

        # Try saving to DB (same as analyze_problem)
        from db.models import Problem as _Problem, StartupIdea as _Idea, AnalysisTier as _Tier
        from agents.analyzers.problem_analyzer import ProblemAnalyzer as _PA
        audience_type = _PA._normalize_audience_type(parsed.get("audience_type"))
        if audience_type == "unknown":
            audience_type = _PA._infer_audience_type(parsed.get("target_audience"), parsed.get("problem_statement"))
        result["audience_type"] = audience_type
        try:
            problem = _Problem(
                discussion_id=discussion.id,
                problem_statement=parsed.get("problem_statement", ""),
                severity=parsed.get("severity"),
                target_audience=parsed.get("target_audience"),
                audience_type=audience_type,
                current_solutions=parsed.get("current_solutions"),
                why_they_fail=parsed.get("why_they_fail"),
                analysis_tier=_Tier.NONE
            )
            db.add(problem)
            db.commit()
            db.refresh(problem)
            result["problem_saved"] = True
            result["problem_id"] = problem.id

            for idea_data in parsed.get("startup_ideas", []):
                idea = _Idea(
                    problem_id=problem.id,
                    idea_title=idea_data.get("title", ""),
                    description=idea_data.get("description", ""),
                    approach=idea_data.get("approach"),
                    business_model=idea_data.get("business_model"),
                    value_proposition=idea_data.get("value_proposition"),
                    core_features=idea_data.get("core_features", []),
                    monetization=idea_data.get("monetization"),
                )
                db.add(idea)
            db.commit()
            result["ideas_saved"] = len(parsed.get("startup_ideas", []))
        except Exception as e:
            db.rollback()
            result["db_error"] = str(e)
            result["db_traceback"] = _tb.format_exc()[-500:]
    except Exception as e:
        result["api_error"] = str(e)
        result["traceback"] = _tb.format_exc()[-500:]

    return result


@router.get("/stats/env-check")
async def check_env():
    """Temporary: check raw os.environ for API key (bypasses pydantic-settings)"""
    import os
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    # Show Railway-injected service identifiers (safe to expose, no secrets)
    railway_vars = {k: v[:30] for k, v in os.environ.items() if k.startswith("RAILWAY_")}
    # Show all env var names that look like API keys (without values)
    api_key_names = [k for k in os.environ if "KEY" in k or "TOKEN" in k or "SECRET" in k]
    return {
        "raw_env_key_set": bool(key),
        "raw_env_key_prefix": key[:10] if key else "(empty)",
        "pydantic_settings_key_set": bool(settings.anthropic_api_key),
        "pydantic_key_prefix": settings.anthropic_api_key[:10] if settings.anthropic_api_key else "(empty)",
        "railway_vars": railway_vars,
        "api_key_env_var_names": api_key_names,
    }


@router.get("/stats/diagnostics")
async def get_diagnostics(db: Session = Depends(get_db)):
    """
    Check system health: API keys, unanalyzed discussions count, etc.
    Useful for debugging why analysis isn't running.
    """
    # Check API keys
    anthropic_key_set = bool(settings.anthropic_api_key)
    tavily_key_set = bool(settings.tavily_api_key)

    # Unanalyzed discussions
    unanalyzed_count = db.query(func.count(Discussion.id)).filter(
        Discussion.is_analyzed == False
    ).scalar()

    # Test Anthropic API if key is set
    anthropic_status = "not_tested"
    sonnet_status = "not_tested"
    if anthropic_key_set:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            msg = client.messages.create(
                model=settings.filter_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Say OK"}]
            )
            anthropic_status = "ok"
        except Exception as e:
            anthropic_status = f"error: {str(e)[:150]}"

        # Also test Sonnet (analysis model)
        try:
            msg2 = client.messages.create(
                model=settings.analysis_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Say OK"}]
            )
            sonnet_status = "ok"
        except Exception as e:
            sonnet_status = f"error: {str(e)[:150]}"
    else:
        anthropic_status = "key_not_set"
        sonnet_status = "key_not_set"

    return {
        "api_keys": {
            "anthropic": anthropic_key_set,
            "tavily": tavily_key_set,
        },
        "anthropic_api_status": anthropic_status,
        "sonnet_api_status": sonnet_status,
        "unanalyzed_discussions": unanalyzed_count,
        "filter_model": settings.filter_model,
        "analysis_model": settings.analysis_model,
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
