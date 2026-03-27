"""
Base model with common fields and multi-tenant support.
All business models must inherit from TenantBaseModel to ensure hospital isolation.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Boolean
from app.core.database_types import UUID_TYPE
from sqlalchemy.sql import func
from datetime import datetime
import uuid

# Import the single declarative base
from app.database.base import Base


class BaseModel(Base):
    """Base model with common audit fields"""
    __abstract__ = True
    
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class TenantBaseModel(BaseModel):
    """
    Base model for all multi-tenant entities.
    CRITICAL: Every business table must inherit from this to ensure hospital isolation.
    """
    __abstract__ = True
    
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id}, hospital_id={self.hospital_id})>"



class TimestampMixin:
    """Mixin for timestamp fields"""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
