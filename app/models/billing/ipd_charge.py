"""
IPD daily charges / bed charges tracking.
"""
from sqlalchemy import Column, String, ForeignKey, Numeric, Date, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database_types import UUID_TYPE
from app.models.base import TenantBaseModel


class IPDCharge(TenantBaseModel):
    """IPD charge line (bed, nursing, procedure, etc.) for a date."""
    __tablename__ = "ipd_charges"

    bill_id = Column(UUID_TYPE, ForeignKey("bills.id"), nullable=False)
    admission_id = Column(UUID_TYPE, ForeignKey("admissions.id"), nullable=False)
    charge_date = Column(Date, nullable=False)
    charge_type = Column(String(30), nullable=False)  # BED, NURSING, PROCEDURE, OTHER
    reference_id = Column(UUID_TYPE, nullable=True)  # bed_id, procedure_id, etc.
    amount = Column(Numeric(12, 2), nullable=False)

    # Relationships
    bill = relationship("Bill", back_populates="ipd_charges")
    admission = relationship("Admission")

    def __repr__(self):
        return f"<IPDCharge(id={self.id}, charge_date={self.charge_date}, type='{self.charge_type}', amount={self.amount})>"
