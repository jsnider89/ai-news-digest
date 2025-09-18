"""In-process log buffer for exposing recent log entries via the API."""
from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Deque, List


class LogBufferHandler(logging.Handler):
    """Logging handler that keeps a rolling buffer of formatted log records."""

    def __init__(self, capacity: int = 1000) -> None:
        super().__init__()
        self.capacity = capacity
        self._entries: Deque[dict[str, Any]] = deque(maxlen=capacity)
        self._lock = Lock()

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - thin wrapper
        formatter = self.formatter or logging.Formatter("%(message)s")
        try:
            message = formatter.format(record)
        except Exception:  # pragma: no cover - defensive fallback
            message = record.getMessage()

        entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }
        if record.exc_info:
            entry["exception"] = formatter.formatException(record.exc_info)  # type: ignore[arg-type]

        with self._lock:
            self._entries.append(entry)

    def get_entries(self, limit: int) -> List[dict[str, Any]]:
        """Return up to ``limit`` entries (oldest-to-newest) without mutating the buffer."""
        if limit <= 0:
            limit = self.capacity
        with self._lock:
            if limit >= len(self._entries):
                return list(self._entries)
            return list(self._entries)[-limit:]

    def size(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


_log_buffer_handler: LogBufferHandler | None = None


def get_log_buffer_handler(capacity: int = 1000) -> LogBufferHandler:
    """Return the singleton in-memory log buffer handler."""
    global _log_buffer_handler
    if _log_buffer_handler is None:
        _log_buffer_handler = LogBufferHandler(capacity=capacity)
    return _log_buffer_handler

