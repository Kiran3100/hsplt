"""
Notification job (outbox). QUEUED -> PROCESSING -> SENT/FAILED. Idempotency via idempotency_key.
"""
from sqlalchemy import Column, String, ForeignKey, Text, Integer, DateTime
from sqlalchemy.orm import relationship
from app.core.database_types import UUID_TYPE, JSON_TYPE
from app.models.base import TenantBaseModel


class NotificationJob(TenantBaseModel):
    __tablename__ = "notification_jobs"

    event_type = Column(String(60), nullable=False, index=True)
    channel = Column(String(20), nullable=False)
    to_address = Column(String(255), nullable=False)
    template_id = Column(UUID_TYPE, ForeignKey("notification_templates.id"), nullable=True)
    payload_ = Column("payload", JSON_TYPE, nullable=True)
    subject_rendered = Column(String(255), nullable=True)
    message_rendered = Column(Text, nullable=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="QUEUED", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    last_error = Column(Text, nullable=True)
    provider_message_id = Column(String(255), nullable=True)
    idempotency_key = Column(String(120), nullable=False, unique=True, index=True)
    created_by_user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)

    delivery_logs = relationship("NotificationDeliveryLog", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<NotificationJob(id={self.id}, event_type='{self.event_type}', status='{self.status}')>"
