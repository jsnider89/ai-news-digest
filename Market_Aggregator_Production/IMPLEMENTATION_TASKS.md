# Implementation Tasks for AI Market Intel Enhancement

## Progress Update (2025-09-05)

- Implemented in code:
  - Market data client (`apps/worker/src/market-data.ts`) using Finnhub quote API
  - `market_data` table added to schema and storage helpers (`saveMarketData`, `getMarketDataByRun`)
  - Structured Gemini prompt and larger token budget (2500) with market data injection
  - Email template updated with Market Performance section + structured summary rendering
  - Selection logic updated to remove watchlist influence and enforce source diversity
  - Main run flow wired to fetch/save market data and pass it through summarize/email

- Required rollout steps (manual):
  - Add secret: `wrangler secret put FINNHUB_API_KEY`
  - Apply DB migration (adds `market_data` table): `wrangler d1 execute ai_market_intel_db --file=./db/schema.sql --remote`
  - Update `watchlist` setting to real tickers: ["QQQ","SPY","UUP","IWM","GLD","BTC"]

## Current Issues to Fix

### ✅ COMPLETED
1. **Digest 401 Authorization** - Fixed: Digest links now publicly accessible

### 🔧 PENDING IMPLEMENTATION

## Task 1: Add Market Data Integration

### Problem
The watchlist (QQQ, SPY, UUP, IWM, GLD, BTC, etc.) should fetch real stock prices and display market performance, not filter articles.

### Required Changes

#### A. Create Market Data Client
**File**: `apps/worker/src/market-data.ts` (NEW FILE)

```typescript
import type { Env } from "./util";

export interface MarketQuote {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
}

export async function fetchMarketData(env: Env, symbols: string[]): Promise<MarketQuote[]> {
  // Implement using Finnhub API or similar
  // Add FINNHUB_API_KEY to secrets
  // Return formatted market data
}
```

**Required Environment Variable**: 
- Add `FINNHUB_API_KEY` secret via `wrangler secret put FINNHUB_API_KEY`
- Finnhub provides free stock market data API

#### B. Update Storage for Market Data
**File**: `apps/worker/src/storage.ts`

Add functions to cache/store market data:
```typescript
export async function saveMarketData(env: Env, run_id: string, marketData: MarketQuote[]) {
  // Store market data for each run
}

export async function getMarketDataByRun(env: Env, run_id: string): Promise<MarketQuote[]> {
  // Retrieve market data for a specific run
}
```

**Database Schema Update**: Add `market_data` table:
```sql
CREATE TABLE IF NOT EXISTS market_data (
  run_id TEXT,
  symbol TEXT,
  price REAL,
  change_amount REAL,
  change_percent REAL,
  timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (run_id, symbol)
);
```

## Task 2: Restructure AI Summarization

### Problem  
Current AI prompt generates simple bullets. Need structured output with 3 sections:
1. Market Performance (with real prices)
2. Top 5 Market & Economy Stories  
3. 10 General News Stories

### Required Changes

#### A. Update AI Prompt
**File**: `apps/worker/src/summarize.ts`

Replace `DEFAULT_PROMPT_HEADER` with:

```typescript
const STRUCTURED_PROMPT = `You are a professional financial analyst creating a comprehensive market intelligence report.

Generate a structured report with exactly these sections:

## SECTION 1 - MARKET PERFORMANCE
[Market data will be injected here - you analyze the implications]
Provide a 3-4 sentence overarching market summary explaining what the price movements mean.

## SECTION 2 - TOP MARKET & ECONOMY STORIES (5 stories)
Select the 5 most important financial/economic stories. For each:
**Story Title**: [Headline]
[Write 4-6 sentences explaining the story, its market implications, and context]
Sources: [List relevant source URLs]

## SECTION 3 - GENERAL NEWS STORIES (10 stories)  
Select 10 other significant news stories. For each:
**Story Title**: [Headline]
[Write 2-3 sentences summarizing the story and any broader implications]
Sources: [List relevant source URLs]

IMPORTANT:
- Use specific company names, tickers, and numbers when available
- Focus on market impact and investor implications
- Each story must cite actual sources from the provided articles
- Write in professional, analytical tone
`;
```

#### B. Update Summarization Function
**File**: `apps/worker/src/summarize.ts`

Modify `summarizeWithGemini` to:
1. Accept market data parameter
2. Inject market performance data into prompt
3. Increase token limits (current: 900, need: ~2500)
4. Handle structured sections

```typescript
export async function summarizeWithGemini(
  env: Env,
  items: SummaryInputItem[],
  marketData: MarketQuote[],  // NEW PARAMETER
  watchlist: string[],
  promptOverride?: string
): Promise<SummarizeResult> {
  // Inject market data into prompt
  // Increase maxOutputTokens to 2500
  // Format market performance section
}
```

## Task 3: Enhance Email Template

### Problem
Current email shows raw RSS links. Need structured HTML with market performance table and AI-generated summaries.

