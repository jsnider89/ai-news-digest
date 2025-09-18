"""Logging utilities with basic secret scrubbing."""
from __future__ import annotations

import logging
import os
import re
from typing import Iterable

from app.utils.log_buffer import get_log_buffer_handler

_SECRET_PATTERNS: tuple[str, ...] = (
    r"sk-[A-Za-z0-9]{20,}",  # OpenAI style
    r"resend_[A-Za-z0-9]{20,}",
    r"[A-Za-z0-9]{32,}",
)


class SecureFormatter(logging.Formatter):
    """Formatter that redacts strings looking like secrets."""

    def __init__(self, *args, secret_patterns: Iterable[str] | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._patterns = [re.compile(pattern) for pattern in (secret_patterns or _SECRET_PATTERNS)]

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - simple wrapper
        message = super().format(record)
        for pattern in self._patterns:
            message = pattern.sub("[REDACTED]", message)
        return message


def setup_logging(name: str = "market_aggregator", level: str | int = "INFO") -> logging.Logger:
    """Configure logging for the application if it is not already configured."""

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    handler.setFormatter(SecureFormatter(fmt))
    logger.addHandler(handler)

    buffer_handler = get_log_buffer_handler()
    if buffer_handler not in logger.handlers:
        buffer_handler.setFormatter(SecureFormatter("%(message)s"))
        logger.addHandler(buffer_handler)
    logger.setLevel(level if isinstance(level, int) else getattr(logging, str(level).upper(), logging.INFO))

    # Avoid duplicate logging from child loggers
    logger.propagate = False
    return logger


def mask_env_vars(*names: str) -> None:
    """Unset specified environment variables from appearing in process-level logs."""

    for name in names:
        value = os.environ.get(name)
        if value:
            os.environ[name] = "***"
