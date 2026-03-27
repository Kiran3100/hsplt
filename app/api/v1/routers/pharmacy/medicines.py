"""
Medicine Management Router - Complete CRUD operations
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.database.session import get_db_session
from app.dependencies.auth import require_admin_or_pharmacist
from app.models.user import User
from app.services.pharmacy_service import PharmacyService
from app.schemas.response import SuccessResponse

router = APIRouter(prefix="/medicines", tags=["Pharmacy - Medicines"])


class MedicineCreate(BaseModel):
    generic_name: str
    brand_name: str
    dosage_form: str
    composition: Optional[str] = None
    strength: Optional[str] = None
    manufacturer: Optional[str] = None
    category: Optional[str] = None
    drug_class: Optional[str] = None
    route: Optional[str] = None
    pack_size: Optional[int] = None
    reorder_level: Optional[int] = 10
    barcode: Optional[str] = None
    hsn_code: Optional[str] = None
    sku: Optional[str] = None
    requires_prescription: Optional[bool] = False
    is_controlled_substance: Optional[bool] = False
    description: Optional[str] = None
    storage_instructions: Optional[str] = None


class MedicineUpdate(BaseModel):
    generic_name: Optional[str] = None
    brand_name: Optional[str] = None
    dosage_form: Optional[str] = None
    composition: Optional[str] = None
    strength: Optional[str] = None
    manufacturer: Optional[str] = None
    category: Optional[str] = None
    drug_class: Optional[str] = None
    route: Optional[str] = None
    pack_size: Optional[int] = None
    reorder_level: Optional[int] = None
    barcode: Optional[str] = None
    hsn_code: Optional[str] = None
    sku: Optional[str] = None
    requires_prescription: Optional[bool] = None
    is_controlled_substance: Optional[bool] = None
    description: Optional[str] = None
    storage_instructions: Optional[str] = None


@router.get("")
async def list_medicines(
    search: Optional[str] = Query(None, description="Search by generic name, brand name, or manufacturer"),
    category: Optional[str] = Query(None, description="Filter by category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_admin_or_pharmacist()),
    db: AsyncSession = Depends(get_db_session)
):
    """List all medicines with search and filters"""
    service = PharmacyService(db)
    medicines = await service.search_medicines(
        hospital_id=current_user.hospital_id,
        search=search,
        category=category,
        skip=skip,
        limit=limit
    )
    
    return SuccessResponse(
        success=True,
        message=f"Found {len(medicines)} medicines",
        data={
            "medicines": [
                {
                    "id": str(m.id),
                    "generic_name": m.generic_name,
                    "brand_name": m.brand_name,
                    "composition": m.composition,
                    "dosage_form": m.dosage_form,
                    "strength": m.strength,
                    "manufacturer": m.manufacturer,
                    "category": m.category,
                    "requires_prescription": m.requires_prescription,
                    "is_controlled_substance": m.is_controlled_substance,
                    "reorder_level": m.reorder_level,
                    "created_at": str(m.created_at)
                }
                for m in medicines
            ],
            "total": len(medicines),
            "skip": skip,
            "limit": limit
        }
    ).dict()


@router.get("/{medicine_id}")
async def get_medicine(
    medicine_id: UUID,
    current_user: User = Depends(require_admin_or_pharmacist()),
    db: AsyncSession = Depends(get_db_session)
):
    """Get medicine details by ID"""
    service = PharmacyService(db)
    medicine = await service.get_medicine(medicine_id, current_user.hospital_id)
    
    return SuccessResponse(
        success=True,
        message="Medicine retrieved successfully",
        data={
            "medicine": {
                "id": str(medicine.id),
                "generic_name": medicine.generic_name,
                "brand_name": medicine.brand_name,
                "composition": medicine.composition,
                "dosage_form": medicine.dosage_form,
                "strength": medicine.strength,
                "manufacturer": medicine.manufacturer,
                "category": medicine.category,
                "drug_class": medicine.drug_class,
                "route": medicine.route,
                "pack_size": medicine.pack_size,
                "reorder_level": medicine.reorder_level,
                "hsn_code": medicine.hsn_code,
                "sku": medicine.sku,
                "barcode": medicine.barcode,
                "requires_prescription": medicine.requires_prescription,
                "is_controlled_substance": medicine.is_controlled_substance,
                "description": medicine.description,
                "storage_instructions": medicine.storage_instructions,
                "created_at": str(medicine.created_at),
                "updated_at": str(medicine.updated_at)
            }
        }
    ).dict()


@router.post("")
async def create_medicine(
    medicine_data: MedicineCreate,
    current_user: User = Depends(require_admin_or_pharmacist()),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new medicine"""
    service = PharmacyService(db)
    medicine = await service.create_medicine(
        hospital_id=current_user.hospital_id,
        **medicine_data.dict()
    )
    await db.commit()
    
    return SuccessResponse(
        success=True,
        message="Medicine created successfully",
        data={"medicine_id": str(medicine.id)}
    ).dict()


@router.put("/{medicine_id}")
async def update_medicine(
    medicine_id: UUID,
    medicine_data: MedicineUpdate,
    current_user: User = Depends(require_admin_or_pharmacist()),
    db: AsyncSession = Depends(get_db_session)
):
    """Update medicine details"""
    service = PharmacyService(db)
    updates = {k: v for k, v in medicine_data.dict().items() if v is not None}
    medicine = await service.update_medicine(
        medicine_id=medicine_id,
        hospital_id=current_user.hospital_id,
        **updates
    )
    await db.commit()
    
    return SuccessResponse(
        success=True,
        message="Medicine updated successfully",
        data={"medicine_id": str(medicine.id)}
    ).dict()


@router.delete("/{medicine_id}")
async def delete_medicine(
    medicine_id: UUID,
    current_user: User = Depends(require_admin_or_pharmacist()),
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete a medicine"""
    service = PharmacyService(db)
    medicine = await service.get_medicine(medicine_id, current_user.hospital_id)
    medicine.is_active = False
    await db.commit()
    
    return SuccessResponse(
        success=True,
        message="Medicine deleted successfully",
        data={"medicine_id": str(medicine_id)}
    ).dict()
