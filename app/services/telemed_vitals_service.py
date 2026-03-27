"""
Telemedicine remote vitals. Patient/doctor entry.
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.patient import PatientProfile
from app.repositories.telemed_repository import TelemedVitalsRepository

VALID_VITALS_TYPES = {"BP", "HR", "SPO2", "TEMP", "WEIGHT", "GLUCOSE"}


class TelemedVitalsService:
    """Remote vitals - patient (self) or doctor can enter."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_vitals(
        self,
        hospital_id: uuid.UUID,
        patient_id: uuid.UUID,
        user_id: uuid.UUID,
        user_roles: List[str],
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        vitals_type: Optional[str] = None,
    ) -> List:
        # Patient: own vitals only. Doctor/staff: any patient in hospital.
        if "PATIENT" in user_roles:
            patient = (
                await self.db.execute(
                    select(PatientProfile).where(
                        PatientProfile.user_id == user_id,
                        PatientProfile.hospital_id == hospital_id,
                    )
                )
            ).scalar_one_or_none()
            if not patient or patient.id != patient_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        else:
            # Doctor/receptionist/admin: verify patient in hospital
            patient = (
                await self.db.execute(
                    select(PatientProfile).where(
                        PatientProfile.id == patient_id,
                        PatientProfile.hospital_id == hospital_id,
                    )
                )
            ).scalar_one_or_none()
            if not patient:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

        repo = TelemedVitalsRepository(self.db, hospital_id)
        return await repo.list_for_patient(
            patient_id=patient_id,
            from_date=from_date,
            to_date=to_date,
            vitals_type=vitals_type,
        )

    async def create_vital(
        self,
        hospital_id: uuid.UUID,
        patient_id: uuid.UUID,
        vitals_type: str,
        value_json: str,
        entered_by: uuid.UUID,
        user_roles: List[str],
        session_id: Optional[uuid.UUID] = None,
        recorded_at: Optional[datetime] = None,
    ):
        if vitals_type not in VALID_VITALS_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid vitals_type. Must be one of: {', '.join(VALID_VITALS_TYPES)}",
            )
        # Patient: can enter for self only
        if "PATIENT" in user_roles:
            patient = (
                await self.db.execute(
                    select(PatientProfile).where(
                        PatientProfile.user_id == entered_by,
                        PatientProfile.hospital_id == hospital_id,
                    )
                )
            ).scalar_one_or_none()
            if not patient or patient.id != patient_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patients can only enter vitals for themselves")
        else:
            patient = (
                await self.db.execute(
                    select(PatientProfile).where(
                        PatientProfile.id == patient_id,
                        PatientProfile.hospital_id == hospital_id,
                    )
                )
            ).scalar_one_or_none()
            if not patient:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

        repo = TelemedVitalsRepository(self.db, hospital_id)
        return await repo.create(
            patient_id=patient_id,
            vitals_type=vitals_type,
            value_json=value_json,
            entered_by=entered_by,
            session_id=session_id,
            recorded_at=recorded_at,
        )
