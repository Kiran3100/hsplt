# Hospital Management SaaS - Backend

Backend API for a multi-tenant Hospital Management SaaS platform. Built with FastAPI, PostgreSQL, and SQLAlchemy. Supports authentication, role-based access control, hospital administration, doctor and patient workflows, pharmacy, lab, billing, telemedicine, and Super Admin operations.

---

## Tech Stack

-   **Framework:** FastAPI
-   **Server:** Uvicorn (ASGI)
-   **Database:** PostgreSQL (async via asyncpg, sync via psycopg2)
-   **ORM:** SQLAlchemy 2.x (async)
-   **Migrations:** Alembic (optional; schema can be bootstrapped from models)
-   **Validation:** Pydantic v2
-   **Auth:** JWT (access + refresh), optional TOTP 2FA
-   **Payments:** Stripe, Razorpay, Paytm (optional integration)

---

## Prerequisites

-   Python 3.10+
-   PostgreSQL 12+
-   Redis (optional, for caching)

---

## Installation

1.  Clone the repository and enter the project directory:
    
    ```bash
    cd HSM
    ```
    
2.  Create a virtual environment and activate it:
    
    ```bash
    python -m venv venvvenvScriptsactivate
    ```
    
    On Linux/macOS:
    
    ```bash
    source venv/bin/activate
    ```
    
3.  Install dependencies:
    
    ```bash
    pip install -r requirements.txt
    ```
    
4.  Create a `.env` file in the project root. Required variables:
    
    ```env
    DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbnameDATABASE_URL_SYNC=postgresql://user:password@localhost:5432/dbnameSECRET_KEY=your-secret-key-change-in-production
    ```
    
    Optional (with defaults):
    
    ```env
    DEBUG=falseLOG_LEVEL=INFODB_BOOTSTRAP_FROM_MODELS=trueSUPERADMIN_EMAIL=superadmin@hsm.comSUPERADMIN_PASSWORD=SuperAdmin123!OPENAPI_DOCS=true
    ```
    
    See `app/core/config.py` for all settings and environment variable names.
    

---

## Running the Application

1.  Ensure PostgreSQL is running and the database exists.
    
2.  Start the server:
    
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8060 --reload
    ```
    
    Or run the module directly:
    
    ```bash
    python main.py
    ```
    
    Default port is 8060. With `DB_BOOTSTRAP_FROM_MODELS=true` (default), tables are created from SQLAlchemy models on startup; no separate Alembic run is required for initial setup.
    
3.  Open API docs:
    
    -   Swagger UI: `http://localhost:8060/docs`
    -   ReDoc: `http://localhost:8060/redoc`
4.  Health checks:
    
    -   Root: `GET /health`
    -   API: `GET /api/v1/health`

---

## Database Setup

-   **Bootstrap from models (default):** Set `DB_BOOTSTRAP_FROM_MODELS=true`. On startup, the app runs `Base.metadata.create_all()`. No Alembic commands needed for a fresh database.
-   **Alembic:** Set `DB_BOOTSTRAP_FROM_MODELS=false` and run `alembic upgrade head` for migration-based schema updates.

Super Admin and required roles are seeded automatically on first run if they do not exist.

---

## API Overview

Base path: `/api/v1`

Area

Description

Auth

Login, refresh, logout, email verification, password reset

2FA

TOTP setup and verify

Super Admin

Hospitals, subscriptions, support tickets, analytics, audit logs

Hospital Admin

Staff, wards, beds, admissions, appointments, patients

Doctor

Dashboard, appointments, patient records, prescriptions, treatment plans

Patient

Appointments, medical history, documents, discharge summary, IPD

Management

Nurse and receptionist management

Surgery

Cases, team assignment, documentation, video upload

Pharmacy

Medicines, suppliers, purchase orders, GRN, stock, sales, returns, alerts

Telemedicine

Appointments, sessions, prescriptions, vitals, config

Lab

Test registration, sample collection, result entry, equipment QC, report access

Billing

Services, OPD/IPD bills, documents

Insurance

Claims

Finance

Reports, reconciliation, audit

Notifications

In-app notifications

Payments

Gateway collect and webhooks

APIs use **patient_ref**, **appointment_ref**, **admission_ref**, **doctor_ref** / doctor name, and **department name** where applicable instead of raw UUIDs in request/response bodies.

---

## Authentication

-   **Login:** `POST /api/v1/auth/login` with email and password. Returns access and refresh tokens.
-   **Protected routes:** Send `Authorization: Bearer <access_token>`.
-   **Hospital context:** Most hospital-scoped endpoints rely on the token’s hospital context and tenant isolation middleware.
-   **Roles:** SUPER_ADMIN, HOSPITAL_ADMIN, DOCTOR, NURSE, PHARMACIST, LAB_TECH, RECEPTIONIST, PATIENT, etc. Access is enforced per endpoint.

---

## Project Structure

```
HSM/  main.py                 # App entry, lifespan, DB bootstrap, middleware  requirements.txt  .env                    # Not committed; copy from example  app/    api/      v1/        api.py            # Main router, mounts all modules        auth.py           # Login, refresh, verification        routers/          admin/          # Super Admin, Hospital Admin          doctor/         # Doctor dashboards, prescriptions, etc.          patient/        # Patient booking, documents, IPD          management/     # Nurse, receptionist          surgery/        # Surgery cases, team, docs          pharmacy/       # Medicines, GRN, sales, etc.          telemed/        # Telemedicine          lab/            # Lab orders, samples, results          billing/        # Bills, services          payments_gateway/    core/      config.py           # Settings from env      security.py         # JWT, password hashing      enums.py      exceptions.py    database/      session.py          # Async engine, session factory    middleware/      tenant_isolation.py # Hospital scoping      clinical_audit.py    models/               # SQLAlchemy models    schemas/              # Pydantic request/response    services/              # Business logic    repositories/          # Data access  alembic/                # Migrations (optional)
```

---

## Configuration

Key settings in `app/core/config.py` (overridable via `.env`):

-   **Database:** `DATABASE_URL`, `DATABASE_URL_SYNC`, `DB_BOOTSTRAP_FROM_MODELS`
-   **Security:** `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
-   **Super Admin:** `SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD`
-   **CORS:** `ALLOWED_ORIGINS`
-   **Logging:** `LOG_LEVEL`
-   **Docs:** `OPENAPI_DOCS` (set false in production to hide `/docs` and `/redoc`)

---

## Development

-   Run with `--reload` for auto-restart on code changes.
-   Set `DEBUG=true` and `LOG_LEVEL=DEBUG` for verbose logs.
-   Use `/docs` for interactive API testing.

---

## License

Proprietary. All rights reserved.