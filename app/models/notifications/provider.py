"""
Notification provider config (email/sms). hospital_id nullable for global defaults.
"""
from sqlalchemy import Column, String, ForeignKey, Boolean
from app.core.database_types import UUID_TYPE, JSON_TYPE
from app.models.base import BaseModel
from app.database.base import Base


class NotificationProvider(BaseModel):
    __tablename__ = "notification_providers"

    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=True, index=True)
    provider_type = Column(String(20), nullable=False)  # EMAIL, SMS
    provider_name = Column(String(30), nullable=False)  # SENDGRID, AWS_SES, TWILIO, MSG91, AWS_SNS
    is_enabled = Column(Boolean, nullable=False, default=True)
    config_ = Column("config", JSON_TYPE, nullable=True)  # encrypted secrets recommended

    def __repr__(self):
        return f"<NotificationProvider(id={self.id}, provider_name='{self.provider_name}', type='{self.provider_type}')>"
