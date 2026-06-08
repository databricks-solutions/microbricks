# Implementation Roadmap

This roadmap is the source of truth for **how to take this scaffolded reference architecture from "docs + skills only" to "fully runnable demo across dev/test/prod."** It's written for follow-up agents (and humans) who will pick up individual phases and drive them to completion.

> **How to use this file**
>
> 1. Phases are ordered by dependency. Start at Phase 1 unless a prior phase is already done.
> 2. Each phase is independently mergeable as one PR (or a small stack).
> 3. Every phase lists: **prerequisites**, **the skills to invoke**, **deliverables**, **acceptance criteria**, and **what comes next**.
> 4. The skills under `.claude/skills/` are the source of truth for *how* to do each step. This file tells you *which* steps to do *when*. Don't reinvent patterns — copy from the canonical references in those skills.
> 5. When a phase is done, mark its acceptance-criteria checkboxes and open the PR. Don't combine phases unless explicitly noted.

---

## Status legend

- ✅ done — already shipped in the initial scaffold
- 🚧 in progress — someone is actively working on this
- ⬜ not started — pick this up next

When you start a phase, edit this file in your branch to flip its checkbox to 🚧 and put your name + branch in the "Owner" line. When the phase merges, flip to ✅ and clear the owner.

---

## Current state

✅ Repository created at https://github.com/erinaldidb/microbricks
✅ Branch protections on `main` and `develop` (PR + CODEOWNERS review required)
✅ `prod` GitHub environment with manual approval gate
✅ Top-level docs: `README.md`, `ARCHITECTURE.md`, `HEALTHCARE_DATA_MODEL.md`, `CONTRIBUTING.md`, `CODEOWNERS`
✅ Six project-local Claude Code skills under `.claude/skills/`
✅ Four architecture diagrams in `docs/diagrams/`
✅ **Phase 1**: `patient-svc` scaffold complete (app/auth/db/routers, Alembic migration, tests, app.yaml); root uv workspace; BFF `patient.py` client stub
✅ **Phase 2**: Remaining five services (`provider`, `appointment`, `lab`, `prescription`, `billing`) scaffolded with byte-identical `auth.py`, `db.py`, `migrations/env.py`; unit tests pass for all six; BFF client stubs created for each.
✅ **Phase 3**: `frontend/hc-portal/` BFF + React UI scaffolded via `apx init`. Six typed clients now extend canonical `_BaseSvcClient`; `patient_summary` aggregation route fans out concurrently with `asyncio.gather` + partial-failure handling; React patient list + patient detail pages render via TanStack Router + Suspense. 8 unit tests cover token forwarding, partial-failure, 502 on required-call failure, and structural concurrency check.
✅ **Phase 4**: Synthetic seed data — `scripts/seeds/_common.py` (deterministic `ID` factory + Lakebase `connect()`) and `services/<svc>/seed/seed.py` for every service. Root `Makefile` runs `make seed-dev` (all six in dependency order) or per-service targets. Idempotent (`ON CONFLICT (id) DO NOTHING`). `tests/seeds/` verifies cross-service ID stability and synthetic-data shape without a DB.
✅ **Phase 5**: DAB bundle — root `databricks.yml` (three targets dev/test/prod with `mode: development|production` + per-target catalog vars + `--var` slots for the per-PR preview pattern), `resources/shared.yml` (common labels), six per-service `resources/<svc>.yml` files (each declares one `apps.<svc>_app`), and `resources/hc-portal.yml` for the BFF + UI. Per-service files are byte-identical except for entity names. CODEOWNERS now gates each `resources/<svc>.yml`. `databricks bundle validate -t {dev,test,prod}` returns "Validation OK!" against the schema shipped with CLI v0.295.0. Live deploy still deferred to Phase 7.

