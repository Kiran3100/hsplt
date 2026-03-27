"""
Lab Audit & Compliance API - Analytics + Audit Trail + NABL/CAP Compliance
Provides comprehensive audit trail, chain of custody, compliance exports, and analytics.
"""
import csv
import io
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc
from uuid import UUID

from app.database.session import get_db_session
from app.core.security import get_current_user, require_roles
from app.core.enums import (
    UserRole, AuditEntityType, AuditAction, ExportFormat, AnalyticsGroupBy,
    LabOrderStatus, SampleStatus, ResultStatus, QCStatus
)
from app.models.user import User
from app.models.lab import (
    LabAuditLog, ChainOfCustody, ComplianceExport, LabOrder, Sample, TestResult,
    QCRun, Equipment, LabReport
)
from app.schemas.lab import (
    AuditLogResponse, AuditLogListResponse, ChainOfCustodyResponse, SampleTraceResponse,
    ComplianceExportRequest, ComplianceExportResponse, AnalyticsTATResponse,
    AnalyticsVolumeResponse, AnalyticsQCResponse, AnalyticsEquipmentResponse
)
from app.services.lab_service import LabService

router = APIRouter(prefix="/lab/audit", tags=["Lab - Audit & Compliance"])

# ============================================================================
# AUDIT & TRACEABILITY ENDPOINTS (6)
# ============================================================================

