"""GRN (Goods Receipt Note) Management Router"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.database.session import get_db_session
from app.dependencies.auth import require_pharmacy_staff, require_hospital_context
from app.models.user import User
from app.services.pharmacy_service import PharmacyService
from app.schemas.pharmacy import GRNCreate, GRNItemCreate
from app.schemas.response import SuccessResponse

router = APIRouter(prefix="/grn", tags=["Pharmacy - GRN"])


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_grn(
    grn_data: GRNCreate,
    current_user: User = Depends(require_pharmacy_staff()),
    db: AsyncSession = Depends(get_db_session)
):
    """Create new GRN"""
    service = PharmacyService(db)
    grn = await service.create_grn(
        hospital_id=current_user.hospital_id,
        received_by=current_user.id,
        **grn_data.model_dump()
    )
    await db.commit()
    return SuccessResponse(success=True, message="GRN created", data={"grn_id": str(grn.id)}).dict()


def _grn_to_dict(grn):
    """Serialize GRN model to dict for JSON response"""
    return {
        "id": str(grn.id),
        "hospital_id": str(grn.hospital_id),
        "supplier_id": str(grn.supplier_id),
        "po_id": str(grn.po_id) if grn.po_id else None,
        "grn_number": grn.grn_number,
        "received_at": grn.received_at.isoformat() if grn.received_at else None,
        "received_by": str(grn.received_by),
        "finalized_at": grn.finalized_at.isoformat() if grn.finalized_at else None,
        "finalized_by": str(grn.finalized_by) if grn.finalized_by else None,
        "is_finalized": bool(grn.is_finalized),
        "notes": grn.notes,
        "created_at": grn.created_at.isoformat() if getattr(grn, "created_at", None) else None,
    }


def _grn_item_to_dict(item):
    """Serialize GRN item to dict"""
    return {
        "id": str(item.id),
        "medicine_id": str(item.medicine_id),
        "batch_no": item.batch_no,
        "expiry_date": item.expiry_date.isoformat() if hasattr(item.expiry_date, "isoformat") else str(item.expiry_date),
        "received_qty": float(item.received_qty),
        "free_qty": float(item.free_qty or 0),
        "purchase_rate": float(item.purchase_rate),
        "mrp": float(item.mrp),
        "selling_price": float(item.selling_price),
        "tax_percent": float(item.tax_percent or 0),
    }


@router.get("", response_model=dict)
async def list_grns(
    supplier_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_pharmacy_staff()),
    context: dict = Depends(require_hospital_context),
    db: AsyncSession = Depends(get_db_session)
):
    """List GRNs"""
    service = PharmacyService(db)
    grns = await service.get_grns(UUID(context["hospital_id"]), supplier_id, skip, limit)
    return SuccessResponse(success=True, message=f"Found {len(grns)} GRNs", data={"grns": [_grn_to_dict(g) for g in grns]}).dict()


@router.get("/{grn_id}", response_model=dict)
async def get_grn(
    grn_id: UUID,
    current_user: User = Depends(require_pharmacy_staff()),
    context: dict = Depends(require_hospital_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Get GRN details"""
    service = PharmacyService(db)
    grn = await service.get_grn(grn_id, UUID(context["hospital_id"]))
    data = _grn_to_dict(grn)
    data["items"] = [_grn_item_to_dict(it) for it in (grn.items if hasattr(grn, "items") and grn.items else [])]
    return SuccessResponse(success=True, message="GRN retrieved", data={"grn": data}).dict()


@router.post("/{grn_id}/items", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_grn_item(
    grn_id: UUID,
    item_data: GRNItemCreate,
    current_user: User = Depends(require_pharmacy_staff()),
    db: AsyncSession = Depends(get_db_session)
):
    """Add item to GRN"""
    service = PharmacyService(db)
    item = await service.add_grn_item(grn_id, current_user.hospital_id, **item_data.model_dump())
    await db.commit()
    return SuccessResponse(success=True, message="Item added", data={"item_id": str(item.id)}).dict()


@router.post("/{grn_id}/finalize", response_model=dict)
async def finalize_grn(
    grn_id: UUID,
    current_user: User = Depends(require_pharmacy_staff()),
    db: AsyncSession = Depends(get_db_session)
):
    """Finalize GRN - creates stock batches"""
    service = PharmacyService(db)
    result = await service.finalize_grn(grn_id, current_user.hospital_id, current_user.id)
    await db.commit()
    return SuccessResponse(success=True, message="GRN finalized", data=result).dict()

