"""
Payment collection APIs (multiple methods, partial, advance, idempotency).
RBAC: Hospital Admin, Receptionist.
"""
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.core.security import get_current_user
from app.api.deps import require_hospital_context, require_roles
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.billing import PaymentCollect, PaymentResponse, PaymentRefund, AdvancePaymentRequest
from app.schemas.response import SuccessResponse
from app.services.billing.billing_service import BillingService
from app.core.exceptions import BusinessLogicError

router = APIRouter(prefix="/payments", tags=["Payments"])
require_billing = require_roles(UserRole.HOSPITAL_ADMIN, UserRole.RECEPTIONIST)


def _payment_to_response(p):
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


@router.post("/collect", response_model=dict)
async def collect_payment(
    body: PaymentCollect,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Record payment against bill (idempotency_key = payment_ref). Partial/advance allowed."""
    service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    try:
        payment = await service.record_payment(
            bill_id=body.bill_id,
            amount=body.amount,
            method=body.method,
            idempotency_key=body.idempotency_key,
            provider=body.provider,
            gateway_transaction_id=body.gateway_transaction_id,
            metadata=body.extra_data,
        )
    except BusinessLogicError as e:
        code = (e.errors or [None])[0]
        if code == "BILL_NOT_FOUND":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": code, "message": e.message})
        if code == "BILL_NOT_FINALIZED":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": e.message})
        if code == "PAYMENT_EXCEEDS_BALANCE":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": e.message})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": e.message})
    await db.commit()
    await db.refresh(payment)
    return SuccessResponse(success=True, message="Payment recorded", data=_payment_to_response(payment)).dict()


@router.get("", response_model=dict)
async def list_payments(
    bill_id: UUID | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    method: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """List payments with filters and pagination."""
    repo = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"])).repo
    date_from_d = date.fromisoformat(date_from) if date_from else None
    date_to_d = date.fromisoformat(date_to) if date_to else None
    payments = await repo.list_payments(bill_id=bill_id, date_from=date_from_d, date_to=date_to_d, method=method, skip=skip, limit=limit)
    return SuccessResponse(success=True, message=f"Found {len(payments)} payments", data=[_payment_to_response(p) for p in payments]).dict()


@router.get("/{payment_id}/receipt/pdf")
async def get_payment_receipt_pdf(
    payment_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate receipt PDF for payment. Stub: 501."""
    repo = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"])).repo
    payment = await repo.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "PAYMENT_NOT_FOUND", "message": "Payment not found"})
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail={"code": "PDF_NOT_IMPLEMENTED", "message": "Receipt PDF: implement WeasyPrint/ReportLab"})


@router.get("/{payment_id}", response_model=dict)
async def get_payment(
    payment_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Get payment by ID."""
    repo = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"])).repo
    payment = await repo.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "PAYMENT_NOT_FOUND", "message": "Payment not found"})
    return SuccessResponse(success=True, message="Payment retrieved", data=_payment_to_response(payment)).dict()


@router.post("/{payment_id}/refund", response_model=dict)
async def refund_payment(
    payment_id: UUID,
    body: PaymentRefund,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Refund payment (full or partial). Full refund if amount not provided."""
    service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    try:
        refund = await service.process_refund(payment_id, amount=body.amount, reason=body.reason)
    except BusinessLogicError as e:
        code = (e.errors or [None])[0]
        if code == "PAYMENT_NOT_FOUND":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": code, "message": e.message})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": e.message})
    await db.commit()
    await db.refresh(refund)
    return SuccessResponse(
        success=True,
        message="Refund processed",
        data={
            "id": str(refund.id),
            "payment_id": str(refund.payment_id),
            "amount": float(refund.amount),
            "reason": refund.reason,
            "status": refund.status,
            "refunded_at": refund.refunded_at.isoformat() if refund.refunded_at else None,
        },
    ).dict()


# Advance payment for IPD (create/use bill or record against admission - SOW says POST /payments/advance)
@router.post("/advance", response_model=dict)
async def record_advance_payment(
    body: AdvancePaymentRequest,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Record advance payment for IPD (admission_id). Creates or finds IPD bill and records payment."""
    # Find or create IPD bill for admission; then record payment with idempotency_key
    from sqlalchemy import select
    from app.models.patient import Admission
    from app.models.billing import Bill
    repo = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"])).repo
    # Get admission
    r = await db.execute(select(Admission).where(Admission.id == body.admission_id, Admission.hospital_id == context["hospital_id"]))
    admission = r.scalar_one_or_none()
    if not admission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "ADMISSION_NOT_FOUND", "message": "Admission not found"})
    # Find existing IPD bill for this admission
    r2 = await db.execute(select(Bill).where(Bill.admission_id == body.admission_id, Bill.hospital_id == context["hospital_id"]).limit(1))
    bill = r2.scalar_one_or_none()
    if not bill:
        # Create minimal IPD bill (DRAFT), finalize, then record payment
        service = BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
        bill = await service.create_ipd_bill(admission.patient_id, body.admission_id, [], notes="Advance payment")
        await service.finalize_bill(bill.id)
        await db.flush()
    payment = await BillingService(db, UUID(context["hospital_id"]), UUID(context["user_id"])).record_payment(
        bill_id=bill.id,
        amount=body.amount,
        method=body.method,
        idempotency_key=body.idempotency_key,
    )
    await db.commit()
    await db.refresh(payment)
    return SuccessResponse(success=True, message="Advance payment recorded", data=_payment_to_response(payment)).dict()
