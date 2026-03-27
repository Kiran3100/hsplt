# Telemedicine Module — Iteration 0: Audit & Gap Analysis

**Date:** 2026-02-19  
**Scope:** Backend APIs + integration readiness for multi-tenant HSM  
**Constraint:** No changes to existing `appointment` model or core appointment workflows.

---

## 1. EXISTING vs REQUIRED — Data Model Mapping

| SOW Model | Exists? | Location | Gap / Delta |
|-----------|---------|----------|-------------|
| **A) tele_appointment** | ✅ | `app/models/telemedicine.py` | **MATCH.** `id`, `hospital_id`, `patient_id`, `doctor_id`, `scheduled_start`, `scheduled_end`, `reason`, `notes`, `status`, `created_by`, `created_at`, `updated_at`. Has `cancelled_at`, `cancelled_by`, `cancellation_reason`. Exclusion constraint `uq_tele_appointments_no_overlap` (telemed_002). |
| **B) telemed_session** | ✅ | `app/models/telemedicine.py` | **MATCH.** `tele_appointment_id` UNIQUE, `provider`, `room_name`, `status`, `scheduled_start/end`, `started_at`, `ended_at`, `recording_enabled`, `recording_status`, `recording_url`, `duration_seconds`, `ended_by`, `end_reason`. Status enum differs from SOW: `READY` vs `SCHEDULED` — acceptable. |
| **C) telemed_participant** | ✅ | `app/models/telemedicine.py` | **MATCH.** `hospital_id`, `session_id`, `user_id`, `role`, `joined_at`, `left_at`. UNIQUE(hospital_id, session_id, user_id). |
| **D) telemed_token** | ❌ | — | **GAP.** Tokens not persisted; generated on demand. SOW OK: "do not persist raw tokens if possible." Token hashes optional. **No action.** |
| **E) telemed_message** | ❌ | — | **GAP.** No chat/message model. Need: `telemed_messages` (id, hospital_id, session_id, sender_id, sender_role, message_type, content/text, file_ref, created_at, encryption-ready). |
| **F) telemed_file** | ❌ | — | **GAP.** No shared file metadata. Need: `telemed_files` (id, hospital_id, session_id, uploaded_by, file_name, mime_type, size_bytes, storage_url, checksum, created_at). |
| **G) telemed_consultation_note** | ❌ | — | **GAP.** No SOAP notes. Need: `telemed_consultation_notes` (id, hospital_id, session_id, doctor_id, soap_json/text, created_at, updated_at). |
| **H) telemed_prescription** | ⚠️ | `app/models/prescription.py` | **PARTIAL.** `TelePrescription` exists with `tele_appointment_id` (nullable), `doctor_id`, `patient_id`, `status` (DRAFT/SIGNED/ISSUED), etc. **No `session_id`** — FK to telemed_session. SOW links to both session and appointment. **Add session_id nullable.** |
| **I) telemed_vitals** | ❌ | — | **GAP.** Vitals exist in nursing/medical records, not telemed. Need: `telemed_vitals` (id, hospital_id, patient_id, session_id nullable, vitals_type, value_json, recorded_at, entered_by, created_at). |
| **J) notifications** | ⚠️ | — | **GAP.** No in-app notification records for session READY/ENDED/message. Need: `telemed_notifications` or reuse existing notification system if present. |

---

## 2. EXISTING vs REQUIRED — API Endpoints

| SOW Endpoint | Exists? | File | Notes |
|--------------|---------|------|-------|
| **A) Tele-Appointment** | | | |
| POST /telemed/tele-appointments | ✅ | `tele_appointments.py` | Create; overlap check + IntegrityError 409 |
| GET /telemed/tele-appointments | ✅ | `tele_appointments.py` | Role-filtered |
| GET /telemed/tele-appointments/{id} | ✅ | `tele_appointments.py` | |
| POST /telemed/tele-appointments/{id}/reschedule | ✅ | `tele_appointments.py` | Receptionist only |
| POST /telemed/tele-appointments/{id}/cancel | ✅ | `tele_appointments.py` | |
| POST /telemed/tele-appointments/{id}/confirm | ✅ | `tele_appointments.py` | Receptionist only |
| **B) Session** | | | |
| POST /telemed/sessions | ✅ | `sessions.py` | Lazy-create from tele_appointment_id |
| GET /telemed/sessions | ✅ | `sessions.py` | |
| GET /telemed/sessions/{session_id} | ✅ | `sessions.py` | |
| POST /telemed/sessions/{session_id}/start | ✅ | `sessions.py` | Doctor only |
| POST /telemed/sessions/{session_id}/end | ✅ | `sessions.py` | Doctor only |
| **C) Join / Token** | | | |
| POST /telemed/sessions/{session_id}/join-token | ✅ | `sessions.py` | Doctor/patient; join window enforced |
| POST /telemed/sessions/{session_id}/refresh-token | ✅ | `sessions.py` | |
| **D) Chat / Files** | | | |
| GET /telemed/sessions/{session_id}/messages | ❌ | — | **GAP** |
| POST /telemed/sessions/{session_id}/messages | ❌ | — | **GAP** |
| POST /telemed/sessions/{session_id}/files | ❌ | — | **GAP** |
| GET /telemed/sessions/{session_id}/files | ❌ | — | **GAP** |
| **E) Notes / Prescription** | | | |
| GET /telemed/sessions/{session_id}/notes | ❌ | — | **GAP** |
| POST /telemed/sessions/{session_id}/notes | ❌ | — | **GAP** |
| POST /telemed/sessions/{session_id}/prescriptions | ❌ | — | **GAP** |
| POST /telemed/prescriptions/{id}/sign | ❌ | — | **GAP** |
| GET /telemed/patients/me/prescriptions | ❌ | — | **GAP** |
| **F) Vitals** | | | |
| POST /telemed/patients/{patient_id}/vitals | ❌ | — | **GAP** |
| GET /telemed/patients/{patient_id}/vitals | ❌ | — | **GAP** |

