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
    
    async def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None):
        """Send email using SMTP"""
        try:
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
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                start_tls=True,
                username=self.smtp_user,
                password=self.smtp_pass,
            )
            
            logger.info(f"Email sent successfully to {to_email}")
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise

    async def send_document_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        pdf_bytes: bytes,
        filename: str = "document.pdf",
        text_fallback: Optional[str] = None,
    ):
        """Send email with PDF attachment (e.g. invoice or receipt)."""
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
        )
        logger.info(f"Document email sent to {to_email} (attachment: {filename})")

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