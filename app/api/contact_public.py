# contact_public.py

"""
Public contact-us API (DCM / marketing site).
POST /contact/send — no authentication.
"""
import logging
import asyncio
from datetime import datetime

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import get_db_session
from app.models.contact_message import ContactMessage
from app.schemas.contact_message import ContactMessageCreate
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact", tags=["Contact"])

_CONTACT_OPENAPI_EXAMPLE = {
    "full_name": "John Smith",
    "email": "john.smith@hospital.com",
    "phone": "+919876543210",
    "hospital_name": "City Care Hospital",
    "message": "We are interested in a demo and want to understand billing and lab modules.",
}


@router.get("/health", include_in_schema=True)
async def contact_health_check():
    """Check if contact service is properly configured"""
    checks = {
        "status": "operational",
        "email_provider": "SendGrid SMTP",
        "smtp_configured": bool(settings.SMTP_USER and settings.SMTP_PASS),
        "smtp_host": settings.SMTP_HOST,
        "smtp_user": settings.SMTP_USER,
        "email_from": settings.EMAIL_FROM,
        "notify_email": settings.CONTACT_MESSAGE_NOTIFY_EMAIL or settings.SUPERADMIN_EMAIL or settings.EMAIL_FROM,
    }
    
    if not checks["smtp_configured"]:
        logger.warning("SMTP credentials not configured")
        checks["status"] = "degraded"
        checks["warning"] = "SMTP_USER and SMTP_PASS not set"
    
    return JSONResponse(content=checks)


