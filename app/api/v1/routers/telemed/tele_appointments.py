"""
Tele-appointment API - standalone telemedicine scheduling.
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db_session
from app.models.doctor import DoctorProfile
from app.api.deps import get_current_user, require_doctor, require_receptionist, require_patient, require_hospital_context
from app.models.user import User
from app.models.patient import PatientProfile
from app.schemas.telemed import (
    TeleAppointmentCreate,
    TeleAppointmentReschedule,
    TeleAppointmentCancel,
    TeleAppointmentResponse,
    TeleAppointmentListResponse,
)
from app.schemas.response import SuccessResponse
from app.services.telemed_appointment_service import TeleAppointmentService

router = APIRouter(prefix="/tele-appointments", tags=["Telemedicine - Appointments"])


def _to_response(apt) -> dict:
    doctor = getattr(apt, "doctor", None)
    doctor_ref = getattr(doctor, "doctor_id", None) if doctor and hasattr(doctor, "doctor_id") else None
    doctor_name = None
    if doctor:
        doctor_name = f"{getattr(doctor, 'first_name', '') or ''} {getattr(doctor, 'last_name', '') or ''}".strip() or None
    return {
        "id": str(apt.id),
        "hospital_id": str(apt.hospital_id),
        "patient_id": str(apt.patient_id),
        "patient_ref": getattr(getattr(apt, "patient", None), "patient_id", None),
        "doctor_id": str(apt.doctor_id),
        "doctor_ref": doctor_ref,
        "doctor_name": doctor_name,
        "scheduled_start": apt.scheduled_start.isoformat() if apt.scheduled_start else None,
        "scheduled_end": apt.scheduled_end.isoformat() if apt.scheduled_end else None,
        "reason": apt.reason,
        "notes": apt.notes,
        "status": apt.status,
        "created_by": str(apt.created_by),
        "created_at": apt.created_at.isoformat() if apt.created_at else None,
        "updated_at": apt.updated_at.isoformat() if apt.updated_at else None,
    }


@router.post("", response_model=dict)
async def create_tele_appointment(
    body: TeleAppointmentCreate,
    context: dict = Depends(require_hospital_context),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create tele-appointment.
    Receptionist: any. Doctor: own only (optional). Patient: self only (optional).
    """
    hospital_id = uuid.UUID(context["hospital_id"])
    user_roles = context.get("roles", [])
    created_by = current_user.id

    # Resolve patient by reference within this hospital
    patient_result = await db.execute(
        select(PatientProfile).where(
            PatientProfile.hospital_id == hospital_id,
            PatientProfile.patient_id == body.patient_ref,
        )
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found for this hospital and reference",
        )

    # Patient: must create for self (enforce that this patient profile belongs to current user)
    if "PATIENT" in user_roles:
        if patient.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only create appointments for themselves",
            )
    # Receptionist: can create for any
    elif "RECEPTIONIST" not in user_roles and "DOCTOR" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only receptionists, doctors, or patients can create tele-appointments"
        )

    # Resolve doctor_ref (DOC-xxx, UUID, or doctor name) to doctor user id
    doctor_ref = (body.doctor_ref or getattr(body, "doctor_id", None) or "").strip()
    if not doctor_ref:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="doctor_ref is required")
    try:
        uid = uuid.UUID(doctor_ref)
        doc_q = select(DoctorProfile).where(
            DoctorProfile.hospital_id == hospital_id,
            or_(DoctorProfile.user_id == uid, DoctorProfile.id == uid),
        ).limit(1)
    except ValueError:
        doc_q = (
            select(DoctorProfile)
            .join(User, DoctorProfile.user_id == User.id)
            .where(
                DoctorProfile.hospital_id == hospital_id,
                or_(
                    DoctorProfile.doctor_id == doctor_ref,
                    User.first_name.ilike(f"%{doctor_ref}%"),
                    User.last_name.ilike(f"%{doctor_ref}%"),
                )
            )
        ).limit(1)
    doc_r = await db.execute(doc_q)
    doctor_profile = doc_r.scalar_one_or_none()
    if not doctor_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Doctor not found: {doctor_ref}")
    doctor_user_id = doctor_profile.user_id

    service = TeleAppointmentService(db)
    try:
        apt = await service.create(
            hospital_id=hospital_id,
            patient_id=patient.id,
            doctor_id=doctor_user_id,
            scheduled_start=body.scheduled_start,
            scheduled_end=body.scheduled_end,
            created_by=created_by,
            reason=body.reason,
            notes=body.notes,
        )
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        err_str = str(e.orig) if hasattr(e, "orig") and e.orig else str(e)
        if "uq_tele_appointments_no_overlap" in err_str or "exclusion" in err_str.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "TELE_APPOINTMENT_OVERLAP", "message": "Doctor has another appointment in this time slot"},
            ) from e
        raise
    return SuccessResponse(
        success=True,
        message="Tele-appointment created",
        data=_to_response(apt),
    ).dict()


