"""
Event hooks for notification enqueue. Call from Appointments, Payments, Lab, Auth.
Uses idempotency keys: appointment_confirm:{id}, payment_receipt:{id}, lab_report_ready:{id}, appointment_reminder:{id}.
"""
from datetime import datetime
from uuid import UUID
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.notifications import NotificationService
from app.core.enums import NotificationEventType


async def enqueue_appointment_confirmation(
    db: AsyncSession,
    hospital_id: UUID,
    appointment_id: UUID,
    to_email: Optional[str] = None,
    to_phone: Optional[str] = None,
    patient_name: str = "",
    slot_time: Optional[datetime] = None,
    template_key: Optional[str] = "APPOINTMENT_CONFIRM",
) -> None:
    """Call after appointment booking. Sends email and/or SMS."""
    svc = NotificationService(db, hospital_id)
    payload = {"patient_name": patient_name, "slot_time": str(slot_time) if slot_time else "", "appointment_id": str(appointment_id)}
    if to_email:
        await svc.send(
            channel="EMAIL",
            to=to_email,
            idempotency_key=f"appointment_confirm:{appointment_id}",
            event_type=NotificationEventType.APPOINTMENT_CONFIRM.value,
            template_key=template_key,
            payload=payload,
        )
    if to_phone:
        await svc.send(
            channel="SMS",
            to=to_phone,
            idempotency_key=f"appointment_confirm_sms:{appointment_id}",
            event_type=NotificationEventType.APPOINTMENT_CONFIRM.value,
            template_key=template_key,
            payload=payload,
        )


async def enqueue_appointment_reminder(
    db: AsyncSession,
    hospital_id: UUID,
    appointment_id: UUID,
    to_email: Optional[str] = None,
    to_phone: Optional[str] = None,
    patient_name: str = "",
    slot_time: Optional[datetime] = None,
    scheduled_for: Optional[datetime] = None,
    template_key: Optional[str] = "APPOINTMENT_REMINDER",
) -> None:
    """Schedule reminder X hours before slot. scheduled_for should be the desired send time."""
    svc = NotificationService(db, hospital_id)
    payload = {"patient_name": patient_name, "slot_time": str(slot_time) if slot_time else "", "appointment_id": str(appointment_id)}
    key = f"appointment_reminder:{appointment_id}"
    if to_email and scheduled_for:
        await svc.schedule(
            event_type=NotificationEventType.APPOINTMENT_REMINDER.value,
            channel="EMAIL",
            to=to_email,
            scheduled_for=scheduled_for,
            idempotency_key=f"{key}:email",
            template_key=template_key,
            payload=payload,
        )
    if to_phone and scheduled_for:
        await svc.schedule(
            event_type=NotificationEventType.APPOINTMENT_REMINDER.value,
            channel="SMS",
            to=to_phone,
            scheduled_for=scheduled_for,
            idempotency_key=f"{key}:sms",
            template_key=template_key,
            payload=payload,
        )


async def enqueue_payment_receipt(
    db: AsyncSession,
    hospital_id: UUID,
    payment_id: UUID,
    to_email: Optional[str] = None,
    to_phone: Optional[str] = None,
    patient_name: str = "",
    amount: str = "",
    receipt_number: str = "",
    template_key: Optional[str] = "PAYMENT_RECEIPT",
) -> None:
    """Call after payment success."""
    svc = NotificationService(db, hospital_id)
    payload = {"patient_name": patient_name, "amount": amount, "receipt_number": receipt_number, "payment_id": str(payment_id)}
    if to_email:
        await svc.send(
            channel="EMAIL",
            to=to_email,
            idempotency_key=f"payment_receipt:{payment_id}",
            event_type=NotificationEventType.PAYMENT_RECEIPT.value,
            template_key=template_key,
            payload=payload,
        )
    if to_phone:
        await svc.send(
            channel="SMS",
            to=to_phone,
            idempotency_key=f"payment_receipt_sms:{payment_id}",
            event_type=NotificationEventType.PAYMENT_RECEIPT.value,
            template_key=template_key,
            payload=payload,
        )


async def enqueue_lab_report_ready(
    db: AsyncSession,
    hospital_id: UUID,
    report_id: UUID,
    to_email: Optional[str] = None,
    to_phone: Optional[str] = None,
    patient_name: str = "",
    report_number: str = "",
    template_key: Optional[str] = "LAB_REPORT_READY",
) -> None:
    """Call when lab report is ready for patient."""
    svc = NotificationService(db, hospital_id)
    payload = {"patient_name": patient_name, "report_number": report_number, "report_id": str(report_id)}
    key = f"lab_report_ready:{report_id}"
    if to_email:
        await svc.send(
            channel="EMAIL",
            to=to_email,
            idempotency_key=f"{key}:email",
            event_type=NotificationEventType.LAB_REPORT_READY.value,
            template_key=template_key,
            payload=payload,
        )
    if to_phone:
        await svc.send(
            channel="SMS",
            to=to_phone,
            idempotency_key=f"{key}:sms",
            event_type=NotificationEventType.LAB_REPORT_READY.value,
            template_key=template_key,
            payload=payload,
        )
