"""Reports Router - Sales, stock valuation, expiry, profit margins"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.database.session import get_db_session
from app.dependencies.auth import require_admin_or_pharmacist, require_hospital_context
from app.models.user import User
from app.services.pharmacy_service import PharmacyService
from app.schemas.response import SuccessResponse

router = APIRouter(prefix="/reports", tags=["Pharmacy - Reports"])


@router.get("/sales-summary", response_model=dict)
async def get_sales_summary(
    from_date: str = Query(...),
    to_date: str = Query(...),
    group_by: str = Query("day", regex="^(day|month)$"),
    current_user: User = Depends(require_admin_or_pharmacist()),
    context: dict = Depends(require_hospital_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Sales summary report"""
    service = PharmacyService(db)
    summary = await service.get_sales_summary(UUID(context["hospital_id"]), from_date, to_date, group_by)
    return SuccessResponse(success=True, message="Sales summary generated", data={"summary": summary}).dict()


@router.get("/stock-valuation", response_model=dict)
async def get_stock_valuation(
    current_user: User = Depends(require_admin_or_pharmacist()),
    context: dict = Depends(require_hospital_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Stock valuation report (weighted average)"""
    service = PharmacyService(db)
    valuation = await service.get_stock_valuation(UUID(context["hospital_id"]))
    return SuccessResponse(success=True, message="Stock valuation generated", data={"valuation": valuation}).dict()


@router.get("/expiry", response_model=dict)
async def get_expiry_report(
    current_user: User = Depends(require_admin_or_pharmacist()),
    context: dict = Depends(require_hospital_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Expiry report (near expiry + expired)"""
    service = PharmacyService(db)
    report = await service.get_expiry_report(UUID(context["hospital_id"]))
    return SuccessResponse(success=True, message="Expiry report generated", data={"report": report}).dict()


@router.get("/fast-slow-moving", response_model=dict)
async def get_fast_slow_moving(
    from_date: str = Query(...),
    to_date: str = Query(...),
    current_user: User = Depends(require_admin_or_pharmacist()),
    context: dict = Depends(require_hospital_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Fast/slow moving items report"""
    service = PharmacyService(db)
    report = await service.get_fast_slow_moving(UUID(context["hospital_id"]), from_date, to_date)
    return SuccessResponse(success=True, message="Fast/slow moving report generated", data={"report": report}).dict()


@router.get("/profit-margins", response_model=dict)
async def get_profit_margins(
    from_date: str = Query(...),
    to_date: str = Query(...),
    current_user: User = Depends(require_admin_or_pharmacist()),
    context: dict = Depends(require_hospital_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Profit margin report (revenue - cost by medicine). Admin or pharmacy context."""
    service = PharmacyService(db)
    report = await service.get_profit_margins(UUID(context["hospital_id"]), from_date, to_date)
    return SuccessResponse(success=True, message="Profit margins generated", data={"report": report}).dict()
