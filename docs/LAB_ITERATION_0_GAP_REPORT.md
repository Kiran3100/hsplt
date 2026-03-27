# LAB (LIMS) Module — Iteration 0: Audit & Gap Report

**Date:** 2026-02-19  
**Scope:** Laboratory Information Management System within multi-tenant Hospital Management SaaS.

---

## 1. WHAT ALREADY EXISTS

### 1.1 Routers (paths + methods)

| Router File | Prefix | Endpoints (summary) |
|-------------|--------|---------------------|
| **lab_test_registration** | `/lab/registration` | POST/GET/PUT tests; POST/GET/PATCH orders (create, list, get, priority, cancel); GET sample-types, order-priorities, order-statuses, stats |
| **lab_sample_collection** | (mounted under lab samples) | POST orders/{id}/create (samples); GET orders/{id}, list, /{id}, /{id}/barcode, scan/{barcode}; PATCH collect, receive, reject; POST bulk/collect; GET utils (container-types, sample-statuses, rejection-reasons), stats |
| **lab_result_entry** | (result entry prefix) | POST results/{order_item_id}; GET/PUT results/{result_id}; POST verify, release, reject; GET worklist, orders/{id}/results; POST/GET orders/{id}/reports; GET reports/{id} |
| **lab_equipment_qc** | (equipment prefix) | CRUD equipment; PATCH status; GET/POST equipment logs; POST/GET qc/rules, qc/runs; GET qc/status |
| **lab_report_access** | `/lab/reports` | GET doctor/patient lab-reports; GET lab-reports/{id}, pdf, summary; PATCH publish/unpublish; POST share-link; GET/POST/PATCH report-share/{token}; POST notifications; GET notification status |
| **lab_audit_compliance** | `/lab/audit` | GET audit/logs, logs/{id}, entity/{type}/{id}; GET samples/{id}/trace, results/{id}/history, reports/{id}/history; POST exports (qc, sample-rejections, result-changes, equipment-calibration, orders-summary); GET analytics (tat, volume, qc-failure-rate, equipment-uptime) |
| **lab_billing_integration** | (billing) | POST create-bill-from-lab-order; GET check-lab-order-billing/{id} |

**Note:** Lab routers are **DISABLED** in `api.py` (commented out). No lab routes are mounted.

### 1.2 Models / Tables

| Table | hospital_id | Notes |
|------|-------------|--------|
| lab_tests | ✓ | test_code unique per hospital (uq_test_code_per_hospital). Missing: category/department, units, methodology, specimen type as structured fields; reference_ranges is JSON only. |
| lab_orders | ✓ | lab_order_no **globally** unique (wrong for multi-tenant). patient_id, requested_by_doctor_id are String(50), not UUID FKs. |
| lab_order_items | ✗ | No hospital_id (derived via order). |
| lab_samples | ✓ | sample_no, barcode_value **globally** unique (wrong). Sample status: REGISTERED, COLLECTED, IN_PROCESS, REJECTED — no RECEIVED/STORED/DISCARDED. |
| sample_order_items | ✗ | Bridge; no hospital_id. uq_sample_order_item_mapping (sample_id, lab_order_item_id). |
| test_results | ✓ | One per order_item (uq_test_result_per_order_item). verified_by/released_by, no approved_by/approved_at; no versioning. |
| result_values | ✗ | No hospital_id. |
| lab_reports | ✓ | report_number **globally** unique (wrong). report_data JSON. No report_template_id. |
| lab_equipment | ✓ | equipment_code not unique per hospital in migration (index only). |
| equipment_maintenance_logs | ✗ | No hospital_id. |
| qc_rules | ✓ | section, test_code, frequency, validity_hours, parameter min/max/target. |
| qc_runs | ✓ | equipment_id, qc_rule_id, run_at, status, values JSON. |
| report_share_tokens | ✓ | Token-based access. |
| notification_outbox | ✓ | Lab report notifications. |
| report_access_logs (ReportAccess) | ✓ | Audit of report access. |
| lab_audit_logs | ✓ | Entity/action audit. |
| chain_of_custody | ✓ | Sample custody. |
| compliance_exports | ✓ | Export tracking. |

### 1.3 Schemas

- Test: Create/Update/Response/List; Order: Create (OrderTestItem, OrderReference), Response, List, PriorityUpdate, Cancel; Sample: Create, Collect, Receive, Reject, Bulk, Response, List, Barcode; Result: Create, Verify, Release, Reject, Response, Worklist; Report: Generate, Response, History, Summary, ShareToken, Access; Equipment: Create/Update/Status/Response/List; Maintenance: Create/Response/List; QC: Rule/Run Create, Response, List, Status; Audit/Compliance/Analytics response schemas. **Missing:** Category/Department schemas, normal ranges + units + methodology + specimen type in test schemas, report template, lab_action_log, structured approval (pathologist) payloads.

