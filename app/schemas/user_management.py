from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserManagementCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    role_id: str
    department_id: str
    status: str = Field(default="ACTIVE")
    profile_image: Optional[str] = None
    joined_date: Optional[str] = None
    hospital_id: Optional[str] = None  # required only for Super Admin

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str):
        value = v.upper()
        if value not in {"ACTIVE", "INACTIVE"}:
            raise ValueError("status must be ACTIVE or INACTIVE")
        return value


class UserManagementUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    role_id: Optional[str] = None
    department_id: Optional[str] = None
    status: Optional[str] = None
    profile_image: Optional[str] = None
    joined_date: Optional[str] = None
    hospital_id: Optional[str] = None  # optional, for Super Admin context

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]):
        if v is None:
            return v
        value = v.upper()
        if value not in {"ACTIVE", "INACTIVE"}:
            raise ValueError("status must be ACTIVE or INACTIVE")
        return value


class UserStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str):
        value = v.upper()
        if value not in {"ACTIVE", "INACTIVE"}:
            raise ValueError("status must be ACTIVE or INACTIVE")
        return value


class UserManagementOut(BaseModel):
    id: str
    full_name: str
    email: str
    phone: str
    role_id: str
    role_name: str
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    status: str
    profile_image: Optional[str] = None
    joined_date: Optional[str] = None
    last_login: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RoleOut(BaseModel):
    id: str
    name: str
    display_name: str


class DepartmentOut(BaseModel):
    id: str
    name: str
    code: Optional[str] = None


class DashboardStatsOut(BaseModel):
    total_admins: int
    total_doctors: int
    total_staff: int
    total_patients: int
    total_users: int