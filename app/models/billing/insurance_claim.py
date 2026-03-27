"""
Insurance claim processing.
"""
from sqlalchemy import Column, String, ForeignKey, Numeric, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database_types import UUID_TYPE
from app.models.base import TenantBaseModel


class InsuranceClaim(TenantBaseModel):
    """Insurance claim for a bill."""
    __tablename__ = "insurance_claims"

    bill_id = Column(UUID_TYPE, ForeignKey("bills.id"), nullable=False)
    patient_id = Column(UUID_TYPE, ForeignKey("patient_profiles.id"), nullable=False)
    insurance_provider_name = Column(String(255), nullable=False)
    policy_number = Column(String(100), nullable=True)
    claim_amount = Column(Numeric(12, 2), nullable=False)
    approved_amount = Column(Numeric(12, 2), nullable=True)
    status = Column(String(20), nullable=False, default="CREATED")  # CREATED, SUBMITTED, IN_REVIEW, APPROVED, REJECTED, SETTLED
    rejection_reason = Column(Text, nullable=True)
    settlement_reference = Column(String(100), nullable=True)

    # Relationships
    bill = relationship("Bill", back_populates="insurance_claims")
    patient = relationship("PatientProfile")

    def __repr__(self):
        return f"<InsuranceClaim(id={self.id}, status='{self.status}', claim_amount={self.claim_amount})>"
