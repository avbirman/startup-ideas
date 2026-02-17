"""
FastAPI Backend - Startup Ideas Collector

Endpoints:
- GET /api/problems - list problems
- GET /api/problems/{id} - problem details
- GET /api/stats - dashboard statistics
- POST /api/scrape - manual scrape trigger
- GET/POST/DELETE /api/schedule - scrape scheduling
- GET /api/scrape/history - scrape log
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from db.database import SessionLocal, migrate_db
from api.routes import problems, scraper, stats
from services.scheduler import scrape_scheduler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Run database migration on startup (add new columns/tables if missing)
migrate_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: start scheduler (restores saved schedule if any)
    scrape_scheduler.start()
    logger.info("Scrape scheduler initialized")
    yield
    # Shutdown: stop scheduler
    scrape_scheduler.shutdown()
    logger.info("Scrape scheduler stopped")


# Create FastAPI app
app = FastAPI(
    title="Startup Ideas Collector API",
    description="Automated system for finding and validating startup ideas from online discussions",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency: Database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Include routers
app.include_router(problems.router, prefix="/api", tags=["problems"])
app.include_router(scraper.router, prefix="/api", tags=["scraper"])
app.include_router(stats.router, prefix="/api", tags=["stats"])


@app.get("/")
async def root():
    """API root - health check"""
    return {
        "message": "Startup Ideas Collector API",
        "version": "0.2.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint - verifies database connection"""
    try:
        from db.models import Discussion
        db.query(Discussion).first()
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
