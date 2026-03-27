"""
Delivery log per send attempt (SENT, DELIVERED, BOUNCED, FAILED).
"""
from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database_types import UUID_TYPE, JSON_TYPE
from app.models.base import BaseModel


class NotificationDeliveryLog(BaseModel):
    __tablename__ = "notification_delivery_logs"

    job_id = Column(UUID_TYPE, ForeignKey("notification_jobs.id"), nullable=False, index=True)
    provider = Column(String(30), nullable=True)
    status = Column(String(20), nullable=False)
    raw_response = Column(JSON_TYPE, nullable=True)

    job = relationship("NotificationJob", back_populates="delivery_logs")

    def __repr__(self):
        return f"<NotificationDeliveryLog(id={self.id}, job_id={self.job_id}, status='{self.status}')>"
