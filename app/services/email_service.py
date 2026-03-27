# email_service.py

"""
Email service using SendGrid SMTP (not API)
"""
import aiosmtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


# app/services/email_service.py

class EmailService:
    """Service for sending emails via SendGrid SMTP"""
    
    # SendGrid supports multiple ports
    SENDGRID_PORTS = [2525, 587, 465]  # Priority order for Render
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_pass = settings.SMTP_PASS
        self.email_from = settings.EMAIL_FROM
        
        # Validate configuration
        if not self.smtp_user or not self.smtp_pass:
            logger.warning(
                "⚠️  SMTP credentials not configured!\n"
                "For SendGrid, set:\n"
                "  SMTP_USER=apikey\n"
                "  SMTP_PASS=<your_sendgrid_api_key>"
            )
        
        logger.info(
            f"EmailService initialized:\n"
            f"  Provider: SendGrid SMTP\n"
            f"  Host: {self.smtp_host}:{self.smtp_port}\n"
            f"  User: {self.smtp_user}\n"
            f"  From: {self.email_from}\n"
            f"  Configured: {bool(self.smtp_user and self.smtp_pass)}"
        )
    
    async def _try_send_with_port(
        self,
        message,
        port: int,
        timeout: int = 10
    ) -> tuple[bool, str]:
        """
        Try sending email with specific port.
        Returns (success, error_message)
        """
        try:
            logger.info(f"📡 Trying SMTP port {port}...")
            
            await asyncio.wait_for(
                aiosmtplib.send(
                    message,
                    hostname=self.smtp_host,
                    port=port,
                    start_tls=True,
                    username=self.smtp_user,
                    password=self.smtp_pass,
                    timeout=timeout,
                ),
                timeout=timeout + 5
            )
            
            logger.info(f"✅ Email sent successfully via port {port}")
            return True, None
            
        except asyncio.TimeoutError:
            error = f"Timeout on port {port}"
            logger.warning(f"⏱️  {error}")
            return False, error
            
        except aiosmtplib.SMTPConnectTimeoutError:
            error = f"Connection timeout on port {port}"
            logger.warning(f"🔌 {error}")
            return False, error
            
        except aiosmtplib.SMTPAuthenticationError as e:
            error = f"Authentication failed: {str(e)}"
            logger.error(f"🔐 {error}")
            return False, error
            
        except Exception as e:
            error = f"{type(e).__name__}: {str(e)}"
            logger.warning(f"❌ Port {port} failed: {error}")
            return False, error
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str, 
        text_content: Optional[str] = None,
        timeout: int = 15
    ) -> bool:
        """
        Send email using SendGrid SMTP with automatic port fallback.
        Tries ports in order: 2525 (Render-friendly), 587, 465
        """
        try:
            logger.info(f"📧 Sending email to {to_email}")
            logger.info(f"   Subject: {subject}")
            
            if not self.smtp_user or not self.smtp_pass:
                logger.error("❌ SMTP credentials not configured")
                return False
            
            # Build message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.email_from
            message["To"] = to_email
            
            if text_content:
                message.attach(MIMEText(text_content, "plain"))
            
            message.attach(MIMEText(html_content, "html"))
            
            # Try primary port first
            success, error = await self._try_send_with_port(message, self.smtp_port, timeout)
            
            if success:
                return True
            
            # If primary port failed, try alternatives (for Render compatibility)
            logger.warning(f"⚠️  Primary port {self.smtp_port} failed: {error}")
            logger.info("🔄 Trying alternative SendGrid ports...")
            
            for alt_port in self.SENDGRID_PORTS:
                if alt_port == self.smtp_port:
                    continue  # Skip already-tried port
                
                success, error = await self._try_send_with_port(message, alt_port, timeout)
                
                if success:
                    logger.info(f"✅ Email sent via fallback port {alt_port}")
                    logger.warning(
                        f"💡 TIP: Update SMTP_PORT to {alt_port} in your environment "
                        f"variables for better performance"
                    )
                    return True
            
            # All ports failed
            logger.error(f"❌ All SMTP ports failed for {to_email}")
            logger.error(f"   Tried ports: {[self.smtp_port] + [p for p in self.SENDGRID_PORTS if p != self.smtp_port]}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Unexpected error sending email: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False


    async def send_document_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        pdf_bytes: bytes,
        filename: str = "document.pdf",
        text_fallback: Optional[str] = None,
        timeout: int = 30
    ) -> bool:
        """
        Send email with PDF attachment via SendGrid
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body_html: HTML email body
            pdf_bytes: PDF file as bytes
            filename: Attachment filename
            text_fallback: Plain text version
            timeout: Request timeout
            
        Returns:
            bool: True if sent successfully
        """
        try:
            logger.info(f"📎 Sending document email to {to_email} (attachment: {filename})")
            
            if not self.sendgrid_api_key:
                logger.error("SendGrid API key not configured")
                return False
            
            # Build content
            content = []
            if text_fallback:
                content.append({
                    "type": "text/plain",
                    "value": text_fallback
                })
            content.append({
                "type": "text/html",
                "value": body_html
            })
            
            # Encode PDF as base64
            pdf_base64 = base64.b64encode(pdf_bytes).decode()
            
            payload = {
                "personalizations": [
                    {
                        "to": [{"email": to_email}],
                        "subject": subject
                    }
                ],
                "from": {
                    "email": self.email_from,
                    "name": "Hospital Management System"
                },
                "content": content,
                "attachments": [
                    {
                        "content": pdf_base64,
                        "type": "application/pdf",
                        "filename": filename,
                        "disposition": "attachment"
                    }
                ]
            }
            
            headers = {
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await asyncio.wait_for(
                    client.post(
                        self.api_url,
                        headers=headers,
                        json=payload
                    ),
                    timeout=timeout
                )
            
            if response.status_code == 202:
                logger.info(f"✓ Document email sent to {to_email} (attachment: {filename})")
                return True
            else:
                logger.error(
                    f"✗ SendGrid API error: {response.status_code}\n"
                    f"Response: {response.text}"
                )
                return False
                
        except Exception as e:
            logger.error(f"✗ Failed to send document email to {to_email}: {type(e).__name__}: {str(e)}")
            return False

    async def send_verification_email(self, email: str, otp_code: str, first_name: str):
        """Send email verification OTP"""
        subject = "Verify Your Email - Hospital Management System"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Email Verification</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">🏥 Hospital Management</h1>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 40px 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #2c3e50; margin-top: 0;">Email Verification</h2>
                
                <p style="font-size: 16px;">Hi <strong>{first_name}</strong>,</p>
                
                <p style="font-size: 16px;">Thank you for registering with our Hospital Management System. To complete your registration, please verify your email address using the code below:</p>
                
                <div style="background-color: #ffffff; padding: 25px; border-radius: 8px; text-align: center; margin: 30px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="font-size: 14px; color: #666; margin-bottom: 10px;">Your verification code:</div>
                    <div style="font-size: 36px; font-weight: bold; color: #667eea; letter-spacing: 8px; font-family: 'Courier New', monospace;">{otp_code}</div>
                </div>
                
                <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px;">
                    <p style="margin: 0; font-size: 14px;"><strong>⚠️ Important:</strong></p>
                    <ul style="margin: 10px 0; padding-left: 20px; font-size: 14px;">
                        <li>This code will expire in <strong>10 minutes</strong></li>
                        <li>Do not share this code with anyone</li>
                        <li>If you didn't request this verification, please ignore this email</li>
                    </ul>
                </div>
                
                <p style="font-size: 14px; color: #666; margin-top: 30px;">
                    If you have any questions, please contact our support team.
                </p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 16px; margin-bottom: 5px;">Best regards,</p>
                <p style="font-size: 16px; margin-top: 0;"><strong>Hospital Management System Team</strong></p>
            </div>
            
            <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                <p>This is an automated message, please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
Email Verification

Hi {first_name},

Thank you for registering with our Hospital Management System. 
To complete your registration, please verify your email address using this code:

{otp_code}

IMPORTANT:
- This code will expire in 10 minutes
- Do not share this code with anyone
- If you didn't request this verification, please ignore this email

If you have any questions, please contact our support team.

Best regards,
Hospital Management System Team

---
This is an automated message, please do not reply to this email.
        """
        
        return await self.send_email(email, subject, html_content, text_content)
    
    async def send_password_reset_email(self, email: str, otp_code: str, first_name: str):
        """Send password reset OTP"""
        subject = "Password Reset - Hospital Management System"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">🔐 Password Reset</h1>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 40px 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #e74c3c; margin-top: 0;">Password Reset Request</h2>
                
                <p style="font-size: 16px;">Hi <strong>{first_name}</strong>,</p>
                
                <p style="font-size: 16px;">We received a request to reset your password. Use the code below to reset your password:</p>
                
                <div style="background-color: #ffffff; padding: 25px; border-radius: 8px; text-align: center; margin: 30px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="font-size: 14px; color: #666; margin-bottom: 10px;">Your reset code:</div>
                    <div style="font-size: 36px; font-weight: bold; color: #e74c3c; letter-spacing: 8px; font-family: 'Courier New', monospace;">{otp_code}</div>
                </div>
                
                <div style="background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 20px 0; border-radius: 4px;">
                    <p style="margin: 0; font-size: 14px;"><strong>🔒 Security Notice:</strong></p>
                    <ul style="margin: 10px 0; padding-left: 20px; font-size: 14px;">
                        <li>This code will expire in <strong>10 minutes</strong></li>
                        <li>Do not share this code with anyone</li>
                        <li>If you didn't request this reset, please ignore this email</li>
                        <li>Your password will remain unchanged until you complete the reset process</li>
                    </ul>
                </div>
                
                <p style="font-size: 14px; color: #666; margin-top: 30px;">
                    If you continue to have problems, please contact our support team.
                </p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 16px; margin-bottom: 5px;">Best regards,</p>
                <p style="font-size: 16px; margin-top: 0;"><strong>Hospital Management System Team</strong></p>
            </div>
            
            <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                <p>This is an automated message, please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
Password Reset Request

Hi {first_name},

We received a request to reset your password. 
Use this code to reset your password:

{otp_code}

SECURITY NOTICE:
- This code will expire in 10 minutes
- Do not share this code with anyone
- If you didn't request this reset, please ignore this email
- Your password will remain unchanged until you complete the reset process

If you continue to have problems, please contact our support team.

Best regards,
Hospital Management System Team

---
This is an automated message, please do not reply to this email.
        """
        
        return await self.send_email(email, subject, html_content, text_content)