**Path prefix:** `/api/v1/telemed` (registered in `app/api/v1/api.py`).

---

## 3. RBAC — Current vs Required

| Role | SOW | Current | Gap |
|------|-----|---------|-----|
| **Patient** | Create tele-appointment for self (optional); view own; join token within window; chat/file; enter vitals. | Create for self; view own; join token within window. | No chat/file/vitals endpoints. |
| **Doctor** | View assigned; start/end; notes/prescription. | View assigned; start/end. | No notes/prescription endpoints under telemed. |
| **Receptionist** | Create/reschedule/cancel; no join tokens. | ✅ Create/reschedule/cancel/confirm. | Match. |
| **Hospital Admin** | Config provider; manage policies. | No dedicated telemed config. | **GAP.** |
| **Super Admin** | Platform-level only. | No telemed-specific. | OK. |

**Session create:** POST /telemed/sessions restricted to RECEPTIONIST, HOSPITAL_ADMIN, DOCTOR only (nurse/patient blocked). ✅

---

## 4. Critical Validations — Current State

| Validation | Status | Notes |
|------------|--------|-------|
| Doctor belongs to hospital | ✅ | `_validate_doctor_in_hospital` |
| Patient belongs to hospital | ✅ | `_validate_patient_in_hospital` |
| Doctor availability (overlap) | ✅ | `_check_overlap` + DB exclusion `uq_tele_appointments_no_overlap` |
| Doctor schedule (day_of_week, start/end) | ❌ | **GAP.** `DoctorSchedule` exists but NOT used in telemed. Regular appointments use it in `appointment_service.get_available_slots`. Telemed only checks overlap, not working hours. |
| Double-booking prevention | ✅ | Service overlap + DB EXCLUDE |
| Join window [start-10m, end+15m] | ✅ | `_is_in_join_window` |
| Session status transitions | ✅ | `telemed_state_machine.validate_transition` |
| Tenant isolation (hospital_id) | ✅ | All repos + queries scoped |

---

## 5. Provider Integration (Twilio/Agora/Zoom)

| Item | Status | Notes |
|------|--------|-------|
| Provider field in session | ✅ | `provider` (TWILIO/AGORA/ZOOM/WEBRTC) |
| Room creation | ⚠️ | `room_name` set locally; no SDK call yet |
| Token generation | ⚠️ | Backend mints hash-based token; no real provider token |
| Provider keys never in API | ✅ | No keys exposed |

**GAP:** No actual Twilio/Agora/Zoom SDK integration. Provider keys/config not wired. SOW says "integration" — hooks for later.

---

## 6. Billing

| Item | Status |
|------|--------|
| TelemedBillingHook interface | ❌ | Not provided |
| Payment tables/endpoints | Out of scope |

**Action:** Add `TelemedBillingHook` protocol/interface only when Iteration 1+ implements billing hooks.

---

## 7. Test Coverage

| Test | Status | File |
|------|--------|------|
| RBAC: nurse/patient cannot create session | ✅ | `test_telemed_fixes.py` |
| RBAC: doctor/receptionist can create session | ✅ | |
| Overlap → 409 TELE_APPOINTMENT_OVERLAP | ✅ | |
| Join window constants | ✅ | |
| Join window violation → 403 | ✅ | |
| Invalid session transitions | ✅ | |
| Prescription tele_appointment_id nullable | ✅ | |
| Repository hospital_id scoping | ✅ | |
| Tenant isolation | ⚠️ | Implicit via repo |
| Chat restricted to participants | ❌ | No chat |
| Prescription creation doctor-only | ❌ | No telemed prescription endpoint |

---

## 8. GAP SUMMARY (Prioritized)

### High priority (core workflow)

