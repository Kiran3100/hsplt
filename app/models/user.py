"""
User and access control models.
Supports unified user management with role-based access control.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Table
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from app.models.base import BaseModel, TenantBaseModel
from app.core.enums import UserRole, UserStatus, AuditAction
from app.core.database_types import JSON_TYPE, UUID_TYPE


# Association table for many-to-many relationship between users and roles
user_roles = Table(
    'user_roles',
    BaseModel.metadata,
    Column('user_id', UUID_TYPE, ForeignKey('users.id'), primary_key=True),
    Column('role_id', UUID_TYPE, ForeignKey('roles.id'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), server_default=func.now()),
    Column('assigned_by', UUID_TYPE, ForeignKey('users.id'))
)

# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    'role_permissions',
    BaseModel.metadata,
    Column('role_id', UUID_TYPE, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', UUID_TYPE, ForeignKey('permissions.id'), primary_key=True),
    Column('granted_at', DateTime(timezone=True), server_default=func.now()),
    Column('granted_by', UUID_TYPE, ForeignKey('users.id'))
)


class User(TenantBaseModel):
    """
    Unified user model for all user types in the system.
    Supports Admin, Doctor, Patient, Pharmacist, Lab Tech through roles.
    """
    __tablename__ = "users"
    
    # Override hospital_id to make it nullable for super admins
    hospital_id = Column(UUID_TYPE, ForeignKey("hospitals.id"), nullable=True, index=True)
    
    # Basic information
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Personal details
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    middle_name = Column(String(100))
    
    # Staff identification (for hospital staff only)
    staff_id = Column(String(10), unique=True, index=True)  # e.g., DRCARDJS01
    
    # Account status
    status = Column(String(20), nullable=False, default=UserStatus.PENDING)
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    
    # Security
    last_login = Column(DateTime(timezone=True))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True))
    password_changed_at = Column(DateTime(timezone=True))
    
    # Profile
    avatar_url = Column(String(500))
    timezone = Column(String(50), default='UTC')
    language = Column(String(10), default='en')
    
    # User metadata
    user_metadata = Column(JSON_TYPE, nullable=False, default=lambda: {})
    
    # Relationships (minimal for authentication to work)
    roles = relationship(
        "Role", 
        secondary=user_roles, 
        back_populates="users",
        primaryjoin="User.id == user_roles.c.user_id",
        secondaryjoin="Role.id == user_roles.c.role_id",
        lazy="select"
    )
    
    # Note: Other relationships temporarily removed to avoid import issues
    # These can be added back once all models are properly organized
    
    @validates('hospital_id')
    def validate_hospital_id_for_role(self, key, value):
        """Validate that hospital_id is required for non-super-admin roles."""
        # Allow None for super admin users
        if value is None:
            # Check if any role is SUPER_ADMIN
            if hasattr(self, 'roles') and self.roles:
                for role in self.roles:
                    if role.name == UserRole.SUPER_ADMIN.value:
                        return value
            # If no roles yet, allow None (will be validated later when roles are assigned)
            return value
        return value
    
    @property
    def is_super_admin(self) -> bool:
        """Check if user is a super admin."""
        if hasattr(self, 'roles') and self.roles:
            return any(role.name == UserRole.SUPER_ADMIN.value for role in self.roles)
        return False
    
    @property
    def is_global_user(self) -> bool:
        """Check if user is global (not tied to a specific hospital)."""
        return self.hospital_id is None
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', hospital_id={self.hospital_id})>"


class Role(BaseModel):
    """
    Role definitions for RBAC system.
    Maps to UserRole enum values.
    """
    __tablename__ = "roles"
    
    name = Column(String(50), nullable=False, unique=True)  # Maps to UserRole enum
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Role metadata
    is_system_role = Column(Boolean, default=True)  # System vs custom roles
    level = Column(Integer, default=0)  # Role hierarchy level
    
    # Relationships
    users = relationship(
        "User", 
        secondary=user_roles, 
        back_populates="roles",
        primaryjoin="Role.id == user_roles.c.role_id",
        secondaryjoin="User.id == user_roles.c.user_id"
    )
    permissions = relationship(
        "Permission", 
        secondary=role_permissions, 
        back_populates="roles",
        primaryjoin="Role.id == role_permissions.c.role_id",
        secondaryjoin="Permission.id == role_permissions.c.permission_id"
    )
    
    def __repr__(self):
        return f"<Role(name='{self.name}', display_name='{self.display_name}')>"


class Permission(BaseModel):
    """
    Granular permissions for fine-grained access control.
    Supports resource-based and action-based permissions.
    """
    __tablename__ = "permissions"
    
    name = Column(String(100), nullable=False, unique=True)  # e.g., "patient.create"
    resource = Column(String(50), nullable=False)  # e.g., "patient"
    action = Column(String(50), nullable=False)  # e.g., "create", "read", "update", "delete"
    description = Column(Text)
    
    # Permission metadata
    is_system_permission = Column(Boolean, default=True)
    
    # Relationships
    roles = relationship(
        "Role", 
        secondary=role_permissions, 
        back_populates="permissions",
        primaryjoin="Permission.id == role_permissions.c.permission_id",
        secondaryjoin="Role.id == role_permissions.c.role_id"
    )
    
    def __repr__(self):
        return f"<Permission(name='{self.name}', resource='{self.resource}', action='{self.action}')>"


class AuditLog(TenantBaseModel):
    """
    Comprehensive audit logging for HIPAA and NDHM compliance.
    Records all sensitive operations in the system.
    """
    __tablename__ = "audit_logs"
    
    # Who performed the action
    user_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    
    # What action was performed
    action = Column(String(20), nullable=False)  # Maps to AuditAction enum
    resource_type = Column(String(50), nullable=False)  # e.g., "Patient", "Appointment"
    resource_id = Column(Integer)  # ID of the affected resource
    
    # Action details
    description = Column(Text, nullable=False)
    old_values = Column(JSON_TYPE)  # Previous state for updates
    new_values = Column(JSON_TYPE)  # New state for creates/updates
    
    # Context
    ip_address = Column(String(45))  # IPv4/IPv6
    user_agent = Column(Text)
    session_id = Column(String(255))
    
    # Compliance metadata
    is_sensitive = Column(Boolean, default=False)  # PHI/PII involved
    retention_date = Column(DateTime(timezone=True))  # When this log can be purged
    
    # Relationships
    user = relationship("User")  # Removed back_populates to avoid circular reference
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', resource='{self.resource_type}')>"