"""
Authentication schemas for login, registration, and user management.
"""
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# INPUT SCHEMAS (Create/Update/Filter)
# ============================================================================

class LoginCreate(BaseModel):
    """Universal login request"""
    email: EmailStr
    password: str


class PasswordChangeUpdate(BaseModel):
    """Change password request"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class HospitalCreate(BaseModel):
    """Hospital creation by Super Admin"""
    name: str = Field(..., min_length=2, max_length=255)
    registration_number: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., pattern=r'^\+?[\d\s\-\(\)]{10,20}$')
    address: str = Field(..., min_length=5)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    country: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(..., min_length=3, max_length=10)


class HospitalAdminCreate(BaseModel):
    """Hospital admin creation by Super Admin"""
    email: EmailStr
    phone: str = Field(..., pattern=r'^\+?[\d\s\-\(\)]{10,20}$')
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8, max_length=128, description="Password must be at least 8 characters with uppercase, lowercase, number, and special character")


class PatientRegistrationCreate(BaseModel):
    """Patient self-registration"""
    email: EmailStr
    phone: str = Field(..., pattern=r'^\+?[\d\s\-\(\)]{10,20}$')
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    # Optional for UX: if omitted, hospital will be auto-resolved when possible
    hospital_name: Optional[str] = Field(
        None,
        description="Hospital name where patient wants to register (optional if only one hospital is active)"
    )
    
    # Patient profile fields
    date_of_birth: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")
    gender: Optional[str] = Field(None, description="Gender (Male/Female/Other)")
    address: Optional[str] = Field(None, description="Address")
    emergency_contact_name: Optional[str] = Field(None, description="Emergency contact name")
    emergency_contact_phone: Optional[str] = Field(None, pattern=r'^\+?[\d\s\-\(\)]{10,20}$', description="Emergency contact phone")


class OTPVerificationCreate(BaseModel):
    """OTP verification for patients"""
    email: EmailStr
    otp_code: str = Field(..., pattern=r'^\d{6}$')


class ForgotPasswordCreate(BaseModel):
    """Forgot password request"""
    email: EmailStr


class PasswordResetCreate(BaseModel):
    """Password reset with OTP"""
    email: EmailStr
    otp_code: str = Field(..., pattern=r'^\d{6}$')
    new_password: str = Field(..., min_length=8, max_length=128)


# ============================================================================
# OUTPUT SCHEMAS (Out/Response)
# ============================================================================

class AuthOut(BaseModel):
    """Authentication response data"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class HospitalAdminOut(BaseModel):
    """Hospital admin creation response data"""
    user_id: str
    email: str


class UserInfoOut(BaseModel):
    """User information response data"""
    id: str
    email: str
    first_name: str
    last_name: str
    phone: str
    status: str
    email_verified: bool
    hospital_id: Optional[str]
    roles: List[str]
    permissions: List[str]
    last_login: Optional[str]
    created_at: str


class HospitalOut(BaseModel):
    """Hospital information data"""
    name: str
    city: str
    state: str
    phone: str
    email: str
    address: str
    full_address: str


# ============================================================================
# LEGACY SCHEMAS (to be phased out)
# ============================================================================

class MessageResponse(BaseModel):
    """Legacy message response - to be replaced"""
    message: str
    status: Optional[str] = None


class AuthResponse(BaseModel):
    """Legacy auth response - to be replaced"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class HospitalAdminResponse(BaseModel):
    """Legacy hospital admin creation response - to be replaced"""
    user_id: str
    email: str
    message: str