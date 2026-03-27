"""
Stripe Payment Provider — Real SDK Integration.

FIX: Previously create_order() was a stub. Now uses stripe Python SDK.
Install: pip install stripe

Operates in SANDBOX_STUB mode if STRIPE_SECRET_KEY is not configured.
"""
import json
import logging
from typing import Optional, Dict, Any
from app.services.payments.providers.base import PaymentProviderInterface
from app.core.config import settings

logger = logging.getLogger(__name__)


class StripeProvider(PaymentProviderInterface):

    def __init__(self):
        self.secret_key = getattr(settings, "STRIPE_SECRET_KEY", "") or ""
        self.webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "") or ""
        self._sandbox = not self.secret_key
        if self._sandbox:
            logger.warning(
                "StripeProvider: STRIPE_SECRET_KEY not configured. "
                "Running in SANDBOX_STUB mode."
            )

    def _get_stripe(self):
        try:
            import stripe
            stripe.api_key = self.secret_key
            return stripe
        except ImportError:
            return None

    async def create_order(
        self,
        amount: float,
        currency: str,
        order_id: str,
        notes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if self._sandbox:
            logger.warning(f"[SANDBOX] Faking Stripe PaymentIntent for ${amount}")
            return {
                "id": f"pi_SANDBOX_{order_id[:16]}",
                "client_secret": f"pi_SANDBOX_secret_{order_id[:16]}",
                "amount": int(amount * 100),
                "currency": currency.lower(),
                "status": "requires_payment_method",
                "sandbox": True,
            }

        stripe = self._get_stripe()
        if not stripe:
            raise RuntimeError("stripe SDK not installed. Run: pip install stripe")

        try:
            intent = stripe.PaymentIntent.create(
                amount=int(round(amount * 100)),
                currency=currency.lower(),
                metadata={"order_id": order_id, **(notes or {})},
            )
            logger.info(f"[STRIPE] PaymentIntent created: {intent.id}")
            return {"id": intent.id, "client_secret": intent.client_secret, "status": intent.status}
        except Exception as e:
            logger.error(f"[STRIPE] PaymentIntent creation failed: {e}")
            raise RuntimeError(f"Stripe order creation failed: {e}")

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        if not self.webhook_secret:
            logger.warning("[STRIPE] webhook_secret not set — signature verification SKIPPED")
            return True
        try:
            import stripe
            stripe.api_key = self.secret_key
            stripe.WebhookSignature.verify_header(payload, signature, self.webhook_secret)
            return True
        except Exception:
            return False

    async def refund_payment(
        self,
        transaction_id: str,
        amount: float,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self._sandbox:
            return {"id": f"re_SANDBOX_{transaction_id[:8]}", "status": "succeeded", "sandbox": True}

        stripe = self._get_stripe()
        if not stripe:
            raise RuntimeError("stripe not installed")
        try:
            refund = stripe.Refund.create(
                payment_intent=transaction_id,
                amount=int(round(amount * 100)),
            )
            return {"id": refund.id, "status": refund.status}
        except Exception as e:
            raise RuntimeError(f"Stripe refund failed: {e}")

    def parse_webhook_payload(self, payload: bytes) -> Dict[str, Any]:
        try:
            data = json.loads(payload.decode("utf-8"))
            obj = data.get("data", {}).get("object", {})
            return {
                "event": data.get("type", ""),
                "payment_id": obj.get("id"),
                "order_id": (obj.get("metadata") or {}).get("order_id"),
                "status": obj.get("status"),
                "amount": (obj.get("amount") or 0) / 100,
            }
        except Exception:
            return {}