### Required Changes

#### A. Create New Email Renderer
**File**: `apps/worker/src/email.ts`

Replace `renderHtml` function with structured template:

```typescript
function renderHtml(
  subject: string, 
  summaryHtml: string, 
  marketData: MarketQuote[],
  items: EmailItem[]
): string {
  const marketTable = generateMarketTable(marketData);
  
  return `<!doctype html>
<html><head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>${escapeHtml(subject)}</title>
  <style>
    /* Add professional CSS styling similar to reference repo */
    body { font-family: system-ui, -apple-system, sans-serif; }
    .market-table { border-collapse: collapse; width: 100%; }
    .market-table th, .market-table td { border: 1px solid #ddd; padding: 8px; }
    .positive { color: #22c55e; }
    .negative { color: #ef4444; }
  </style>
</head>
<body>
  <div style="max-width: 720px; margin: 0 auto; padding: 16px;">
    <h1>📊 Daily Market & News Intelligence</h1>
    <p>Generated: ${new Date().toLocaleString()} UTC</p>
    
    <h2>SECTION 1 - MARKET PERFORMANCE</h2>
    ${marketTable}
    
    <div>${summaryHtml}</div>
    
    <hr/>
    <p style="color:#666;font-size:12px;">
      🤖 AI Market Intelligence System<br/>
      Tracking: ${marketData.map(m => m.symbol).join(' | ')}
    </p>
  </div>
</body></html>`;
}

function generateMarketTable(marketData: MarketQuote[]): string {
  // Generate HTML table with symbols, prices, changes
  // Add green/red styling for positive/negative changes
}
```

## Task 4: Update Main Processing Logic

### Required Changes

#### A. Update Main Run Function
**File**: `apps/worker/src/index.ts`

In the `runOnce` function around line 200, add market data fetching:

```typescript
async function runOnce(env: Env): Promise<RunResult> {
  // ... existing code ...
  
  // NEW: Fetch market data
  const watchlistStr = settings["watchlist"] || "[]";
  const watchlist = JSON.parse(watchlistStr);
  const marketData = await fetchMarketData(env, watchlist);
  await saveMarketData(env, run_id, marketData);
  
  // Update AI summarization call
  const aiRes = await summarizeWithGemini(env, ranked.slice(0, maxAiItems), marketData, watchlist, promptOverride);
  
  // Update email call
  const emailRes = await sendDigestEmail(env, recipients, subject, summaryHtml, marketData, ranked.map(r => r.item), fromAddress);
  
  // ... rest of function ...
}
```

#### B. Fix Article Selection Logic
**File**: `apps/worker/src/select.ts`

The watchlist should NOT filter articles. Update `rankItems` to:
1. Remove watchlist filtering for article selection
2. Use watchlist only for market data fetching
3. Select articles based on recency and source diversity only

## Task 5: Database Updates

### Required SQL Changes

Execute via `wrangler d1 execute ai_market_intel_db --file=schema_update.sql --remote`:

```sql
-- Add market data table
CREATE TABLE IF NOT EXISTS market_data (
  run_id TEXT,
  symbol TEXT,
  price REAL,
  change_amount REAL,
  change_percent REAL,
  timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (run_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_market_data_run ON market_data(run_id);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol);
```

## Configuration Updates

### Environment Variables Needed
```bash
# Add these secrets
wrangler secret put FINNHUB_API_KEY
# Get free API key from https://finnhub.io/

# Update watchlist in settings to proper ticker symbols
# Current: ["market","economy","Fed","financial","stock","dollar","inflation","rate","bank","economy","business","trade"]  
# Should be: ["QQQ","SPY","UUP","IWM","GLD","BTC"]
```

## Testing Steps

After implementation:

1. **Test market data**: Verify API calls return proper quote data
2. **Test AI prompt**: Ensure structured output with 3 sections
3. **Test email format**: Check HTML rendering and styling  
4. **Test end-to-end**: Run manual trigger and verify complete flow

## Expected Result

After these changes, the system will generate emails matching your reference format:
- Market performance table with real prices/changes
- 5 detailed market/economy story summaries
- 10 general news story summaries  
- Professional HTML styling
- Proper source attribution

## Implementation Priority

1. **Market Data Client** (foundational)
2. **AI Prompt Restructuring** (core logic)
3. **Email Template** (presentation)
4. **Integration** (connecting pieces)

## Files to Modify

- `apps/worker/src/market-data.ts` (NEW)
- `apps/worker/src/storage.ts` (ADD functions)  
- `apps/worker/src/summarize.ts` (MAJOR UPDATE)
- `apps/worker/src/email.ts` (MAJOR UPDATE)
- `apps/worker/src/index.ts` (UPDATE main flow)
- `apps/worker/src/select.ts` (FIX filtering logic)
- `db/schema.sql` (ADD table)

Total estimated implementation time: 4-6 hours for experienced developer.
