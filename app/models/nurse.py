"""
Nurse profile models.
Manages nurse profiles, department assignments, and nursing credentials.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.core.database_types import JSON_TYPE, UUID_TYPE
from app.models.base import TenantBaseModel


class NurseProfile(TenantBaseModel):
    """
    Extended profile for nurses.
    Links to User model for authentication and basic info.
    """
    __tablename__ = "nurse_profiles"
    
    user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False, unique=True)
    department_id = Column(UUID_TYPE, ForeignKey("departments.id"), nullable=False)
    
    # Professional identification
    nurse_id = Column(String(50), nullable=False)  # Hospital-specific nurse ID
    nursing_license_number = Column(String(100), nullable=False, unique=True)
    
    # Professional details
    designation = Column(String(100), nullable=False)  # "Staff Nurse", "Senior Nurse", "Charge Nurse"
    specialization = Column(String(255))  # "ICU", "Emergency", "Pediatric", "Surgical"
    
    # Experience and qualifications
    experience_years = Column(Integer, default=0)
    qualifications = Column(JSON_TYPE, default=[])  # ["BSN", "MSN", "RN"]
    certifications = Column(JSON_TYPE, default=[])  # ["BLS", "ACLS", "PALS"]
    
    # Work details
    shift_type = Column(String(20), default="DAY")  # "DAY", "NIGHT", "ROTATING"
    employment_type = Column(String(20), default="FULL_TIME")  # "FULL_TIME", "PART_TIME", "CONTRACT"
    
    # Skills and competencies
    clinical_skills = Column(JSON_TYPE, default=[])  # ["IV_INSERTION", "WOUND_CARE", "MEDICATION_ADMIN"]
    languages_spoken = Column(JSON_TYPE, default=["English"])
    
    # Profile information
    bio = Column(Text)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User")
    department = relationship("Department")
    
    def __repr__(self):
        return f"<NurseProfile(id={self.id}, nurse_id='{self.nurse_id}', hospital_id={self.hospital_id})>"