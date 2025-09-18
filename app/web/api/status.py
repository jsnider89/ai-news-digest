"""Health and status endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import and_, func, select
from sqlalchemy.orm import joinedload

from app.data import models
from app.data.database import SessionLocal
from app.tasks.scheduler import scheduler

router = APIRouter(tags=["status"])


def _serialize_run(record: models.RunRecord | None) -> dict | None:
    if record is None:
        return None
    return {
        "id": record.id,
        "newsletter_id": record.newsletter_id,
        "newsletter_name": record.newsletter.name if record.newsletter else "",
        "status": record.status,
        "started_at": record.started_at.isoformat() if record.started_at else None,
        "finished_at": record.finished_at.isoformat() if record.finished_at else None,
        "ai_provider": record.ai_provider,
        "article_count": record.article_count,
        "error_message": record.error_message,
    }


@router.get("/health")
async def healthcheck() -> dict:
    now = datetime.now(timezone.utc)
    today_start = now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)

    async with SessionLocal() as session:
        total_newsletters = await session.scalar(select(func.count(models.Newsletter.id))) or 0
        active_newsletters = (
            await session.scalar(select(func.count(models.Newsletter.id)).where(models.Newsletter.active.is_(True)))
            or 0
        )

        latest_run_stmt = (
            select(models.RunRecord)
            .options(joinedload(models.RunRecord.newsletter))
            .order_by(models.RunRecord.started_at.desc())
            .limit(1)
        )
        latest_run = (await session.execute(latest_run_stmt)).scalars().first()

        recent_runs_stmt = (
            select(models.RunRecord)
            .options(joinedload(models.RunRecord.newsletter))
            .order_by(models.RunRecord.started_at.desc())
            .limit(10)
        )
        recent_runs = list((await session.execute(recent_runs_stmt)).scalars())

        runs_today = (
            await session.scalar(
                select(func.count(models.RunRecord.id)).where(models.RunRecord.started_at >= today_start)
            )
            or 0
        )
        failures_today = (
            await session.scalar(
                select(func.count(models.RunRecord.id)).where(
                    and_(models.RunRecord.started_at >= today_start, models.RunRecord.status == "failed")
                )
            )
            or 0
        )

        newsletter_rows = await session.execute(
            select(
                models.Newsletter.id,
                models.Newsletter.name,
                models.Newsletter.active,
                models.Newsletter.schedule_times,
                models.Newsletter.timezone,
            )
        )
        newsletter_summary = [
            {
                "id": row.id,
                "name": row.name,
                "active": row.active,
                "schedule_times": list(row.schedule_times or []),
                "timezone": row.timezone,
            }
            for row in newsletter_rows
        ]

    scheduler_jobs: list[dict] = []
    next_runs_map: dict[int, list[str]] = {}
    newsletter_names = {item["id"]: item["name"] for item in newsletter_summary}
    try:
        jobs = scheduler.scheduler.get_jobs()
    except Exception:  # pragma: no cover - scheduler access failure
        jobs = []

    for job in jobs:
        newsletter_id: int | None = None
        if job.id.startswith("newsletter-"):
            parts = job.id.split("-", 2)
            if len(parts) >= 3:
                try:
                    newsletter_id = int(parts[1])
                except ValueError:
                    newsletter_id = None
        next_run_time = job.next_run_time.isoformat() if job.next_run_time else None
        scheduler_jobs.append(
            {
                "id": job.id,
                "newsletter_id": newsletter_id,
                "newsletter_name": newsletter_names.get(newsletter_id) if newsletter_id is not None else None,
                "next_run_time": next_run_time,
                "trigger": str(job.trigger),
            }
        )
        if newsletter_id is not None and next_run_time:
            next_runs_map.setdefault(newsletter_id, []).append(next_run_time)

    for summary in newsletter_summary:
        summary["next_run_times"] = sorted(next_runs_map.get(summary["id"], []))

    # Improved health status logic
    status = "ok"
    status_details = []

    # Check if latest run failed (immediate concern)
    if latest_run and latest_run.status == "failed":
        status = "degraded"
        status_details.append(f"Latest run failed: {latest_run.error_message or 'Unknown error'}")

    # Check for recent consecutive failures (more serious)
    consecutive_failures = 0
    for run in recent_runs[:3]:  # Check last 3 runs
        if run.status == "failed":
            consecutive_failures += 1
        else:
            break

    if consecutive_failures >= 2:
        status = "issues"
        status_details.append(f"{consecutive_failures} consecutive failures detected")
    elif failures_today >= 3 and latest_run and latest_run.status == "failed":
        # Multiple failures today AND latest is failed = ongoing issue
        status = "issues"
        status_details.append(f"{failures_today} failures today, latest run failed")

    # Check for inactive newsletters
    if total_newsletters > 0 and active_newsletters == 0:
        status = "degraded" if status == "ok" else status
        status_details.append("No active newsletters")

    return {
        "status": status,
        "status_details": status_details,
        "timestamp": now.isoformat(),
        "metrics": {
            "total_newsletters": total_newsletters,
            "active_newsletters": active_newsletters,
            "runs_today": runs_today,
            "failed_runs_today": failures_today,
        },
        "latest_run": _serialize_run(latest_run),
        "recent_runs": [_serialize_run(run) for run in recent_runs],
        "newsletters": newsletter_summary,
        "scheduler": {
            "running": getattr(scheduler.scheduler, "running", False),
            "job_count": len(scheduler_jobs),
            "jobs": scheduler_jobs,
        },
    }
