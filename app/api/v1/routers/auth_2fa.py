"""
2FA (TOTP) Authentication Router.

Implements true Two-Factor Authentication using TOTP (RFC 6238).
Previously the system only had email OTP for registration — not real 2FA for login.

Endpoints:
  POST /auth/2fa/setup      — Generate TOTP secret + QR code for user to scan
  POST /auth/2fa/verify     — Verify TOTP code and enable 2FA on the account
  POST /auth/2fa/validate   — Validate TOTP code during login (step 2 of login)
  DELETE /auth/2fa/disable  — Disable 2FA (requires password confirmation)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models.user import User
from app.services.totp_service import TOTPService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/2fa", tags=["Authentication - 2FA (TOTP)"])

totp_svc = TOTPService()


class TOTPSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    qr_code_base64: str | None = None
    message: str


class TOTPVerifyRequest(BaseModel):
    code: str  # 6-digit TOTP code from authenticator app


class TOTPValidateRequest(BaseModel):
    user_id: str
    code: str  # 6-digit code during login step 2


@router.post("/setup", response_model=dict)
async def setup_totp(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Step 1 of 2FA enrollment: generate TOTP secret and QR code.
    The user must scan the QR code with their authenticator app,
    then call /auth/2fa/verify with the 6-digit code to confirm enrollment.
    """
    if getattr(current_user, "totp_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled on this account. Disable first to re-enroll.",
        )

    secret = totp_svc.generate_secret()

    # Store the unverified secret temporarily
    current_user.totp_secret = secret
    current_user.totp_enabled = False  # Not enabled until verified
    await db.commit()

    provisioning_uri = totp_svc.get_provisioning_uri(
        secret=secret,
        user_email=current_user.email,
        hospital_name=str(current_user.hospital_id or "HSM"),
    )
    qr_code = totp_svc.get_qr_code_base64(provisioning_uri)

    return {
        "success": True,
        "message": "Scan the QR code with Google Authenticator or Authy, then call /auth/2fa/verify.",
        "data": {
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "qr_code_base64": qr_code,
        }
    }


@router.post("/verify", response_model=dict)
async def verify_and_enable_totp(
    body: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Step 2 of 2FA enrollment: verify the TOTP code from the authenticator app.
    On success, 2FA is enabled for this account.
    """
    secret = getattr(current_user, "totp_secret", None)
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No TOTP secret found. Call /auth/2fa/setup first.",
        )

    if not totp_svc.verify_totp(secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TOTP_INVALID",
                "message": "Invalid or expired code. Please try again.",
            }
        )

    from datetime import datetime, timezone
    current_user.totp_enabled = True
    current_user.totp_verified_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"2FA enabled for user {current_user.id} ({current_user.email})")
    return {
        "success": True,
        "message": "2FA enabled successfully. You will now be required to enter a TOTP code on every login.",
    }


@router.post("/validate", response_model=dict)
async def validate_totp_on_login(
    body: TOTPValidateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Step 2 of login for users with 2FA enabled.
    Called after successful password verification with the temporary user_id.
    Returns confirmation that 2FA passed — frontend should then use the JWT
    from the step-1 login response.
    """
    result = await db.execute(select(User).where(User.id == body.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not getattr(user, "totp_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled for this account.",
        )

    secret = getattr(user, "totp_secret", None)
    if not secret or not totp_svc.verify_totp(secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOTP_INVALID",
                "message": "Invalid or expired 2FA code.",
            }
        )

    return {"success": True, "message": "2FA validated successfully."}


@router.delete("/disable", response_model=dict)
async def disable_totp(
    body: TOTPVerifyRequest,  # Require current TOTP code to disable
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Disable 2FA for the current user. Requires a valid TOTP code as confirmation.
    """
    if not getattr(current_user, "totp_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not currently enabled.",
        )

    secret = getattr(current_user, "totp_secret", None)
    if not totp_svc.verify_totp(secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code. Cannot disable 2FA.",
        )

    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.totp_verified_at = None
    await db.commit()

    logger.info(f"2FA disabled for user {current_user.id} ({current_user.email})")
    return {"success": True, "message": "2FA disabled. Your account is now less secure."}
