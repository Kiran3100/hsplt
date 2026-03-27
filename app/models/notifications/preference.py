"""
Notification preferences per owner (patient/staff). Quiet hours, channel toggles.
"""
from sqlalchemy import Column, String, ForeignKey, Boolean, Time
from app.core.database_types import UUID_TYPE
from app.models.base import TenantBaseModel


class NotificationPreference(TenantBaseModel):
    __tablename__ = "notification_preferences"

    owner_type = Column(String(20), nullable=False)  # PATIENT, STAFF
    owner_id = Column(UUID_TYPE, nullable=False, index=True)
    email_enabled = Column(Boolean, nullable=False, default=True)
    sms_enabled = Column(Boolean, nullable=False, default=True)
    whatsapp_enabled = Column(Boolean, nullable=False, default=False)
    quiet_hours_start = Column(Time, nullable=True)
    quiet_hours_end = Column(Time, nullable=True)

    def __repr__(self):
        return f"<NotificationPreference(id={self.id}, owner_type='{self.owner_type}', owner_id={self.owner_id})>"
