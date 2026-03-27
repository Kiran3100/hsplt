"""SMS provider implementations: Twilio, MSG91, AWS SNS. Config from provider config or env."""
import asyncio
import logging
from typing import Any, Optional

from app.utils.notifications.interfaces import SmsProviderInterface

logger = logging.getLogger(__name__)


class TwilioSmsProvider(SmsProviderInterface):
    """Twilio. Config: account_sid, auth_token, from_number (or env)."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}
        import os
        self._account_sid = self.config.get("account_sid") or os.getenv("TWILIO_ACCOUNT_SID")
        self._auth_token = self.config.get("auth_token") or os.getenv("TWILIO_AUTH_TOKEN")
        self._from_number = self.config.get("from_number") or os.getenv("TWILIO_FROM_NUMBER")

    async def send_sms(
        self,
        to: str,
        message: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        if not self._account_sid or not self._auth_token:
            logger.warning("Twilio not configured; stubbing send")
            return "stub-twilio-" + to[:8]
        try:
            from twilio.rest import Client
        except ImportError:
            logger.warning("twilio package not installed; stubbing send")
            return "stub-twilio-" + to[:8]

        def _send():
            client = Client(self._account_sid, self._auth_token)
            msg = client.messages.create(
                body=message,
                from_=self._from_number or "+0000000000",
                to=to,
            )
            return msg.sid

        try:
            return await asyncio.to_thread(_send)
        except Exception as e:
            logger.exception("Twilio send failed: %s", e)
            raise


class Msg91SmsProvider(SmsProviderInterface):
    """MSG91. Config: auth_key, sender (optional)."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}
        import os
        self._auth_key = self.config.get("auth_key") or os.getenv("MSG91_AUTH_KEY")
        self._sender = self.config.get("sender") or os.getenv("MSG91_SENDER", "HSM")

    async def send_sms(
        self,
        to: str,
        message: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        if not self._auth_key:
            logger.warning("MSG91 not configured; stubbing send")
            return "stub-msg91-" + to[:8]
        try:
            import aiohttp
        except ImportError:
            logger.warning("aiohttp not installed; stubbing MSG91 send")
            return "stub-msg91-" + to[:8]
        url = "https://api.msg91.com/api/v5/flow/"
        headers = {"authkey": self._auth_key, "Content-Type": "application/json"}
        payload = {
            "sender": self._sender,
            "short_url": "0",
            "mobiles": to.lstrip("+"),
            "message": message,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"MSG91 error {resp.status}: {text}")
                data = await resp.json()
                return data.get("request_id") or data.get("type") or "msg91-ok"
        return None


class AwsSnsSmsProvider(SmsProviderInterface):
    """AWS SNS SMS. Config: region, (optional credentials)."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}
        import os
        self._region = self.config.get("region") or os.getenv("AWS_REGION", "us-east-1")

    async def send_sms(
        self,
        to: str,
        message: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        try:
            import boto3
        except ImportError:
            logger.warning("boto3 not installed; stubbing SNS send")
            return "stub-sns-" + to[:8]

        def _send():
            client = boto3.client("sns", region_name=self._region)
            resp = client.publish(PhoneNumber=to, Message=message)
            return resp.get("MessageId")

        try:
            return await asyncio.to_thread(_send)
        except Exception as e:
            logger.exception("SNS send failed: %s", e)
            raise