### 1.4 Services

- **LabService** only (single ~6k-line service). No repository layer for lab; all DB access in service. Methods: test CRUD; order create/get/update_priority/cancel + _generate_lab_order_number; sample create_for_order, get, get_by_id, barcode, scan, collect, receive, reject, bulk_collect + _generate_sample_number; result create, verify, release, reject, get_by_id, worklist, get_results_for_order; report generate, get_report_history, _generate_report_number, publish, unpublish, get_report_publish_status, get_doctor/patient_reports, get_report_with_access_check, get_report_pdf_with_access_check, create_share_token, validate_share_token, log_report_access, create_report_ready_notification, revoke_share_token, verify_share_token_otp; create_notification, get_notification_status; _count_abnormal_results, _count_critical_results, _get_tests_summary; equipment CRUD + status + maintenance logs; qc_rule/qc_run CRUD + check_qc_status; create_audit_log, create_custody_event, create_compliance_export + _generate_export_file and _export_* helpers; get_tat_analytics, get_volume_analytics, get_qc_failure_analytics, get_equipment_uptime_analytics; get_registration_statistics, get_sample_collection_statistics.

### 1.5 Permissions / RBAC

- **lab_test_registration**: `get_current_user` + `verify_lab_tech_role` (UserRole.LAB_TECH only).
- **lab_sample_collection**: Same — LAB_TECH only.
- **lab_result_entry**: `require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"])` — **string literals**; UserRole enum has **only LAB_TECH** (no LAB_SUPERVISOR, LAB_ADMIN, PATHOLOGIST). Verify/release are in service but not pathologist-specific.
- **lab_equipment_qc**: Same string-based require_roles(["LAB_TECH", "LAB_SUPERVISOR", "LAB_ADMIN"]).
- **lab_report_access**: Doctor/Patient via require_roles([UserRole.DOCTOR]), require_roles([UserRole.PATIENT]); publish/unpublish/share: LAB_TECH or HOSPITAL_ADMIN.
- **lab_audit_compliance**: LAB_TECH or HOSPITAL_ADMIN.
- **lab_billing_integration**: Manual role check (HOSPITAL_ADMIN, RECEPTIONIST, LAB_TECH, SUPER_ADMIN).
- **Receptionist:** Not explicitly given “register orders, schedule sample collection” in lab routers; only LAB_TECH can create orders today. **Pathologist:** Not in UserRole; no “approve results / finalize reports” role.

### 1.6 Background tasks / jobs

- None found. No scheduled QC, no async report generation, no billing hooks.

---

## 2. GAP ANALYSIS VS REQUIRED LIMS FEATURES

### We already have (keep)

- Test catalogue with hospital-scoped test code uniqueness, basic CRUD, pagination, active filter.
- Lab order creation with multiple tests, priority, source, optional prescription/encounter refs.
- Sample creation linked to order, sample–order_item mapping (sample_order_items).
- Sample lifecycle: REGISTERED → COLLECTED → IN_PROCESS (and REJECTED) with some transition checks.
- Barcode/sample number generation (server-side); scan by barcode; phlebotomist (collected_by) and timestamps.
- Result entry (technician); result_values for multi-parameter tests; verify/release (but not pathologist approval); draft/reject flow.
- Lab report generation (report_data JSON); report versioning; publish/unpublish; share tokens; report access logging.
- Equipment CRUD; maintenance logs; QC rules and QC runs; QC status check.
- Audit log (lab_audit_logs); chain of custody; compliance exports; TAT/volume/QC/equipment analytics.
- Hospital-scoped service (hospital_id in constructor); most queries filtered by hospital_id.

### We have but it’s wrong (change)

- **lab_order_no, sample_no, barcode_value, report_number:** Uniqueness is **global**. Must be **unique per hospital** to avoid cross-tenant collisions and allow same numbers across tenants.
- **Order status machine:** Current: REGISTERED, SAMPLE_COLLECTED, IN_PROGRESS, COMPLETED, CANCELLED. Missing: DRAFT, RESULT_ENTERED, APPROVED, REPORTED; transitions not enforced in one place; order_item status not driven by result/report state.
- **Sample status:** Missing RECEIVED (you have COLLECTED then IN_PROCESS; “received in lab” is mixed into COLLECTED). Add RECEIVED, STORED, DISCARDED and clear transition rules.
- **Result workflow:** Uses verified_by/released_by; no **approved_by/approved_at** (pathologist); no “approval locks data, corrections = new version” rule; no version chain (previous_result_id).
- **Test master:** No category/department table; no units, methodology, specimen type as first-class fields; reference_ranges JSON only (no gender/age breakdown in model). Add lab_test_category and structured fields.
- **LabOrder:** patient_id and requested_by_doctor_id as String(50). Prefer UUID FKs to patient_profiles and users (or document that they are external refs and enforce in API).
- **Equipment:** equipment_code unique per hospital not enforced in DB (only in application). Add unique constraint (hospital_id, equipment_code).
- **RBAC:** LAB_SUPERVISOR and LAB_ADMIN do not exist in UserRole; PATHOLOGIST missing. Replace string roles with enum; add PATHOLOGIST; restrict “approve result / finalize report” to pathologist.
- **Billing:** lab_billing_integration router exists and is in scope of “out of scope for now”. Remove or stub billing endpoints and keep only hooks/interfaces/events.