> **Architectural correction (2026-06-06):** `postgres_projects` resources were originally in each `resources/<svc>.yml` alongside the apps. That coupling caused a per-PR `bundle destroy` of a preview to wipe the shared dev Lakebase projects. Removed the `postgres_projects:` blocks from per-service files; project lifecycle moved to `scripts/lakebase-project-{up,down}.sh`. Apps still reference projects by path string. See `dev-bundle-destroy-disaster` memory note for the post-mortem.
✅ **Phase 5.1** (Phase 6 prep): Wired app resources + OBO into the bundle on `feature/HC-005-dab-bundle`. Each `apps.<svc>_app` now declares (a) `user_api_scopes: [iam.access-control:read, iam.current-user:read, sql]`, and (b) a `resources` block linking to its `postgres_projects.<svc>_db` with `CAN_CONNECT_AND_CREATE` — Apps platform now auto-injects PGHOST/PGUSER/PGDATABASE/PGPORT/PGSSLMODE/PGAPPNAME at runtime. `apps.hc_portal_app` declares `CAN_USE` on each of the six service apps and exposes the cross-app URLs via `config.env` with `${resources.apps.<svc>_app.url}` (DAB-time substitution; the per-app `app.yml` can't see those refs). Per-service `app.yaml` files now contain only `SERVICE_NAME` + `ENDPOINT_NAME` (the latter via `valueFrom: <svc>_db`). New `lakebase_branch` bundle variable replaces the six per-service `<svc>_endpoint` slots — `--var "lakebase_branch=feat-<slug>"` on dev binds every app to the operator's Lakebase feature branch (defaults to `production` for test/prod). `bundle validate -t {dev,test,prod}` still passes. `hc-dab-deployment` and `hc-microservice-scaffold` skills updated; `hc-lakebase-branching` documents the deploy verb.
✅ **Phase 7**: GitHub Actions workflows + per-PR Lakebase isolation. `scripts/sanitize-branch-slug.sh` is the canonical code-branch → slug transform; `scripts/lakebase-branch-{up,down}.sh` are the idempotent provision/teardown verbs that local devs and the workflows both call. Six workflows landed under `.github/workflows/`: `pr-validate.yml` (path-scoped matrix via dorny/paths-filter, six-service Lakebase fan-out, alembic on changed services only, bundle deploy with `app_name_suffix=-feat-<slug>` + `lakebase_branch=feat-<slug>`, preview-URL PR comment), `pr-cleanup.yml` (PR-close → bundle destroy + Lakebase teardown), `deploy-dev.yml` / `deploy-test.yml` / `deploy-prod.yml` (trunk deploys triggered by push to `develop` / `main`+`release/*` / `v*` tag, all running migrations BEFORE bundle deploy and smoke-testing all seven apps), and `nightly-orphan-cleanup.yml` (cron'd GC against the open-PR list). Auth uses OIDC: each workflow writes its named `~/.databrickscfg` profile (`hc-dev`/`hc-test`/`hc-prod`) with `auth_type = github-oidc` so the bundle's `workspace.profile` resolves in CI without checking in tokens. Bundle gained an `app_name_suffix` variable + per-user dev `root_path` so concurrent PR previews don't collide on bundle state. `databricks bundle validate -t {dev,test,prod}` and the preview shape (`--var app_name_suffix=-feat-test --var lakebase_branch=feat-test`) all pass. Live workflow runs blocked until Phase 0 prerequisites are completed (`vars.DATABRICKS_HOST_*`, `vars.DATABRICKS_*_CLIENT_ID`, OIDC trust per workspace).

✅ **Phase 7.1** (Phase 7 follow-up, landed on `feat-one`): Workflows now run end-to-end against the dev workspace. Material changes vs. the original Phase 7 shape:
> - **Auth: M2M client-credentials, not OIDC.** Each deploy job writes `~/.databrickscfg` from `vars.DATABRICKS_HOST_<ENV>` + `secrets.DATABRICKS_CLIENT_ID` + `secrets.DATABRICKS_CLIENT_SECRET` (scoped to the matching GitHub environment). Smoke tests mint a short-lived bearer by POSTing `client_credentials` to `${DATABRICKS_HOST}/oidc/v1/token` — `databricks auth token` only supports U2M, which is incompatible with SP auth. OIDC trust is still the documented migration path; the inline rationale lives in `pr-validate.yml`.
> - **Frontend build step.** `scripts/build-frontends.sh` auto-discovers every apx project under `frontend/` (anything with both `pyproject.toml` and `package.json`) and runs `apx frontend build` before `bundle deploy`. Each project writes to `src/<pkg>/__dist__/` (gitignored); the bundle force-includes those via `sync.include`. Without this, deploys would serve the BFF/API only and 404 on every page route.
> - **Parallel `bundle run` per app, then poll for `RUNNING`.** `bundle deploy` syncs source + updates resource specs but does NOT submit a new app deployment — without `bundle run`, the platform keeps serving the previous source (or stays UNAVAILABLE on first deploy). All seven `bundle run` calls now fire concurrently in the background (each subshell logs to its own file), then the workflow polls `apps get` per app until `app_status.state == RUNNING` (20×15s ceiling). `bundle deploy` already wires the cross-app `CAN_USE` ACLs at deploy-time, so parallelism is safe.
> - **Strict `/healthz` smoke.** Both the HTTP status code AND the response body are asserted — Apps' OBO gateway returns 200-with-HTML-login-body for unauthenticated requests, which would fool a vanilla `curl -fsS`. Backends mount `/api/v1/healthz`; the BFF mounts `/api/bff/healthz`; both return literal `{"ok":true}`.
> - **Project names no longer carry env suffixes.** Lakebase projects are `patient`/`provider`/… (each workspace IS its own env, so the namespace is already scoped); the corresponding apps are also unsuffixed in trunk deploys (e.g. `patient`, not `patient-dev`). Per-PR previews still get `-feat-<slug>` via the `app_name_suffix` variable.
> - **`CAN_CONNECT_AND_CREATE` on each app→postgres resource.** Was `CAN_CONNECT`; bumped so apps can also create per-user roles on first OBO connect (`hc-obo-auth` canonical flow).
> - **Canonical URL resolution from the apps API.** Apps embeds the workspace ID into each hostname (e.g. `hc-portal-7405606704848118.18.azure.databricksapps.com`), so `<svc>-<slug>.databricksapps.com` is not the real URL. Each deploy workflow's final step calls `databricks apps get <name> -o json` and feeds the `.url` field into `environment.url`; `pr-validate.yml` does the same fan-out for all seven apps and feeds them into the PR comment table.
> - **CLI pinned to `1.2.1`** across all four deploy workflows (was floating).
> - **New helper: `scripts/deploy-and-run-bundle.sh`** — wraps `bundle deploy` + per-app `bundle run` into one verb with `--only=<apps>` / `--skip-deploy` / `--restart` / `--no-wait` / `--var KEY=VALUE` passthrough. Devs use this for ad-hoc redeploys; CI uses the inlined steps for finer control over per-app log capture.

---

## Phase 0: One-time prerequisites (human must do, not an agent)

**Owner:** repo owner (you)
**Status:** ✅
**Estimated effort:** 30 min, mostly waiting

This phase is environmental setup that requires credentials/permissions an agent doesn't have. Do this once, before agents start Phase 1.

### Tasks

1. **Confirm three Databricks workspaces are FE-VM serverless type** (required for Lakebase Autoscale + Apps).
2. **Configure CLI profiles** in `~/.databrickscfg`:
   ```bash
   databricks auth login --host https://<dev-ws>.cloud.databricks.com  --profile hc-dev
   databricks auth login --host https://<test-ws>.cloud.databricks.com --profile hc-test
   databricks auth login --host https://<prod-ws>.cloud.databricks.com --profile hc-prod
   ```
3. **Verify CLI version is ≥ 0.285.0**: `databricks --version`. Upgrade with `brew upgrade databricks` if needed.
4. **Install local toolchain**: `apx`, `uv`, `bun`, `psql` (see README.md "Prerequisites" table).
5. **Create three Unity Catalog catalogs** — `hc_dev`, `hc_test`, `hc_prod` — one per workspace. (The DAB target variable `catalog` references these.)
6. **Set GitHub repository variables** (Settings → Secrets and variables → Actions → Variables):
   - `DATABRICKS_HOST_DEV`, `DATABRICKS_HOST_TEST`, `DATABRICKS_HOST_PROD` — workspace URLs
   - `DATABRICKS_DEV_CLIENT_ID`, `DATABRICKS_TEST_CLIENT_ID`, `DATABRICKS_PROD_CLIENT_ID` — service-principal client IDs (created in Phase 7)
7. **(Optional, for OIDC)** Register the GitHub repo as an OIDC trust on each workspace's account. If unavailable, agents will fall back to client-secret auth in Phase 7 and document the migration.

### Acceptance

- [ ] `databricks bundle validate -t dev` returns "no errors" against an empty bundle (run from a temp dir with a stub `databricks.yml`).
- [ ] `databricks postgres list-projects -p hc-dev` returns 200 (empty is fine).
- [ ] `apx --version` succeeds.
- [ ] GitHub repo variables are set.

### Next

→ Phase 1.

---

## Phase 1: Scaffold the first service (`patient-svc`) end-to-end

**Owner:** —
**Status:** ✅ (landed on `feature/HC-001-patient-service-scaffold`)
**Estimated effort:** 1 session (~2-3 hours of agent work)
**Skill to invoke:** `hc-microservice-scaffold` (with `hc-obo-auth` for the canonical code shapes)

> **What landed:** `services/patient/` complete — app/auth/db/routers, Alembic env + initial migration (`patient`, `patient_address`, `patient_consent`), unit + integration test scaffolds, `app.yaml`, `.env.example`. Root `pyproject.toml` registers the uv workspace; `frontend/hc-portal/src/hc_portal/clients/patient.py` is the BFF stub. Live-deploy checks (`apx dev start`, `alembic upgrade head`, `databricks bundle validate`) are environmental and verified naturally in Phases 5/6 once a workspace + DAB bundle exist.

The first service is the template. Once it's done correctly, the next five services are mechanical replication.

### Why patient first

Every other service references `patient_id`. Building it first means the BFF integration test (later phase) has something real to point at. It's also the service whose data model is most likely to drive UC RLS policy decisions.

### Prerequisites

- Phase 0 complete.
- Working directory is a fresh checkout of the repo on a `feature/HC-001-patient-service-scaffold` branch.

### Skills to invoke (in order)

1. `hc-microservice-scaffold` — drives the whole thing.
2. `hc-obo-auth` — when wiring the first route, copy `auth.py`, `db.py`, and the router from `references/canonical-patterns.md`. **Do not invent new shapes.**
3. `hc-lakebase-branching` — when the agent reaches the "create the dev Lakebase project" step. **The agent must ask the user before running `databricks postgres create-project` commands** (these cost money). The user should run them, the agent should verify.

### Deliverables

```
services/patient/
├── pyproject.toml                    # name = "patient-svc", uv workspace member
├── app.yaml                          # canonical shape from hc-microservice-scaffold step 3
├── README.md                         # one-sentence ownership statement + links
├── .env.example                      # PGHOST, ENDPOINT_NAME, etc. with placeholders
├── src/patient/
│   ├── __init__.py
│   ├── app.py                        # FastAPI entrypoint with lifespan
│   ├── auth.py                       # verbatim from hc-obo-auth canonical
│   ├── db.py                         # verbatim from hc-obo-auth canonical (per-user pool)
│   └── routers/
│       ├── __init__.py
│       └── patients.py               # GET /patients, GET /patients/{id} from canonical
├── migrations/
│   ├── env.py                        # reads PG* env vars, uses OAuthConnection
│   ├── alembic.ini
│   └── versions/
│       └── 0001_initial_patient_schema.py   # patient, patient_address, patient_consent
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── unit/test_models.py
    └── integration/test_obo.py        # the conformance test from hc-obo-auth
```

Plus root-level edits:
- Root `pyproject.toml` created (uv workspace) with `services/patient` as a member.
- `frontend/hc-portal/src/hc_portal/clients/patient.py` stub (deferred-import-able placeholder; full BFF wiring is Phase 4).

### Acceptance criteria

- [x] `pytest -m 'not integration'` passes (5 collected, 2 selected, 2 passed; 3 integration tests deselected).
- [x] App imports cleanly with no DB / env required at import time (`test_app_imports_cleanly`).
- [x] OBO conformance test scaffold exists for the trust path (401 without token, isolation across users, `/healthz`).
- [ ] `apx dev start` from `services/patient/` boots without import errors. *(deferred — needs a Lakebase feature-branch endpoint, validated in Phase 6)*
- [ ] `uv run alembic upgrade head` against a feature-branch Lakebase endpoint creates the three tables. *(deferred — Phase 6)*
- [ ] `curl -H "X-Forwarded-Access-Token: <user-token>" http://localhost:8001/api/v1/patients` returns `[]` (or seeded rows) with status 200. *(deferred — Phase 6)*
- [ ] `curl http://localhost:8001/api/v1/patients` (no header) returns 401. *(deferred — Phase 6)*
- [ ] `databricks bundle validate -t dev` still passes (the bundle is empty until Phase 5 but should not be broken). *(deferred — Phase 5 introduces the bundle)*

### Hand-off notes for the next phase

- Capture the exact `pyproject.toml` shape, `app.yaml` shape, `migrations/env.py` shape — Phase 2 services should be near-byte-identical except for the entity names. If `hc-microservice-scaffold` produced something subtly different from `hc-obo-auth`'s canonical patterns, **fix the skill, not the service**.

### Next

→ Phase 2.

---

## Phase 2: Scaffold the remaining five services

**Owner:** —
**Status:** ✅ (landed on `feature/HC-002-remaining-services`)
**Estimated effort:** 1 session (one PR per service is fine, or one PR for all five)
**Skill to invoke:** `hc-microservice-scaffold`

> **What landed:** Five services (`provider`, `appointment`, `lab`, `prescription`, `billing`) scaffolded with the exact `patient-svc` template — `auth.py`, `db.py`, and `migrations/env.py` are byte-identical across all six. Each has its own initial Alembic migration with within-DB FKs only (cross-service IDs stored as bare UUIDs). Five new BFF client stubs in `frontend/hc-portal/src/hc_portal/clients/`. Six entries in root `pyproject.toml` workspace + `CODEOWNERS`. Per-service `pytest -m 'not integration'` passes (15 total tests across the six services). Live-deploy checks (alembic against Lakebase, OBO conformance) deferred to Phase 6 once feature-branch endpoints exist.

Mechanically apply Phase 1's pattern to: `provider`, `appointment`, `lab`, `prescription`, `billing`.

### Prerequisites

- Phase 1 merged. The `patient-svc` template is the reference.

### Per-service details

| Service | Owns (from `HEALTHCARE_DATA_MODEL.md`) | Cross-service IDs stored | First migration tables |
|---|---|---|---|
| `provider` | clinicians, organizations, specialties | — | `provider`, `organization`, `provider_specialty` |
| `appointment` | scheduled & past visits | `patient_id`, `provider_id` | `appointment`, `appointment_slot`, `visit_type` |
| `lab` | lab orders, results, ranges | `patient_id`, `provider_id`, `appointment_id` | `lab_panel`, `reference_range`, `lab_order`, `lab_result` |
| `prescription` | active/historical Rx, refills | `patient_id`, `provider_id` | `medication_catalog`, `prescription`, `refill_request` |
| `billing` | invoices, claims, payments | `patient_id`, `appointment_id` | `payer`, `invoice`, `claim`, `payment` |

For each: feature branch, run `hc-microservice-scaffold`, write the first migration, write a placeholder list/get route, write the OBO conformance test.

### Deliverables

Five new directories under `services/` matching the `patient/` shape exactly. Five additions to root `pyproject.toml` workspace members. Five entries in `CODEOWNERS`.

### Acceptance criteria

- [x] All six services have identical structure (`diff services/{patient,billing}/src/*/auth.py`, `db.py`, and `migrations/env.py` all return empty; the only differences between any two services are entity-specific).
- [ ] All six pass their OBO conformance test against a real Lakebase feature branch. *(deferred — Phase 6 once feature-branch endpoints exist)*
- [ ] `databricks bundle validate -t dev` still passes. *(deferred — Phase 5 introduces the bundle)*
- [x] No service imports from another service (verified by hand; routers depend only on `..auth` / `..db` and never reach across `services/`).

### Next

→ Phase 3 (BFF + frontend) **or** Phase 5 (DAB resources) in parallel — they're independent.

---

## Phase 3: Build the BFF + frontend (`hc-portal`)

**Owner:** —
**Status:** ✅ (landed on `feature/HC-003-bff-frontend`)
**Estimated effort:** 1-2 sessions
**Skill to invoke:** `hc-bff-pattern` (with `hc-obo-auth` for the auth layer)

> **What landed:** `frontend/hc-portal/` scaffolded via `apx init` (React + TanStack Router + shadcn). BFF wired with canonical `auth.py` and a new `clients/_base.py` that all six per-service clients now extend. `routers/aggregations.py` ships the canonical `patient_summary` aggregation: per-request clients, `asyncio.gather(..., return_exceptions=True)` fan-out, peripheral-failure → `partial: true`, required-call failure → 502. React UI ships landing → patients list → patient detail pages, all behind `<Suspense>` + `<ErrorBoundary>`. `app.yml` resolves all six `<SVC>_SVC_URL` env vars from the bundle (consumed in Phase 5). 8 unit tests + 3 integration test scaffolds. The per-portal `databricks.yml` was removed in favor of the root bundle to be authored in Phase 5. Live `apx dev start` checks deferred to Phase 6 once Lakebase feature-branch endpoints exist.

### Prerequisites

- Phase 1 done (we need at least one real service to call). Phase 2 ideal but not strictly required — the BFF can be built incrementally as more services land.

### Deliverables

```
frontend/hc-portal/
├── pyproject.toml                    # name = "hc-portal", uv workspace member
├── app.yaml                          # env vars: <SVC>_SVC_URL for each service
├── README.md
├── src/hc_portal/
│   ├── __init__.py
│   ├── app.py                        # FastAPI mounted at /api/bff
│   ├── auth.py                       # same shape as service auth.py
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── _base.py                  # _BaseSvcClient from hc-obo-auth canonical
│   │   ├── patient.py                # PatientClient
│   │   ├── provider.py
│   │   ├── appointment.py
│   │   ├── lab.py
│   │   ├── prescription.py
│   │   └── billing.py
│   └── routers/
│       └── aggregations.py           # patient_summary route from hc-bff-pattern canonical
└── ui/                               # React app (apx default scaffold)
    ├── package.json
    ├── src/
    │   ├── routes/                   # tanstack-router pages
    │   │   ├── index.tsx             # landing
    │   │   ├── patients/index.tsx    # list view
    │   │   └── patients/$id.tsx      # detail using getPatientSummary
    │   ├── lib/api.ts                # Orval-generated, do not edit
    │   └── lib/selector.ts           # default query selector
    └── tests/
        └── e2e/                      # Playwright smoke tests
```

### Implementation notes

- The BFF is a single Databricks App, **not** six separate apps. It has both a React frontend AND a FastAPI BFF in one.
- `apx init hc-portal` from `frontend/` is the right starting point; then apply the BFF pattern by replacing the default routes with aggregation routes.
- Build at minimum: `GET /api/bff/patient-summary/{patient_id}` (the canonical example from `hc-bff-pattern`). One real route is enough to prove the pattern.
- Add Playwright smoke that hits the deployed app's `/api/bff/healthz` and one rendered React page.

### Acceptance criteria

- [ ] `apx dev start` from `frontend/hc-portal/` boots both the React UI and the BFF. *(deferred — needs all six services running locally + a Lakebase feature branch, validated in Phase 6)*
- [ ] BFF `GET /api/bff/patient-summary/{id}` returns valid JSON when called with a user token. *(deferred — verified by integration test once preview apps deploy in Phase 7)*
- [x] The aggregation route uses `asyncio.gather` (not sequential awaits) — `test_fanout_uses_asyncio_gather` asserts this structurally and `test_summary_happy_path_forwards_token_to_every_service` confirms five concurrent client calls.
- [x] `pytest` passes (8 unit tests, 3 integration tests skipped without env). Playwright smoke against deployed app deferred to Phase 7.
- [x] No state in the BFF process (no `redis`, no module-level mutable cache, no DB pool) — `clients/__init__.py` only re-exports classes; routes construct clients per-request.
- [x] No backend service was modified to call another backend service — only files outside `services/` were edited (`frontend/`, root `pyproject.toml`, `ROADMAP.md`, `CODEOWNERS`).

### Next

→ Phase 4 in parallel with Phase 5.

---

## Phase 4: Synthetic seed data + per-service Genie spaces (optional but recommended)

**Owner:** —
**Status:** ✅ (landed on `feature/HC-003-bff-frontend`)
**Estimated effort:** 1 session
**Skill to invoke:** `fe-databricks-tools:databricks-data-generation` (healthcare profile)

> **What landed:** A shared `scripts/seeds/_common.py` module with a deterministic UUIDv5-based `ID` factory, a sync `connect()` helper that mints a Lakebase OAuth credential the same way runtime `db.py` does, and demographically diverse name/address/language pools. Six per-service loaders at `services/<svc>/seed/seed.py` populate each database with `~50` patients / `~5` providers / `~200` appointments / `~60` lab orders / `~30` prescriptions / `~100` invoices. Cross-service IDs (`patient_id`, `provider_id`, `appointment_id`) match across DBs because they're derived from `(entity, ordinal)` rather than queried. Every insert is idempotent (`ON CONFLICT (id) DO NOTHING`). A root `Makefile` orchestrates `make seed-dev` (all six, dependency order) and per-service targets. `tests/seeds/` covers ID determinism and synthetic-data shape with no DB requirement.

### Deliverables

- `scripts/seeds/_common.py` — shared `ID`, `connect()`, generators, volume knobs (`SEED_NUM_*` env vars).
- `services/<svc>/seed/seed.py` for every service — thin loaders that import from `_common.py`.
- Root `Makefile` with `seed-dev` + `seed-<svc>` + `seed-tests` targets.
- `tests/seeds/test_seed_determinism.py` — verifies cross-service ID stability and synthetic-data invariants.
- `scripts/seeds/README.md` documenting the deterministic-ID contract and volume knobs.
- Per-service README addendum pointing at `make seed-<svc>` and the shared helpers.

### Acceptance criteria

- [x] Loaders use `INSERT ... ON CONFLICT (id) DO NOTHING` everywhere; re-running any seed is a no-op.
- [x] Cross-service IDs are guaranteed to match across DBs (`tests/seeds/test_seed_determinism.py:test_cross_service_id_stability`).
- [x] No real names, real MRNs, or real medical record content. All names come from a fixed, hand-curated diverse pool; MRNs are `MRN-1000+i`; NPIs are `1000000000+i`.
- [x] `make seed-dev` populates all six dev DBs end-to-end. Verified post-Phase 6: row counts patient 50, provider 5, appointment 200, lab 60, prescription 30, billing 100.
- [x] BFF's `patient-summary` route returns rich data for a seeded patient ID across all services. Verified — see Phase 6 acceptance.

### Next

→ Phase 6 (the BFF can be visually demoed once seeded). The DAB phase doesn't depend on this.

---

## Phase 5: Author DAB bundle (`databricks.yml` + `resources/*.yml`)

**Owner:** —
**Status:** ✅ (landed on `feature/HC-005-dab-bundle`)
**Estimated effort:** 1 session
**Skill to invoke:** `hc-dab-deployment`

> **What landed:** Root `databricks.yml` (three targets with `mode: development|production`, per-target `catalog` variable, `preview_slug` + six per-service `<svc>_endpoint` `--var` slots for the PR preview pattern). `resources/shared.yml` declares a `common_labels` variable. Six per-service files (`resources/<svc>.yml`) each declare a `postgres_projects.<svc>_db` Lakebase Autoscale project (PG17, autoscale 0.5–4 CU) plus one `apps.<svc>_app` pointing at `../services/<svc>`. `resources/hc-portal.yml` defines the BFF/UI app pointing at `../frontend/hc-portal`; the per-app cross-service URL wiring stays in `frontend/hc-portal/app.yml` (now using snake_case `resources.apps.<svc>_app` keys to match the bundle). CODEOWNERS now gates each `resources/*.yml`. `databricks bundle validate -t {dev,test,prod}` returns "Validation OK!" with no warnings.
>
> **Schema corrections vs. the skill template:** the skill's example used `databases:` + `CAN_USE` permission + an in-app `database` resource block; the actual CLI v0.295.0 schema requires `postgres_projects:` (Lakebase Autoscale) or `database_instances:` (provisioned). We picked `postgres_projects` to match the rest of the project (per `hc-lakebase-branching`). The `app.resources` block was dropped from each service file — it's only valid for `database_instances` and would need different fields anyway. Production targets got `workspace.root_path: /Workspace/.bundle/...` to address the "single canonical deploy location" recommendation `bundle validate` emits otherwise. The `hc-dab-deployment` skill should be updated in a follow-up to reflect these corrections.

### Prerequisites

- Phase 1 done (need at least one real `services/<svc>/` directory to point `source_code_path` at).
- Phase 2 ideal — easier to author all six resource files at once than to add them incrementally.
- Phase 3 ideal — the `hc-portal.yml` resource needs to know all six service apps' resource keys.

### Deliverables

```
databricks.yml                        # root bundle, includes resources/*.yml
resources/
├── shared.yml                        # cross-cutting variables
├── patient.yml                       # apps + databases for patient-svc
├── provider.yml
├── appointment.yml
├── lab.yml
├── prescription.yml
├── billing.yml
└── hc-portal.yml                     # apps for the portal + BFF
```

Use the templates from `hc-dab-deployment` SKILL verbatim. Per-service files must be near-identical except for the entity name.

### Acceptance criteria

- [x] `databricks bundle validate -t dev` returns no errors.
- [x] `databricks bundle validate -t test` returns no errors.
- [x] `databricks bundle validate -t prod` returns no errors.
- [x] `databricks bundle deploy -t dev` succeeds against the dev workspace and creates 7 apps + 6 Lakebase projects (verified Phase 6).
- [x] App URLs in dev workspace return 200 on `/healthz` and 401 on `/api/v1/*` without a token (verified Phase 6).
- [x] `hc-portal-dev` calls all six service URLs end-to-end. The BFF resolves URLs at runtime (`clients/_base.py`) — explicit `<SVC>_SVC_URL` override if set, else derived from the platform-injected `DATABRICKS_APP_URL`. See Phase 6's "Cross-app URL resolution" section for the rationale.

### Next

→ Phase 7 (CI/CD).

---

## Phase 6: One-time Lakebase project provisioning per env

**Owner:** —
**Status:** ✅ for dev (test + prod still ⬜ until owner deploys those targets)
**Estimated effort:** 30 min
**Skill to invoke:** `hc-dab-deployment` (preferred) or `hc-lakebase-branching` (fallback), `hc-microservice-scaffold` step 4

### Prerequisites

- Phase 5 merged (including the Phase 5.1 follow-up: app resources, OBO scopes, `lakebase_branch` variable). The bundle now manages every Lakebase project + every app + every cross-resource permission.

### Tasks

The clean way is bundle-managed (preferred) — one verb per env, atomic create or update:

```bash
# dev — agent can run this autonomously
databricks bundle deploy -t dev

# test — ASK USER before running
databricks bundle deploy -t test

# prod — ASK USER before running
databricks bundle deploy -t prod
```

Each command creates 7 Apps + 6 Lakebase Autoscale projects, each project with a `production` branch + `primary` endpoint. The bundle deploy is idempotent.

If for some reason a per-resource manual fallback is needed (e.g. Lakebase quota issues, or working around a bundle bug):

```bash
# dev manual fallback
for svc in patient provider appointment lab prescription billing; do
  databricks postgres create-project $svc-dev -p hc-dev
done
```

Then deploy the apps separately: `databricks bundle deploy -t dev`. Cost: see `hc-lakebase-branching/references/cli-walkthrough.md`.

### Acceptance criteria

- [x] `databricks bundle deploy -t dev` succeeds end-to-end (6 dev Lakebase projects + 7 dev Apps).
- [ ] All 18 Lakebase projects exist (6 services × 3 envs): only the 6 dev ones exist so far. Test + prod deferred until owner runs `databricks bundle deploy -t {test,prod}`.
- [x] Each dev project has a `production` branch with a `primary` read-write endpoint.
- [x] Every dev app has the postgres resource attached: `databricks apps get <svc>-dev -p hc-dev -o json | jq '.resources'` returns the `<svc>_db` postgres entry with `CAN_CONNECT_AND_CREATE`.
- [x] `hc-portal-dev` has `CAN_USE` resources for all six service apps. (No `config.env` URL injection — see "Cross-app URL resolution" below.)
- [x] OBO scopes correct: each backend service declares `user_api_scopes: [postgres]`; `hc-portal` declares `[sql, postgres]`. Verified via `apps get`.
- [x] All seven dev apps start and serve. Six backend services + the BFF: `/healthz` returns 200, `/api/v1/*` returns 401 unauth (platform OBO gateway gates `/api/v1/*` automatically).
- [x] All six dev DBs have schema applied via `alembic upgrade head` against each `<svc>-dev/branches/production/endpoints/primary` using the operator's CLI token.
- [x] All six dev DBs are seeded via `make seed-dev`. Row counts: patient 50, provider 5, appointment 200, lab 60, prescription 30, billing 100. Cross-service `patient_id`/`provider_id` references are deterministic UUIDv5 values that match across services.
- [x] All six service apps + hc-portal deployed and ACTIVE. Each service `GET /api/v1/<route>` returns its full seeded set with the operator's OBO token (verified via curl with `X-Forwarded-Access-Token` + `X-Forwarded-Email`).
- [x] BFF aggregation works end-to-end: `GET /api/bff/patient-summary/<patient_id>` returns a 120 KB JSON with `patient`, `last_appointments`, `active_prescriptions`, `recent_lab_orders`, `outstanding_invoices`, `partial=false` — proves the `asyncio.gather` fan-out across all five downstream services succeeds with the operator's forwarded token.

### Cross-app URL resolution (default + override)

The original Phase 5 design wired downstream URLs through DAB substitution (`${resources.apps.<svc>_app.url}`) in `resources/hc-portal.yml` `config.env`. Two DAB asymmetries break this:

1. `${resources.apps.<key>.url}` does **not** resolve at `bundle deploy` time — `bundle validate -o json` shows `resources.apps.<key>.url = null`, so the unsubstituted `${...}` reaches the App spec and Apps drops the env block.
2. `bundle deploy` syncs source files but does NOT push a `config.env` block to the running App spec; an extra `apps update` round-trip would be required.

**Resolution (final design):** the BFF's `clients/_base.py` resolves each downstream URL in two steps:

1. **Explicit override** — read `<SVC>_SVC_URL` (e.g. `PATIENT_SVC_URL`). Set this in `frontend/hc-portal/app.yml` (`env:`) or in a bundle `config.env` block when you need to point at a non-canonical host: local dev (`http://localhost:800x`), a per-PR preview, an alternate region, etc.
2. **Runtime-derived default** — the BFF strips its own `hc-portal` prefix off the platform-injected `DATABRICKS_APP_URL` (e.g. `hc-portal-dev-7474643727449861.aws.databricksapps.com`) and prepends the per-service slug. Sibling services share the `<svc>-<target>-<workspace_id>.<region>.databricksapps.com` pattern by construction.

This means: zero cross-app wiring needed for the canonical layout, an env-var escape hatch for everything else, and no dependency on DAB resolving `.url` references. Both paths are unit-tested (`tests/unit/test_base_url_resolution.py`) and live-verified in dev (override `LAB_SVC_URL` to an unreachable host → `partial=true` for `recent_lab_orders` while the other four downstreams keep working).

### Next

→ Phase 7.

---

## Phase 7: Author GitHub Actions workflows

**Owner:** —
**Status:** ✅ (landed on `feature/HC-005-dab-bundle`)
**Estimated effort:** 1-2 sessions
**Skill to invoke:** `hc-gitflow-cicd` (with `hc-lakebase-branching` for the per-PR scripts)

> **What landed:** Six workflows under `.github/workflows/` plus three idempotent shell helpers in `scripts/` (`sanitize-branch-slug.sh`, `lakebase-branch-up.sh`, `lakebase-branch-down.sh`). The bundle root gained an `app_name_suffix` variable + per-user dev `root_path` so per-PR previews are isolated on disk and in app names. Auth uses per-environment GitHub secrets (`secrets.DATABRICKS_CLIENT_ID` + `secrets.DATABRICKS_CLIENT_SECRET` scoped to the `dev`/`test`/`prod` GitHub environments) — each workflow writes a named `~/.databrickscfg` profile so the bundle's `workspace.profile: hc-<env>` resolves; OIDC migration path is documented inline in `pr-validate.yml`. The branch → environment map is unchanged from the skill: PRs get previews in `dev`, `develop` deploys to dev, `main` + `release/*` deploys to test, `v*` tag deploys to prod (manual approval gate via `prod` environment). Preview deploys provision all six Lakebase feature branches per PR (COW from `production`, scale-to-zero) so every app's postgres resource resolves; alembic only runs against the services the PR actually touched. `databricks bundle validate` passes for all three targets and for the preview shape.
>
> **Phase 7 follow-up needed (does NOT block Phase 7's close):** the first live `pr-validate` run on PR #1 surfaced two pre-existing issues in earlier phases — fixed in the same PR — and one environmental blocker that is intentionally deferred:
> 1. ✅ **`pytest` couldn't find the local module in any of the seven Python projects** because `[tool.uv] package = false` was set repo-wide for runtime parity but the pytest configs didn't compensate. Added `pythonpath = ["src"]` to all seven `[tool.pytest.ini_options]` blocks; portal-checks + all six service-checks now pass.
> 2. ✅ **`ty check` (lint) failed in `services/<svc>/src/<svc>/db.py`** with two real type errors around `AsyncConnectionPool`'s generic parameter. Fixed in patient and propagated to the other five (the file is byte-identical across services); `ty check src` now returns "All checks passed" everywhere.
> 3. ❌ **Every Databricks-touching CI job is blocked by the dev workspace's IP ACL.** FE-VM provisioning installs a managed allowlist (`fevm-managed-allowlist-DoNotModify`, ~500 ranges) covering Databricks regional egress but NOT GitHub-hosted runner egress. Confirmed on dev (`enableIpAccessLists=true`); prod has `enableIpAccessLists=""` so prod is unaffected; test was not checked. **Decision: keep CI red on the Databricks-touching jobs and ship Phase 7 as-is.** Three deferred unblock options live in the `github-runner-ip-acl` memory note: self-hosted runner inside FE-VM, separate non-managed IP ACL for GitHub IP ranges, or disable the ACL on dev. Phase 8 picks one.
>
> **Workaround until Phase 8 unblocks CI: `scripts/ci-local.sh`.** A local emulator that runs the same logical pipelines from a developer's workstation (whose IP is already allowlisted). Subcommands `pr-validate`/`pr-cleanup`/`deploy {dev,test,prod}`/`nightly-cleanup` mirror the four workflow shapes step-for-step; only difference is auth resolution (`~/.databrickscfg` profile vs. GH env-secret). See "Running CI locally" in `CONTRIBUTING.md`. End-to-end verified on this branch.

### Prerequisites

- Phase 5 (so deploy workflows have something to deploy).
- Phase 6 (so dev project exists for PR previews).
- GitHub repo variables and OIDC config from Phase 0.

### Deliverables

```
.github/
├── workflows/
│   ├── pr-validate.yml               # path-scoped matrix, per-feature Lakebase branch
│   ├── pr-cleanup.yml                # on PR close: tear down preview + Lakebase branch
│   ├── deploy-dev.yml                # push to develop
│   ├── deploy-test.yml               # push to release/* or main
│   ├── deploy-prod.yml               # tag v* + manual approval
│   └── nightly-orphan-cleanup.yml    # GC orphan Lakebase branches with no open PR
└── release-template.md               # PR description template for release PRs

scripts/
├── sanitize-branch-slug.sh           # canonical slug transform from hc-lakebase-branching
├── lakebase-branch-up.sh             # idempotent create
└── lakebase-branch-down.sh           # idempotent teardown
```

### Implementation notes

- Use OIDC, not long-lived PATs. If OIDC isn't available in a workspace, fall back to client-secret stored as a GitHub *environment* secret (not repo secret), and document the migration path inline in the workflow.
- `pr-validate.yml` MUST be path-scoped via `dorny/paths-filter` so a PR touching only `services/lab/` doesn't spin up `patient`'s preview.
- `deploy-prod.yml` MUST use `environment: prod` to inherit the manual-approval gate already configured in Phase 0.
- All four deploy workflows MUST run `alembic upgrade head` BEFORE `databricks bundle deploy`. Running migrations after the app deploys means a brief window of broken prod.

### Acceptance criteria

- [x] Six workflow files exist under `.github/workflows/` and parse as valid YAML (`pr-validate`, `pr-cleanup`, `deploy-dev`, `deploy-test`, `deploy-prod`, `nightly-orphan-cleanup`).
- [x] Three shell helpers exist + are executable: `scripts/sanitize-branch-slug.sh`, `scripts/lakebase-branch-up.sh`, `scripts/lakebase-branch-down.sh`. Slug transform produces the cases listed in `hc-lakebase-branching` (verified locally).
- [x] `databricks bundle validate -t dev` returns "Validation OK!" for both the trunk-dev shape and the preview shape (`--var "app_name_suffix=-feat-<slug>" --var "lakebase_branch=feat-<slug>"`).
- [x] `release-template.md` exists for `release/*` → `main` PRs.
- [x] PR #1 (Phase 5/6/7 cumulative) opened against `develop` and triggered `pr-validate.yml`. The path filter correctly identified all changed services + portal + infra.
- [x] `pr-validate.yml` `service-checks` matrix passes for all six services (lint + unit tests) — lint errors and pytest module-resolution issues fixed in the same PR.
- [x] `pr-validate.yml` `portal-checks` passes for the BFF (12 unit tests).
- [x] `pr-validate.yml` `bundle-validate` and `preview-deploy` jobs reach Databricks — *unblocked via Phase 7.1's M2M auth shape and (where required) by deploying outside the FE-VM IP ACL; live on `feat-one`.*
- [x] `deploy-dev.yml` deploys all six services + portal to dev end-to-end on push to `develop` (frontend build → bundle deploy → parallel `bundle run` → wait for `RUNNING` → strict `/healthz` smoke → URL resolution).
- [ ] Close a PR. `pr-cleanup.yml` runs. *(verified locally via `scripts/ci-local.sh pr-cleanup`; live CI verification deferred to the first non-Phase-7 PR close)*
- [ ] Tag `v0.0.1`. `deploy-prod.yml` waits for approval, then deploys. *(covered in Phase 8 once the prod env's variables/secrets are populated.)*
- [ ] `actionlint .github/workflows/*.yml` is clean. *(deferred — actionlint not installed locally; Phase 8 fresh-clone test covers)*

### Next

→ Phase 8 (polish & validate end-to-end).

---

## Phase 8: End-to-end validation + demo polish

**Owner:** unassigned
**Status:** ⬜
**Estimated effort:** 1 session
**Skill to invoke:** None — this is integration work

The goal is a clean clone-to-demo path that a stranger could follow.

### Tasks

0. **Confirm CI ↔ Databricks reachability per env.** Dev is verified end-to-end on `feat-one` after Phase 7.1; test and prod still need a first live deploy. If a workspace's FE-VM-managed IP allowlist blocks GH-hosted runner egress (`github-runner-ip-acl` finding), pick an unblock: self-hosted runner inside FE-VM (cleanest, heaviest); separate non-managed IP ACL containing GitHub's `actions` IP ranges (lightest, requires periodic refresh); or disable the ACL on the affected env for a reference-only workspace.
1. **Fresh-clone test**: in a new directory, clone the repo, follow `README.md` quickstart from scratch. Note every step that breaks or needs clarification. Fix the docs.
2. **End-to-end smoke**: log into the deployed `hc-portal-dev` URL as your user, navigate to a patient detail page, see real data flowing from all six services. Take screenshots; add to `docs/screenshots/` and link from README.
3. **Negative-path test**: open a PR with a deliberately-failing test in one service. Confirm `pr-validate.yml` blocks the merge.
4. **Cost audit**: check `databricks postgres list-endpoints` in dev. Confirm idle endpoints have scaled to zero. Document expected dev-env monthly cost in the README.
5. **Add `docs/runbooks/`**:
   - `prod-rollback.md` — how to redeploy a previous tag.
   - `hotfix.md` — the hotfix flow with a worked example.
   - `lakebase-branch-orphan.md` — what to do if a feature branch is leaked.
6. **Update this `ROADMAP.md`** to flip phases 1-7 to ✅.

### Acceptance criteria

- [ ] A new contributor can go from `git clone` to a working PR with a preview app in under 30 min, following only the README and CONTRIBUTING.md.
- [ ] Screenshots in README show the actual deployed demo.
- [ ] All 18 Lakebase projects scale to zero when idle.
- [ ] `pr-validate.yml` blocks failing PRs.
- [ ] Three runbooks exist.

### Next

→ Demo it. Optional follow-ups in the next section.

---

## Future / optional follow-ups

Not on the critical path, but valuable when basics are done:

- **Phase 9 — Service mesh observability**: Lakeflow pipelines that ingest each service's CDC stream into UC for cross-service analytics (without violating "no cross-service joins in service code"). Demonstrates "operational data → analytical data" pattern.
- **Phase 10 — Saga / events**: replace the BFF "book appointment + create draft invoice" example with an event-driven version using a Lakeflow trigger or Databricks job. Shows the alternative pattern.
- **Phase 11 — RLS demo**: configure Unity Catalog row-level security so two test users see different patients. Wire the `test_route_isolates_users` conformance test in CI to assert this. Demonstrates the OBO trust path under load.
- **Phase 12 — Read-replica for prod**: configure `read-replica` endpoints in `<svc>-prod` Lakebase projects, document when to use them in the BFF.
- **Phase 13 — Multi-region**: extend `databricks.yml` to deploy to a second region for prod. Document the active/passive failover model.
- **Phase 14 — APX UI library**: build a shared `@hc-portal/ui` component library for repeated patterns (patient header, lab panel, etc). Consume from `frontend/hc-portal/` and any future internal-facing portals.

---

## Working on a phase: protocol

For agents and humans both:

1. Read this whole file first.
2. Pick the lowest-numbered ⬜ phase. Don't skip ahead.
3. Read the phase's "Skills to invoke" section. Open those skill files in order. Internalize the canonical patterns before touching code.
4. Check out a feature branch following `CONTRIBUTING.md` naming: `feature/HC-<ticket>-<slug>`.
5. If the phase requires a Lakebase branch, run the `hc-lakebase-branching` flow before writing any DB code.
6. Implement. Run the phase's acceptance criteria locally. Don't rely on CI to find your bugs.
7. Open a PR against `develop`. Title format: `<type>(<scope>): <description>` per Conventional Commits.
8. After merge: in your next branch, edit this file to flip the phase to ✅ with a one-line summary of what landed.

If a phase reveals that a skill is wrong, **fix the skill in the same PR** (or a stacked PR landing first). Skills are the source of truth — if reality contradicts them, one of the two needs to update.

---

## Open questions to resolve before each phase

A non-exhaustive list of decisions that need to be made when picking up specific phases. If an agent hits one of these, **ask the user** before guessing:

- ~~**Phase 1**: Which Postgres extensions do we need?~~ Resolved: `pgcrypto` for `gen_random_uuid()` — see `services/patient/migrations/versions/0001_initial_patient_schema.py`. Apply the same to Phase 2 services.
- **Phase 2**: Do we generate Pydantic models from SQL via `sqlc`-style codegen, or hand-write them? (Phase 1 hand-wrote them in `routers/patients.py`; default is to keep hand-writing for clarity in a reference repo.)
- **Phase 3**: Do we use Orval for typed BFF→service clients, or hand-write? (Default: hand-write per `hc-bff-pattern`. Orval is for the React→BFF direction only.)
- **Phase 4**: How many synthetic patients? (Default: 50. More if any service genuinely needs volume to demo.)
- **Phase 5**: Should `shared.yml` use `lookup:` for the warehouse, or hardcode an ID per env? (Default: `lookup:` by name — portable across workspaces.)
- **Phase 7**: OIDC or client-secret for the initial CI? (Try OIDC first; fall back to client-secret + leave a TODO referencing the OIDC migration.)
- **Phase 8**: Do we want a public demo URL (anyone-can-view), or keep it Databricks-internal? (Default: internal — Databricks Apps default. Public would need additional auth wiring.)

---

*Last updated: 2026-06-08 — Phase 7.1 landed on `feat-one`. Workflows now run end-to-end against the dev workspace: M2M client-credentials auth replaces the OIDC stub, frontend builds run in CI via `scripts/build-frontends.sh`, `bundle deploy` is followed by per-app `bundle run` in parallel + `apps get` polling until `RUNNING`, smoke tests assert both status and body, project/app names lose their env suffixes, app→postgres permissions bump to `CAN_CONNECT_AND_CREATE`, and each `environment.url` / PR-comment URL is resolved from `databricks apps get` (canonical, workspace-ID-embedded). New helper `scripts/deploy-and-run-bundle.sh` wraps deploy+run as one verb. Logo + brand assets landed under `docs/brand/`; README + ARCHITECTURE updated to match. Phase 8 picks up test/prod live verification.*
