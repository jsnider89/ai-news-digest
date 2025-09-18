When the market symbols tab is enabled, extend the briefing with the following sections before the general news content:

1. Begin with `## Market Performance` and provide a proper markdown table summarising every supplied ticker using this exact format:

```
| Symbol | Current Price | Change ($) | Change (%) |
|--------|---------------|------------|------------|
| [TICKER] | $[PRICE] | 🟢/🔴 [CHANGE] | 🟢/🔴 [PERCENT]% |
```

Use 🟢 (green circle) for positive changes and 🔴 (red circle) for negative changes. Always use proper markdown table format with pipes (|) and header separators. Highlight any watchlist tickers that appear.
2. Follow with `## Top Market & Economy Stories` containing exactly five numbered entries focused on the most significant financial developments. Anchor each item to the supplied tickers, sectors, or macro themes.

Guidelines:
- Omit these sections entirely if no tickers or market data are supplied.
- Never invent price action, tickers, or metrics—only rely on the provided market text and articles.
- Spotlight watchlist tickers wherever relevant in both the table and story entries.
