"""
Lab Equipment & QC Management API Endpoints
Handles equipment registration, maintenance tracking, QC rules, and QC runs.
"""
import uuid
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.models.user import User
from app.core.security import get_current_user, require_roles
from app.services.lab_service import LabService
from app.schemas.lab import (
    EquipmentCreateRequest, EquipmentUpdateRequest, EquipmentStatusUpdateRequest,
    EquipmentResponse, EquipmentListResponse, MaintenanceLogCreateRequest,
    MaintenanceLogResponse, MaintenanceLogListResponse, QCRuleCreateRequest,
    QCRuleResponse, QCRuleListResponse, QCRunCreateRequest, QCRunResponse,
    QCRunListResponse, QCStatusResponse, MessageResponse
)
from app.core.enums import EquipmentCategory, EquipmentStatus, MaintenanceType

# Create router with prefix and tags
router = APIRouter(
    prefix="/lab/equipment-qc",
    tags=["Lab - Equipment & QC"],
    responses={404: {"description": "Not found"}}
)


# ============================================================================
# EQUIPMENT MANAGEMENT ENDPOINTS (6 endpoints)
# ============================================================================

@router.post("/equipment", response_model=EquipmentResponse)
async def create_equipment(
    equipment_data: EquipmentCreateRequest,
    current_user: User = Depends(require_roles(["LAB_ADMIN", "LAB_SUPERVISOR"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new lab equipment.
    
    **Permissions:** LAB_ADMIN, LAB_SUPERVISOR
    
    **Business Rules:**
    - Equipment code must be unique within hospital
    - Equipment is created with ACTIVE status by default
    - Category must be valid lab section
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        result = await lab_service.create_equipment(equipment_data.model_dump())
        
        # Get the full equipment details to return
        equipment_details = await lab_service.get_equipment_by_id(result["equipment_id"])
        
        return EquipmentResponse(**equipment_details)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "EQUIPMENT_CREATION_FAILED",
                "message": f"Failed to create equipment: {str(e)}"
            }
        )


@router.get("/equipment", response_model=EquipmentListResponse)
async def get_equipment_list(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    category: Optional[EquipmentCategory] = Query(None, description="Filter by equipment category"),
    status: Optional[EquipmentStatus] = Query(None, description="Filter by equipment status"),
    active_only: bool = Query(True, description="Show only active equipment"),
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get paginated list of lab equipment with filtering options.
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    **Features:**
    - Filter by category (HEMATOLOGY, BIOCHEMISTRY, etc.)
    - Filter by status (ACTIVE, INACTIVE, UNDER_MAINTENANCE, DOWN)
    - Option to show only active equipment
    - Pagination support
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        equipment_list = await lab_service.get_equipment_list(
            page=page,
            limit=limit,
            category_filter=category.value if category else None,
            status_filter=status.value if status else None,
            active_only=active_only
        )
        
        return EquipmentListResponse(**equipment_list)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "EQUIPMENT_FETCH_FAILED",
                "message": f"Failed to fetch equipment list: {str(e)}"
            }
        )


@router.get("/equipment/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: uuid.UUID,
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get equipment details by ID.
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    Returns complete equipment information including specifications and maintenance history.
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        equipment = await lab_service.get_equipment_by_id(equipment_id)
        
        return EquipmentResponse(**equipment)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "EQUIPMENT_FETCH_FAILED",
                "message": f"Failed to fetch equipment: {str(e)}"
            }
        )


