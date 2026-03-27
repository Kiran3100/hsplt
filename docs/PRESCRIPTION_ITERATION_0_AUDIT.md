# Digital Prescription – Iteration 0 (Audit)

**Canonical API:** `/api/v1/simple-prescription/*`  
**Deprecated API:** `/api/v1/doctor-prescription-system/*` (return 410 Gone or hide in Swagger)

---

## 1. Endpoints: Active vs Deprecated

### 1.1 Canonical (remain active)

All under **`/api/v1/simple-prescription`**:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/doctor/medicines/search` | Doctor medicine search (to be enhanced with pharmacy stock) |
| POST | `/doctor/prescriptions/create` | Doctor create prescription |
| GET | `/doctor/prescriptions` | Doctor list own prescriptions |
| GET | `/pharmacist/prescriptions` | Pharmacist list prescriptions (hospital) |
| POST | `/pharmacist/prescriptions/{prescription_id}/dispense` | Pharmacist dispense (to add pack + stock deduction) |
| GET | `/prescriptions/{prescription_id}` | Get prescription details (doctor/pharmacist) |

**To add (if missing):**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/prescriptions/{prescription_id}/pdf` | Patient download PDF (RBAC: patient own only) |
| (Optional) | `/pharmacist/prescriptions/{prescription_id}/pack` | Only if pack is a separate step; otherwise implement packing inside dispense |

---

### 1.2 Deprecated (410 Gone or exclude from Swagger)

All under **`/api/v1/doctor-prescription-system`**:

**Drug “fake database” (deprecate all):**

| Method | Path |
|--------|------|
| GET | `/drugs/search` |
| GET | `/drugs/{drug_id}` |
| POST | `/drugs/check-interactions` |
| POST | `/drugs/dosage-recommendation` |

**Advanced prescription (deprecate):**

| Method | Path |
|--------|------|
| POST | `/prescriptions/create-advanced` |
| PUT | `/prescriptions/{prescription_number}/modify` |
| POST | `/prescriptions/{prescription_number}/dispense` |

**Optional deprecate later (analytics/templates):**

| Method | Path |
|--------|------|
| POST | `/prescriptions/validate` |
| GET | `/prescriptions/digital/{prescription_number}` |
| GET | `/prescriptions/history` |
| GET | `/prescriptions/{prescription_number}/verify` |
| GET | `/analytics/prescription-patterns` |
| GET | `/analytics/drug-utilization` |
| GET | `/templates/common-prescriptions` |
| POST | `/templates/create-from-prescription` |

**Implementation:** Replace handler with `HTTPException(status_code=410, detail="Deprecated. Use /api/v1/simple-prescription/...")` and/or set `include_in_schema=False` so they do not appear in Swagger. If any UI still calls a deprecated URL, add an internal redirect to the canonical service (no duplicate logic).

---

## 2. Current DB and Code State

### 2.1 Simple-prescription (canonical) – current behavior

- **Model used:** `app.models.doctor.Prescription` (`prescriptions` table).
- **Table `prescriptions`:**
  - `id`, `hospital_id` (TenantBaseModel), `patient_id`, `doctor_id`, `appointment_id`, `medical_record_id`
  - `prescription_number`, `prescription_date`
  - `diagnosis`, `symptoms`
  - `medications` (JSON) – list of objects (medicine_id, dosage, frequency, duration, instructions, quantity, etc.)
  - `general_instructions`, `diet_instructions`, `follow_up_date`
  - `is_dispensed`, `dispensed_at`, `dispensed_by`
  - `is_digitally_signed`, `signature_hash`
  - No `status` (DRAFT/SUBMITTED/PACKING/READY/DISPENSED); no `submitted_at`.
- **Router:** `app.api.v1.routers.doctor.simple_prescription`:
  - Medicine search and create currently reference `Medicine` and `StockBatch` but:
    - `Medicine` has no `medicine_code` (only `sku`, `barcode`, `hsn_code`) – code uses `Medicine.medicine_code` → **bug**.
    - `StockBatch` has `qty_on_hand` and `qty_reserved`, not `quantity_available` – code uses `StockBatch.quantity_available` → **bug**.
  - Medicine search and create will fail at runtime until these are fixed and pharmacy models are imported (comments say "PHARMACY REMOVED" but code still uses them).

### 2.2 Pharmacy (real data)