@router.get("/lab/audit/logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[str] = Query(None, description="Filter by specific entity ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    from_date: Optional[datetime] = Query(None, description="Filter from date"),
    to_date: Optional[datetime] = Query(None, description="Filter to date"),
    performed_by: Optional[UUID] = Query(None, description="Filter by user"),
    is_critical: Optional[bool] = Query(None, description="Filter critical actions only"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=1000, description="Items per page"),
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get audit logs with filtering and pagination.
    Provides comprehensive audit trail for compliance.
    """
    lab_service = LabService(db, current_user.hospital_id)
    
    # Build query conditions
    conditions = [LabAuditLog.hospital_id == current_user.hospital_id]
    
    if entity_type:
        conditions.append(LabAuditLog.entity_type == entity_type)
    if entity_id:
        conditions.append(LabAuditLog.entity_id == entity_id)
    if action:
        conditions.append(LabAuditLog.action == action)
    if from_date:
        conditions.append(LabAuditLog.performed_at >= from_date)
    if to_date:
        conditions.append(LabAuditLog.performed_at <= to_date)
    if performed_by:
        conditions.append(LabAuditLog.performed_by == performed_by)
    if is_critical is not None:
        conditions.append(LabAuditLog.is_critical == is_critical)
    
    # Get total count
    count_query = select(func.count(LabAuditLog.id)).where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results with user names
    offset = (page - 1) * limit
    audit_query = (
        select(LabAuditLog, User.full_name)
        .outerjoin(User, LabAuditLog.performed_by == User.id)
        .where(and_(*conditions))
        .order_by(desc(LabAuditLog.performed_at))
        .offset(offset)
        .limit(limit)
    )
    
    audit_result = await db.execute(audit_query)
    audit_data = audit_result.fetchall()
    
    # Format response
    audit_logs = []
    critical_count = 0
    
    for audit_log, user_name in audit_data:
        if audit_log.is_critical:
            critical_count += 1
            
        audit_logs.append(AuditLogResponse(
            audit_id=audit_log.id,
            entity_type=audit_log.entity_type,
            entity_id=audit_log.entity_id,
            action=audit_log.action,
            performed_by=audit_log.performed_by,
            performed_at=audit_log.performed_at,
            old_value=audit_log.old_value,
            new_value=audit_log.new_value,
            ip_address=audit_log.ip_address,
            user_agent=audit_log.user_agent,
            remarks=audit_log.remarks,
            reference_id=audit_log.reference_id,
            is_critical=audit_log.is_critical,
            requires_approval=audit_log.requires_approval,
            performed_by_name=user_name
        ))
    
    return AuditLogListResponse(
        audit_logs=audit_logs,
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        },
        summary={
            "total_actions": total,
            "critical_actions": critical_count,
            "date_range": f"{from_date or 'All'} to {to_date or 'All'}"
        }
    )


@router.get("/lab/audit/logs/{audit_id}", response_model=AuditLogResponse)
async def get_audit_log_detail(
    audit_id: UUID,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """Get detailed audit log entry."""
    # Get audit log with user name
    audit_query = (
        select(LabAuditLog, User.full_name)
        .outerjoin(User, LabAuditLog.performed_by == User.id)
        .where(
            and_(
                LabAuditLog.id == audit_id,
                LabAuditLog.hospital_id == current_user.hospital_id
            )
        )
    )
    
    audit_result = await db.execute(audit_query)
    audit_data = audit_result.first()
    
    if not audit_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log entry not found"
        )
    
    audit_log, user_name = audit_data
    
    return AuditLogResponse(
        audit_id=audit_log.id,
        entity_type=audit_log.entity_type,
        entity_id=audit_log.entity_id,
        action=audit_log.action,
        performed_by=audit_log.performed_by,
        performed_at=audit_log.performed_at,
        old_value=audit_log.old_value,
        new_value=audit_log.new_value,
        ip_address=audit_log.ip_address,
        user_agent=audit_log.user_agent,
        remarks=audit_log.remarks,
        reference_id=audit_log.reference_id,
        is_critical=audit_log.is_critical,
        requires_approval=audit_log.requires_approval,
        performed_by_name=user_name
    )


@router.get("/lab/audit/entity/{entity_type}/{entity_id}", response_model=AuditLogListResponse)
async def get_entity_audit_trail(
    entity_type: str,
    entity_id: str,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """Get complete audit trail for a specific entity."""
    # Get all audit logs for the entity
    audit_query = (
        select(LabAuditLog, User.full_name)
        .outerjoin(User, LabAuditLog.performed_by == User.id)
        .where(
            and_(
                LabAuditLog.hospital_id == current_user.hospital_id,
                LabAuditLog.entity_type == entity_type,
                LabAuditLog.entity_id == entity_id
            )
        )
        .order_by(desc(LabAuditLog.performed_at))
    )
    
    audit_result = await db.execute(audit_query)
    audit_data = audit_result.fetchall()
    
    # Format response
    audit_logs = []
    critical_count = 0
    
    for audit_log, user_name in audit_data:
        if audit_log.is_critical:
            critical_count += 1
            
        audit_logs.append(AuditLogResponse(
            audit_id=audit_log.id,
            entity_type=audit_log.entity_type,
            entity_id=audit_log.entity_id,
            action=audit_log.action,
            performed_by=audit_log.performed_by,
            performed_at=audit_log.performed_at,
            old_value=audit_log.old_value,
            new_value=audit_log.new_value,
            ip_address=audit_log.ip_address,
            user_agent=audit_log.user_agent,
            remarks=audit_log.remarks,
            reference_id=audit_log.reference_id,
            is_critical=audit_log.is_critical,
            requires_approval=audit_log.requires_approval,
            performed_by_name=user_name
        ))
    
    return AuditLogListResponse(
        audit_logs=audit_logs,
        pagination={
            "page": 1,
            "limit": len(audit_logs),
            "total": len(audit_logs),
            "pages": 1
        },
        summary={
            "total_actions": len(audit_logs),
            "critical_actions": critical_count,
            "entity": f"{entity_type}:{entity_id}"
        }
    )


@router.get("/lab/samples/{sample_id}/trace", response_model=SampleTraceResponse)
async def get_sample_trace(
    sample_id: UUID,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get complete traceability for a sample.
    Shows chain of custody, test results, and audit trail.
    """
    lab_service = LabService(db, current_user.hospital_id)
    
    # Get sample details
    sample_query = (
        select(Sample, LabOrder)
        .join(LabOrder, Sample.lab_order_id == LabOrder.id)
        .where(
            and_(
                Sample.id == sample_id,
                Sample.hospital_id == current_user.hospital_id
            )
        )
    )
    
    sample_result = await db.execute(sample_query)
    sample_data = sample_result.first()
    
    if not sample_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found"
        )
    
    sample, lab_order = sample_data
    
    # Get chain of custody
    custody_query = (
        select(ChainOfCustody, User.full_name.label("from_user_name"), 
               User.full_name.label("to_user_name"), Equipment.name.label("equipment_name"))
        .outerjoin(User, ChainOfCustody.from_user == User.id)
        .outerjoin(User, ChainOfCustody.to_user == User.id)
        .outerjoin(Equipment, ChainOfCustody.equipment_id == Equipment.id)
        .where(ChainOfCustody.sample_id == sample_id)
        .order_by(ChainOfCustody.event_timestamp)
    )
    
    custody_result = await db.execute(custody_query)
    custody_data = custody_result.fetchall()
    
    custody_chain = []
    for custody, from_user_name, to_user_name, equipment_name in custody_data:
        custody_chain.append(ChainOfCustodyResponse(
            custody_id=custody.id,
            sample_id=custody.sample_id,
            sample_no=custody.sample_no,
            event_type=custody.event_type,
            event_timestamp=custody.event_timestamp,
            from_user=custody.from_user,
            to_user=custody.to_user,
            from_location=custody.from_location,
            to_location=custody.to_location,
            equipment_id=custody.equipment_id,
            temperature=custody.temperature,
            humidity=custody.humidity,
            remarks=custody.remarks,
            condition_on_receipt=custody.condition_on_receipt,
            from_user_name=from_user_name,
            to_user_name=to_user_name,
            equipment_name=equipment_name
        ))
    
    # Get test results (simplified)
    test_results = []  # Would populate with actual test results
    
    # Get audit trail for this sample
    audit_trail = []  # Would populate with audit logs
    
    return SampleTraceResponse(
        sample_id=sample.id,
        sample_no=sample.sample_no,
        patient_id=sample.patient_id,
        lab_order_no=lab_order.lab_order_no,
        sample_type=sample.sample_type,
        created_at=sample.created_at,
        current_status=sample.status,
        current_location=custody_chain[-1].to_location if custody_chain else "UNKNOWN",
        custody_chain=custody_chain,
        test_results=test_results,
        audit_trail=audit_trail
    )


