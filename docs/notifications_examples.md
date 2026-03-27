# Notification API – Example request bodies

Base URL: `/api/v1/notifications`

---

## 1. Send OTP

**POST** `/otp/send`

```json
{
  "phone": "+919876543210",
  "purpose": "LOGIN"
}
```

Rate limit: 5 OTPs per phone per 15 minutes.

---

## 2. Verify OTP

**POST** `/otp/verify`

```json
{
  "phone": "+919876543210",
  "otp": "123456"
}
```

---

## 3. Send payment receipt (unified send)

**POST** `/send`

```json
{
  "channel": "EMAIL",
  "to": "patient@example.com",
  "template_key": "PAYMENT_RECEIPT",
  "subject": "Payment receipt",
  "payload": {
    "patient_name": "John Doe",
    "amount": "1500.00",
    "receipt_number": "RCP-000042"
  },
  "idempotency_key": "payment_receipt:550e8400-e29b-41d4-a716-446655440000",
  "event_type": "PAYMENT_RECEIPT"
}
```

SMS variant:

```json
{
  "channel": "SMS",
  "to": "+919876543210",
  "template_key": "PAYMENT_RECEIPT",
  "payload": {
    "patient_name": "John Doe",
    "amount": "1500.00",
    "receipt_number": "RCP-000042"
  },
  "idempotency_key": "payment_receipt_sms:550e8400-e29b-41d4-a716-446655440000",
  "event_type": "PAYMENT_RECEIPT"
}
```

---

## 4. Schedule appointment reminder

**POST** `/schedule`

```json
{
  "event_type": "APPOINTMENT_REMINDER",
  "channel": "SMS",
  "to": "+919876543210",
  "template_key": "APPOINTMENT_REMINDER",
  "payload": {
    "patient_name": "Jane Doe",
    "slot_time": "2025-03-01 10:00",
    "appointment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  },
  "scheduled_for": "2025-02-28T09:00:00Z",
  "idempotency_key": "appointment_reminder:a1b2c3d4-e5f6-7890-abcd-ef1234567890:sms"
}
```

`scheduled_for` should be the desired send time (e.g. X hours before the appointment).

---

## 5. Bulk SMS (staff-only)

**POST** `/sms/bulk`

Requires Hospital Admin (or authorized staff).

```json
{
  "phones": ["+919876543210", "+919876543211"],
  "message": "Hospital announcement: OPD timings changed to 9 AM – 2 PM from Monday.",
  "idempotency_key": "bulk_announce_20250220_001"
}
```

Max 500 recipients per request.
