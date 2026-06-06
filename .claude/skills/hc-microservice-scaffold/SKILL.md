---
name: hc-microservice-scaffold
description: Scaffold a new backend microservice in this healthcare reference architecture. Use when the user asks to "add a new service", "scaffold X service", "create a new microservice for Y", "bootstrap a new service", or "add a service called <name>". Wires APX project, app.yaml, Lakebase project, DAB resource block, BFF client stub, tests, CODEOWNERS, and migrations directory consistent with the rest of the monorepo.
---

# hc-microservice-scaffold

Adds a new backend microservice to the monorepo following every convention in [`ARCHITECTURE.md`](../../../ARCHITECTURE.md) and [`CONTRIBUTING.md`](../../../CONTRIBUTING.md). Use this skill instead of running `apx init` ad hoc — it guarantees the service is wired into Lakebase, DAB, the BFF, CODEOWNERS, and CI consistently.

## When to use

- "Add a service called `referral`" / "scaffold a `notification` service".
- The user is starting a new bounded context that needs its own DB.
- The user references a service that doesn't exist yet under `services/`.

## When NOT to use

- The user wants to add a *route* to an existing service → use `hc-obo-auth`.
- The user wants to add a *cross-service aggregation* → use `hc-bff-pattern`.
- The user wants a *one-off script* → make a directory under `scripts/`, not a service.

## Inputs you must collect from the user before scaffolding

| Input | Example | Validation |
|---|---|---|
| Service name | `referral` | lowercase, kebab-case, ≤20 chars, doesn't already exist under `services/` |
| Owns (1-sentence) | "Specialist referral requests and their statuses" | one sentence, used in README and DAB description |
| Owner team / GitHub group | `@erinaldidb` or `@hc-referrals` | added to CODEOWNERS |
| Cross-service IDs it stores | `patient_id`, `provider_id` | UUID columns only, no FKs |
| Initial entities | `referral`, `referral_status_history` | will become first Alembic migration |

If the user is vague, **ask clarifying questions** before generating files.

## Workflow

### 1. Validate

```bash
test -d services/<name> && echo "ERROR: services/<name> already exists" && exit 1
```

Reject `name` if it collides with `patient`, `provider`, `appointment`, `lab`, `prescription`, `billing`, `bff`, `infra`, `frontend`.

### 2. Generate the APX project

```bash
cd services/
uv run --with apx apx init <name> \
  --addons=lakebase \
  --description "<one-sentence ownership statement>"
```

After init, immediately:

- Set `pyproject.toml` `[project] name = "<name>-svc"`.
- Add a `[tool.uv]` block with `package = false` so `uv sync` installs deps without trying to build the local source as a wheel (the runtime imports the package from `src/` via `PYTHONPATH=src`).
- Run `uv lock` inside `services/<name>/` — this produces `services/<name>/uv.lock`, the file Databricks Apps uses at deploy. Commit `pyproject.toml` + `uv.lock` together. Do **not** add the service to any `[tool.uv.workspace] members` block at root: each service is a standalone uv project.
- Do **not** create or check in a `services/<name>/requirements.txt` — Apps prefers `requirements.txt` over `uv.lock` when both exist, which would silently bypass the lockfile.
- Replace the default `app.py` boilerplate with the OBO-correct shape from [`hc-obo-auth/references/canonical-patterns.md`](../hc-obo-auth/references/canonical-patterns.md).

### 3. Create `services/<name>/app.yaml`

Use this shape verbatim — it's the contract every service must satisfy. Replace `<name>`.

```yaml
command:
  - "python"
  - "-m"
  - "uvicorn"
  - "<name>.app:app"
  - "--host"
  - "0.0.0.0"
  - "--port"
  - "8000"

env:
  - name: SERVICE_NAME
    value: "<name>"

  # PG* env vars (PGHOST/PGUSER/PGDATABASE/PGPORT/PGSSLMODE/PGAPPNAME) are
  # auto-injected by the Apps platform once the `<name>_db` postgres resource
  # is declared in resources/<name>.yml. Don't shadow them here.
  #
  # ENDPOINT_NAME is the Lakebase endpoint path used by db.py to mint
  # per-connection OAuth credentials. `valueFrom: <name>_db` resolves the
  # postgres app resource (named in resources/<name>.yml) to its endpoint path.
  - name: ENDPOINT_NAME
    valueFrom: "<name>_db"
```

`app.yaml` is read by the Apps runtime, NOT the bundle — DAB substitutions like `${bundle.target}` are NOT available here. The Lakebase branch (production for test/prod, `feat-<slug>` for per-feature dev) is bound by the bundle when it materializes the postgres resource block, and the resulting endpoint path comes through `valueFrom: <name>_db` automatically.

### 4. Lakebase: create the project in the dev workspace

Run **once** when the service is first scaffolded — not per feature branch:

```bash
databricks postgres create-project <name>-dev -p hc-dev
databricks postgres create-project <name>-test -p hc-test
databricks postgres create-project <name>-prod -p hc-prod
```

This creates a `production` branch + a `primary` read-write endpoint in each. Ask the user before running the test/prod commands — they cost money and need workspace permissions.

### 5. DAB: add `resources/<name>.yml`

The bundle declares both the Lakebase project AND the app, including OBO scopes and the postgres app resource that auto-injects PG* env vars. See `hc-dab-deployment` for the full template; this is the canonical service shape:

