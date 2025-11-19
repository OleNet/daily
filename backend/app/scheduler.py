"""
Background scheduler for automated tasks using APScheduler.

This module sets up scheduled jobs like daily digest email sending.
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import select

from app.core.config import settings
from app.db.session import session_scope
from app.models.entities import Paper, Subscriber
from app.services.email_service import email_service

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def send_daily_digest_job():
    """
    Scheduled job to send daily digest to all verified subscribers.

    This job runs daily at the configured hour (default: 8 AM).
    It sends papers from yesterday's HF listing.
    """
    logger.info("🕐 Starting scheduled daily digest job")

    # Check if email service is configured
    if not settings.brevo_api_key:
        logger.warning("BREVO_API_KEY not configured. Skipping daily digest.")
        return

    try:
        # Get yesterday's date
        yesterday = datetime.utcnow() - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")

        logger.info(f"Fetching papers for date: {target_date}")

        # Get papers from database
        with session_scope() as session:
            papers = session.exec(
                select(Paper)
                .where(Paper.hf_listing_date == target_date)
                .order_by(Paper.breakthrough_score.desc(), Paper.published_at.desc())
            ).all()

            if not papers:
                logger.info(f"No papers found for {target_date}. Skipping digest.")
                return

            logger.info(f"Found {len(papers)} papers to send")
            breakthrough_count = sum(1 for p in papers if p.breakthrough_label)
            logger.info(f"  - Breakthrough: {breakthrough_count}")
            logger.info(f"  - Regular: {len(papers) - breakthrough_count}")

            # Get all verified subscribers
            subscribers = session.exec(
                select(Subscriber).where(Subscriber.verified == True)
            ).all()

            if not subscribers:
                logger.info("No verified subscribers. Skipping digest.")
                return

            logger.info(f"Sending digest to {len(subscribers)} subscriber(s)")

            # Send to each subscriber
            sent = 0
            failed = 0

            for subscriber in subscribers:
                try:
                    success = email_service.send_daily_digest(
                        email=subscriber.email,
                        papers=papers,
                        unsubscribe_token=subscriber.verify_token
                    )

                    if success:
                        sent += 1
                        logger.info(f"✅ Sent to {subscriber.email}")
                    else:
                        failed += 1
                        logger.error(f"❌ Failed to send to {subscriber.email}")

                except Exception as e:
                    failed += 1
                    logger.error(f"❌ Error sending to {subscriber.email}: {e}")

            # Log summary
            logger.info("=" * 60)
            logger.info(f"Daily digest job completed")
            logger.info(f"✅ Sent: {sent}")
            logger.info(f"❌ Failed: {failed}")
            logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error in daily digest job: {e}", exc_info=True)


def start_scheduler():
    """
    Start the background scheduler with all configured jobs.

    This should be called once during application startup.
    """
    if scheduler.running:
        logger.warning("Scheduler is already running")
        return

    # Add daily digest job
    # Runs every day at the configured hour (default: 8 AM UTC)
    scheduler.add_job(
        send_daily_digest_job,
        trigger=CronTrigger(hour=settings.daily_digest_hour, minute=0),
        id="daily_digest",
        name="Send Daily Paper Digest",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"✅ Scheduler started. Daily digest will run at {settings.daily_digest_hour}:00 UTC")


def stop_scheduler():
    """
    Stop the background scheduler.

    This should be called during application shutdown.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")