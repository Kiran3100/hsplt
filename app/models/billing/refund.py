"""
Payment refunds - audit trail and status.
"""
from sqlalchemy import Column, String, ForeignKey, Numeric, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database_types import UUID_TYPE
from app.models.base import TenantBaseModel


class Refund(TenantBaseModel):
    """Refund against a payment (full or partial)."""
    __tablename__ = "refunds"

    payment_id = Column(UUID_TYPE, ForeignKey("payments.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="SUCCESS")  # PENDING, SUCCESS, FAILED
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    refunded_by_user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    gateway_refund_id = Column(String(255), nullable=True)

    # Relationships
    payment = relationship("BillingPayment", back_populates="refunds")
    refunded_by_user = relationship("User")

    def __repr__(self):
        return f"<Refund(id={self.id}, payment_id={self.payment_id}, amount={self.amount}, status='{self.status}')>"