- **Tables:** `pharmacy_medicines` (Medicine), `pharmacy_stock_batches` (StockBatch), `pharmacy_stock_ledger` (StockLedger), plus PO, GRN, sales, returns.
- **Medicine:** `id`, `hospital_id`, `generic_name`, `brand_name`, `composition`, `dosage_form`, `strength`, `manufacturer`, `drug_class`, `category`, `route`, `pack_size`, `reorder_level`, `barcode`, `hsn_code`, `sku`, `requires_prescription`, `is_controlled_substance`, `description`, `storage_instructions`, `is_active`, `created_at`, `updated_at`. **No `medicine_code`** – use `sku` or add a column.
- **StockBatch:** `id`, `hospital_id`, `medicine_id`, `batch_no`, `expiry_date`, `purchase_rate`, `mrp`, `selling_price`, `qty_on_hand`, `qty_reserved`, `grn_item_id`. **Available qty = `qty_on_hand - qty_reserved`** (no `quantity_available`).
- **StockLedger:** append-only; every stock change must create an entry (`txn_type`, `qty_change`, `reference_type`, `reference_id`, etc.).

### 2.3 Telemed prescriptions (separate)

- **Tables:** `tele_prescriptions` (TelePrescription), `prescription_medicines` (PrescriptionMedicine with FK to `pharmacy_medicines.id`), `prescription_lab_orders`, `prescription_pdfs`, `prescription_integrations`.
- These are for telemed flow only; canonical OPD prescription remains `prescriptions` + (optionally) new prescription_items table.

---

## 3. DB Changes (Exact)

### 3.1 Option A – Keep single `prescriptions` table and JSON items

- **`prescriptions` table (alter):**
  - Add `status` VARCHAR(20) NOT NULL DEFAULT 'DRAFT': `DRAFT | SUBMITTED | PACKING | READY | DISPENSED | CANCELLED`.
  - Add `submitted_at` TIMESTAMP WITH TIME ZONE NULL.
  - Keep `medications` JSON for now; ensure each item includes `medicine_id` (UUID, pharmacy_medicines.id) and structured directions (see schema below). No new table.

### 3.2 Option B – Normalized prescription_items (recommended for pharmacy/ledger)

- **`prescriptions` (alter):** Same as Option A: add `status`, `submitted_at`.
- **New table `prescription_items`:**
  - `id` UUID PK, `hospital_id` UUID NOT NULL FK, `prescription_id` UUID NOT NULL FK → `prescriptions.id`
  - `medicine_id` UUID NOT NULL FK → `pharmacy_medicines.id`
  - `requested_qty` INT NOT NULL
  - `route` VARCHAR(50) (ORAL, TOPICAL, etc.)
  - `dosage_text` VARCHAR(100) (e.g. "1 tablet")
  - `frequency` VARCHAR(20) (BD, TID, QID, OD, SOS)
  - `timing_json` JSONB (e.g. morning/afternoon/night booleans or times list)
  - `before_food` BOOLEAN, `after_food` BOOLEAN (reject both true)
  - `duration_days` INT NOT NULL
  - `instructions` TEXT
  - `created_at` TIMESTAMP WITH TIME ZONE
  - Unique per hospital: ensure (prescription_id, order) or single FK only.

- **Fulfillment (choose one):**
  - **Option B1 – JSON on prescription or prescription_items:** Add `batch_allocations` JSONB on `prescription_items`: `[{ "batch_id": "...", "packed_qty": N }, ...]`. On dispense, write ledger and update batch `qty_on_hand`/`qty_reserved`.
  - **Option B2 – New tables:** `prescription_fulfillment` (id, prescription_id, hospital_id, fulfilled_at, fulfilled_by), `prescription_fulfillment_item` (id, fulfillment_id, prescription_item_id, batch_id, packed_qty). Same ledger/batch logic.

**Recommendation:** Option B with `prescription_items` + `batch_allocations` JSONB on each item (or one JSON on prescription) to avoid extra tables in Iteration 0; add fulfillment tables later if needed.

### 3.3 Medicine code

- Either add `medicine_code` to `pharmacy_medicines` (VARCHAR, unique per hospital) or use `sku` everywhere in simple-prescription as the “code”. Audit recommends adding `medicine_code` for clarity (optional migration).

---

## 4. Request/Response Schema Changes

### 4.1 Doctor medicine search (GET `/simple-prescription/doctor/medicines/search`)