### We don’t have (add)

- **Test catalogue:** lab_test_category (department/category); lab_test_master with normal ranges (by gender/age optional), units, methodology, specimen type, price fields; search + pagination + active/inactive (partially there, extend).
- **Order status machine:** Explicit DRAFT → REGISTERED → SAMPLE_COLLECTED → IN_PROCESS → RESULT_ENTERED → APPROVED → REPORTED → CANCELLED; validation on every transition; order_item status aligned.
- **Sample tracking:** Uniqueness of barcode/sample_no **per hospital**; lifecycle RECEIVED, STORED, DISCARDED; deterministic barcode/QR (server-side, unique per hospital).
- **Result entry & validation:** Validation against normal ranges; pathologist approval with approved_by/approved_at; immutability after approval; correction = new result version linked to previous.
- **Report:** lab_report_template (department-wise); “render payload” endpoint (structured JSON for PDF later); historical comparison (previous results same patient/test); secure online access (existing tokens are a start; no public URLs).
- **Equipment:** equipment–test mapping (lab_equipment_test_map); utilization counters; calibration/maintenance schedule (you have logs, add next_due and utilization).
- **QC:** QC schedule per equipment/test; QC result entry; deviation alerts and corrective action log.
- **Analytics:** Test volume, TAT, technician productivity; revenue hooks only (no billing).
- **Audit:** lab_action_log as a single, stock-like ledger for critical lab events (order registered, sample collected, result approved, report generated, etc.).
- **Repository layer:** No lab repository; add repositories for test, order, sample, result, report, equipment, QC, audit.

### We have but should delete/merge (remove)

- **lab_billing_integration** router: Remove or disable billing endpoints; keep only BillingHook interface or event payload for “order completed / report finalized” for future billing.
- **Duplicate/inconsistent role checks:** Unify on UserRole enum; remove LAB_SUPERVISOR/LAB_ADMIN until roles are defined; add PATHOLOGIST and use for approval.

---

## 3. CRITICAL DESIGN FLAWS (DATA CORRUPTION / MULTI-TENANCY)

1. **Missing hospital_id scoping on uniqueness**  
   lab_order_no, sample_no, barcode_value, report_number are globally unique. Two hospitals cannot use the same human-readable numbers. Risk: migration/merge issues; constraint violations when integrating. **Fix:** Unique constraints (hospital_id, lab_order_no), (hospital_id, sample_no), (hospital_id, barcode_value), (hospital_id, report_number).

2. **Sample tracking not unique per tenant**  
   Same as above: barcode_value and sample_no must be unique **per hospital**, not globally.

3. **Results not versioned/audited**  
   TestResult is overwritten in place for DRAFT/REJECTED; no previous_result_id; no “after approval, only add correction version” rule. Risk: no audit trail of who changed what and when; compliance failure. **Fix:** After approval, do not update in place; create new TestResult linked to previous; store entered_by, approved_by, approved_at; optional lab_action_log for result_approved.

4. **Missing status machine for orders/samples**  
   Order: no DRAFT, RESULT_ENTERED, APPROVED, REPORTED; transitions not validated (e.g. can cancel without checking current state in all code paths). Sample: RECEIVED/STORED/DISCARDED missing; transition rules not centralized. **Fix:** Explicit allowed transitions; single place (service or state machine) that validates current state → new state.

5. **No pathologist approval workflow**  
   verify/release exist but no role “Pathologist” and no “approve then lock” semantics. Risk: any LAB_TECH (or broken LAB_SUPERVISOR/LAB_ADMIN string check) could “release” without pathologist sign-off. **Fix:** Add PATHOLOGIST role; approval = pathologist only; after approval, result immutable (corrections as new version).

6. **Tables without hospital_id**  
   lab_order_items, sample_order_items, result_values, equipment_maintenance_logs have no hospital_id. For multi-tenant isolation and future sharding, either add hospital_id to these or strictly ensure all queries always join through a hospital-scoped parent and never expose cross-tenant data. Recommendation: add hospital_id to all for consistency and simpler security audits.

---

## 4. PROPOSED MODULE BOUNDARY

