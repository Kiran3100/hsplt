"""
Password history model for tracking password changes and preventing reuse.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from app.core.database_types import UUID_TYPE
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database.base import Base


class PasswordHistory(Base):
    """
    Track password history to prevent reuse of recent passwords.
    Stores hashed passwords for security.
    """
    __tablename__ = "password_history"
    
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<PasswordHistory(id={self.id}, user_id={self.user_id}, created_at={self.created_at})>"