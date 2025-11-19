# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Daily Paper Insights is an automated pipeline that ingests papers from Hugging Face's daily feed, fetches full arXiv content, and uses DeepSeek LLM to extract structured insights (problem/solution/effect, breakthrough scoring, findings with experimental evidence, and keywords). The system serves a dashboard and provides a subscription API for daily email notifications.

## Development Setup

This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable dependency management.

```bash
# Install uv (if not already installed)
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows:
# powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install dependencies (creates .venv automatically)
uv sync

# Run the API server (serves dashboard at http://localhost:8000/dashboard)
uv run uvicorn app.main:app --reload --app-dir backend
```

## Environment Configuration

Create a `.env` file in the `backend/` directory (see `.env.example` for template):

```
DATABASE_URL=sqlite:///./papers.db
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
BREAKTHROUGH_THRESHOLD=0.7
INSTITUTION_WHITELIST=ai2,allen institute for ai,anthropic,openai,google deepmind,deepseek,meta ai

# Email Configuration (Brevo)
BREVO_API_KEY=your-brevo-api-key
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
EMAIL_FROM_NAME=Daily Paper Insights
FRONTEND_URL=http://localhost:8000
DAILY_DIGEST_HOUR=8
```

**Configuration Notes:**
- If `DEEPSEEK_API_KEY` is omitted, the LLM client falls back to heuristics (less detailed but functional)
- If `BREVO_API_KEY` is omitted, email features are disabled (subscribers can still register but won't receive emails)
- Get Brevo API key from: https://app.brevo.com/settings/keys/api (free tier: 300 emails/day)
- `DAILY_DIGEST_HOUR` sets when daily emails are sent (UTC time, default: 8 AM)

## Running Tests

```bash
uv run pytest backend
uv run pytest backend -v  # verbose output
uv run pytest backend/tests/test_models/  # run specific test directory
uv run pytest backend/tests/test_models/test_entities.py  # run specific test file
```

## Daily Ingestion Pipeline

```bash
uv run python backend/scripts/daily_ingest.py  # ingest yesterday's papers
uv run python backend/scripts/daily_ingest.py --limit 5  # test with 5 papers
uv run python backend/scripts/daily_ingest.py --date 2024-10-24  # ingest specific date
uv run python backend/scripts/daily_ingest.py --debug  # enable verbose logging
```

The script fetches papers from Hugging Face's daily page for the specified date, retrieves full content from arXiv, analyzes with LLM, and stores in SQLite. Logs are written to `backend/logs/daily_ingest.log`.

## Email Subscription System

### Sending Daily Digest Emails

```bash
uv run python backend/scripts/send_daily_digest.py                    # Send yesterday's papers
uv run python backend/scripts/send_daily_digest.py --date 2024-10-24  # Send specific date
uv run python backend/scripts/send_daily_digest.py --limit 5          # Test with 5 subscribers
uv run python backend/scripts/send_daily_digest.py --breakthrough-only # Only breakthrough papers
uv run python backend/scripts/send_daily_digest.py --debug            # Enable verbose logging
```

The script sends digest emails to all verified subscribers. Logs are written to `backend/logs/send_daily_digest.log`.

### Automated Daily Sending

When the FastAPI server is running, emails are automatically sent daily at the configured hour (default: 8 AM UTC). This is handled by APScheduler running in the background.

To disable automatic sending, comment out `start_scheduler()` in `app/main.py`.

### Testing Email Subscription Flow

1. **Subscribe via API:**
   ```bash
   curl -X POST http://localhost:8000/api/subscribers \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com"}'
   ```

2. **Check verification email** (if Brevo is configured)

3. **Verify email manually** (for testing without Brevo):
   ```bash
   # Get token from database
   sqlite3 backend/papers.db "SELECT verify_token FROM subscriber WHERE email='test@example.com';"

   # Visit verification URL
   curl "http://localhost:8000/api/subscribers/verify?token=TOKEN_HERE"
   ```

4. **Send test digest:**
   ```bash
   cd backend
   python scripts/send_daily_digest.py --limit 1
   ```

5. **Unsubscribe:**
   ```
   Visit the unsubscribe link in any digest email, or manually:
   http://localhost:8000/api/subscribers/unsubscribe?token=TOKEN_HERE
   ```

## Architecture

### Backend Structure (`backend/`)

- **`app/main.py`** - FastAPI application entry point. Includes routers, initializes database on startup, mounts the frontend static files at `/dashboard`, and provides CORS middleware.

- **`app/models/entities.py`** - SQLModel definitions for the entire database schema:
  - `Paper` - Main paper entity with arXiv metadata, LLM-generated summaries (problem/solution/effect), keywords, breakthrough scoring, and source tracking (HTML or PDF)
  - `Finding` - Evidence-backed findings extracted from papers (claim, experiment design, metrics)
  - `KeywordStat` - Keyword frequency tracking across all papers
  - `Subscriber` - Email subscribers with verification tokens

- **`app/services/`** - Core business logic:
  - `hf_client.py` - Scrapes paper identifiers from Hugging Face daily pages using selectolax HTML parser
  - `arxiv_fetcher.py` - Fetches arXiv content (HTML preferred, PDF fallback), extracts metadata, sections, and author institutions
  - `llm_client.py` - Prompts DeepSeek LLM for structured analysis (problem/solution/effect, breakthrough scoring, findings with experimental evidence, keywords). Falls back to heuristics when no API key is provided
  - `email_service.py` - Handles email sending via Brevo API (verification emails, daily digests with HTML templates)

- **`app/api/routes/`** - REST API endpoints:
  - `papers.py` - List papers, get paper details, filter breakthroughs
  - `keywords.py` - Keyword frequency stats for dashboard charts
  - `subscribers.py` - Email subscription management (create subscription with verification email, verify email, unsubscribe, statistics)

- **`app/db/session.py`** - Database initialization and session management with context manager (`session_scope()`)

- **`app/core/config.py`** - Settings loaded from environment variables with defaults (including Brevo API configuration)

- **`app/scheduler.py`** - Background scheduler using APScheduler for automated daily tasks (sends digest emails at configured hour)

- **`scripts/daily_ingest.py`** - Orchestrates the full pipeline: fetch identifiers → fetch arXiv content → analyze with LLM → store in database → update keyword stats. Supports date targeting, limit flag for testing, and debug logging

- **`scripts/send_daily_digest.py`** - Sends daily digest emails to verified subscribers. Can be run manually or automatically via scheduler. Supports date targeting, subscriber limits, and breakthrough-only mode

### Frontend Structure (`frontend/`)

Static HTML/CSS/JS dashboard served by FastAPI:
- `index.html` - Dashboard layout with paper cards and keyword chart
- `app.js` - Fetches data from API endpoints, renders cards, handles breakthrough filtering
- `styles.css` - Responsive styling

### Data Flow

1. **Ingestion**: `daily_ingest.py` → `hf_client.fetch_daily_identifiers()` → `arxiv_fetcher.fetch()` → `llm_client.analyze_paper_with_llm()` → Database
2. **API Serving**: FastAPI reads from SQLite and serves JSON to dashboard
3. **Dashboard**: Frontend calls `/api/papers` and `/api/keywords/stats`, renders UI

### Key Design Patterns

- **Session Management**: Use `session_scope()` context manager for all database operations to ensure proper transaction handling
- **LLM Fallback**: If DeepSeek API key is missing, `llm_client.py` uses heuristics (title/abstract keyword matching) to generate basic insights
- **Date Tracking**: Papers store both `published_at` (arXiv publication date) and `hf_listing_date` (when they appeared on HF daily page) for accurate temporal analysis
- **Institution Filtering**: Breakthrough scoring is influenced by whether the paper comes from tracked institutions (configured in `INSTITUTION_WHITELIST`)

## Common Development Commands

```bash
# Start development server with auto-reload
uv run uvicorn app.main:app --reload --app-dir backend

# Run ingestion with different options
uv run python backend/scripts/daily_ingest.py --limit 10 --debug
uv run python backend/scripts/daily_ingest.py --date 2024-10-20

# Check database
sqlite3 backend/papers.db
# sqlite> .tables
# sqlite> SELECT arxiv_id, title, breakthrough_score FROM paper LIMIT 5;

# View logs
tail -f backend/logs/daily_ingest.log
```

## API Endpoints

**Papers:**
- `GET /api/papers` - List papers with optional `?breakthrough_only=true` filter
- `GET /api/papers/{id}` - Full paper details including findings

**Keywords:**
- `GET /api/keywords/stats` - Keyword frequency table

**Subscribers:**
- `POST /api/subscribers` - Subscribe to daily emails (body: `{"email": "user@example.com"}`, sends verification email)
- `GET /api/subscribers` - Get subscriber statistics (total and verified counts)
- `GET /api/subscribers/verify?token=...` - Verify email address (returns HTML page)
- `GET /api/subscribers/unsubscribe?token=...` - Unsubscribe from emails (returns HTML page)

**System:**
- `GET /health` - Health check

## Important Notes

- The database is SQLite by default (`papers.db` in backend directory)
- Frontend is served at `/dashboard` by the FastAPI app itself (no separate web server needed)
- LLM analysis is synchronous and can be slow; consider adding async task queue (Celery/RQ) for production
- **Email System:**
  - Fully implemented with Brevo (Sendinblue) API integration
  - Supports verification emails, daily digests, and unsubscribe
  - Emails are sent automatically daily at configured hour when server is running
  - Free tier: 300 emails/day (sufficient for small to medium subscriber base)
  - Falls back gracefully if BREVO_API_KEY is not configured (subscribers can still register)
