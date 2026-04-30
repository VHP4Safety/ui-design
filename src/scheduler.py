"""
Nightly background job that re-seeds the database from upstream GitHub sources.

Uses APScheduler's BackgroundScheduler so it runs inside the same Flask /
SQLite process — no external cron or second container needed.
"""

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _reseed_job() -> None:
    """Idempotently re-seed all tables from upstream GitHub JSON sources."""
    from src.seed import seed_all  # late import to avoid circular deps

    log.info("⏳ Nightly re-seed started …")
    try:
        seed_all()
        log.info("✅ Nightly re-seed complete")
    except Exception:
        log.exception("❌ Nightly re-seed failed")


def init_scheduler(app=None) -> BackgroundScheduler:
    """
    Start (or return) the background scheduler.

    Environment knobs (all optional):
      RESEED_HOUR   – hour to run (0-23, default 3)
      RESEED_MINUTE – minute to run (0-59, default 0)
      RESEED_ENABLED – set to "false" to disable entirely
    """
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    enabled = os.environ.get("RESEED_ENABLED", "true").lower()
    if enabled == "false":
        log.info("🔕 Nightly re-seed disabled (RESEED_ENABLED=false)")
        return None

    hour = int(os.environ.get("RESEED_HOUR", "3"))
    minute = int(os.environ.get("RESEED_MINUTE", "0"))

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _reseed_job,
        trigger=CronTrigger(hour=hour, minute=minute),
        id="nightly_reseed",
        name="Re-seed DB from upstream",
        replace_existing=True,
    )
    _scheduler.start()
    log.info("🕐 Nightly re-seed scheduled at %02d:%02d UTC", hour, minute)
    return _scheduler
