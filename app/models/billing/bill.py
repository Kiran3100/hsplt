"""
Bill header and line items (OPD/IPD).
Workflow: DRAFT -> FINALIZED -> PARTIALLY_PAID -> PAID (or CANCELLED).
"""
from sqlalchemy import Column, String, ForeignKey, Numeric, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database_types import UUID_TYPE
from app.models.base import BaseModel, TenantBaseModel


class Bill(TenantBaseModel):
    """Bill header (OPD or IPD)."""
    __tablename__ = "bills"

    bill_number = Column(String(50), nullable=False)
    bill_type = Column(String(10), nullable=False)  # OPD, IPD
    patient_id = Column(UUID_TYPE, ForeignKey("patient_profiles.id"), nullable=False)
    appointment_id = Column(UUID_TYPE, ForeignKey("appointments.id"), nullable=True)
    admission_id = Column(UUID_TYPE, ForeignKey("admissions.id"), nullable=True)
    status = Column(String(20), nullable=False, default="DRAFT")  # DRAFT, FINALIZED, PARTIALLY_PAID, PAID, CANCELLED
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(12, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(12, 2), nullable=False, default=0)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)
    amount_paid = Column(Numeric(12, 2), nullable=False, default=0)
    balance_due = Column(Numeric(12, 2), nullable=False, default=0)
    created_by_user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    finalized_by_user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    finalized_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    discount_approval_required = Column(Boolean, default=False)
    discount_approved_by_user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)

    # Relationships
    patient = relationship("PatientProfile", backref="bills")
    appointment = relationship("Appointment", backref="bills")
    admission = relationship("Admission", backref="bills")
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    finalized_by_user = relationship("User", foreign_keys=[finalized_by_user_id])
    discount_approved_by_user = relationship("User", foreign_keys=[discount_approved_by_user_id])
    items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")
    payments = relationship("BillingPayment", back_populates="bill")
    ipd_charges = relationship("IPDCharge", back_populates="bill")
    insurance_claims = relationship("InsuranceClaim", back_populates="bill")
    financial_documents = relationship("FinancialDocument", back_populates="bill")

    def __repr__(self):
        return f"<Bill(id={self.id}, bill_number='{self.bill_number}', status='{self.status}')>"


class BillItem(BaseModel):
    """Bill line item (linked to service or custom description). No hospital_id (scoped by bill)."""
    __tablename__ = "bill_items"

    bill_id = Column(UUID_TYPE, ForeignKey("bills.id"), nullable=False)
    service_item_id = Column(UUID_TYPE, ForeignKey("service_items.id"), nullable=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=False)
    tax_percentage = Column(Numeric(5, 2), nullable=False, default=0)
    line_subtotal = Column(Numeric(12, 2), nullable=False)
    line_tax = Column(Numeric(12, 2), nullable=False, default=0)
    line_total = Column(Numeric(12, 2), nullable=False)

    # Relationships
    bill = relationship("Bill", back_populates="items")
    service_item = relationship("ServiceItem", back_populates="bill_items")

    def __repr__(self):
        return f"<BillItem(id={self.id}, bill_id={self.bill_id}, description='{self.description[:30]}')>"
