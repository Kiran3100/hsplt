"""
Public contact-us API (DCM / marketing site).
POST /contact/send — no authentication.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException
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
        "smtp_configured": bool(settings.SMTP_USER and settings.SMTP_PASS),
        "smtp_host": settings.SMTP_HOST,
        "smtp_port": settings.SMTP_PORT,
        "email_from": settings.EMAIL_FROM,
        "notify_email": settings.CONTACT_MESSAGE_NOTIFY_EMAIL or settings.SUPERADMIN_EMAIL or settings.EMAIL_FROM,
    }
    
    if not checks["smtp_configured"]:
        logger.warning("SMTP not fully configured")
        checks["status"] = "degraded"
        checks["warning"] = "SMTP credentials not configured"
    
    return JSONResponse(content=checks)


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
    
    1. Save message to database
    2. Send notification to admin
    3. Send acknowledgment to user (if enabled)
    """
    
    logger.info(f"Contact form submission from {payload.email}")
    
    # Validate SMTP configuration
    if not settings.SMTP_USER or not settings.SMTP_PASS:
        logger.error("SMTP credentials not configured - contact form will save to DB only")
        # Continue anyway - at least save to database
    
    # 1. Save to database
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
    
    logger.info(f"Notification will be sent to: {notify_to}")

    # 2. Send notification email to admin
    email_service = EmailService()
    email_sent = False
    
    try:
        admin_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                table {{ border-collapse: collapse; width: 100%; }}
                td {{ padding: 8px; border: 1px solid #ddd; }}
                b {{ color: #333; }}
            </style>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2c3e50;">New Contact Message</h2>
            <table>
                <tr><td><b>Name</b></td><td>{payload.full_name}</td></tr>
                <tr><td><b>Email</b></td><td>{payload.email}</td></tr>
                <tr><td><b>Phone</b></td><td>{payload.phone or '—'}</td></tr>
                <tr><td><b>Hospital</b></td><td>{payload.hospital_name or '—'}</td></tr>
                <tr><td><b>Message</b></td><td style="white-space: pre-wrap;">{payload.message}</td></tr>
            </table>
            <p style="color: #666; font-size: 12px; margin-top: 20px;">
                Submitted at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            </p>
        </body>
        </html>
        """
        
        admin_text = (
            f"New Contact Message\n"
            f"==================\n\n"
            f"Name: {payload.full_name}\n"
            f"Email: {payload.email}\n"
            f"Phone: {payload.phone or '-'}\n"
            f"Hospital: {payload.hospital_name or '-'}\n"
            f"Message:\n{payload.message}\n\n"
            f"Submitted at {datetime.utcnow().isoformat()}Z"
        )
        
        await email_service.send_email(
            notify_to,
            f"[Contact Form] {payload.full_name}",
            admin_html,
            admin_text,
        )
        email_sent = True
        logger.info(f"✓ Admin notification sent to {notify_to}")
        
    except Exception as e:
        logger.error(f"✗ Admin notification email failed: {type(e).__name__}: {str(e)}")
        # Don't fail the request - message is already saved to DB

    # 3. Send acknowledgment email to user (if enabled)
    ack_sent = False
    
    if settings.CONTACT_MESSAGE_SEND_ACK:
        try:
            ack_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
            </head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
                    <h2 style="color: #2c3e50;">Thank You for Contacting Us</h2>
                    
                    <p>Hi {payload.full_name},</p>
                    
                    <p>Thank you for reaching out to us. We have received your message and our team will get back to you as soon as possible.</p>
                    
                    <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>Your message:</strong></p>
                        <p style="margin: 10px 0 0 0; white-space: pre-wrap;">{payload.message}</p>
                    </div>
                    
                    <p>If you have any urgent concerns, please don't hesitate to call us.</p>
                    
                    <p>Best regards,<br/>
                    <strong>Hospital Management Team</strong></p>
                </div>
            </body>
            </html>
            """
            
            ack_text = (
                f"Hi {payload.full_name},\n\n"
                f"Thank you for contacting us. We have received your message:\n\n"
                f"{payload.message}\n\n"
                f"Our team will reach out to you soon.\n\n"
                f"Best regards,\n"
                f"Hospital Management Team"
            )
            
            await email_service.send_email(
                str(payload.email),
                "We Received Your Message",
                ack_html,
                ack_text,
            )
            ack_sent = True
            logger.info(f"✓ Acknowledgment email sent to {payload.email}")
            
        except Exception as e:
            logger.error(f"✗ Acknowledgment email failed: {type(e).__name__}: {str(e)}")
            # Don't fail the request

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": "Message received successfully. We'll get back to you soon!",
            "details": {
                "saved_to_database": True,
                "admin_notified": email_sent,
                "acknowledgment_sent": ack_sent,
            }
        },
    )