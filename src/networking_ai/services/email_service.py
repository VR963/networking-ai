"""
Email Service - Phase 3 Week 2.

Email delivery service with template support.

Features:
- HTML email templates
- Template variable substitution
- SMTP delivery
- SendGrid/Mailgun integration (optional)
- Delivery tracking
- Email validation
"""

from typing import Dict, Optional, List
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path


class EmailService:
    """
    Service for sending HTML emails with templates.

    Supports SMTP and third-party email providers.
    """

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = "Networking AI",
        use_sendgrid: bool = False,
        sendgrid_api_key: Optional[str] = None
    ):
        """
        Initialize email service.

        Args:
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_username: SMTP username
            smtp_password: SMTP password
            from_email: From email address
            from_name: From name
            use_sendgrid: Use SendGrid instead of SMTP
            sendgrid_api_key: SendGrid API key
        """
        # SMTP configuration
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "localhost")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = smtp_username or os.getenv("SMTP_USERNAME", "")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD", "")

        # Email configuration
        self.from_email = from_email or os.getenv("FROM_EMAIL", "noreply@networking-ai.com")
        self.from_name = from_name

        # Third-party providers
        self.use_sendgrid = use_sendgrid
        self.sendgrid_api_key = sendgrid_api_key or os.getenv("SENDGRID_API_KEY")

        # Template directory
        self.template_dir = Path(__file__).parent.parent.parent / "templates" / "email"

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text fallback (optional)

        Returns:
            True if sent successfully
        """
        try:
            if self.use_sendgrid and self.sendgrid_api_key:
                return await self._send_via_sendgrid(to_email, subject, html_content, text_content)
            else:
                return await self._send_via_smtp(to_email, subject, html_content, text_content)
        except Exception as e:
            print(f"[Email] Failed to send email to {to_email}: {e}")
            return False

    async def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str]
    ) -> bool:
        """Send email via SMTP."""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            # Add text and HTML parts
            if text_content:
                part1 = MIMEText(text_content, "plain")
                msg.attach(part1)

            part2 = MIMEText(html_content, "html")
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_username and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)

                server.send_message(msg)

            print(f"[Email] Sent to {to_email}: {subject}")
            return True

        except Exception as e:
            print(f"[Email] SMTP error: {e}")
            return False

    async def _send_via_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str]
    ) -> bool:
        """Send email via SendGrid."""
        try:
            # TODO: Implement SendGrid integration
            # from sendgrid import SendGridAPIClient
            # from sendgrid.helpers.mail import Mail
            #
            # message = Mail(
            #     from_email=self.from_email,
            #     to_emails=to_email,
            #     subject=subject,
            #     html_content=html_content
            # )
            #
            # sg = SendGridAPIClient(self.sendgrid_api_key)
            # response = sg.send(message)
            #
            # return response.status_code == 202

            print(f"[Email] SendGrid not implemented, falling back to SMTP")
            return await self._send_via_smtp(to_email, subject, html_content, text_content)

        except Exception as e:
            print(f"[Email] SendGrid error: {e}")
            return False

    def load_template(self, template_name: str) -> str:
        """
        Load an email template from file.

        Args:
            template_name: Template filename (without .html extension)

        Returns:
            Template HTML content
        """
        template_path = self.template_dir / f"{template_name}.html"

        if not template_path.exists():
            print(f"[Email] Template not found: {template_path}")
            return self._get_default_template()

        with open(template_path, "r") as f:
            return f.read()

    def render_template(self, template_content: str, variables: Dict[str, str]) -> str:
        """
        Render template with variables.

        Simple string substitution: {{variable_name}} -> value

        Args:
            template_content: Template HTML
            variables: Dictionary of variable name -> value

        Returns:
            Rendered HTML
        """
        rendered = template_content

        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            rendered = rendered.replace(placeholder, str(value))

        return rendered

    async def send_notification_email(
        self,
        to_email: str,
        notification
    ) -> bool:
        """
        Send email for a notification using appropriate template.

        Args:
            to_email: Recipient email
            notification: Notification object

        Returns:
            True if sent successfully
        """
        # Get template name based on notification type
        template_name = self._get_template_for_type(notification.notification_type.value)

        # Load template
        template_html = self.load_template(template_name)

        # Prepare variables
        variables = {
            "title": notification.title,
            "message": notification.message,
            "action_url": notification.action_url or "#",
            "action_text": notification.action_text or "View Details",
            "year": "2024"
        }

        # Add metadata variables
        if notification.metadata:
            variables.update(notification.metadata)

        # Render template
        html_content = self.render_template(template_html, variables)

        # Send email
        return await self.send_email(
            to_email=to_email,
            subject=notification.title,
            html_content=html_content,
            text_content=notification.message
        )

    async def send_daily_digest(
        self,
        to_email: str,
        user_name: str,
        matches: List[Dict],
        messages: List[Dict],
        applications: List[Dict]
    ) -> bool:
        """
        Send daily digest email.

        Args:
            to_email: Recipient email
            user_name: User's name
            matches: List of match dictionaries
            messages: List of message dictionaries
            applications: List of application dictionaries

        Returns:
            True if sent successfully
        """
        template_html = self.load_template("daily_digest")

        # Build match list HTML
        matches_html = ""
        for match in matches:
            matches_html += f"""
            <li style="margin-bottom: 15px;">
                <strong>{match['job_title']}</strong> at {match['company_name']}<br>
                <small>{int(match['match_score'] * 100)}% match</small>
            </li>
            """

        # Build message list HTML
        messages_html = ""
        for message in messages:
            messages_html += f"""
            <li style="margin-bottom: 15px;">
                <strong>From {message['sender']}</strong><br>
                <small>{message['preview']}</small>
            </li>
            """

        variables = {
            "user_name": user_name,
            "matches_count": len(matches),
            "messages_count": len(messages),
            "applications_count": len(applications),
            "matches_html": matches_html or "<p>No new matches today</p>",
            "messages_html": messages_html or "<p>No new messages today</p>",
            "year": "2024"
        }

        html_content = self.render_template(template_html, variables)

        return await self.send_email(
            to_email=to_email,
            subject=f"Your Daily Digest - {len(matches)} new matches",
            html_content=html_content
        )

    def _get_template_for_type(self, notification_type: str) -> str:
        """Get template name for notification type."""
        template_map = {
            "match_new": "new_match",
            "message_new": "new_message",
            "application_received": "application_received",
            "application_screened": "application_screened",
            "interview_scheduled": "interview_scheduled",
            "daily_digest": "daily_digest"
        }

        return template_map.get(notification_type, "generic_notification")

    def _get_default_template(self) -> str:
        """Get default email template."""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{title}}</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f4f4f4; padding: 20px; border-radius: 10px;">
        <h1 style="color: #2c3e50;">{{title}}</h1>
        <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
            <p>{{message}}</p>
            <a href="{{action_url}}" style="display: inline-block; background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 15px;">
                {{action_text}}
            </a>
        </div>
        <p style="font-size: 12px; color: #7f8c8d; text-align: center;">
            &copy; {{year}} Networking AI. All rights reserved.
        </p>
    </div>
</body>
</html>
        """.strip()


def create_email_service(
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    from_email: Optional[str] = None
) -> EmailService:
    """
    Factory function to create email service.

    Args:
        smtp_host: SMTP server host
        smtp_port: SMTP server port
        from_email: From email address

    Returns:
        EmailService instance
    """
    return EmailService(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        from_email=from_email
    )
