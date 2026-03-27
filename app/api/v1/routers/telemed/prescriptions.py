"""
Telemedicine prescriptions - create/sign and PDF download.
No pharmacy DB: doctor enters medicine name + directions; patient can download PDF.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.api.deps import get_current_user, require_hospital_context
from app.models.user import User
from app.models.patient import PatientProfile
from app.models.tenant import Hospital
from app.models.prescription import TelePrescription
from app.schemas.response import SuccessResponse
from app.services.telemed_prescription_service import TelemedPrescriptionService
from app.services.prescription_pdf_service import generate_prescription_pdf
from app.core.enums import UserRole

router = APIRouter(prefix="/prescriptions", tags=["Telemedicine - Prescriptions"])


class TelemedPrescriptionMedicineInput(BaseModel):
    """Single medicine line for telemed prescription (no pharmacy linkage)."""
    medicine_name: str = Field(..., min_length=1, description="Free-text medicine name")
    medicine_strength: Optional[str] = Field(None, description="e.g. 500mg")
    medicine_form: Optional[str] = Field(None, description="TABLET, SYRUP, etc.")
    dose: str = Field(..., min_length=1, description="e.g. 1 tablet")
    frequency: str = Field(..., min_length=1, description="e.g. 1-0-1")
    duration_days: int = Field(..., ge=1)
    instructions: Optional[str] = Field(None, description="Extra instructions (after food, etc.)")
    quantity: Optional[int] = Field(None, ge=1)
    quantity_unit: Optional[str] = Field(None, description="tablets, bottles, etc.")


class TelemedPrescriptionCreate(BaseModel):
    """Create telemed prescription for a telemed session (no pharmacy integration)."""
    diagnosis: str = Field(..., min_length=1)
    clinical_notes: Optional[str] = None
    follow_up_date: Optional[str] = Field(
        None, description="YYYY-MM-DD follow-up date (optional)"
    )
    medicines: List[TelemedPrescriptionMedicineInput] = Field(
        default_factory=list, description="Medicine lines with free-text names"
    )


@router.post("/session/{session_id}", response_model=dict)
async def create_prescription_for_session(
    session_id: str,
    body: TelemedPrescriptionCreate,
    context: dict = Depends(require_hospital_context),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create telemedicine prescription for a session.

    - No pharmacy integration (no pharmacy tables touched)
    - Doctor types medicine name + dosage manually
    - Status: DRAFT (doctor can sign later)
    """
    roles = [r.name for r in (current_user.roles or [])]
    if UserRole.DOCTOR.value not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can create telemedicine prescriptions",
        )

    hospital_id = uuid.UUID(context["hospital_id"])
    service = TelemedPrescriptionService(db)
    rx = await service.create_for_session(
        hospital_id=hospital_id,
        session_id=uuid.UUID(session_id),
        doctor_id=current_user.id,
        diagnosis=body.diagnosis,
        clinical_notes=body.clinical_notes,
        follow_up_date=body.follow_up_date,
        medicines=[m.model_dump() for m in body.medicines],
    )
    await db.commit()
    return SuccessResponse(
        success=True,
        message="Telemed prescription created",
        data={
            "id": str(rx.id),
            "prescription_no": rx.prescription_no,
            "status": rx.status,
            "session_id": str(rx.session_id) if rx.session_id else None,
        },
    ).dict()


