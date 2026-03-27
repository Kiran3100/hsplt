"""
Nurse Management API
Nurse-specific functionality for patient care, vitals, and nursing notes.
BUSINESS RULES:
- Nurses are created by Hospital Admin only
- Nurses belong to one hospital AND one department
- Nurses can ONLY access patients in their assigned department
- Nurses CAN: View patient profiles, Update vitals, Upload reports, Add nursing notes
- Nurses CANNOT: Book appointments, Modify appointments, Prescribe medicines, Access billing/admin data
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models.user import User
from app.services.nursing_service import NursingService
from app.schemas.clinical import (
    VitalSignsUpdate, NursingNoteCreate
)
from app.core.response_utils import success_response

router = APIRouter(prefix="/nurse-management", tags=["Staff Management - Nursing Operations"])


# ============================================================================
# PATIENT PROFILE MANAGEMENT (NURSE ACCESS)
# ============================================================================

@router.get("/patients")
async def get_patients_list(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get list of patients for nursing care in nurse's assigned department.
    
    Access Control:
    - **Who can access:** Nurses only (patients in assigned department)
    """
    nursing_service = NursingService(db)
    filters = {
        "page": page,
        "limit": limit,
        "search": search
    }
    result = await nursing_service.get_patients_list(filters, current_user)
    return success_response(message="Operation completed successfully", data=result)


