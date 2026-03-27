"""
Pharmacy Data Seed Script
=========================
Populates the database with sample pharmacy data for endpoint testing.

Run from project root:
    python scripts/seed_pharmacy_data.py

Prerequisites:
- Database running (PostgreSQL)
- .env with DATABASE_URL
- At least one hospital exists (run app once to seed superadmin/hospital)

After running:
- Medicines, suppliers, stock batches will be created
- Use PHARMACIST or HOSPITAL_ADMIN user for the same hospital to test
- Doctor can search medicines at GET /api/v1/simple-prescription/doctor/medicines/search
- Pharmacist can dispense prescriptions at POST /api/v1/simple-prescription/pharmacist/prescriptions/{id}/dispense
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal

# Project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


async def seed_pharmacy_data():
    from sqlalchemy import select
    from app.database.session import AsyncSessionLocal
    from app.models.tenant import Hospital
    from app.models.user import User, Role, user_roles
    from app.models.pharmacy import Medicine, Supplier, StockBatch
    from app.services.pharmacy_service import PharmacyService

    print("=" * 60)
    print("PHARMACY DATA SEED")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # 1. Get ALL active hospitals (seed for every hospital so any user sees data)
        hospitals_result = await db.execute(
            select(Hospital).where(Hospital.is_active == True)
        )
        hospitals = hospitals_result.scalars().all()
        if not hospitals:
            print("ERROR: No hospital found. Run the app once to seed superadmin/hospital.")
            return
        print(f"Found {len(hospitals)} hospital(s). Seeding pharmacy data for each...")

        # 2. Get PHARMACIST role
        pharmacist_role_result = await db.execute(select(Role).where(Role.name == "PHARMACIST"))
        pharmacist_role = pharmacist_role_result.scalar_one_or_none()
        if not pharmacist_role:
            print("ERROR: PHARMACIST role not found. Run app to seed roles.")
            return

        for idx, hospital in enumerate(hospitals):
            hospital_id = hospital.id
            print(f"\n--- Hospital: {hospital.name} ({hospital_id}) ---")

            # Get or create PHARMACIST user for this hospital (unique email per hospital)
            pharm_email = f"pharmacist_h{idx + 1}@test.com" if idx > 0 else "pharmacist@test.com"
            user_result = await db.execute(
                select(User)
                .join(user_roles, User.id == user_roles.c.user_id)
                .where(user_roles.c.role_id == pharmacist_role.id)
                .where(User.hospital_id == hospital_id)
                .limit(1)
            )
            pharmacist_user = user_result.scalar_one_or_none()
            if not pharmacist_user:
                from app.core.security import SecurityManager
                pharmacist_user = User(
                    id=uuid.uuid4(),
                    hospital_id=hospital_id,
                    email=pharm_email,
                    phone="+1999888777",
                    password_hash=SecurityManager.hash_password("Pharmacist123!"),
                    first_name="Pharmacy",
                    last_name="Staff",
                    staff_id="PHARM01",
                    status="ACTIVE",
                )
                db.add(pharmacist_user)
                await db.flush()
                await db.execute(user_roles.insert().values(user_id=pharmacist_user.id, role_id=pharmacist_role.id))
                await db.commit()
                await db.refresh(pharmacist_user)
                print(f"  Created PHARMACIST: {pharmacist_user.email}")
            else:
                print(f"  PHARMACIST: {pharmacist_user.email}")

            service = PharmacyService(db)

            # 3. Create medicines
            medicines_data = [
            {
                "generic_name": "Paracetamol",
                "brand_name": "Crocin",
                "dosage_form": "TABLET",
                "strength": "500mg",
                "composition": "Paracetamol 500mg",
                "manufacturer": "GSK",
                "category": "PAINKILLER",
                "drug_class": "Antipyretic",
                "route": "ORAL",
                "pack_size": 10,
                "reorder_level": 50,
                "sku": "PAR-500-TAB",
                "requires_prescription": False,
            },
            {
                "generic_name": "Amoxicillin",
                "brand_name": "Amoxil",
                "dosage_form": "CAPSULE",
                "strength": "500mg",
                "composition": "Amoxicillin trihydrate 500mg",
                "manufacturer": "Sun Pharma",
                "category": "ANTIBIOTIC",
                "drug_class": "Penicillin",
                "route": "ORAL",
                "pack_size": 10,
                "reorder_level": 30,
                "sku": "AMX-500-CAP",
                "requires_prescription": True,
            },
            {
                "generic_name": "Omeprazole",
                "brand_name": "Omez",
                "dosage_form": "CAPSULE",
                "strength": "20mg",
                "composition": "Omeprazole 20mg",
                "manufacturer": "Dr Reddy's",
                "category": "ANTACID",
                "drug_class": "Proton pump inhibitor",
                "route": "ORAL",
                "pack_size": 14,
                "reorder_level": 40,
                "sku": "OME-20-CAP",
                "requires_prescription": False,
            },
            {
                "generic_name": "Cetirizine",
                "brand_name": "Zyrtec",
                "dosage_form": "TABLET",
                "strength": "10mg",
                "composition": "Cetirizine hydrochloride 10mg",
                "manufacturer": "Johnson & Johnson",
                "category": "ANTIHISTAMINE",
                "drug_class": "H1 antagonist",
                "route": "ORAL",
                "pack_size": 10,
                "reorder_level": 25,
                "sku": "CET-10-TAB",
                "requires_prescription": False,
            },
            {
                "generic_name": "Metformin",
                "brand_name": "Glucophage",
                "dosage_form": "TABLET",
                "strength": "500mg",
                "composition": "Metformin hydrochloride 500mg",
                "manufacturer": "Merck",
                "category": "ANTIDIABETIC",
                "drug_class": "Biguanide",
                "route": "ORAL",
                "pack_size": 30,
                "reorder_level": 60,
                "sku": "MET-500-TAB",
                "requires_prescription": True,
            },
            ]

            medicine_ids = {}
            for m in medicines_data:
                existing = await db.execute(
                    select(Medicine).where(
                        Medicine.hospital_id == hospital_id,
                        Medicine.sku == m.get("sku"),
                    )
                )
                med = existing.scalar_one_or_none()
                if not med:
                    med = await service.create_medicine(
                        hospital_id=hospital_id,
                        generic_name=m["generic_name"],
                        brand_name=m["brand_name"],
                        composition=m.get("composition"),
                        dosage_form=m["dosage_form"],
                        strength=m.get("strength"),
                        manufacturer=m.get("manufacturer"),
                        category=m.get("category"),
                        drug_class=m.get("drug_class"),
                        route=m.get("route"),
                        pack_size=m.get("pack_size"),
                        reorder_level=m.get("reorder_level", 10),
                        sku=m.get("sku"),
                        requires_prescription=m.get("requires_prescription", False),
                    )
                    await db.flush()
                medicine_ids[m["sku"]] = med.id
            await db.commit()
            print(f"  Medicines: {len(medicine_ids)} created/found")

            # 4. Create suppliers
            suppliers_data = [
            {
                "name": "MedPlus Wholesale",
                "phone": "+911234567890",
                "email": "orders@medpluswholesale.com",
                "contact_person": "Rajesh Kumar",
                "address_line1": "123 Pharma Park",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001",
                "gstin": "27AABCU9603R1ZM",
                "payment_terms": "NET_30",
                "rating": 5,
            },
            {
                "name": "Apollo Pharmacy Supply",
                "phone": "+919876543210",
                "email": "supply@apollopharma.in",
                "contact_person": "Priya Sharma",
                "address_line1": "456 Medical Hub",
                "city": "Chennai",
                "state": "Tamil Nadu",
                "pincode": "600001",
                "gstin": "33AABCA1234M1Z5",
                "payment_terms": "NET_15",
                "rating": 4,
            },
            ]

            supplier_ids = []
            for s in suppliers_data:
                existing = await db.execute(
                    select(Supplier).where(
                        Supplier.hospital_id == hospital_id,
                        Supplier.name == s["name"],
                    )
                )
                sup = existing.scalar_one_or_none()
                if not sup:
                    sup = await service.create_supplier(
                        hospital_id=hospital_id,
                        name=s["name"],
                        phone=s["phone"],
                        email=s.get("email"),
                        contact_person=s.get("contact_person"),
                        address_line1=s.get("address_line1"),
                        city=s.get("city"),
                        state=s.get("state"),
                        pincode=s.get("pincode"),
                        gstin=s.get("gstin"),
                        payment_terms=s.get("payment_terms", "NET_30"),
                        rating=s.get("rating"),
                    )
                    await db.flush()
                supplier_ids.append(sup.id)
            await db.commit()
            print(f"  Suppliers: {len(supplier_ids)} created/found")

            # 5. Create GRN with items and finalize (creates stock batches)
            expiry_future = (date.today() + timedelta(days=365)).isoformat()
            grn_items = []
            for sku, med_id in medicine_ids.items():
                grn_items.append({
                    "medicine_id": med_id,
                    "batch_no": f"BATCH-{sku}-001",
                    "expiry_date": expiry_future,
                    "received_qty": 100,
                    "free_qty": 0,
                    "purchase_rate": 5.00,
                    "mrp": 12.00,
                    "selling_price": 10.00,
                    "tax_percent": 5,
                })

            # Check if we already have stock for this hospital
            stock_result = await db.execute(
                select(StockBatch).where(
                    StockBatch.hospital_id == hospital_id,
                ).limit(1)
            )
            has_stock = stock_result.scalar_one_or_none() is not None

            if not has_stock and supplier_ids and medicine_ids:
                grn = await service.create_grn(
                    hospital_id=hospital_id,
                    received_by=pharmacist_user.id,
                    supplier_id=supplier_ids[0],
                    received_at=datetime.utcnow(),
                    notes="Initial stock seed",
                    items=grn_items,
                )
                await db.flush()
                result = await service.finalize_grn(grn.id, hospital_id, pharmacist_user.id)
                await db.commit()
                print(f"  GRN finalized: {grn.grn_number} -> {len(result.get('batches_created', []))} stock batches")
            else:
                await db.commit()
                if has_stock:
                    print("  Stock batches already exist. Skipping GRN.")
                else:
                    print("  Could not create GRN (missing supplier or medicines).")

        # Summary
        print("\n" + "=" * 60)
        print("SEED COMPLETE")
        print("=" * 60)
        print("Pharmacy data seeded for ALL hospitals.")
        print("Login with any user (Doctor/Pharmacist/Admin) from your hospital.")
        print("Password for pharmacist@* users: Pharmacist123!")
        print("\nTest flow:")
        print("  1. GET  /api/v1/pharmacy/medicines")
        print("  2. GET  /api/v1/simple-prescription/doctor/medicines/search?query=paracetamol")
        print("  3. POST /api/v1/simple-prescription/doctor/prescriptions/create")
        print("  4. POST /api/v1/simple-prescription/pharmacist/prescriptions/{id}/dispense (reduces stock)")


if __name__ == "__main__":
    asyncio.run(seed_pharmacy_data())
