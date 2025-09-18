"""Prompt assembly helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

BASE_DIR = Path(__file__).resolve().parent.parent / "prompts"

_BASE_PROMPT_FILE = BASE_DIR / "base_prompt.md"
_FORMAT_FILE = BASE_DIR / "format_instructions.md"
_MARKET_PROMPT_FILE = BASE_DIR / "market_prompt.md"
_SYSTEM_FILE = BASE_DIR / "system_message.md"


def load_system_prompt() -> str:
    return _read_file(_SYSTEM_FILE)


def build_prompt(*, articles_text: str, market_text: str | None = None, watchlist: Iterable[str] | None = None, newsletter_type: str | None = None, custom_prompt: str | None = None) -> str:
    normalized_watchlist = [ticker.upper() for ticker in (watchlist or []) if ticker]
    include_market_instructions = bool(normalized_watchlist)

    sections = [_read_file(_BASE_PROMPT_FILE).strip()]

    # Add newsletter type-specific instructions
    if newsletter_type:
        newsletter_type_file = BASE_DIR / "newsletter_types" / f"{newsletter_type}.md"
        if newsletter_type_file.exists():
            newsletter_instructions = _read_file(newsletter_type_file).strip()
            if newsletter_instructions:
                sections.append(newsletter_instructions)

    if include_market_instructions:
        market_instructions = _read_file(_MARKET_PROMPT_FILE).strip()
        if market_instructions:
            sections.append(market_instructions)

    if market_text:
        sections.append("\n\n## Market Data\n" + market_text.strip())
    elif include_market_instructions:
        sections.append(
            "\n\nNo direct market performance data was supplied for this briefing. Do not fabricate price tables or refer to watchlist tickers unless they are explicitly provided."
        )

    if articles_text:
        sections.append("\n\n## Articles\n" + articles_text.strip())

    if normalized_watchlist:
        tickers = ", ".join(sorted(set(normalized_watchlist)))
        sections.append(f"\n\nFocus especially on these watchlist tickers: {tickers}.")
    if custom_prompt:
        sections.append("\n\n" + custom_prompt.strip())
    format_instructions = _read_file(_FORMAT_FILE).strip()
    if format_instructions:
        sections.append("\n\n" + format_instructions)
    return "\n".join(section for section in sections if section)


def _read_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Prompt fragment not found at {path}")
    return path.read_text(encoding="utf-8")
