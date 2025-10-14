"""Google Gemini provider implementation."""
from __future__ import annotations

from typing import Tuple

import requests

from .base import AIProvider, ProviderError, require_env, normalise_usage, DEFAULT_SYSTEM_PROMPT
from ..pipeline import ProviderConfig


class GeminiProvider(AIProvider):
    """Google Gemini API provider."""

    endpoint = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self.api_key = require_env("GEMINI_API_KEY")
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def name(self) -> str:
        return f"Gemini {self.config.model}"

    def generate(
        self, prompt: str, *, system_prompt: str | None = None, verbosity: str | None = None
    ) -> Tuple[str, dict | None]:
        text = f"{system_prompt or DEFAULT_SYSTEM_PROMPT}\n\n{prompt}"
        body = {
            "contents": [
                {
                    "parts": [{"text": text}],
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 12000,
            },
        }
        url = f"{self.endpoint}/models/{self.config.model}:generateContent"

        try:
            response = self._session.post(url, params={"key": self.api_key}, json=body, timeout=120)
            response.raise_for_status()
            payload = response.json()

            candidates = payload.get("candidates") or []
            if not candidates:
                raise ProviderError(self.name(), "No candidates returned")

            content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if not content.strip():
                raise ProviderError(self.name(), "Empty response from Gemini")

            usage = normalise_usage(
                payload.get("usageMetadata", {}),
                prompt_key="promptTokenCount",
                completion_key="candidatesTokenCount",
                total_key="totalTokenCount",
            )
            return content, usage

        except requests.exceptions.RequestException as exc:
            raise ProviderError(self.name(), "Network error", exc) from exc
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(self.name(), str(exc), exc) from exc

    def cleanup(self) -> None:  # pragma: no cover - trivial
        self._session.close()
