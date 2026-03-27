"""
OPD/IPD bills and bill management (items, discount, finalize, cancel).
RBAC: Hospital Admin, Receptionist for billing; Doctor read-only own patients.
"""
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database.session import get_db_session
from app.models.billing import Bill
from app.models.patient import PatientProfile, Appointment, Admission
from app.models.tenant import Hospital
from app.services.billing.invoice_pdf import build_invoice_pdf
from app.core.security import get_current_user
from app.api.deps import require_hospital_context, require_roles
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.billing import (
    BillCreate, BillResponse, BillListQuery,
    BillItemCreate, BillItemResponse, BillItemUpdate,
    BillFinalize, BillDiscountApply, BillCancel, BillReopen,
)
from app.schemas.response import SuccessResponse
from app.services.billing.billing_service import BillingService
from app.core.exceptions import BusinessLogicError

router = APIRouter(prefix="/billing", tags=["M1.2 Billing - OPD & IPD Bills"])
require_billing = require_roles(UserRole.HOSPITAL_ADMIN, UserRole.RECEPTIONIST)


def _bill_to_response(bill):
    from app.schemas.billing import BillItemResponse
    items = [BillItemResponse.model_validate(i).model_dump() for i in (bill.items or [])]
    patient_ref = bill.patient.patient_id if (bill.patient_id and getattr(bill, "patient", None) and bill.patient) else None
    appointment_ref = bill.appointment.appointment_ref if (bill.appointment_id and getattr(bill, "appointment", None) and bill.appointment) else None
    admission_ref = None
    if bill.admission_id and getattr(bill, "admission", None) and bill.admission:
        admission_ref = bill.admission.admission_number
    d = {
        "id": str(bill.id),
        "hospital_id": str(bill.hospital_id),
        "bill_number": bill.bill_number,
        "bill_type": bill.bill_type,
        "patient_id": str(bill.patient_id),
        "patient_ref": patient_ref,
        "appointment_id": str(bill.appointment_id) if bill.appointment_id else None,
        "appointment_ref": appointment_ref,
        "admission_id": str(bill.admission_id) if bill.admission_id else None,
        "admission_ref": admission_ref,
        "status": bill.status,
        "subtotal": float(bill.subtotal),
        "discount_amount": float(bill.discount_amount),
        "tax_amount": float(bill.tax_amount),
        "total_amount": float(bill.total_amount),
        "amount_paid": float(bill.amount_paid),
        "balance_due": float(bill.balance_due),
        "created_by_user_id": str(bill.created_by_user_id),
        "finalized_by_user_id": str(bill.finalized_by_user_id) if bill.finalized_by_user_id else None,
        "finalized_at": bill.finalized_at.isoformat() if bill.finalized_at else None,
        "notes": bill.notes,
        "items": items,
        "created_at": bill.created_at.isoformat() if hasattr(bill, "created_at") and bill.created_at else None,
        "updated_at": bill.updated_at.isoformat() if hasattr(bill, "updated_at") and bill.updated_at else None,
    }
    return d


