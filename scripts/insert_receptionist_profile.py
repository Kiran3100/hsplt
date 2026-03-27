"""
Insert Receptionist Profile for a User
======================================
Creates a ReceptionistProfile row for a user who has RECEPTIONIST role but no profile.

Run from project root:
    python scripts/insert_receptionist_profile.py

User ID: b78241c8-242c-428e-ba55-33f431f53df8 (Priya Sharma)
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime

# Project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

USER_ID = "b78241c8-242c-428e-ba55-33f431f53df8"


async def insert_receptionist_profile():
    from sqlalchemy import select
    from app.database.session import AsyncSessionLocal
    from app.models.user import User
    from app.models.receptionist import ReceptionistProfile
    from app.models.hospital import Department

    print("=" * 60)
    print("INSERT RECEPTIONIST PROFILE")
    print("=" * 60)

    user_uuid = uuid.UUID(USER_ID)

    async with AsyncSessionLocal() as db:
        # 1. Get user
        user_result = await db.execute(select(User).where(User.id == user_uuid))
        user = user_result.scalar_one_or_none()
        if not user:
            print(f"ERROR: User {USER_ID} not found.")
            return
        if not user.hospital_id:
            print("ERROR: User has no hospital_id. Assign hospital first.")
            return
        hospital_id = user.hospital_id
        print(f"User: {user.first_name} {user.last_name} ({user.email})")
        print(f"Hospital ID: {hospital_id}")

        # 2. Check if profile already exists
        existing = await db.execute(
            select(ReceptionistProfile).where(ReceptionistProfile.user_id == user_uuid)
        )
        if existing.scalar_one_or_none():
            print("Profile already exists. Nothing to do.")
            return

        # 3. Get first department in hospital
        dept_result = await db.execute(
            select(Department)
            .where(Department.hospital_id == hospital_id)
            .where(Department.is_active == True)
            .limit(1)
        )
        department = dept_result.scalar_one_or_none()
        if not department:
            print("ERROR: No active department found in this hospital. Create a department first.")
            return
        department_id = department.id
        print(f"Department: {department.name} ({department_id})")

        # 4. Generate unique IDs (use timestamp to avoid collisions)
        ts = datetime.now().strftime("%Y%m%d%H%M")
        receptionist_id = f"REC-{ts}"
        employee_id = f"EMP-{user_uuid.hex[:8].upper()}"

        # 5. Create ReceptionistProfile
        profile = ReceptionistProfile(
            id=uuid.uuid4(),
            hospital_id=hospital_id,
            user_id=user_uuid,
            department_id=department_id,
            receptionist_id=receptionist_id,
            employee_id=employee_id,
            designation="Front Desk Receptionist",
            work_area="OPD",
            experience_years=0,
            shift_type="DAY",
            employment_type="FULL_TIME",
            can_schedule_appointments=True,
            can_modify_appointments=True,
            can_register_patients=True,
            can_collect_payments=False,
            is_active=True,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

        print(f"\nSUCCESS: Receptionist profile created.")
        print(f"  receptionist_id: {profile.receptionist_id}")
        print(f"  employee_id: {profile.employee_id}")
        print(f"  designation: {profile.designation}")
        print(f"\nGET /receptionist/profile should now return full profile.")


if __name__ == "__main__":
    asyncio.run(insert_receptionist_profile())
