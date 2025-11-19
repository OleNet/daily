import secrets
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from app.api.deps import get_db
from app.api.schemas import SubscriberCreateSchema, SubscriberResponseSchema
from app.models import Subscriber
from app.services.email_service import email_service

router = APIRouter(prefix="/subscribers", tags=["subscribers"])


@router.post("/", response_model=SubscriberResponseSchema, status_code=status.HTTP_201_CREATED)
def create_subscriber(
    payload: SubscriberCreateSchema,
    db: Session = Depends(get_db),
) -> SubscriberResponseSchema:
    """Create a new subscriber and send verification email"""
    existing = db.exec(select(Subscriber).where(Subscriber.email == payload.email)).first()
    if existing:
        if existing.verified:
            raise HTTPException(status_code=400, detail="Email already subscribed and verified")
        else:
            # Resend verification email for unverified subscriber
            email_service.send_verification_email(existing.email, existing.verify_token)
            return SubscriberResponseSchema(
                email=existing.email,
                verified=existing.verified,
                created_at=existing.created_at,
            )

    token = secrets.token_urlsafe(32)
    subscriber = Subscriber(email=payload.email, verify_token=token)
    db.add(subscriber)
    db.commit()
    db.refresh(subscriber)

    # Send verification email
    email_sent = email_service.send_verification_email(subscriber.email, token)
    if not email_sent:
        # Note: We still create the subscriber even if email fails
        # Admin can manually verify if needed
        pass

    return SubscriberResponseSchema(
        email=subscriber.email,
        verified=subscriber.verified,
        created_at=subscriber.created_at,
    )


@router.get("/verify", response_class=HTMLResponse)
def verify_email(
    token: str = Query(..., description="Verification token from email"),
    db: Session = Depends(get_db),
) -> str:
    """Verify subscriber email address via token"""
    subscriber = db.exec(
        select(Subscriber).where(Subscriber.verify_token == token)
    ).first()

    if not subscriber:
        return """
        <html>
            <head><title>Verification Failed</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #dc2626;">❌ Verification Failed</h1>
                <p>Invalid or expired verification token.</p>
            </body>
        </html>
        """

    if subscriber.verified:
        return """
        <html>
            <head><title>Already Verified</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #059669;">✅ Already Verified</h1>
                <p>This email address is already verified.</p>
            </body>
        </html>
        """

    # Mark as verified
    subscriber.verified = True
    db.commit()

    return """
    <html>
        <head><title>Email Verified</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #059669;">✅ Email Verified!</h1>
            <p>Your subscription to Daily Paper Insights is now active.</p>
            <p style="color: #666;">You'll receive your first digest soon.</p>
        </body>
    </html>
    """


@router.get("/unsubscribe", response_class=HTMLResponse)
def unsubscribe(
    token: str = Query(..., description="Unsubscribe token"),
    db: Session = Depends(get_db),
) -> str:
    """Unsubscribe using token from email"""
    # Token is the verify_token (we reuse it for unsubscribe)
    subscriber = db.exec(
        select(Subscriber).where(Subscriber.verify_token == token)
    ).first()

    if not subscriber:
        return """
        <html>
            <head><title>Unsubscribe Failed</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #dc2626;">❌ Unsubscribe Failed</h1>
                <p>Invalid token. If you need help, please contact support.</p>
            </body>
        </html>
        """

    email = subscriber.email
    db.delete(subscriber)
    db.commit()

    return f"""
    <html>
        <head><title>Unsubscribed</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #059669;">👋 Unsubscribed</h1>
            <p>You have been successfully unsubscribed from Daily Paper Insights.</p>
            <p style="color: #666;">Email: {email}</p>
            <p style="color: #666; margin-top: 30px;">
                Changed your mind? You can always subscribe again later.
            </p>
        </body>
    </html>
    """


@router.get("/", response_model=Dict[str, int])
def subscriber_summary(db: Session = Depends(get_db)) -> Dict[str, int]:
    """Get subscriber statistics"""
    total = db.exec(select(Subscriber)).all()
    verified = len([s for s in total if s.verified])
    return {"total": len(total), "verified": verified}