"""Global settings API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.data import repositories
from app.tasks.scheduler import scheduler

from . import deps, schemas

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _compose_response(overrides: dict[str, object]) -> schemas.SettingsResponse:
    env_settings = get_settings()
    timezone = overrides.get("default_timezone", env_settings.default_timezone)
    if not isinstance(timezone, str):
        timezone = env_settings.default_timezone
    send_times = overrides.get("default_send_times", env_settings.default_send_times)
    if not isinstance(send_times, list):
        send_times = env_settings.default_send_times
    primary_model = overrides.get("primary_model", env_settings.primary_model)
    if not isinstance(primary_model, str):
        primary_model = env_settings.primary_model
    secondary_model = overrides.get("secondary_model", env_settings.secondary_model)
    if not isinstance(secondary_model, str):
        secondary_model = env_settings.secondary_model
    reasoning = overrides.get("reasoning_level", env_settings.reasoning_level)
    if not isinstance(reasoning, str):
        reasoning = env_settings.reasoning_level
    recipients = overrides.get("default_recipients", env_settings.default_recipients)
    if isinstance(recipients, str):
        recipients = [recipients]
    if not isinstance(recipients, list):
        recipients = env_settings.default_recipients
    return schemas.SettingsResponse(
        default_timezone=str(timezone),
        default_send_times=list(send_times),
        ai_provider_order=env_settings.ai_provider_order,
        primary_model=str(primary_model),
        secondary_model=str(secondary_model),
        reasoning_level=str(reasoning),
        resend_from_email=env_settings.resend_from_email,
        resend_from_name=env_settings.resend_from_name,
        default_recipients=list(recipients),
        available_models=env_settings.available_models,
        available_reasoning_levels=env_settings.available_reasoning_levels,
    )


@router.get("", response_model=schemas.SettingsResponse)
async def get_global_settings_route(db: AsyncSession = Depends(deps.get_db)):
    overrides = await repositories.get_global_settings(db)
    return _compose_response(overrides)


@router.put("", response_model=schemas.SettingsResponse)
async def update_global_settings_route(
    payload: schemas.SettingsUpdate,
    db: AsyncSession = Depends(deps.get_db),
):
    overrides = await repositories.get_global_settings(db)
    updates: dict[str, object] = {}
    if payload.default_timezone is not None:
        overrides["default_timezone"] = payload.default_timezone
        updates["default_timezone"] = payload.default_timezone
    if payload.default_send_times is not None:
        overrides["default_send_times"] = payload.default_send_times
        updates["default_send_times"] = payload.default_send_times
    if payload.primary_model is not None:
        overrides["primary_model"] = payload.primary_model
        updates["primary_model"] = payload.primary_model
    if payload.secondary_model is not None:
        overrides["secondary_model"] = payload.secondary_model
        updates["secondary_model"] = payload.secondary_model
    if payload.reasoning_level is not None:
        overrides["reasoning_level"] = payload.reasoning_level
        updates["reasoning_level"] = payload.reasoning_level
    if payload.default_recipients is not None:
        overrides["default_recipients"] = payload.default_recipients
        updates["default_recipients"] = payload.default_recipients
    if updates:
        await repositories.upsert_global_settings(db, updates)
        await db.commit()
        await scheduler.refresh_jobs()
    return _compose_response(overrides)