- **Current (broken):** Uses non-existent `Medicine.medicine_code`, `StockBatch.quantity_available`.
- **Response (enhanced) – per item:**
  - `medicine_id`, `generic_name`, `brand_name`, `dosage_form`, `strength`
  - `stock_status`: `IN_STOCK` | `LOW_STOCK` | `OUT_OF_STOCK` (e.g. by reorder_level)
  - `available_qty`: sum of (qty_on_hand - qty_reserved) for non-expired batches
  - `soonest_expiry_date`: min expiry_date among batches with qty > 0
  - Optionally keep `medicine_code` as `sku` or new column.

### 4.2 Prescription create (POST `/simple-prescription/doctor/prescriptions/create`)

- **Current:** `SimplePrescriptionCreate` with `PrescriptionMedicineCreate`: dosage, frequency, duration, instructions, quantity.
- **New/updated item schema (structured directions):**
  - `medicine_id` (UUID, from pharmacy)
  - `requested_qty` (int)
  - `dosage_text` (e.g. "1 tablet")
  - `frequency` (e.g. BD, TID, QID, OD, SOS)
  - `timing`: object with e.g. `morning`, `afternoon`, `night` booleans OR `times` list
  - `before_food` / `after_food` (reject if both true)
  - `duration_days` (int)
  - `route` (ORAL, TOPICAL, INHALATION, etc.)
  - `instructions` (free text)
- **Validation:** Reject `before_food && after_food` both true.

### 4.3 Pharmacist dispense

- **Request:** Either current (minimal) or extend with optional `pack_detail`: list of `{ "prescription_item_id" or "medicine_id", "batch_id", "quantity" }`. If omitted, backend selects batches (FIFO by expiry) and performs pack + ledger + mark dispensed in one transaction.
- **Response:** Include prescription_id, status DISPENSED, dispensed_at, and optionally batch allocations used.

### 4.4 PDF (GET `/simple-prescription/prescriptions/{id}/pdf`)

- **Response:** PDF file (Content-Type: application/pdf).
- **Content:** Hospital info, doctor name, patient info, date, prescription_number/prescription_id, medicines with directions clearly formatted.
- **RBAC:** Patient may only download their own; doctor/pharmacist/receptionist by existing rules.

---

## 5. Service / Repo Logic (What to Modify)

- **Simple prescription router:**  
  - Fix medicine search: use `app.models.pharmacy.Medicine` and `StockBatch`; available = `sum(qty_on_hand - qty_reserved)` where `expiry_date > today`; use `sku` as code or add `medicine_code`; add stock_status and soonest_expiry_date.
- **Prescription create:**  
  - Validate items against pharmacy medicines and (optionally) stock; persist to `prescriptions` (+ `prescription_items` if Option B); set status SUBMITTED and submitted_at; enqueue notifications (Patient, Receptionist, Pharmacy) via BackgroundTasks.
- **Dispense:**  
  - In one transaction: select batches (FIFO by expiry), decrement qty_on_hand (or reserve then decrement), write StockLedger, set batch_allocations, set prescription status DISPENSED and dispensed_at/dispensed_by.
- **PDF:**  
  - Use ReportLab (or existing PDF path); enforce RBAC; return file.

---

## 6. Summary Checklist

| Item | Action |
|------|--------|
| Canonical API | `/api/v1/simple-prescription/*` only for prescription workflow |
| Deprecate | `/api/v1/doctor-prescription-system` drug endpoints + create-advanced, modify, dispense (410 or hide) |
| DB | Add `status`, `submitted_at` to `prescriptions`; add `prescription_items` with medicine_id FK and structured directions; optional batch_allocations JSONB |
| Medicine search | Use pharmacy Medicine + StockBatch; fix medicine_code → sku or new column; add stock_status, available_qty, soonest_expiry_date |
| Create schema | Structured directions (dosage_text, frequency, timing, before/after_food, duration_days, route, instructions); reject before_food && after_food |
| Notifications | On submit: notify Patient, Receptionist, Pharmacy (event-driven, non-blocking) |
| Dispense | Batch selection (FIFO), ledger write, no negative stock (transaction + row locks) |
| PDF | GET `/prescriptions/{id}/pdf`; ReportLab; RBAC patient own only |

**STOP. Wait for "NEXT" to proceed to Iteration 1.**
