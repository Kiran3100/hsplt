"""
Payment Gateway - collect, get, list, advance, refund, receipt, ledger, outstanding, reconciliation.
All operations via PaymentService (no billing service payment logic).
"""
from uuid import UUID
from datetime import date, datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.models.payments import Payment
from app.models.billing import Bill
from app.models.tenant import Hospital
from app.services.payments.receipt_pdf import build_receipt_pdf
from app.api.deps import require_hospital_context, require_roles
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.payments import (
    PaymentCollectRequest,
    PaymentCollectResponse,
    AdvancePaymentRequest,
    AdvancePaymentResponse,
    RefundRequest,
    RefundResponse,
    LedgerEntryResponse,
    LedgerQuery,
    ReceiptResponse,
)
from pydantic import BaseModel
from app.schemas.response import SuccessResponse
from app.services.payments.payment_service import PaymentService
from app.services.payments.payment_service import PaymentServiceError

router = APIRouter(prefix="/payments")
require_billing = require_roles(UserRole.HOSPITAL_ADMIN, UserRole.RECEPTIONIST)

# --- 2.1 Payment Gateway SDK ---
@router.get("/providers", response_model=dict, tags=["M2.1 Payments - Providers"])
async def list_providers(
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
):
    """List configured payment providers (razorpay, stripe, paytm) and status."""
    from app.core.config import settings
    providers = []
    for name, key_attr in [("razorpay", "RAZORPAY_KEY_ID"), ("stripe", "STRIPE_SECRET_KEY"), ("paytm", "PAYTM_MID")]:
        configured = bool(getattr(settings, key_attr, None))
        providers.append({"provider": name, "configured": configured})
    return SuccessResponse(success=True, message="Providers", data={"providers": providers}).dict()


@router.get("/providers/{provider}/status", response_model=dict, tags=["M2.1 Payments - Providers"])
async def provider_status(
    provider: str,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
):
    """Provider health/status (keys configured, webhook secret set)."""
    from app.core.config import settings
    key_map = {"razorpay": ("RAZORPAY_KEY_ID", "RAZORPAY_WEBHOOK_SECRET"), "stripe": ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"), "paytm": ("PAYTM_MID", "PAYTM_KEY")}
    keys = key_map.get(provider.lower(), ())
    configured = all(bool(getattr(settings, k, None)) for k in keys) if keys else False
    return SuccessResponse(success=True, message=f"Provider {provider}", data={"provider": provider, "configured": configured}).dict()


@router.patch("/providers/{provider}/config", response_model=dict, tags=["M2.1 Payments - Providers"])
async def update_provider_config(
    provider: str,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_roles(UserRole.HOSPITAL_ADMIN)),
):
    """
    Provider config is read from .env only (no API update).
    Returns current config status so UI can show success when keys are present.
    Add keys to .env and restart the app to configure.
    """
    from app.core.config import settings
    provider_lower = provider.lower()
    key_map = {
        "razorpay": ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET"),
        "stripe": ("STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY"),
        "paytm": ("PAYTM_MID", "PAYTM_KEY"),
    }
    keys = key_map.get(provider_lower, ())
    configured = all(bool(getattr(settings, k, "") or "") for k in keys) if keys else False
    required = list(keys) if keys else []
    return SuccessResponse(
        success=True,
        message="Provider is configured (keys loaded from .env)." if configured else "Provider config is read from .env. Add keys and restart the app.",
        data={
            "provider": provider,
            "configured": configured,
            "required_env_vars": required,
            "note": "Configuration loaded from .env. Ready for payments." if configured else "Add these variables to your .env file and restart the application.",
        },
    ).dict()


# --- 2) Payment Processing: initiate, verify, collect, advance ---
class InitiateBody(BaseModel):
    bill_id: UUID
    amount: float
    currency: str = "INR"
    idempotency_key: str


