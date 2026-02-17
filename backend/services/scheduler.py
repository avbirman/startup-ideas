"""
Scrape scheduler service using APScheduler.

Stores schedule config in a JSON file for persistence across restarts.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

SCHEDULE_FILE = Path(__file__).parent.parent / "data" / "schedule.json"
JOB_ID = "scrape_job"


class ScrapeScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._scrape_fn = None

    def set_scrape_function(self, fn):
        """Set the function to call on each scheduled run."""
        self._scrape_fn = fn

    def start(self):
        """Start the scheduler. Restore saved schedule if exists."""
        self.scheduler.start()
        logger.info("Scheduler started")

        config = self._load_config()
        if config and config.get("enabled"):
            self._add_job(config)
            logger.info(f"Restored schedule: every {config['interval_hours']}h, source={config['source']}")

    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def get_schedule(self) -> Optional[Dict[str, Any]]:
        """Get current schedule config with next_run_at."""
        config = self._load_config()
        if not config or not config.get("enabled"):
            return None

        job = self.scheduler.get_job(JOB_ID)
        next_run = None
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()

        return {
            **config,
            "next_run_at": next_run,
        }

    def set_schedule(self, interval_hours: int, source: str, limit: int, analyze: bool) -> Dict[str, Any]:
        """Set or update the scrape schedule."""
        config = {
            "enabled": True,
            "interval_hours": interval_hours,
            "source": source,
            "limit": limit,
            "analyze": analyze,
            "created_at": datetime.utcnow().isoformat(),
            "last_run_at": None,
        }

        # Remove old job if exists
        if self.scheduler.get_job(JOB_ID):
            self.scheduler.remove_job(JOB_ID)

        self._save_config(config)
        self._add_job(config)

        job = self.scheduler.get_job(JOB_ID)
        next_run = job.next_run_time.isoformat() if job and job.next_run_time else None

        logger.info(f"Schedule set: every {interval_hours}h, source={source}, limit={limit}")
        return {**config, "next_run_at": next_run}

    def remove_schedule(self):
        """Remove the current schedule."""
        if self.scheduler.get_job(JOB_ID):
            self.scheduler.remove_job(JOB_ID)

        if SCHEDULE_FILE.exists():
            SCHEDULE_FILE.unlink()

        logger.info("Schedule removed")

    def _on_scheduled_run(self, source: str, limit: int, analyze: bool):
        """Called by APScheduler on each tick."""
        logger.info(f"Scheduled scrape triggered: source={source}, limit={limit}")

        # Update last_run_at
        config = self._load_config()
        if config:
            config["last_run_at"] = datetime.utcnow().isoformat()
            self._save_config(config)

        if self._scrape_fn:
            self._scrape_fn(source, limit, "schedule")

    def _add_job(self, config: Dict[str, Any]):
        """Add the scrape job to the scheduler."""
        self.scheduler.add_job(
            self._on_scheduled_run,
            trigger=IntervalTrigger(hours=config["interval_hours"]),
            id=JOB_ID,
            replace_existing=True,
            kwargs={
                "source": config["source"],
                "limit": config["limit"],
                "analyze": config.get("analyze", True),
            },
        )

    def _load_config(self) -> Optional[Dict[str, Any]]:
        if not SCHEDULE_FILE.exists():
            return None
        try:
            with open(SCHEDULE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _save_config(self, config: Dict[str, Any]):
        SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SCHEDULE_FILE, "w") as f:
            json.dump(config, f, indent=2)


# Global instance
scrape_scheduler = ScrapeScheduler()