async def send_email_safe(
    email_service: EmailService, 
    to_email: str, 
    subject: str, 
    html: str, 
    text: str, 
    timeout: int = 15
) -> bool:
    """
    Safely send email with timeout protection.
    Returns True if successful, False otherwise.
    Never raises exceptions.
    """
    try:
        result = await asyncio.wait_for(
            email_service.send_email(to_email, subject, html, text),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        logger.error(f"Email to {to_email} timed out after {timeout}s")
        return False
    except Exception as e:
        logger.error(f"Email to {to_email} failed: {type(e).__name__}: {str(e)}")
        return False


@router.post("/test-email", include_in_schema=True)
async def test_email_sending(test_email: str = "kiranios456@gmail.com"):
    """Test SendGrid email sending (for debugging)"""
    logger.info(f"Testing SendGrid email to {test_email}")
    
    if not settings.SENDGRID_API_KEY:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "SENDGRID_API_KEY not configured in environment variables"
            }
        )
    
    email_service = EmailService()
    
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px;">
            <h1 style="color: white;">✅ Test Email Success!</h1>
        </div>
        <div style="padding: 20px;">
            <h2>SendGrid Configuration Working</h2>
            <p>This is a test email from your Hospital Management System.</p>
            <p>If you received this, SendGrid is configured correctly! 🎉</p>
        </div>
    </body>
    </html>
    """
    
    test_text = "Test email from Hospital Management System. If you received this, SendGrid is working correctly!"
    
    result = await send_email_safe(
        email_service,
        test_email,
        "🧪 Test Email - Hospital Management System",
        test_html,
        test_text,
        timeout=20
    )
    
    return JSONResponse(
        status_code=200 if result else 500,
        content={
            "success": result,
            "message": "Test email sent successfully! Check your inbox." if result else "Test email failed. Check logs for details.",
            "config": {
                "provider": "SendGrid",
                "api_key_set": bool(settings.SENDGRID_API_KEY),
                "email_from": settings.EMAIL_FROM,
            }
        }
    )


@router.post(
    "/send",
    summary="Send contact-us message",
    description="Public endpoint for contact form submissions from website/DCM.",
    response_model=None,
)
async def send_contact_message(
    db: AsyncSession = Depends(get_db_session),
    payload: ContactMessageCreate = Body(
        ...,
        openapi_examples={
            "default": {"summary": "Full example", "value": _CONTACT_OPENAPI_EXAMPLE},
            "minimal": {
                "summary": "Required fields only",
                "value": {
                    "full_name": "Jane Doe",
                    "email": "jane@clinic.com",
                    "message": "Please contact us for onboarding details.",
                },
            },
        },
    ),
):
    """
    Handle contact form submissions.
    
    1. Save message to database (required)
    2. Send notification to admin via SendGrid (best effort)
    3. Send acknowledgment to user via SendGrid (best effort)
    """
    
    logger.info(f"📨 Contact form submission from {payload.email}")
    
    # 1. Save to database (CRITICAL)
    try:
        row = ContactMessage(
            full_name=payload.full_name,
            email=str(payload.email).strip().lower(),
            phone=payload.phone,
            hospital_name=payload.hospital_name,
            message=payload.message,
        )
        db.add(row)
        await db.commit()
        logger.info(f"✓ Contact message saved to database (id: {row.id})")
    except Exception as e:
        logger.exception(f"✗ Contact message DB save failed: {e}")
        await db.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "success": False, 
                "error": "Failed to save message. Please try again later."
            },
        )

    # Determine notification recipient
    notify_to = (
        (settings.CONTACT_MESSAGE_NOTIFY_EMAIL or "").strip() 
        or (settings.SUPERADMIN_EMAIL or "").strip() 
        or settings.EMAIL_FROM
    )

    # 2. Send emails via SendGrid (NON-BLOCKING)
    email_service = EmailService()
    email_sent = False
    ack_sent = False
    
    # Send admin notification
    if settings.SENDGRID_API_KEY:
        try:
            admin_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 25px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">🔔 New Contact Message</h1>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                    <table style="width: 100%; border-collapse: collapse; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <tr style="background-color: #f8f9fa;">
                            <td style="padding: 12px 15px; border-bottom: 1px solid #dee2e6; font-weight: bold; width: 30%;">Name</td>
                            <td style="padding: 12px 15px; border-bottom: 1px solid #dee2e6;">{payload.full_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px 15px; border-bottom: 1px solid #dee2e6; font-weight: bold; background-color: #f8f9fa;">Email</td>
                            <td style="padding: 12px 15px; border-bottom: 1px solid #dee2e6;"><a href="mailto:{payload.email}" style="color: #667eea; text-decoration: none;">{payload.email}</a></td>
                        </tr>
                        <tr>
                            <td style="padding: 12px 15px; border-bottom: 1px solid #dee2e6; font-weight: bold; background-color: #f8f9fa;">Phone</td>
                            <td style="padding: 12px 15px; border-bottom: 1px solid #dee2e6;">{payload.phone or '—'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px 15px; border-bottom: 1px solid #dee2e6; font-weight: bold; background-color: #f8f9fa;">Hospital</td>
                            <td style="padding: 12px 15px; border-bottom: 1px solid #dee2e6;">{payload.hospital_name or '—'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px 15px; font-weight: bold; background-color: #f8f9fa; vertical-align: top;">Message</td>
                            <td style="padding: 12px 15px; white-space: pre-wrap;">{payload.message}</td>
                        </tr>
                    </table>
                    
                    <div style="margin-top: 20px; padding: 15px; background-color: #e7f3ff; border-left: 4px solid #2196F3; border-radius: 4px;">
                        <p style="margin: 0; font-size: 13px; color: #666;">
                            📅 Submitted at <strong>{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</strong>
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            admin_text = (
                f"🔔 NEW CONTACT MESSAGE\n"
                f"{'='*60}\n\n"
                f"Name:     {payload.full_name}\n"
                f"Email:    {payload.email}\n"
                f"Phone:    {payload.phone or '-'}\n"
                f"Hospital: {payload.hospital_name or '-'}\n\n"
                f"Message:\n{'-'*60}\n{payload.message}\n{'-'*60}\n\n"
                f"Submitted: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
            
            email_sent = await send_email_safe(
                email_service,
                notify_to,
                f"🔔 [Contact Form] {payload.full_name}",
                admin_html,
                admin_text,
                timeout=15
            )
            
            if email_sent:
                logger.info(f"✓ Admin notification sent to {notify_to}")
            else:
                logger.warning(f"✗ Admin notification failed for {notify_to}")
            
        except Exception as e:
            logger.error(f"✗ Admin email error: {type(e).__name__}: {str(e)}")

        # Send acknowledgment to user
        if settings.CONTACT_MESSAGE_SEND_ACK:
            try:
                ack_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                </head>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                        <h1 style="color: white; margin: 0; font-size: 28px;">✅ Thank You!</h1>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 40px 30px; border-radius: 0 0 10px 10px;">
                        <h2 style="color: #2c3e50; margin-top: 0;">We Received Your Message</h2>
                        
                        <p style="font-size: 16px;">Hi <strong>{payload.full_name}</strong>,</p>
                        
                        <p style="font-size: 16px;">Thank you for reaching out to us! We have received your message and our team will get back to you as soon as possible.</p>
                        
                        <div style="background-color: #e8f4f8; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #3498db;">
                            <p style="margin: 0 0 10px 0; color: #666; font-size: 14px;"><strong>📝 Your message:</strong></p>
                            <p style="margin: 0; white-space: pre-wrap; color: #333; font-size: 15px;">{payload.message}</p>
                        </div>
                        
                        <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px;">
                            <p style="margin: 0; font-size: 14px;">
                                💡 <strong>What happens next?</strong><br>
                                Our team reviews all inquiries during business hours and typically responds within 24-48 hours.
                            </p>
                        </div>
                        
                        <p style="font-size: 14px; color: #666;">
                            If you have any urgent concerns, please feel free to contact us directly.
                        </p>
                        
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                        
                        <p style="font-size: 16px; margin-bottom: 5px;">Best regards,</p>
                        <p style="font-size: 16px; margin-top: 0;"><strong>Hospital Management Team</strong></p>
                    </div>
                    
                    <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                        <p>This is an automated message, please do not reply to this email.</p>
                    </div>
                </body>
                </html>
                """
                
                ack_text = (
                    f"Hi {payload.full_name},\n\n"
                    f"Thank you for contacting us! We have received your message:\n\n"
                    f'"{payload.message}"\n\n'
                    f"Our team will reach out to you soon, typically within 24-48 hours.\n\n"
                    f"Best regards,\n"
                    f"Hospital Management Team\n\n"
                    f"---\n"
                    f"This is an automated message, please do not reply."
                )
                
                ack_sent = await send_email_safe(
                    email_service,
                    str(payload.email),
                    "✅ We Received Your Message - Hospital Management",
                    ack_html,
                    ack_text,
                    timeout=15
                )
                
                if ack_sent:
                    logger.info(f"✓ Acknowledgment sent to {payload.email}")
                else:
                    logger.warning(f"✗ Acknowledgment failed for {payload.email}")
                
            except Exception as e:
                logger.error(f"✗ Acknowledgment email error: {type(e).__name__}: {str(e)}")
    else:
        logger.warning("⚠️  SENDGRID_API_KEY not configured - emails not sent")

    # Always return success if DB save succeeded
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": "Thank you for reaching out! We've received your message and will get back to you soon.",
            "details": {
                "saved_to_database": True,
                "admin_notified": email_sent,
                "acknowledgment_sent": ack_sent,
            }
        },
    )