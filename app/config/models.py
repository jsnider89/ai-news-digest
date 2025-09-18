"""Catalog of supported AI models and provider metadata."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class ModelOption:
    value: str
    label: str
    provider: str
    supports_reasoning: bool = False


_MODEL_CATALOG: tuple[ModelOption, ...] = (
    ModelOption("gpt-5-mini", "GPT-5 Mini (OpenAI)", provider="openai", supports_reasoning=True),
    ModelOption("gpt-5-nano", "GPT-5 Nano (OpenAI)", provider="openai", supports_reasoning=True),
    ModelOption("gpt-4.1-mini", "GPT-4.1 Mini (OpenAI)", provider="openai", supports_reasoning=True),
    ModelOption("gemini-2.5-flash", "Gemini 2.5 Flash (Google)", provider="gemini", supports_reasoning=False),
    ModelOption("gemini-2.0-pro", "Gemini 2.0 Pro (Google)", provider="gemini", supports_reasoning=False),
    ModelOption("claude-3-haiku-20240307", "Claude 3 Haiku (Anthropic)", provider="anthropic", supports_reasoning=False),
    ModelOption("claude-3-sonnet-20240229", "Claude 3 Sonnet (Anthropic)", provider="anthropic", supports_reasoning=False),
)


def iter_catalog(values: Optional[Iterable[str]] = None) -> list[ModelOption]:
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
    for option in _MODEL_CATALOG:
        if option.value == value:
            return option
    return None

