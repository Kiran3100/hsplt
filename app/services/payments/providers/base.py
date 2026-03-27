"""
Payment provider interface - create_order, verify_signature, refund_payment.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class PaymentProviderInterface(ABC):
    @abstractmethod
    async def create_order(self, amount: float, currency: str, order_id: str, notes: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create order with gateway; return order_id, amount, etc."""
        pass

    @abstractmethod
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook/callback signature."""
        pass

    @abstractmethod
    async def refund_payment(self, transaction_id: str, amount: float, reason: Optional[str] = None) -> Dict[str, Any]:
        """Initiate refund with gateway; return gateway_refund_id."""
        pass

    @abstractmethod
    def parse_webhook_payload(self, payload: bytes) -> Dict[str, Any]:
        """Parse webhook body to get event type, payment_id, status."""
        pass
