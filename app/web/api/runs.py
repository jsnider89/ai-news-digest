"""Run history routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.data import repositories
from app.utils.time_utils import format_local_time

from . import deps, schemas

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("", response_model=list[schemas.RunSummary])
async def list_runs(limit: int = 20, db: AsyncSession = Depends(deps.get_db)):
    runs = await repositories.list_recent_runs(db, limit=limit)
    summaries: list[schemas.RunSummary] = []
    for run in runs:
        summaries.append(
            schemas.RunSummary(
                id=run.id,
                newsletter_id=run.newsletter_id,
                newsletter_name=run.newsletter.name if run.newsletter else "",
                status=run.status,
                started_at=format_local_time(run.started_at),
                finished_at=format_local_time(run.finished_at),
                ai_provider=run.ai_provider,
                article_count=run.article_count,
                error_message=run.error_message,
            )
        )
    return summaries


@router.get("/{run_id}/digest", response_model=dict)
async def get_run_digest(run_id: int, db: AsyncSession = Depends(deps.get_db)):
    digest = await repositories.get_run_digest(db, run_id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found for run")
    return {"run_id": run_id, "subject": digest.subject, "html": digest.html_content}