def _payment_to_response(p):
    """Lightweight copy of payments._payment_to_response for bill-scoped endpoints."""
    return {
        "id": str(p.id),
        "hospital_id": str(p.hospital_id),
        "bill_id": str(p.bill_id),
        "payment_ref": p.payment_ref,
        "method": p.method,
        "provider": p.provider,
        "amount": float(p.amount),
        "status": p.status,
        "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        "collected_by_user_id": str(p.collected_by_user_id),
        "gateway_transaction_id": p.gateway_transaction_id,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


class BillPaymentCollect(BaseModel):
    amount: float
    method: str
    provider: str | None = None
    idempotency_key: str
    gateway_transaction_id: str | None = None
    extra_data: dict | None = None


# ---------- OPD ----------
@router.post("/opd/bills", response_model=dict)
async def create_opd_bill(
    body: BillCreate,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create OPD bill from appointment_ref + items (or patient_ref only).
    
    Access Control:
    - **Who can access:** Hospital Admin, Receptionist
    """
    if body.bill_type != "OPD":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use bill_type OPD")
    hospital_id = UUID(context["hospital_id"])
    # Resolve appointment_ref / patient_ref to internal UUIDs
    patient_uuid: UUID | None = None
    appointment_uuid: UUID | None = None
    if body.appointment_ref:
        r = await db.execute(
            select(Appointment)
            .where(
                Appointment.appointment_ref == body.appointment_ref,
                Appointment.hospital_id == hospital_id,
            )
            .limit(1)
        )
        appt = r.scalar_one_or_none()
        if not appt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "APPOINTMENT_NOT_FOUND", "message": f"Appointment {body.appointment_ref} not found"},
            )
        appointment_uuid = appt.id
        patient_uuid = appt.patient_id
    if not patient_uuid and body.patient_ref:
        r = await db.execute(
            select(PatientProfile)
            .where(
                PatientProfile.patient_id == body.patient_ref,
                PatientProfile.hospital_id == hospital_id,
            )
            .limit(1)
        )
        patient = r.scalar_one_or_none()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PATIENT_NOT_FOUND", "message": f"Patient {body.patient_ref} not found"},
            )
        patient_uuid = patient.id
    if not patient_uuid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MISSING_PATIENT_REF", "message": "Provide appointment_ref or patient_ref"},
        )
    service = BillingService(db, hospital_id, UUID(context["user_id"]))
    items_data = [
        {
            "service_item_id": i.service_item_id,
            "description": i.description,
            "quantity": i.quantity,
            "unit_price": i.unit_price,
            "tax_percentage": i.tax_percentage,
        }
        for i in body.items
    ]
    try:
        bill = await service.create_opd_bill(patient_uuid, appointment_uuid, items_data, body.notes)
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": (e.errors or [None])[0], "message": e.message},
        )
    await db.commit()
    # Eagerly load items, patient, appointment for response (patient_ref, appointment_ref)
    result = await db.execute(
        select(Bill)
        .where(Bill.id == bill.id)
        .options(
            selectinload(Bill.items),
            selectinload(Bill.patient),
            selectinload(Bill.appointment),
            selectinload(Bill.admission),
        )
    )
    bill = result.scalar_one()
    return SuccessResponse(success=True, message="OPD bill created", data=_bill_to_response(bill)).dict()


@router.get("/opd/bills", response_model=dict)
async def list_opd_bills(
    status: str | None = Query(None),
    patient_id: UUID | None = Query(None, description="Patient profile UUID"),
    patient_ref: str | None = Query(None, description="Patient reference (e.g. PAT-001)"),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List OPD bills with pagination. Use patient_ref (e.g. PAT-001) or patient_id.
    
    Access Control:
    - **Who can access:** Hospital Admin, Receptionist
    """
    hospital_id = UUID(context["hospital_id"])
    resolved_patient_id = patient_id
    if not resolved_patient_id and patient_ref:
        r = await db.execute(
            select(PatientProfile.id).where(
                PatientProfile.patient_id == patient_ref,
                PatientProfile.hospital_id == hospital_id,
            ).limit(1)
        )
        resolved_patient_id = r.scalar_one_or_none()
    repo = BillingService(db, hospital_id, UUID(context["user_id"])).repo
    date_from_d = date.fromisoformat(date_from) if date_from else None
    date_to_d = date.fromisoformat(date_to) if date_to else None
    bills, total = await repo.list_bills(status=status, patient_id=resolved_patient_id, date_from=date_from_d, date_to=date_to_d, bill_type="OPD", skip=skip, limit=limit)
    return SuccessResponse(success=True, message=f"Found {len(bills)} OPD bills", data={"bills": [_bill_to_response(b) for b in bills], "total": total, "skip": skip, "limit": limit}).dict()


@router.get("/opd/bills/{bill_id}", response_model=dict)
async def get_opd_bill(
    bill_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get OPD bill by ID.
    
    Access Control:
    - **Who can access:** Hospital Admin, Receptionist
    """
    repo = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"])).repo
    bill = await repo.get_bill(bill_id)
    if not bill or bill.bill_type != "OPD":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "BILL_NOT_FOUND", "message": "OPD bill not found"})
    return SuccessResponse(success=True, message="OPD bill retrieved", data=_bill_to_response(bill)).dict()


# ---------- IPD ----------
@router.post("/ipd/bills", response_model=dict)
async def create_ipd_bill(
    body: BillCreate,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Create IPD bill from admission_number + items."""
    if body.bill_type != "IPD":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use bill_type IPD")
    if not body.admission_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="admission_number required for IPD")
    hospital_id = UUID(context["hospital_id"])
    # Resolve admission_number -> Admission (and patient)
    r = await db.execute(
        select(Admission)
        .where(
            Admission.admission_number == body.admission_number,
            Admission.hospital_id == hospital_id,
        )
        .limit(1)
    )
    admission = r.scalar_one_or_none()
    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ADMISSION_NOT_FOUND", "message": f"Admission {body.admission_number} not found"},
        )
    service = BillingService(db, hospital_id, UUID(context["user_id"]))
    items_data = [
        {
            "service_item_id": i.service_item_id,
            "description": i.description,
            "quantity": i.quantity,
            "unit_price": i.unit_price,
            "tax_percentage": i.tax_percentage,
        }
        for i in body.items
    ]
    try:
        bill = await service.create_ipd_bill(admission.patient_id, admission.id, items_data, body.notes)
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": (e.errors or [None])[0], "message": e.message},
        )
    await db.commit()
    # Eagerly load items, patient, admission for response (patient_ref, admission_ref)
    result = await db.execute(
        select(Bill)
        .where(Bill.id == bill.id)
        .options(
            selectinload(Bill.items),
            selectinload(Bill.patient),
            selectinload(Bill.appointment),
            selectinload(Bill.admission),
        )
    )
    bill = result.scalar_one()
    return SuccessResponse(success=True, message="IPD bill created", data=_bill_to_response(bill)).dict()


