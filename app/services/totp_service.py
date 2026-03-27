"""
TOTP (Time-based One-Time Password) service for 2FA.

Implements RFC 6238 using the pyotp library.
This fixes the SOW requirement for 2FA (previously only email OTP was used
for registration flows — not true 2FA for login).

Required package: pip install pyotp qrcode[pil]
"""
import logging
import base64
import secrets
from typing import Optional, Dict, Any
from io import BytesIO

try:
    import pyotp
    PYOTP_AVAILABLE = True
except ImportError:
    PYOTP_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "pyotp not installed. Run: pip install pyotp qrcode[pil] "
        "2FA will not work until this is installed."
    )

logger = logging.getLogger(__name__)

TOTP_ISSUER = "HospitalManagementSaaS"
TOTP_DIGITS = 6
TOTP_INTERVAL = 30  # seconds


class TOTPService:
    """TOTP 2FA service for hospital staff."""

    def generate_secret(self) -> str:
        """
        Generate a new TOTP secret for a user.
        Store this encrypted in users.totp_secret.
        """
        if not PYOTP_AVAILABLE:
            raise RuntimeError("pyotp not installed. Run: pip install pyotp")
        return pyotp.random_base32()

    def get_provisioning_uri(self, secret: str, user_email: str, hospital_name: str) -> str:
        """
        Generate the otpauth:// URI that gets embedded in the QR code.
        Users scan this with Google Authenticator / Authy.
        """
        if not PYOTP_AVAILABLE:
            raise RuntimeError("pyotp not installed")
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=user_email,
            issuer_name=f"{TOTP_ISSUER} - {hospital_name}"
        )

    def get_qr_code_base64(self, provisioning_uri: str) -> Optional[str]:
        """
        Generate a base64-encoded PNG QR code from the provisioning URI.
        Returns None if qrcode library is not installed.
        """
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except ImportError:
            logger.warning("qrcode not installed — QR code generation unavailable")
            return None

    def verify_totp(self, secret: str, code: str) -> bool:
        """
        Verify a TOTP code submitted by the user.
        Allows 1 window drift (±30s) to account for clock skew.
        """
        if not PYOTP_AVAILABLE:
            logger.error("pyotp not installed — all TOTP verifications will FAIL")
            return False
        if not secret or not code:
            return False
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=1)
        except Exception as e:
            logger.error(f"TOTP verification error: {e}")
            return False

    def get_current_code(self, secret: str) -> str:
        """For testing only — get current TOTP code."""
        if not PYOTP_AVAILABLE:
            raise RuntimeError("pyotp not installed")
        return pyotp.TOTP(secret).now()
