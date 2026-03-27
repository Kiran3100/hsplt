# API Request Bodies Reference

Copy-paste examples for all main API request bodies. Replace UUIDs and refs with your real values.

**Base URL:** `http://127.0.0.1:8000/api/v1`  
**Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`, `X-Hospital-ID: <hospital_uuid>` where required.

---

## 1. Billing – Bills & Payments

### Create OPD bill  
**POST** `/billing/opd/bills`

```json
{
  "bill_type": "OPD",
  "patient_ref": "PID-001",
  "appointment_ref": "APPT-123",
  "items": [
    {
      "service_item_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "description": "Consultation",
      "quantity": 1,
      "unit_price": 500,
      "tax_percentage": 5
    },
    {
      "service_item_id": null,
      "description": "Procedure - ECG",
      "quantity": 1,
      "unit_price": 200,
      "tax_percentage": 0
    }
  ],
  "notes": "OPD visit"
}
```

### Create IPD bill  
**POST** `/billing/ipd/bills`

```json
{
  "bill_type": "IPD",
  "admission_number": "ADM-001",
  "items": [
    {
      "service_item_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "description": "Room charges",
      "quantity": 3,
      "unit_price": 1000,
      "tax_percentage": 5
    }
  ],
  "notes": null
}
```

### Add bill items  
**POST** `/billing/bills/{bill_id}/items`

```json
[
  {
    "service_item_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "description": "Lab test",
    "quantity": 1,
    "unit_price": 300,
    "tax_percentage": 5
  }
]
```

### Update bill item  
**PATCH** `/billing/bills/{bill_id}/items/{item_id}`

```json
{
  "description": "Consultation - General",
  "quantity": 1,
  "unit_price": 600,
  "tax_percentage": 5
}
```

### Apply discount  
**PATCH** `/billing/bills/{bill_id}/apply-discount`

```json
{
  "discount_amount": 100,
  "reason": "Staff discount"
}
```

### Cancel bill  
**PATCH** `/billing/bills/{bill_id}/cancel`

```json
{
  "reason": "Duplicate bill"
}
```

### Reopen bill  
**PATCH** `/billing/bills/{bill_id}/reopen`

```json
{
  "reason": "Correction required"
}
```

### Collect payment (offline – cash/card/UPI)  
**POST** `/billing/bills/{bill_id}/payments`

```json
{
  "amount": 2625,
  "method": "CARD",
  "provider": "HDFC_PAYMENT_GATEWAY",
  "idempotency_key": "PAY-ADM-2026-9C6D7032-001",
  "gateway_transaction_id": "HDFC982374650129",
  "extra_data": {
    "card_last_four": "4821",
    "card_type": "VISA",
    "payment_time": "2026-02-24T12:40:00"
  }
}
```

### Run IPD daily bed charges  
**POST** `/billing/ipd/bills/{bill_id}/run-daily-bed-charges`

```json
{
  "from_date": "2026-02-20",
  "to_date": "2026-02-24",
  "bed_rate_per_day": 500
}
```

---

## 2. Billing – Service items & tax profiles

### Create tax profile  
**POST** `/billing/services/tax-profiles`

```json
{
  "name": "GST 5%",
  "gst_percentage": 5,
  "is_active": true
}
```

### Update tax profile  
**PUT** `/billing/services/tax-profiles/{tax_id}`

```json
{
  "name": "GST 5% Medical",
  "gst_percentage": 5,
  "is_active": true
}
```

### Create service item  
**POST** `/billing/services`

```json
{
  "department_id": null,
  "code": "CONS-GEN",
  "name": "General Consultation",
  "category": "CONSULTATION",
  "base_price": 500,
  "tax_profile_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "is_active": true
}
```

### Update service item  
**PUT** `/billing/services/{service_id}`

```json
{
  "department_id": null,
  "code": "CONS-GEN",
  "name": "General Consultation (Updated)",
  "category": "CONSULTATION",
  "base_price": 600,
  "tax_profile_id": null,
  "is_active": true
}
```

---

## 3. Payments gateway (Razorpay / collect / advance / refund)

### Initiate payment (create Razorpay order)  
**POST** `/payments/initiate`

```json
{
  "bill_id": "b75e25cd-2e65-4a0b-a2e1-2b20119bb234",
  "amount": 1000,
  "currency": "INR",
  "idempotency_key": "ORDER-2026-001"
}
```

### Collect payment (gateway – after verify or direct)  
**POST** `/payments/collect`

```json
{
  "bill_id": "b75e25cd-2e65-4a0b-a2e1-2b20119bb234",
  "amount": 1000,
  "method": "CARD",
  "provider": "RAZORPAY",
  "idempotency_key": "PAY-REF-001",
  "transaction_id": "pay_xyz123",
  "gateway_order_id": "order_abc456",
  "gateway_signature": "signature_from_razorpay",
  "currency": "INR"
}
```

### Verify payment  
**POST** `/payments/verify`

```json
{
  "payment_reference": "PAY-REF-001",
  "transaction_id": "pay_xyz123",
  "gateway_order_id": "order_abc456",
  "gateway_signature": "signature_from_razorpay"
}
```

### Advance payment (IPD)  
**POST** `/payments/advance`

```json
{
  "admission_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "amount": 5000,
  "method": "CASH",
  "idempotency_key": "ADV-2026-001",
  "currency": "INR"
}
```

### Refund payment  
**POST** `/payments/{payment_id}/refund`

```json
{
  "amount": 500,
  "reason": "Patient request"
}
```
*(Omit `amount` for full refund.)*

### Email receipt  
**POST** `/payments/{payment_id}/receipt/email`

```json
{
  "to_email": "patient@example.com"
}
```

---

## 4. Pharmacy – Sales & orders

### Create sale  
**POST** `/pharmacy/sales`  
**Header:** `Idempotency-Key: SALE-2026-001` (optional)

```json
{
  "sale_type": "PRESCRIPTION",
  "patient_ref": "PID-001",
  "doctor_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "prescription_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "billed_via": "PHARMACY_COUNTER",
  "payment_method": "CASH",
  "notes": null,
  "items": [
    {
      "medicine_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "qty": 2,
      "unit_price": 50,
      "discount": 0
    }
  ]
}
```

### Add sale item  
**POST** `/pharmacy/sales/{sale_id}/items`

```json
{
  "medicine_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "qty": 1,
  "unit_price": 100,
  "discount": 0
}
```

### Patient return  
**POST** `/pharmacy/returns/patient`

```json
{
  "sale_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "return_reason": "Wrong medicine",
  "items": [
    {
      "medicine_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "batch_id": null,
      "qty": 1,
      "unit_price": 50
    }
  ]
}
```

### Create purchase order  
**POST** `/pharmacy/purchase-orders`

```json
{
  "supplier_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "items": [
    {
      "medicine_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "quantity": 100,
      "unit_price": 25,
      "batch_no": "BATCH-001",
      "expiry_date": "2027-12-31"
    }
  ],
  "expected_date": "2026-03-01"
}
```

### Stock adjustment  
**POST** `/pharmacy/stock/adjustments`

```json
{
  "medicine_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "batch_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "quantity_change": -5,
  "reason": "Damaged"
}
```

---

## 5. Prescriptions (Doctor)

### Create simple prescription  
**POST** `/doctor/prescriptions/simple`

```json
{
  "patient_ref": "PID-001",
  "appointment_ref": "APPT-123",
  "medicines": [
    {
      "medicine_code": "MET-500-TAB",
      "medicine_name": "Metformin 500mg",
      "quantity": 30,
      "duration_days": 30,
      "frequency": "TWICE_DAILY",
      "timing": {
        "morning": true,
        "afternoon": false,
        "night": true,
        "specific_times": null
      },
      "instructions": "Take after meals",
      "indication": "Diabetes"
    }
  ],
  "notes": "Follow up in 2 weeks"
}
```

---

## 6. Patient care – Appointments & records

### Book appointment  
**POST** `/patient-care/appointments/book`

```json
{
  "department_name": "General",
  "doctor_name": "Dr. Smith",
  "appointment_date": "2026-03-01",
  "appointment_time": "10:00",
  "chief_complaint": "Fever and cough"
}
```

### Cancel appointment  
**POST** `/patient-care/appointments/{appointment_id}/cancel`

```json
{
  "cancellation_reason": "Rescheduled"
}
```

### Create medical record  
**POST** `/patient-care/medical-records`

```json
{
  "patient_ref": "PID-001",
  "appointment_ref": "APPT-123",
  "chief_complaint": "Headache",
  "history_of_present_illness": "3 days",
  "past_medical_history": "Hypertension",
  "examination_findings": "BP 130/80",
  "vital_signs": {
    "blood_pressure_systolic": 130,
    "blood_pressure_diastolic": 80,
    "pulse_rate": 72,
    "temperature": 98.6
  },
  "diagnosis": "Tension headache",
  "treatment_plan": "Rest, paracetamol",
  "follow_up_instructions": "Return if worse"
}
```

### Create discharge summary  
**POST** `/patient-care/discharge-summaries`

```json
{
  "admission_number": "ADM-001",
  "diagnosis_summary": "Recovered from pneumonia",
  "treatment_summary": "Antibiotics, rest",
  "discharge_medications": "Continue amoxicillin 5 days",
  "follow_up_instructions": "Review in OPD after 1 week",
  "advice_on_discharge": "Avoid exertion"
}
```

---

## 7. Surgery

### Create surgery case  
**POST** `/surgery/cases`

```json
{
  "patient_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "admission_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "surgery_name": "Appendectomy",
  "surgery_type": "MAJOR",
  "scheduled_date": "2026-03-15T09:00:00Z"
}
```

### Assign surgical team  
**POST** `/surgery/cases/{case_id}/team`

```json
{
  "members": [
    {
      "staff_name": "Dr. Jane Doe",
      "role": "ASSISTANT"
    },
    {
      "staff_name": "Dr. John Smith",
      "role": "ANESTHESIOLOGIST"
    }
  ]
}
```

### Surgery documentation  
**POST** `/surgery/documentation`

```json
{
  "surgery_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "patient_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "procedure_performed": "Laparoscopic appendectomy",
  "findings": "Inflamed appendix",
  "complications": null,
  "notes": "Routine",
  "post_op_instructions": "Light diet, wound care"
}
```

---

## 8. Notifications

### Send OTP  
**POST** `/notifications/otp/send`

```json
{
  "phone_number": "+919876543210",
  "purpose": "LOGIN"
}
```

### Verify OTP  
**POST** `/notifications/otp/verify`

```json
{
  "phone_number": "+919876543210",
  "otp": "123456"
}
```

### Send notification  
**POST** `/notifications/send`

```json
{
  "recipient_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "channel": "EMAIL",
  "template_code": "APPOINTMENT_REMINDER",
  "context": {
    "patient_name": "John",
    "appointment_date": "2026-03-01",
    "doctor_name": "Dr. Smith"
  }
}
```

---

*Replace all UUIDs (e.g. `3fa85f64-5717-4562-b3fc-2c963f66afa6`) and references (e.g. `PID-001`, `APPT-123`) with values from your database or previous API responses.*
