"""Multi-provider AI client with cascading fallbacks."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
from typing import Iterable, Optional, Sequence, Tuple

import requests

from .pipeline import ProviderConfig, load_pipeline
from app.config.settings import get_settings
from app.config.models import get_model_option

logger = logging.getLogger("market_aggregator.ai")


class ProviderError(RuntimeError):
    """Raised when a provider fails to produce a completion."""

    def __init__(self, provider: str, message: str, original: Exception | None = None) -> None:
        super().__init__(f"{provider}: {message}")
        self.provider = provider
        self.original = original


class AIProvider(ABC):
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate(self, prompt: str, *, system_prompt: str | None = None, verbosity: str | None = None) -> Tuple[str, dict | None]:
        raise NotImplementedError

    def cleanup(self) -> None:  # pragma: no cover - optional override
        pass


class OpenAIProvider(AIProvider):
    endpoint = "https://api.openai.com/v1/chat/completions"

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        api_key = _require_env("OPENAI_API_KEY")
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def name(self) -> str:
        return f"OpenAI {self.config.model}"

    def generate(self, prompt: str, *, system_prompt: str | None = None, verbosity: str | None = None) -> Tuple[str, dict | None]:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt or _DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        if self.config.model.startswith("gpt-5"):
            payload["max_completion_tokens"] = 8000
            if self.config.reasoning_effort:
                payload["reasoning_effort"] = self.config.reasoning_effort
            # Use passed verbosity or fall back to config verbosity or default
            effective_verbosity = verbosity or self.config.verbosity or "medium"
            payload["verbosity"] = effective_verbosity
            # gpt-5 models don't use temperature/top_p
        else:
            payload.update({"max_tokens": 8000, "temperature": 0.7, "top_p": 0.9})
        try:
            response = self._session.post(self.endpoint, json=payload, timeout=120)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as exc:
                detail: str
                try:
                    detail = response.text
                except Exception:  # pragma: no cover - defensive fallback
                    detail = "<failed to read error body>"
                raise ProviderError(self.name(), f"HTTP {response.status_code}: {detail}", exc) from exc
            body = response.json()
            content = (
                body.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            if not content.strip():
                raise ProviderError(self.name(), "Empty response from OpenAI")
            usage = _normalise_usage(
                body.get("usage", {}),
                prompt_key="prompt_tokens",
                completion_key="completion_tokens",
                total_key="total_tokens",
            )
            return content, usage
        except ProviderError:
            raise
        except requests.exceptions.RequestException as exc:  # pragma: no cover - network
            raise ProviderError(self.name(), "Network error", exc) from exc
        except Exception as exc:  # pragma: no cover - unexpected
            raise ProviderError(self.name(), str(exc), exc) from exc

    def cleanup(self) -> None:  # pragma: no cover - trivial
        self._session.close()


class GeminiProvider(AIProvider):
    endpoint = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self.api_key = _require_env("GEMINI_API_KEY")
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def name(self) -> str:
        return f"Gemini {self.config.model}"

    def generate(self, prompt: str, *, system_prompt: str | None = None, verbosity: str | None = None) -> Tuple[str, dict | None]:
        text = f"{system_prompt or _DEFAULT_SYSTEM_PROMPT}\n\n{prompt}"
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
            usage = _normalise_usage(
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


class AnthropicProvider(AIProvider):
    endpoint = "https://api.anthropic.com/v1/messages"

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        api_key = _require_env("ANTHROPIC_API_KEY")
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

    def generate(self, prompt: str, *, system_prompt: str | None = None, verbosity: str | None = None) -> Tuple[str, dict | None]:
        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt or _DEFAULT_SYSTEM_PROMPT},
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
            usage = _normalise_usage(
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


_PROVIDER_MAP = {
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "anthropic": AnthropicProvider,
}

_DEFAULT_SYSTEM_PROMPT = (
    "You are a professional financial and market analyst. Produce concise "
    "markdown-formatted briefings with sections, tables, and actionable insight."
)


class AIClient:
    """Factory and dispatcher for provider cascade."""

    def __init__(self, pipeline: Sequence[ProviderConfig] | None = None) -> None:
        base_pipeline = list(pipeline or load_pipeline())
        settings = get_settings()

        def build_config(model_value: str) -> ProviderConfig | None:
            option = get_model_option(model_value)
            if not option:
                logger.warning("Unknown model '%s' requested", model_value)
                return None
            config = ProviderConfig(provider=option.provider, model=option.value)
            if option.provider == "openai":
                config.reasoning_effort = settings.reasoning_level
                config.verbosity = "medium"
            return config

        configs: list[ProviderConfig] = []

        primary_config = build_config(settings.primary_model)
        if primary_config:
            configs.append(primary_config)

        if settings.secondary_model and settings.secondary_model != settings.primary_model:
            secondary_config = build_config(settings.secondary_model)
            if secondary_config and all(secondary_config.provider != existing.provider for existing in configs):
                configs.append(secondary_config)

        for entry in base_pipeline:
            if any(existing.provider == entry.provider for existing in configs):
                continue
            configs.append(entry)

        self.providers: list[AIProvider] = []
        for config in configs:
            provider_cls = _PROVIDER_MAP.get(config.provider)
            if not provider_cls:
                logger.warning("Unknown provider '%s' in pipeline", config.provider)
                continue
            try:
                provider = provider_cls(config)
                self.providers.append(provider)
            except Exception as exc:
                logger.warning("Failed to initialise provider %s: %s", config.provider, exc)
        if not self.providers:
            logger.error("No AI providers initialised; falling back to static analysis")

    def available_providers(self) -> list[str]:
        return [provider.name() for provider in self.providers]

    def generate(self, prompt: str, *, system_prompt: str | None = None, verbosity: str | None = None) -> Tuple[str, str, dict | None]:
        for index, provider in enumerate(self.providers):
            try:
                output, usage = provider.generate(prompt, system_prompt=system_prompt, verbosity=verbosity)
                label = provider.name()
                if index > 0:
                    label = f"{label} (fallback)"
                return output, label, usage
            except ProviderError as exc:
                logger.warning("Provider failure: %s", exc)
        logger.error("All providers failed; returning static analysis")
        return self._basic_analysis(), "basic", None

    def _basic_analysis(self) -> str:
        return (
            "## Market Analysis Unavailable\n\n"
            "All configured AI providers failed to respond. Please check API keys and network connectivity."
        )

    def close(self) -> None:
        for provider in self.providers:
            try:
                provider.cleanup()
            except Exception:  # pragma: no cover - logging only
                logger.debug("Error cleaning up provider %s", provider.name())

def __del__(self) -> None:  # pragma: no cover - GC hook
        self.close()


def _require_env(name: str) -> str:
    import os

    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required for AI provider")
    return value


def _normalise_usage(
    payload: dict | None,
    *,
    prompt_key: str,
    completion_key: str,
    total_key: str,
) -> dict | None:
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
