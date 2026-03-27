"""Email and SMS provider interfaces."""
from abc import ABC, abstractmethod
from typing import Any, Optional


class EmailProviderInterface(ABC):
    @abstractmethod
    async def send_email(
        self,
        to: str,
        subject: str,
        html: Optional[str] = None,
        text: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Send email. Returns provider_message_id on success, None or raises on failure.
        """
        pass


class SmsProviderInterface(ABC):
    @abstractmethod
    async def send_sms(
        self,
        to: str,
        message: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Send SMS. Returns provider_message_id on success, None or raises on failure.
        """
        pass
