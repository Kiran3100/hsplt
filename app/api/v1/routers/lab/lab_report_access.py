"""
Lab Report Access API - Doctor/Patient Report Access + Notifications + Secure Sharing
Handles secure report access for doctors and patients with RBAC and sharing functionality.
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database.session import get_db_session
from app.core.security import get_current_user, require_roles
from app.core.enums import UserRole, ReportPublishStatus, ViewerType, NotificationEventType, NotificationChannel
from app.models.user import User
from app.models.lab import LabOrder, LabReport, ReportShareToken, NotificationOutbox, ReportAccess
from app.schemas.lab import (
    DoctorReportListResponse, PatientReportListResponse, ReportMetadataResponse,
    ShareTokenCreateRequest, ShareTokenResponse, ShareTokenAccessResponse,
    NotificationCreateRequest, NotificationResponse, NotificationStatusResponse,
    ReportSummaryResponse
)
from app.services.lab_service import LabService

router = APIRouter(prefix="/lab/reports", tags=["Lab - Report Access"])

# ============================================================================
# DOCTOR & PATIENT REPORT LISTING ENDPOINTS (5)
# ============================================================================

@router.get("/doctor/lab-reports", response_model=DoctorReportListResponse)
async def get_doctor_lab_reports(
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    from_date: Optional[datetime] = Query(None, description="Filter from date"),
    to_date: Optional[datetime] = Query(None, description="Filter to date"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_roles([UserRole.DOCTOR])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get lab reports accessible to the doctor.
    
    Access Control:
    - **Who can access:** Doctors only (reports for patients/encounters assigned to them)
    """
    lab_service = LabService(db, current_user.hospital_id)
    
    # Get reports with RBAC enforcement
    result = await lab_service.get_doctor_reports(
        doctor_id=current_user.user_id,
        hospital_id=current_user.hospital_id,
        patient_id=patient_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        limit=limit
    )
    
    return result


@router.get("/patient/lab-reports", response_model=PatientReportListResponse)
async def get_patient_lab_reports(
    from_date: Optional[datetime] = Query(None, description="Filter from date"),
    to_date: Optional[datetime] = Query(None, description="Filter to date"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_roles([UserRole.PATIENT])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get lab reports for the current patient.
    
    Access Control:
    - **Who can access:** Patients only (own reports from JWT token)
    """
    lab_service = LabService(db, current_user.hospital_id)
    
    # Get patient's own reports
    result = await lab_service.get_patient_reports(
        patient_id=current_user.user_id,
        hospital_id=current_user.hospital_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        limit=limit
    )
    
    return result


@router.get("/receptionist/lab-reports", response_model=PatientReportListResponse)
async def get_receptionist_lab_reports(
    patient_id: str = Query(..., description="Patient reference (e.g. PAT-XXX) to view reports for"),
    from_date: Optional[datetime] = Query(None, description="Filter from date"),
    to_date: Optional[datetime] = Query(None, description="Filter to date"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_roles([UserRole.RECEPTIONIST])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get lab reports for a patient (receptionist view).
    
    Access Control:
    - **Who can access:** Receptionists only (any patient in their hospital)
    """
    lab_service = LabService(db, current_user.hospital_id)
    result = await lab_service.get_patient_reports(
        patient_id=patient_id,
        hospital_id=current_user.hospital_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        limit=limit
    )
    return result


@router.get("/lab-reports/{report_id}", response_model=ReportMetadataResponse)
async def get_lab_report_metadata(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    request: Request = None
):
    """
    Get lab report metadata with RBAC check.
    
    Access Control:
    - **Who can access:** Doctors (assigned patients), Patients (own reports), Receptionists (hospital)
    """
    lab_service = LabService(db, current_user.hospital_id)
    
    # Get report with access validation
    report = await lab_service.get_report_with_access_check(
        report_id=report_id,
        user_id=current_user.id,
        user_role=(current_user.roles[0].name if current_user.roles else None),
        hospital_id=current_user.hospital_id
    )
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or access denied"
        )
    
    # Log access
    await lab_service.log_report_access(
        report_id=report_id,
        accessed_by=current_user.id,
        access_method="DIRECT",
        access_type="VIEW",
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
        hospital_id=current_user.hospital_id
    )
    
    return report


@router.get("/lab-reports/{report_id}/pdf")
async def download_lab_report_pdf(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    request: Request = None
):
    """
    Download lab report PDF with RBAC check.
    
    Access Control:
    - **Who can access:** Doctors (assigned patients), Patients (own reports), Receptionists (hospital)
    """
    lab_service = LabService(db, current_user.hospital_id)
    
    # Validate access and get PDF path
    pdf_info = await lab_service.get_report_pdf_with_access_check(
        report_id=report_id,
        user_id=current_user.id,
        user_role=(current_user.roles[0].name if current_user.roles else None),
        hospital_id=current_user.hospital_id
    )
    
    if not pdf_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report PDF not found or access denied"
        )
    
    # Log access
    await lab_service.log_report_access(
        report_id=report_id,
        accessed_by=current_user.id,
        access_method="DIRECT",
        access_type="DOWNLOAD",
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
        hospital_id=current_user.hospital_id
    )
    
    # Return PDF file
    return FileResponse(
        path=pdf_info["pdf_path"],
        filename=f"lab_report_{pdf_info['report_number']}.pdf",
        media_type="application/pdf"
    )


