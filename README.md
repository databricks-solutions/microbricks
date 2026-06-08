

# microbricks

A reference architecture demonstrating how to build **microservices on Databricks** using **Databricks Apps** for the runtime, **Lakebase Autoscale Postgres** for per-service state, **OBO authentication** for end-to-end user identity, and **DABs + GitHub Actions** for CI/CD across dev/test/prod.

The demo domain is healthcare: six backend services that loosely follow HL7 FHIR resource boundaries, plus one frontend portal with an in-process BFF.

> **Status:** Phases 1–7 complete — six backend services + the BFF + the DAB bundle + six GitHub Actions workflows are all in place; dev is end-to-end runnable via `scripts/ci-local.sh`. The remaining work (Phase 8) is unblocking GH-hosted runners against the dev workspace's IP allowlist, then a clone-to-demo polish pass. See `[ROADMAP.md](ROADMAP.md)` for the full phase breakdown and [open work](#open-work) for what's next.

---

## At a glance

```
Browser  →  hc-portal (frontend + BFF)  →  6 backend services  →  6 Lakebase databases
            └── joins in-memory             └── one DB per service, no shared schema
            └── forwards OBO token
```

- **6 backend services** (`patient`, `provider`, `appointment`, `lab`, `prescription`, `billing`), each its own Databricks App with its own Lakebase project.
- **1 frontend** (`hc-portal`) — a [BFF](https://samnewman.io/patterns/architectural/bff/) that orchestrates calls and joins data in-memory. Holds no data of its own.
- **OBO auth** end-to-end. Every Postgres connection is opened with the calling user's OAuth credential, so Unity Catalog enforces access at the data layer.
- **No backend-to-backend calls.** The BFF is the only place where data from multiple services is joined.

Detailed architecture: `[ARCHITECTURE.md](ARCHITECTURE.md)`. Data model: `[HEALTHCARE_DATA_MODEL.md](HEALTHCARE_DATA_MODEL.md)`. Implementation plan: `[ROADMAP.md](ROADMAP.md)`.

---

## Prerequisites


| Tool              | Min version | Install                                                                                                                    |
| ----------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------- |
| Databricks CLI    | `0.295.0`   | `brew install databricks`                                                                                                  |
| `apx`             | latest      | `curl -fsSL [https://databricks-solutions.github.io/apx/install.sh](https://databricks-solutions.github.io/apx/install.sh) |
| `uv`              | latest      | `curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh)                                             |
| `bun`             | latest      | `curl -fsSL [https://bun.sh/install](https://bun.sh/install)                                                               |
| `gh`              | latest      | `brew install gh`                                                                                                          |
| `psql` (optional) | 16          | `brew install postgresql@16`                                                                                               |


Three Databricks workspaces (FE-VM serverless type, required for Lakebase + Apps):


| Profile   | Workspace          | Used for                                                                    |
| --------- | ------------------ | --------------------------------------------------------------------------- |
| `hc-dev`  | dev workspace URL  | `develop` branch + per-feature-branch preview environments (local dev + PR) |
| `hc-test` | test workspace URL | `release/*` branches and `main` HEAD                                        |
| `hc-prod` | prod workspace URL | tagged releases (`v*`)                                                      |


Configure them in `~/.databrickscfg`:

```bash
databricks auth login --host https://<dev-workspace>.cloud.databricks.com --profile hc-dev
databricks auth login --host https://<test-workspace>.cloud.databricks.com --profile hc-test
databricks auth login --host https://<prod-workspace>.cloud.databricks.com --profile hc-prod
```

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/erinaldidb/microbricks.git
cd microbricks

# 2. Validate the bundle (no Databricks calls, just YAML + schema checks)
databricks bundle validate -t dev

# 3. Bootstrap dev: lint + tests + provision 6 Lakebase projects + alembic +
#    `bundle deploy -t dev`. ci-local.sh wraps every step the GitHub Actions
#    `deploy-dev.yml` workflow runs in CI.
./scripts/ci-local.sh deploy dev

# 4. Seed synthetic patient/provider/appointment/lab/prescription/billing
#    data into the freshly-provisioned production branches.
make seed-dev
```

The seven dev apps (`patient-dev` … `billing-dev`, `hc-portal-dev`) come up STOPPED and scale-to-zero after 1h idle. Hitting any of their URLs warms them.

For the per-PR / per-feature-branch workflow:

```bash
# Day-to-day fast loop: lint + tests + bundle-validate, no deploy.
./scripts/ci-local.sh pr-validate --no-deploy

# Full preview deploy: provision 6 feature branches off `production`, alembic
# on changed services, deploy 7 preview apps suffixed `-<slug>`, smoke-test.
./scripts/ci-local.sh pr-validate

# Tear it all down when you're done iterating.
./scripts/ci-local.sh pr-cleanup
```

See `CONTRIBUTING.md` "Running CI locally" for the full reference. Every step can also be driven by Claude Code — open the repo in Claude Code and the project-local skills (`.claude/skills/`) are auto-discovered.

---

## Repository layout

```
.
├── README.md                       # This file
├── ARCHITECTURE.md                 # Architecture reference
├── HEALTHCARE_DATA_MODEL.md        # Per-service data model
├── CONTRIBUTING.md                 # GitFlow + PR rules + "Running CI locally"
├── ROADMAP.md                      # Phased implementation plan (all phases ✅ except 8)
├── Makefile                        # `make seed-dev` and per-service seed targets
├── databricks.yml                  # Root DAB (3 targets: dev / test / prod)
├── resources/                      # DAB resource includes (apps + BFF + shared)
├── services/                       # 6 backend microservices (one APX project each)
│   ├── patient/                    # ✅ all six scaffolded; auth.py / db.py / migrations
│   ├── provider/                   #     are byte-identical except for entity names
│   ├── appointment/
│   ├── lab/
│   ├── prescription/
│   └── billing/
├── frontend/
│   └── hc-portal/                  # ✅ React UI + BFF; aggregates patient summary
│                                   #     across all six services with concurrent fan-out
├── scripts/
│   ├── ci-local.sh                 # Local CI emulator — pr-validate / pr-cleanup /
│   │                               #     deploy {dev,test,prod} / nightly-cleanup
│   ├── sanitize-branch-slug.sh     # Code-branch -> Lakebase-/preview-slug transform
│   ├── lakebase-project-{up,down}.sh   # Per-env Lakebase project lifecycle
│   ├── lakebase-branch-{up,down}.sh    # Per-feature-branch lifecycle
│   └── seeds/                      # Shared seed primitives (deterministic UUIDs)
├── tests/seeds/                    # Cross-service ID-stability tests (no DB needed)
├── docs/diagrams/                  # *.drawio + exported *.png
├── .github/
│   ├── workflows/                  # 6 workflows: pr-validate, pr-cleanup,
│   │                               # deploy-{dev,test,prod}, nightly-orphan-cleanup
│   └── release-template.md         # PR template for release/* -> main PRs
└── .claude/                        # Project-local Claude Code skills (auto-discovered)
    └── skills/
        ├── hc-microservice-scaffold/
        ├── hc-lakebase-branching/
        ├── hc-obo-auth/
        ├── hc-dab-deployment/
        ├── hc-bff-pattern/
        └── hc-gitflow-cicd/
```

---

## Working with this repo via Claude Code

The repo ships six project-local skills under `.claude/skills/`. Each one codifies a piece of the reference architecture so that future contributors (and Claude Code itself) follow the same patterns.


| Ask Claude Code…                                            | Skill that fires           |
| ----------------------------------------------------------- | -------------------------- |
| "Scaffold a new service called X"                           | `hc-microservice-scaffold` |
| "Spin up a Lakebase branch for my feature" / "tear it down" | `hc-lakebase-branching`    |
| "Add a new route to the patient service"                    | `hc-obo-auth`              |
| "Deploy to test"                                            | `hc-dab-deployment`        |
| "Add a BFF endpoint that joins patient + appointment"       | `hc-bff-pattern`           |
| "Cut a release / open a PR"                                 | `hc-gitflow-cicd`          |


---

## CI/CD

The repo ships six workflows under `.github/workflows/`:


| Workflow                     | Trigger                                           | What it does                                                                                                                                                                                 |
| ---------------------------- | ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pr-validate.yml`            | PR open/sync against `develop`/`release/*`/`main` | Path-scoped matrix: lint + unit tests for changed services, BFF tests, bundle-validate, provision per-feature Lakebase branches, alembic, deploy preview apps, smoke, comment URLs on the PR |
| `pr-cleanup.yml`             | PR close (merged or not)                          | `bundle destroy` of the preview + tear down 6 Lakebase feature branches                                                                                                                      |
| `deploy-dev.yml`             | Push to `develop`                                 | `bundle deploy -t dev`, alembic against `production` branches, smoke 7 apps                                                                                                                  |
| `deploy-test.yml`            | Push to `release/*` or `main`                     | Same shape, `-t test`                                                                                                                                                                        |
| `deploy-prod.yml`            | Push tag `v*` on `main`                           | Same shape, `-t prod`, gated by manual approval on the `prod` GitHub environment                                                                                                             |
| `nightly-orphan-cleanup.yml` | Daily cron (04:17 UTC) + manual                   | GC Lakebase feature branches whose PR is closed                                                                                                                                              |


Auth is service-principal client-secret M2M, scoped to a per-environment GitHub secret (`secrets.DATABRICKS_CLIENT_{ID,SECRET}` resolves differently in `dev` / `test` / `prod` environments). OIDC migration path is documented inline in `pr-validate.yml`.

> **Note:** the workflows currently can't reach the dev workspace from GH-hosted runners — FE-VM provisions a managed IP allowlist that doesn't include GitHub egress. Until Phase 8 picks an unblock (self-hosted runner inside FE-VM, parallel allowlist for GitHub IPs, or a dedicated CI workspace), `scripts/ci-local.sh` runs the same logical pipelines from a developer's machine where the IP is already allowlisted. See `CONTRIBUTING.md` "Running CI locally" for the dev/CI division of labor.

---

## Open work

The phased plan in `[ROADMAP.md](ROADMAP.md)` is mostly done — phases 1-7 (six services + BFF + seed data + DAB bundle + dev rollout + workflows) are ✅. Phase 8 wraps it up:

- **Unblock CI ↔ Databricks** — pick one of the three options in the `github-runner-ip-acl` finding so the workflows actually fire against the workspace.
- **Fresh-clone test** — verify a stranger can go from `git clone` to a working PR with a preview app in under 30 minutes following only README + CONTRIBUTING.
- **Runbooks** — `docs/runbooks/{prod-rollback,hotfix,lakebase-branch-orphan}.md`.
- **Cost audit** — confirm idle endpoints scale to zero (already wired: 1h `suspend_timeout_duration` in `scripts/lakebase-project-up.sh` + `scripts/lakebase-branch-up.sh`); document expected dev-env monthly cost.

Future / optional follow-ups (Phases 9–14 in `ROADMAP.md`): service-mesh observability, saga/events demo, RLS demo, read-replica for prod, multi-region, shared APX UI library.

---

## License

MIT. This is a reference architecture — **HIPAA compliance is your responsibility**, the data model is illustrative and the synthetic data is intentionally non-realistic. 