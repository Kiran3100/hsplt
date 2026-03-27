"""
Invoice, receipt, credit/debit note (PDF path, email, duplicate copy).
"""
from sqlalchemy import Column, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database_types import UUID_TYPE
from app.models.base import TenantBaseModel


class FinancialDocument(TenantBaseModel):
    """Generated document (invoice, receipt, credit note, debit note)."""
    __tablename__ = "financial_documents"

    bill_id = Column(UUID_TYPE, ForeignKey("bills.id"), nullable=True)
    payment_id = Column(UUID_TYPE, ForeignKey("payments.id"), nullable=True)
    doc_type = Column(String(20), nullable=False)  # INVOICE, RECEIPT, CREDIT_NOTE, DEBIT_NOTE
    doc_number = Column(String(50), nullable=False)
    pdf_path = Column(String(500), nullable=True)  # or storage_key
    emailed_to = Column(String(255), nullable=True)
    template_version = Column(String(50), nullable=True)
    is_duplicate_copy = Column(Boolean, nullable=False, default=False)

    # Relationships
    bill = relationship("Bill", back_populates="financial_documents")
    payment = relationship("BillingPayment", back_populates="financial_documents")

    def __repr__(self):
        return f"<FinancialDocument(id={self.id}, doc_type='{self.doc_type}', doc_number='{self.doc_number}')>"
