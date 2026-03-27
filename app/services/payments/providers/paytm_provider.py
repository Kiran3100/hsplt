"""
Paytm Payment Provider.

FIX: Previous version was a stub that returned fake order IDs with no actual
Paytm API calls. This version calls the official Paytm Payment Gateway API.

Install: pip install paytmchecksum requests

Operates in SANDBOX_STUB mode if PAYTM_MID / PAYTM_KEY are not configured.
The stub mode logs a clear warning so operators know payments are not real.
"""
import json
import logging
import hashlib
import string
import random
from typing import Optional, Dict, Any
from app.services.payments.providers.base import PaymentProviderInterface
from app.core.config import settings

logger = logging.getLogger(__name__)


class PaytmProvider(PaymentProviderInterface):

    def __init__(self):
        self.mid = getattr(settings, "PAYTM_MID", "") or ""
        self.key = getattr(settings, "PAYTM_KEY", "") or ""
        self.env = getattr(settings, "PAYTM_ENV", "sandbox")
        self.website = getattr(settings, "PAYTM_WEBSITE", "WEBSTAGING")
        self.callback_url = getattr(settings, "PAYTM_CALLBACK_URL", "")
        self._sandbox = not (self.mid and self.key)
        if self._sandbox:
            logger.warning(
                "PaytmProvider: PAYTM_MID/PAYTM_KEY not configured. "
                "Running in SANDBOX_STUB mode — no real payments will be processed."
            )

        if self.env == "production":
            self.base_url = "https://securegw.paytm.in"
        else:
            self.base_url = "https://securegw-stage.paytm.in"

    def _generate_checksum(self, params: dict) -> str:
        """Generate Paytm checksum using HMAC-SHA256."""
        try:
            import paytmchecksum
            return paytmchecksum.generateSignature(params, self.key)
        except ImportError:
            # Fallback simple checksum (not secure — install paytmchecksum)
            logger.warning("paytmchecksum not installed. Checksum generation is insecure.")
            payload = "|".join(str(params.get(k, "")) for k in sorted(params))
            import hmac, hashlib
            return hmac.new(self.key.encode(), payload.encode(), hashlib.sha256).hexdigest()

    async def create_order(
        self,
        amount: float,
        currency: str,
        order_id: str,
        notes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if self._sandbox:
            logger.warning(f"[SANDBOX] Faking Paytm order for ₹{amount}")
            return {
                "orderId": order_id,
                "txnToken": f"PAYTM_SANDBOX_TOKEN_{order_id[:12]}",
                "txnAmount": {"value": str(amount), "currency": "INR"},
                "sandbox": True,
            }

        try:
            import requests
            params = {
                "MID": self.mid,
                "WEBSITE": self.website,
                "CHANNEL_ID": "WEB",
                "ORDER_ID": order_id[:50],
                "CUST_ID": (notes or {}).get("patient_id", "CUST_" + order_id[:8]),
                "TXN_AMOUNT": f"{amount:.2f}",
                "CURRENCY": "INR",
                "CALLBACK_URL": self.callback_url,
            }
            params["CHECKSUMHASH"] = self._generate_checksum(params)

            response = requests.post(
                f"{self.base_url}/theia/api/v1/initiateTransaction?mid={self.mid}&orderId={order_id}",
                json={"head": {"requestTimestamp": "", "channelId": "WEB", "version": "v1"}, "body": params},
                timeout=15,
            )
            data = response.json()
            body = data.get("body", {})

            if body.get("resultInfo", {}).get("resultStatus") != "S":
                raise RuntimeError(f"Paytm error: {body.get('resultInfo', {}).get('resultMsg')}")

            logger.info(f"[PAYTM] Order initiated: {order_id}")
            return {
                "orderId": order_id,
                "txnToken": body.get("txnToken"),
                "txnAmount": {"value": str(amount), "currency": "INR"},
            }
        except Exception as e:
            logger.error(f"[PAYTM] Order creation failed: {e}")
            raise RuntimeError(f"Paytm order creation failed: {e}")

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        if not self.key:
            logger.warning("[PAYTM] key not set — signature verification SKIPPED")
            return True
        try:
            import paytmchecksum
            data = json.loads(payload.decode("utf-8"))
            checksum = data.get("CHECKSUMHASH", signature)
            return paytmchecksum.verifySignature(data, self.key, checksum)
        except Exception as e:
            logger.error(f"[PAYTM] Signature verification error: {e}")
            return False

    async def refund_payment(
        self,
        transaction_id: str,
        amount: float,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self._sandbox:
            return {"refId": f"REF_{transaction_id[:8]}", "status": "TXN_SUCCESS", "sandbox": True}

        try:
            import requests
            ref_id = "REF" + "".join(random.choices(string.digits, k=10))
            params = {
                "MID": self.mid,
                "TXNID": transaction_id,
                "REFUNDAMOUNT": f"{amount:.2f}",
                "REFID": ref_id,
            }
            params["CHECKSUMHASH"] = self._generate_checksum(params)
            response = requests.post(
                f"{self.base_url}/v2/refund/apply",
                json={"head": {}, "body": params},
                timeout=15,
            )
            data = response.json().get("body", {})
            logger.info(f"[PAYTM] Refund {ref_id} for txn {transaction_id}")
            return {"refId": data.get("refId", ref_id), "status": data.get("resultInfo", {}).get("resultStatus")}
        except Exception as e:
            raise RuntimeError(f"Paytm refund failed: {e}")

    def parse_webhook_payload(self, payload: bytes) -> Dict[str, Any]:
        try:
            data = json.loads(payload.decode("utf-8"))
            return {
                "event": data.get("STATUS", "TXN_SUCCESS"),
                "payment_id": data.get("TXNID"),
                "order_id": data.get("ORDERID"),
                "status": "SUCCESS" if data.get("STATUS") == "TXN_SUCCESS" else "FAILED",
                "amount": float(data.get("TXNAMOUNT", 0)),
            }
        except Exception:
            return {}
