"""Catalog of supported AI models and provider metadata."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class ModelOption:
    value: str
    label: str
    provider: str
    supports_reasoning: bool = False


# Default model catalog - used as fallback if AVAILABLE_MODELS env var is not set
_DEFAULT_MODEL_CATALOG: tuple[ModelOption, ...] = (
    ModelOption("gpt-5-mini", "GPT-5 Mini (OpenAI)", provider="openai", supports_reasoning=True),
    ModelOption("gpt-5-nano", "GPT-5 Nano (OpenAI)", provider="openai", supports_reasoning=True),
    ModelOption("gpt-4.1-mini", "GPT-4.1 Mini (OpenAI)", provider="openai", supports_reasoning=True),
    ModelOption("gemini-2.5-flash", "Gemini 2.5 Flash (Google)", provider="gemini", supports_reasoning=False),
    ModelOption("gemini-2.0-pro", "Gemini 2.0 Pro (Google)", provider="gemini", supports_reasoning=False),
    ModelOption("claude-3-haiku-20240307", "Claude 3 Haiku (Anthropic)", provider="anthropic", supports_reasoning=False),
    ModelOption("claude-3-sonnet-20240229", "Claude 3 Sonnet (Anthropic)", provider="anthropic", supports_reasoning=False),
)


def _parse_model_catalog_from_env() -> tuple[ModelOption, ...]:
    """Parse AVAILABLE_MODELS environment variable.

    Format: model_id:Display Label:provider:true/false,model_id2:Label2:provider2:false,...
    Example: gpt-5-mini:GPT-5 Mini (OpenAI):openai:true,gemini-2.5-flash:Gemini 2.5 Flash:gemini:false
    """
    env_models = os.getenv("AVAILABLE_MODELS", "").strip()
    if not env_models:
        return _DEFAULT_MODEL_CATALOG

    models = []
    for entry in env_models.split(","):
        entry = entry.strip()
        if not entry:
            continue

        parts = entry.split(":")
        if len(parts) != 4:
            continue  # Skip malformed entries

        model_id, label, provider, supports_reasoning_str = parts
        supports_reasoning = supports_reasoning_str.strip().lower() == "true"

        models.append(ModelOption(
            value=model_id.strip(),
            label=label.strip(),
            provider=provider.strip(),
            supports_reasoning=supports_reasoning
        ))

    # Return defaults if parsing failed
    return tuple(models) if models else _DEFAULT_MODEL_CATALOG


# Load model catalog from environment or use defaults
_MODEL_CATALOG = _parse_model_catalog_from_env()


def iter_catalog(values: Optional[Iterable[str]] = None) -> list[ModelOption]:
    """Get list of available model options."""
    if values is None:
        return list(_MODEL_CATALOG)
    selected = []
    lookup = {option.value: option for option in _MODEL_CATALOG}
    for value in values:
        option = lookup.get(value)
        if option:
            selected.append(option)
    return selected


def get_model_option(value: str) -> Optional[ModelOption]:
    """Get a specific model option by its value/ID."""
    for option in _MODEL_CATALOG:
        if option.value == value:
            return option
    return None

