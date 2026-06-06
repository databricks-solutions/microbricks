# Healthcare Data Model

The reference domain is a small outpatient clinic system. Each of the six backend services owns one Lakebase database (one per env: `<svc>-dev` / `<svc>-test` / `<svc>-prod`). Tables loosely follow [HL7 FHIR](https://hl7.org/fhir/) resource shapes — recognizable to healthcare audiences without being a FHIR implementation.

> **PHI / synthetic data disclaimer.** Every sample row in this document is fabricated. The schema is illustrative — production use needs real PHI handling, encryption, BAAs, and compliance review.

---

## Cross-service rules (non-negotiable)

1. **No cross-DB foreign keys.** A `lab_result` may store a `patient_id` UUID, but Postgres has no FK constraint to `patient.id` — the patient row lives in a different database.
2. **IDs only across boundaries.** Services reference other services' data by UUID, never by human-readable fields (no copying `patient_name` into `lab_result`).
3. **No cross-service joins in service code.** If a route needs data from another service, the BFF orchestrates it; the service stays single-DB.
4. **Source of truth = the owning service.** If `lab-svc` shows a stale patient name, the fix is "join via BFF on read", not "denormalize patient name into `lab_result`".
5. **Soft delete by default.** Every table has `deleted_at TIMESTAMPTZ NULL`. Hard deletes only for compliance erasures.
6. **Auditable rows.** Every table has `created_at`, `created_by` (user email from OBO), `updated_at`, `updated_by`.

---

## Service overview

| Service | Database | Owns | Key cross-service IDs |
|---|---|---|---|
| `patient` | `patient_db` | demographics, addresses, consent | — |
| `provider` | `provider_db` | clinicians, organizations, specialties | — |
| `appointment` | `appointment_db` | scheduled visits, slots, visit types | `patient_id`, `provider_id` |
| `lab` | `lab_db` | orders, results, reference ranges | `patient_id`, `provider_id`, `appointment_id` |
| `prescription` | `prescription_db` | active/historical Rx, refills | `patient_id`, `provider_id` |
| `billing` | `billing_db` | invoices, claims, payments | `patient_id`, `appointment_id` |

```
                 patient_id ──────────────────┐
                   │                          │
provider_id ──┐    │                          │
              ▼    ▼                          ▼
        ┌──────────────┐    ┌─────┐    ┌──────────┐    ┌────────────┐    ┌─────────┐
        │ appointment  │◀───│ lab │    │ provider │    │ prescription│    │ billing │
        └──────────────┘    └─────┘    └──────────┘    └────────────┘    └─────────┘
              ▲   ▲           ▲   ▲                         ▲                ▲   ▲
              │   │           │   │                         │                │   │
              │   appointment_id  appointment_id             provider_id      patient_id
              │                                                                    │
              patient_id                                                appointment_id
```

---

## 1. `patient-svc` → `patient_db`

The system of record for who a patient is.

### `patient`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | server-generated |
| `mrn` | `TEXT UNIQUE NOT NULL` | medical record number, externally-facing |
| `given_name` | `TEXT NOT NULL` | |
| `family_name` | `TEXT NOT NULL` | |
| `birth_date` | `DATE NOT NULL` | |
| `sex_at_birth` | `TEXT NOT NULL CHECK (sex_at_birth IN ('female','male','other','unknown'))` | |
| `gender_identity` | `TEXT NULL` | free text |
| `preferred_language` | `TEXT NULL` | BCP-47 |
| `email` | `TEXT NULL` | |
| `phone` | `TEXT NULL` | E.164 |
| `created_at`, `created_by`, `updated_at`, `updated_by`, `deleted_at` | audit | |

Indexes: `(mrn)`, `(family_name, given_name)`, `(birth_date)`.

### `patient_address`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `patient_id` | `UUID NOT NULL REFERENCES patient(id)` | within-DB FK is fine |
| `kind` | `TEXT NOT NULL CHECK (kind IN ('home','work','billing'))` | |
| `line1`, `line2`, `city`, `region`, `postal_code`, `country` | `TEXT` | |
| audit cols | | |

### `patient_consent`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `patient_id` | `UUID NOT NULL REFERENCES patient(id)` | |
| `kind` | `TEXT NOT NULL CHECK (kind IN ('share_with_lab','share_with_billing','marketing','research'))` | |
| `granted` | `BOOLEAN NOT NULL` | |
| `effective_at` | `TIMESTAMPTZ NOT NULL` | |
| `expires_at` | `TIMESTAMPTZ NULL` | |
| audit cols | | |

### Sample rows

```sql
-- patient
('a3c1...', 'MRN-1001', 'Maya',     'Okafor',  '1989-04-12', 'female',  'female',     'en-US', 'maya.o@example.org',  '+14155550101'),
('b4d2...', 'MRN-1002', 'Hiroshi',  'Tanaka',  '1972-11-30', 'male',    'male',       'ja-JP', 'h.tanaka@example.org','+13105550199'),
('c5e3...', 'MRN-1003', 'Aaliyah',  'Greene',  '2014-07-23', 'female',   NULL,        'en-US', NULL,                   NULL),
('d6f4...', 'MRN-1004', 'Mateo',    'Vargas',  '1955-02-08', 'male',    'male',       'es-MX', 'mvargas@example.org', '+16175550144'),
('e7a5...', 'MRN-1005', 'Riley',    'Kim',     '1998-09-17', 'unknown', 'non-binary', 'en-US', 'r.kim@example.org',   '+12065550178');
```

### Non-ownership

- `patient` does not store appointments, prescriptions, lab results, or invoices.
- A "give me everything for patient X" view is composed by the **BFF**, not by `patient-svc`.

---

## 2. `provider-svc` → `provider_db`

The system of record for clinicians and the organizations they work in.

### `provider`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `npi` | `TEXT UNIQUE NOT NULL` | National Provider Identifier (US) |
| `given_name`, `family_name`, `credential_suffix` | `TEXT` | e.g. "MD", "RN", "PA-C" |
| `email` | `TEXT NOT NULL` | matches Databricks user email — links to OBO identity |
| `is_active` | `BOOLEAN NOT NULL DEFAULT true` | |
| `organization_id` | `UUID NOT NULL REFERENCES organization(id)` | |
| audit cols | | |

### `organization`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `name` | `TEXT NOT NULL` | |
| `kind` | `TEXT NOT NULL CHECK (kind IN ('clinic','hospital','lab','pharmacy'))` | |
| `time_zone` | `TEXT NOT NULL` | IANA, e.g. `America/Los_Angeles` |
| audit cols | | |

### `provider_specialty`

| Column | Type | Notes |
|---|---|---|
| `provider_id` | `UUID NOT NULL REFERENCES provider(id)` | composite PK with `specialty_code` |
| `specialty_code` | `TEXT NOT NULL` | e.g. `ENDO`, `CARDIO`, `FAM` |
| `is_primary` | `BOOLEAN NOT NULL DEFAULT false` | |

### Sample rows

```sql
-- organization
('org-001', 'Bay Family Health',     'clinic',   'America/Los_Angeles'),
('org-002', 'Riverside Diagnostics', 'lab',      'America/New_York');

-- provider
('prv-001', '1234567890', 'Sara',  'Levine',   'MD',    'sara.levine@bayhealth.example',  true,  'org-001'),
('prv-002', '2345678901', 'Anil',  'Sharma',   'NP',    'anil.sharma@bayhealth.example',  true,  'org-001'),
('prv-003', '3456789012', 'Diana', 'Marquez',  'MD',    'diana.marquez@riverside.example',true,  'org-002');
```

---

## 3. `appointment-svc` → `appointment_db`

Scheduled and historical visits. Stores IDs, never names.

### `appointment`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `patient_id` | `UUID NOT NULL` | references `patient_db`, no constraint |
| `provider_id` | `UUID NOT NULL` | references `provider_db`, no constraint |
| `slot_id` | `UUID NULL REFERENCES appointment_slot(id)` | |
| `visit_type_code` | `TEXT NOT NULL` | FK within DB |
| `scheduled_start` | `TIMESTAMPTZ NOT NULL` | |
| `scheduled_end` | `TIMESTAMPTZ NOT NULL` | |
| `status` | `TEXT NOT NULL CHECK (status IN ('booked','arrived','in_progress','completed','cancelled','no_show'))` | |
| `reason` | `TEXT NULL` | |
| audit cols | | |

Indexes: `(patient_id, scheduled_start DESC)`, `(provider_id, scheduled_start)`, `(status)` partial on `('booked','arrived','in_progress')`.

### `appointment_slot`

Pre-defined open slots a provider exposes. Used to prevent double-booking.

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `provider_id` | `UUID NOT NULL` | |
| `start_at` | `TIMESTAMPTZ NOT NULL` | |
| `end_at` | `TIMESTAMPTZ NOT NULL` | |
| `is_available` | `BOOLEAN NOT NULL DEFAULT true` | |
| `UNIQUE (provider_id, start_at)` | | prevents overlapping seeds |

### `visit_type`

| Column | Type |
|---|---|
| `code` (PK) | `TEXT` |
| `display_name` | `TEXT NOT NULL` |
| `default_duration_minutes` | `INT NOT NULL` |

### Sample rows

```sql
-- visit_type
('NEW_PATIENT', 'New patient intake', 45),
('FOLLOW_UP',   'Follow-up visit',     20),
('TELEHEALTH',  'Telehealth visit',    30);

-- appointment
('appt-001','a3c1...','prv-001', NULL, 'NEW_PATIENT', '2026-06-12 09:00-07', '2026-06-12 09:45-07', 'booked',      'annual physical'),
('appt-002','b4d2...','prv-001', NULL, 'FOLLOW_UP',   '2026-06-10 14:30-07', '2026-06-10 14:50-07', 'completed',   'medication review'),
('appt-003','c5e3...','prv-002', NULL, 'TELEHEALTH',  '2026-06-08 11:00-07', '2026-06-08 11:30-07', 'no_show',      NULL);
```

---

## 4. `lab-svc` → `lab_db`

Lab orders and their results.

### `lab_panel`

| Column | Type | Notes |
|---|---|---|
| `code` (PK) | `TEXT` | LOINC-style code |
| `display_name` | `TEXT NOT NULL` | |
| `category` | `TEXT NOT NULL CHECK (category IN ('chem','heme','endo','micro','other'))` | |

### `reference_range`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `panel_code` | `TEXT NOT NULL REFERENCES lab_panel(code)` | |
| `unit` | `TEXT NOT NULL` | |
| `low` | `NUMERIC NULL` | |
| `high` | `NUMERIC NULL` | |
| `sex_filter` | `TEXT NULL CHECK (sex_filter IN ('female','male'))` | NULL = applies to all |
| `min_age_years`, `max_age_years` | `INT NULL` | |

### `lab_order`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `patient_id` | `UUID NOT NULL` | reference |
| `ordering_provider_id` | `UUID NOT NULL` | reference |
| `appointment_id` | `UUID NULL` | reference |
| `panel_code` | `TEXT NOT NULL REFERENCES lab_panel(code)` | |
| `status` | `TEXT NOT NULL CHECK (status IN ('ordered','collected','resulted','cancelled'))` | |
| `ordered_at` | `TIMESTAMPTZ NOT NULL` | |
| `collected_at`, `resulted_at` | `TIMESTAMPTZ NULL` | |
| audit cols | | |

### `lab_result`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `lab_order_id` | `UUID NOT NULL REFERENCES lab_order(id)` | |
| `analyte_code` | `TEXT NOT NULL` | LOINC for the specific analyte (a panel has many) |
| `value_numeric` | `NUMERIC NULL` | |
| `value_text` | `TEXT NULL` | for non-numeric results |
| `unit` | `TEXT NULL` | |
| `flag` | `TEXT NULL CHECK (flag IN ('low','high','critical_low','critical_high'))` | |
| audit cols | | |

### Sample rows

```sql
-- lab_panel
('LP-CBC',   'Complete Blood Count',     'heme'),
('LP-LIPID', 'Lipid panel',              'chem'),
('LP-A1C',   'Hemoglobin A1c',           'endo');

-- lab_order
('lab-ord-001', 'b4d2...', 'prv-001', 'appt-002', 'LP-A1C',    'resulted',  '2026-06-10 14:35-07', '2026-06-10 14:50-07', '2026-06-11 09:14-07'),
('lab-ord-002', 'a3c1...', 'prv-001',  NULL,      'LP-LIPID',  'ordered',   '2026-06-12 09:30-07', NULL,                  NULL);

-- lab_result (just one analyte for the A1c order)
('lab-res-001', 'lab-ord-001', '4548-4', 6.8, NULL, '%', 'high');
```

---

## 5. `prescription-svc` → `prescription_db`

Active and historical prescriptions, plus refill workflow.

### `medication_catalog`

| Column | Type | Notes |
|---|---|---|
| `code` (PK) | `TEXT` | RxNorm code |
| `display_name` | `TEXT NOT NULL` | |
| `default_form` | `TEXT NOT NULL CHECK (default_form IN ('tablet','capsule','liquid','injection','patch','other'))` | |
| `is_controlled` | `BOOLEAN NOT NULL DEFAULT false` | |

### `prescription`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `patient_id` | `UUID NOT NULL` | reference |
| `prescribing_provider_id` | `UUID NOT NULL` | reference |
| `medication_code` | `TEXT NOT NULL REFERENCES medication_catalog(code)` | |
| `dose_text` | `TEXT NOT NULL` | e.g. "500 mg PO BID" |
| `quantity` | `INT NOT NULL` | |
| `refills_remaining` | `INT NOT NULL DEFAULT 0` | |
| `status` | `TEXT NOT NULL CHECK (status IN ('active','completed','cancelled','expired'))` | |
| `start_at` | `TIMESTAMPTZ NOT NULL` | |
| `end_at` | `TIMESTAMPTZ NULL` | |
| audit cols | | |

### `refill_request`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `prescription_id` | `UUID NOT NULL REFERENCES prescription(id)` | |
| `requested_at` | `TIMESTAMPTZ NOT NULL` | |
| `status` | `TEXT NOT NULL CHECK (status IN ('pending','approved','denied'))` | |
| `decided_by_provider_id` | `UUID NULL` | reference |
| `decided_at` | `TIMESTAMPTZ NULL` | |

### Sample rows

```sql
-- medication_catalog
('MED-METFORMIN', 'Metformin 500 mg',    'tablet',    false),
('MED-ATORVA',    'Atorvastatin 20 mg',  'tablet',    false),
('MED-AMOX',      'Amoxicillin 500 mg',  'capsule',   false);

-- prescription
('rx-001', 'b4d2...', 'prv-001', 'MED-METFORMIN', '500 mg PO BID', 60, 5, 'active',   '2026-05-15-07', NULL),
('rx-002', 'b4d2...', 'prv-001', 'MED-ATORVA',    '20 mg PO QD',   30, 3, 'active',   '2026-05-15-07', NULL);
```

---

## 6. `billing-svc` → `billing_db`

Invoices, payer claims, payments.

### `payer`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `name` | `TEXT NOT NULL` | |
| `kind` | `TEXT NOT NULL CHECK (kind IN ('commercial','medicare','medicaid','self_pay','other'))` | |

### `invoice`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `patient_id` | `UUID NOT NULL` | reference |
| `appointment_id` | `UUID NULL` | reference |
| `total_amount_cents` | `INT NOT NULL` | always store as integer cents |
| `currency` | `TEXT NOT NULL DEFAULT 'USD'` | |
| `status` | `TEXT NOT NULL CHECK (status IN ('draft','sent','partially_paid','paid','void'))` | |
| `issued_at` | `TIMESTAMPTZ NOT NULL` | |
| `due_at` | `TIMESTAMPTZ NULL` | |
| audit cols | | |

### `claim`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `invoice_id` | `UUID NOT NULL REFERENCES invoice(id)` | |
| `payer_id` | `UUID NOT NULL REFERENCES payer(id)` | |
| `submitted_at` | `TIMESTAMPTZ NULL` | |
| `status` | `TEXT NOT NULL CHECK (status IN ('draft','submitted','accepted','denied','partially_paid'))` | |
| `adjudicated_amount_cents` | `INT NULL` | |

### `payment`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `invoice_id` | `UUID NOT NULL REFERENCES invoice(id)` | |
| `claim_id` | `UUID NULL REFERENCES claim(id)` | |
| `amount_cents` | `INT NOT NULL` | |
| `method` | `TEXT NOT NULL CHECK (method IN ('card','ach','check','cash','adjustment'))` | |
| `received_at` | `TIMESTAMPTZ NOT NULL` | |
| audit cols | | |

### Sample rows

```sql
-- payer
('payer-001', 'Blue Shield',   'commercial'),
('payer-002', 'Self-Pay',      'self_pay');

-- invoice
('inv-001', 'b4d2...', 'appt-002', 18500, 'USD', 'sent',           '2026-06-10-07', '2026-07-10-07'),
('inv-002', 'a3c1...',  NULL,       4200,  'USD', 'partially_paid', '2026-06-01-07', '2026-07-01-07');
```

---

## How the BFF composes a "patient summary" page

Concrete worked example so the rules above feel real. The portal needs to render a clinician's patient summary view with: demographics, last 3 appointments, active meds, recent labs, outstanding balance.

The BFF:

1. `GET patient-svc /api/v1/patients/{id}` — demographics.
2. **In parallel** (`asyncio.gather`):
   - `GET appointment-svc /api/v1/appointments?patient_id={id}&limit=3&order=desc`
   - `GET prescription-svc /api/v1/prescriptions?patient_id={id}&status=active`
   - `GET lab-svc /api/v1/lab-orders?patient_id={id}&status=resulted&limit=5`
   - `GET billing-svc /api/v1/invoices?patient_id={id}&status_in=sent,partially_paid`
3. For each appointment, the response carries `provider_id` only. The BFF either:
   - calls `provider-svc /api/v1/providers?ids=...` to resolve display names in **one batched call**, or
   - leaves IDs as IDs and the React component renders a separate Suspense-bounded provider fetch.
4. Returns the composed shape to the React component.

What the BFF **must not** do: copy `patient.given_name` into the appointment response and store it. If the patient renames, the appointment response goes stale.

---

## Migrations

Each service uses **Alembic** with a per-service `migrations/` directory. The `hc-microservice-scaffold` skill provisions the initial migration. The `hc-lakebase-branching` skill notes that schema changes are applied to the *feature branch* DB locally — the feature branch carries the schema delta into PR CI automatically.

A schema change merging into `develop` does **not** automatically run on `<svc>-test` or `<svc>-prod`. Schema migrations to non-dev environments are gated by the `deploy-test.yml` and `deploy-prod.yml` workflows, which run `alembic upgrade head` against the target DB before `databricks bundle deploy`.
