"""
Schemas for user and access control models.
"""
from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.schemas.base import BaseSchema, TenantBaseSchema, TimestampMixin
from app.core.enums import UserRole, UserStatus, AuditAction


# User Schemas
class UserBase(BaseModel):
    """Base user fields"""
    email: EmailStr
    phone: str = Field(..., pattern=r'^\+?[\d\s\-\(\)]{10,20}$')
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    
    # Optional profile fields
    avatar_url: Optional[str] = Field(None, max_length=500)
    timezone: str = Field("UTC", max_length=50)
    language: str = Field("en", max_length=10)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class UserCreate(UserBase):
    """Schema for creating a user"""
    password: str = Field(..., min_length=8, max_length=128)
    hospital_id: int
    roles: List[UserRole] = Field(..., min_items=1)
    
    @validator('password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    phone: Optional[str] = Field(None, pattern=r'^\+?[\d\s\-\(\)]{10,20}$')
    first_name: Optional[str] = Field(None, min_length=2, max_length=100)
    last_name: Optional[str] = Field(None, min_length=2, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    metadata: Optional[Dict[str, Any]] = None


class UserPasswordUpdate(BaseModel):
    """Schema for password updates"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserResponse(UserBase, TenantBaseSchema, TimestampMixin):
    """Schema for user API responses"""
    id: int
    status: UserStatus
    email_verified: bool
    phone_verified: bool
    last_login: Optional[datetime]
    
    # Role information
    roles: List[str]
    permissions: List[str]


class UserList(BaseModel):
    """Schema for user list items"""
    id: int
    email: str
    first_name: str
    last_name: str
    status: UserStatus
    roles: List[str]
    last_login: Optional[datetime]
    created_at: datetime


# Authentication Schemas
class LoginRequest(BaseModel):
    """Schema for login requests"""
    email: EmailStr
    password: str
    hospital_id: Optional[int] = None  # For multi-hospital users


class LoginResponse(BaseModel):
    """Schema for login responses"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh requests"""
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password requests"""
    email: EmailStr
    hospital_id: Optional[int] = None


class ResetPasswordRequest(BaseModel):
    """Schema for password reset requests"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


# Role Schemas
class RoleBase(BaseModel):
    """Base role fields"""
    name: UserRole
    display_name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    level: int = Field(0, ge=0)


class RoleCreate(RoleBase):
    """Schema for creating a role"""
    permissions: List[int] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """Schema for updating a role"""
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    level: Optional[int] = Field(None, ge=0)


class RoleResponse(RoleBase, BaseSchema, TimestampMixin):
    """Schema for role API responses"""
    id: int
    is_system_role: bool
    permissions: List[str]


# Permission Schemas
class PermissionBase(BaseModel):
    """Base permission fields"""
    name: str = Field(..., min_length=3, max_length=100)
    resource: str = Field(..., min_length=2, max_length=50)
    action: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None


class PermissionCreate(PermissionBase):
    """Schema for creating a permission"""
    pass


class PermissionUpdate(BaseModel):
    """Schema for updating a permission"""
    description: Optional[str] = None


class PermissionResponse(PermissionBase, BaseSchema, TimestampMixin):
    """Schema for permission API responses"""
    id: int
    is_system_permission: bool


# Audit Log Schemas
class AuditLogResponse(TenantBaseSchema, TimestampMixin):
    """Schema for audit log API responses"""
    id: int
    user_id: int
    action: AuditAction
    resource_type: str
    resource_id: Optional[int]
    description: str
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    is_sensitive: bool
    
    # User information
    user_email: Optional[str]
    user_name: Optional[str]


class AuditLogFilter(BaseModel):
    """Schema for audit log filtering"""
    user_id: Optional[int] = None
    action: Optional[AuditAction] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    is_sensitive: Optional[bool] = None
    date_from: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    date_to: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')