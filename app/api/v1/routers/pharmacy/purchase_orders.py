"""Purchase Order Router - Complete PO management"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
from datetime import date

from app.database.session import get_db_session
from app.dependencies.auth import require_admin_or_pharmacist, require_hospital_admin
from app.models.user import User
from app.services.pharmacy_service import PharmacyService
from app.schemas.response import SuccessResponse

router = APIRouter(prefix="/purchase-orders", tags=["Pharmacy - Purchase Orders"])


class POItemCreate(BaseModel):
    medicine_id: UUID
    ordered_qty: float
    purchase_rate: float
    tax_percent: Optional[float] = 0
    discount_percent: Optional[float] = 0


class PurchaseOrderCreate(BaseModel):
    supplier_id: UUID
    expected_date: Optional[date] = None
    items: List[POItemCreate]
    notes: Optional[str] = None


class PurchaseOrderUpdate(BaseModel):
    expected_date: Optional[date] = None
    notes: Optional[str] = None


@router.get("")
async def list_purchase_orders(
    status: Optional[str] = Query(None, description="Filter by status"),
    supplier_id: Optional[UUID] = Query(None, description="Filter by supplier"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_admin_or_pharmacist()),
    db: AsyncSession = Depends(get_db_session)
):
    """
    List all purchase orders.
    
    Access Control:
    - **Who can access:** Authenticated users with hospital context (Pharmacist, Hospital Admin)
    """
    service = PharmacyService(db)
    pos = await service.get_purchase_orders(
        hospital_id=current_user.hospital_id,
        status=status,
        supplier_id=supplier_id,
        skip=skip,
        limit=limit
    )
    
    return SuccessResponse(
        success=True,
        message=f"Found {len(pos)} purchase orders",
        data={
            "purchase_orders": [
                {
                    "id": str(po.id),
                    "po_number": po.po_number,
                    "supplier_id": str(po.supplier_id),
                    "status": po.status,
                    "expected_date": str(po.expected_date) if po.expected_date else None,
                    "subtotal": float(po.subtotal),
                    "tax_total": float(po.tax_total),
                    "discount_total": float(po.discount_total),
                    "grand_total": float(po.grand_total),
                    "created_at": str(po.created_at),
                    "approved_at": str(po.approved_at) if po.approved_at else None
                }
                for po in pos
            ],
            "total": len(pos),
            "skip": skip,
            "limit": limit
        }
    ).dict()


@router.get("/{po_id}")
async def get_purchase_order(
    po_id: UUID,
    current_user: User = Depends(require_admin_or_pharmacist()),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get purchase order details with items.
    
    Access Control:
    - **Who can access:** Authenticated users with hospital context (Pharmacist, Hospital Admin)
    """
    service = PharmacyService(db)
    po = await service.get_purchase_order(po_id, current_user.hospital_id)
    
    return SuccessResponse(
        success=True,
        message="Purchase order retrieved successfully",
        data={
            "purchase_order": {
                "id": str(po.id),
                "po_number": po.po_number,
                "supplier_id": str(po.supplier_id),
                "status": po.status,
                "expected_date": str(po.expected_date) if po.expected_date else None,
                "subtotal": float(po.subtotal),
                "tax_total": float(po.tax_total),
                "discount_total": float(po.discount_total),
                "grand_total": float(po.grand_total),
                "notes": po.notes,
                "created_at": str(po.created_at),
                "approved_at": str(po.approved_at) if po.approved_at else None,
                "items": [
                    {
                        "id": str(item.id),
                        "medicine_id": str(item.medicine_id),
                        "ordered_qty": float(item.ordered_qty),
                        "received_qty": float(item.received_qty),
                        "purchase_rate": float(item.purchase_rate),
                        "tax_percent": float(item.tax_percent),
                        "discount_percent": float(item.discount_percent),
                        "line_total": float(item.line_total)
                    }
                    for item in po.items
                ]
            }
        }
    ).dict()


