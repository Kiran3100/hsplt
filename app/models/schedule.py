"""
Doctor Schedule Management Models
Manages doctor availability schedules with the unified user model.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, Time
from sqlalchemy.orm import relationship
from app.core.database_types import UUID_TYPE
from app.models.base import TenantBaseModel


class DoctorSchedule(TenantBaseModel):
    """
    Doctor availability schedules.
    Works with the unified user model - references users.id directly.
    """
    __tablename__ = "doctor_schedules"
    
    # Reference to the doctor user directly
    doctor_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    
    # Schedule details
    day_of_week = Column(String(10), nullable=False)  # MONDAY, TUESDAY, etc.
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    
    # Schedule metadata
    is_active = Column(Boolean, default=True)
    slot_duration_minutes = Column(Integer, default=30)  # Default appointment duration
    max_patients_per_slot = Column(Integer, default=1)
    
    # Break times
    break_start_time = Column(Time)
    break_end_time = Column(Time)
    
    # Additional settings
    notes = Column(Text)
    is_emergency_available = Column(Boolean, default=False)
    
    # Effective dates (optional)
    effective_from = Column(String(10))  # YYYY-MM-DD
    effective_to = Column(String(10))    # YYYY-MM-DD
    
    # Relationships
    doctor = relationship("User", foreign_keys=[doctor_id])
    
    def __repr__(self):
        return f"<DoctorSchedule(id={self.id}, day='{self.day_of_week}', time='{self.start_time}-{self.end_time}')>"