@router.post("/initiate", response_model=dict, tags=["M2.2 Payments - Processing"])
async def initiate_payment(
    body: InitiateBody,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Initiate gateway order (e.g. Razorpay order). Returns order_id / client_secret for frontend."""
    from app.services.payments.providers import RazorpayProvider, StripeProvider
    svc = PaymentService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    bill = await svc.repo.get_bill(body.bill_id)
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BILL_NOT_FOUND", "message": "Bill not found or not accessible. Ensure the bill exists and belongs to your hospital."},
        )
    if bill.status not in ("FINALIZED", "PARTIALLY_PAID"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BILL_NOT_READY", "message": f"Bill must be FINALIZED or PARTIALLY_PAID to accept payments (current status: {bill.status})"},
        )
    balance = float(bill.balance_due)
    if body.amount > balance:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "AMOUNT_EXCEEDS_BALANCE", "message": "Amount exceeds balance due"})
    provider = RazorpayProvider()
    order = await provider.create_order(body.amount, body.currency, body.idempotency_key, notes={"bill_id": str(body.bill_id)})
    return SuccessResponse(success=True, message="Order created", data=order).dict()


class VerifyBody(BaseModel):
    payment_reference: str
    transaction_id: str
    gateway_order_id: str | None = None
    gateway_signature: str | None = None


@router.post("/verify", response_model=dict, tags=["M2.2 Payments - Processing"])
async def verify_payment(
    body: VerifyBody,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Verify gateway payment and confirm (idempotent). If already SUCCESS, returns existing."""
    svc = PaymentService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    existing = await svc.repo.get_payment_by_reference(body.payment_reference)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "PAYMENT_NOT_FOUND", "message": "Payment not found"})
    if existing.status == "SUCCESS":
        return SuccessResponse(success=True, message="Already verified", data=_payment_to_response(existing)).dict()
    return SuccessResponse(success=True, message="Verify via webhook or collect with transaction_id", data=_payment_to_response(existing)).dict()


