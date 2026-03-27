"""
Support ticket model for Super Admin helpdesk and escalations.
"""
from sqlalchemy import Column, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database_types import UUID_TYPE
from app.models.base import TenantBaseModel


class SupportTicket(TenantBaseModel):
    """
    Support tickets raised by hospital staff, escalated to Super Admin.
    """
    __tablename__ = "support_tickets"

    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    raised_by_user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="OPEN")  # OPEN, IN_PROGRESS, ESCALATED, RESOLVED, CLOSED
    priority = Column(String(20), default="NORMAL")  # LOW, NORMAL, HIGH, URGENT
    assigned_to_user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)  # Super Admin when escalated
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    hospital = relationship("Hospital", backref="support_tickets")
    raised_by = relationship("User", foreign_keys=[raised_by_user_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])

    def __repr__(self):
        return f"<SupportTicket(id={self.id}, subject='{self.subject[:30]}', status='{self.status}')>"