- **Inside LAB module:** Test catalogue (categories + tests), lab orders & order items, samples & sample–order_item mapping, equipment & equipment–test mapping, test results & result values, report templates & report generation payload, QC rules & QC runs, report sharing & access tokens, lab audit log & action log, chain of custody, compliance exports, lab analytics (volume, TAT, productivity, QC, equipment).  
- **Outside LAB module:**  
  - **Patient/Doctor/User:** Patient profiles, users, doctors (from existing auth and user/patient modules). Lab references patient_id and doctor_id (UUIDs recommended).  
  - **Prescription:** Optional link from lab_order to prescription (prescription_id); prescription module owns prescription; lab only stores reference.  
  - **Billing:** Out of scope; lab emits events/hooks (e.g. “order completed”, “report finalized”) and provides interfaces only; no billing endpoints in lab.  
  - **Notifications:** Report-ready and share-link notifications can stay in lab or move to a shared notification service; keep payloads in lab, delivery elsewhere if needed.

---

## 5. FINAL LIST OF ENTITIES / TABLES TO STANDARDIZE ON

Aligned with your minimum data model and the gaps above:

| Entity | Table | Notes |
|--------|--------|--------|
| Test category | lab_test_category | id, hospital_id, name/code, created_at, updated_at. |
| Test master | lab_test_master | id, hospital_id, category_id, test_code, test_name, units, methodology, specimen_type, normal ranges (JSON or separate table by gender/age), price fields (no billing integration), active, created_at, updated_at. Unique (hospital_id, test_code). |
| Lab order | lab_order | id, hospital_id, order_number (unique per hospital), patient_id (UUID FK), requested_by_doctor_id (UUID FK), source, priority, status (enum with full state machine), prescription_id (optional), encounter_id (optional), notes, timestamps, cancelled_* fields. |
| Lab order item | lab_order_item | id, lab_order_id, test_id, status, sample_collected_at, started_at, completed_at, timestamps. (hospital_id optional but recommended.) |
| Sample | lab_sample | id, hospital_id, sample_no (unique per hospital), barcode_value (unique per hospital), qr_value, lab_order_id, patient_id, sample_type, container_type, status (enum: COLLECTED, RECEIVED, IN_ANALYSIS, STORED, DISCARDED), collected_by, collected_at, received_by, received_at, etc. |
| Sample–order item | lab_sample_item | id, sample_id, lab_order_item_id. Unique (sample_id, lab_order_item_id). Same as current sample_order_items; rename for clarity if desired. |
| Equipment | lab_equipment | id, hospital_id, equipment_code (unique per hospital), name, category, manufacturer, model, status, calibration/maintenance dates, location, specifications, is_active, created_at, updated_at. |
| Equipment–test map | lab_equipment_test_map | id, hospital_id, equipment_id, test_id (or test master id). |
| Result (per order item) | lab_result | id, hospital_id, lab_order_item_id, version, previous_result_id (for corrections), status (DRAFT, APPROVED), entered_by, entered_at, approved_by, approved_at, signature_placeholder, timestamps. One “current” per order_item (or latest version). |
| Result value | lab_result_value | id, test_result_id, parameter_name, value, unit, reference_range, flag, is_abnormal, display_order, notes, timestamps. |
| Report template | lab_report_template | id, hospital_id, department/section, name, template_config (JSON), created_at, updated_at. |
| QC run | lab_qc_run | id, hospital_id, equipment_id, qc_rule_id, section, run_at, run_by, status, values (JSON), batch/lot, remarks, valid_until, created_at, updated_at. (Already largely there; align name to lab_qc_run.) |
| QC result | lab_qc_result | If you need per-parameter QC results separate from “values” JSON; otherwise qc_runs.values is enough. |
| Lab action log | lab_action_log | id, hospital_id, entity_type, entity_id, action, performed_by, performed_at, payload (JSON), created_at. Single ledger for critical events. |

Existing tables to rename/align (optional): test_results → lab_result; result_values → lab_result_value; lab_tests → lab_test_master after adding category; Sample → lab_sample; SampleOrderItem → lab_sample_item; QCRun → lab_qc_run. Keep lab_audit_logs and chain_of_custody; add lab_action_log for high-level events.

---

## 6. ITERATION PLAN (TITLES ONLY)

- **Iteration 1:** Test Catalogue Management  
- **Iteration 2:** Lab Test Registration (Orders)  
- **Iteration 3:** Sample Collection & Tracking  
- **Iteration 4:** Result Entry & Validation  
- **Iteration 5:** Report Generation  
- **Iteration 6:** Equipment Management  
- **Iteration 7:** Quality Control Workflows  
- **Iteration 8:** Analytics & Reports  

**Stop. Await "NEXT" to proceed to Iteration 1.**
