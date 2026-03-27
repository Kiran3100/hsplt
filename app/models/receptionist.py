"""
Receptionist profile models.
Manages receptionist profiles, OPD assignments, and front desk operations.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.core.database_types import JSON_TYPE, UUID_TYPE
from app.models.base import TenantBaseModel


class ReceptionistProfile(TenantBaseModel):
    """
    Extended profile for receptionists.
    Links to User model for authentication and basic info.
    Handles OPD (Outpatient Department) operations.
    """
    __tablename__ = "receptionist_profiles"
    
    user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False, unique=True)
    department_id = Column(UUID_TYPE, ForeignKey("departments.id"), nullable=False)
    
    # Professional identification
    receptionist_id = Column(String(50), nullable=False)  # Hospital-specific receptionist ID
    employee_id = Column(String(100), nullable=False, unique=True)
    
    # Professional details
    designation = Column(String(100), nullable=False)  # "Front Desk Receptionist", "OPD Coordinator", "Senior Receptionist"
    work_area = Column(String(100), default="OPD")  # "OPD", "EMERGENCY", "GENERAL"
    
    # Experience and qualifications
    experience_years = Column(Integer, default=0)
    qualifications = Column(JSON_TYPE, default=[])  # ["High School", "Diploma", "Certificate"]
    
    # Work details
    shift_type = Column(String(20), default="DAY")  # "DAY", "NIGHT", "ROTATING"
    employment_type = Column(String(20), default="FULL_TIME")  # "FULL_TIME", "PART_TIME", "CONTRACT"
    
    # Skills and competencies
    computer_skills = Column(JSON_TYPE, default=[])  # ["MS_OFFICE", "HOSPITAL_SOFTWARE", "DATA_ENTRY"]
    languages_spoken = Column(JSON_TYPE, default=["English"])
    
    # Permissions and access
    can_schedule_appointments = Column(Boolean, default=True)
    can_modify_appointments = Column(Boolean, default=True)
    can_register_patients = Column(Boolean, default=True)
    can_collect_payments = Column(Boolean, default=False)  # Usually separate cashier role
    
    # Profile information
    bio = Column(Text)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User")
    department = relationship("Department")
    
    def __repr__(self):
        return f"<ReceptionistProfile(id={self.id}, receptionist_id='{self.receptionist_id}', hospital_id={self.hospital_id})>"