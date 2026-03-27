"""Returns Router - Patient & Supplier returns"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.database.session import get_db_session
from app.dependencies.auth import require_pharmacy_staff, require_hospital_context
from app.models.user import User
from app.services.pharmacy_service import PharmacyService
from app.schemas.pharmacy import PatientReturnCreate, SupplierReturnCreate
from app.schemas.response import SuccessResponse

router = APIRouter(prefix="/returns", tags=["Pharmacy - Returns"])


@router.post("/patient", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_patient_return(
    return_data: PatientReturnCreate,
    current_user: User = Depends(require_pharmacy_staff()),
    db: AsyncSession = Depends(get_db_session)
):
    """Patient return - increments stock"""
    service = PharmacyService(db)
    return_record = await service.create_patient_return(
        hospital_id=current_user.hospital_id,
        returned_by=current_user.id,
        **return_data.dict()
    )
    await db.commit()
    return SuccessResponse(success=True, message="Patient return created", data={"return_id": str(return_record.id)}).dict()


@router.post("/supplier", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_supplier_return(
    return_data: SupplierReturnCreate,
    current_user: User = Depends(require_pharmacy_staff()),
    db: AsyncSession = Depends(get_db_session)
):
    """Supplier return - decrements stock"""
    service = PharmacyService(db)
    return_record = await service.create_supplier_return(
        hospital_id=current_user.hospital_id,
        returned_by=current_user.id,
        **return_data.dict()
    )
    await db.commit()
    return SuccessResponse(success=True, message="Supplier return created", data={"return_id": str(return_record.id)}).dict()


@router.get("", response_model=dict)
async def list_returns(
    return_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    context: dict = Depends(require_hospital_context),
    db: AsyncSession = Depends(get_db_session)
):
    """List returns"""
    service = PharmacyService(db)
    returns_list = await service.get_returns(UUID(context["hospital_id"]), return_type, skip, limit)
    return SuccessResponse(success=True, message=f"Found {len(returns_list)} returns", data={"returns": returns_list}).dict()
