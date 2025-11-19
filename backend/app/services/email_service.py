import logging
from typing import List, Optional

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from app.core.config import settings
from app.models.entities import Paper

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via Brevo (Sendinblue)"""

    def __init__(self):
        if not settings.brevo_api_key:
            logger.warning("BREVO_API_KEY not configured. Email sending will be disabled.")
            self.api_instance = None
        else:
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = settings.brevo_api_key
            api_client = sib_api_v3_sdk.ApiClient(configuration)
            self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        to_name: Optional[str] = None
    ) -> bool:
        """
        Internal method to send email via Brevo API

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.api_instance:
            logger.error("Email service not configured. Skipping email send.")
            return False

        try:
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": to_email, "name": to_name or to_email}],
                html_content=html_content,
                sender={
                    "email": settings.email_from_address,
                    "name": settings.email_from_name
                },
                subject=subject
            )

            response = self.api_instance.send_transac_email(send_smtp_email)
            logger.info(f"Email sent successfully to {to_email}. Message ID: {response.message_id}")
            return True

        except ApiException as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to_email}: {e}")
            return False

    def send_verification_email(self, email: str, verify_token: str) -> bool:
        """
        Send email verification link to new subscriber

        Args:
            email: Subscriber's email address
            verify_token: Unique verification token

        Returns:
            bool: True if email sent successfully
        """
        verify_url = f"{settings.frontend_url}/api/subscribers/verify?token={verify_token}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                          color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea;
                          color: white !important; text-decoration: none; border-radius: 5px;
                          font-weight: bold; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📧 Verify Your Email</h1>
                </div>
                <div class="content">
                    <h2>Welcome to Daily Paper Insights!</h2>
                    <p>Thank you for subscribing to our daily AI research paper digest.
                       Click the button below to verify your email address:</p>

                    <div style="text-align: center;">
                        <a href="{verify_url}" class="button">Verify Email Address</a>
                    </div>

                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #667eea;">{verify_url}</p>

                    <p style="margin-top: 30px; color: #666;">
                        If you didn't subscribe to Daily Paper Insights, you can safely ignore this email.
                    </p>
                </div>
                <div class="footer">
                    <p>Daily Paper Insights - Stay updated with breakthrough AI research</p>
                </div>
            </div>
        </body>
        </html>
        """

        return self._send_email(
            to_email=email,
            subject="Verify your email - Daily Paper Insights",
            html_content=html_content
        )

    def send_daily_digest(self, email: str, papers: List[Paper], unsubscribe_token: str) -> bool:
        """
        Send daily digest of papers to subscriber

        Args:
            email: Subscriber's email address
            papers: List of Paper objects to include in digest
            unsubscribe_token: Token for unsubscribe link

        Returns:
            bool: True if email sent successfully
        """
        if not papers:
            logger.info(f"No papers to send to {email}, skipping digest")
            return False

        unsubscribe_url = f"{settings.frontend_url}/api/subscribers/unsubscribe?token={unsubscribe_token}"

        # Separate breakthrough and regular papers
        breakthrough_papers = [p for p in papers if p.breakthrough_label]
        regular_papers = [p for p in papers if not p.breakthrough_label]

        # Build paper cards HTML
        papers_html = ""

        if breakthrough_papers:
            papers_html += "<h2 style='color: #d97706; margin-top: 30px;'>🔥 Breakthrough Papers</h2>"
            for paper in breakthrough_papers:
                papers_html += self._render_paper_card(paper, is_breakthrough=True)

        if regular_papers:
            papers_html += "<h2 style='color: #667eea; margin-top: 30px;'>📄 Other Notable Papers</h2>"
            for paper in regular_papers:
                papers_html += self._render_paper_card(paper, is_breakthrough=False)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }}
                .container {{ max-width: 700px; margin: 0 auto; background: white; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                          color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 20px 30px; }}
                .paper-card {{ background: #f9f9f9; border-left: 4px solid #667eea;
                              padding: 20px; margin: 15px 0; border-radius: 5px; }}
                .paper-card.breakthrough {{ border-left-color: #d97706; background: #fffbeb; }}
                .paper-title {{ font-size: 18px; font-weight: bold; color: #1f2937; margin-bottom: 10px; }}
                .paper-meta {{ font-size: 13px; color: #666; margin-bottom: 10px; }}
                .paper-section {{ margin: 10px 0; }}
                .paper-section strong {{ color: #667eea; }}
                .keywords {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
                .keyword {{ background: #e0e7ff; color: #4338ca; padding: 4px 12px;
                           border-radius: 12px; font-size: 12px; }}
                .arxiv-link {{ display: inline-block; margin-top: 10px; color: #667eea;
                              text-decoration: none; font-weight: bold; }}
                .footer {{ background: #f9f9f9; padding: 20px; text-align: center;
                          color: #666; font-size: 12px; }}
                .unsubscribe {{ color: #999; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📚 Daily Paper Insights</h1>
                    <p style="margin: 0; opacity: 0.9;">Your curated AI research digest</p>
                </div>
                <div class="content">
                    <p>Hi there! Here are today's most interesting AI research papers:</p>
                    {papers_html}
                </div>
                <div class="footer">
                    <p>Daily Paper Insights - Curated AI research delivered daily</p>
                    <p><a href="{unsubscribe_url}" class="unsubscribe">Unsubscribe</a></p>
                </div>
            </div>
        </body>
        </html>
        """

        return self._send_email(
            to_email=email,
            subject=f"📚 Daily AI Papers - {len(papers)} papers ({len(breakthrough_papers)} breakthroughs)",
            html_content=html_content
        )

    def _render_paper_card(self, paper: Paper, is_breakthrough: bool = False) -> str:
        """Render a single paper card HTML"""
        card_class = "paper-card breakthrough" if is_breakthrough else "paper-card"

        # Format authors (show first 3)
        authors_str = ", ".join(paper.authors[:3])
        if len(paper.authors) > 3:
            authors_str += f" et al. ({len(paper.authors)} total)"

        # Format institutions (show first 2)
        institutions_str = ""
        if paper.institutions:
            institutions_str = ", ".join(paper.institutions[:2])
            if len(paper.institutions) > 2:
                institutions_str += f" +{len(paper.institutions) - 2} more"

        # Build sections
        sections_html = ""
        if paper.problem_summary:
            sections_html += f"<div class='paper-section'><strong>Problem:</strong> {paper.problem_summary}</div>"
        if paper.solution_summary:
            sections_html += f"<div class='paper-section'><strong>Solution:</strong> {paper.solution_summary}</div>"
        if paper.effect_summary:
            sections_html += f"<div class='paper-section'><strong>Impact:</strong> {paper.effect_summary}</div>"

        # Keywords
        keywords_html = ""
        if paper.keywords:
            keyword_tags = "".join([f"<span class='keyword'>{kw}</span>" for kw in paper.keywords[:8]])
            keywords_html = f"<div class='keywords'>{keyword_tags}</div>"

        # Breakthrough indicator
        breakthrough_badge = ""
        if is_breakthrough:
            score = f"{paper.breakthrough_score:.2f}" if paper.breakthrough_score else "N/A"
            breakthrough_badge = f"<div style='color: #d97706; font-weight: bold; margin-bottom: 10px;'>🔥 Breakthrough Score: {score}</div>"

        return f"""
        <div class='{card_class}'>
            {breakthrough_badge}
            <div class='paper-title'>{paper.title}</div>
            <div class='paper-meta'>
                👤 {authors_str}<br/>
                🏛️ {institutions_str if institutions_str else "N/A"}<br/>
                📅 {paper.published_at.strftime('%Y-%m-%d') if paper.published_at else 'N/A'}
            </div>
            {sections_html}
            {keywords_html}
            <a href='https://arxiv.org/abs/{paper.arxiv_id}' class='arxiv-link' target='_blank'>
                Read on arXiv →
            </a>
        </div>
        """


# Singleton instance
email_service = EmailService()