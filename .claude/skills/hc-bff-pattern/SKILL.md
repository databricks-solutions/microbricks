---
name: hc-bff-pattern
description: Add or modify a BFF (Backend-For-Frontend) aggregation route in hc-portal. Use when the user asks to "add a BFF endpoint", "join data across services", "compose a view that needs patient + appointment + lab", "fan out to multiple services", "build a portal route", or anything about cross-service aggregation. Enforces the "BFF is the only joiner" rule and the canonical concurrent-fetch / token-forwarding patterns.
---

# hc-bff-pattern

The BFF (`frontend/hc-portal/`) is the **only** place in this architecture where data from multiple services can be combined. Backend services never call each other. This skill is the source of truth for how to write a BFF route.

## When to use

- "Add a `/patient-summary/{id}` route that returns demographics + last 3 appointments + active meds"
- "Build the dashboard view that mixes lab + billing data"
- "Fan out to N services concurrently and merge the results"
- "Add a write route to the BFF" (rare — see [Write routes](#write-routes-rare-and-careful) below)

## When NOT to use

- The user wants to add a single-service route → it belongs in that service, not the BFF. Use `hc-obo-auth`.
- The user wants the BFF to *cache* data across requests → don't. Push the join down to UC if it's expensive.
- The user wants the BFF to call its *own* database → it doesn't have one. The BFF holds no state.

## The four BFF rules

1. **No persistent state.** No DB pool, no Redis, no shared cache. If you find yourself wanting one, stop and reconsider whether the data really belongs in a service.
2. **Concurrent fan-out.** Use `asyncio.gather` for independent calls. Sequential awaits are a code review reject.
3. **Per-request clients.** Construct service clients inside the route handler, not at module scope. Each request gets its own clients with its own bound user token.
4. **Forward both headers.** `Authorization: Bearer <token>` *and* `X-Forwarded-Access-Token`. The downstream service should be unable to tell whether the user called directly or via the BFF.

## Canonical aggregation route

Worked example: the `patient-summary` route from [`HEALTHCARE_DATA_MODEL.md`](../../../HEALTHCARE_DATA_MODEL.md#how-the-bff-composes-a-patient-summary-page).

```python
from __future__ import annotations
import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import user_token  # same shape as the service-side auth.py
from ..clients import (
    PatientClient,
    ProviderClient,
    AppointmentClient,
    LabClient,
    PrescriptionClient,
    BillingClient,
)

router = APIRouter(tags=["aggregations"])


class PatientSummaryOut(BaseModel):
    patient: dict
    last_appointments: list[dict]
    active_prescriptions: list[dict]
    recent_lab_orders: list[dict]
    outstanding_invoices: list[dict]


@router.get(
    "/patient-summary/{patient_id}",
    response_model=PatientSummaryOut,
    operation_id="getPatientSummary",
)
async def patient_summary(
    patient_id: UUID,
    token: Annotated[str, Depends(user_token)],
):
    async with (
        PatientClient(token) as patient,
        AppointmentClient(token) as appointment,
        LabClient(token) as lab,
        PrescriptionClient(token) as rx,
        BillingClient(token) as billing,
    ):
        # Concurrent fan-out — none of these depends on another
        results = await asyncio.gather(
            patient.get(patient_id),
            appointment.list_for_patient(patient_id, limit=3, order="desc"),
            lab.list_orders_for_patient(patient_id, status="resulted", limit=5),
            rx.list_active_for_patient(patient_id),
            billing.list_outstanding_for_patient(patient_id),
            return_exceptions=True,
        )

    # Partial-failure handling: if the patient lookup itself fails, 404/5xx out.
    # If a peripheral lookup fails, return what we have with a `partial: true` flag.
    p, appts, labs, rxs, bills = results
    if isinstance(p, Exception):
        raise HTTPException(502, "patient-svc unavailable") from p

    def _safe(value, default):
        return default if isinstance(value, Exception) else value

    return PatientSummaryOut(
        patient=p.model_dump(),
        last_appointments=[a.model_dump() for a in _safe(appts, [])],
        active_prescriptions=[r.model_dump() for r in _safe(rxs, [])],
        recent_lab_orders=[l.model_dump() for l in _safe(labs, [])],
        outstanding_invoices=[b.model_dump() for b in _safe(bills, [])],
    )
```

Notes on the shape:

- **`return_exceptions=True`**: a single failing peripheral call doesn't take down the whole page. The patient-load *is* required (we fail closed).
- **No N+1 calls**: when you need provider names for the appointments, batch them — `provider.list(ids=[...])`, not a loop of `provider.get(id)`.
- **Pydantic in / Pydantic out**: clients return validated objects, the BFF re-serializes for the response. Type errors caught at the boundary.

## When to resolve names vs leave IDs

The `patient-summary` example returns appointments with raw `provider_id` UUIDs. Two options:

| Option | When to pick |
|---|---|
| Resolve names in the BFF (one extra batched call) | The frontend renders names "above the fold"; users perceive the latency of every call |
| Leave IDs, frontend fetches names lazily via Suspense | The list is long, name resolution is optional, or cardinality is high (e.g. 50 appointments) |

The reference defaults to **resolve in the BFF** for primary aggregation views (patient summary, appointment detail), and **leave IDs** for list/index views (the "all appointments" page).

## Write routes (rare and careful)

The BFF should mostly be read-only aggregation. When a write spans services, prefer:

1. **Don't.** Reshape the request so it goes to one service. Often this is achievable.
2. If you can't, write a **saga-style** route: call service A, then service B, with explicit compensation if B fails. Document this loudly.
3. Never wrap multiple service writes in a "transaction" — there are no distributed transactions here.

Concrete example: "book an appointment AND send a notification". Wrong shape — the BFF books, then enqueues a notification job (Lakeflow / job task), with no expectation of atomicity. The notification can fire eventually.

## Timeouts and resilience

- Default per-call timeout: `connect=2s, read=5s` (in `_BaseSvcClient`).
- A BFF route that fans out to N services should respond within `max(per-call) + overhead`, not `sum(per-call)`. Always concurrent.
- No retries in v1. A 503 from a service propagates as a 502 from the BFF (or as a partial response). Adding retries hides flakiness — make services boring instead.
- No circuit breakers in v1. Adding `pybreaker` is a justified follow-up if you observe a service that takes everyone down with it.

## How downstream URLs are resolved

The BFF doesn't read per-service URL env vars. `clients/_base.py` derives them at runtime from two platform-injected vars:

- `DATABRICKS_APP_URL` — the BFF's own URL, e.g. `https://hc-portal-dev-7474643727449861.aws.databricksapps.com`.
- `DATABRICKS_WORKSPACE_ID` — the workspace this BFF is deployed in.

Sibling services share the same `<target>-<workspace_id>.<region>.databricksapps.com` tail and follow the `<svc>-<target>` naming pattern, so the BFF just strips its own `hc-portal` prefix off the host and prepends the per-service slug. No bundle `config.env`, no `<SVC>_SVC_URL` env vars, no `apps update` step. See `clients/_base.py:_own_app_suffix` for the canonical implementation.

This was deliberate: DAB has two relevant gaps — `${resources.apps.<key>.url}` does not resolve at bundle-deploy time (validate output shows `url=null`), and `bundle deploy` doesn't push `config.env` to the App spec without an extra `apps update` round-trip. Deriving from `DATABRICKS_APP_URL` sidesteps both.

## Local development

For non-Apps local dev, the BFF derives URLs the same way: set `DATABRICKS_APP_URL` to a fake `hc-portal-*-host` value that satisfies the prefix-strip — `respx` (or your local mocks) can intercept the resulting URLs. See `tests/conftest.py:_stub_svc_env` for a working stub. Then:

```bash
# Make the BFF accept the dev's CLI token as if it were forwarded
LOCAL_DEV_TOKEN_FROM_CLI=true
LOCAL_DEV_TOKEN=<paste from `databricks auth token -p hc-dev | jq -r .access_token`>
```

`apx dev start` from `frontend/hc-portal/` boots the React app + the BFF.

## Anti-patterns

| Pattern | Why it's wrong |
|---|---|
| Module-scope client (`patient_client = PatientClient(...)`) | Loses per-user token isolation; one global client shares one identity |
| Sequential awaits in a route (`a = await x(); b = await y()`) | Doubles the wall-clock time when nothing depends on the order |
| Caching response bodies in the BFF | Stale data reads as a bug; BFF is stateless on purpose |
| `try/except` swallowing service errors with empty default | Hides outages from the user; use `return_exceptions=True` + explicit `partial:true` flag |
| Joining data the frontend doesn't render | "Just in case" data inflates payloads and ties services together unnecessarily |

## Tests

`frontend/hc-portal/tests/integration/test_<route>.py` — runs against deployed preview apps in CI:

```python
@pytest.mark.integration
async def test_patient_summary_concurrent(httpx_client, user_token, sample_patient_id):
    import time
    t0 = time.monotonic()
    r = await httpx_client.get(
        f"/api/bff/patient-summary/{sample_patient_id}",
        headers={"X-Forwarded-Access-Token": user_token},
    )
    elapsed = time.monotonic() - t0
    assert r.status_code == 200
    # Concurrent fan-out: should be roughly the slowest single call, not their sum
    # Five 5xx calls in series would be ~25s; concurrent is < ~6s including overhead
    assert elapsed < 6.0, f"BFF took {elapsed:.1f}s — fan-out is probably sequential"
```

Plus a `test_partial_failure` that injects a 503 from one service via WireMock or a stub and asserts the response still 200s with `partial: true`.

## Verification

After adding a route:

- [ ] `apx dev check` passes (TS + Python types).
- [ ] OpenAPI regenerated; the React Suspense hook for the new route shows up in `ui/src/lib/api.ts`.
- [ ] Integration test exists and passes against the preview app.
- [ ] Per-call timeouts set on every client (the base class enforces this).
- [ ] No state added to the BFF process.
- [ ] No backend service was modified to call another backend service.