@router.post("")
async def create_purchase_order(
    po_data: PurchaseOrderCreate,
    current_user: User = Depends(require_admin_or_pharmacist()),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new purchase order"""
    service = PharmacyService(db)
    po = await service.create_purchase_order(
        hospital_id=current_user.hospital_id,
        supplier_id=po_data.supplier_id,
        items=po_data.items,
        expected_date=po_data.expected_date,
        notes=po_data.notes,
        created_by=current_user.id
    )
    await db.commit()
    
    return SuccessResponse(
        success=True,
        message="Purchase order created successfully",
        data={
            "po_id": str(po.id),
            "po_number": po.po_number
        }
    ).dict()


@router.put("/{po_id}")
async def update_purchase_order(
    po_id: UUID,
    po_data: PurchaseOrderUpdate,
    current_user: User = Depends(require_admin_or_pharmacist()),
    db: AsyncSession = Depends(get_db_session)
):
    """Update purchase order (only in DRAFT status)"""
    service = PharmacyService(db)
    updates = {k: v for k, v in po_data.dict().items() if v is not None}
    po = await service.update_purchase_order(
        po_id=po_id,
        hospital_id=current_user.hospital_id,
        **updates
    )
    await db.commit()
    
    return SuccessResponse(
        success=True,
        message="Purchase order updated successfully",
        data={"po_id": str(po.id)}
    ).dict()


@router.post("/{po_id}/submit")
async def submit_purchase_order(
    po_id: UUID,
    current_user: User = Depends(require_admin_or_pharmacist()),
    db: AsyncSession = Depends(get_db_session)
):
    """Submit a purchase order for approval (DRAFT → PENDING). After this, status will show as PENDING."""
    service = PharmacyService(db)
    po = await service.submit_purchase_order(
        po_id=po_id,
        hospital_id=current_user.hospital_id
    )
    await db.commit()
    return SuccessResponse(
        success=True,
        message="Purchase order submitted for approval",
        data={
            "po_id": str(po.id),
            "status": po.status
        }
    ).dict()


@router.post("/{po_id}/approve")
async def approve_purchase_order(
    po_id: UUID,
    current_user: User = Depends(require_hospital_admin()),
    db: AsyncSession = Depends(get_db_session)
):
    """Approve a purchase order"""
    service = PharmacyService(db)
    po = await service.approve_purchase_order(
        po_id=po_id,
        hospital_id=current_user.hospital_id,
        approved_by=current_user.id
    )
    await db.commit()
    
    return SuccessResponse(
        success=True,
        message="Purchase order approved successfully",
        data={
            "po_id": str(po.id),
            "status": po.status
        }
    ).dict()


@router.post("/{po_id}/send")
async def send_purchase_order(
    po_id: UUID,
    current_user: User = Depends(require_admin_or_pharmacist()),
    db: AsyncSession = Depends(get_db_session)
):
    """Send purchase order to supplier"""
    service = PharmacyService(db)
    po = await service.send_purchase_order(
        po_id=po_id,
        hospital_id=current_user.hospital_id
    )
    await db.commit()
    
    return SuccessResponse(
        success=True,
        message="Purchase order sent to supplier",
        data={
            "po_id": str(po.id),
            "status": po.status
        }
    ).dict()


@router.post("/{po_id}/cancel")
async def cancel_purchase_order(
    po_id: UUID,
    reason: str,
    current_user: User = Depends(require_admin_or_pharmacist()),
    db: AsyncSession = Depends(get_db_session)
):
    """Cancel a purchase order"""
    service = PharmacyService(db)
    po = await service.cancel_purchase_order(
        po_id=po_id,
        hospital_id=current_user.hospital_id,
        reason=reason
    )
    await db.commit()
    
    return SuccessResponse(
        success=True,
        message="Purchase order cancelled",
        data={
            "po_id": str(po.id),
            "status": po.status
        }
    ).dict()


@router.delete("/{po_id}")
async def delete_purchase_order(
    po_id: UUID,
    current_user: User = Depends(require_admin_or_pharmacist()),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a purchase order (only DRAFT status)"""
    service = PharmacyService(db)
    po = await service.get_purchase_order(po_id, current_user.hospital_id)
    if po.status != "DRAFT":
        from app.core.exceptions import BusinessLogicError
        raise BusinessLogicError("Only DRAFT purchase orders can be deleted")
    
    po.is_active = False
    await db.commit()
    
    return SuccessResponse(
        success=True,
        message="Purchase order deleted successfully",
        data={"po_id": str(po_id)}
    ).dict()

