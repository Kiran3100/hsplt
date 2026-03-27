"""
Insurance claim processing.
RBAC: Hospital Admin, Receptionist.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.core.security import get_current_user
from app.api.deps import require_hospital_context, require_roles
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.billing import InsuranceClaimCreate, InsuranceClaimUpdate, InsuranceClaimResponse
from app.schemas.response import SuccessResponse
from app.repositories.billing.billing_repository import BillingRepository
from app.models.billing import InsuranceClaim
import uuid

router = APIRouter(prefix="/insurance", tags=["M1.5 Billing - Insurance Claims"])
require_billing = require_roles(UserRole.HOSPITAL_ADMIN, UserRole.RECEPTIONIST)


@router.post("/claims", response_model=dict)
async def create_claim(
    body: InsuranceClaimCreate,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Create insurance claim for a bill."""
    repo = BillingRepository(db, UUID(context["hospital_id"]))
    bill = await repo.get_bill(body.bill_id)
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "BILL_NOT_FOUND", "message": "Bill not found"})
    claim = InsuranceClaim(
        id=uuid.uuid4(),
        hospital_id=UUID(context["hospital_id"]),
        bill_id=body.bill_id,
        patient_id=body.patient_id,
        insurance_provider_name=body.insurance_provider_name,
        policy_number=body.policy_number,
        claim_amount=body.claim_amount,
        status="CREATED",
    )
    await repo.create_insurance_claim(claim)
    await db.commit()
    await db.refresh(claim)
    return SuccessResponse(success=True, message="Claim created", data=InsuranceClaimResponse.model_validate(claim).model_dump()).dict()


@router.get("/claims", response_model=dict)
async def list_claims(
    status: str | None = Query(None),
    bill_id: UUID | None = Query(None),
    patient_id: UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """List insurance claims with filters."""
    repo = BillingRepository(db, UUID(context["hospital_id"]))
    claims = await repo.list_insurance_claims(status=status, bill_id=bill_id, patient_id=patient_id, skip=skip, limit=limit)
    return SuccessResponse(success=True, message=f"Found {len(claims)} claims", data=[InsuranceClaimResponse.model_validate(c).model_dump() for c in claims]).dict()


@router.get("/claims/{claim_id}", response_model=dict)
async def get_claim(
    claim_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Get claim by ID."""
    repo = BillingRepository(db, UUID(context["hospital_id"]))
    claim = await repo.get_insurance_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CLAIM_NOT_FOUND", "message": "Claim not found"})
    return SuccessResponse(success=True, message="Claim retrieved", data=InsuranceClaimResponse.model_validate(claim).model_dump()).dict()


@router.patch("/claims/{claim_id}/status", response_model=dict)
async def update_claim_status(
    claim_id: UUID,
    body: InsuranceClaimUpdate,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Update claim status (approve/reject/settle)."""
    repo = BillingRepository(db, UUID(context["hospital_id"]))
    claim = await repo.get_insurance_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CLAIM_NOT_FOUND", "message": "Claim not found"})
    if body.status is not None:
        claim.status = body.status
    if body.approved_amount is not None:
        claim.approved_amount = body.approved_amount
    if body.rejection_reason is not None:
        claim.rejection_reason = body.rejection_reason
    if body.settlement_reference is not None:
        claim.settlement_reference = body.settlement_reference
    await db.flush()
    await db.commit()
    await db.refresh(claim)
    return SuccessResponse(success=True, message="Claim updated", data=InsuranceClaimResponse.model_validate(claim).model_dump()).dict()


@router.post("/claims/{claim_id}/record-settlement", response_model=dict)
async def record_settlement(
    claim_id: UUID,
    body: InsuranceClaimUpdate,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Record settlement (status=SETTLED, settlement_reference)."""
    repo = BillingRepository(db, UUID(context["hospital_id"]))
    claim = await repo.get_insurance_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CLAIM_NOT_FOUND", "message": "Claim not found"})
    claim.status = "SETTLED"
    if body.settlement_reference is not None:
        claim.settlement_reference = body.settlement_reference
    if body.approved_amount is not None:
        claim.approved_amount = body.approved_amount
    await db.flush()
    await db.commit()
    await db.refresh(claim)
    return SuccessResponse(success=True, message="Settlement recorded", data=InsuranceClaimResponse.model_validate(claim).model_dump()).dict()
