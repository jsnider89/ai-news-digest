"""Metadata endpoints for UI configuration options."""
from __future__ import annotations

from fastapi import APIRouter

from app.config.settings import get_settings
from app.config.timezones import build_timezone_options
from app.config.models import iter_catalog

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/options", response_model=dict)
def get_options() -> dict:
    settings = get_settings()
    timezones = build_timezone_options(extra=[settings.default_timezone])
    tz_options = [
        {"value": option.value, "label": option.label}
        for option in timezones
    ]
    model_options = []
    for option in iter_catalog(settings.available_models):
        model_options.append(
            {
                "value": option.value,
                "label": option.label,
                "provider": option.provider,
                "supports_reasoning": option.supports_reasoning,
            }
        )
    return {
        "timezones": tz_options,
        "models": model_options,
        "reasoning_levels": settings.available_reasoning_levels,
        "default_timezone": settings.default_timezone,
    }
