"""
OTP (One-Time Password) service for email verification and password reset.
"""
import secrets
import redis.asyncio as redis
from datetime import datetime, timedelta
from typing import Optional
import json
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class OTPService:
    """Service for generating and verifying OTP codes"""
    
    def __init__(self):
        # In production, use Redis for OTP storage
        # For now, use in-memory storage (not suitable for production)
        self._otp_storage = {}
        self.otp_expiry_minutes = 10
        self.max_attempts = 3
    
    def _generate_otp_code(self) -> str:
        """Generate 6-digit OTP code"""
        return f"{secrets.randbelow(1000000):06d}"
    
    def _get_otp_key(self, identifier: str, purpose: str) -> str:
        """Generate Redis key for OTP storage"""
        return f"otp:{purpose}:{identifier}"
    
    async def generate_otp(self, identifier: str, purpose: str) -> str:
        """
        Generate OTP for given identifier and purpose.
        
        Args:
            identifier: Email or phone number
            purpose: 'email_verification' or 'password_reset'
        
        Returns:
            6-digit OTP code
        """
        otp_code = self._generate_otp_code()
        expiry_time = datetime.utcnow() + timedelta(minutes=self.otp_expiry_minutes)
        
        # Store OTP with metadata
        otp_data = {
            "code": otp_code,
            "purpose": purpose,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expiry_time.isoformat(),
            "attempts": 0,
            "max_attempts": self.max_attempts
        }
        
        # Store in memory (in production, use Redis)
        key = self._get_otp_key(identifier, purpose)
        self._otp_storage[key] = otp_data
        
        logger.info(f"OTP generated for {identifier} with purpose {purpose}")
        return otp_code
    
    async def verify_otp(self, identifier: str, otp_code: str, purpose: str) -> bool:
        """
        Verify OTP code for given identifier and purpose.
        
        Args:
            identifier: Email or phone number
            otp_code: 6-digit OTP code to verify
            purpose: 'email_verification' or 'password_reset'
        
        Returns:
            True if OTP is valid, False otherwise
        """
        key = self._get_otp_key(identifier, purpose)
        print(f"DEBUG OTP: Looking for key: {key}")
        print(f"DEBUG OTP: Available keys: {list(self._otp_storage.keys())}")
        
        otp_data = self._otp_storage.get(key)
        print(f"DEBUG OTP: Found OTP data: {otp_data}")
        
        if not otp_data:
            logger.warning(f"OTP not found for {identifier} with purpose {purpose}")
            return False
        
        # Check if OTP has expired
        expires_at = datetime.fromisoformat(otp_data["expires_at"])
        current_time = datetime.utcnow()
        print(f"DEBUG OTP: Current time: {current_time}, Expires at: {expires_at}")
        
        if current_time > expires_at:
            logger.warning(f"OTP expired for {identifier}")
            # Clean up expired OTP
            del self._otp_storage[key]
            return False
        
        # Check attempts
        print(f"DEBUG OTP: Attempts: {otp_data['attempts']}, Max: {otp_data['max_attempts']}")
        if otp_data["attempts"] >= otp_data["max_attempts"]:
            logger.warning(f"Max OTP attempts exceeded for {identifier}")
            # Clean up after max attempts
            del self._otp_storage[key]
            return False
        
        # Increment attempts
        otp_data["attempts"] += 1
        
        # Verify code
        print(f"DEBUG OTP: Comparing '{otp_data['code']}' with '{otp_code}'")
        if otp_data["code"] == otp_code:
            logger.info(f"OTP verified successfully for {identifier}")
            # Clean up successful OTP
            del self._otp_storage[key]
            return True
        else:
            logger.warning(f"Invalid OTP code for {identifier}")
            # Update attempts in storage
            self._otp_storage[key] = otp_data
            return False
    
    async def invalidate_otp(self, identifier: str, purpose: str) -> bool:
        """
        Invalidate OTP for given identifier and purpose.
        
        Args:
            identifier: Email or phone number
            purpose: 'email_verification' or 'password_reset'
        
        Returns:
            True if OTP was found and invalidated, False otherwise
        """
        key = self._get_otp_key(identifier, purpose)
        if key in self._otp_storage:
            del self._otp_storage[key]
            logger.info(f"OTP invalidated for {identifier} with purpose {purpose}")
            return True
        return False
    
    async def get_otp_info(self, identifier: str, purpose: str) -> Optional[dict]:
        """
        Get OTP information without revealing the code.
        Useful for checking expiry and attempts.
        
        Args:
            identifier: Email or phone number
            purpose: 'email_verification' or 'password_reset'
        
        Returns:
            Dict with OTP info (without the actual code) or None
        """
        key = self._get_otp_key(identifier, purpose)
        otp_data = self._otp_storage.get(key)
        
        if not otp_data:
            return None
        
        return {
            "purpose": otp_data["purpose"],
            "created_at": otp_data["created_at"],
            "expires_at": otp_data["expires_at"],
            "attempts": otp_data["attempts"],
            "max_attempts": otp_data["max_attempts"],
            "is_expired": datetime.utcnow() > datetime.fromisoformat(otp_data["expires_at"])
        }
    
    async def cleanup_expired_otps(self):
        """Clean up expired OTPs from storage"""
        current_time = datetime.utcnow()
        expired_keys = []
        
        for key, otp_data in self._otp_storage.items():
            expires_at = datetime.fromisoformat(otp_data["expires_at"])
            if current_time > expires_at:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._otp_storage[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired OTPs")


# Global singleton instance so OTPs persist across requests within the process
otp_service = OTPService()


# Production Redis implementation (commented out for now)
"""
class RedisOTPService(OTPService):
    def __init__(self):
        super().__init__()
        self.redis = redis.from_url(settings.REDIS_URL)
    
    async def generate_otp(self, identifier: str, purpose: str) -> str:
        otp_code = self._generate_otp_code()
        expiry_seconds = self.otp_expiry_minutes * 60
        
        otp_data = {
            "code": otp_code,
            "purpose": purpose,
            "created_at": datetime.utcnow().isoformat(),
            "attempts": 0,
            "max_attempts": self.max_attempts
        }
        
        key = self._get_otp_key(identifier, purpose)
        await self.redis.setex(key, expiry_seconds, json.dumps(otp_data))
        
        return otp_code
    
    async def verify_otp(self, identifier: str, otp_code: str, purpose: str) -> bool:
        key = self._get_otp_key(identifier, purpose)
        otp_data_json = await self.redis.get(key)
        
        if not otp_data_json:
            return False
        
        otp_data = json.loads(otp_data_json)
        
        if otp_data["attempts"] >= otp_data["max_attempts"]:
            await self.redis.delete(key)
            return False
        
        otp_data["attempts"] += 1
        
        if otp_data["code"] == otp_code:
            await self.redis.delete(key)
            return True
        else:
            # Update attempts
            ttl = await self.redis.ttl(key)
            if ttl > 0:
                await self.redis.setex(key, ttl, json.dumps(otp_data))
            return False
"""