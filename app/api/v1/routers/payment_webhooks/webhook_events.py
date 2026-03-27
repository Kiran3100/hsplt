"""
3) Webhook Implementation — Events / tracking.
GET /api/v1/payments/webhooks/{provider}/events?from=&to=
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
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


@router.get("/{provider}/events")
async def webhook_events(
    provider: str,
    date_from: str | None = Query(None, alias="from", description="YYYY-MM-DD"),
    date_to: str | None = Query(None, alias="to", description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db_session),
):
    """List webhook events for provider (from/to date). Stub: returns empty list; implement with event store if needed."""
    if provider.lower() not in _PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNKNOWN_PROVIDER", "message": f"Unknown provider: {provider}"},
        )
    return {
        "ok": True,
        "provider": provider,
        "events": [],
        "message": "Webhook events not persisted; use gateway dashboard for event history",
    }
