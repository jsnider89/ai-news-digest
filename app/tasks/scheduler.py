"""APScheduler wrapper for newsletter jobs."""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config.settings import get_settings
from app.data import repositories
from app.data.database import SessionLocal
from app.tasks import service as task_service

logger = logging.getLogger("market_aggregator.scheduler")


class SchedulerManager:
    def __init__(self) -> None:
        settings = get_settings()
        self.scheduler = AsyncIOScheduler(timezone=settings.default_timezone)
        self._started = False

    async def start(self) -> None:
        if not self._started:
            self.scheduler.start()
            self._started = True
            logger.info("Scheduler started")
        await self.refresh_jobs()

    async def refresh_jobs(self) -> None:
        async with SessionLocal() as session:
            newsletters = await repositories.list_newsletters(session)
            overrides = await repositories.get_global_settings(session)
            schedule_data = [
                (n.id, n.name, list(n.schedule_times or []), n.timezone, n.active)
                for n in newsletters
            ]
        self._clear_newsletter_jobs()
        settings = get_settings()
        default_times = overrides.get("default_send_times", settings.default_send_times) if overrides else settings.default_send_times
        default_timezone = overrides.get("default_timezone", settings.default_timezone) if overrides else settings.default_timezone
        for newsletter_id, name, times, timezone, active in schedule_data:
            if not active:
                continue
            schedule_times = times or default_times
            target_timezone = timezone or default_timezone
            for time_str in schedule_times:
                try:
                    hour, minute = time_str.split(":", 1)
                except ValueError:
                    logger.warning("Invalid schedule time '%s' for newsletter %s", time_str, newsletter_id)
                    continue
                trigger = CronTrigger(hour=int(hour), minute=int(minute), timezone=target_timezone)
                job_id = self._job_id(newsletter_id, time_str)
                self.scheduler.add_job(
                    self._run_newsletter,
                    trigger=trigger,
                    id=job_id,
                    replace_existing=True,
                    kwargs={"newsletter_id": newsletter_id},
                )
                logger.info(
                    "Scheduled newsletter %s (%s) at %s %s",
                    name,
                    newsletter_id,
                    time_str,
                    target_timezone,
                )

    async def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self._started = False
            logger.info("Scheduler stopped")

    async def _run_newsletter(self, newsletter_id: int) -> None:
        try:
            await task_service.run_newsletter_once(newsletter_id)
        except Exception:
            logger.exception("Scheduled run failed for newsletter %s", newsletter_id)

    def _clear_newsletter_jobs(self) -> None:
        for job in list(self.scheduler.get_jobs()):
            if job.id.startswith("newsletter-"):
                self.scheduler.remove_job(job.id)

    @staticmethod
    def _job_id(newsletter_id: int, time_str: str) -> str:
        return f"newsletter-{newsletter_id}-{time_str.replace(':', '')}"


scheduler = SchedulerManager()
