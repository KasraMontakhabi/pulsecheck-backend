import logging
from typing import Optional
from postmarker.core import PostmarkClient
from app.core.config import settings
from app.models.monitor import Monitor

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.client = None
        if settings.POSTMARK_API_TOKEN and not settings.EMAIL_DEV_MODE:
            self.client = PostmarkClient(server_token=settings.POSTMARK_API_TOKEN)

    async def send_down_alert(self, monitor: Monitor, error_message: Optional[str] = None):
        """Send email alert when monitor goes down"""
        subject = f"🔴 {monitor.name or monitor.url} is DOWN"

        error_text = f"\nError: {error_message}" if error_message else ""

        html_body = f"""
        <h2>Monitor Alert</h2>
        <p><strong>{monitor.name or monitor.url}</strong> is currently down.</p>
        <p><strong>URL:</strong> <a href="{monitor.url}">{monitor.url}</a></p>
        <p><strong>Check Interval:</strong> {monitor.interval} seconds</p>
        <p><strong>Last Checked:</strong> {monitor.last_checked_at}</p>
        {f"<p><strong>Error:</strong> {error_message}</p>" if error_message else ""}
        <hr>
        <p>This is an automated alert from PulseCheck.</p>
        """

        text_body = f"""
        Monitor Alert: {monitor.name or monitor.url} is DOWN

        URL: {monitor.url}
        Check Interval: {monitor.interval} seconds
        Last Checked: {monitor.last_checked_at}
        {error_text}

        This is an automated alert from PulseCheck.
        """

        if self.client and not settings.EMAIL_DEV_MODE:
            try:

                to_email = "admin@example.com"  # TODO: Get from monitor.user.email

                self.client.emails.send(
                    From=settings.EMAIL_FROM,
                    To=to_email,
                    Subject=subject,
                    HtmlBody=html_body,
                    TextBody=text_body,
                )
                logger.info(f"Alert email sent for monitor {monitor.id}")
            except Exception as e:
                logger.error(f"Failed to send email alert: {e}")
        else:
            # Development mode - log to console
            logger.info(f"EMAIL ALERT (DEV MODE):")
            logger.info(f"Subject: {subject}")
            logger.info(f"Body: {text_body}")

    async def send_up_alert(self, monitor: Monitor):
        """Send email alert when monitor comes back up"""
        subject = f"✅ {monitor.name or monitor.url} is UP"

        html_body = f"""
        <h2>Monitor Recovery</h2>
        <p><strong>{monitor.name or monitor.url}</strong> is back online!</p>
        <p><strong>URL:</strong> <a href="{monitor.url}">{monitor.url}</a></p>
        <p><strong>Response Time:</strong> {monitor.last_latency_ms}ms</p>
        <p><strong>Recovered At:</strong> {monitor.last_checked_at}</p>
        <hr>
        <p>This is an automated notification from PulseCheck.</p>
        """

        if settings.EMAIL_DEV_MODE:
            logger.info(f"EMAIL RECOVERY (DEV MODE): {subject}")
            logger.info(f"Monitor {monitor.name or monitor.url} is back up!")