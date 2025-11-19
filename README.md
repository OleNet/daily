# Daily Paper Insights

An automated pipeline that ingests the Hugging Face daily paper feed, fetches full arXiv content, distills structured insights with a DeepSeek LLM call, and serves a dashboard with breakthrough highlights, experiment evidence, and keyword momentum. A lightweight subscription API lets readers sign up for daily push emails (email delivery hook ready for integration).

## Repository Layout

- `backend/` – FastAPI app, database models, and ingest scripts.
  - `app/services/hf_client.py` – scrapes paper identifiers from the Hugging Face daily page.
  - `app/services/arxiv_fetcher.py` – pulls arXiv HTML (or PDF fallback) and extracts sections, metadata, and institutions.
  - `app/services/llm_client.py` – prompts an LLM for problem/solution/effect, breakthrough scoring, findings, and keywords (heuristic fallback if no API key).
  - `scripts/daily_ingest.py` – orchestrates the daily pipeline end to end.
- `frontend/` – Static dashboard (HTML/CSS/JS) that calls the API, renders daily cards, and charts keyword stats.

## Getting Started

This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable dependency management.

### Installation

First, install uv if you haven't already:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Setup and Run

```bash
# Install dependencies (creates .venv automatically)
uv sync

# Run API (serves dashboard at http://localhost:8000/dashboard)
uv run uvicorn app.main:app --reload --app-dir backend
```

Create a `.env` file at the repository root when you want to customise behaviour:

```
DATABASE_URL=sqlite:///./papers.db
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
BREAKTHROUGH_THRESHOLD=0.7
INSTITUTION_WHITELIST=ai2,allen institute for ai,anthropic,openai,google deepmind,deepseek,meta ai
```

If `DEEPSEEK_API_KEY` is omitted the summariser falls back to heuristics (less detailed, but keeps the pipeline running).

## Daily Ingestion

```bash
# optional: limit number of papers during testing
uv run python backend/scripts/daily_ingest.py --limit 5
```

Schedule this script with cron, GitHub Actions, or any workflow orchestrator. The script:
1. Pulls new arXiv identifiers from the previous day's Hugging Face daily page (`https://huggingface.co/papers/date/YYYY-MM-DD`).
2. Fetches full HTML (PDF fallback) and metadata.
3. Requests LLM analysis for problem/solution/effect, breakthrough scoring, keywords, and evidence-backed findings.
4. Stores everything in SQLite and updates keyword momentum stats.

## API Overview

- `GET /api/papers` – list daily summaries (`?breakthrough_only=true` filters the breakthroughs).
- `GET /api/papers/{id}` – full record including findings and metrics.
- `GET /api/keywords/stats` – keyword frequency table for the dashboard chart.
- `POST /api/subscribers` – accepts email address, stores verify token (extend with email delivery of your choice).
- `GET /health` – lightweight readiness probe.

The FastAPI app automatically initialises the database and serves the static dashboard, so visiting `http://localhost:8000/dashboard` after running `uvicorn` is enough to explore the data.

## Next Steps

- Plug the subscriber endpoint into your email service (Resend, Postmark, SendGrid) and send the LLM summary to the daily mailing list.
- Integrate a task queue (Celery, RQ) if you want ingestion and email dispatch to run asynchronously.
- Enhance breakthrough scoring by feeding historical context (the database keeps everything you need for trend comparisons).
