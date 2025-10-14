"""Multi-provider AI client with cascading fallbacks."""
from __future__ import annotations

import logging
from typing import Sequence, Tuple

from .pipeline import ProviderConfig, load_pipeline
from .providers import AIProvider, ProviderError, OpenAIProvider, GeminiProvider, AnthropicProvider
from app.config.settings import get_settings
from app.config.models import get_model_option

logger = logging.getLogger("market_aggregator.ai")

# Provider registry mapping provider names to classes
_PROVIDER_MAP = {
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "anthropic": AnthropicProvider,
}


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