@router.get("", response_model=dict)
async def list_tele_appointments(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    context: dict = Depends(require_hospital_context),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List tele-appointments. Role-filtered: patient=own, doctor=assigned, receptionist=all."""
    hospital_id = uuid.UUID(context["hospital_id"])
    user_roles = context.get("roles", [])
    service = TeleAppointmentService(db)

    if "PATIENT" in user_roles:
        patient_result = await db.execute(
            select(PatientProfile).where(PatientProfile.user_id == current_user.id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
        items = await service.list_for_patient(hospital_id, patient.id, status_filter)
    elif "DOCTOR" in user_roles:
        items = await service.list_for_doctor(hospital_id, current_user.id, status_filter)
    elif "RECEPTIONIST" in user_roles or "HOSPITAL_ADMIN" in user_roles:
        items = await service.list_for_receptionist(hospital_id, status_filter)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return SuccessResponse(
        success=True,
        message="Tele-appointments retrieved",
        data={"items": [_to_response(i) for i in items], "total": len(items)},
    ).dict()


@router.get("/{tele_appointment_id}", response_model=dict)
async def get_tele_appointment(
    tele_appointment_id: str,
    context: dict = Depends(require_hospital_context),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get tele-appointment by ID. Role-filtered access."""
    hospital_id = uuid.UUID(context["hospital_id"])
    user_roles = context.get("roles", [])
    service = TeleAppointmentService(db)
    apt = await service.get_by_id(uuid.UUID(tele_appointment_id), hospital_id)
    if not apt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tele-appointment not found")
    if "PATIENT" in user_roles:
        patient_result = await db.execute(
            select(PatientProfile).where(PatientProfile.user_id == current_user.id)
        )
        patient = patient_result.scalar_one_or_none()
        if patient and apt.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif "DOCTOR" in user_roles and apt.doctor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return SuccessResponse(
        success=True,
        message="Tele-appointment retrieved",
        data=_to_response(apt),
    ).dict()


@router.post("/{tele_appointment_id}/reschedule", response_model=dict)
async def reschedule_tele_appointment(
    tele_appointment_id: str,
    body: TeleAppointmentReschedule,
    context: dict = Depends(require_hospital_context),
    current_user: User = Depends(require_receptionist()),
    db: AsyncSession = Depends(get_db_session),
):
    """Reschedule tele-appointment. Receptionist only."""
    hospital_id = uuid.UUID(context["hospital_id"])
    service = TeleAppointmentService(db)
    apt = await service.reschedule(
        uuid.UUID(tele_appointment_id),
        hospital_id,
        body.scheduled_start,
        body.scheduled_end,
        body.reason,
    )
    await db.commit()
    return SuccessResponse(
        success=True,
        message="Tele-appointment rescheduled",
        data=_to_response(apt),
    ).dict()


@router.post("/{tele_appointment_id}/cancel", response_model=dict)
async def cancel_tele_appointment(
    tele_appointment_id: str,
    body: Optional[TeleAppointmentCancel] = None,
    context: dict = Depends(require_hospital_context),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Cancel tele-appointment. Receptionist or doctor or patient (own)."""
    hospital_id = uuid.UUID(context["hospital_id"])
    user_roles = [r.name for r in (current_user.roles or [])]
    service = TeleAppointmentService(db)
    apt = await service.get_by_id(uuid.UUID(tele_appointment_id), hospital_id)
    if not apt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tele-appointment not found")
    if "RECEPTIONIST" not in user_roles and "HOSPITAL_ADMIN" not in user_roles:
        if "DOCTOR" in user_roles and apt.doctor_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if "PATIENT" in user_roles:
            patient_result = await db.execute(
                select(PatientProfile).where(PatientProfile.user_id == current_user.id)
            )
            patient = patient_result.scalar_one_or_none()
            if not patient or apt.patient_id != patient.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    reason = body.cancellation_reason if body is not None else None
    apt = await service.cancel(uuid.UUID(tele_appointment_id), hospital_id, current_user.id, reason)
    await db.commit()
    return SuccessResponse(
        success=True,
        message="Tele-appointment cancelled",
        data=_to_response(apt),
    ).dict()


@router.post("/{tele_appointment_id}/confirm", response_model=dict)
async def confirm_tele_appointment(
    tele_appointment_id: str,
    context: dict = Depends(require_hospital_context),
    current_user: User = Depends(require_receptionist()),
    db: AsyncSession = Depends(get_db_session),
):
    """Confirm tele-appointment. Receptionist only."""
    hospital_id = uuid.UUID(context["hospital_id"])
    service = TeleAppointmentService(db)
    apt = await service.confirm(uuid.UUID(tele_appointment_id), hospital_id)
    await db.commit()
    return SuccessResponse(
        success=True,
        message="Tele-appointment confirmed",
        data=_to_response(apt),
    ).dict()
