"""
Full Hospital Seed Data
=======================
Seeds one hospital with: departments, staff (all roles), patients, appointments,
billing (tax, services, OPD bill), and optional IPD (ward, bed, admission).

Run from project root:
    python scripts/seed_full_hospital_data.py

Prerequisites:
- Database running (PostgreSQL)
- .env with DATABASE_URL
- App run at least once (superadmin + roles + Platform Hospital exist)
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, date, time, timezone, timedelta
from decimal import Decimal

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Default password for all seeded users
SEED_PASSWORD = "SeedUser123!"


async def seed_full_hospital():
    from sqlalchemy import select, func
    from sqlalchemy.orm import selectinload
    from app.database.session import AsyncSessionLocal
    from app.models.tenant import Hospital
    from app.models.user import User, Role, user_roles
    from app.models.hospital import Department, StaffDepartmentAssignment, Ward, Bed
    from app.models.patient import PatientProfile, Appointment, Admission
    from app.models.doctor import DoctorProfile
    from app.models.receptionist import ReceptionistProfile
    from app.models.billing import Bill, BillItem, TaxProfile, ServiceItem
    from app.repositories.billing.billing_repository import BillingRepository
    from app.core.security import SecurityManager
    from app.core.enums import AppointmentStatus

    print("=" * 60)
    print("FULL HOSPITAL SEED DATA")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # --- 1. Hospital ---
        r = await db.execute(select(Hospital).where(Hospital.is_active == True).limit(1))
        hospital = r.scalar_one_or_none()
        if not hospital:
            print("ERROR: No hospital found. Run the app once to seed superadmin/hospital.")
            return
        hospital_id = hospital.id
        print(f"Hospital: {hospital.name} ({hospital_id})")

        # --- 2. Roles ---
        role_names = ["HOSPITAL_ADMIN", "DOCTOR", "NURSE", "RECEPTIONIST", "PHARMACIST", "LAB_TECH", "PATIENT"]
        roles = {}
        for name in role_names:
            rr = await db.execute(select(Role).where(Role.name == name))
            rl = rr.scalar_one_or_none()
            if not rl:
                print(f"ERROR: Role {name} not found. Run app to seed roles.")
                return
            roles[name] = rl

        # --- 3. Departments ---
        dept_specs = [
            ("General Medicine", "GEN", "General OPD"),
            ("Cardiology", "CARD", "Cardiology"),
            ("Operation Theatre", "OT", "Surgical OT"),
            ("Emergency", "ER", "Emergency"),
        ]
        departments = {}
        for name, code, desc in dept_specs:
            dr = await db.execute(
                select(Department).where(
                    Department.hospital_id == hospital_id,
                    Department.code == code,
                )
            )
            d = dr.scalar_one_or_none()
            if not d:
                d = Department(
                    id=uuid.uuid4(),
                    hospital_id=hospital_id,
                    name=name,
                    code=code,
                    description=desc,
                    is_24x7=(code == "ER" or code == "OT"),
                    is_active=True,
                )
                db.add(d)
                await db.flush()
            departments[code] = d
        print("  Departments: GEN, CARD, OT, ER")

        # --- 4. Staff users (Hospital Admin, Doctor, Receptionist, Nurse, Pharmacist, Lab Tech) ---
        async def _get_or_create_user(email, first_name, last_name, role_name, staff_id_suffix):
            ur = await db.execute(select(User).where(User.email == email).limit(1))
            u = ur.scalar_one_or_none()
            if u:
                return u
            u = User(
                id=uuid.uuid4(),
                hospital_id=hospital_id,
                email=email,
                phone="+1999000000",
                password_hash=SecurityManager.hash_password(SEED_PASSWORD),
                first_name=first_name,
                last_name=last_name,
                staff_id=staff_id_suffix,
                status="ACTIVE",
            )
            db.add(u)
            await db.flush()
            await db.execute(user_roles.insert().values(user_id=u.id, role_id=roles[role_name].id))
            return u

        admin_user = await _get_or_create_user("admin@seed.com", "Hospital", "Admin", "HOSPITAL_ADMIN", "ADMIN01")
        doctor_user = await _get_or_create_user("doctor@seed.com", "Seed", "Doctor", "DOCTOR", "DOC01")
        receptionist_user = await _get_or_create_user("receptionist@seed.com", "Seed", "Receptionist", "RECEPTIONIST", "REC01")
        nurse_user = await _get_or_create_user("nurse@seed.com", "Seed", "Nurse", "NURSE", "NURSE01")
        pharmacist_user = await _get_or_create_user("pharmacist@seed.com", "Seed", "Pharmacist", "PHARMACIST", "PHARM01")
        labtech_user = await _get_or_create_user("labtech@seed.com", "Seed", "LabTech", "LAB_TECH", "LAB01")
        print("  Staff users: admin, doctor, receptionist, nurse, pharmacist, labtech")

        # DoctorProfile
        dp = await db.execute(select(DoctorProfile).where(DoctorProfile.user_id == doctor_user.id))
        if not dp.scalar_one_or_none():
            doc_prof = DoctorProfile(
                id=uuid.uuid4(),
                hospital_id=hospital_id,
                user_id=doctor_user.id,
                department_id=departments["GEN"].id,
                doctor_id="DOC-SEED-01",
                medical_license_number="ML-SEED-001",
                designation="Consultant",
                specialization="General Medicine",
                consultation_fee=Decimal("500.00"),
                is_active=True,
            )
            db.add(doc_prof)
            await db.flush()
        # StaffDepartmentAssignment for doctor
        for code in ["GEN"]:
            da = await db.execute(
                select(StaffDepartmentAssignment).where(
                    StaffDepartmentAssignment.staff_id == doctor_user.id,
                    StaffDepartmentAssignment.department_id == departments[code].id,
                    StaffDepartmentAssignment.hospital_id == hospital_id,
                )
            )
            if not da.scalar_one_or_none():
                a = StaffDepartmentAssignment(
                    id=uuid.uuid4(),
                    hospital_id=hospital_id,
                    staff_id=doctor_user.id,
                    department_id=departments[code].id,
                    is_primary=True,
                    effective_from=datetime.now(timezone.utc),
                    is_active=True,
                )
                db.add(a)

        # ReceptionistProfile
        rp = await db.execute(select(ReceptionistProfile).where(ReceptionistProfile.user_id == receptionist_user.id))
        if not rp.scalar_one_or_none():
            rec_prof = ReceptionistProfile(
                id=uuid.uuid4(),
                hospital_id=hospital_id,
                user_id=receptionist_user.id,
                department_id=departments["GEN"].id,
                receptionist_id="REC-SEED-01",
                employee_id="EMP-REC01",
                designation="Receptionist",
                work_area="OPD",
                can_schedule_appointments=True,
                can_modify_appointments=True,
                can_register_patients=True,
                can_collect_payments=True,
                is_active=True,
            )
            db.add(rec_prof)
            await db.flush()

        # Nurse + Lab Tech + Pharmacist: StaffDepartmentAssignment only
        for usr, code in [(nurse_user, "GEN"), (labtech_user, "GEN"), (pharmacist_user, "GEN")]:
            da = await db.execute(
                select(StaffDepartmentAssignment).where(
                    StaffDepartmentAssignment.staff_id == usr.id,
                    StaffDepartmentAssignment.hospital_id == hospital_id,
                )
            )
            if not da.scalar_one_or_none():
                a = StaffDepartmentAssignment(
                    id=uuid.uuid4(),
                    hospital_id=hospital_id,
                    staff_id=usr.id,
                    department_id=departments[code].id,
                    is_primary=True,
                    effective_from=datetime.now(timezone.utc),
                    is_active=True,
                )
                db.add(a)

        # --- 5. Patients (User + PatientProfile) ---
        patients_data = [
            ("patient1@seed.com", "John", "Patient", "PAT-JOHN-001"),
            ("patient2@seed.com", "Jane", "Patient", "PAT-JANE-002"),
        ]
        patient_users = []
        for email, fn, ln, pid in patients_data:
            ur = await db.execute(select(User).where(User.email == email).limit(1))
            pu = ur.scalar_one_or_none()
            if not pu:
                pu = User(
                    id=uuid.uuid4(),
                    hospital_id=hospital_id,
                    email=email,
                    phone="+1999111111",
                    password_hash=SecurityManager.hash_password(SEED_PASSWORD),
                    first_name=fn,
                    last_name=ln,
                    status="ACTIVE",
                )
                db.add(pu)
                await db.flush()
                await db.execute(user_roles.insert().values(user_id=pu.id, role_id=roles["PATIENT"].id))
            pr = await db.execute(select(PatientProfile).where(PatientProfile.user_id == pu.id))
            if not pr.scalar_one_or_none():
                pp = PatientProfile(
                    id=uuid.uuid4(),
                    hospital_id=hospital_id,
                    user_id=pu.id,
                    patient_id=pid,
                    mrn=f"MRN-{pid}",
                    is_active=True,
                )
                db.add(pp)
                await db.flush()
                patient_users.append((pu, pp))
            else:
                pp = pr.scalar_one_or_none()
                patient_users.append((pu, pp))
        print("  Patients: PAT-JOHN-001, PAT-JANE-002")

        # --- 6. Appointments (today) ---
        today = date.today().isoformat()
        pat_user, pat_profile = patient_users[0]
        apt = None
        apt_ref = f"APT-SEED-{uuid.uuid4().hex[:8].upper()}"
        ap = await db.execute(select(Appointment).where(Appointment.appointment_ref == apt_ref))
        if not ap.scalar_one_or_none():
            apt = Appointment(
                id=uuid.uuid4(),
                hospital_id=hospital_id,
                appointment_ref=apt_ref,
                patient_id=pat_profile.id,
                doctor_id=doctor_user.id,
                department_id=departments["GEN"].id,
                appointment_date=today,
                appointment_time="10:00:00",
                status=AppointmentStatus.CONFIRMED.value,
                appointment_type="CONSULTATION",
                chief_complaint="Checkup",
                created_by_role="RECEPTIONIST",
                created_by_user=receptionist_user.id,
            )
            db.add(apt)
            await db.flush()
            print(f"  Appointment: {apt_ref} for {today}")
        else:
            apt = (await db.execute(select(Appointment).where(Appointment.hospital_id == hospital_id).limit(1))).scalar_one_or_none()
            if apt:
                apt_ref = apt.appointment_ref
                print(f"  Appointment: using existing {apt_ref}")
        if not apt:
            apt = (await db.execute(select(Appointment).where(Appointment.hospital_id == hospital_id).limit(1))).scalar_one_or_none()

        # --- 7. Billing: TaxProfile, ServiceItem ---
        tx = await db.execute(select(TaxProfile).where(TaxProfile.hospital_id == hospital_id).limit(1))
        tax_profile = tx.scalar_one_or_none()
        if not tax_profile:
            tax_profile = TaxProfile(
                id=uuid.uuid4(),
                hospital_id=hospital_id,
                name="GST 5%",
                gst_percentage=Decimal("5.00"),
                is_active=True,
            )
            db.add(tax_profile)
            await db.flush()
        for code, name, cat, price in [
            ("CONS-01", "Consultation", "CONSULTATION", "500.00"),
            ("LAB-CBC", "CBC Test", "LAB", "300.00"),
            ("PROC-01", "ECG", "PROCEDURE", "400.00"),
        ]:
            sr = await db.execute(
                select(ServiceItem).where(
                    ServiceItem.hospital_id == hospital_id,
                    ServiceItem.code == code,
                )
            )
            if not sr.scalar_one_or_none():
                si = ServiceItem(
                    id=uuid.uuid4(),
                    hospital_id=hospital_id,
                    department_id=departments["GEN"].id,
                    code=code,
                    name=name,
                    category=cat,
                    base_price=Decimal(price),
                    tax_profile_id=tax_profile.id,
                    is_active=True,
                )
                db.add(si)
                await db.flush()
        print("  Billing: TaxProfile, ServiceItems (CONS-01, LAB-CBC, PROC-01)")

        # --- 8. OPD Bill (DRAFT with items, then FINALIZED) ---
        billing_repo = BillingRepository(db, hospital_id)
        bills_exist = await db.execute(
            select(Bill).where(Bill.hospital_id == hospital_id).limit(1)
        )
        if not bills_exist.scalar_one_or_none():
            bill_number = await billing_repo.get_next_bill_number("OPD")
            # Get appointment we created or first one
            apt_for_bill = apt
            if not apt_for_bill:
                apt_result = await db.execute(
                    select(Appointment).where(
                        Appointment.hospital_id == hospital_id,
                        Appointment.patient_id == pat_profile.id,
                    ).limit(1)
                )
                apt_for_bill = apt_result.scalar_one_or_none()
            bill = Bill(
                id=uuid.uuid4(),
                hospital_id=hospital_id,
                bill_number=bill_number,
                bill_type="OPD",
                patient_id=pat_profile.id,
                appointment_id=apt_for_bill.id if apt_for_bill else None,
                admission_id=None,
                status="DRAFT",
                subtotal=Decimal("0"),
                discount_amount=Decimal("0"),
                tax_amount=Decimal("0"),
                total_amount=Decimal("0"),
                amount_paid=Decimal("0"),
                balance_due=Decimal("0"),
                created_by_user_id=receptionist_user.id,
            )
            db.add(bill)
            await db.flush()
            # Add items
            services = await db.execute(
                select(ServiceItem).where(
                    ServiceItem.hospital_id == hospital_id,
                    ServiceItem.code.in_(["CONS-01", "LAB-CBC"]),
                )
            )
            for svc in services.scalars().all():
                unit_price = float(svc.base_price)
                tax_pct = float(tax_profile.gst_percentage) if tax_profile else 0
                line_sub = round(unit_price * 1, 2)
                line_tax = round(line_sub * tax_pct / 100, 2)
                line_tot = line_sub + line_tax
                bi = BillItem(
                    id=uuid.uuid4(),
                    bill_id=bill.id,
                    service_item_id=svc.id,
                    description=svc.name,
                    quantity=Decimal("1"),
                    unit_price=Decimal(str(unit_price)),
                    tax_percentage=Decimal(str(tax_pct)),
                    line_subtotal=Decimal(str(line_sub)),
                    line_tax=Decimal(str(line_tax)),
                    line_total=Decimal(str(line_tot)),
                )
                db.add(bi)
                bill.subtotal += Decimal(str(line_sub))
                bill.tax_amount += Decimal(str(line_tax))
                bill.total_amount += Decimal(str(line_tot))
            bill.balance_due = bill.total_amount - bill.amount_paid
            bill.status = "FINALIZED"
            bill.finalized_by_user_id = receptionist_user.id
            bill.finalized_at = datetime.now(timezone.utc)
            print(f"  OPD Bill: {bill_number} (FINALIZED), total={bill.total_amount}")
        else:
            print("  OPD Bill: already exists, skip")

        # --- 9. Optional: Ward, Bed, Admission (IPD) ---
        wr = await db.execute(select(Ward).where(Ward.hospital_id == hospital_id).limit(1))
        if not wr.scalar_one_or_none():
            ward = Ward(
                id=uuid.uuid4(),
                hospital_id=hospital_id,
                name="General Ward",
                code="GW-1",
                ward_type="GENERAL",
                total_beds=5,
                is_active=True,
            )
            db.add(ward)
            await db.flush()
            bed = Bed(
                id=uuid.uuid4(),
                hospital_id=hospital_id,
                ward_id=ward.id,
                bed_number="101",
                bed_code="GW-1-101",
                status="AVAILABLE",
                bed_type="STANDARD",
                daily_rate=Decimal("1000.00"),
                is_active=True,
            )
            db.add(bed)
            await db.flush()
            adm_number = f"ADM-{date.today().strftime('%Y%m%d')}-001"
            adm = Admission(
                id=uuid.uuid4(),
                hospital_id=hospital_id,
                patient_id=pat_profile.id,
                doctor_id=doctor_user.id,
                department_id=departments["GEN"].id,
                admission_number=adm_number,
                admission_type="IPD",
                admission_date=datetime.now(timezone.utc),
                chief_complaint="Observation",
                is_active=True,
            )
            db.add(adm)
            await db.flush()
            print(f"  IPD: Ward GW-1, Bed 101, Admission {adm_number}")
        else:
            print("  IPD: ward/bed/admission already exist, skip")

        await db.commit()

    print("\n" + "=" * 60)
    print("SEED COMPLETE – One hospital with staff, patients, billing")
    print("=" * 60)
    print("Logins (password for all: " + SEED_PASSWORD + ")")
    print("  Hospital Admin: admin@seed.com")
    print("  Doctor:         doctor@seed.com")
    print("  Receptionist:  receptionist@seed.com")
    print("  Nurse:          nurse@seed.com")
    print("  Pharmacist:     pharmacist@seed.com")
    print("  Lab Tech:       labtech@seed.com")
    print("  Patients:       patient1@seed.com, patient2@seed.com")
    print("Patient refs: PAT-JOHN-001, PAT-JANE-002")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed_full_hospital())