@router.get("/ipd/bills", response_model=dict)
async def list_ipd_bills(
    status: str | None = Query(None),
    patient_id: UUID | None = Query(None, description="Patient profile UUID"),
    patient_ref: str | None = Query(None, description="Patient reference (e.g. PAT-001)"),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """List IPD bills with pagination. Use patient_ref (e.g. PAT-001) or patient_id."""
    hospital_id = UUID(context["hospital_id"])
    resolved_patient_id = patient_id
    if not resolved_patient_id and patient_ref:
        r = await db.execute(
            select(PatientProfile.id).where(
                PatientProfile.patient_id == patient_ref,
                PatientProfile.hospital_id == hospital_id,
            ).limit(1)
        )
        resolved_patient_id = r.scalar_one_or_none()
    repo = BillingService(db, hospital_id, UUID(context["user_id"])).repo
    date_from_d = date.fromisoformat(date_from) if date_from else None
    date_to_d = date.fromisoformat(date_to) if date_to else None
    bills, total = await repo.list_bills(status=status, patient_id=resolved_patient_id, date_from=date_from_d, date_to=date_to_d, bill_type="IPD", skip=skip, limit=limit)
    return SuccessResponse(success=True, message=f"Found {len(bills)} IPD bills", data={"bills": [_bill_to_response(b) for b in bills], "total": total, "skip": skip, "limit": limit}).dict()


@router.get("/ipd/bills/{bill_id}", response_model=dict)
async def get_ipd_bill(
    bill_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Get IPD bill by ID."""
    repo = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"])).repo
    bill = await repo.get_bill(bill_id)
    if not bill or bill.bill_type != "IPD":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "BILL_NOT_FOUND", "message": "IPD bill not found"})
    return SuccessResponse(success=True, message="IPD bill retrieved", data=_bill_to_response(bill)).dict()


class RunDailyBedChargesBody(BaseModel):
    from_date: str  # YYYY-MM-DD
    to_date: str
    bed_rate_per_day: float


@router.post("/ipd/bills/{bill_id}/run-daily-bed-charges", response_model=dict)
async def run_daily_bed_charges(
    bill_id: UUID,
    body: RunDailyBedChargesBody,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Run daily bed charges for IPD bill for date range."""
    service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    from_d = date.fromisoformat(body.from_date)
    to_d = date.fromisoformat(body.to_date)
    try:
        added = await service.run_ipd_daily_bed_charges(bill_id, from_d, to_d, body.bed_rate_per_day)
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": (e.errors or [None])[0], "message": e.message})
    await db.commit()
    return SuccessResponse(success=True, message=f"Added {added} bed charge(s)", data={"charges_added": added}).dict()


# ---------- Bill management (common) ----------
@router.post("/bills/{bill_id}/items", response_model=dict)
async def add_bill_items(
    bill_id: UUID,
    body: list[BillItemCreate],
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Add line items to DRAFT bill."""
    service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    items_data = [{"service_item_id": i.service_item_id, "description": i.description, "quantity": i.quantity, "unit_price": i.unit_price, "tax_percentage": i.tax_percentage} for i in body]
    try:
        bill = await service.add_bill_items(bill_id, items_data)
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": (e.errors or [None])[0], "message": e.message})
    await db.commit()
    # Eagerly load items, patient, appointment, admission for response
    result = await db.execute(
        select(Bill)
        .where(Bill.id == bill.id)
        .options(
            selectinload(Bill.items),
            selectinload(Bill.patient),
            selectinload(Bill.appointment),
            selectinload(Bill.admission),
        )
    )
    bill = result.scalar_one()
    return SuccessResponse(success=True, message="Items added", data=_bill_to_response(bill)).dict()


@router.get("/bills/{bill_id}/items", response_model=dict)
async def list_bill_items(
    bill_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """List items for a bill."""
    service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    bill = await service.repo.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "BILL_NOT_FOUND", "message": "Bill not found"})
    items = [BillItemResponse.model_validate(i).model_dump() for i in (bill.items or [])]
    return SuccessResponse(success=True, message=f"Found {len(items)} items", data={"bill_id": str(bill.id), "items": items}).dict()


@router.delete("/bills/{bill_id}/items/{item_id}", response_model=dict)
async def delete_bill_item(
    bill_id: UUID,
    item_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Remove line item from DRAFT bill only."""
    service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    try:
        bill = await service.remove_bill_item(bill_id, item_id)
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": (e.errors or [None])[0], "message": e.message})
    await db.commit()
    # Eagerly load items, patient, appointment, admission for response
    result = await db.execute(
        select(Bill)
        .where(Bill.id == bill.id)
        .options(
            selectinload(Bill.items),
            selectinload(Bill.patient),
            selectinload(Bill.appointment),
            selectinload(Bill.admission),
        )
    )
    bill = result.scalar_one()
    return SuccessResponse(success=True, message="Item removed", data=_bill_to_response(bill)).dict()


@router.patch("/bills/{bill_id}/items/{item_id}", response_model=dict)
async def update_bill_item(
    bill_id: UUID,
    item_id: UUID,
    body: BillItemUpdate,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Update a bill item (qty/price/tax/description) for DRAFT bills."""
    service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    try:
        bill = await service.update_bill_item(
            bill_id=bill_id,
            item_id=item_id,
            description=body.description,
            quantity=body.quantity,
            unit_price=body.unit_price,
            tax_percentage=body.tax_percentage,
        )
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": (e.errors or [None])[0], "message": e.message})
    await db.commit()
    # Eagerly load items, patient, appointment, admission for response
    result = await db.execute(
        select(Bill)
        .where(Bill.id == bill.id)
        .options(
            selectinload(Bill.items),
            selectinload(Bill.patient),
            selectinload(Bill.appointment),
            selectinload(Bill.admission),
        )
    )
    bill = result.scalar_one()
    return SuccessResponse(success=True, message="Item updated", data=_bill_to_response(bill)).dict()


@router.patch("/bills/{bill_id}/apply-discount", response_model=dict)
async def apply_discount(
    bill_id: UUID,
    body: BillDiscountApply,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Apply discount; may require admin approval if over threshold."""
    service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    try:
        bill = await service.apply_discount(bill_id, body.discount_amount, require_approval_if_over_threshold=True)
    except BusinessLogicError as e:
        if "DISCOUNT_REQUIRES_APPROVAL" in (e.errors or []):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "DISCOUNT_REQUIRES_APPROVAL", "message": e.message})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": (e.errors or [None])[0], "message": e.message})
    await db.commit()
    # Eagerly load items, patient, appointment, admission for response
    result = await db.execute(
        select(Bill)
        .where(Bill.id == bill.id)
        .options(
            selectinload(Bill.items),
            selectinload(Bill.patient),
            selectinload(Bill.appointment),
            selectinload(Bill.admission),
        )
    )
    bill = result.scalar_one()
    return SuccessResponse(success=True, message="Discount applied", data=_bill_to_response(bill)).dict()


@router.post("/bills/{bill_id}/discount/approve", response_model=dict)
async def approve_discount(
    bill_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_roles(UserRole.HOSPITAL_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
):
    """Hospital Admin: approve discount on bill."""
    service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    try:
        bill = await service.approve_discount(bill_id)
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": (e.errors or [None])[0], "message": e.message})
    await db.commit()
    # Eagerly load items, patient, appointment, admission for response
    result = await db.execute(
        select(Bill)
        .where(Bill.id == bill.id)
        .options(
            selectinload(Bill.items),
            selectinload(Bill.patient),
            selectinload(Bill.appointment),
            selectinload(Bill.admission),
        )
    )
    bill = result.scalar_one()
    return SuccessResponse(success=True, message="Discount approved", data=_bill_to_response(bill)).dict()


@router.patch("/bills/{bill_id}/finalize", response_model=dict)
async def finalize_bill(
    bill_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Finalize bill (DRAFT -> FINALIZED). Items cannot be edited after."""
    service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    try:
        bill = await service.finalize_bill(bill_id)
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": (e.errors or [None])[0], "message": e.message})
    await db.commit()
    # Eagerly load items, patient, appointment, admission for response
    result = await db.execute(
        select(Bill)
        .where(Bill.id == bill.id)
        .options(
            selectinload(Bill.items),
            selectinload(Bill.patient),
            selectinload(Bill.appointment),
            selectinload(Bill.admission),
        )
    )
    bill = result.scalar_one()
    return SuccessResponse(success=True, message="Bill finalized", data=_bill_to_response(bill)).dict()


@router.patch("/bills/{bill_id}/cancel", response_model=dict)
async def cancel_bill(
    bill_id: UUID,
    body: BillCancel,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Cancel bill."""
    service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    try:
        bill = await service.cancel_bill(bill_id, body.reason)
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": (e.errors or [None])[0], "message": e.message})
    await db.commit()
    # Eagerly load items, patient, appointment, admission for response
    result = await db.execute(
        select(Bill)
        .where(Bill.id == bill.id)
        .options(
            selectinload(Bill.items),
            selectinload(Bill.patient),
            selectinload(Bill.appointment),
            selectinload(Bill.admission),
        )
    )
    bill = result.scalar_one()
    return SuccessResponse(success=True, message="Bill cancelled", data=_bill_to_response(bill)).dict()


@router.patch("/bills/{bill_id}/reopen", response_model=dict)
async def reopen_bill(
    bill_id: UUID,
    body: BillReopen,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Reopen bill (FINALIZED/PARTIALLY_PAID -> DRAFT) for corrections."""
    service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    try:
        bill = await service.reopen_bill(bill_id, body.reason)
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": (e.errors or [None])[0], "message": e.message})
    await db.commit()
    # Eagerly load items, patient, appointment, admission for response
    result = await db.execute(
        select(Bill)
        .where(Bill.id == bill.id)
        .options(
            selectinload(Bill.items),
            selectinload(Bill.patient),
            selectinload(Bill.appointment),
            selectinload(Bill.admission),
        )
    )
    bill = result.scalar_one()
    return SuccessResponse(success=True, message="Bill reopened", data=_bill_to_response(bill)).dict()


@router.get("/bills/{bill_id}/invoice/pdf", response_class=Response)
async def get_bill_invoice_pdf(
    bill_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate invoice PDF for bill: hospital, patient, line items, totals, amount paid, balance due."""
    hospital_id = UUID(context["hospital_id"])
    r = await db.execute(
        select(Bill)
        .options(
            selectinload(Bill.items),
            selectinload(Bill.patient),
        )
        .where(Bill.id == bill_id, Bill.hospital_id == hospital_id)
    )
    bill = r.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "BILL_NOT_FOUND", "message": "Bill not found"})
    hr = await db.execute(select(Hospital).where(Hospital.id == hospital_id))
    hospital = hr.scalar_one_or_none()
    pdf_bytes = build_invoice_pdf(
        bill=bill,
        items=getattr(bill, "items", None) or [],
        patient=getattr(bill, "patient", None),
        hospital=hospital,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=invoice.pdf"},
    )


@router.get("/bills", response_model=dict)
async def list_bills(
    status: str | None = Query(None),
    patient_id: UUID | None = Query(None, description="Patient profile UUID"),
    patient_ref: str | None = Query(None, description="Patient reference (e.g. PAT-001)"),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """List bills (OPD+IPD) with pagination. Use patient_ref (e.g. PAT-001) or patient_id."""
    hospital_id = UUID(context["hospital_id"])
    resolved_patient_id = patient_id
    if not resolved_patient_id and patient_ref:
        r = await db.execute(
            select(PatientProfile.id).where(
                PatientProfile.patient_id == patient_ref,
                PatientProfile.hospital_id == hospital_id,
            ).limit(1)
        )
        resolved_patient_id = r.scalar_one_or_none()
    repo = BillingService(db, hospital_id, UUID(context["user_id"])).repo
    date_from_d = date.fromisoformat(date_from) if date_from else None
    date_to_d = date.fromisoformat(date_to) if date_to else None
    bills, total = await repo.list_bills(status=status, patient_id=resolved_patient_id, date_from=date_from_d, date_to=date_to_d, skip=skip, limit=limit)
    return SuccessResponse(success=True, message=f"Found {len(bills)} bills", data={"bills": [_bill_to_response(b) for b in bills], "total": total, "skip": skip, "limit": limit}).dict()


@router.post("/bills/{bill_id}/payments", response_model=dict)
async def collect_bill_payment(
    bill_id: UUID,
    body: BillPaymentCollect,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Collect payment for a specific bill (nested endpoint wrapper over /payments/collect)."""
    service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    try:
        payment = await service.record_payment(
            bill_id=bill_id,
            amount=body.amount,
            method=body.method,
            idempotency_key=body.idempotency_key,
            provider=body.provider,
            gateway_transaction_id=body.gateway_transaction_id,
            metadata=body.extra_data,
        )
    except BusinessLogicError as e:
        code = (e.errors or [None])[0]
        # Error codes are plain strings from BillingService (e.g. "BILL_NOT_FOUND")
        if code in ("BILL_NOT_FOUND", "BILL_NOT_FINALIZED", "PAYMENT_EXCEEDS_BALANCE"):
            status_code = status.HTTP_404_NOT_FOUND if code == "BILL_NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            raise HTTPException(status_code=status_code, detail={"code": code, "message": e.message})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": e.message})
    await db.commit()
    await db.refresh(payment)
    return SuccessResponse(success=True, message="Payment recorded", data=_payment_to_response(payment)).dict()


@router.get("/bills/{bill_id}/payments", response_model=dict)
async def list_bill_payments(
    bill_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """List payments for a specific bill."""
    service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    payments = await service.repo.list_payments(bill_id=bill_id)
    return SuccessResponse(success=True, message=f"Found {len(payments)} payments", data=[_payment_to_response(p) for p in payments]).dict()


@router.get("/bills/{bill_id}/balance", response_model=dict)
async def get_bill_balance(
    bill_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Get bill balance summary (total, paid, due)."""
    service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    bill = await service.repo.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "BILL_NOT_FOUND", "message": "Bill not found"})
    total = float(bill.total_amount)
    paid = float(bill.amount_paid)
    due = float(bill.balance_due)
    return SuccessResponse(
        success=True,
        message="Bill balance",
        data={"bill_id": str(bill.id), "total": total, "paid": paid, "due": due},
    ).dict()