@router.get("/lab/results/{result_id}/history", response_model=AuditLogListResponse)
async def get_result_history(
    result_id: UUID,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """Get complete edit history for a test result."""
    return await get_entity_audit_trail("RESULT", str(result_id), current_user, db)


@router.get("/lab/reports/{report_id}/history", response_model=AuditLogListResponse)
async def get_report_history(
    report_id: UUID,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """Get complete history for a lab report."""
    return await get_entity_audit_trail("REPORT", str(report_id), current_user, db)


# ============================================================================
# COMPLIANCE EXPORTS ENDPOINTS (5)
# ============================================================================

@router.post("/lab/exports/qc", response_model=ComplianceExportResponse)
async def export_qc_logs(
    request: ComplianceExportRequest,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """Export QC logs for compliance audit."""
    lab_service = LabService(db, current_user.hospital_id)
    
    # Create export record
    export_record = await lab_service.create_compliance_export(
        export_type="QC_LOGS",
        export_format=request.export_format,
        from_date=request.from_date,
        to_date=request.to_date,
        filters=request.filters,
        exported_by=current_user.id,
        export_reason=request.export_reason
    )
    
    return export_record


@router.post("/lab/exports/sample-rejections", response_model=ComplianceExportResponse)
async def export_sample_rejections(
    request: ComplianceExportRequest,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """Export sample rejection logs for compliance audit."""
    lab_service = LabService(db, current_user.hospital_id)
    
    export_record = await lab_service.create_compliance_export(
        export_type="SAMPLE_REJECTIONS",
        export_format=request.export_format,
        from_date=request.from_date,
        to_date=request.to_date,
        filters=request.filters,
        exported_by=current_user.id,
        export_reason=request.export_reason
    )
    
    return export_record


@router.post("/lab/exports/result-changes", response_model=ComplianceExportResponse)
async def export_result_changes(
    request: ComplianceExportRequest,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """Export result modification history for compliance audit."""
    lab_service = LabService(db, current_user.hospital_id)
    
    export_record = await lab_service.create_compliance_export(
        export_type="RESULT_CHANGES",
        export_format=request.export_format,
        from_date=request.from_date,
        to_date=request.to_date,
        filters=request.filters,
        exported_by=current_user.id,
        export_reason=request.export_reason
    )
    
    return export_record


@router.post("/lab/exports/equipment-calibration", response_model=ComplianceExportResponse)
async def export_equipment_calibration(
    request: ComplianceExportRequest,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """Export equipment calibration logs for compliance audit."""
    lab_service = LabService(db, current_user.hospital_id)
    
    export_record = await lab_service.create_compliance_export(
        export_type="EQUIPMENT_CALIBRATION",
        export_format=request.export_format,
        from_date=request.from_date,
        to_date=request.to_date,
        filters=request.filters,
        exported_by=current_user.id,
        export_reason=request.export_reason
    )
    
    return export_record


@router.post("/lab/exports/orders-summary", response_model=ComplianceExportResponse)
async def export_orders_summary(
    request: ComplianceExportRequest,
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """Export lab orders summary for compliance audit."""
    lab_service = LabService(db, current_user.hospital_id)
    
    export_record = await lab_service.create_compliance_export(
        export_type="ORDERS_SUMMARY",
        export_format=request.export_format,
        from_date=request.from_date,
        to_date=request.to_date,
        filters=request.filters,
        exported_by=current_user.id,
        export_reason=request.export_reason
    )
    
    return export_record


# ============================================================================
# ANALYTICS / KPIs ENDPOINTS (4)
# ============================================================================

@router.get("/lab/analytics/tat", response_model=AnalyticsTATResponse)
async def get_turnaround_time_analytics(
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    test_code: Optional[str] = Query(None, description="Filter by test code"),
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """Get turnaround time analytics for lab performance monitoring."""
    lab_service = LabService(db, current_user.hospital_id)
    
    analytics = await lab_service.get_tat_analytics(
        from_date=from_date,
        to_date=to_date,
        test_code=test_code
    )
    
    return analytics


@router.get("/lab/analytics/volume", response_model=AnalyticsVolumeResponse)
async def get_volume_analytics(
    group_by: str = Query("DAY", description="Group by: DAY, WEEK, MONTH, TEST, SECTION"),
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """Get test volume analytics and trends."""
    lab_service = LabService(db, current_user.hospital_id)
    
    analytics = await lab_service.get_volume_analytics(
        group_by=group_by,
        from_date=from_date,
        to_date=to_date
    )
    
    return analytics


@router.get("/lab/analytics/qc-failure-rate", response_model=AnalyticsQCResponse)
async def get_qc_failure_analytics(
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    section: Optional[str] = Query(None, description="Filter by lab section"),
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """Get QC failure rate analytics for quality monitoring."""
    lab_service = LabService(db, current_user.hospital_id)
    
    analytics = await lab_service.get_qc_failure_analytics(
        from_date=from_date,
        to_date=to_date,
        section=section
    )
    
    return analytics


@router.get("/lab/analytics/equipment-uptime", response_model=AnalyticsEquipmentResponse)
async def get_equipment_uptime_analytics(
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    equipment_id: Optional[UUID] = Query(None, description="Filter by equipment"),
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """Get equipment uptime and maintenance analytics."""
    lab_service = LabService(db, current_user.hospital_id)
    
    analytics = await lab_service.get_equipment_uptime_analytics(
        from_date=from_date,
        to_date=to_date,
        equipment_id=equipment_id
    )
    
    return analytics


@router.get("/lab/analytics/technician-productivity")
async def get_technician_productivity_analytics(
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """Get technician productivity (results entered per technician)."""
    lab_service = LabService(db, current_user.hospital_id)
    return await lab_service.get_technician_productivity_analytics(
        from_date=from_date,
        to_date=to_date
    )


@router.get("/lab/analytics/dashboard-summary")
async def get_lab_dashboard_summary(
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    current_user: User = Depends(require_roles([UserRole.LAB_TECH, UserRole.HOSPITAL_ADMIN])),
    db: AsyncSession = Depends(get_db_session)
):
    """Get aggregated lab dashboard summary (TAT, volume, QC, equipment, productivity)."""
    lab_service = LabService(db, current_user.hospital_id)
    return await lab_service.get_lab_dashboard_summary(
        from_date=from_date,
        to_date=to_date
    )