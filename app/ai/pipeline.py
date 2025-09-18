"""Helpers for loading configurable AI provider pipelines."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import yaml

PIPELINE_FILE = Path("config/ai_pipeline.yml")


@dataclass
class ProviderConfig:
    provider: str
    model: str
    reasoning_effort: str | None = None
    verbosity: str | None = None


def load_pipeline(config_path: Path | None = None) -> List[ProviderConfig]:
    """Load provider pipeline from YAML configuration."""
    path = config_path or PIPELINE_FILE
    if not path.exists():
        raise FileNotFoundError(f"AI pipeline config not found at {path}")
    data = yaml.safe_load(path.read_text())
    entries = data.get("pipeline") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise ValueError("Pipeline configuration must contain a 'pipeline' list")
    configs: List[ProviderConfig] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        configs.append(
            ProviderConfig(
                provider=str(entry.get("provider")),
                model=str(entry.get("model")),
                reasoning_effort=entry.get("reasoning_effort"),
                verbosity=entry.get("verbosity"),
            )
        )
    if not configs:
        raise ValueError("No provider configurations could be loaded")
    return configs


def dump_default_pipeline(destination: Path | None = None) -> Path:
    """Write a default pipeline file if one does not exist."""
    path = destination or PIPELINE_FILE
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pipeline": [
            {
                "provider": "openai",
                "model": "gpt-5-mini",
                "reasoning_effort": "medium",
                "verbosity": "medium",
            },
            {"provider": "gemini", "model": "gemini-2.5-flash"},
            {"provider": "anthropic", "model": "claude-3-haiku-20240307"},
        ]
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False))
    return path