1. **Doctor schedule validation** — Telemed does not check `DoctorSchedule` (day_of_week, start_time, end_time). Can book outside working hours.
2. **Chat / Messages** — No `telemed_messages` table or endpoints.
3. **Files** — No `telemed_files` table or endpoints.
4. **Consultation notes** — No `telemed_consultation_notes` or SOAP notes.
5. **Prescription under telemed** — No POST /telemed/sessions/{id}/prescriptions or GET /telemed/patients/me/prescriptions. TelePrescription exists but not wired to telemed API.
6. **Vitals** — No `telemed_vitals` or endpoints.

### Medium priority (UX / compliance)

7. **TelePrescription.session_id** — Add nullable FK to telemed_session for session-scoped prescriptions.
8. **Prescription sign** — POST /telemed/prescriptions/{id}/sign placeholder.
9. **Notifications** — In-app notification records for session READY/ENDED/new message.

### Low priority (later)

10. **Hospital Admin** — Provider config endpoint.
11. **TelemedBillingHook** — Interface only.

---

## 9. Iteration 1 Recommendation (when you say "NEXT")

**Suggested scope for Iteration 1:**

1. **DB:** Add `telemed_messages`, `telemed_files`, `telemed_consultation_notes`, `telemed_vitals`; add `session_id` nullable to `tele_prescriptions`.
2. **Endpoints:** Chat (GET/POST messages), Files (GET/POST), Notes (GET/POST), Prescriptions (POST session, GET patient/me), Vitals (POST/GET).
3. **RBAC:** Doctor-only notes/prescription; participant-only chat/files; patient vitals entry.
4. **Validations:** Doctor schedule check (optional in Iteration 1 if time-constrained).
5. **Tests:** Chat participant restriction, prescription doctor-only, vitals patient/doctor.

**Alternative:** Iteration 1 = Doctor schedule validation only (smallest change). Then Iteration 2 = Chat + Files + Notes + Prescription + Vitals.

---

## 10. File Inventory (Existing)

| Path | Purpose |
|------|---------|
| `app/models/telemedicine.py` | TeleAppointment, TelemedSession, TelemedParticipant |
| `app/models/prescription.py` | TelePrescription, PrescriptionMedicine, PrescriptionLabOrder, PrescriptionPDF, PrescriptionIntegration |
| `app/api/v1/routers/telemed/tele_appointments.py` | Tele-appointment CRUD + reschedule/cancel/confirm |
| `app/api/v1/routers/telemed/sessions.py` | Session CRUD + start/end + join-token |
| `app/services/telemed_appointment_service.py` | Create, overlap, reschedule, cancel, confirm |
| `app/services/telemed_session_service.py` | Create, start, end, join token |
| `app/services/telemed_state_machine.py` | Status transitions |
| `app/repositories/telemed_repository.py` | TeleAppointmentRepository, TelemedSessionRepository |
| `app/schemas/telemed.py` | Request/response schemas |
| `alembic/versions/telemed_001` (add_telemedicine_tables_v2) | Base tables |
| `alembic/versions/telemed_002` | Exclusion constraint |
| `alembic/versions/telemed_003` | Prescription tele_appointment_id nullable |
| `tests/test_telemed_fixes.py` | 10 tests |

---

---

## 11. Iteration 1 — COMPLETED (2026-02-19)

### DB Changes
- **telemed_messages**: session_id, sender_id, sender_role, message_type, content, file_ref, content_encrypted, key_ref
- **telemed_files**: session_id, uploaded_by, file_name, mime_type, size_bytes, storage_url, checksum
- **telemed_consultation_notes**: session_id, doctor_id, soap_json, soap_text, version
- **telemed_vitals**: patient_id, session_id (nullable), vitals_type, value_json, recorded_at, entered_by
- **tele_prescriptions**: added session_id (nullable FK to telemed_sessions)

Migration: `telemed_004_chat_files_notes_vitals.py`

### Endpoints Added
| Method | Path | RBAC |
|--------|------|------|
| GET | /api/v1/telemed/sessions/{id}/messages | Participants only |
| POST | /api/v1/telemed/sessions/{id}/messages | Participants only |
| GET | /api/v1/telemed/sessions/{id}/files | Participants only |
| POST | /api/v1/telemed/sessions/{id}/files | Participants only |
| GET | /api/v1/telemed/sessions/{id}/notes | Doctor only |
| POST | /api/v1/telemed/sessions/{id}/notes | Doctor only |
| POST | /api/v1/telemed/sessions/{id}/prescriptions | Doctor only |
| POST | /api/v1/telemed/prescriptions/{id}/sign | Prescribing doctor only |
| GET | /api/v1/telemed/patients/me/prescriptions | Patient only |
| GET | /api/v1/telemed/patients/me/vitals | Patient only |
| GET | /api/v1/telemed/patients/{id}/vitals | Patient (own) or doctor/staff |
| POST | /api/v1/telemed/patients/{id}/vitals | Patient (self) or doctor/staff |

### Tests Added
- `test_iter1_chat_restricted_to_participants` — non-participant gets 403
- `test_iter1_vitals_valid_types` — BP, HR, SPO2, TEMP, WEIGHT, GLUCOSE
- `test_iter1_prescription_service_has_sign` — sign + create_for_session exist
