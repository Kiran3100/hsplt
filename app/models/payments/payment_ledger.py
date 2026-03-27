"""
Payment ledger - financial history (DEBIT, CREDIT, REFUND).
"""
from sqlalchemy import Column, String, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database_types import UUID_TYPE
from app.models.base import TenantBaseModel


class PaymentLedger(TenantBaseModel):
    __tablename__ = "payment_ledger"

    bill_id = Column(UUID_TYPE, ForeignKey("bills.id"), nullable=False)
    payment_id = Column(UUID_TYPE, ForeignKey("gateway_payments.id"), nullable=True)  # null for some adjustments
    entry_type = Column(String(20), nullable=False)  # DEBIT, CREDIT, REFUND
    amount = Column(Numeric(12, 2), nullable=False)
    balance_after = Column(Numeric(12, 2), nullable=True)

    # Relationships
    bill = relationship("Bill")
    payment = relationship("Payment", back_populates="ledger_entries")

    def __repr__(self):
        return f"<PaymentLedger(id={self.id}, entry_type='{self.entry_type}', amount={self.amount})>"
