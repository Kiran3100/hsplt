"""
Email service for sending OTP, notification, and document (invoice/receipt) emails.
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_pass = settings.SMTP_PASS
        self.email_from = settings.EMAIL_FROM
        
        # Log configuration (mask password)
        logger.info(
            f"EmailService initialized: host={self.smtp_host}, port={self.smtp_port}, "
            f"user={self.smtp_user}, from={self.email_from}"
        )
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str, 
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send email using SMTP
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            logger.info(f"Attempting to send email to {to_email}")
            logger.debug(f"Subject: {subject}")
            
            # Validate configuration
            if not self.smtp_user or not self.smtp_pass:
                logger.error("SMTP credentials not configured")
                raise ValueError("SMTP_USER and SMTP_PASS must be set")
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.email_from
            message["To"] = to_email
            
            # Add text content
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Log connection attempt
            logger.debug(
                f"Connecting to SMTP server: {self.smtp_host}:{self.smtp_port}"
            )
            
            # Send email with timeout
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                start_tls=True,
                username=self.smtp_user,
                password=self.smtp_pass,
                timeout=30,  # 30 second timeout
            )
            
            logger.info(f"✓ Email sent successfully to {to_email}")
            return True
            
        except aiosmtplib.SMTPAuthenticationError as e:
            logger.error(f"✗ SMTP Authentication failed for {to_email}: {str(e)}")
            logger.error("Check SMTP_USER and SMTP_PASS environment variables")
            logger.error("For Gmail, ensure you're using an App Password, not your regular password")
            raise
            
        except aiosmtplib.SMTPRecipientsRefused as e:
            logger.error(f"✗ Recipient refused for {to_email}: {str(e)}")
            raise
            
        except aiosmtplib.SMTPException as e:
            logger.error(f"✗ SMTP error sending email to {to_email}: {type(e).__name__}: {str(e)}")
            raise
            
        except TimeoutError as e:
            logger.error(f"✗ SMTP connection timeout for {to_email}: {str(e)}")
            logger.error(f"Could not connect to {self.smtp_host}:{self.smtp_port}")
            raise
            
        except Exception as e:
            logger.error(f"✗ Unexpected error sending email to {to_email}: {type(e).__name__}: {str(e)}")
            logger.exception("Full traceback:")
            raise

    async def send_document_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        pdf_bytes: bytes,
        filename: str = "document.pdf",
        text_fallback: Optional[str] = None,
    ) -> bool:
        """
        Send email with PDF attachment (e.g. invoice or receipt).
        
        Returns:
            bool: True if email sent successfully
        """
        try:
            logger.info(f"Sending document email to {to_email} (attachment: {filename})")
            
            message = MIMEMultipart()
            message["Subject"] = subject
            message["From"] = self.email_from
            message["To"] = to_email
            
            if text_fallback:
                message.attach(MIMEText(text_fallback, "plain"))
            
            message.attach(MIMEText(body_html, "html"))
            
            attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
            attachment.add_header("Content-Disposition", "attachment", filename=filename)
            message.attach(attachment)
            
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                start_tls=True,
                username=self.smtp_user,
                password=self.smtp_pass,
                timeout=30,
            )
            
            logger.info(f"✓ Document email sent to {to_email} (attachment: {filename})")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to send document email to {to_email}: {type(e).__name__}: {str(e)}")
            raise

    async def send_verification_email(self, email: str, otp_code: str, first_name: str):
        """Send email verification OTP"""
        subject = "Verify Your Email - Hospital Management System"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Email Verification</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
                <h2 style="color: #2c3e50; text-align: center;">Email Verification</h2>
                
                <p>Dear {first_name},</p>
                
                <p>Thank you for registering with our Hospital Management System. To complete your registration, please verify your email address using the code below:</p>
                
                <div style="background-color: #ffffff; padding: 20px; border-radius: 5px; text-align: center; margin: 20px 0;">
                    <h1 style="color: #3498db; font-size: 32px; letter-spacing: 5px; margin: 0;">{otp_code}</h1>
                </div>
                
                <p><strong>Important:</strong></p>
                <ul>
                    <li>This code will expire in 10 minutes</li>
                    <li>Do not share this code with anyone</li>
                    <li>If you didn't request this verification, please ignore this email</li>
                </ul>
                
                <p>If you have any questions, please contact our support team.</p>
                
                <p>Best regards,<br>Hospital Management System Team</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Email Verification
        
        Dear {first_name},
        
        Thank you for registering with our Hospital Management System. 
        To complete your registration, please verify your email address using this code:
        
        {otp_code}
        
        This code will expire in 10 minutes.
        Do not share this code with anyone.
        
        Best regards,
        Hospital Management System Team
        """
        
        await self.send_email(email, subject, html_content, text_content)
    
    async def send_password_reset_email(self, email: str, otp_code: str, first_name: str):
        """Send password reset OTP"""
        subject = "Password Reset - Hospital Management System"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Password Reset</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
                <h2 style="color: #e74c3c; text-align: center;">Password Reset Request</h2>
                
                <p>Dear {first_name},</p>
                
                <p>We received a request to reset your password. Use the code below to reset your password:</p>
                
                <div style="background-color: #ffffff; padding: 20px; border-radius: 5px; text-align: center; margin: 20px 0;">
                    <h1 style="color: #e74c3c; font-size: 32px; letter-spacing: 5px; margin: 0;">{otp_code}</h1>
                </div>
                
                <p><strong>Security Notice:</strong></p>
                <ul>
                    <li>This code will expire in 10 minutes</li>
                    <li>Do not share this code with anyone</li>
                    <li>If you didn't request this reset, please ignore this email</li>
                    <li>Your password will remain unchanged until you complete the reset process</li>
                </ul>
                
                <p>If you continue to have problems, please contact our support team.</p>
                
                <p>Best regards,<br>Hospital Management System Team</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Reset Request
        
        Dear {first_name},
        
        We received a request to reset your password. 
        Use this code to reset your password:
        
        {otp_code}
        
        This code will expire in 10 minutes.
        Do not share this code with anyone.
        
        If you didn't request this reset, please ignore this email.
        
        Best regards,
        Hospital Management System Team
        """
        
        await self.send_email(email, subject, html_content, text_content)