import uuid
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_current_user, require_roles
from app.models.user import User
from app.core.enums import UserRole
from app.schemas.response import SuccessResponse
from app.schemas.user_management import (
    UserManagementCreate,
    UserManagementUpdate,
    UserStatusUpdate,
)
from app.services.user_management_service import UserManagementService

router = APIRouter(prefix="", tags=["User Management"])


def _safe_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(str(value))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}. Must be a valid UUID."
        )


async def get_target_hospital_id_for_user_management(
    hospital_id: str | None = Query(None, description="Required for Super Admin"),
    current_user: User = Depends(get_current_user),
) -> UUID:
    role_names = [r.name for r in (current_user.roles or [])]

    if UserRole.HOSPITAL_ADMIN in role_names:
        if not current_user.hospital_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hospital Admin has no hospital context"
            )
        return current_user.hospital_id

    if UserRole.SUPER_ADMIN in role_names:
        if not hospital_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="hospital_id is required for Super Admin"
            )
        return _safe_uuid(hospital_id, "hospital_id")

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied"
    )


@router.get("/users")
async def list_users(
    current_user: User = Depends(require_roles(UserRole.HOSPITAL_ADMIN, UserRole.SUPER_ADMIN)),
    target_hospital_id: UUID = Depends(get_target_hospital_id_for_user_management),
    db: AsyncSession = Depends(get_db_session),
):
    service = UserManagementService(db, target_hospital_id)
    data = await service.list_users()
    return SuccessResponse(success=True, message="Users retrieved successfully", data=data).dict()


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserManagementCreate,
    current_user: User = Depends(require_roles(UserRole.HOSPITAL_ADMIN, UserRole.SUPER_ADMIN)),
    target_hospital_id: UUID = Depends(get_target_hospital_id_for_user_management),
    db: AsyncSession = Depends(get_db_session),
):
    service = UserManagementService(db, target_hospital_id)
    try:
        data = await service.create_user(body.model_dump())
        return SuccessResponse(success=True, message="User created successfully", data=data).dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UserManagementUpdate,
    current_user: User = Depends(require_roles(UserRole.HOSPITAL_ADMIN, UserRole.SUPER_ADMIN)),
    target_hospital_id: UUID = Depends(get_target_hospital_id_for_user_management),
    db: AsyncSession = Depends(get_db_session),
):
    _safe_uuid(user_id, "user_id")
    service = UserManagementService(db, target_hospital_id)
    try:
        data = await service.update_user(user_id, body.model_dump(exclude_none=True))
        return SuccessResponse(success=True, message="User updated successfully", data=data).dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_roles(UserRole.HOSPITAL_ADMIN, UserRole.SUPER_ADMIN)),
    target_hospital_id: UUID = Depends(get_target_hospital_id_for_user_management),
    db: AsyncSession = Depends(get_db_session),
):
    _safe_uuid(user_id, "user_id")
    service = UserManagementService(db, target_hospital_id)
    try:
        data = await service.delete_user(user_id)
        return SuccessResponse(success=True, message="User deleted successfully", data=data).dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    body: UserStatusUpdate,
    current_user: User = Depends(require_roles(UserRole.HOSPITAL_ADMIN, UserRole.SUPER_ADMIN)),
    target_hospital_id: UUID = Depends(get_target_hospital_id_for_user_management),
    db: AsyncSession = Depends(get_db_session),
):
    _safe_uuid(user_id, "user_id")
    service = UserManagementService(db, target_hospital_id)
    try:
        data = await service.update_user_status(user_id, body.status)
        return SuccessResponse(success=True, message="User status updated successfully", data=data).dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/roles")
async def list_roles(
    current_user: User = Depends(require_roles(UserRole.HOSPITAL_ADMIN, UserRole.SUPER_ADMIN)),
    target_hospital_id: UUID = Depends(get_target_hospital_id_for_user_management),
    db: AsyncSession = Depends(get_db_session),
):
    service = UserManagementService(db, target_hospital_id)
    data = await service.list_roles()
    return SuccessResponse(success=True, message="Roles retrieved successfully", data=data).dict()


@router.get("/departments")
async def list_departments(
    current_user: User = Depends(require_roles(UserRole.HOSPITAL_ADMIN, UserRole.SUPER_ADMIN)),
    target_hospital_id: UUID = Depends(get_target_hospital_id_for_user_management),
    db: AsyncSession = Depends(get_db_session),
):
    service = UserManagementService(db, target_hospital_id)
    data = await service.list_departments()
    return SuccessResponse(success=True, message="Departments retrieved successfully", data=data).dict()


@router.get("/dashboard/stats")
async def dashboard_stats(
    current_user: User = Depends(require_roles(UserRole.HOSPITAL_ADMIN, UserRole.SUPER_ADMIN)),
    target_hospital_id: UUID = Depends(get_target_hospital_id_for_user_management),
    db: AsyncSession = Depends(get_db_session),
):
    service = UserManagementService(db, target_hospital_id)
    data = await service.dashboard_stats()
    return SuccessResponse(success=True, message="Dashboard stats retrieved successfully", data=data).dict()