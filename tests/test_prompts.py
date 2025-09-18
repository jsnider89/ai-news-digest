from app.ai.prompts import build_prompt, load_system_prompt


def test_build_prompt_includes_sections():
    prompt = build_prompt(
        articles_text="### Source A\n- **Title**\n  Summary",
        market_text="| Symbol | Price |\n| --- | --- |\n| SPY | $500 |",
        watchlist=["SPY"],
        custom_prompt="Custom instructions",
    )
    assert "## Market Data" in prompt
    assert "Focus especially on these watchlist tickers: SPY" in prompt
    assert "Custom instructions" in prompt


def test_system_prompt_not_empty():
    system_prompt = load_system_prompt()
    assert isinstance(system_prompt, str)
    assert len(system_prompt.strip()) > 0


def test_build_prompt_handles_missing_market_data():
    prompt = build_prompt(
        articles_text="### Source A\n- **Title**",
        market_text=None,
        watchlist=[],
        custom_prompt=None,
    )
    assert "No direct market performance data" not in prompt
    assert "## Market Data" not in prompt


def test_build_prompt_includes_market_instructions_when_watchlist_enabled():
    prompt = build_prompt(
        articles_text="### Source A\n- **Title**",
        market_text=None,
        watchlist=["spy", "QQQ"],
        custom_prompt=None,
    )
    assert "When the market symbols tab is enabled" in prompt
    assert "No direct market performance data" in prompt


def test_build_prompt_skips_market_instructions_without_watchlist():
    prompt = build_prompt(
        articles_text="### Source A\n- **Title**",
        market_text="",
        watchlist=[],
        custom_prompt=None,
    )
    assert "When the market symbols tab is enabled" not in prompt
    assert "No direct market performance data" not in prompt
