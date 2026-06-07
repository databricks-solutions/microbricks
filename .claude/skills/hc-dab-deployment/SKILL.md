---
name: hc-dab-deployment
description: Deploy services to dev/test/prod via Databricks Asset Bundles. Use when the user asks to "deploy", "promote", "deploy to dev/test/prod", "run bundle deploy", "validate the bundle", "add a resource to the bundle", "set a DAB variable", or anything about DAB targets, profiles, or app deployment. Codifies the per-service resource-include layout, the target → profile mapping, the app → Lakebase + app → app resource wiring, and the verbs to use at each step.
---

# hc-dab-deployment

DABs (Declarative Automation Bundles, formerly Databricks Asset Bundles) deploy every service + every job atomically against the target workspace. Lakebase **projects** are intentionally OUTSIDE the bundle (see below) — they must be provisioned first via `scripts/lakebase-project-up.sh`, then `databricks bundle deploy -t <target>` wires the apps to those projects.

## Deploy order (always)

1. **Provision Lakebase projects** for the target — once per `(service, env)` pair, idempotent:
   ```bash
   for svc in patient provider appointment lab prescription billing; do
     ./scripts/lakebase-project-up.sh "$svc" <env>
   done
   ```
   Skipping this step makes `bundle deploy` fail with `Postgres branch projects/<svc>-<env>/branches/production does not exist` — the bundle's app resources reference these projects by path string, so the projects must exist first.
2. **Validate** the bundle: `databricks bundle validate -t <target>`.
3. **Deploy + start** the apps: `scripts/deploy-and-run-bundle.sh <target>`. This wraps `bundle deploy` (which materializes the seven app *resources* but leaves them in `UNAVAILABLE`) with a `bundle run` per app key, which submits an app deployment from the synced source and starts the app. See "`bundle deploy` vs. `bundle run`" below.

For per-PR previews, replace step 1 with `scripts/lakebase-branch-up.sh` per service (creates the `feat-<slug>` branch on the existing project) and pass the matching `--var` overrides into the deploy-and-run script in step 3 — see "Per-PR preview deployment" below.

## `bundle deploy` vs. `bundle run`

`databricks bundle deploy` is two things stuck together:

