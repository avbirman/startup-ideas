"""
Scraper API routes

Endpoints for manually triggering scraping, scheduling, and viewing history
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging

from db.database import SessionLocal
from db.models import Source, ScrapeLog
from agents.scrapers.reddit_agent import RedditScraper
from agents.scrapers.hackernews_agent import HackerNewsScraper
from agents.scrapers.youtube_agent import YouTubeScraper
from agents.scrapers.medium_agent import MediumScraper
from agents.scrapers.tavily_agent import TavilySearchScraper
from agents.scrapers.appstore_agent import AppStoreScraper
from services.orchestrator import Orchestrator
from services.scheduler import scrape_scheduler

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_scrape_and_analyze(source: str, limit: int, triggered_by: str = "manual"):
    """
    Background task: scrape and analyze discussions, log result to ScrapeLog
    """
    db = SessionLocal()
    log_entry = ScrapeLog(
        source=source,
        status="running",
        started_at=datetime.utcnow(),
        triggered_by=triggered_by,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    log_id = log_entry.id

    try:
        logger.info(f"Starting scrape for source: {source} (triggered_by={triggered_by})")

        # Run scraper
        if source == "reddit":
            scraper = RedditScraper(db)
            scrape_result = scraper.run(limit_per_subreddit=limit)
        elif source == "hackernews":
            scraper = HackerNewsScraper(db)
            scraper.max_items = limit
            scrape_result = scraper.run()
        elif source == "youtube":
            scraper = YouTubeScraper(db)
            scrape_result = scraper.run()
        elif source == "medium":
            scraper = MediumScraper(db)
            scrape_result = scraper.run()
        elif source == "tavily":
            scraper = TavilySearchScraper(db)
            scrape_result = scraper.run()
        elif source == "appstore":
            scraper = AppStoreScraper(db)
            scrape_result = scraper.run()
        else:
            log_entry = db.query(ScrapeLog).get(log_id)
            log_entry.status = "failed"
            log_entry.error_message = f"Unknown source: {source}"
            log_entry.completed_at = datetime.utcnow()
            db.commit()
            return

        if not scrape_result.get("success", False):
            log_entry = db.query(ScrapeLog).get(log_id)
            log_entry.status = "failed"
            log_entry.error_message = scrape_result.get("error", "Scraper returned success=False")
            log_entry.completed_at = datetime.utcnow()
            db.commit()
            logger.error(f"Scrape failed: {scrape_result}")
            return

        discussions_count = scrape_result.get("discussions_count", 0)
        logger.info(f"Scrape complete: {scrape_result}")

        # Run analysis on new discussions
        orchestrator = Orchestrator(db)
        analysis_result = orchestrator.batch_analyze(limit=discussions_count)
        problems_created = analysis_result.get("problems_created", 0) if analysis_result else 0
        logger.info(f"Analysis complete: {analysis_result}")

        # Update log
        log_entry = db.query(ScrapeLog).get(log_id)
        log_entry.status = "completed"
        log_entry.discussions_found = discussions_count
        log_entry.problems_created = problems_created
        log_entry.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"Error in scrape_and_analyze: {e}")
        try:
            log_entry = db.query(ScrapeLog).get(log_id)
            if log_entry:
                log_entry.status = "failed"
                log_entry.error_message = str(e)[:500]
                log_entry.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _scheduled_scrape(source: str, limit: int, triggered_by: str = "schedule"):
    """Wrapper for scheduler to call run_scrape_and_analyze."""
    run_scrape_and_analyze(source, limit, triggered_by)


# Wire up the scheduler
scrape_scheduler.set_scrape_function(_scheduled_scrape)


@router.post("/scrape")
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    source: str = "reddit",
    limit: int = 10,
    analyze: bool = True,
    db: Session = Depends(get_db)
):
    """
    Manually trigger scraping for a specific source.
    Runs in background, returns immediately.
    """
    logger.info(f"Manual scrape triggered: source={source}, limit={limit}, analyze={analyze}")

    if source == "all":
        per_source_limit = max(1, limit // 6)
        background_tasks.add_task(run_scrape_and_analyze, "reddit", per_source_limit, "manual")
        background_tasks.add_task(run_scrape_and_analyze, "hackernews", per_source_limit, "manual")
        background_tasks.add_task(run_scrape_and_analyze, "youtube", per_source_limit, "manual")
        background_tasks.add_task(run_scrape_and_analyze, "medium", per_source_limit, "manual")
        background_tasks.add_task(run_scrape_and_analyze, "tavily", per_source_limit, "manual")
        background_tasks.add_task(run_scrape_and_analyze, "appstore", per_source_limit, "manual")
        return {
            "status": "started",
            "message": f"Scraping Reddit, Hacker News, YouTube, Medium, Tavily, App Store ({per_source_limit} each)",
            "analyze": analyze,
            "timestamp": datetime.utcnow().isoformat()
        }
    elif source in ["reddit", "hackernews", "youtube", "medium", "tavily", "appstore"]:
        background_tasks.add_task(run_scrape_and_analyze, source, limit, "manual")
        return {
            "status": "started",
            "source": source,
            "limit": limit,
            "analyze": analyze,
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        return {
            "status": "error",
            "message": f"Unknown source: {source}. Use 'reddit', 'hackernews', 'youtube', 'medium', or 'all'"
        }


# --- Scrape history ---

@router.get("/scrape/history")
async def get_scrape_history(limit: int = 20, db: Session = Depends(get_db)):
    """Get recent scrape log entries."""
    logs = (
        db.query(ScrapeLog)
        .order_by(ScrapeLog.started_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "source": log.source,
            "status": log.status,
            "discussions_found": log.discussions_found,
            "problems_created": log.problems_created,
            "error_message": log.error_message,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "triggered_by": log.triggered_by,
        }
        for log in logs
    ]


# --- Schedule CRUD ---

class ScheduleRequest(BaseModel):
    interval_hours: int = 6
    source: str = "all"
    limit: int = 10
    analyze: bool = True


@router.get("/schedule")
async def get_schedule():
    """Get current scrape schedule."""
    schedule = scrape_scheduler.get_schedule()
    if not schedule:
        return {"enabled": False}
    return schedule


@router.post("/schedule")
async def set_schedule(req: ScheduleRequest):
    """Set or update scrape schedule."""
    result = scrape_scheduler.set_schedule(
        interval_hours=req.interval_hours,
        source=req.source,
        limit=req.limit,
        analyze=req.analyze,
    )
    return result


@router.delete("/schedule")
async def delete_schedule():
    """Remove scrape schedule."""
    scrape_scheduler.remove_schedule()
    return {"status": "removed"}


# --- Sources status ---

@router.get("/sources/status")
async def get_sources_status(db: Session = Depends(get_db)):
    """Get status of all scraping sources."""
    sources = db.query(Source).all()

    result = []
    for source in sources:
        result.append({
            "name": source.name,
            "type": source.type.value,
            "is_active": source.is_active,
            "last_scraped": source.last_scraped.isoformat() if source.last_scraped else None,
            "created_at": source.created_at.isoformat()
        })

    return {
        "sources": result,
        "count": len(result)
    }
