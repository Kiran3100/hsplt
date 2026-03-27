"""
Payment refund - refund_amount, reason, gateway_refund_id.
"""
from sqlalchemy import Column, String, ForeignKey, Numeric, Text, DateTime
from sqlalchemy.orm import relationship
from app.core.database_types import UUID_TYPE
from app.models.base import TenantBaseModel


class PaymentRefund(TenantBaseModel):
    __tablename__ = "payment_refunds"

    payment_id = Column(UUID_TYPE, ForeignKey("gateway_payments.id"), nullable=False)
    refund_amount = Column(Numeric(12, 2), nullable=False)
    reason = Column(Text, nullable=True)
    refund_status = Column(String(20), nullable=False, default="SUCCESS")  # INITIATED, SUCCESS, FAILED
    gateway_refund_id = Column(String(255), nullable=True)
    refunded_by_user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)

    # Relationships
    payment = relationship("Payment", back_populates="refunds")
    refunded_by_user = relationship("User")

    def __repr__(self):
        return f"<PaymentRefund(id={self.id}, payment_id={self.payment_id}, refund_amount={self.refund_amount})>"
