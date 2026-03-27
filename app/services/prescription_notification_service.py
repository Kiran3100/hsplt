"""
In-app prescription notifications (no SMS/email).
Creates PrescriptionNotification for Patient, Receptionist, Pharmacy on submit and dispensed.
Calls are non-blocking when used from BackgroundTasks; failures are logged.
"""
import uuid
import logging
from typing import List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.doctor import Prescription, PrescriptionNotification
from app.models.user import User
from app.models.patient import PatientProfile
from app.core.enums import UserRole

logger = logging.getLogger(__name__)

EVENT_PRESCRIPTION_SUBMITTED = "PRESCRIPTION_SUBMITTED"
EVENT_PRESCRIPTION_DISPENSED = "PRESCRIPTION_DISPENSED"


async def get_user_ids_by_roles(
    db: AsyncSession, hospital_id: uuid.UUID, role_names: List[str]
) -> List[uuid.UUID]:
    """Return user IDs for users in this hospital with any of the given role names."""
    from app.models.user import user_roles, Role

    result = await db.execute(
        select(User.id)
        .select_from(User)
        .join(user_roles, User.id == user_roles.c.user_id)
        .join(Role, user_roles.c.role_id == Role.id)
        .where(
            and_(
                User.hospital_id == hospital_id,
                User.is_active == True,
                Role.name.in_(role_names),
            )
        )
        .distinct()
    )
    return [row[0] for row in result.all()]


async def create_notification(
    db: AsyncSession,
    hospital_id: uuid.UUID,
    recipient_user_id: uuid.UUID,
    prescription_id: uuid.UUID,
    event_type: str,
    title: str,
    body: str,
) -> None:
    """Create one PrescriptionNotification. Does not commit."""
    n = PrescriptionNotification(
        hospital_id=hospital_id,
        recipient_user_id=recipient_user_id,
        prescription_id=prescription_id,
        event_type=event_type,
        title=title,
        body=body,
    )
    db.add(n)


async def notify_prescription_submitted(
    db: AsyncSession, prescription_id: uuid.UUID, hospital_id: uuid.UUID
) -> None:
    """
    Create in-app notifications for Patient, Receptionist, Pharmacy when prescription is submitted.
    Does not commit; caller must commit.
    """
    result = await db.execute(
        select(Prescription)
        .where(
            and_(
                Prescription.id == prescription_id,
                Prescription.hospital_id == hospital_id,
            )
        )
        .options(selectinload(Prescription.patient).selectinload(PatientProfile.user))
    )
    prescription = result.scalar_one_or_none()
    if not prescription or not prescription.patient:
        return
    patient_user_id = prescription.patient.user_id
    rx_number = prescription.prescription_number or str(prescription_id)
    title = "New prescription"
    body = f"Prescription {rx_number} has been created."

    recipients: List[uuid.UUID] = [patient_user_id]
    receptionists = await get_user_ids_by_roles(
        db, hospital_id, [UserRole.RECEPTIONIST.value]
    )
    pharmacists = await get_user_ids_by_roles(
        db, hospital_id, [UserRole.PHARMACIST.value]
    )
    recipients.extend(receptionists)
    recipients.extend(pharmacists)
    recipients = list(dict.fromkeys(recipients))  # dedupe

    for uid in recipients:
        await create_notification(
            db, hospital_id, uid, prescription_id,
            EVENT_PRESCRIPTION_SUBMITTED, title, body,
        )


async def notify_prescription_dispensed(
    db: AsyncSession, prescription_id: uuid.UUID, hospital_id: uuid.UUID
) -> None:
    """
    Create in-app notifications for Patient (and optionally Receptionist) when prescription is dispensed.
    Does not commit; caller must commit.
    """
    result = await db.execute(
        select(Prescription)
        .where(
            and_(
                Prescription.id == prescription_id,
                Prescription.hospital_id == hospital_id,
            )
        )
        .options(selectinload(Prescription.patient).selectinload(PatientProfile.user))
    )
    prescription = result.scalar_one_or_none()
    if not prescription or not prescription.patient:
        return
    patient_user_id = prescription.patient.user_id
    rx_number = prescription.prescription_number or str(prescription_id)
    title = "Prescription ready"
    body = f"Prescription {rx_number} has been dispensed and is ready for pickup."

    recipients: List[uuid.UUID] = [patient_user_id]
    receptionists = await get_user_ids_by_roles(
        db, hospital_id, [UserRole.RECEPTIONIST.value]
    )
    recipients.extend(receptionists)
    recipients = list(dict.fromkeys(recipients))

    for uid in recipients:
        await create_notification(
            db, hospital_id, uid, prescription_id,
            EVENT_PRESCRIPTION_DISPENSED, title, body,
        )
