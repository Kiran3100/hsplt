"""
Revenue reconciliation (daily summary, gateway reconciliation, discrepancy alerts).
"""
from sqlalchemy import Column, String, ForeignKey, Numeric, Text, Date, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database_types import UUID_TYPE
from app.models.base import TenantBaseModel


class Reconciliation(TenantBaseModel):
    """Daily reconciliation record."""
    __tablename__ = "reconciliations"

    recon_date = Column(Date, nullable=False)
    total_cash = Column(Numeric(12, 2), nullable=False, default=0)
    total_card = Column(Numeric(12, 2), nullable=False, default=0)
    total_upi = Column(Numeric(12, 2), nullable=False, default=0)
    total_online = Column(Numeric(12, 2), nullable=False, default=0)
    gateway_report_total = Column(Numeric(12, 2), nullable=True)
    discrepancy_amount = Column(Numeric(12, 2), nullable=True)
    status = Column(String(20), nullable=False, default="OK")  # OK, DISCREPANCY
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)

    # Relationships
    created_by_user = relationship("User")

    def __repr__(self):
        return f"<Reconciliation(id={self.id}, recon_date={self.recon_date}, status='{self.status}')>"
