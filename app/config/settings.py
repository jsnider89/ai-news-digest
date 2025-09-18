"""Application configuration and environment management."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.config.models import iter_catalog, get_model_option

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9 fallback
    from backports.zoneinfo import ZoneInfo  # type: ignore


load_dotenv()


def _detect_timezone() -> str:
    tz_env = (
        os.environ.get("TZ")
        or os.environ.get("LOCAL_TIMEZONE")
        or os.environ.get("APP_TIMEZONE")
    )
    if tz_env:
        return tz_env

    try:
        import tzlocal

        local_tz = tzlocal.get_localzone()
        return str(local_tz)
    except Exception:
        return "UTC"


class Settings(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    app_name: str = Field(default="AI News Digest", description="Human readable app name")
    environment: str = Field(default="development", description="Runtime environment name")

    data_dir: Path = Field(default=Path("data"), description="Directory for persistent data")
    database_url: str = Field(
        default="sqlite+aiosqlite:///data/app.db",
        description="SQLAlchemy connection string",
    )

    default_timezone: str = Field(
        default_factory=_detect_timezone,
        description="Olson timezone identifier used for scheduling",
    )

    ai_provider_order: List[str] = Field(
        default_factory=lambda: ["openai", "gemini", "anthropic"],
        description="Preferred provider sequence",
    )
    available_models: List[str] = Field(
        default_factory=lambda: [option.value for option in iter_catalog()],
        description="Selectable model catalogue for the admin UI",
    )
    primary_model: str = Field(default_factory=lambda: iter_catalog()[0].value, description="Primary AI model")
    secondary_model: str = Field(default_factory=lambda: iter_catalog()[1].value, description="Fallback AI model")
    reasoning_level: str = Field(default="medium", description="Reasoning level for OpenAI models")
    available_reasoning_levels: List[str] = Field(
        default_factory=lambda: ["low", "medium", "high"],
        description="Reasoning effort presets",
    )

    resend_api_key: Optional[str] = Field(default=None, description="Resend API key")
    resend_from_email: str = Field(
        default="market-intel@example.com",
        description="Default From address for digests",
    )
    resend_from_name: str = Field(default="News Digest", description="Default sender name")
    default_recipients: List[str] = Field(
        default_factory=list,
        description="Global recipient list",
    )

    default_send_times: List[str] = Field(
        default_factory=lambda: ["06:30", "17:30"],
        description="Times (HH:MM) newsletters should run by default",
    )

    @field_validator("default_recipients", mode="before")
    @classmethod
    def _split_recipients(cls, value: Optional[str | List[str]]) -> List[str]:
        if not value:
            return []
        if isinstance(value, list):
            return value
        # Split on both commas and newlines, then filter out empty strings
        import re
        return [item.strip() for item in re.split(r'[,\n]', value) if item.strip()]

    @field_validator("default_timezone")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        ZoneInfo(value)
        return value

    @field_validator("default_send_times", mode="after")
    @classmethod
    def _validate_times(cls, value: List[str]) -> List[str]:
        valid: List[str] = []
        for entry in value:
            if len(entry) != 5 or entry[2] != ":":
                continue
            hour, minute = entry.split(":", 1)
            if hour.isdigit() and minute.isdigit() and 0 <= int(hour) < 24 and 0 <= int(minute) < 60:
                valid.append(entry)
        return valid or ["06:30", "17:30"]

    @field_validator("primary_model", "secondary_model")
    @classmethod
    def _validate_model(cls, value: str) -> str:
        if not value:
            raise ValueError("Model cannot be empty")
        option = get_model_option(value)
        if option is None:
            raise ValueError(f"Unknown model '{value}'")
        return option.value

    @field_validator("reasoning_level")
    @classmethod
    def _validate_reasoning(cls, value: str) -> str:
        allowed = {"low", "medium", "high"}
        value_lower = value.lower()
        if value_lower not in allowed:
            raise ValueError("Reasoning level must be low, medium, or high")
        return value_lower

    def database_path(self) -> Path:
        if self.database_url.startswith("sqlite"):
            if "///" in self.database_url:
                path = self.database_url.split("///", 1)[1]
            else:
                path = self.database_url.split(":", 1)[-1]
            return Path(path)
        raise ValueError("Database path only available for sqlite URLs")


_ENV_MAPPING = {
    "APP_NAME": "app_name",
    "ENVIRONMENT": "environment",
    "DATABASE_URL": "database_url",
    "DEFAULT_TIMEZONE": "default_timezone",
    "AI_PROVIDER_ORDER": "ai_provider_order",
    "PRIMARY_MODEL": "primary_model",
    "SECONDARY_MODEL": "secondary_model",
    "REASONING_LEVEL": "reasoning_level",
    "RESEND_API_KEY": "resend_api_key",
    "RESEND_FROM_EMAIL": "resend_from_email",
    "RESEND_FROM_NAME": "resend_from_name",
    "DEFAULT_RECIPIENTS": "default_recipients",
    "DEFAULT_SEND_TIMES": "default_send_times",
    "AVAILABLE_MODELS": "available_models",
    "AVAILABLE_REASONING_LEVELS": "available_reasoning_levels",
}


def _load_settings() -> Settings:
    data: dict[str, object] = {}
    for env_name, field_name in _ENV_MAPPING.items():
        if env_name not in os.environ:
            continue
        value = os.environ[env_name]
        if field_name in {"ai_provider_order", "default_send_times", "available_models", "available_reasoning_levels"}:
            data[field_name] = [item.strip() for item in value.split(",") if item.strip()]
        else:
            data[field_name] = value
    return Settings(**data)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = _load_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
