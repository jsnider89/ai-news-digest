"""Base provider interface and shared utilities."""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Tuple

from ..pipeline import ProviderConfig


class ProviderError(RuntimeError):
    """Raised when a provider fails to produce a completion."""

    def __init__(self, provider: str, message: str, original: Exception | None = None) -> None:
        super().__init__(f"{provider}: {message}")
        self.provider = provider
        self.original = original


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    def name(self) -> str:
        """Return the human-readable name of this provider."""
        raise NotImplementedError

    @abstractmethod
    def generate(
        self, prompt: str, *, system_prompt: str | None = None, verbosity: str | None = None
    ) -> Tuple[str, dict | None]:
        """Generate a completion from the provider.

        Returns:
            Tuple of (completion_text, usage_dict)
        """
        raise NotImplementedError

    def cleanup(self) -> None:
        """Clean up resources. Optional override."""
        pass


def require_env(name: str) -> str:
    """Get required environment variable or raise RuntimeError."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required for AI provider")
    return value


def normalise_usage(
    payload: dict | None,
    *,
    prompt_key: str,
    completion_key: str,
    total_key: str,
) -> dict | None:
    """Normalize usage statistics from different providers into a common format."""
    if not payload or not isinstance(payload, dict):
        return None

    prompt = payload.get(prompt_key)
    completion = payload.get(completion_key)
    total = payload.get(total_key)

    if total is None and prompt is not None and completion is not None:
        total = prompt + completion

    if all(value is None for value in (prompt, completion, total)):
        return None

    usage: dict[str, int] = {}
    if prompt is not None:
        usage["prompt_tokens"] = int(prompt)
    if completion is not None:
        usage["completion_tokens"] = int(completion)
    if total is not None:
        usage["total_tokens"] = int(total)
    return usage or None


DEFAULT_SYSTEM_PROMPT = (
    "You are a professional financial and market analyst. Produce concise "
    "markdown-formatted briefings with sections, tables, and actionable insight."
)
