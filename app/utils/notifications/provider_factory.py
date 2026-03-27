"""Build Email/SMS provider instance from provider name and config."""
from typing import Any, Optional

from app.utils.notifications.interfaces import EmailProviderInterface, SmsProviderInterface
from app.utils.notifications.email_providers import SendGridEmailProvider, AwsSesEmailProvider
from app.utils.notifications.sms_providers import TwilioSmsProvider, Msg91SmsProvider, AwsSnsSmsProvider


def get_email_provider(provider_name: str, config: Optional[dict[str, Any]] = None) -> EmailProviderInterface:
    name = (provider_name or "").upper()
    if name == "SENDGRID":
        return SendGridEmailProvider(config)
    if name == "AWS_SES":
        return AwsSesEmailProvider(config)
    return SendGridEmailProvider(config)


def get_sms_provider(provider_name: str, config: Optional[dict[str, Any]] = None) -> SmsProviderInterface:
    name = (provider_name or "").upper()
    if name == "TWILIO":
        return TwilioSmsProvider(config)
    if name == "MSG91":
        return Msg91SmsProvider(config)
    if name == "AWS_SNS":
        return AwsSnsSmsProvider(config)
    return TwilioSmsProvider(config)
