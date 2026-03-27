"""Email provider implementations: SendGrid, AWS SES. Config from provider config or env."""
import asyncio
import logging
from typing import Any, Optional

from app.utils.notifications.interfaces import EmailProviderInterface

logger = logging.getLogger(__name__)


class SendGridEmailProvider(EmailProviderInterface):
    """SendGrid. Config: api_key, from_email (optional)."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}
        self._api_key = self.config.get("api_key") or self._env_key()
        self._from_email = self.config.get("from_email") or self._env_from()

    def _env_key(self) -> Optional[str]:
        import os
        return os.getenv("SENDGRID_API_KEY")

    def _env_from(self) -> Optional[str]:
        import os
        return os.getenv("EMAIL_FROM") or os.getenv("SENDGRID_FROM_EMAIL")

    async def send_email(
        self,
        to: str,
        subject: str,
        html: Optional[str] = None,
        text: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        if not self._api_key:
            logger.warning("SendGrid: api_key not configured, skipping send")
            return None
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content
        except ImportError:
            logger.warning("sendgrid package not installed; stubbing send")
            return "stub-sendgrid-" + to[:8]
        try:
            message = Mail(
                from_email=Email(self._from_email or "noreply@example.com"),
                to_emails=To(to),
                subject=subject,
                plain_text_content=Content("text/plain", text or (html or "")),
                html_content=Content("text/html", html or (text or "")),
            )
            sg = SendGridAPIClient(api_key=self._api_key)

            def _send():
                return sg.send(message)

            response = await asyncio.to_thread(_send)
            return getattr(response, "headers", {}).get("X-Message-Id") or str(response.status_code)
        except Exception as e:
            logger.exception("SendGrid send failed: %s", e)
            raise


class AwsSesEmailProvider(EmailProviderInterface):
    """AWS SES. Config: region, access_key, secret_key (optional if env/IAM), from_email."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}
        self._region = self.config.get("region") or __import__("os").getenv("AWS_REGION", "us-east-1")
        self._from = self.config.get("from_email") or __import__("os").getenv("EMAIL_FROM")

    async def send_email(
        self,
        to: str,
        subject: str,
        html: Optional[str] = None,
        text: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            logger.warning("boto3 not installed; stubbing SES send")
            return "stub-ses-" + to[:8]
        body = {}
        if html:
            body["Html"] = {"Data": html, "Charset": "UTF-8"}
        if text:
            body["Text"] = {"Data": text, "Charset": "UTF-8"}
        if not body:
            body["Text"] = {"Data": subject, "Charset": "UTF-8"}

        def _send():
            client = boto3.client("ses", region_name=self._region)
            return client.send_email(
                Source=self._from or "noreply@example.com",
                Destination={"ToAddresses": [to]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": body,
                },
            )

        try:
            resp = await asyncio.to_thread(_send)
            return resp.get("MessageId")
        except Exception as e:
            logger.exception("SES send failed: %s", e)
            raise