@router.get("/me", response_model=dict)
async def list_my_telemed_prescriptions(
    context: dict = Depends(require_hospital_context),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Patient: list own telemedicine prescriptions and tests to do.

    - Uses PatientProfile linked to current user
    - Returns prescriptions with medicines and lab tests (names only, no pharmacy IDs)
    """
    roles = [r.name for r in (current_user.roles or [])]
    if UserRole.PATIENT.value not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can view their own telemedicine prescriptions",
        )

    hospital_id = uuid.UUID(context["hospital_id"])
    # Find patient profile for current user in this hospital
    patient_result = await db.execute(
        select(PatientProfile).where(
            PatientProfile.user_id == current_user.id,
            PatientProfile.hospital_id == hospital_id,
        )
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found for current user",
        )

    # Load prescriptions with medicines and lab orders
    rx_result = await db.execute(
        select(TelePrescription)
        .where(
            TelePrescription.hospital_id == hospital_id,
            TelePrescription.patient_id == patient.id,
        )
        .options(
            selectinload(TelePrescription.medicines),
            selectinload(TelePrescription.lab_orders),
        )
        .order_by(TelePrescription.created_at.desc())
    )
    items = rx_result.scalars().all()

    prescriptions: List[dict] = []
    for rx in items:
        meds = [
            {
                "medicine_name": m.medicine_name,
                "medicine_strength": m.medicine_strength,
                "medicine_form": m.medicine_form,
                "dose": m.dose,
                "frequency": m.frequency,
                "duration_days": m.duration_days,
                "instructions": m.instructions,
                "quantity": m.quantity,
                "quantity_unit": m.quantity_unit,
            }
            for m in (rx.medicines or [])
        ]
        tests = [
            {
                "test_name": t.test_name,
                "test_code": t.test_code,
                "test_category": t.test_category,
                "urgency": t.urgency,
                "sent_to_lab": t.sent_to_lab,
            }
            for t in (rx.lab_orders or [])
        ]
        prescriptions.append(
            {
                "id": str(rx.id),
                "prescription_no": rx.prescription_no,
                "status": rx.status,
                "diagnosis": rx.diagnosis,
                "clinical_notes": rx.clinical_notes,
                "follow_up_date": rx.follow_up_date,
                "created_at": rx.created_at.isoformat() if rx.created_at else None,
                "medicines": meds,
                "tests": tests,
            }
        )

    return SuccessResponse(
        success=True,
        message=f"Found {len(prescriptions)} telemed prescription(s)",
        data={"prescriptions": prescriptions},
    ).dict()

@router.post("/{prescription_id}/sign", response_model=dict)
async def sign_prescription(
    prescription_id: str,
    context: dict = Depends(require_hospital_context),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Sign prescription. Prescribing doctor only."""
    hospital_id = uuid.UUID(context["hospital_id"])
    service = TelemedPrescriptionService(db)
    rx = await service.sign(hospital_id, uuid.UUID(prescription_id), current_user.id)
    await db.commit()
    return SuccessResponse(
        success=True,
        message="Prescription signed",
        data={
            "id": str(rx.id),
            "prescription_no": rx.prescription_no,
            "status": rx.status,
            "signed_at": rx.signed_at.isoformat() if rx.signed_at else None,
        },
    ).dict()


@router.get("/{prescription_id}/pdf")
async def get_telemed_prescription_pdf(
    prescription_id: str,
    context: dict = Depends(require_hospital_context),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Download telemed prescription as PDF (no pharmacy integration).
    RBAC: Patient can only download their own; Doctor can download their own prescriptions.
    """
    hospital_id = uuid.UUID(context["hospital_id"])
    rx_id = uuid.UUID(prescription_id)
    roles = [r.name for r in (current_user.roles or [])]

    rx_result = await db.execute(
        select(TelePrescription)
        .where(
            TelePrescription.id == rx_id,
            TelePrescription.hospital_id == hospital_id,
        )
        .options(
            selectinload(TelePrescription.medicines),
            selectinload(TelePrescription.patient).selectinload(PatientProfile.user),
            selectinload(TelePrescription.doctor),
        )
    )
    rx = rx_result.scalar_one_or_none()
    if not rx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")

    if UserRole.PATIENT.value in roles:
        if rx.patient.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only download your own prescriptions",
            )
    elif UserRole.DOCTOR.value in roles:
        if rx.doctor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only download prescriptions you created",
            )
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    hospital_result = await db.execute(select(Hospital).where(Hospital.id == rx.hospital_id))
    hospital = hospital_result.scalar_one_or_none()
    hospital_dict = {
        "name": hospital.name if hospital else "Hospital",
        "address": hospital.address if hospital else "",
        "city": hospital.city if hospital else "",
        "state": hospital.state if hospital else "",
        "pincode": hospital.pincode if hospital else "",
        "phone": hospital.phone if hospital else "",
        "email": hospital.email if hospital else "",
    }

    patient_name = f"{rx.patient.user.first_name} {rx.patient.user.last_name}"
    doctor_name = f"Dr. {rx.doctor.first_name} {rx.doctor.last_name}"
    prescription_date = rx.created_at.strftime("%Y-%m-%d") if rx.created_at else ""

    # Map PrescriptionMedicine (telemed, no pharmacy) to PDF payload
    medications = []
    for m in rx.medicines or []:
        medications.append({
            "generic_name": m.medicine_name,
            "brand_name": m.medicine_name,
            "strength": m.medicine_strength,
            "dosage_text": m.dose,
            "frequency": m.frequency,
            "duration_days": m.duration_days,
            "instructions": m.instructions,
            "quantity": m.quantity,
        })

    pdf_bytes = generate_prescription_pdf(
        hospital=hospital_dict,
        doctor_name=doctor_name,
        patient_name=patient_name,
        patient_ref=getattr(rx.patient, "patient_id", None),
        prescription_number=rx.prescription_no,
        prescription_id=str(rx.id),
        prescription_date=prescription_date,
        diagnosis=rx.diagnosis,
        medications=medications,
        general_instructions=rx.clinical_notes,
        diet_instructions=None,
        follow_up_date=rx.follow_up_date,
    )

    filename = f"telemed_prescription_{rx.prescription_no or prescription_id}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