@router.get("/patients/{patient_ref}")
async def get_patient_profile(
    patient_ref: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get detailed patient profile for nursing care.
    
    Access Control:
    - **Who can access:** Nurses only (patients in assigned department)
    """
    nursing_service = NursingService(db)
    result = await nursing_service.get_patient_profile(patient_ref, current_user)
    return success_response(message="Operation completed successfully", data=result)


# ============================================================================
# VITAL SIGNS MANAGEMENT
# ============================================================================

@router.post("/patients/{patient_ref}/vitals")
async def update_patient_vitals(
    patient_ref: str,
    vitals_data: VitalSignsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update patient vital signs.
    
    Access Control:
    - **Who can access:** Nurses only (patients in assigned department)
    """
    nursing_service = NursingService(db)
    result = await nursing_service.update_patient_vitals(patient_ref, vitals_data.dict(), current_user)
    return success_response(message="Operation completed successfully", data=result)


@router.get("/patients/{patient_ref}/vitals/history")
async def get_patient_vitals_history(
    patient_ref: str,
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get patient vital signs history.
    
    Access Control:
    - **Who can access:** Nurses only (patients in assigned department)
    """
    nursing_service = NursingService(db)
    result = await nursing_service.get_patient_vitals_history(patient_ref, days, current_user)
    return success_response(message="Operation completed successfully", data=result)


# ============================================================================
# NURSING NOTES MANAGEMENT
# ============================================================================

@router.post("/patients/{patient_ref}/nursing-notes")
async def add_nursing_note(
    patient_ref: str,
    note_data: NursingNoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Add nursing note for patient.
    
    Access Control:
    - **Who can access:** Nurses only (patients in assigned department)
    """
    nursing_service = NursingService(db)
    result = await nursing_service.add_nursing_note(patient_ref, note_data.dict(), current_user)
    return success_response(message="Operation completed successfully", data=result)


@router.get("/patients/{patient_ref}/nursing-notes")
async def get_nursing_notes(
    patient_ref: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    note_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get nursing notes for patient.
    
    Access Control:
    - **Who can access:** Nurses only (patients in assigned department)
    """
    nursing_service = NursingService(db)
    filters = {
        "page": page,
        "limit": limit,
        "note_type": note_type
    }
    result = await nursing_service.get_nursing_notes(patient_ref, filters, current_user)
    return success_response(message="Operation completed successfully", data=result)


# ============================================================================
# DOCUMENT UPLOAD (NURSE REPORTS)
# ============================================================================

@router.post("/patients/{patient_ref}/reports/upload")
async def upload_nursing_report(
    patient_ref: str,
    file: UploadFile = File(...),
    report_type: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Upload nursing report for patient.
    
    Access Control:
    - Only Nurses can upload reports
    """
    from fastapi import HTTPException, status
    import os
    import uuid
    
    nursing_service = NursingService(db)
    
    # Validate report type
    allowed_report_types = ["NURSING_ASSESSMENT", "CARE_PLAN", "PROGRESS_NOTE", "INCIDENT_REPORT"]
    if report_type not in allowed_report_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report type. Allowed types: {allowed_report_types}"
        )
    
    # Use the document storage functionality
    from app.api.v1.routers.patient.patient_document_storage import validate_file_type, validate_file_size, get_upload_directory, save_uploaded_file
    
    # Validate file
    if not validate_file_type(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type"
        )
    
    if not validate_file_size(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds limit"
        )
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Get upload directory
    user_context = nursing_service.get_user_context(current_user)
    upload_dir = get_upload_directory(user_context["hospital_id"], patient_ref)
    file_path = os.path.join(upload_dir, unique_filename)
    
    try:
        # Save file
        file_size = await save_uploaded_file(file, file_path)
        
        # Prepare file data for service
        file_data = {
            "report_type": report_type,
            "title": title,
            "description": description,
            "file_name": file.filename or unique_filename,
            "file_path": file_path,
            "file_size": file_size,
            "mime_type": file.content_type
        }
        
        result = await nursing_service.upload_nursing_report(patient_ref, file_data, current_user)
        return success_response(message="Operation completed successfully", data=result)
        
    except Exception as e:
        # Clean up file if database operation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload report: {str(e)}"
        )


# ============================================================================
# NURSE DASHBOARD
# ============================================================================

@router.get("/dashboard")
async def get_nurse_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get nurse dashboard with key metrics and information.
    
    Access Control:
    - Only Nurses can access dashboard
    - Shows only department-specific data
    """
    nursing_service = NursingService(db)
    result = await nursing_service.get_nurse_dashboard(current_user)
    return success_response(message="Operation completed successfully", data=result)



# ============================================================================
# NEW FEATURE 1: MEDICATION ADMINISTRATION TRACKING
# ============================================================================

from pydantic import BaseModel, Field
from datetime import datetime

class MedicationAdministration(BaseModel):
    prescription_id: str
    medicine_name: str
    dosage: str
    route: str = Field(..., description="ORAL, IV, IM, SC, etc.")
    administered_at: Optional[str] = None
    notes: Optional[str] = None
    patient_response: Optional[str] = None


@router.post("/patients/{patient_ref}/medication-administration")
async def record_medication_administration(
    patient_ref: str,
    med_data: MedicationAdministration,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Record medication administration for a patient.
    
    Access Control:
    - Only Nurses can record medication administration
    - Nurses can only record for patients in their assigned department
    
    Workflow:
    1. Verify prescription exists
    2. Record administration time
    3. Note patient response
    4. Update medication log
    """
    nursing_service = NursingService(db)
    result = await nursing_service.record_medication_administration(
        patient_ref, 
        med_data.dict(), 
        current_user
    )
    return success_response(
        message="Medication administration recorded successfully", 
        data=result
    )


@router.get("/patients/{patient_ref}/medication-administration/history")
async def get_medication_administration_history(
    patient_ref: str,
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get medication administration history for a patient.
    
    Shows all medications administered by nurses in the last N days.
    """
    nursing_service = NursingService(db)
    result = await nursing_service.get_medication_administration_history(
        patient_ref, 
        days, 
        current_user
    )
    return success_response(
        message="Medication history retrieved successfully", 
        data=result
    )


# ============================================================================
# NEW FEATURE 2: DOCTOR ORDERS INTEGRATION
# ============================================================================

@router.get("/orders/pending")
async def get_pending_doctor_orders(
    ward: Optional[str] = Query(None, description="Filter by ward"),
    priority: Optional[str] = Query(None, description="ROUTINE, URGENT, STAT"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get all pending doctor orders for nurse's department.
    
    Access Control:
    - Only Nurses can view orders
    - Shows orders for patients in nurse's assigned department
    
    Returns:
    - Medication orders
    - Lab test orders
    - Procedure orders
    - Diet orders
    - Activity orders
    """
    nursing_service = NursingService(db)
    filters = {
        "ward": ward,
        "priority": priority,
        "page": page,
        "limit": limit
    }
    result = await nursing_service.get_pending_doctor_orders(filters, current_user)
    return success_response(
        message="Pending orders retrieved successfully", 
        data=result
    )


@router.post("/orders/{order_id}/execute")
async def execute_doctor_order(
    order_id: str,
    execution_notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Mark a doctor order as executed.
    
    Access Control:
    - Only Nurses can execute orders
    - Nurses can only execute orders in their assigned department
    
    Workflow:
    1. Verify order exists and is pending
    2. Mark as executed
    3. Record execution time and nurse
    4. Add execution notes
    """
    nursing_service = NursingService(db)
    result = await nursing_service.execute_doctor_order(
        order_id, 
        execution_notes, 
        current_user
    )
    return success_response(
        message="Doctor order executed successfully", 
        data=result
    )


@router.get("/orders/my-executed")
async def get_my_executed_orders(
    date_from: Optional[str] = Query(None, pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    date_to: Optional[str] = Query(None, pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get orders executed by the current nurse.
    
    Useful for shift handover and performance tracking.
    """
    nursing_service = NursingService(db)
    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "page": page,
        "limit": limit
    }
    result = await nursing_service.get_my_executed_orders(filters, current_user)
    return success_response(
        message="Executed orders retrieved successfully", 
        data=result
    )


# ============================================================================
# NEW FEATURE 3: VITALS TRENDING AND CHARTS
# ============================================================================

@router.get("/patients/{patient_ref}/vitals/trend")
async def get_vitals_trend(
    patient_ref: str,
    vital_type: str = Query(..., description="BP, PULSE, TEMP, SPO2, RR, WEIGHT"),
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get vitals trend data for charting.
    
    Access Control:
    - Only Nurses can view vitals trends
    - Nurses can only access patients in their assigned department
    
    Returns:
    - Time series data for the specified vital sign
    - Min, max, average values
    - Trend direction (improving, stable, declining)
    - Alert flags for abnormal values
    
    Useful for:
    - Creating charts/graphs
    - Identifying patterns
    - Early warning signs
    """
    nursing_service = NursingService(db)
    result = await nursing_service.get_vitals_trend(
        patient_ref, 
        vital_type, 
        days, 
        current_user
    )
    return success_response(
        message="Vitals trend retrieved successfully", 
        data=result
    )


@router.get("/patients/{patient_ref}/vitals/summary")
async def get_vitals_summary(
    patient_ref: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get comprehensive vitals summary with trends for all vital signs.
    
    Returns:
    - Latest values for all vitals
    - 24-hour trends
    - 7-day trends
    - Alert flags
    - Comparison with normal ranges
    
    Perfect for quick patient assessment.
    """
    nursing_service = NursingService(db)
    result = await nursing_service.get_vitals_summary(patient_ref, current_user)
    return success_response(
        message="Vitals summary retrieved successfully", 
        data=result
    )


@router.get("/patients/{patient_ref}/vitals/alerts")
async def get_vitals_alerts(
    patient_ref: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get active vitals alerts for a patient.
    
    Returns alerts for:
    - Abnormal vital signs
    - Rapid changes
    - Missing vitals (overdue)
    - Critical values
    
    Helps nurses prioritize patient care.
    """
    nursing_service = NursingService(db)
    result = await nursing_service.get_vitals_alerts(patient_ref, current_user)
    return success_response(
        message="Vitals alerts retrieved successfully", 
        data=result
    )


# ============================================================================
# NEW FEATURE 4: SHIFT HANDOVER
# ============================================================================

class ShiftHandover(BaseModel):
    shift_type: str = Field(..., description="MORNING, AFTERNOON, NIGHT")
    ward: str
    patients_count: int
    critical_patients: list = []
    pending_tasks: list = []
    completed_tasks: list = []
    incidents: list = []
    notes: Optional[str] = None


@router.post("/shift-handover")
async def create_shift_handover(
    handover_data: ShiftHandover,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create shift handover report.
    
    Access Control:
    - Only Nurses can create handover reports
    
    Workflow:
    1. Record shift details
    2. List critical patients
    3. Document pending tasks
    4. Note completed tasks
    5. Report any incidents
    6. Add handover notes
    """
    nursing_service = NursingService(db)
    result = await nursing_service.create_shift_handover(
        handover_data.dict(), 
        current_user
    )
    return success_response(
        message="Shift handover created successfully", 
        data=result
    )


@router.get("/shift-handover/latest")
async def get_latest_shift_handover(
    ward: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get the latest shift handover report.
    
    Useful for incoming nurses to understand current situation.
    """
    nursing_service = NursingService(db)
    result = await nursing_service.get_latest_shift_handover(ward, current_user)
    return success_response(
        message="Latest shift handover retrieved successfully", 
        data=result
    )


@router.get("/shift-handover/history")
async def get_shift_handover_history(
    days: int = Query(7, ge=1, le=30),
    ward: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get shift handover history.
    
    Useful for reviewing past shifts and identifying patterns.
    """
    nursing_service = NursingService(db)
    filters = {
        "days": days,
        "ward": ward,
        "page": page,
        "limit": limit
    }
    result = await nursing_service.get_shift_handover_history(filters, current_user)
    return success_response(
        message="Shift handover history retrieved successfully", 
        data=result
    )


# ============================================================================
# NEW FEATURE 5: WARD MANAGEMENT
# ============================================================================

@router.get("/wards/{ward_name}/patients")
async def get_ward_patients(
    ward_name: str,
    status: Optional[str] = Query(None, description="ADMITTED, CRITICAL, STABLE"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get all patients in a specific ward.
    
    Access Control:
    - Only Nurses can view ward patients
    - Nurses can only view wards in their assigned department
    
    Returns:
    - Patient list with bed assignments
    - Current status
    - Latest vitals
    - Pending orders
    - Alerts
    """
    nursing_service = NursingService(db)
    result = await nursing_service.get_ward_patients(ward_name, status, current_user)
    return success_response(
        message="Ward patients retrieved successfully", 
        data=result
    )


@router.get("/wards/overview")
async def get_wards_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get overview of all wards in nurse's department.
    
    Returns:
    - Ward names
    - Bed occupancy
    - Patient count
    - Critical patients count
    - Pending orders count
    - Staff assigned
    
    Useful for charge nurses and supervisors.
    """
    nursing_service = NursingService(db)
    result = await nursing_service.get_wards_overview(current_user)
    return success_response(
        message="Wards overview retrieved successfully", 
        data=result
    )


# ============================================================================
# NEW FEATURE 6: PATIENT CARE PLANS
# ============================================================================

class CarePlan(BaseModel):
    patient_ref: str
    diagnosis: str
    goals: list
    interventions: list
    expected_outcomes: list
    review_date: str
    notes: Optional[str] = None


@router.post("/care-plans")
async def create_care_plan(
    care_plan_data: CarePlan,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create nursing care plan for a patient.
    
    Access Control:
    - Only Nurses can create care plans
    """
    nursing_service = NursingService(db)
    result = await nursing_service.create_care_plan(
        care_plan_data.dict(), 
        current_user
    )
    return success_response(
        message="Care plan created successfully", 
        data=result
    )


@router.get("/patients/{patient_ref}/care-plans")
async def get_patient_care_plans(
    patient_ref: str,
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get care plans for a patient.
    """
    nursing_service = NursingService(db)
    result = await nursing_service.get_patient_care_plans(
        patient_ref, 
        active_only, 
        current_user
    )
    return success_response(
        message="Care plans retrieved successfully", 
        data=result
    )


@router.put("/care-plans/{care_plan_id}")
async def update_care_plan(
    care_plan_id: str,
    care_plan_data: CarePlan,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update existing care plan.
    """
    nursing_service = NursingService(db)
    result = await nursing_service.update_care_plan(
        care_plan_id, 
        care_plan_data.dict(), 
        current_user
    )
    return success_response(
        message="Care plan updated successfully", 
        data=result
    )
