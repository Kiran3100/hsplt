"""
Razorpay Payment Provider — Real SDK Integration.

FIX: Previously create_order() was a stub comment with no actual Razorpay API call.
This implementation uses the official razorpay Python SDK.

Install: pip install razorpay

If RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are not set, the provider operates
in SANDBOX_STUB mode — it generates fake order IDs locally and logs a warning.
This prevents crashes in development while making it obvious no real payments occur.
"""
import json
import hmac
import hashlib
import logging
from typing import Optional, Dict, Any
from app.services.payments.providers.base import PaymentProviderInterface
from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_razorpay_client():
    """Lazy import razorpay client."""
    try:
        import razorpay
        return razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    except ImportError:
        return None


class RazorpayProvider(PaymentProviderInterface):

    def __init__(self):
        self.key_id = getattr(settings, "RAZORPAY_KEY_ID", "") or ""
        self.key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "") or ""
        self.webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "") or ""
        self._sandbox = not (self.key_id and self.key_secret)
        if self._sandbox:
            logger.warning(
                "RazorpayProvider: RAZORPAY_KEY_ID/KEY_SECRET not configured. "
                "Running in SANDBOX_STUB mode — no real payments will be processed."
            )

    async def create_order(
        self,
        amount: float,
        currency: str,
        order_id: str,
        notes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a Razorpay order.
        Returns the Razorpay order object which includes the razorpay_order_id
        that the frontend uses to open the payment widget.
        """
        amount_paise = int(round(amount * 100))  # Razorpay uses smallest currency unit

        if self._sandbox:
            logger.warning(f"[SANDBOX] Faking Razorpay order for ₹{amount}")
            return {
                "id": f"order_SANDBOX_{order_id[:16]}",
                "entity": "order",
                "amount": amount_paise,
                "currency": currency,
                "receipt": order_id,
                "status": "created",
                "sandbox": True,
            }

        client = _get_razorpay_client()
        if not client:
            raise RuntimeError(
                "razorpay SDK not installed. Run: pip install razorpay"
            )

        try:
            razorpay_order = client.order.create({
                "amount": amount_paise,
                "currency": currency,
                "receipt": order_id[:40],  # max 40 chars
                "notes": notes or {},
                "payment_capture": 1,  # Auto-capture
            })
            logger.info(
                f"[RAZORPAY] Order created: {razorpay_order.get('id')} "
                f"for ₹{amount} ({currency})"
            )
            return razorpay_order
        except Exception as e:
            logger.error(f"[RAZORPAY] Order creation failed: {e}")
            raise RuntimeError(f"Razorpay order creation failed: {e}")

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Razorpay webhook signature using HMAC-SHA256."""
        if not self.webhook_secret:
            logger.warning("[RAZORPAY] webhook_secret not set — signature verification SKIPPED")
            return True  # Allow in dev; reject in prod if this is called without secret
        if not signature:
            return False
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def refund_payment(
        self,
        transaction_id: str,
        amount: float,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Issue a refund for a Razorpay payment.
        """
        if self._sandbox:
            logger.warning(f"[SANDBOX] Faking Razorpay refund for payment {transaction_id}")
            return {
                "id": f"rfnd_SANDBOX_{transaction_id[:8]}",
                "payment_id": transaction_id,
                "amount": int(amount * 100),
                "status": "processed",
                "sandbox": True,
            }

        client = _get_razorpay_client()
        if not client:
            raise RuntimeError("razorpay SDK not installed. Run: pip install razorpay")

        try:
            refund = client.payment.refund(transaction_id, {
                "amount": int(round(amount * 100)),
                "notes": {"reason": reason or "Requested by hospital"},
            })
            logger.info(f"[RAZORPAY] Refund issued: {refund.get('id')} for payment {transaction_id}")
            return refund
        except Exception as e:
            logger.error(f"[RAZORPAY] Refund failed for {transaction_id}: {e}")
            raise RuntimeError(f"Razorpay refund failed: {e}")

    def parse_webhook_payload(self, payload: bytes) -> Dict[str, Any]:
        """Parse Razorpay webhook event payload."""
        try:
            data = json.loads(payload.decode("utf-8"))
            event = data.get("event", "")
            entity = (
                data.get("payload", {})
                .get("payment", {})
                .get("entity", data.get("payload", {}).get("entity", {}))
            )
            return {
                "event": event,
                "payment_id": entity.get("id"),
                "order_id": entity.get("order_id"),
                "status": entity.get("status"),
                "amount": (entity.get("amount") or 0) / 100,
            }
        except Exception as e:
            logger.error(f"[RAZORPAY] Webhook parse error: {e}")
            return {}