```yaml
resources:
  postgres_projects:
    <name>_db:
      project_id: <name>-${bundle.target}
      pg_version: 17
      default_endpoint_settings:
        autoscaling_limit_min_cu: 0.5
        autoscaling_limit_max_cu: 4.0

  apps:
    <name>_app:
      name: <name>-${bundle.target}
      description: "<one-sentence ownership statement>"
      source_code_path: ../services/<name>

      # OBO scope the forwarded user token must carry. The service mints
      # Lakebase credentials from that token via the postgres app resource
      # below; that mint requires the `postgres` scope. The BFF's scopes
      # (`sql, postgres`) are a superset — see hc-dab-deployment.
      user_api_scopes:
        - "postgres"

      resources:
        - name: <name>_db
          description: "<name> service Lakebase Autoscale project."
          postgres:
            branch: projects/<name>-${bundle.target}/branches/${var.lakebase_branch}
            database: projects/<name>-${bundle.target}/branches/${var.lakebase_branch}/databases/databricks_postgres
            permission: CAN_CONNECT_AND_CREATE
```

Verify the include glob in the root `databricks.yml` covers `resources/*.yml` (it does — no edit needed).

Then update `resources/hc-portal.yml` so the BFF can call your new service: add a `<name>_app` entry under `apps.hc_portal_app.resources` with `permission: CAN_USE`, and a `<NAME>_SVC_URL` entry under `apps.hc_portal_app.config.env` set to `${resources.apps.<name>_app.url}`.

### 6. Migrations

```bash
cd services/<name>
uv run alembic init migrations
```

Edit `migrations/env.py` to read `PGHOST`/`PGDATABASE`/etc. from env (canonical pattern in [`hc-obo-auth`](../hc-obo-auth/SKILL.md)).

Generate the first migration covering the entities the user named:

```bash
uv run alembic revision -m "initial <name> schema"
# then hand-write the upgrade() / downgrade() with the entities discussed in step 0
```

Schema rules from [`HEALTHCARE_DATA_MODEL.md`](../../../HEALTHCARE_DATA_MODEL.md):

- UUID PK on every table (`id UUID PRIMARY KEY DEFAULT gen_random_uuid()`).
- Audit columns on every table (`created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `created_by TEXT NOT NULL`, `updated_at`, `updated_by`, `deleted_at TIMESTAMPTZ NULL`).
- No FKs to tables in other databases.
- `CHECK` constraints for any enum-like columns.

### 7. Wire the BFF client stub

Create `frontend/hc-portal/src/hc_portal/clients/<name>.py`:

```python
"""Typed client for <name>-svc. Generated stub — extend after first route exists."""
import os
import httpx
from typing import Any

class <Name>Client:
    def __init__(self, user_token: str):
        self._client = httpx.AsyncClient(
            base_url=os.environ["<NAME>_SVC_URL"],
            headers={
                "Authorization": f"Bearer {user_token}",
                "X-Forwarded-Access-Token": user_token,
            },
            timeout=httpx.Timeout(connect=2.0, read=5.0, write=5.0, pool=5.0),
        )

    async def aclose(self) -> None:
        await self._client.aclose()
```

The `<NAME>_SVC_URL` env var is set by the bundle in `resources/hc-portal.yml`'s `apps.hc_portal_app.config.env` block (NOT in `frontend/hc-portal/app.yml` — that file can't see DAB substitutions). See step 5 above.

Register the client in `frontend/hc-portal/src/hc_portal/clients/__init__.py`.

### 8. Tests scaffolding

```
services/<name>/tests/
├── __init__.py
├── conftest.py        # spins up a TEST DB connection from env
├── unit/
│   └── test_models.py
└── integration/
    └── test_routes.py # pytest marks: @pytest.mark.integration
```

`conftest.py` uses the same `OAuthConnection` pattern as the runtime, but the test fixture connects to whichever endpoint `ENDPOINT_NAME` is set to (in CI: the feature-branch endpoint; locally: the dev's feature endpoint).

### 9. CODEOWNERS

Append to root `CODEOWNERS`:

```
/services/<name>/                <github-handle-or-team>
/resources/<name>.yml            <github-handle-or-team>
```

### 10. README per service

`services/<name>/README.md`:

```markdown
# <name>-svc

<one-sentence ownership statement>

Owns: <entities>
References: <cross-service IDs, if any>
Lakebase project: `projects/<name>-{dev,test,prod}`

See:
- [Architecture](../../ARCHITECTURE.md)
- [Data model](../../HEALTHCARE_DATA_MODEL.md#<name>)
- [Contributing](../../CONTRIBUTING.md)
```

## Verification checklist

After scaffolding, confirm:

- [ ] `services/<name>/` exists with `pyproject.toml`, `uv.lock`, `app.yaml`, `src/<name>/`, `migrations/`, `tests/`, `README.md` — and **no** `requirements.txt`.
- [ ] `services/<name>/pyproject.toml` includes `[tool.uv]` with `package = false`, and the service is **not** listed in any root `[tool.uv.workspace] members` block (the root project intentionally has none).
- [ ] `resources/<name>.yml` exists and references `<name>-${bundle.target}`.
- [ ] `databricks bundle validate -t dev` succeeds.
- [ ] `frontend/hc-portal/src/hc_portal/clients/<name>.py` exists and is importable.
- [ ] `CODEOWNERS` has an entry for the new service.
- [ ] `apx dev start` in `services/<name>/` boots without import errors (it'll fail to connect to Lakebase until step 4 runs — that's fine, document it).

## What this skill does NOT do

- It does **not** run the `databricks postgres create-project` commands without explicit confirmation — those cost money.
- It does **not** deploy via DAB. Use `hc-dab-deployment` after scaffolding.
- It does **not** create Lakebase feature branches — that's `hc-lakebase-branching`.