@router.put("/equipment/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: uuid.UUID,
    equipment_data: EquipmentUpdateRequest,
    current_user: User = Depends(require_roles(["LAB_ADMIN", "LAB_SUPERVISOR"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update equipment information.
    
    **Permissions:** LAB_ADMIN, LAB_SUPERVISOR
    
    **Business Rules:**
    - Can update equipment details, location, specifications
    - Cannot change equipment code (use for identification)
    - Status changes should use dedicated status endpoint
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        await lab_service.update_equipment(
            equipment_id=equipment_id,
            update_data=equipment_data.model_dump(exclude_unset=True),
        )
        
        # Get updated equipment details
        equipment = await lab_service.get_equipment_by_id(equipment_id)
        
        return EquipmentResponse(**equipment)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "EQUIPMENT_UPDATE_FAILED",
                "message": f"Failed to update equipment: {str(e)}"
            }
        )


@router.patch("/equipment/{equipment_id}/status", response_model=MessageResponse)
async def update_equipment_status(
    equipment_id: uuid.UUID,
    status_data: EquipmentStatusUpdateRequest,
    current_user: User = Depends(require_roles(["LAB_ADMIN", "LAB_SUPERVISOR"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update equipment status.
    
    **Permissions:** LAB_ADMIN, LAB_SUPERVISOR
    
    **Business Rules:**
    - Status changes: ACTIVE ↔ INACTIVE ↔ UNDER_MAINTENANCE ↔ DOWN
    - Status change reason should be provided
    - Equipment under maintenance or down cannot be used for QC
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        result = await lab_service.update_equipment_status(
            equipment_id=equipment_id,
            new_status=status_data.status,
            reason=status_data.reason
        )
        
        return MessageResponse(
            message=result["message"],
            status="success"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "STATUS_UPDATE_FAILED",
                "message": f"Failed to update equipment status: {str(e)}"
            }
        )


@router.get("/equipment/{equipment_id}/logs", response_model=MaintenanceLogListResponse)
async def get_equipment_logs(
    equipment_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    maintenance_type: Optional[MaintenanceType] = Query(None, description="Filter by maintenance type"),
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get maintenance logs for specific equipment.
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    **Features:**
    - Filter by maintenance type (CALIBRATION, PREVENTIVE, BREAKDOWN, etc.)
    - Chronological order (latest first)
    - Includes cost and service provider information
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        logs = await lab_service.get_maintenance_logs(
            equipment_id=equipment_id,
            page=page,
            limit=limit,
            maintenance_type=maintenance_type.value if maintenance_type else None
        )
        
        return MaintenanceLogListResponse(**logs)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "LOGS_FETCH_FAILED",
                "message": f"Failed to fetch maintenance logs: {str(e)}"
            }
        )


# ============================================================================
# MAINTENANCE LOG ENDPOINTS (3 endpoints)
# ============================================================================

@router.post("/equipment/{equipment_id}/logs", response_model=MaintenanceLogResponse)
async def create_maintenance_log(
    equipment_id: uuid.UUID,
    log_data: MaintenanceLogCreateRequest,
    current_user: User = Depends(require_roles(["LAB_ADMIN", "LAB_SUPERVISOR"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create maintenance log entry for equipment.
    
    **Permissions:** LAB_ADMIN, LAB_SUPERVISOR
    
    **Business Rules:**
    - Calibration logs update equipment's last_calibrated_at
    - Next due date is calculated based on maintenance type
    - Cost and service provider tracking for external services
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        result = await lab_service.create_maintenance_log(
            equipment_id=equipment_id,
            log_data=log_data.model_dump(),
            performed_by=str(current_user.id),
        )
        
        # Get the full log details to return
        logs = await lab_service.get_maintenance_logs(
            equipment_id=equipment_id,
            page=1,
            limit=1
        )
        
        if logs["logs"]:
            return MaintenanceLogResponse(**logs["logs"][0])
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"code": "LOG_FETCH_FAILED", "message": "Failed to fetch created log"}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "LOG_CREATION_FAILED",
                "message": f"Failed to create maintenance log: {str(e)}"
            }
        )


@router.get("/equipment/logs", response_model=MaintenanceLogListResponse)
async def get_all_maintenance_logs(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    maintenance_type: Optional[MaintenanceType] = Query(None, description="Filter by maintenance type"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get all maintenance logs across all equipment with filtering.
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    **Features:**
    - Filter by maintenance type and date range
    - Cross-equipment maintenance overview
    - Useful for maintenance scheduling and cost tracking
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        logs = await lab_service.get_maintenance_logs(
            page=page,
            limit=limit,
            maintenance_type=maintenance_type.value if maintenance_type else None,
            date_from=date_from,
            date_to=date_to
        )
        
        return MaintenanceLogListResponse(**logs)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "LOGS_FETCH_FAILED",
                "message": f"Failed to fetch maintenance logs: {str(e)}"
            }
        )


@router.get("/equipment/logs/{log_id}", response_model=MaintenanceLogResponse)
async def get_maintenance_log(
    log_id: uuid.UUID,
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get specific maintenance log details by ID.
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    Returns complete maintenance log information including attachments and costs.
    """
    try:
        # This would be implemented to fetch specific log details
        # For now, return a placeholder response
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "code": "NOT_IMPLEMENTED",
                "message": "Specific log retrieval not yet implemented"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "LOG_FETCH_FAILED",
                "message": f"Failed to fetch maintenance log: {str(e)}"
            }
        )


# ============================================================================
# QC RULE ENDPOINTS (2 endpoints)
# ============================================================================

@router.post("/qc/rules", response_model=QCRuleResponse)
async def create_qc_rule(
    rule_data: QCRuleCreateRequest,
    current_user: User = Depends(require_roles(["LAB_ADMIN", "LAB_SUPERVISOR"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create QC rule for lab section or specific test.
    
    **Permissions:** LAB_ADMIN, LAB_SUPERVISOR
    
    **Business Rules:**
    - QC rules define frequency and validity for quality control
    - Can be section-wide or test-specific
    - Min/max values define acceptable QC ranges
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        result = await lab_service.create_qc_rule(
            rule_data=rule_data.model_dump(),
            created_by=str(current_user.id),
        )
        
        # Get the full rule details to return
        rules = await lab_service.get_qc_rules(
            page=1,
            limit=1,
            section_filter=result["section"]
        )
        
        # Find the created rule
        for rule in rules["rules"]:
            if rule["rule_id"] == result["rule_id"]:
                return QCRuleResponse(**rule)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "RULE_FETCH_FAILED", "message": "Failed to fetch created rule"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "RULE_CREATION_FAILED",
                "message": f"Failed to create QC rule: {str(e)}"
            }
        )


@router.get("/qc/rules", response_model=QCRuleListResponse)
async def get_qc_rules(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    section: Optional[EquipmentCategory] = Query(None, description="Filter by lab section"),
    test_code: Optional[str] = Query(None, description="Filter by test code"),
    active_only: bool = Query(True, description="Show only active rules"),
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get QC rules with filtering options.
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    **Features:**
    - Filter by lab section and test code
    - Show frequency and validity requirements
    - Used for QC planning and compliance tracking
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        rules = await lab_service.get_qc_rules(
            page=page,
            limit=limit,
            section_filter=section.value if section else None,
            test_code_filter=test_code,
            active_only=active_only
        )
        
        return QCRuleListResponse(**rules)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "RULES_FETCH_FAILED",
                "message": f"Failed to fetch QC rules: {str(e)}"
            }
        )


# ============================================================================
# QC RUN ENDPOINTS (3 endpoints)
# ============================================================================

@router.post("/qc/runs", response_model=QCRunResponse)
async def create_qc_run(
    run_data: QCRunCreateRequest,
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create QC run entry.
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    **Business Rules:**
    - QC runs validate equipment performance
    - PASS status enables result release for validity period
    - FAIL status blocks result release until new PASS QC
    - Values are validated against QC rule ranges
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        result = await lab_service.create_qc_run(
            run_data=run_data.model_dump(),
            run_by=str(current_user.id),
        )
        
        # Get the full run details to return
        runs = await lab_service.get_qc_runs(
            page=1,
            limit=1,
            equipment_id_filter=result["equipment_id"]
        )
        
        # Find the created run
        for run in runs["runs"]:
            if run["run_id"] == result["run_id"]:
                return QCRunResponse(**run)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "RUN_FETCH_FAILED", "message": "Failed to fetch created run"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "RUN_CREATION_FAILED",
                "message": f"Failed to create QC run: {str(e)}"
            }
        )


@router.get("/qc/runs", response_model=QCRunListResponse)
async def get_qc_runs(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    section: Optional[EquipmentCategory] = Query(None, description="Filter by lab section"),
    equipment_id: Optional[uuid.UUID] = Query(None, description="Filter by equipment"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get QC runs with filtering options.
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    **Features:**
    - Filter by section, equipment, and date range
    - Shows QC history and trends
    - Includes validity status for each run
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        runs = await lab_service.get_qc_runs(
            page=page,
            limit=limit,
            section_filter=section.value if section else None,
            equipment_id_filter=equipment_id,
            date_from=date_from,
            date_to=date_to
        )
        
        return QCRunListResponse(**runs)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "RUNS_FETCH_FAILED",
                "message": f"Failed to fetch QC runs: {str(e)}"
            }
        )


@router.get("/qc/status", response_model=QCStatusResponse)
async def get_qc_status(
    section: EquipmentCategory = Query(..., description="Lab section to check"),
    equipment_id: Optional[uuid.UUID] = Query(None, description="Specific equipment (optional)"),
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Check QC status for lab section or equipment.
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    **Critical for Result Release:**
    - Returns whether QC is valid for result release
    - Shows time remaining until QC expires
    - Used by result release workflow to block/allow releases
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        qc_status = await lab_service.check_qc_status(
            section=section.value,
            equipment_id=equipment_id
        )
        
        return QCStatusResponse(**qc_status)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "QC_STATUS_CHECK_FAILED",
                "message": f"Failed to check QC status: {str(e)}"
            }
        )