1. Sync the source tree into the workspace (`/Workspace/.../source/...` under the bundle's `root_path`).
2. Materialize each declared resource — for an `app` resource that means *registering* the app with the Apps platform, attaching Lakebase + cross-app permissions, and plumbing env vars.

What it does **NOT** do is submit an app *deployment* — the platform unit that pulls the synced source path and actually starts running the app. So a fresh `bundle deploy` against a never-deployed workspace leaves every app in `UNAVAILABLE`.

`databricks bundle run -t <target> <app_key>` is the verb that flips them on. For an app resource it (a) submits a new app deployment from `source_code_path`, (b) starts/updates the running app, (c) blocks until ACTIVE (or fails). Run it once per app key after `bundle deploy` and the apps are live.

`scripts/deploy-and-run-bundle.sh` does both in deploy-order (services first, BFF last):

```bash
# Trunk-dev: deploy bundle, then start all 7 apps
scripts/deploy-and-run-bundle.sh dev

# Already deployed; just (re)launch every app
scripts/deploy-and-run-bundle.sh dev --skip-deploy --restart

# Iterate on one or two services
scripts/deploy-and-run-bundle.sh dev --only=patient,lab

# PR-preview shape (matches ci-local.sh pr-validate's overrides)
SLUG=$(./scripts/sanitize-branch-slug.sh "$(git branch --show-current)")
scripts/deploy-and-run-bundle.sh dev \
  --var "app_name_suffix=-feat-$SLUG" \
  --var "lakebase_branch=feat-$SLUG"
```

Pass-through flags: `--no-wait`, `--restart` (forwarded to `bundle run`); `--var KEY=VALUE` (forwarded to both `bundle deploy` and `bundle run`); `--skip-deploy` (skip step 1 if the bundle is already up-to-date); `--only=<svc,svc,...>` (restrict to a comma-separated subset of app keys). The script does NOT run Lakebase project provisioning, migrations, or smoke tests — for the full pipeline use `ci-local.sh deploy <env>`.

## When to use

- "Deploy all services to dev"
- "Promote to test" / "deploy to prod"
- "Add a new app/job/resource to the bundle"
- "Validate the bundle before pushing"
- "Set a DAB variable for catalog / Lakebase branch"
- "Wire app A so it can call app B"
- The user is editing `databricks.yml` or `resources/*.yml`

## When NOT to use

- The user is creating a Lakebase **branch** (per-feature) — that's `hc-lakebase-branching`. The bundle's `lakebase_branch` variable selects *which* branch each app's postgres resource binds to; creating the branch itself is out of band.
- The user is editing GitHub Actions workflows — that's `hc-gitflow-cicd`.

## Layout

```
databricks.yml                  ← root bundle, includes resources/*.yml
resources/
  patient.yml                   ← postgres_projects.<svc>_db + apps.<svc>_app (with resources block)
  provider.yml
  appointment.yml
  lab.yml
  prescription.yml
  billing.yml
  hc-portal.yml                 ← apps.hc_portal_app (with cross-app resources block)
  shared.yml                    ← shared variables, common labels
```

One file per service, plus `hc-portal.yml` for the frontend, plus `shared.yml` for cross-cutting bits.

## `databricks.yml` (the root)

```yaml
bundle:
  name: microbricks

include:
  - resources/*.yml

variables:
  catalog:
    description: "Unity Catalog the apps read from"
    default: "main"

  # Suffix appended to every app name. Empty for canonical dev/test/prod
  # deploys; `-feat-<slug>` for per-PR previews driven by pr-validate.yml.
  app_name_suffix:
    description: "Optional suffix on every app name. Empty for stable deploys; '-feat-<slug>' for previews."
    default: ""

  lakebase_branch:
    description: "Lakebase branch every <svc>_db postgres resource binds to. 'production' for test/prod; 'feat-<slug>' for per-feature-branch dev deploys."
    default: "production"

targets:
  dev:
    default: true
    mode: development
    workspace:
      profile: hc-dev
      # `mode: development` requires `${workspace.current_user.userName}` in
      # root_path. The suffix further isolates trunk-dev (no suffix) from
      # per-PR previews so concurrent deploys don't stomp each other's state.
      root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/${bundle.target}${var.app_name_suffix}
    variables:
      catalog: "hc_dev"

  test:
    mode: production
    workspace:
      profile: hc-test
      root_path: /Workspace/.bundle/${bundle.name}/${bundle.target}
    variables:
      catalog: "hc_test"

  prod:
    mode: production
    workspace:
      profile: hc-prod
      root_path: /Workspace/.bundle/${bundle.name}/${bundle.target}
    variables:
      catalog: "hc_prod"
```

`mode: development` automatically prefixes resource names with the deploying user's email so multiple devs can deploy to the same `hc-dev` workspace without colliding. `mode: production` skips that prefix and requires `workspace.root_path` to fix the deploy location.

`production` mode also rejects `bundle destroy` without `--force`, which is the right safety floor.

## `resources/<svc>.yml` shape (the canonical template)

Every service follows this shape. The only differences across the six service files are entity names — `auth.py`, `db.py`, and the bundle resource shapes are byte-identical otherwise.

> **Important: Lakebase projects (`postgres_projects`) are NOT in the bundle.** They live outside via `scripts/lakebase-project-{up,down}.sh`. Reason: putting the project in the bundle meant `bundle deploy`/`bundle destroy` tracked the SHARED project in its terraform state, and a per-PR preview deploy/destroy would attempt to delete the project that trunk-dev shares (see `dev-bundle-destroy-disaster` memory note). App resources reference projects by path string, which doesn't require bundle ownership.

```yaml
# NOTE: postgres_projects is NOT in this file by design — see above.
resources:
  apps:
    <svc>_app:
      name: <svc>-${bundle.target}${var.app_name_suffix}
      description: "<one-sentence ownership statement>"
      source_code_path: ../services/<svc>

      # OBO scope the user's forwarded token must carry. The service uses
      # that token to mint Lakebase credentials per request via
      # `WorkspaceClient(token=...).postgres.generate_database_credential(...)`,
      # which requires the `postgres` scope. `iam.*` scopes are platform
      # defaults and are NOT user-grantable.
      user_api_scopes:
        - "postgres"

      # Declaring the postgres app resource:
      #   1. Auto-injects PGHOST / PGUSER / PGDATABASE / PGPORT / PGSSLMODE /
      #      PGAPPNAME at runtime (Apps platform contract — see
      #      docs.databricks.com/aws/en/dev-tools/databricks-apps/lakebase).
      #   2. Creates a Postgres role for this app's service principal with
      #      CONNECT + CREATE on `databricks_postgres` so Alembic migrations
      #      can run.
      # `valueFrom: <svc>_db` in the app's app.yaml resolves to the full
      # endpoint path, used by db.py to mint per-connection OAuth tokens.
      resources:
        - name: <svc>_db
          description: "<svc> service Lakebase Autoscale project."
          postgres:
            branch: projects/<svc>-${bundle.target}/branches/${var.lakebase_branch}
            database: projects/<svc>-${bundle.target}/branches/${var.lakebase_branch}/databases/databricks_postgres
            permission: CAN_CONNECT_AND_CREATE
```

The bundle deploys the *project + production branch + primary endpoint* for the service's Lakebase database. Feature branches are out of band — `hc-lakebase-branching` creates them with the `databricks postgres` CLI directly, and `--var "lakebase_branch=feat-<slug>"` rebinds every app's postgres resource to that branch for the deploy.

### Why `database: .../databricks_postgres`

Every Lakebase Autoscale project ships with one default database named `databricks_postgres` and that's where our schema lives. The app resource needs the full path to that database, including the branch.

If you ever want to host multiple logical databases inside one project, you'd `databricks postgres create-database` them imperatively (no DAB resource type for that yet) and reference each one in a separate app resource entry.

## `resources/hc-portal.yml` shape

The BFF doesn't talk to a DB itself — only the six backend services do — but it needs (a) OBO scopes so it can forward the user's token and (b) a `CAN_USE` ACL on each backend app + the URL of each.

```yaml
resources:
  apps:
    hc_portal_app:
      name: hc-portal-${bundle.target}
      description: "Healthcare clinician portal — frontend + BFF."
      source_code_path: ../frontend/hc-portal

      # No `config.env` block by default — the BFF derives every downstream
      # URL at runtime from the platform-injected `DATABRICKS_APP_URL`
      # (see `frontend/hc-portal/src/hc_portal/clients/_base.py`). The
      # convention is `<svc>-<target>-<wsid>.<region>.databricksapps.com`
      # for every app in this workspace+target.
      #
      # Why not inject URLs from DAB: `${resources.apps.<key>.url}` does
      # NOT resolve at bundle-deploy time (`bundle validate -o json` shows
      # `url=null`), and `bundle deploy` does NOT push `config.env` to the
      # running App spec without an extra `apps update` round-trip.
      #
      # OVERRIDE: when a downstream lives somewhere non-canonical (PR
      # preview, local dev, alternate region), set `<SVC>_SVC_URL` here:
      #
      #   config:
      #     env:
      #       - name: PATIENT_SVC_URL
      #         value: "https://patient-pr-1234-<wsid>.<region>.databricksapps.com"
      #
      # The BFF's `_resolve_base_url` reads `<SVC>_SVC_URL` first, falls
      # back to runtime derivation. Same override can also live in
      # `frontend/hc-portal/app.yml` `env:`.

      # OBO scopes the BFF needs (the six backend services declare only
      # `postgres` for their own Lakebase access). `iam.*` scopes are platform
      # defaults and are NOT user-grantable.
      #   - sql       → portal can query Lakehouse warehouses (saved configs,
      #                 dashboards-style reads, cross-UC joins).
      #   - postgres  → forwarded token can be used by the BFF *and* by
      #                 downstream services to mint Lakebase credentials.
      user_api_scopes:
        - "sql"
        - "postgres"

      # CAN_USE on each backend app: (a) records the dependency so deploys
      # order correctly (services first, portal last); (b) grants the BFF's
      # service principal the platform ACL Apps uses to gate cross-app
      # traffic. The actual URL goes through `config.env` above — the app
      # resource block here is for ACL/wiring, not URL exposure.
      resources:
        - name: patient_app
          description: "Patient service backend."
          app:
            name: ${resources.apps.patient_app.name}
            permission: CAN_USE
        - name: provider_app
          description: "Provider service backend."
          app:
            name: ${resources.apps.provider_app.name}
            permission: CAN_USE
        - name: appointment_app
          app:
            name: ${resources.apps.appointment_app.name}
            permission: CAN_USE
        - name: lab_app
          app:
            name: ${resources.apps.lab_app.name}
            permission: CAN_USE
        - name: prescription_app
          app:
            name: ${resources.apps.prescription_app.name}
            permission: CAN_USE
        - name: billing_app
          app:
            name: ${resources.apps.billing_app.name}
            permission: CAN_USE
```

## How the per-app `app.yaml` looks

`app.yaml` is the runtime config — read by the Apps platform when the app starts. It has NO bundle interpolation. Anything that needs DAB-time substitution (`${resources.apps.X.url}` and friends) must go in the bundle's `app.config.env` block instead, where it overrides `app.yaml`.

For the six services, `app.yaml` is minimal because the Lakebase resource auto-injects PG*:

```yaml
# services/<svc>/app.yaml
command:
  - "python"
  - "-m"
  - "uvicorn"
  - "<svc>.app:app"
  - "--host"
  - "0.0.0.0"
  - "--port"
  - "8000"

env:
  - name: SERVICE_NAME
    value: "<svc>"

  # PG* env vars (PGHOST/PGUSER/PGDATABASE/PGPORT/PGSSLMODE/PGAPPNAME) are
  # auto-injected by the Apps platform once the `<svc>_db` postgres resource
  # is declared in resources/<svc>.yml.
  #
  # ENDPOINT_NAME is the Lakebase endpoint path used by db.py to mint
  # per-connection OAuth credentials. `valueFrom: <svc>_db` resolves the
  # postgres resource to its endpoint path automatically.
  - name: ENDPOINT_NAME
    valueFrom: "<svc>_db"
```

For the BFF, `app.yml` is even simpler — all cross-app URLs are resolved at runtime from `DATABRICKS_APP_URL`:

```yaml
# frontend/hc-portal/app.yml
command:
  - "uvicorn"
  - "hc_portal.backend.app:app"
  - "--workers"
  - "2"

env:
  - name: SERVICE_NAME
    value: "hc-portal"

# Per-service URLs are resolved at runtime by `clients/_base.py`:
#   1. Explicit override `<SVC>_SVC_URL` (e.g. `PATIENT_SVC_URL`) if set.
#   2. Otherwise, derived from `DATABRICKS_APP_URL` + the canonical
#      `<svc>-<target>-<workspace_suffix>` host pattern.
# Add `<SVC>_SVC_URL` entries above when the canonical pattern doesn't
# fit (local dev, PR preview, cross-region fan-out).
```

### Why `valueFrom` looks the way it does

Per the Apps platform, `valueFrom: <key>` resolves the resource named `<key>` to a single string. The mapping is:

| Resource type             | Resolves to              |
|---------------------------|--------------------------|
| Lakebase Autoscale postgres | Endpoint path            |
| Databricks app            | App name                 |
| SQL warehouse             | Warehouse ID             |
| Secret                    | Decrypted secret value   |
| Model serving endpoint    | Endpoint name            |

For the `app` resource, `valueFrom` returns the **app name**, NOT the URL. That's why we put the cross-app URLs in `config.env` with `${resources.apps.<key>.url}` substitution.

For the `postgres` resource, `valueFrom` returns the **endpoint path**, which is what `db.py` needs as `ENDPOINT_NAME`. PG* env vars come for free as auto-injected platform vars.

## Target → profile mapping

| Target | Profile | When to deploy |
|---|---|---|
| `dev` | `hc-dev` | Local validation, push to `develop` |
| `test` | `hc-test` | Push to `release/*`, merge to `main` |
| `prod` | `hc-prod` | Tagged release `v*` (manual approval gate) |

Profiles in `~/.databrickscfg`:

```ini
[hc-dev]
host = https://<dev-workspace>.cloud.databricks.com
auth_type = databricks-cli

[hc-test]
host = https://<test-workspace>.cloud.databricks.com
auth_type = databricks-cli

[hc-prod]
host = https://<prod-workspace>.cloud.databricks.com
auth_type = databricks-cli
```

## CLI verbs

```bash
# 0. Provision Lakebase projects FIRST (idempotent — no-op if they exist).
#    The bundle's app resources reference these by path; if missing, the
#    deploy fails with "Postgres branch projects/<svc>-<env>/branches/production
#    does not exist".
for svc in patient provider appointment lab prescription billing; do
  ./scripts/lakebase-project-up.sh "$svc" dev
done

# Always validate next — catches schema errors and unresolved references
databricks bundle validate -t dev

# Canonical deploy: register resources AND start every app.
# Wrapper around `bundle deploy` + `bundle run <app_key>` for each of the
# seven apps. Without the `bundle run` step every app stays in UNAVAILABLE.
scripts/deploy-and-run-bundle.sh dev

# Lower-level pieces if you need them — for diffing what's wired vs.
# what's actually running, or for app-only re-deploys:
databricks bundle deploy -t dev                # register resources only
databricks bundle run    -t dev <app_key>      # start a single app
databricks bundle sync   -t dev                # source-only sync (no resource changes)

# See what's deployed
databricks bundle summary -t dev

# Inspect the materialized bundle (resource blocks fully resolved)
databricks bundle validate -t dev -o json | jq .

# Tear down (CAREFUL — deletes apps and databases)
databricks bundle destroy -t dev
```

`databricks bundle destroy -t prod` is **never** a good idea. Workflows enforce `-t dev` and `-t test` only.

## Variables and overrides

```bash
# Override a variable at deploy time
scripts/deploy-and-run-bundle.sh test --var "catalog=hc_test_canary"

# Per-feature-branch dev deploy: bind every app to your Lakebase branch
# AND name them with a -feat-<slug> suffix so they don't collide with trunk-dev.
SLUG=$(./scripts/sanitize-branch-slug.sh "$(git branch --show-current)")
scripts/deploy-and-run-bundle.sh dev \
  --var "app_name_suffix=-feat-$SLUG" \
  --var "lakebase_branch=feat-$SLUG"
```

`--var KEY=VALUE` is forwarded to both `bundle deploy` and `bundle run` underneath. The branch must already exist (`hc-lakebase-branching` covers creation). The bundle's `lakebase_branch` default is `"production"`, which is the only valid choice for `test` and `prod`.

## What to do before deploying

| Step | Why |
|---|---|
| Run `scripts/lakebase-project-up.sh <svc> <env>` for all six services | The bundle's `apps.<svc>_app.resources[].postgres` blocks reference `projects/<svc>-<env>/branches/<branch>` by path string. If the project doesn't exist, deploy fails with `Postgres branch ... does not exist`. The script is idempotent — safe to re-run on every deploy. |
| `databricks bundle validate -t <target>` | Catches schema errors, unresolved refs, missing files. Validation does NOT check that referenced Lakebase projects exist — that fails at apply time. |
| Run service tests locally | Bundle deploy doesn't run tests — that's CI's job, but smoke locally first |
| For dev with `lakebase_branch=feat-...`: confirm the branch exists | Otherwise the postgres resource declaration fails at deploy time |
| For test/prod: confirm migration plan | Bundle deploy doesn't auto-run Alembic; the deploy workflow runs `alembic upgrade head` first |
| Use `scripts/deploy-and-run-bundle.sh <env>` rather than raw `bundle deploy` | `bundle deploy` alone leaves apps in `UNAVAILABLE` (see "`bundle deploy` vs. `bundle run`" above) |
| For prod: have a rollback plan | DAB has no built-in rollback — the rollback is "redeploy the previous tag" |

## Path-resolution rules (gotchas)

- From `databricks.yml` (the root), use paths like `./services/...`.
- From `resources/<file>.yml`, use paths like `../services/...` (working dir for resource path resolution is the resource file's parent, which is `resources/`).

Most common DAB validation error. If `bundle validate` complains about "path not found", swap `./` and `../`.

## Per-PR preview deployment (the trick)

A PR can deploy ephemeral preview apps wired to feature-branch endpoints by overriding `app_name_suffix` and `lakebase_branch` together:

```bash
SLUG=$(./scripts/sanitize-branch-slug.sh "$GITHUB_HEAD_REF")
scripts/deploy-and-run-bundle.sh dev \
  --var "app_name_suffix=-feat-$SLUG" \
  --var "lakebase_branch=feat-$SLUG"
```

What each override does:

- `app_name_suffix=-feat-<slug>` — gets concatenated into every `apps.<svc>.name` (e.g. `patient-dev-feat-hc-123`) AND into the dev target's `root_path`. The first isolates the running app from `patient-dev`; the second isolates the bundle deploy state so a `bundle destroy` of the preview doesn't touch the trunk-dev deploy.
- `lakebase_branch=feat-<slug>` — rebinds every postgres resource (`branch:` + `database:` lines under `apps.<svc>.resources[].postgres`) to the per-feature Lakebase branch. The branch must already exist; `pr-validate.yml` provisions all six (one per service) before deploying so the bundle never references a missing branch.

The PR's `pr-validate.yml` workflow drives this for you. `pr-cleanup.yml` runs the matching `bundle destroy -t dev --var "app_name_suffix=-feat-$SLUG" --var "lakebase_branch=feat-$SLUG"` on PR close (merged or not).

## Verification

```bash
# After a deploy-and-run:
databricks bundle summary -t dev | grep -E "apps|Postgres" | head
databricks apps list -p hc-dev | grep "<svc>-dev"
databricks postgres list-projects -p hc-dev | grep "<svc>-dev"

# Confirm each app is actually serving (not just registered).
# `compute_status.state` should be RUNNING and `app_status.state` should be
# RUNNING; if either is UNAVAILABLE the bundle was deployed but the app
# was never `bundle run`. Re-run scripts/deploy-and-run-bundle.sh dev --skip-deploy.
databricks apps get patient-dev -p hc-dev -o json \
  | jq '{compute: .compute_status.state, app: .app_status.state, url}'

# Inspect the wired resources for one app
databricks apps get patient-dev -p hc-dev -o json | jq '.resources, .user_api_scopes'

# Smoke the deployed app
curl -s https://<svc>-dev.<workspace>.databricksapps.com/api/v1/healthz | jq
```

## Checklist before merging changes to `databricks.yml` / `resources/`

- [ ] All six Lakebase projects for the target env exist (`databricks postgres list-projects -p hc-<env> | grep -E '^(patient|provider|appointment|lab|prescription|billing)-<env>'` returns six rows). If not, run `scripts/lakebase-project-up.sh` for each missing one.
- [ ] `databricks bundle validate -t dev` passes locally
- [ ] `databricks bundle validate -t test` passes locally
- [ ] `databricks bundle validate -t prod` passes locally
- [ ] No hardcoded workspace URLs or catalog names — all via `${bundle.target}` or variables
- [ ] No new resources added without a corresponding CODEOWNERS entry
- [ ] Every app that talks to a Lakebase project declares the postgres resource (NOT just the postgres_projects block)
- [ ] Every app that calls another app declares it as an `app` resource with `CAN_USE` AND has a `config.env` line with `${resources.apps.<key>.url}` for the URL
- [ ] BFF (`hc-portal`) declares `user_api_scopes: [sql, postgres]`; each backend service declares `user_api_scopes: [postgres]`. The forwarded token must already carry `postgres` so each service can mint Lakebase creds from it.
- [ ] If you bumped `autoscaling_limit_max_cu`, you've justified it in the PR description
