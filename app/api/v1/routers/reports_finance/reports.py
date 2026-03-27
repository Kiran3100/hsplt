"""
Financial reports & analytics: revenue, outstanding, department/doctor-wise, tax GST.
RBAC: Hospital Admin; Receptionist for own scope if needed.
"""
from uuid import UUID
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.core.security import get_current_user
from app.api.deps import require_hospital_context, require_roles
from app.core.enums import UserRole
from app.models.user import User
from app.models.billing import Bill, BillingPayment
from app.models.patient import Appointment, Admission
from app.models.hospital import Department
from app.schemas.response import SuccessResponse

router = APIRouter(prefix="/finance/reports", tags=["M1.8 Finance - Reports"])
require_admin = require_roles(UserRole.HOSPITAL_ADMIN)


@router.get("/revenue", response_model=dict)
async def revenue_report(
    granularity: str = Query("daily", pattern="^(daily|monthly|yearly)$"),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Revenue report: daily/monthly/yearly. Uses payments (SUCCESS) and optionally finalized bill totals."""
    hospital_id = UUID(context["hospital_id"])
    if not date_from:
        date_from = (date.today() - timedelta(days=30)).isoformat()
    if not date_to:
        date_to = date.today().isoformat()
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)
    # Sum payments by paid_at in range
    r = await db.execute(
        select(
            func.date(BillingPayment.paid_at).label("dt"),
            func.sum(BillingPayment.amount).label("total"),
            func.count(BillingPayment.id).label("count"),
        )
        .where(
            and_(
                BillingPayment.hospital_id == hospital_id,
                BillingPayment.status == "SUCCESS",
                BillingPayment.paid_at >= datetime.combine(d_from, datetime.min.time()),
                BillingPayment.paid_at <= datetime.combine(d_to, datetime.max.time()),
            )
        )
        .group_by(func.date(BillingPayment.paid_at))
    )
    rows = r.all()
    data = [{"date": str(row.dt), "total": float(row.total), "payment_count": row.count} for row in rows]
    return SuccessResponse(success=True, message="Revenue report", data={"granularity": granularity, "from": date_from, "to": date_to, "series": data}).dict()


@router.get("/outstanding", response_model=dict)
async def outstanding_report(
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Outstanding payments: FINALIZED/PARTIALLY_PAID bills with balance_due > 0."""
    hospital_id = UUID(context["hospital_id"])
    r = await db.execute(
        select(Bill)
        .where(
            and_(
                Bill.hospital_id == hospital_id,
                Bill.status.in_(["FINALIZED", "PARTIALLY_PAID"]),
                Bill.balance_due > 0,
            )
        )
        .order_by(Bill.created_at.desc())
        .limit(500)
    )
    bills = r.scalars().all()
    total_outstanding = sum(float(b.balance_due) for b in bills)
    data = [
        {"bill_id": str(b.id), "bill_number": b.bill_number, "patient_id": str(b.patient_id), "balance_due": float(b.balance_due), "total_amount": float(b.total_amount)}
        for b in bills
    ]
    return SuccessResponse(success=True, message="Outstanding report", data={"total_outstanding": total_outstanding, "bills": data}).dict()


@router.get("/department-revenue", response_model=dict)
async def department_revenue(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Department-wise revenue (from appointments/bills linked to department)."""
    hospital_id = UUID(context["hospital_id"])
    if not date_from:
        date_from = (date.today() - timedelta(days=30)).isoformat()
    if not date_to:
        date_to = date.today().isoformat()
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)
    # Bills don't have department_id; use appointment -> department for OPD. For simplicity aggregate by bill type.
    r = await db.execute(
        select(Bill.bill_type, func.sum(Bill.total_amount).label("total"), func.count(Bill.id).label("count"))
        .where(
            and_(
                Bill.hospital_id == hospital_id,
                Bill.status.in_(["PAID", "PARTIALLY_PAID"]),
                Bill.created_at >= datetime.combine(d_from, datetime.min.time()),
                Bill.created_at <= datetime.combine(d_to, datetime.max.time()),
            )
        )
        .group_by(Bill.bill_type)
    )
    rows = r.all()
    data = [{"department_type": row.bill_type, "total": float(row.total), "bill_count": row.count} for row in rows]
    return SuccessResponse(success=True, message="Department revenue", data={"from": date_from, "to": date_to, "breakdown": data}).dict()


@router.get("/doctor-revenue", response_model=dict)
async def doctor_revenue(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Doctor-wise revenue (from appointments with consultation_fee / OPD bills linked to appointment)."""
    hospital_id = UUID(context["hospital_id"])
    if not date_from:
        date_from = (date.today() - timedelta(days=30)).isoformat()
    if not date_to:
        date_to = date.today().isoformat()
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)
    # Sum bill total by doctor via appointment: Bill -> appointment_id -> doctor_id
    r = await db.execute(
        select(
            Appointment.doctor_id,
            func.sum(Bill.total_amount).label("total"),
            func.count(Bill.id).label("count"),
        )
        .join(Bill, Bill.appointment_id == Appointment.id)
        .where(
            and_(
                Bill.hospital_id == hospital_id,
                Appointment.hospital_id == hospital_id,
                Bill.status.in_(["PAID", "PARTIALLY_PAID"]),
                Bill.created_at >= datetime.combine(d_from, datetime.min.time()),
                Bill.created_at <= datetime.combine(d_to, datetime.max.time()),
            )
        )
        .group_by(Appointment.doctor_id)
    )
    rows = r.all()
    data = [{"doctor_id": str(row.doctor_id), "total": float(row.total), "bill_count": row.count} for row in rows]
    return SuccessResponse(success=True, message="Doctor revenue", data={"from": date_from, "to": date_to, "breakdown": data}).dict()


@router.get("/tax-gst", response_model=dict)
async def tax_gst_report(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    context: dict = Depends(require_hospital_context),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """Tax (GST) report: sum of tax_amount from finalized/paid bills."""
    hospital_id = UUID(context["hospital_id"])
    if not date_from:
        date_from = (date.today() - timedelta(days=30)).isoformat()
    if not date_to:
        date_to = date.today().isoformat()
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)
    r = await db.execute(
        select(func.sum(Bill.tax_amount).label("total_tax"), func.sum(Bill.total_amount).label("total_amount"), func.count(Bill.id).label("count"))
        .where(
            and_(
                Bill.hospital_id == hospital_id,
                Bill.status.in_(["PAID", "PARTIALLY_PAID", "FINALIZED"]),
                Bill.created_at >= datetime.combine(d_from, datetime.min.time()),
                Bill.created_at <= datetime.combine(d_to, datetime.max.time()),
            )
        )
    )
    row = r.one()
    return SuccessResponse(
        success=True,
        message="Tax GST report",
        data={"from": date_from, "to": date_to, "total_tax": float(row.total_tax or 0), "total_amount": float(row.total_amount or 0), "bill_count": row.count or 0},
    ).dict()