@router.get("/lab-reports/{report_id}/summary", response_model=ReportSummaryResponse)
async def get_lab_report_summary(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get quick summary view of lab report.
    
    Access Control:
    - **Who can access:** Doctors (assigned patients), Patients (own reports), Receptionists (hospital)
    """
    lab_service = LabService(db, current_user.hospital_id)
    
    # Get summary with access validation
    summary = await lab_service.get_report_summary_with_access_check(
        report_id=report_id,
        user_id=current_user.id,
        user_role=(current_user.roles[0].name if current_user.roles else None),
        hospital_id=current_user.hospital_id
    )
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or access denied"
        )
    
    return summary


# ============================================================================
# PUBLISH CONTROL ENDPOINTS (Lab Admin) (3)
# ============================================================================

@router.patch("/lab/orders/{order_id}/report/publish")
async def publish_lab_report(
    order_id: UUID,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Publish lab report - makes it available to doctor and patient.
    
    Access Control:
    - **Who can access:** Lab Tech, Hospital Admin only
    """
    lab_service = LabService(db, current_user.hospital_id)
    
    # Publish report
    result = await lab_service.publish_report(
        order_id=order_id,
        published_by=current_user.id,
        hospital_id=current_user.hospital_id
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab order or report not found"
        )
    
    # Create notification for report ready
    await lab_service.create_report_ready_notification(
        order_id=order_id,
        hospital_id=current_user.hospital_id
    )
    
    return {
        "message": "Lab report published successfully",
        "report_id": result["report_id"],
        "published_at": result["published_at"]
    }


@router.patch("/lab/orders/{order_id}/report/unpublish")
async def unpublish_lab_report(
    order_id: UUID,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Unpublish lab report - removes access from doctor and patient.
    
    Access Control:
    - **Who can access:** Lab Tech, Hospital Admin only
    """
    lab_service = LabService(db, current_user.hospital_id)
    
    # Unpublish report
    result = await lab_service.unpublish_report(
        order_id=order_id,
        unpublished_by=current_user.id,
        hospital_id=current_user.hospital_id
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab order or report not found"
        )
    
    return {
        "message": "Lab report unpublished successfully",
        "report_id": result["report_id"],
        "unpublished_at": result["unpublished_at"]
    }


@router.get("/lab/orders/{order_id}/report/publish-status")
async def get_report_publish_status(
    order_id: UUID,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get current publish status of lab report.
    
    Access Control:
    - **Who can access:** Lab Tech, Hospital Admin only
    """
    lab_service = LabService(db, current_user.hospital_id)
    
    # Get publish status
    status_info = await lab_service.get_report_publish_status(
        order_id=order_id,
        hospital_id=current_user.hospital_id
    )
    
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab order or report not found"
        )
    
    return status_info


# ============================================================================
# SECURE SHARE LINKS ENDPOINTS (Lab Admin) (4)
# ============================================================================

@router.post("/lab/orders/{order_id}/report/share-link", response_model=ShareTokenResponse)
async def create_report_share_link(
    order_id: UUID,
    request: ShareTokenCreateRequest,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create secure share link for lab report.
    
    Access Control:
    - **Who can access:** Lab Tech, Hospital Admin only
    """
    lab_service = LabService(db, current_user.hospital_id)
    
    # Create share token
    share_token = await lab_service.create_share_token(
        order_id=order_id,
        viewer_type=request.viewer_type,
        expires_hours=request.expires_hours,
        specific_user_id=request.specific_user_id,
        created_by=current_user.id,
        hospital_id=current_user.hospital_id
    )
    
    if not share_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab order or report not found"
        )
    
    return share_token


@router.get("/lab/report-share/{token}")
async def access_shared_report(
    token: str,
    db: AsyncSession = Depends(get_db_session),
    request: Request = None
):
    """
    Access reports via share token (public - no auth required).
    
    Access Control:
    - **Who can access:** Anyone with valid share token (token validates access)
    """
    lab_service = LabService(db, None)  # No hospital_id needed for token validation
    
    # Validate token and get report access
    report_access = await lab_service.validate_share_token(
        token=token,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    
    if not report_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired share link"
        )
    
    return report_access


@router.post("/lab/report-share/{token}/verify-otp")
async def verify_share_token_otp(
    token: str,
    otp_code: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Optional OTP verification for extra security on share tokens.
    
    Access Control:
    - **Who can access:** Anyone with valid share token
    """
    lab_service = LabService(db, None)  # No hospital_id needed for OTP verification
    
    # Verify OTP (if implemented)
    result = await lab_service.verify_share_token_otp(
        token=token,
        otp_code=otp_code
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code"
        )
    
    return {"message": "OTP verified successfully", "access_granted": True}


@router.patch("/lab/report-share/{token}/revoke")
async def revoke_share_token(
    token: str,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Revoke share token - disables access via the share link.
    
    Access Control:
    - **Who can access:** Lab Tech, Hospital Admin only
    """
    lab_service = LabService(db, current_user.hospital_id)
    
    # Revoke token
    result = await lab_service.revoke_share_token(
        token=token,
        revoked_by=current_user.id,
        hospital_id=current_user.hospital_id
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share token not found"
        )
    
    return {
        "message": "Share token revoked successfully",
        "revoked_at": result["revoked_at"]
    }


# ============================================================================
# NOTIFICATION ENDPOINTS (2)
# ============================================================================

@router.post("/notifications/lab-report-ready/{order_id}", response_model=NotificationResponse)
async def create_lab_report_notification(
    order_id: UUID,
    request: NotificationCreateRequest,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create notification for lab report ready event.
    
    Access Control:
    - **Who can access:** Lab Tech, Hospital Admin only
    """
    lab_service = LabService(db, current_user.hospital_id)
    
    # Create notification
    notification = await lab_service.create_notification(
        event_type=NotificationEventType.LAB_REPORT_READY,
        event_id=str(order_id),
        recipient_type=request.recipient_type,
        recipient_id=request.recipient_id,
        title=request.title,
        message=request.message,
        channel=request.channel,
        payload=request.payload,
        hospital_id=current_user.hospital_id,
        scheduled_at=request.scheduled_at
    )
    
    return notification


@router.get("/notifications/status", response_model=NotificationStatusResponse)
async def get_notification_status(
    order_id: str = Query(..., description="Lab order ID to check notifications for"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Check notification status for a lab order.
    
    Access Control:
    - **Who can access:** Authenticated users (hospital-scoped)
    """
    lab_service = LabService(db, current_user.hospital_id)
    
    # Get notification status
    status_info = await lab_service.get_notification_status(
        order_id=order_id,
        hospital_id=current_user.hospital_id
    )
    
    return status_info