def _payment_to_response(p):
    first_receipt = p.receipts[0] if getattr(p, "receipts", None) and len(p.receipts) > 0 else None
    return {
        "id": str(p.id),
        "hospital_id": str(p.hospital_id),
        "bill_id": str(p.bill_id),
        "payment_reference": p.payment_reference,
        "method": p.method,
        "provider": p.provider,
        "amount": float(p.amount),
        "currency": p.currency,
        "status": p.status,
        "transaction_id": p.transaction_id,
        "gateway_order_id": p.gateway_order_id,
        "collected_by_user_id": str(p.collected_by_user_id),
        "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        "receipt_number": first_receipt.receipt_number if first_receipt else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.post("/collect", response_model=dict, tags=["M2.2 Payments - Processing"])
async def collect_payment(
    body: PaymentCollectRequest,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Collect payment: validate bill finalized, prevent overpayment, create payment, update bill, ledger, receipt."""
    svc = PaymentService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    try:
        payment = await svc.record_payment(
            bill_id=body.bill_id,
            amount=body.amount,
            method=body.method,
            idempotency_key=body.idempotency_key,
            provider=body.provider,
            currency=body.currency,
            transaction_id=body.transaction_id,
            gateway_order_id=body.gateway_order_id,
            gateway_signature=body.gateway_signature,
            status="SUCCESS",
        )
    except PaymentServiceError as e:
        if e.code == "BILL_NOT_FOUND":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": e.code, "message": e.message})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": e.code, "message": e.message})
    await db.commit()
    await db.refresh(payment)
    return SuccessResponse(success=True, message="Payment recorded", data=_payment_to_response(payment)).dict()


@router.get("", response_model=dict, tags=["M2.2 Payments - Processing"])
async def list_payments(
    bill_id: UUID | None = Query(None),
    patient_id: UUID | None = Query(None),
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    method: str | None = Query(None),
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """List payments: bill_id, patient_id, from, to, method, status."""
    svc = PaymentService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    date_from_d = date.fromisoformat(date_from) if date_from else None
    date_to_d = date.fromisoformat(date_to) if date_to else None
    payments = await svc.repo.list_payments(bill_id=bill_id, patient_id=patient_id, date_from=date_from_d, date_to=date_to_d, method=method, status=status, skip=skip, limit=limit)
    return SuccessResponse(success=True, message=f"Found {len(payments)} payments", data=[_payment_to_response(p) for p in payments]).dict()


@router.get("/ledger", response_model=dict, tags=["M2.5 Payments - Ledger"])
async def get_ledger(
    bill_id: UUID | None = Query(None),
    patient_id: UUID | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Transaction history (payment ledger)."""
    svc = PaymentService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    date_from_d = datetime.fromisoformat(date_from) if date_from else None
    date_to_d = datetime.fromisoformat(date_to) if date_to else None
    entries = await svc.repo.list_ledger(bill_id=bill_id, patient_id=patient_id, date_from=date_from_d, date_to=date_to_d, skip=skip, limit=limit)
    data = [
        {
            "id": str(e.id),
            "bill_id": str(e.bill_id),
            "payment_id": str(e.payment_id) if e.payment_id else None,
            "entry_type": e.entry_type,
            "amount": float(e.amount),
            "balance_after": float(e.balance_after) if e.balance_after is not None else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]
    return SuccessResponse(success=True, message=f"Found {len(data)} ledger entries", data=data).dict()


@router.get("/outstanding", response_model=dict, tags=["M2.5 Payments - Ledger"])
async def get_outstanding(
    as_of: str | None = Query(None, description="Date YYYY-MM-DD; default today"),
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Outstanding payments: bills with balance_due > 0 (FINALIZED or PARTIALLY_PAID). Optional as_of date."""
    from sqlalchemy import select
    from app.models.billing import Bill
    r = await db.execute(
        select(Bill).where(
            Bill.hospital_id == UUID(context["hospital_id"]),
            Bill.status.in_(["FINALIZED", "PARTIALLY_PAID"]),
            Bill.balance_due > 0,
        ).order_by(Bill.created_at.desc()).limit(500)
    )
    bills = r.scalars().all()
    total = sum(float(b.balance_due) for b in bills)
    data = [
        {"bill_id": str(b.id), "bill_number": b.bill_number, "patient_id": str(b.patient_id), "balance_due": float(b.balance_due), "total_amount": float(b.total_amount)}
        for b in bills
    ]
    return SuccessResponse(success=True, message="Outstanding payments", data={"total_outstanding": total, "bills": data}).dict()


@router.get("/reports/reconciliation", response_model=dict, tags=["M2.5 Payments - Ledger"])
async def reconciliation_report(
    date_param: str = Query(..., alias="date", description="YYYY-MM-DD"),
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Reconciliation report: system records vs date."""
    svc = PaymentService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    d = datetime.strptime(date_param, "%Y-%m-%d").date()
    date_from = datetime.combine(d, datetime.min.time())
    date_to = datetime.combine(d, datetime.max.time())
    result = await svc.reconcile_transactions(date_from, date_to)
    return SuccessResponse(success=True, message="Reconciliation report", data={"date": date_param, **result}).dict()


@router.get("/reports/daily-summary", response_model=dict, tags=["M2.5 Payments - Ledger"])
async def daily_summary(
    date_param: str = Query(..., alias="date", description="YYYY-MM-DD"),
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Daily payment summary: total collected, by method, count."""
    svc = PaymentService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    d = datetime.strptime(date_param, "%Y-%m-%d").date()
    date_from = datetime.combine(d, datetime.min.time())
    date_to = datetime.combine(d, datetime.max.time())
    result = await svc.reconcile_transactions(date_from, date_to)
    return SuccessResponse(success=True, message="Daily summary", data={"date": date_param, **result}).dict()


@router.get("/{payment_id}", response_model=dict, tags=["M2.2 Payments - Processing"])
async def get_payment(
    payment_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Get payment by ID."""
    svc = PaymentService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    payment = await svc.repo.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "PAYMENT_NOT_FOUND", "message": "Payment not found"})
    return SuccessResponse(success=True, message="Payment retrieved", data=_payment_to_response(payment)).dict()


@router.post("/advance", response_model=dict, tags=["M2.2 Payments - Processing"])
async def advance_payment(
    body: AdvancePaymentRequest,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Advance payment for IPD (admission_id). Creates ledger credit and attaches to bill."""
    svc = PaymentService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    try:
        payment = await svc.record_advance_payment(
            admission_id=body.admission_id,
            amount=body.amount,
            method=body.method,
            idempotency_key=body.idempotency_key,
            currency=body.currency,
        )
    except PaymentServiceError as e:
        if e.code == "ADMISSION_NOT_FOUND":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": e.code, "message": e.message})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": e.code, "message": e.message})
    await db.commit()
    await db.refresh(payment)
    return SuccessResponse(success=True, message="Advance payment recorded", data=_payment_to_response(payment)).dict()


@router.post("/{payment_id}/refund", response_model=dict, tags=["M2.2 Payments - Processing"])
async def refund_payment(
    payment_id: UUID,
    body: RefundRequest,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Refund payment. Cannot exceed paid amount; updates bill balance and ledger REFUND."""
    svc = PaymentService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    try:
        refund = await svc.process_refund(payment_id, amount=body.amount, reason=body.reason)
    except PaymentServiceError as e:
        if e.code == "PAYMENT_NOT_FOUND":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": e.code, "message": e.message})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": e.code, "message": e.message})
    await db.commit()
    await db.refresh(refund)
    return SuccessResponse(
        success=True,
        message="Refund processed",
        data=RefundResponse.model_validate(refund).model_dump(mode="json"),
    ).dict()


@router.get("/{payment_id}/refunds", response_model=dict, tags=["M2.2 Payments - Processing"])
async def list_payment_refunds(
    payment_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """List refunds for a payment."""
    svc = PaymentService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    payment = await svc.repo.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "PAYMENT_NOT_FOUND", "message": "Payment not found"})
    refunds = await svc.repo.list_refunds_for_payment(payment_id)
    data = [{"id": str(r.id), "refund_amount": float(r.refund_amount), "reason": r.reason, "refund_status": r.refund_status, "created_at": r.created_at.isoformat() if r.created_at else None} for r in refunds]
    return SuccessResponse(success=True, message=f"Found {len(refunds)} refunds", data={"refunds": data}).dict()


@router.get("/{payment_id}/receipt/pdf", response_class=Response, tags=["M2.4 Payments - Receipt"])
async def get_receipt_pdf(
    payment_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate receipt PDF: hospital info, patient, bill number, payment method, amount, date."""
    hospital_id = UUID(context["hospital_id"])
    r = await db.execute(
        select(Payment)
        .options(
            selectinload(Payment.bill).selectinload(Bill.patient),
            selectinload(Payment.receipts),
        )
        .where(Payment.id == payment_id, Payment.hospital_id == hospital_id)
    )
    payment = r.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "PAYMENT_NOT_FOUND", "message": "Payment not found"})
    bill = payment.bill
    if not bill:
        bill = await PaymentService(db, hospital_id, UUID(context["user_id"])).repo.get_bill(payment.bill_id)
    hr = await db.execute(select(Hospital).where(Hospital.id == hospital_id))
    hospital = hr.scalar_one_or_none()
    receipt_number = None
    if getattr(payment, "receipts", None) and len(payment.receipts) > 0:
        receipt_number = payment.receipts[0].receipt_number
    pdf_bytes = build_receipt_pdf(
        payment=payment,
        bill=bill or type("Bill", (), {"bill_number": "—"})(),
        patient=bill.patient if bill and getattr(bill, "patient", None) else None,
        hospital=hospital,
        receipt_number=receipt_number,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=receipt.pdf"},
    )


class ReceiptEmailBody(BaseModel):
    to_email: str


@router.post("/{payment_id}/receipt/email", response_model=dict, tags=["M2.4 Payments - Receipt"])
async def email_receipt(
    payment_id: UUID,
    body: ReceiptEmailBody,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Email receipt PDF to recipient."""
    hospital_id = UUID(context["hospital_id"])
    r = await db.execute(
        select(Payment)
        .options(selectinload(Payment.bill).selectinload(Bill.patient), selectinload(Payment.receipts))
        .where(Payment.id == payment_id, Payment.hospital_id == hospital_id)
    )
    payment = r.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "PAYMENT_NOT_FOUND", "message": "Payment not found"})
    bill = payment.bill
    hr = await db.execute(select(Hospital).where(Hospital.id == hospital_id))
    hospital = hr.scalar_one_or_none()
    receipt_number = payment.receipts[0].receipt_number if getattr(payment, "receipts", None) and len(payment.receipts) > 0 else None
    pdf_bytes = build_receipt_pdf(payment=payment, bill=bill or type("B", (), {"bill_number": "—"})(), patient=bill.patient if bill and getattr(bill, "patient", None) else None, hospital=hospital, receipt_number=receipt_number)
    from app.services.email_service import EmailService
    email_svc = EmailService()
    to_email = (body.to_email or "").strip().lower()
    if not to_email or "@" not in to_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "INVALID_EMAIL", "message": "Valid to_email required"})
    await email_svc.send_document_email(to_email=to_email, subject=f"Receipt {receipt_number or payment_id} - Hospital", body_html="<p>Please find your payment receipt attached.</p>", pdf_bytes=pdf_bytes, filename="receipt.pdf")
    return SuccessResponse(success=True, message="Receipt emailed", data={"to_email": to_email}).dict()


@router.post("/{payment_id}/receipt/duplicate", response_model=dict, tags=["M2.4 Payments - Receipt"])
async def duplicate_receipt(
    payment_id: UUID,
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_billing),
    db: AsyncSession = Depends(get_db_session),
):
    """Create duplicate copy of receipt."""
    svc = PaymentService(db, UUID(context["hospital_id"]), UUID(context["user_id"]))
    try:
        receipt = await svc.generate_receipt(payment_id, is_duplicate=True)
    except PaymentServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": e.code, "message": e.message})
    await db.commit()
    await db.refresh(receipt)
    return SuccessResponse(success=True, message="Duplicate receipt created", data=ReceiptResponse.model_validate(receipt).model_dump(mode="json")).dict()


