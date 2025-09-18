"""Market data client for Finnhub quotes."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Iterable, Sequence

import httpx

logger = logging.getLogger("market_aggregator.ingest.market")


class MarketDataClient:
    """Simple Finnhub quote fetcher."""

    def __init__(
        self,
        api_key: str | None,
        *,
        base_url: str = "https://finnhub.io/api/v1",
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout, headers={"User-Agent": "MarketAggregator/1.0"})

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch_quotes(self, symbols: Sequence[str]) -> list[dict]:
        if not self.api_key:
            logger.warning("FINNHUB_API_KEY not configured; market data disabled")
            return []

        tasks = [self._fetch(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        quotes: list[dict] = []
        for result in results:
            if isinstance(result, dict):
                quotes.append(result)
        return quotes

    async def _fetch(self, symbol: str) -> dict:
        params = {"symbol": symbol, "token": self.api_key}
        try:
            response = await self._client.get(f"{self.base_url}/quote", params=params)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("Finnhub returned %s for %s", exc.response.status_code, symbol)
            return _empty_quote(symbol, error=f"HTTP {exc.response.status_code}")
        except Exception as exc:  # pragma: no cover - network failure logging
            logger.exception("Error fetching quote for %s", symbol)
            return _empty_quote(symbol, error=str(exc))

        current = payload.get("c")
        if current is None:
            return _empty_quote(symbol, error="No data")
        return {
            "symbol": symbol.upper(),
            "current": float(current),
            "change": float(payload.get("d") or 0.0),
            "change_percent": float(payload.get("dp") or 0.0),
            "timestamp": datetime.utcnow().isoformat(),
        }


def _empty_quote(symbol: str, *, error: str) -> dict:
    return {
        "symbol": symbol.upper(),
        "current": 0.0,
        "change": 0.0,
        "change_percent": 0.0,
        "error": error,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def fetch_quotes(api_key: str | None, symbols: Iterable[str]) -> list[dict]:
    client = MarketDataClient(api_key)
    try:
        return await client.fetch_quotes(list(symbols))
    finally:
        await client.close()

