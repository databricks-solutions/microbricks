# clinic-sim

Animated patient-journey simulator. Calls every backend service end-to-end
to exercise CRUD operations and visualize the flow in real time.

## What it does

Given a count between 1 and 10,000, the simulator runs that many patient
journeys against the real backend services in dev/test/prod, then streams
the events back to the browser via Server-Sent Events. The UI renders each
patient as a walking SVG figure that moves through the clinic floor as the
journey progresses:

```
Reception → Waiting Room → Exam Room → (Lab | Pharmacy) → Checkout
```

Each step corresponds to one or more real API calls against the matching
service:

| Stage | Service | Calls |
| --- | --- | --- |
| Register or pick patient | patient | `POST /patients` (~30%) or `GET /patients` (~70%) |
| Book appointment | appointment | `POST /appointments` |
| Patient arrives | appointment | `PATCH /appointments/{id}/status` → `arrived` |
| In progress | appointment | `PATCH /appointments/{id}/status` → `in_progress` |
| Order lab (~40%) | lab | `POST /lab-orders` then `PATCH .../status` → `collected` → `resulted` |
| Prescribe medication (~50%) | prescription | `POST /prescriptions` |
| Complete | appointment | `PATCH /appointments/{id}/status` → `completed` |
| Invoice + pay | billing | `POST /invoices` then `PATCH .../status` → `sent` → `paid` |

The BFF bounds per-request concurrency with `SIM_MAX_CONCURRENCY` (default 16).

## Prerequisites

- The six backend services (patient, provider, appointment, lab, prescription,
  billing) must already be running. The simulator does not provision compute.
- Catalog tables (`visit_type`, `medication_catalog`, `lab_panel`) must be
  seeded — run `make seed-dev` (or the per-service seed scripts) once per env.

## Architecture

Same shape as `hc-portal`:

- `src/clinic_sim/backend/`: FastAPI BFF. Forwards the user's OBO token to
  every downstream service. No persistent state of its own.
- `src/clinic_sim/clients/`: per-service typed clients that wrap the OBO
  token forwarding rules. Each has both list/read methods AND `create`/
  `update_status` methods.
- `src/clinic_sim/ui/`: React app. Single page — the simulator floor.
- `src/clinic_sim/__dist__/`: built React bundle, force-included by the
  bundle's `sync.include` glob (see `databricks.yml`).

## Local dev

```bash
cd frontend/clinic-sim
apx dev start
```

The CRUD endpoints write to the same per-feature-branch Lakebase branches
as the rest of the workspace, so you can run the simulator against your own
branch's database without polluting `production`.
