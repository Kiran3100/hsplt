"""
Payment collection (multiple methods, partial, advance).
Idempotency via payment_ref.
"""
from sqlalchemy import Column, String, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database_types import UUID_TYPE, JSON_TYPE
from app.models.base import TenantBaseModel


class BillingPayment(TenantBaseModel):
    """Payment against a bill (idempotency via payment_ref)."""
    __tablename__ = "payments"

    bill_id = Column(UUID_TYPE, ForeignKey("bills.id"), nullable=False)
    payment_ref = Column(String(100), nullable=False)  # idempotency key
    method = Column(String(30), nullable=False)  # CASH, CARD, UPI, NETBANKING, WALLET, ONLINE_GATEWAY
    provider = Column(String(50), nullable=True)  # razorpay, stripe
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), nullable=False, default="INITIATED")  # INITIATED, SUCCESS, FAILED, REFUNDED
    paid_at = Column(DateTime(timezone=True), nullable=True)
    collected_by_user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    gateway_transaction_id = Column(String(255), nullable=True)
    extra_data = Column(JSON_TYPE, nullable=True)  # gateway payload, etc. (avoid name 'metadata' - reserved by SQLAlchemy)

    # Relationships
    bill = relationship("Bill", back_populates="payments")
    collected_by_user = relationship("User")
    financial_documents = relationship("FinancialDocument", back_populates="payment")
    refunds = relationship("Refund", back_populates="payment")

    def __repr__(self):
        return f"<BillingPayment(id={self.id}, payment_ref='{self.payment_ref}', status='{self.status}')>"
