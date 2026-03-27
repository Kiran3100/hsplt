# app/services/email_service.py

"""
Email service using SendGrid SMTP with correct port handling
"""
import aiosmtplib
import asyncio
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SendGrid SMTP"""
    
    # SendGrid port configurations (tested on Render)
    # Port 587: STARTTLS (standard, but blocked on Render)
    # Port 2525: Opportunistic TLS (auto-upgrades, works on Render!)
    # Port 465: Implicit SSL/TLS
    SENDGRID_PORTS = [2525, 587, 465]
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_pass = settings.SMTP_PASS
        self.email_from = settings.EMAIL_FROM
        
        if not self.smtp_user or not self.smtp_pass:
            logger.warning(
                "⚠️  SMTP credentials not configured!\n"
                "For SendGrid, set:\n"
                "  SMTP_USER=apikey\n"
                "  SMTP_PASS=<your_sendgrid_api_key>"
            )
        
        # Determine TLS method based on port
        if self.smtp_port == 465:
            tls_mode = "Implicit SSL/TLS"
        elif self.smtp_port == 2525:
            tls_mode = "Opportunistic TLS (auto-upgrade)"
        else:  # 587
            tls_mode = "STARTTLS"
        
        logger.info(
            f"EmailService initialized:\n"
            f"  Provider: SendGrid SMTP\n"
            f"  Host: {self.smtp_host}:{self.smtp_port}\n"
            f"  TLS Mode: {tls_mode}\n"
            f"  User: {self.smtp_user}\n"
            f"  From: {self.email_from}\n"
            f"  Configured: {bool(self.smtp_user and self.smtp_pass)}"
        )
    
    def _get_tls_settings(self, port: int) -> dict:
        """
        Get appropriate TLS settings for each port.
        
        Returns dict with 'use_tls' and 'start_tls' flags.
        """
        if port == 465:
            # Port 465: Implicit TLS from start
            return {"use_tls": True, "start_tls": False}
        elif port == 2525:
            # Port 2525: Plain connection, auto-upgrades to TLS (Render-friendly)
            return {"use_tls": False, "start_tls": False}
        else:
            # Port 587: Standard STARTTLS
            return {"use_tls": False, "start_tls": True}
    
    async def _try_send_with_port(
        self,
        message,
        port: int,
        timeout: int = 10
    ) -> tuple[bool, str]:
        """
        Try sending email with specific port and appropriate TLS handling.
        Returns (success, error_message)
        """
        try:
            tls_settings = self._get_tls_settings(port)
            
            if port == 465:
                tls_mode = "Implicit TLS"
            elif port == 2525:
                tls_mode = "Opportunistic TLS"
            else:
                tls_mode = "STARTTLS"
            
            logger.info(f"📡 Trying port {port} ({tls_mode})...")
            
            await asyncio.wait_for(
                aiosmtplib.send(
                    message,
                    hostname=self.smtp_host,
                    port=port,
                    use_tls=tls_settings["use_tls"],
                    start_tls=tls_settings["start_tls"],
                    username=self.smtp_user,
                    password=self.smtp_pass,
                    timeout=timeout,
                ),
                timeout=timeout + 5
            )
            
            logger.info(f"✅ Email sent successfully via port {port} ({tls_mode})")
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
        
        except aiosmtplib.SMTPException as e:
            error = f"SMTP error: {str(e)}"
            logger.warning(f"📮 Port {port} failed: {error}")
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
        Port 2525 uses opportunistic TLS (works on Render!).
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
            
            # If primary port failed, try alternatives
            logger.warning(f"⚠️  Primary port {self.smtp_port} failed: {error}")
            logger.info("🔄 Trying alternative SendGrid ports...")
            
            for alt_port in self.SENDGRID_PORTS:
                if alt_port == self.smtp_port:
                    continue  # Skip already-tried port
                
                success, error = await self._try_send_with_port(message, alt_port, timeout)
                
                if success:
                    logger.info(f"✅ Email sent via fallback port {alt_port}")
                    logger.warning(
                        f"💡 Update SMTP_PORT to {alt_port} in environment variables for better performance"
                    )
                    return True
            
            # All ports failed
            logger.error(f"❌ All SMTP ports failed for {to_email}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Unexpected error: {type(e).__name__}: {str(e)}")
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
        """Send email with PDF attachment via SMTP"""
        try:
            logger.info(f"📎 Sending document email to {to_email} (attachment: {filename})")
            
            if not self.smtp_user or not self.smtp_pass:
                logger.error("SMTP credentials not configured")
                return False
            
            # Build multipart message
            message = MIMEMultipart()
            message["Subject"] = subject
            message["From"] = self.email_from
            message["To"] = to_email
            
            # Add text/HTML parts
            if text_fallback:
                message.attach(MIMEText(text_fallback, "plain"))
            message.attach(MIMEText(body_html, "html"))
            
            # Attach PDF
            pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
            pdf_attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=filename
            )
            message.attach(pdf_attachment)
            
            # Get TLS settings for current port
            tls_settings = self._get_tls_settings(self.smtp_port)
            
            await asyncio.wait_for(
                aiosmtplib.send(
                    message,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    use_tls=tls_settings["use_tls"],
                    start_tls=tls_settings["start_tls"],
                    username=self.smtp_user,
                    password=self.smtp_pass,
                    timeout=timeout,
                ),
                timeout=timeout + 5
            )
            
            logger.info(f"✅ Document email sent to {to_email} (attachment: {filename})")
            return True
                
        except Exception as e:
            logger.error(f"❌ Failed to send document email: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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
                
                <p style="font-size: 16px;">Thank you for registering! Please verify your email using the code below:</p>
                
                <div style="background-color: #ffffff; padding: 25px; border-radius: 8px; text-align: center; margin: 30px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="font-size: 14px; color: #666; margin-bottom: 10px;">Your verification code:</div>
                    <div style="font-size: 36px; font-weight: bold; color: #667eea; letter-spacing: 8px; font-family: 'Courier New', monospace;">{otp_code}</div>
                </div>
                
                <p style="font-size: 14px; color: #666;">This code expires in 10 minutes.</p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 16px; margin-bottom: 5px;">Best regards,</p>
                <p style="font-size: 16px; margin-top: 0;"><strong>Hospital Management System Team</strong></p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"Hi {first_name},\n\nYour verification code: {otp_code}\n\nThis code expires in 10 minutes.\n\nBest regards,\nHospital Management System Team"
        
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
                
                <p style="font-size: 16px;">Use the code below to reset your password:</p>
                
                <div style="background-color: #ffffff; padding: 25px; border-radius: 8px; text-align: center; margin: 30px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="font-size: 14px; color: #666; margin-bottom: 10px;">Your reset code:</div>
                    <div style="font-size: 36px; font-weight: bold; color: #e74c3c; letter-spacing: 8px; font-family: 'Courier New', monospace;">{otp_code}</div>
                </div>
                
                <p style="font-size: 14px; color: #666;">This code expires in 10 minutes.</p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 16px; margin-bottom: 5px;">Best regards,</p>
                <p style="font-size: 16px; margin-top: 0;"><strong>Hospital Management System Team</strong></p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"Hi {first_name},\n\nYour password reset code: {otp_code}\n\nThis code expires in 10 minutes.\n\nBest regards,\nHospital Management System Team"
        
        return await self.send_email(email, subject, html_content, text_content)