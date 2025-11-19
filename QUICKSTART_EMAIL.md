# Email Subscription - Quick Start Guide

Get the email subscription feature up and running in 5 minutes!

## Prerequisites

- Backend is set up and running (`uvicorn app.main:app --reload`)
- You have a Brevo account and API key (see `backend/BREVO_SETUP.md` for details)

## Quick Setup

### 1. Configure Environment

Add to `backend/.env`:

```bash
BREVO_API_KEY=xkeysib-your-api-key-here
EMAIL_FROM_ADDRESS=your-email@example.com
EMAIL_FROM_NAME=Daily Paper Insights
FRONTEND_URL=http://localhost:8000
DAILY_DIGEST_HOUR=8
```

### 2. Restart Server

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

You should see:
```
✅ Scheduler started. Daily digest will run at 8:00 UTC
```

### 3. Test Subscription Flow

**Subscribe:**
```bash
curl -X POST http://localhost:8000/api/subscribers \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

**Check verification email** in your inbox!

**Verify manually (for testing):**
```bash
# Get token from database
sqlite3 backend/papers.db "SELECT verify_token FROM subscriber WHERE email='test@example.com';"

# Visit verification URL (use token from above)
open "http://localhost:8000/api/subscribers/verify?token=YOUR_TOKEN"
```

### 4. Test Email Sending

First, make sure you have some papers in the database:
```bash
cd backend
python scripts/daily_ingest.py --limit 5
```

Then send a test digest:
```bash
python scripts/send_daily_digest.py --limit 1 --debug
```

Check your inbox for the digest email!

## What Happens Next?

### Automatic Daily Emails

When the server is running, the system will **automatically send digest emails** every day at the configured hour (default: 8 AM UTC).

The digest includes:
- 🔥 Breakthrough papers (highlighted)
- 📄 Other notable papers
- Problem/Solution/Impact summaries
- Keywords
- Direct links to arXiv

### API Endpoints Available

- **Subscribe:** `POST /api/subscribers` with `{"email": "..."}`
- **Statistics:** `GET /api/subscribers` (returns total and verified counts)
- **Verify:** `GET /api/subscribers/verify?token=...`
- **Unsubscribe:** `GET /api/subscribers/unsubscribe?token=...`

## Monitoring

### Check Subscriber Stats

```bash
curl http://localhost:8000/api/subscribers
# Returns: {"total": 5, "verified": 3}
```

### View Logs

```bash
# Email sending logs
tail -f backend/logs/send_daily_digest.log

# Application logs (scheduler)
# Check console output where uvicorn is running
```

### Database Queries

```bash
sqlite3 backend/papers.db

# View all subscribers
SELECT email, verified, created_at FROM subscriber;

# View verified subscribers only
SELECT email FROM subscriber WHERE verified = 1;
```

## Common Tasks

### Send Test Digest to Specific Date

```bash
python scripts/send_daily_digest.py --date 2024-10-24
```

### Send Only Breakthrough Papers

```bash
python scripts/send_daily_digest.py --breakthrough-only
```

### Test with Limited Subscribers

```bash
python scripts/send_daily_digest.py --limit 5
```

### Disable Automatic Sending

Edit `backend/app/main.py` and comment out:
```python
@app.on_event("startup")
def on_startup() -> None:
    init_db()
    # start_scheduler()  # Comment this line
```

## Troubleshooting

### "Email service not configured"

➡️ Check that `BREVO_API_KEY` is set in `.env`

### Emails not received

1. Check spam/junk folder
2. Verify sender email in Brevo dashboard
3. Check logs: `tail -f backend/logs/send_daily_digest.log`
4. Ensure subscriber is verified: `SELECT verified FROM subscriber WHERE email='test@example.com';`

### "No papers found for date"

➡️ Run daily ingestion first:
```bash
python scripts/daily_ingest.py --date 2024-10-24
```

### Rate limit errors

➡️ Free tier is 300 emails/day. Upgrade Brevo plan if needed.

## Production Deployment

Before going to production:

1. ✅ **Verify sender domain** in Brevo
2. ✅ Add **SPF and DKIM records** to your DNS
3. ✅ Set `FRONTEND_URL` to your production domain
4. ✅ Use a **proper sender address** (not Gmail)
5. ✅ Set up **monitoring** for scheduler failures
6. ✅ Consider **database backups** for subscribers
7. ✅ Add **rate limiting** to subscription endpoint
8. ✅ Test **unsubscribe flow** thoroughly

## Need Help?

- 📖 **Full setup guide:** `backend/BREVO_SETUP.md`
- 📖 **Architecture docs:** `CLAUDE.md`
- 🐛 **Issues:** GitHub Issues (if available)
- 📧 **Brevo support:** https://help.brevo.com/

---

Happy emailing! 📧
