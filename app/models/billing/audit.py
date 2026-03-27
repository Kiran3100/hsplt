"""
Audit trail for financial transactions (modification logs, discount approval, refund audit).
"""
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database_types import UUID_TYPE, JSON_TYPE
from app.models.base import TenantBaseModel


class FinanceAuditLog(TenantBaseModel):
    """Audit log for billing/payment/claim/document actions."""
    __tablename__ = "finance_audit_logs"

    entity_type = Column(String(20), nullable=False)  # BILL, PAYMENT, CLAIM, DOC
    entity_id = Column(UUID_TYPE, nullable=False)
    action = Column(String(30), nullable=False)  # CREATE, UPDATE, FINALIZE, CANCEL, DISCOUNT_APPLY, REFUND, APPROVE, REJECT
    old_value = Column(JSON_TYPE, nullable=True)
    new_value = Column(JSON_TYPE, nullable=True)
    performed_by_user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    performed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(String(45), nullable=True)

    # Relationships
    performed_by_user = relationship("User")

    def __repr__(self):
        return f"<FinanceAuditLog(id={self.id}, entity_type='{self.entity_type}', action='{self.action}')>"
