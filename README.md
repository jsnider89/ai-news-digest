# Local Aggregator Stack

A combined Python + React implementation of the AI-powered market/newsletter aggregator. It ingests RSS feeds, runs multi-provider AI analysis, delivers formatted emails via Resend, and exposes a web dashboard for managing newsletters, schedules, and run history—all packaged for containerised deployment.

## Quick Start

1. **Clone & install**
   ```bash
   git clone <repo-url> local-aggregator
   cd local-aggregator
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   cd frontend && npm install && npm run build && cd ..
   ```

2. **Run locally**
   ```bash
   .venv/bin/python -m app.tasks.prestart  # creates DB/migrations
   .venv/bin/uvicorn app.web.main:app --reload
   ```
   Visit `http://localhost:8000` to use the dashboard.

3. **One-shot run**
   ```bash
   .venv/bin/python -m app.tasks.service --run <newsletter_id>
   ```

4. **Docker**
   ```bash
   docker build -t market-aggregator .
   docker run --env-file .env -p 8000:8000 market-aggregator
   ```

See `INTEGRATION_PLAN.md` for architecture details.
