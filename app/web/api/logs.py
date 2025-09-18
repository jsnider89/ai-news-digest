"""Expose recent log entries for the admin dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.data import repositories
from app.utils.log_buffer import get_log_buffer_handler

from . import deps

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("", response_model=dict)
async def list_logs(
    limit: int = Query(200, ge=1, le=1000),
    run_id: int | None = Query(default=None, description="Optional run id to retrieve archived logs for."),
    db: AsyncSession = Depends(deps.get_db),
) -> dict:
    if run_id is not None:
        total = await repositories.count_run_logs(db, run_id=run_id)
        entries = await repositories.list_run_logs(db, run_id=run_id, limit=limit)
        return {
            "entries": [
                {
                    "timestamp": (entry.timestamp.isoformat() if entry.timestamp else None),
                    "level": entry.level,
                    "logger": entry.logger,
                    "message": entry.message,
                    "exception": entry.exception,
                }
                for entry in entries
            ],
            "count": len(entries),
            "limit": limit,
            "available": total,
            "capacity": total,
            "run_id": run_id,
        }

    handler = get_log_buffer_handler()
    entries = handler.get_entries(limit)
    return {
        "entries": entries,
        "count": len(entries),
        "limit": limit,
        "available": handler.size(),
        "capacity": handler.capacity,
    }


@router.delete("", response_model=dict)
def clear_logs() -> dict:
    handler = get_log_buffer_handler()
    handler.clear()
    return {"cleared": True}
