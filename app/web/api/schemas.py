"""Pydantic models shared across API routes."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator
from datetime import datetime
from zoneinfo import ZoneInfo


def _validate_schedule_time(value: str) -> str:
    if len(value) != 5 or value[2] != ":":
        raise ValueError("Times must be in HH:MM format")
    hour, minute = value.split(":", 1)
    if not hour.isdigit() or not minute.isdigit():
        raise ValueError("Times must be numeric")
    if not (0 <= int(hour) < 24 and 0 <= int(minute) < 60):
        raise ValueError("Invalid time")
    return value


class NewsletterFeedInput(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    category: Optional[str] = None
    enabled: bool = True


class NewsletterFeedOutput(BaseModel):
    url: str
    title: Optional[str] = None
    category: Optional[str] = None
    enabled: bool = True

    class Config:
        from_attributes = True


class NewsletterCreate(BaseModel):
    slug: str = Field(..., pattern=r"^[a-z0-9-]+$", max_length=64)
    name: str = Field(..., max_length=120)
    timezone: str
    schedule_times: List[str] = Field(default_factory=list)
    include_watchlist: bool = False
    newsletter_type: str = "general_business"
    verbosity_level: str = "medium"
    custom_prompt: str = ""
    feeds: List[NewsletterFeedInput]
    watchlist_symbols: List[str] = Field(default_factory=list)

    @field_validator("schedule_times")
    @classmethod
    def validate_time_format(cls, value: List[str]) -> List[str]:
        return [_validate_schedule_time(item) for item in value]

    @field_validator("watchlist_symbols", mode="before")
    @classmethod
    def normalise_symbols(cls, value):  # type: ignore[override]
        if isinstance(value, str):
            value = [item.strip() for item in value.split(",") if item.strip()]
        return [item.upper() for item in value]


class NewsletterResponse(BaseModel):
    id: int
    slug: str
    name: str
    timezone: str
    schedule_times: List[str]
    include_watchlist: bool
    newsletter_type: str
    verbosity_level: str
    custom_prompt: str
    active: bool

    class Config:
        from_attributes = True


class RunResponse(BaseModel):
    newsletter_id: int
    success: bool
    ai_provider: str
    articles: int
    feed_statuses: List[str]
    subject: Optional[str]
    run_id: Optional[int] = None



class SettingsResponse(BaseModel):
    default_timezone: str
    default_send_times: List[str]
    ai_provider_order: List[str]
    primary_model: str
    secondary_model: str
    reasoning_level: str
    resend_from_email: str
    resend_from_name: str
    default_recipients: List[str]
    available_models: List[str]
    available_reasoning_levels: List[str]


class SettingsUpdate(BaseModel):
    default_timezone: Optional[str] = None
    default_send_times: Optional[List[str]] = None
    primary_model: Optional[str] = None
    secondary_model: Optional[str] = None
    reasoning_level: Optional[str] = None
    default_recipients: Optional[List[str]] = None

    @field_validator('default_send_times')
    @classmethod
    def validate_schedule_time(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        validated = []
        for item in value:
            if len(item) != 5 or item[2] != ':':
                raise ValueError('Times must be in HH:MM format')
            hour, minute = item.split(':', 1)
            if not hour.isdigit() or not minute.isdigit():
                raise ValueError('Times must be numeric')
            if not (0 <= int(hour) < 24 and 0 <= int(minute) < 60):
                raise ValueError('Invalid time')
            validated.append(item)
        return validated

    @field_validator('default_timezone')
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        ZoneInfo(value)
        return value

    @field_validator('primary_model', 'secondary_model')
    @classmethod
    def validate_model(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return value.strip()

    @field_validator('default_recipients', mode='before')
    @classmethod
    def parse_recipients(cls, value):  # type: ignore[override]
        if value is None:
            return value
        if isinstance(value, str):
            import re
            return [item.strip() for item in re.split(r'[,\n]', value) if item.strip()]
        return value


class RunSummary(BaseModel):
    id: int
    newsletter_id: int
    newsletter_name: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    ai_provider: Optional[str]
    article_count: int
    error_message: Optional[str]

    class Config:
        from_attributes = True



class NewsletterUpdate(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None
    schedule_times: Optional[List[str]] = None
    include_watchlist: Optional[bool] = None
    newsletter_type: Optional[str] = None
    verbosity_level: Optional[str] = None
    custom_prompt: Optional[str] = None
    feeds: Optional[List[NewsletterFeedInput]] = None
    watchlist_symbols: Optional[List[str]] = None
    active: Optional[bool] = None

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        ZoneInfo(value)
        return value

    @field_validator('schedule_times')
    @classmethod
    def ensure_valid_times(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        return [_validate_schedule_time(item) for item in value]

    @field_validator('watchlist_symbols', mode='before')
    @classmethod
    def normalise_symbols(cls, value):  # type: ignore[override]
        if value is None:
            return value
        if isinstance(value, str):
            value = [item.strip() for item in value.split(',') if item.strip()]
        return [item.upper() for item in value]


class NewsletterDetail(NewsletterResponse):
    feeds: List[NewsletterFeedOutput]
    watchlist_symbols: List[str]

    class Config:
        from_attributes = True
