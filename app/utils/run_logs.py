"""Helpers for capturing structured log entries during pipeline runs."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, List, TypedDict

from app.utils.logging import SecureFormatter


class CapturedRunLog(TypedDict):
    timestamp: datetime
    level: str
    logger: str
    message: str
    exception: str | None


class _RunLogCaptureHandler(logging.Handler):
    """Collect log records emitted during a run."""

    def __init__(self) -> None:
        super().__init__()
        self._formatter = SecureFormatter("%(message)s")
        self.entries: List[CapturedRunLog] = []

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - thin wrapper
        try:
            message = self._formatter.format(record)
        except Exception:  # pragma: no cover - fall back to basic formatting
            message = record.getMessage()

        exception_text: str | None = None
        if record.exc_info:
            try:
                exception_text = self._formatter.formatException(record.exc_info)
            except Exception:  # pragma: no cover - defensive
                exception_text = logging.Formatter().formatException(record.exc_info)

        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).replace(tzinfo=None)
        self.entries.append(
            {
                "timestamp": timestamp,
                "level": record.levelname,
                "logger": record.name,
                "message": message,
                "exception": exception_text,
            }
        )


@contextmanager
def capture_run_logs() -> Iterator[List[CapturedRunLog]]:
    """Attach a temporary handler that captures aggregator log output."""

    handler = _RunLogCaptureHandler()
    handler.setLevel(logging.NOTSET)
    logger = logging.getLogger("market_aggregator")
    logger.addHandler(handler)
    try:
        yield handler.entries
    finally:
        logger.removeHandler(handler)
