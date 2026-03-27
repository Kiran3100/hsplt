"""
Telemedicine prescription service. Doctor creates during session.
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.prescription import TelePrescription, PrescriptionMedicine
from app.models.telemedicine import TelemedSession
from app.models.patient import PatientProfile
from app.repositories.telemed_repository import TelemedSessionRepository
from app.services.telemed_notification_service import TelemedNotificationService


def _generate_prescription_no(hospital_id: uuid.UUID) -> str:
    """Generate unique prescription number per hospital."""
    return f"RX-{hospital_id.hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"


class TelemedPrescriptionService:
    """Session-scoped prescriptions. Doctor only."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_for_session(
        self,
        hospital_id: uuid.UUID,
        session_id: uuid.UUID,
        doctor_id: uuid.UUID,
        diagnosis: str,
        clinical_notes: Optional[str] = None,
        follow_up_date: Optional[str] = None,
        medicines: Optional[List[dict]] = None,
    ) -> TelePrescription:
        """Create telemed prescription (no pharmacy DB). Optionally add medicine lines (name + directions only)."""
        repo = TelemedSessionRepository(self.db, hospital_id)
        session = await repo.get_by_id(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        if session.tele_appointment.doctor_id != doctor_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the doctor can create prescriptions")

        apt = session.tele_appointment
        prescription = TelePrescription(
            hospital_id=hospital_id,
            session_id=session_id,
            tele_appointment_id=apt.id,
            prescription_no=_generate_prescription_no(hospital_id),
            doctor_id=doctor_id,
            patient_id=apt.patient_id,
            diagnosis=diagnosis,
            clinical_notes=clinical_notes,
            follow_up_date=follow_up_date,
            status="DRAFT",
        )
        self.db.add(prescription)
        await self.db.flush()
        await self.db.refresh(prescription)

        # Add medicine lines (no pharmacy; doctor-entered name + directions only)
        for item in medicines or []:
            pm = PrescriptionMedicine(
                hospital_id=hospital_id,
                prescription_id=prescription.id,
                medicine_id=None,
                medicine_name=item.get("medicine_name", ""),
                medicine_strength=item.get("medicine_strength"),
                medicine_form=item.get("medicine_form"),
                dose=item.get("dose", ""),
                frequency=item.get("frequency", ""),
                duration_days=item.get("duration_days", 1),
                instructions=item.get("instructions"),
                quantity=item.get("quantity"),
                quantity_unit=item.get("quantity_unit"),
            )
            self.db.add(pm)
        await self.db.flush()
        return prescription

    async def sign(self, hospital_id: uuid.UUID, prescription_id: uuid.UUID, doctor_id: uuid.UUID) -> TelePrescription:
        result = await self.db.execute(
            select(TelePrescription).where(
                TelePrescription.id == prescription_id,
                TelePrescription.hospital_id == hospital_id,
            )
        )
        rx = result.scalar_one_or_none()
        if not rx:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
        if rx.doctor_id != doctor_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the prescribing doctor can sign")
        if rx.status != "DRAFT":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prescription already signed or issued")
        rx.status = "SIGNED"
        rx.signed_at = datetime.utcnow()
        rx.signed_by = doctor_id
        await self.db.flush()
        await self.db.refresh(rx)
        if rx.session_id:
            patient_result = await self.db.execute(
                select(PatientProfile).where(PatientProfile.id == rx.patient_id)
            )
            patient = patient_result.scalar_one_or_none()
            if patient:
                notif = TelemedNotificationService(self.db, hospital_id)
                await notif.notify_prescription_issued(rx.session_id, patient.user_id)
        
        return rx

    async def list_for_patient(
        self,
        hospital_id: uuid.UUID,
        patient_profile_id: uuid.UUID,
        user_id: uuid.UUID,
        is_patient_self: bool,
    ) -> List[TelePrescription]:
        if not is_patient_self:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patients can only view their own prescriptions")
        result = await self.db.execute(
            select(TelePrescription).where(
                TelePrescription.patient_id == patient_profile_id,
                TelePrescription.hospital_id == hospital_id,
            ).order_by(TelePrescription.created_at.desc())
        )
        return list(result.scalars().all())
