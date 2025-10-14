"""Anthropic Claude provider implementation."""
from __future__ import annotations

from typing import Tuple

import requests

from .base import AIProvider, ProviderError, require_env, normalise_usage, DEFAULT_SYSTEM_PROMPT
from ..pipeline import ProviderConfig


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider."""

    endpoint = "https://api.anthropic.com/v1/messages"

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        api_key = require_env("ANTHROPIC_API_KEY")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
        )

    def name(self) -> str:
        return f"Anthropic {self.config.model}"

    def generate(
        self, prompt: str, *, system_prompt: str | None = None, verbosity: str | None = None
    ) -> Tuple[str, dict | None]:
        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 4000,
            "temperature": 0.7,
        }

        try:
            response = self._session.post(self.endpoint, json=body, timeout=120)
            response.raise_for_status()
            payload = response.json()

            contents = payload.get("content") or []
            if not contents:
                raise ProviderError(self.name(), "No content returned")

            text = contents[0].get("text", "")
            if not text.strip():
                raise ProviderError(self.name(), "Empty response from Anthropic")

            usage = normalise_usage(
                payload.get("usage", {}),
                prompt_key="input_tokens",
                completion_key="output_tokens",
                total_key="total_tokens",
            )
            return text, usage

        except requests.exceptions.RequestException as exc:
            raise ProviderError(self.name(), "Network error", exc) from exc
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(self.name(), str(exc), exc) from exc

    def cleanup(self) -> None:  # pragma: no cover - trivial
        self._session.close()
