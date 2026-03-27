"""
Payment receipt - receipt_number, pdf_path, emailed_to.
"""
from sqlalchemy import Column, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.core.database_types import UUID_TYPE
from app.models.base import TenantBaseModel


class PaymentReceipt(TenantBaseModel):
    __tablename__ = "payment_receipts"

    payment_id = Column(UUID_TYPE, ForeignKey("gateway_payments.id"), nullable=False)
    receipt_number = Column(String(50), nullable=False)
    pdf_path = Column(String(500), nullable=True)
    emailed_to = Column(String(255), nullable=True)
    is_duplicate = Column(Boolean, nullable=False, default=False)

    # Relationships
    payment = relationship("Payment", back_populates="receipts")

    def __repr__(self):
        return f"<PaymentReceipt(id={self.id}, receipt_number='{self.receipt_number}')>"
