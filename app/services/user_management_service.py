import uuid
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, Role
from app.models.hospital import Department, StaffDepartmentAssignment
from app.models.patient import PatientProfile
from app.core.enums import UserRole, UserStatus


class UserManagementService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def _resolve_role(self, role_value: str) -> Role:
        if not role_value:
            raise ValueError("role_id is required")

        try:
            role_uuid = uuid.UUID(str(role_value))
            role = await self.db.get(Role, role_uuid)
            if role:
                return role
        except Exception:
            pass

        result = await self.db.execute(
            select(Role).where(Role.name.ilike(str(role_value).strip()))
        )
        role = result.scalar_one_or_none()
        if not role:
            raise ValueError("Invalid role_id or role name")
        return role

    async def _resolve_department(self, department_value: str) -> Department:
        if not department_value:
            raise ValueError("department_id is required")

        try:
            dept_uuid = uuid.UUID(str(department_value))
            department = await self.db.get(Department, dept_uuid)
            if department and department.hospital_id == self.hospital_id:
                return department
        except Exception:
            pass

        result = await self.db.execute(
            select(Department).where(
                and_(
                    Department.hospital_id == self.hospital_id,
                    Department.name.ilike(str(department_value).strip()),
                    Department.is_active == True
                )
            )
        )
        department = result.scalar_one_or_none()
        if not department:
            raise ValueError("Invalid department_id or department name")
        return department

    async def list_roles(self):
        result = await self.db.execute(
            select(Role).order_by(Role.display_name.asc())
        )
        roles = result.scalars().all()
        return [
            {
                "id": str(role.id),
                "name": role.name,
                "display_name": role.display_name,
            }
            for role in roles
        ]

    async def list_departments(self):
        result = await self.db.execute(
            select(Department)
            .where(
                and_(
                    Department.hospital_id == self.hospital_id,
                    Department.is_active == True
                )
            )
            .order_by(Department.name.asc())
        )
        departments = result.scalars().all()
        return [
            {
                "id": str(dept.id),
                "name": dept.name,
                "code": dept.code,
            }
            for dept in departments
        ]

    async def list_users(self):
        result = await self.db.execute(
            select(User)
            .where(User.hospital_id == self.hospital_id)
            .options(selectinload(User.roles))
            .order_by(User.created_at.desc())
        )
        users = result.scalars().all()
        return [await self._serialize_user(user) for user in users]

    async def create_user(self, payload: dict):
        email = payload["email"].lower().strip()

        existing = await self.db.execute(
            select(User).where(User.email == email)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Email already exists")

        role = await self._resolve_role(payload["role_id"])
        department = await self._resolve_department(payload["department_id"])

        name_parts = payload["full_name"].strip().split()
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "-"

        status_value = payload.get("status", "ACTIVE").upper()
        mapped_status = UserStatus.ACTIVE if status_value == "ACTIVE" else UserStatus.INACTIVE

        user = User(
            hospital_id=self.hospital_id,
            email=email,
            phone=payload["phone"],
            password_hash="TEMP_PASSWORD_CHANGE_ME",
            first_name=first_name,
            last_name=last_name,
            status=mapped_status,
            avatar_url=payload.get("profile_image"),
            email_verified=True,
            password_changed_at=datetime.utcnow(),
        )
        self.db.add(user)
        await self.db.flush()

        user.roles.append(role)
        await self.db.flush()

        if role.name == UserRole.PATIENT:
            patient_profile = PatientProfile(
                hospital_id=self.hospital_id,
                user_id=user.id,
                patient_id=f"PAT-{str(user.id)[:8].upper()}",
                date_of_birth=None,
                gender=None,
            )
            self.db.add(patient_profile)
        else:
            assignment = StaffDepartmentAssignment(
                hospital_id=self.hospital_id,
                staff_id=user.id,
                department_id=department.id,
                is_primary=True,
                effective_from=datetime.utcnow(),
                is_active=True,
            )
            self.db.add(assignment)

        await self.db.commit()
        await self.db.refresh(user)
        return await self._serialize_user(user)

    async def update_user(self, user_id: str, payload: dict):
        result = await self.db.execute(
            select(User)
            .where(
                and_(
                    User.id == uuid.UUID(user_id),
                    User.hospital_id == self.hospital_id,
                    User.is_active == True
                )
            )
            .options(selectinload(User.roles))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        if "email" in payload and payload["email"]:
            email = payload["email"].lower().strip()
            existing = await self.db.execute(
                select(User).where(
                    and_(
                        User.email == email,
                        User.id != user.id
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError("Email already exists")
            user.email = email

        if "full_name" in payload and payload["full_name"]:
            name_parts = payload["full_name"].strip().split()
            user.first_name = name_parts[0]
            user.last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "-"

        if "phone" in payload and payload["phone"] is not None:
            user.phone = payload["phone"]

        if "profile_image" in payload:
            user.avatar_url = payload["profile_image"]

        if "status" in payload and payload["status"]:
            user.status = UserStatus.ACTIVE if payload["status"].upper() == "ACTIVE" else UserStatus.INACTIVE

        if "role_id" in payload and payload["role_id"]:
            role = await self._resolve_role(payload["role_id"])
            user.roles = [role]

        if "department_id" in payload and payload["department_id"]:
            department = await self._resolve_department(payload["department_id"])

            role_names = [r.name for r in user.roles]
            if UserRole.PATIENT not in role_names:
                assignment_result = await self.db.execute(
                    select(StaffDepartmentAssignment)
                    .where(
                        and_(
                            StaffDepartmentAssignment.staff_id == user.id,
                            StaffDepartmentAssignment.hospital_id == self.hospital_id,
                            StaffDepartmentAssignment.is_primary == True
                        )
                    )
                )
                assignment = assignment_result.scalar_one_or_none()

                if assignment:
                    assignment.department_id = department.id
                else:
                    self.db.add(
                        StaffDepartmentAssignment(
                            hospital_id=self.hospital_id,
                            staff_id=user.id,
                            department_id=department.id,
                            is_primary=True,
                            effective_from=datetime.utcnow(),
                            is_active=True,
                        )
                    )

        await self.db.commit()
        await self.db.refresh(user)
        return await self._serialize_user(user)

    async def delete_user(self, user_id: str):
        result = await self.db.execute(
            select(User).where(
                and_(
                    User.id == uuid.UUID(user_id),
                    User.hospital_id == self.hospital_id
                )
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        user.is_active = False
        user.status = UserStatus.INACTIVE
        await self.db.commit()

        return {
            "id": str(user.id),
            "message": "User deleted successfully"
        }

    async def update_user_status(self, user_id: str, status_value: str):
        result = await self.db.execute(
            select(User).where(
                and_(
                    User.id == uuid.UUID(user_id),
                    User.hospital_id == self.hospital_id
                )
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        user.status = UserStatus.ACTIVE if status_value.upper() == "ACTIVE" else UserStatus.INACTIVE
        await self.db.commit()

        return {
            "id": str(user.id),
            "status": "ACTIVE" if user.status == UserStatus.ACTIVE else "INACTIVE"
        }

    async def dashboard_stats(self):
        result = await self.db.execute(
            select(User)
            .where(
                and_(
                    User.hospital_id == self.hospital_id,
                    User.is_active == True
                )
            )
            .options(selectinload(User.roles))
        )
        users = result.scalars().all()

        total_admins = 0
        total_doctors = 0
        total_staff = 0
        total_patients = 0

        for user in users:
            role_names = [r.name for r in user.roles]
            if UserRole.HOSPITAL_ADMIN in role_names or UserRole.SUPER_ADMIN in role_names:
                total_admins += 1
            elif UserRole.DOCTOR in role_names:
                total_doctors += 1
            elif UserRole.PATIENT in role_names:
                total_patients += 1
            else:
                total_staff += 1

        return {
            "total_admins": total_admins,
            "total_doctors": total_doctors,
            "total_staff": total_staff,
            "total_patients": total_patients,
            "total_users": len(users),
        }

    async def _serialize_user(self, user: User):
        role = user.roles[0] if user.roles else None
        role_names = [r.name for r in user.roles]

        department_id = None
        department_name = None

        if UserRole.PATIENT not in role_names:
            assignment_result = await self.db.execute(
                select(StaffDepartmentAssignment)
                .where(
                    and_(
                        StaffDepartmentAssignment.staff_id == user.id,
                        StaffDepartmentAssignment.hospital_id == self.hospital_id,
                        StaffDepartmentAssignment.is_primary == True
                    )
                )
                .options(selectinload(StaffDepartmentAssignment.department))
            )
            assignment = assignment_result.scalar_one_or_none()
            if assignment and assignment.department:
                department_id = str(assignment.department.id)
                department_name = assignment.department.name

        return {
            "id": str(user.id),
            "full_name": f"{user.first_name} {user.last_name}".strip(),
            "email": user.email,
            "phone": user.phone,
            "role_id": str(role.id) if role else "",
            "role_name": role.name if role else "",
            "department_id": department_id,
            "department_name": department_name,
            "status": "ACTIVE" if user.status == UserStatus.ACTIVE else "INACTIVE",
            "profile_image": user.avatar_url,
            "joined_date": user.created_at.date().isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }