"""Routes for managing newsletters."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.data import repositories, models
from app.tasks import service as task_service
from app.tasks.scheduler import scheduler
from sqlalchemy import select

from . import deps, schemas

router = APIRouter(prefix="/api/newsletters", tags=["newsletters"])


def _serialize_newsletter(model) -> schemas.NewsletterDetail:
    return schemas.NewsletterDetail(
        id=model.id,
        slug=model.slug,
        name=model.name,
        timezone=model.timezone,
        schedule_times=model.schedule_times,
        include_watchlist=model.include_watchlist,
        newsletter_type=model.newsletter_type,
        verbosity_level=model.verbosity_level,
        custom_prompt=model.custom_prompt,
        active=model.active,
        feeds=[
            schemas.NewsletterFeedOutput(
                url=feed.url,
                title=feed.title,
                category=feed.category,
                enabled=feed.enabled,
            )
            for feed in model.feeds
        ],
        watchlist_symbols=[entry.symbol for entry in model.watchlist],
    )


@router.get("", response_model=list[schemas.NewsletterResponse])
async def list_newsletters(db: AsyncSession = Depends(deps.get_db)):
    newsletters = await repositories.list_newsletters(db)
    return newsletters


@router.get("/{newsletter_id}", response_model=schemas.NewsletterDetail)
async def get_newsletter_detail(newsletter_id: int, db: AsyncSession = Depends(deps.get_db)):
    newsletter = await repositories.get_newsletter(db, newsletter_id)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")
    return _serialize_newsletter(newsletter)


@router.post("", response_model=schemas.NewsletterDetail, status_code=status.HTTP_201_CREATED)
async def create_newsletter(payload: schemas.NewsletterCreate, db: AsyncSession = Depends(deps.get_db)):
    from sqlalchemy.exc import IntegrityError
    import logging
    logger = logging.getLogger(__name__)

    settings = get_settings()
    overrides = await repositories.get_global_settings(db)
    schedule_times = payload.schedule_times or overrides.get("default_send_times") or settings.default_send_times
    timezone = payload.timezone or overrides.get("default_timezone") or settings.default_timezone

    # Auto-generate unique slug from name
    def slugify_name(name: str) -> str:
        return name.lower().strip().replace(' ', '-').replace('_', '-')

    base_slug = slugify_name(payload.name)
    slug = base_slug
    counter = 1

    # Find a unique slug
    while True:
        existing = await db.scalar(select(models.Newsletter).where(models.Newsletter.slug == slug))
        if not existing:
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
        if counter > 100:  # Prevent infinite loop
            raise HTTPException(status_code=400, detail="Could not generate unique slug")

    logger.info(f"Creating newsletter with auto-generated slug: {slug}")
    newsletter = await repositories.create_newsletter(
        db,
        slug=slug,
        name=payload.name,
        timezone=timezone,
        schedule_times=schedule_times,
        include_watchlist=payload.include_watchlist,
        newsletter_type=payload.newsletter_type,
        verbosity_level=payload.verbosity_level,
        custom_prompt=payload.custom_prompt,
        feeds=[feed.model_dump() for feed in payload.feeds],
        watchlist_symbols=payload.watchlist_symbols,
    )
    await db.commit()
    # Reload newsletter with relationships
    newsletter = await repositories.get_newsletter(db, newsletter.id)

    await scheduler.refresh_jobs()
    return _serialize_newsletter(newsletter)


@router.put("/{newsletter_id}", response_model=schemas.NewsletterDetail)
async def update_newsletter(
    newsletter_id: int,
    payload: schemas.NewsletterUpdate,
    db: AsyncSession = Depends(deps.get_db),
):
    newsletter = await repositories.get_newsletter(db, newsletter_id)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")

    updated = await repositories.update_newsletter(
        db,
        newsletter,
        name=payload.name,
        timezone=payload.timezone,
        schedule_times=payload.schedule_times,
        include_watchlist=payload.include_watchlist,
        newsletter_type=payload.newsletter_type,
        verbosity_level=payload.verbosity_level,
        custom_prompt=payload.custom_prompt,
        feeds=[feed.model_dump() for feed in payload.feeds] if payload.feeds is not None else None,
        watchlist_symbols=payload.watchlist_symbols,
        active=payload.active,
    )
    await db.commit()
    await scheduler.refresh_jobs()
    return _serialize_newsletter(updated)


@router.delete("/{newsletter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_newsletter(newsletter_id: int, db: AsyncSession = Depends(deps.get_db)):
    newsletter = await repositories.get_newsletter(db, newsletter_id)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")
    await repositories.delete_newsletter(db, newsletter_id)
    await db.commit()
    await scheduler.refresh_jobs()
    return None


@router.post("/{newsletter_id}/run", response_model=schemas.RunResponse)
async def run_newsletter(newsletter_id: int):
    try:
        result = await task_service.run_newsletter_once(newsletter_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result


@router.post("/{newsletter_id}/reset", response_model=dict)
async def reset_newsletter(newsletter_id: int, hours: int = 24, db: AsyncSession = Depends(deps.get_db)):
    deleted = await repositories.reset_recent_runs(db, newsletter_id=newsletter_id, hours=hours)
    await db.commit()
    return {"deleted_runs": deleted}
