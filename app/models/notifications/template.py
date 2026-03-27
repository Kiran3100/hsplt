"""
Notification template (email/sms). hospital_id nullable for global.
"""
from sqlalchemy import Column, String, ForeignKey, Boolean, Text, UniqueConstraint
from app.core.database_types import UUID_TYPE
from app.models.base import BaseModel


class NotificationTemplate(BaseModel):
    __tablename__ = "notification_templates"
    __table_args__ = (UniqueConstraint("hospital_id", "template_key", name="uq_notification_templates_hospital_template_key"),)

    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=True, index=True)
    channel = Column(String(20), nullable=False)  # EMAIL, SMS
    template_key = Column(String(80), nullable=False)
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<NotificationTemplate(id={self.id}, template_key='{self.template_key}', channel='{self.channel}')>"
