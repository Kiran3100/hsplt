# Telemedicine API — Endpoints & Iterations

All telemed routes are under **`/api/v1/telemed`**. They appear in Swagger when `OPENAPI_DOCS=true` (default). Set `OPENAPI_DOCS=false` in production to hide /docs and /redoc.

---

## Iterations completed

| Iteration | Scope | Status |
|-----------|--------|--------|
| **0** | Audit & gap analysis | ✅ |
| **1** | Chat, files, notes, prescriptions, vitals (DB + endpoints) | ✅ |
| **2** | Doctor schedule validation, TelemedBillingHook (NoOp + wired) | ✅ |
| **3** | In-app notifications (create, list /me, mark read) | ✅ |
| **4** | Hospital Admin provider config (GET/PATCH /config) | ✅ |
| **+** | Session uses provider config default + enabled_providers | ✅ |
| **+** | Mark notification as read | ✅ |

---

## Endpoints by router

### Telemedicine - Appointments (`/api/v1/telemed/tele-appointments`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/telemed/tele-appointments` | Create tele-appointment |
| GET | `/api/v1/telemed/tele-appointments` | List (filter by doctor/patient/status) |
| GET | `/api/v1/telemed/tele-appointments/{tele_appointment_id}` | Get one |
| POST | `/api/v1/telemed/tele-appointments/{tele_appointment_id}/reschedule` | Reschedule |
| POST | `/api/v1/telemed/tele-appointments/{tele_appointment_id}/cancel` | Cancel |
| POST | `/api/v1/telemed/tele-appointments/{tele_appointment_id}/confirm` | Confirm |

### Telemedicine - Sessions (`/api/v1/telemed/sessions`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/telemed/sessions` | Create session for tele-appointment |
| GET | `/api/v1/telemed/sessions` | List sessions |
| GET | `/api/v1/telemed/sessions/{session_id}` | Get session |
| POST | `/api/v1/telemed/sessions/{session_id}/start` | Start (doctor) |
| POST | `/api/v1/telemed/sessions/{session_id}/end` | End (doctor) |
| POST | `/api/v1/telemed/sessions/{session_id}/join-token` | Get join token |
| POST | `/api/v1/telemed/sessions/{session_id}/refresh-token` | Refresh token |
| GET | `/api/v1/telemed/sessions/{session_id}/messages` | List messages |
| POST | `/api/v1/telemed/sessions/{session_id}/messages` | Send message |
| GET | `/api/v1/telemed/sessions/{session_id}/files` | List files |
| POST | `/api/v1/telemed/sessions/{session_id}/files` | Upload file |
| GET | `/api/v1/telemed/sessions/{session_id}/notes` | List notes |
| POST | `/api/v1/telemed/sessions/{session_id}/notes` | Create note |
| POST | `/api/v1/telemed/sessions/{session_id}/prescriptions` | Create prescription |

### Telemedicine - Prescriptions (`/api/v1/telemed/prescriptions`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/telemed/prescriptions/{prescription_id}/sign` | Sign prescription (doctor) |

### Telemedicine - Vitals (`/api/v1/telemed/patients`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/telemed/patients/me/prescriptions` | My prescriptions (patient) |
| GET | `/api/v1/telemed/patients/me/vitals` | My vitals (patient) |
| GET | `/api/v1/telemed/patients/{patient_id}/vitals` | List vitals (patient own / doctor) |
| POST | `/api/v1/telemed/patients/{patient_id}/vitals` | Add vitals |

### Telemedicine - Notifications (`/api/v1/telemed/notifications`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/telemed/notifications/me` | List my notifications |
| PATCH | `/api/v1/telemed/notifications/me/{notification_id}/read` | Mark as read |

### Telemedicine - Provider Config (`/api/v1/telemed/config`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/telemed/config` | Get hospital provider config |
| PATCH | `/api/v1/telemed/config` | Update config (Hospital Admin only) |

---

## Swagger / ReDoc

- **Swagger UI:** `GET /docs` (when `OPENAPI_DOCS=true`, default).
- **ReDoc:** `GET /redoc`.
- Telemed endpoints are grouped by tags: *Telemedicine - Appointments*, *Telemedicine - Sessions*, etc.

If you do not see them:

1. Ensure `OPENAPI_DOCS` is not set to `false` in env or `.env`.
2. Restart the app after changing config.
3. Open `http://<host>:<port>/docs` and expand the **Telemedicine** tag groups.
