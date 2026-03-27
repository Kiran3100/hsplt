"""
Lab Result Entry API Endpoints
Handles result entry, verification, release, and report generation for lab tests.
"""
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db_session
from app.models.user import User
from app.core.security import get_current_user, require_roles
from app.services.lab_service import LabService
from app.schemas.lab import (
    ResultCreateRequest, ResultVerifyRequest, ResultReleaseRequest, ResultRejectRequest,
    ResultApproveRequest,
    TestResultResponse, WorklistResponse, ReportGenerateRequest, LabReportResponse,
    ReportHistoryResponse, MessageResponse
)
from app.core.enums import ResultStatus, SampleStatus, LabOrderPriority

# Create router with prefix and tags
router = APIRouter(
    prefix="/lab/result-entry",
    tags=["Lab - Result Entry"],
    responses={404: {"description": "Not found"}}
)


@router.post("/results/{order_item_id}", response_model=TestResultResponse)
async def create_result(
    order_item_id: uuid.UUID,
    result_data: ResultCreateRequest,
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create or update test result for an order item.
    
    **Accepts either:**
    - **Order item ID** in path (when you have the specific order item UUID)
    - **Order ID** in path (when you only have order ID) – body must include test_id
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    **Business Rules:**
    - Sample must be IN_PROCESS status
    - Can create new result or update existing DRAFT/REJECTED result
    - Result is saved as DRAFT status initially
    - All parameter values are required
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        result = await lab_service.create_result(
            order_item_id=order_item_id,
            result_data=result_data.model_dump(),
            entered_by=str(current_user.id)
        )
        
        # Get the full result details to return
        result_details = await lab_service.get_result_by_id(result["result_id"])
        
        return TestResultResponse(**result_details)
        
    except HTTPException as he:
        # If order item not found, try treating path ID as order_id (user has order_id, not order_item_id)
        if he.status_code == status.HTTP_404_NOT_FOUND and he.detail:
            detail = he.detail if isinstance(he.detail, dict) else {}
            if detail.get("code") == "ORDER_ITEM_NOT_FOUND" and result_data.test_id:
                try:
                    result = await lab_service.create_result_for_order(
                        order_id=order_item_id,
                        test_id=result_data.test_id,
                        result_data=result_data.model_dump(),
                        entered_by=str(current_user.id)
                    )
                    result_details = await lab_service.get_result_by_id(result["result_id"])
                    return TestResultResponse(**result_details)
                except HTTPException:
                    raise
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "RESULT_CREATION_FAILED",
                "message": f"Failed to create result: {str(e)}"
            }
        )


@router.get("/results/{result_id}", response_model=TestResultResponse)
async def get_result(
    result_id: uuid.UUID,
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get test result details by ID.
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    Returns complete result information including all parameter values.
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        result = await lab_service.get_result_by_id(result_id)
        
        return TestResultResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "RESULT_FETCH_FAILED",
                "message": f"Failed to fetch result: {str(e)}"
            }
        )


@router.put("/results/{result_id}", response_model=TestResultResponse)
async def update_result(
    result_id: uuid.UUID,
    result_data: ResultCreateRequest,
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update an existing test result.
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    **Business Rules:**
    - Can only update DRAFT or REJECTED results
    - Updates reset status to DRAFT
    - All verification/release data is cleared
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        # Get existing result to get order_item_id
        existing_result = await lab_service.get_result_by_id(result_id)
        
        # Update using the same create_result method (it handles updates; may create new version if approved)
        result = await lab_service.create_result(
            order_item_id=existing_result["lab_order_item_id"],
            result_data=result_data.model_dump(),
            entered_by=str(current_user.id),
        )
        
        # Return the result that was created/updated (may be new version if previous was approved)
        result_details = await lab_service.get_result_by_id(result["result_id"])
        
        return TestResultResponse(**result_details)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "RESULT_UPDATE_FAILED",
                "message": f"Failed to update result: {str(e)}"
            }
        )


