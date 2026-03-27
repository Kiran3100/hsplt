"""
Lab Test Data Seed Script
=========================
Populates the database with sample lab data for endpoint testing.

Run from project root:
    python scripts/seed_lab_test_data.py

Prerequisites:
- Database running (PostgreSQL)
- .env with DATABASE_URL
- At least one hospital exists (run app once to seed superadmin/hospital)

After running, use the printed IDs to test endpoints in Swagger (/docs) or Postman.
Login as a user with LAB_TECH role for the same hospital.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime
from decimal import Decimal

# Project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


async def seed_lab_data():
    from sqlalchemy import select, desc
    from app.database.session import AsyncSessionLocal
    from app.models.tenant import Hospital
    from app.models.user import User, Role, user_roles
    from app.models.lab import (
        LabTestCategory,
        LabTest,
        LabOrder,
        LabOrderItem,
        Sample,
        SampleOrderItem,
        TestResult,
        ResultValue,
        Equipment,
    )
    from app.core.enums import (
        SampleType,
        LabOrderSource,
        LabOrderPriority,
        LabOrderStatus,
        LabOrderItemStatus,
        SampleStatus,
        ContainerType,
        ResultStatus,
    )

    print("=" * 60)
    print("LAB TEST DATA SEED")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # 1. Get first hospital
        hospital_result = await db.execute(select(Hospital).limit(1))
        hospital = hospital_result.scalar_one_or_none()
        if not hospital:
            print("ERROR: No hospital found. Run the app once to seed superadmin/hospital.")
            return
        hospital_id = hospital.id
        print(f"Hospital: {hospital.name} ({hospital_id})")

        # 2. Get or create LAB_TECH user for this hospital
        lab_role_result = await db.execute(select(Role).where(Role.name == "LAB_TECH"))
        lab_role = lab_role_result.scalar_one_or_none()
        if not lab_role:
            print("ERROR: LAB_TECH role not found. Run app to seed roles.")
            return

        user_result = await db.execute(
            select(User)
            .join(user_roles, User.id == user_roles.c.user_id)
            .where(user_roles.c.role_id == lab_role.id)
            .where(User.hospital_id == hospital_id)
            .limit(1)
        )
        lab_user = user_result.scalar_one_or_none()
        if not lab_user:
            from app.core.security import SecurityManager
            lab_user = User(
                id=uuid.uuid4(),
                hospital_id=hospital_id,
                email="labtech@test.com",
                phone="+1999999999",
                password_hash=SecurityManager.hash_password("LabTech123!"),
                first_name="Lab",
                last_name="Technician",
                staff_id="LAB01",
                status="ACTIVE",
            )
            db.add(lab_user)
            await db.flush()
            await db.execute(user_roles.insert().values(user_id=lab_user.id, role_id=lab_role.id))
            await db.commit()
            await db.refresh(lab_user)
            print(f"Created LAB_TECH user: {lab_user.email} (id={lab_user.id})")
        else:
            print(f"LAB_TECH user: {lab_user.email} (id={lab_user.id})")

        # 3. Create categories
        categories_data = [
            {"category_code": "HEMA", "name": "Hematology", "description": "Blood tests", "display_order": 1},
            {"category_code": "BIO", "name": "Biochemistry", "description": "Chemistry tests", "display_order": 2},
        ]
        category_ids = {}
        for c in categories_data:
            existing = await db.execute(
                select(LabTestCategory).where(
                    LabTestCategory.hospital_id == hospital_id,
                    LabTestCategory.category_code == c["category_code"],
                )
            )
            cat = existing.scalar_one_or_none()
            if not cat:
                cat = LabTestCategory(
                    id=uuid.uuid4(),
                    hospital_id=hospital_id,
                    category_code=c["category_code"],
                    name=c["name"],
                    description=c.get("description"),
                    display_order=c.get("display_order", 0),
                )
                db.add(cat)
                await db.flush()
            category_ids[c["category_code"]] = cat.id
        await db.commit()
        print(f"Categories: HEMA={category_ids.get('HEMA')}, BIO={category_ids.get('BIO')}")

        # 4. Create tests
        tests_data = [
            {
                "test_code": "CBC",
                "test_name": "Complete Blood Count",
                "category_code": "HEMA",
                "sample_type": SampleType.BLOOD,
                "turnaround_hours": 6,
                "price": 350.00,
                "unit": "g/dL",
                "reference_ranges": {"HB": "12-16", "WBC": "4-11", "Platelets": "150-400"},
            },
            {
                "test_code": "TSH",
                "test_name": "Thyroid Stimulating Hormone",
                "category_code": "BIO",
                "sample_type": SampleType.BLOOD,
                "turnaround_hours": 24,
                "price": 450.00,
                "unit": "mIU/L",
                "reference_ranges": {"TSH": "0.4-4.0"},
            },
            {
                "test_code": "RBS",
                "test_name": "Random Blood Sugar",
                "category_code": "BIO",
                "sample_type": SampleType.BLOOD,
                "turnaround_hours": 2,
                "price": 150.00,
                "unit": "mg/dL",
                "reference_ranges": {"Glucose": "70-140"},
            },
        ]
        test_ids = {}
        for t in tests_data:
            existing = await db.execute(
                select(LabTest).where(
                    LabTest.hospital_id == hospital_id,
                    LabTest.test_code == t["test_code"],
                )
            )
            test = existing.scalar_one_or_none()
            if not test:
                test = LabTest(
                    id=uuid.uuid4(),
                    hospital_id=hospital_id,
                    category_id=category_ids.get(t["category_code"]),
                    test_code=t["test_code"],
                    test_name=t["test_name"],
                    sample_type=t["sample_type"].value,
                    turnaround_time_hours=t["turnaround_hours"],
                    price=Decimal(str(t["price"])),
                    unit=t.get("unit"),
                    reference_ranges=t.get("reference_ranges", {}),
                )
                db.add(test)
                await db.flush()
            test_ids[t["test_code"]] = test.id
        await db.commit()
        print(f"Tests: CBC={test_ids.get('CBC')}, TSH={test_ids.get('TSH')}, RBS={test_ids.get('RBS')}")

        # 5. Create lab order (generate unique order number)
        year = datetime.now().year
        max_result = await db.execute(
            select(LabOrder.lab_order_no).where(
                LabOrder.hospital_id == hospital_id,
                LabOrder.lab_order_no.like(f"LAB-{year}-%"),
            ).order_by(desc(LabOrder.lab_order_no)).limit(1)
        )
        last_no = max_result.scalar_one_or_none()
        seq = 10001 if not last_no else int(last_no.split("-")[-1]) + 1
        order = LabOrder(
            id=uuid.uuid4(),
            hospital_id=hospital_id,
            lab_order_no=f"LAB-{year}-{seq:05d}",
            patient_id=str(uuid.uuid4()),  # Use UUID string (some flows expect valid UUID)
            requested_by_doctor_id=str(uuid.uuid4()),
            source=LabOrderSource.WALKIN.value,
            priority=LabOrderPriority.ROUTINE.value,
            status=LabOrderStatus.REGISTERED.value,
            notes="Fever and fatigue - routine checkup",
        )
        db.add(order)
        await db.flush()

        items = []
        for code in ["CBC", "TSH"]:
            item = LabOrderItem(
                id=uuid.uuid4(),
                lab_order_id=order.id,
                test_id=test_ids[code],
                status=LabOrderItemStatus.REGISTERED.value,
            )
            db.add(item)
            await db.flush()
            items.append((code, item))
        await db.commit()
        print(f"Order: {order.lab_order_no} (id={order.id})")
        for code, item in items:
            print(f"  - Order item {code}: {item.id}")

        # 6. Create samples
        barcode = f"SMP-{uuid.uuid4().hex[:8].upper()}"
        sample_no = f"SMP-{uuid.uuid4().hex[:12].upper()}"  # Unique per hospital
        sample = Sample(
            id=uuid.uuid4(),
            hospital_id=hospital_id,
            lab_order_id=order.id,
            patient_id=order.patient_id,
            sample_type=SampleType.BLOOD.value,
            container_type=ContainerType.EDTA.value,
            sample_no=sample_no,
            barcode_value=barcode,
            status=SampleStatus.IN_PROCESS.value,
            volume_ml=5.0,
        )
        db.add(sample)
        await db.flush()

        for code, oi in items:
            soi = SampleOrderItem(
                id=uuid.uuid4(),
                sample_id=sample.id,
                lab_order_item_id=oi.id,
            )
            db.add(soi)
        await db.commit()
        print(f"Sample: {sample.barcode_value} (id={sample.id})")

        # 7. Create results for each order item
        result_values_map = {
            "CBC": [
                {"parameter_name": "HB", "value": "13.2", "unit": "g/dL", "reference_range": "12-16"},
                {"parameter_name": "WBC", "value": "7.5", "unit": "cells/uL", "reference_range": "4-11"},
                {"parameter_name": "Platelets", "value": "220", "unit": "x10^9/L", "reference_range": "150-400"},
            ],
            "TSH": [
                {"parameter_name": "TSH", "value": "2.1", "unit": "mIU/L", "reference_range": "0.4-4.0"},
            ],
        }
        result_ids = []
        for code, oi in items:
            result = TestResult(
                id=uuid.uuid4(),
                hospital_id=hospital_id,
                lab_order_item_id=oi.id,
                sample_id=sample.id,
                status=ResultStatus.DRAFT.value,
                entered_by=lab_user.id,
            )
            db.add(result)
            await db.flush()
            for v in result_values_map.get(code, []):
                rv = ResultValue(
                    id=uuid.uuid4(),
                    test_result_id=result.id,
                    parameter_name=v["parameter_name"],
                    value=v["value"],
                    unit=v.get("unit"),
                    reference_range=v.get("reference_range"),
                )
                db.add(rv)
            result_ids.append((code, result.id))
        await db.commit()
        print("Results created:")
        for code, rid in result_ids:
            print(f"  - {code}: {rid}")

        # 8. Create equipment (optional - skip EquipmentTestMap if table schema differs)
        equip = await db.execute(
            select(Equipment).where(
                Equipment.hospital_id == hospital_id,
                Equipment.equipment_code == "HEMA-001",
            )
        )
        equip_obj = equip.scalar_one_or_none()
        if not equip_obj:
            equip_obj = Equipment(
                id=uuid.uuid4(),
                hospital_id=hospital_id,
                equipment_code="HEMA-001",
                name="Automated Hematology Analyzer",
                category="HEMATOLOGY",
                manufacturer="Sysmex",
                model="XN-1000",
                status="ACTIVE",
            )
            db.add(equip_obj)
            await db.commit()
            print(f"Equipment: HEMA-001 (id={equip_obj.id})")

    # Print summary for testing
    print()
    print("=" * 60)
    print("TEST DATA SUMMARY - Use these for API testing")
    print("=" * 60)
    print(f"Hospital ID:     {hospital_id}")
    print(f"Lab User ID:      {lab_user.id}")
    print(f"Lab User Email:  {lab_user.email}  (password: LabTech123! - use for POST /api/v1/auth/login)")
    print(f"Category HEMA:   {category_ids.get('HEMA')}")
    print(f"Category BIO:    {category_ids.get('BIO')}")
    print(f"Test CBC:        {test_ids.get('CBC')}")
    print(f"Test TSH:        {test_ids.get('TSH')}")
    print(f"Test RBS:        {test_ids.get('RBS')}")
    print(f"Lab Order:       {order.id}")
    print(f"Order Ref:       {order.lab_order_no}")
    print(f"Sample:          {sample.id}")
    for code, rid in result_ids:
        print(f"Result {code}:      {rid}")
    print()
    print("Example API calls (after login with Bearer token):")
    print(f"  GET  /api/v1/lab/registration/categories")
    print(f"  GET  /api/v1/lab/registration/tests")
    print(f"  GET  /api/v1/lab/registration/orders")
    print(f"  GET  /api/v1/lab/samples?page=1&limit=10")
    print(f"  GET  /api/v1/lab/result-entry/worklist")
    print(f"  GET  /api/v1/lab/result-entry/orders/{order.id}/results")
    print(f"  POST /api/v1/lab/result-entry/orders/{order.id}/reports")
    print(f"  GET  /api/v1/lab/equipment-qc/equipment")
    print(f"  GET  /api/v1/lab/audit/lab/analytics/dashboard-summary")
    print("=" * 60)


def main():
    asyncio.run(seed_lab_data())


if __name__ == "__main__":
    main()
