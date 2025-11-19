#!/usr/bin/env python3
"""
Send daily digest emails to all verified subscribers.

Usage:
    python scripts/send_daily_digest.py                    # Send yesterday's papers
    python scripts/send_daily_digest.py --date 2024-10-24  # Send specific date
    python scripts/send_daily_digest.py --limit 5          # Test with 5 subscribers
    python scripts/send_daily_digest.py --debug            # Enable verbose logging
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from sqlmodel import Session, select

from app.core.config import settings
from app.db.session import engine, session_scope
from app.models.entities import Paper, Subscriber
from app.services.email_service import email_service

# Setup logging
log_dir = backend_dir / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "send_daily_digest.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Send daily digest emails to subscribers")
    parser.add_argument(
        "--date",
        type=str,
        help="Date to send digest for (YYYY-MM-DD). Defaults to yesterday.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of subscribers (for testing)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--breakthrough-only",
        action="store_true",
        help="Only send breakthrough papers",
    )
    return parser.parse_args()


def get_papers_for_date(session: Session, target_date: str, breakthrough_only: bool = False):
    """Get papers for a specific date"""
    query = select(Paper).where(Paper.hf_listing_date == target_date)

    if breakthrough_only:
        query = query.where(Paper.breakthrough_label == True)

    # Order by breakthrough score descending, then by published date
    query = query.order_by(Paper.breakthrough_score.desc(), Paper.published_at.desc())

    papers = session.exec(query).all()
    return papers


def send_digest_to_subscribers(
    papers: list[Paper],
    limit: int = None,
    breakthrough_only: bool = False
) -> dict:
    """
    Send digest to all verified subscribers

    Returns:
        dict: Statistics about sending (sent, failed, skipped)
    """
    if not papers:
        logger.warning("No papers to send. Aborting digest.")
        return {"sent": 0, "failed": 0, "skipped": 0}

    stats = {"sent": 0, "failed": 0, "skipped": 0}

    with session_scope() as session:
        # Get all verified subscribers
        query = select(Subscriber).where(Subscriber.verified == True)

        if limit:
            query = query.limit(limit)

        subscribers = session.exec(query).all()

        logger.info(f"Found {len(subscribers)} verified subscriber(s)")
        logger.info(f"Sending digest with {len(papers)} paper(s)")

        for subscriber in subscribers:
            try:
                logger.info(f"Sending digest to {subscriber.email}")

                # Send email using the verify_token as unsubscribe token
                success = email_service.send_daily_digest(
                    email=subscriber.email,
                    papers=papers,
                    unsubscribe_token=subscriber.verify_token
                )

                if success:
                    stats["sent"] += 1
                    logger.info(f"✅ Successfully sent to {subscriber.email}")
                else:
                    stats["failed"] += 1
                    logger.error(f"❌ Failed to send to {subscriber.email}")

            except Exception as e:
                stats["failed"] += 1
                logger.error(f"❌ Error sending to {subscriber.email}: {e}")

    return stats


def main():
    args = parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine target date
    if args.date:
        target_date = args.date
        logger.info(f"Using specified date: {target_date}")
    else:
        # Default to yesterday
        yesterday = datetime.utcnow() - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")
        logger.info(f"Using yesterday's date: {target_date}")

    # Validate Brevo API key
    if not settings.brevo_api_key:
        logger.error("BREVO_API_KEY not configured. Cannot send emails.")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Starting Daily Digest Send")
    logger.info(f"Target Date: {target_date}")
    logger.info(f"Breakthrough Only: {args.breakthrough_only}")
    if args.limit:
        logger.info(f"Limit: {args.limit} subscribers (test mode)")
    logger.info("=" * 60)

    # Get papers for the date
    with session_scope() as session:
        papers = get_papers_for_date(session, target_date, args.breakthrough_only)

    if not papers:
        logger.warning(f"No papers found for date {target_date}. Nothing to send.")
        return

    logger.info(f"Found {len(papers)} paper(s) for {target_date}")

    # Count breakthroughs
    breakthrough_count = sum(1 for p in papers if p.breakthrough_label)
    logger.info(f"  - Breakthrough papers: {breakthrough_count}")
    logger.info(f"  - Regular papers: {len(papers) - breakthrough_count}")

    # Send to subscribers
    stats = send_digest_to_subscribers(papers, limit=args.limit, breakthrough_only=args.breakthrough_only)

    # Print summary
    logger.info("=" * 60)
    logger.info("Daily Digest Send Complete")
    logger.info(f"✅ Sent: {stats['sent']}")
    logger.info(f"❌ Failed: {stats['failed']}")
    logger.info(f"⏭️  Skipped: {stats['skipped']}")
    logger.info("=" * 60)

    if stats["failed"] > 0:
        logger.warning("Some emails failed to send. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()