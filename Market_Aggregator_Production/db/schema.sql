-- D1 schema (minimal + digest archive)

-- feeds the system should pull
CREATE TABLE IF NOT EXISTS feeds (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  category TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  added_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- canonical article inventory (dedup across runs)
CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY,
  content_hash TEXT UNIQUE NOT NULL,
  source TEXT NOT NULL,               -- domain/host
  title TEXT NOT NULL,
  canonical_url TEXT NOT NULL,
  published_at TEXT,                   -- RFC3339
  first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- fast “have we seen this?” set
CREATE TABLE IF NOT EXISTS seen_hashes (
  content_hash TEXT PRIMARY KEY,
  first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- per run bookkeeping
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  started_at TEXT,
  finished_at TEXT,
  status TEXT,                         -- success|partial|failed
  feeds_total INTEGER,
  feeds_ok INTEGER,
  articles_seen INTEGER,
  articles_used INTEGER,
  ai_tokens_in INTEGER,
  ai_tokens_out INTEGER,
  email_sent INTEGER                   -- 0/1
);

-- which articles were used in a run (and in what order)
CREATE TABLE IF NOT EXISTS run_articles (
  run_id TEXT,
  article_id INTEGER,
  rank INTEGER,
  score REAL,
  PRIMARY KEY (run_id, article_id)
);

-- editable system settings (simple key/value)
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- archived rendered HTML for each run
CREATE TABLE IF NOT EXISTS digests (
  run_id TEXT PRIMARY KEY,
  html TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- per run structured logs (optional, for troubleshooting)
CREATE TABLE IF NOT EXISTS run_logs (
  run_id TEXT,
  ts TEXT DEFAULT CURRENT_TIMESTAMP,
  level TEXT,
  message TEXT,
  context_json TEXT,
  PRIMARY KEY (run_id, ts, message)
);

-- per run market data snapshot
CREATE TABLE IF NOT EXISTS market_data (
  run_id TEXT,
  symbol TEXT,
  price REAL,
  change_amount REAL,
  change_percent REAL,
  timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (run_id, symbol)
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at);
CREATE INDEX IF NOT EXISTS idx_run_logs_run ON run_logs(run_id);
CREATE INDEX IF NOT EXISTS idx_market_data_run ON market_data(run_id);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol);
