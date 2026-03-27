"""
3) Webhook Implementation — Receive gateway callbacks (status updates).
POST /api/v1/payments/webhooks/{provider}
No JWT; verification by gateway signature.
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db_session
from app.models.payments import Payment
from app.services.payments.payment_service import PaymentService
from app.services.payments.payment_service import PaymentServiceError
from app.services.payments.providers.razorpay_provider import RazorpayProvider
from app.services.payments.providers.stripe_provider import StripeProvider
from app.services.payments.providers.paytm_provider import PaytmProvider

router = APIRouter(
    prefix="/payments/webhooks",
    tags=["M2.3 Payments - Webhooks"],
)

_PROVIDERS = {
    "razorpay": RazorpayProvider(),
    "stripe": StripeProvider(),
    "paytm": PaytmProvider(),
}


@router.post("/{provider}")
async def webhook_receive(
    request: Request,
    provider: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Receive gateway callback; verify signature; idempotent update payment status and bill."""
    body = await request.body()
    signature = (
        request.headers.get("X-Razorpay-Signature")
        or request.headers.get("Stripe-Signature")
        or ""
    )
    impl = _PROVIDERS.get(provider.lower())
    if not impl:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNKNOWN_PROVIDER", "message": f"Unknown provider: {provider}"},
        )
    if not impl.verify_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_SIGNATURE", "message": "Signature verification failed"},
        )
    data = impl.parse_webhook_payload(body)
    payment_ref = data.get("payment_id") or data.get("order_id")
    if not payment_ref:
        return {"ok": True, "message": "Event ignored (no payment ref)"}
    result = await db.execute(
        select(Payment).where(
            (Payment.gateway_order_id == payment_ref)
            | (Payment.payment_reference == payment_ref)
            | (Payment.transaction_id == payment_ref)
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        return {"ok": True, "message": "Payment not found (idempotent ignore)"}
    svc = PaymentService(
        db, payment.hospital_id, payment.collected_by_user_id
    )
    try:
        await svc.handle_webhook_event(provider, body, signature)
    except PaymentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message},
        )
    await db.commit()
    return {"ok": True, "message": "Webhook processed"}
