"""
Service/Item master and tax configuration for billing.
"""
from sqlalchemy import Column, String, ForeignKey, Boolean, Numeric, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database_types import UUID_TYPE
from app.models.base import TenantBaseModel


class TaxProfile(TenantBaseModel):
    """Tax configuration (e.g. GST 5%)."""
    __tablename__ = "tax_profiles"

    name = Column(String(100), nullable=False)
    gst_percentage = Column(Numeric(5, 2), nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    hospital = relationship("Hospital", backref="billing_tax_profiles")
    service_items = relationship("ServiceItem", back_populates="tax_profile")

    def __repr__(self):
        return f"<TaxProfile(id={self.id}, name='{self.name}', hospital_id={self.hospital_id})>"


class ServiceItem(TenantBaseModel):
    """Service/Item master for billing (consultation, procedure, investigation, etc.)."""
    __tablename__ = "service_items"

    department_id = Column(UUID_TYPE, ForeignKey("departments.id"), nullable=True)
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)  # CONSULTATION, PROCEDURE, INVESTIGATION, LAB, PHARMACY, BED, PACKAGE, MISC
    base_price = Column(Numeric(12, 2), nullable=False, default=0)
    tax_profile_id = Column(UUID_TYPE, ForeignKey("tax_profiles.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    department = relationship("Department")
    tax_profile = relationship("TaxProfile", back_populates="service_items")
    bill_items = relationship("BillItem", back_populates="service_item")

    __table_args__ = (
        # Unique code per hospital
        {"sqlite_autoincrement": False},
    )

    def __repr__(self):
        return f"<ServiceItem(id={self.id}, code='{self.code}', hospital_id={self.hospital_id})>"
