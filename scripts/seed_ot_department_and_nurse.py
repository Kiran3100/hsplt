"""
Seed OT Department and Nurse
============================
Creates Operation Theatre (OT) department and assigns a nurse to it.
Enables surgery video upload (nurse must be in OT department).

Run from project root:
    python scripts/seed_ot_department_and_nurse.py

Prerequisites:
- Database running (PostgreSQL)
- .env with DATABASE_URL
- At least one hospital exists (run app once to seed superadmin/hospital)
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

# Project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


async def seed_ot_and_nurse():
    from sqlalchemy import select
    from app.database.session import AsyncSessionLocal
    from app.models.tenant import Hospital
    from app.models.user import User, Role, user_roles
    from app.models.hospital import Department, StaffDepartmentAssignment

    print("=" * 60)
    print("SEED OT DEPARTMENT AND NURSE")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # 1. Get first active hospital
        hospitals_result = await db.execute(
            select(Hospital).where(Hospital.is_active == True).limit(1)
        )
        hospital = hospitals_result.scalar_one_or_none()
        if not hospital:
            print("ERROR: No hospital found. Run the app once to seed superadmin/hospital.")
            return
        hospital_id = hospital.id
        print(f"Hospital: {hospital.name} ({hospital_id})")

        # 2. Get or create OT department
        ot_result = await db.execute(
            select(Department).where(
                Department.hospital_id == hospital_id,
                Department.code == "OT",
            )
        )
        ot_dept = ot_result.scalar_one_or_none()
        if not ot_dept:
            ot_dept = Department(
                id=uuid.uuid4(),
                hospital_id=hospital_id,
                name="Operation Theatre",
                code="OT",
                description="Surgical operations and procedures",
                is_24x7=True,
                is_active=True,
            )
            db.add(ot_dept)
            await db.flush()
            print(f"  Created OT department: {ot_dept.name} (code: {ot_dept.code})")
        else:
            print(f"  OT department exists: {ot_dept.name}")

        # 3. Get NURSE role
        nurse_role_result = await db.execute(select(Role).where(Role.name == "NURSE"))
        nurse_role = nurse_role_result.scalar_one_or_none()
        if not nurse_role:
            print("ERROR: NURSE role not found. Run app to seed roles.")
            return

        # 4. Get or create nurse user
        nurse_result = await db.execute(
            select(User)
            .join(user_roles, User.id == user_roles.c.user_id)
            .where(user_roles.c.role_id == nurse_role.id)
            .where(User.hospital_id == hospital_id)
            .limit(1)
        )
        nurse_user = nurse_result.scalar_one_or_none()
        if not nurse_user:
            from app.core.security import SecurityManager
            nurse_user = User(
                id=uuid.uuid4(),
                hospital_id=hospital_id,
                email="nurse.ot@test.com",
                phone="+1999888666",
                password_hash=SecurityManager.hash_password("NurseOT123!"),
                first_name="OT",
                last_name="Nurse",
                staff_id="NURSE-OT1",
                status="ACTIVE",
            )
            db.add(nurse_user)
            await db.flush()
            await db.execute(
                user_roles.insert().values(user_id=nurse_user.id, role_id=nurse_role.id)
            )
            print(f"  Created nurse user: {nurse_user.email}")
        else:
            print(f"  Nurse user exists: {nurse_user.email}")

        # 5. Assign nurse to OT department (StaffDepartmentAssignment)
        existing_assignment = await db.execute(
            select(StaffDepartmentAssignment).where(
                StaffDepartmentAssignment.staff_id == nurse_user.id,
                StaffDepartmentAssignment.hospital_id == hospital_id,
                StaffDepartmentAssignment.department_id == ot_dept.id,
                StaffDepartmentAssignment.is_active == True,
            )
        )
        if existing_assignment.scalar_one_or_none():
            print("  Nurse already assigned to OT department.")
        else:
            assignment = StaffDepartmentAssignment(
                id=uuid.uuid4(),
                hospital_id=hospital_id,
                staff_id=nurse_user.id,
                department_id=ot_dept.id,
                is_primary=True,
                effective_from=datetime.now(timezone.utc),
                is_active=True,
            )
            db.add(assignment)
            print("  Assigned nurse to OT department.")

        await db.commit()

    print("\nSUCCESS: OT department and nurse ready.")
    print("  Login: nurse.ot@test.com / NurseOT123!")
    print("  Use POST /surgery/nurse/cases/{surgery_id}/video?patient_ref=PAT-XXX to upload videos.")


if __name__ == "__main__":
    asyncio.run(seed_ot_and_nurse())