@router.post("/results/{result_id}/verify", response_model=MessageResponse)
async def verify_result(
    result_id: uuid.UUID,
    verify_data: ResultVerifyRequest,
    current_user: User = Depends(require_roles(["LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Verify a test result (LAB_SUPERVISOR/LAB_ADMIN only).
    
    **Permissions:** LAB_SUPERVISOR, LAB_ADMIN
    
    **Business Rules:**
    - Can only verify DRAFT results
    - Changes status from DRAFT to VERIFIED
    - Required step before release
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        result = await lab_service.verify_result(
            result_id=result_id,
            verify_data=verify_data.model_dump(),
            verified_by=str(current_user.id),
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
                "code": "VERIFICATION_FAILED",
                "message": f"Failed to verify result: {str(e)}"
            }
        )


@router.post("/results/{result_id}/release", response_model=MessageResponse)
async def release_result(
    result_id: uuid.UUID,
    release_data: ResultReleaseRequest,
    current_user: User = Depends(require_roles(["LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Release a verified test result (LAB_SUPERVISOR/LAB_ADMIN only).
    
    **Permissions:** LAB_SUPERVISOR, LAB_ADMIN
    
    **Business Rules:**
    - Can only release VERIFIED results
    - Changes status from VERIFIED to RELEASED
    - **QC VALIDATION**: Checks QC status before release
    - Blocks release if QC is expired or failed
    - Released results can be included in reports
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        # First get the result to determine the test section
        result_details = await lab_service.get_result_by_id(result_id)
        
        # Get test details to determine section/category
        from app.models.lab import LabTest, LabOrderItem
        test_result = await db.execute(
            select(LabTest)
            .join(LabOrderItem, LabTest.id == LabOrderItem.test_id)
            .where(LabOrderItem.id == result_details["lab_order_item_id"])
        )
        test = test_result.scalar_one_or_none()
        
        if test:
            # Check QC status for the test's section
            qc_status = await lab_service.check_qc_status(
                section=test.sample_type,  # Using sample_type as section for now
                equipment_id=None  # Check section-wide QC
            )
            
            # Block release if QC is not valid
            if qc_status["blocking_release"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "QC_REQUIRED",
                        "message": f"Cannot release result: {qc_status['message']}. Valid QC required for {qc_status['section']} section.",
                        "qc_status": qc_status
                    }
                )
        
        # Proceed with result release if QC is valid
        result = await lab_service.release_result(
            result_id=result_id,
            release_data=release_data.model_dump(),
            released_by=str(current_user.id),
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
                "code": "RELEASE_FAILED",
                "message": f"Failed to release result: {str(e)}"
            }
        )


@router.post("/results/{result_id}/reject", response_model=MessageResponse)
async def reject_result(
    result_id: uuid.UUID,
    reject_data: ResultRejectRequest,
    current_user: User = Depends(require_roles(["LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Reject a test result (LAB_SUPERVISOR/LAB_ADMIN only).
    
    **Permissions:** LAB_SUPERVISOR, LAB_ADMIN
    
    **Business Rules:**
    - Can reject DRAFT or VERIFIED results
    - Changes status to REJECTED
    - Rejected results can be re-entered by LAB_TECH
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        result = await lab_service.reject_result(
            result_id=result_id,
            reject_data=reject_data.model_dump(),
            rejected_by=str(current_user.id),
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
                "code": "REJECTION_FAILED",
                "message": f"Failed to reject result: {str(e)}"
            }
        )


@router.post("/results/{result_id}/approve", response_model=MessageResponse)
async def approve_result(
    result_id: uuid.UUID,
    approval_data: ResultApproveRequest,
    current_user: User = Depends(require_roles(["PATHOLOGIST", "HOSPITAL_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Approve a test result (pathologist). Result becomes immutable; corrections create a new version.
    
    **Permissions:** PATHOLOGIST, HOSPITAL_ADMIN
    
    **Business Rules:**
    - Can approve DRAFT or VERIFIED results
    - Changes status to APPROVED
    - After approval, result cannot be edited; corrections create a new version linked via previous_result_id
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        result = await lab_service.approve_result(
            result_id=result_id,
            approval_data=approval_data.model_dump(),
            approved_by=str(current_user.id),
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
                "code": "APPROVAL_FAILED",
                "message": "Failed to approve result"
            }
        )


@router.get("/worklist", response_model=WorklistResponse)
async def get_worklist(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    sample_status: Optional[SampleStatus] = Query(None, description="Filter by sample status"),
    result_status: Optional[ResultStatus] = Query(None, description="Filter by result status"),
    priority: Optional[LabOrderPriority] = Query(None, description="Filter by order priority"),
    test_code: Optional[str] = Query(None, description="Filter by test code"),
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get worklist for lab staff showing samples ready for result entry.
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    **Features:**
    - Shows samples with IN_PROCESS status
    - Filters by result status, priority, test code
    - Sorted by priority (URGENT first) then by received time
    - Includes summary statistics
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        worklist = await lab_service.get_worklist(
            page=page,
            limit=limit,
            sample_status_filter=sample_status,
            result_status_filter=result_status,
            priority_filter=priority,
            test_code_filter=test_code
        )
        
        return WorklistResponse(**worklist)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "WORKLIST_FETCH_FAILED",
                "message": f"Failed to fetch worklist: {str(e)}"
            }
        )


@router.post("/orders/{order_id}/results", response_model=TestResultResponse)
async def create_result_for_order(
    order_id: uuid.UUID,
    result_data: ResultCreateRequest,
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create or update test result using order ID and test ID (no order item ID needed).
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    Provide order_id in the path and test_id in the body. The order item is resolved automatically.
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        result = await lab_service.create_result_for_order(
            order_id=order_id,
            test_id=result_data.test_id,
            result_data=result_data.model_dump(),
            entered_by=str(current_user.id)
        )
        result_details = await lab_service.get_result_by_id(result["result_id"])
        return TestResultResponse(**result_details)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "RESULT_CREATION_FAILED",
                "message": f"Failed to create result: {str(e)}"
            }
        )


@router.get("/orders/{order_id}/results", response_model=List[TestResultResponse])
async def get_results_for_order(
    order_id: uuid.UUID,
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get all results for a specific lab order.
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    Returns all test results associated with the order, regardless of status.
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        results = await lab_service.get_results_for_order(order_id)
        
        return [TestResultResponse(**result) for result in results]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "RESULTS_FETCH_FAILED",
                "message": f"Failed to fetch results for order: {str(e)}"
            }
        )


@router.post("/orders/{order_id}/reports", response_model=LabReportResponse)
async def generate_report(
    order_id: uuid.UUID,
    report_data: ReportGenerateRequest,
    current_user: User = Depends(require_roles(["LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Generate PDF report for a lab order.
    
    **Permissions:** LAB_SUPERVISOR, LAB_ADMIN
    
    **Business Rules:**
    - By default, only includes RELEASED results
    - Can include DRAFT results if include_draft=true
    - Generates new version if report already exists
    - Creates database record (PDF generation to be implemented)
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        report = await lab_service.generate_report(
            order_id=order_id,
            report_data=report_data.model_dump(),
            generated_by=str(current_user.id),
        )
        
        return LabReportResponse(**report)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "REPORT_GENERATION_FAILED",
                "message": f"Failed to generate report: {str(e)}"
            }
        )


@router.get("/orders/{order_id}/reports", response_model=ReportHistoryResponse)
async def get_report_history(
    order_id: uuid.UUID,
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get report generation history for an order.
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    Returns all report versions generated for the order, with latest version first.
    """
    try:
        lab_service = LabService(db, current_user.hospital_id)
        
        history = await lab_service.get_report_history(order_id)
        
        return ReportHistoryResponse(**history)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "REPORT_HISTORY_FETCH_FAILED",
                "message": f"Failed to fetch report history: {str(e)}"
            }
        )


@router.get("/reports/{report_id}", response_model=LabReportResponse)
async def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get specific report details by ID.
    
    **Permissions:** LAB_TECH, LAB_SUPERVISOR, LAB_ADMIN
    
    Returns report metadata. PDF download would be handled separately.
    """
    try:
        # This would be implemented to fetch specific report details
        # For now, return a placeholder response
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "code": "NOT_IMPLEMENTED",
                "message": "Report retrieval not yet implemented"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "REPORT_FETCH_FAILED",
                "message": f"Failed to fetch report: {str(e)}"
            }
        )