"""
Payment record - idempotency via payment_reference, gateway fields.
Table: gateway_payments (to avoid conflict with billing.payments if present).
"""
from sqlalchemy import Column, String, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import relationship
from app.core.database_types import UUID_TYPE, JSON_TYPE
from app.models.base import TenantBaseModel


class Payment(TenantBaseModel):
    __tablename__ = "gateway_payments"

    bill_id = Column(UUID_TYPE, ForeignKey("bills.id"), nullable=False)
    payment_reference = Column(String(100), nullable=False, unique=True)  # idempotency key
    method = Column(String(20), nullable=False)  # CASH, CARD, UPI, ONLINE, WALLET
    provider = Column(String(30), nullable=True)  # RAZORPAY, STRIPE, PAYTM, NULL for cash
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(5), nullable=False, default="INR")
    status = Column(String(20), nullable=False, default="INITIATED")  # INITIATED, SUCCESS, FAILED, REFUNDED
    transaction_id = Column(String(255), nullable=True)  # gateway txn id
    gateway_order_id = Column(String(255), nullable=True)
    gateway_signature = Column(String(500), nullable=True)
    collected_by_user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSON_TYPE, nullable=True)  # jsonb; avoid 'metadata' attr name conflict with SA

    # Relationships
    bill = relationship("Bill", backref="gateway_payments")
    collected_by_user = relationship("User")
    receipts = relationship("PaymentReceipt", back_populates="payment")
    ledger_entries = relationship("PaymentLedger", back_populates="payment")
    refunds = relationship("PaymentRefund", back_populates="payment")

    def __repr__(self):
        return f"<Payment(id={self.id}, payment_reference='{self.payment_reference}', status='{self.status}')>"
