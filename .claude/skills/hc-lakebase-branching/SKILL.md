---
name: hc-lakebase-branching
description: Manage Lakebase database branches that mirror code branches. Use when the user asks to "create a Lakebase branch", "spin up a feature DB", "branch the database for this feature", "tear down feature branch", "list active branches", or anything about Lakebase branch lifecycle. Implements the per-feature-branch model where each code branch has a matching Lakebase branch used for both local dev and PR CI.
---

# hc-lakebase-branching

The branching model is **one Lakebase branch per code branch**, used for both local development AND PR-time integration tests. Same branch from feature start to PR close.

## When to use

- "Create a feature branch for HC-123" / "spin up a DB for this feature".
- "Tear down my Lakebase branch" / "clean up feat-hc-123".
- "List active feature branches" / "what's running in dev".
- The user is starting work on a feature touching schema or data.
- The user needs the `ENDPOINT_NAME` to put in their local `.env`.

## When NOT to use

- The user wants a permanent branch (`production`, `staging`) → that's a one-time `databricks postgres create-project` operation, see `hc-microservice-scaffold` step 4.
- The user wants to *promote* a branch's data to prod → that's not how this works; promote schema migrations via `deploy-test.yml` / `deploy-prod.yml`.

## Concepts (read once)

```
Project (per service, per env)
  e.g. projects/patient-dev
  └── Branch
        e.g. projects/patient-dev/branches/production       ← long-lived, source of truth
        e.g. projects/patient-dev/branches/feat-hc-123-...  ← per code branch, ephemeral
        └── Endpoint
              e.g. .../endpoints/primary  ← compute, has the host you connect to
```

- A **branch** is a copy-on-write copy of another branch's data.
- An **endpoint** is the compute that accepts Postgres connections. A branch with no endpoint is just storage.
- Branches *not* created with `no_expiry: true` are auto-deleted by the platform after ~24h of inactivity. We rely on this as the safety net for orphans.

## Branch naming rules

The Lakebase branch name is derived from the code branch via this exact transformation:

| Code branch | Lakebase branch |
|---|---|
| `feature/HC-123-add-allergies` | `feat-hc-123-add-allergies` |
| `feature/HC-99-fix-bug` | `feat-hc-99-fix-bug` |
| `hotfix/HC-456-rounding` | `hotfix-hc-456-rounding` |
| `release/v0.4.0` | (don't branch — release branches deploy to test, not dev previews) |

Algorithm (also lives in `scripts/sanitize-branch-slug.sh`):

```bash
echo "$CODE_BRANCH" \
  | tr '[:upper:]' '[:lower:]' \
  | sed -E 's|^feature/|feat-|; s|^hotfix/|hotfix-|' \
  | sed -E 's|[/_]+|-|g; s|[^a-z0-9-]||g; s|^-+||; s|-+$||' \
  | cut -c1-50
```

50-char cap because Lakebase resource IDs are 3-63 chars and we need room for the `feat-` prefix and any project name.

## Workflows

### Create a feature branch (called from the dev's machine, idempotent)

For each service the feature touches:

```bash
SERVICE=$1                     # e.g. patient
SLUG=$(./scripts/sanitize-branch-slug.sh "$(git branch --show-current)")
PROJECT="projects/$SERVICE-dev"
BRANCH_PATH="$PROJECT/branches/feat-$SLUG"

# Idempotent create
if ! databricks postgres get-branch "$BRANCH_PATH" -p hc-dev >/dev/null 2>&1; then
  databricks postgres create-branch "$PROJECT" "feat-$SLUG" \
    --json "$(cat <<EOF
{
  "spec": {
    "source_branch": "$PROJECT/branches/production"
  }
}
EOF
)" -p hc-dev
fi

# Idempotent endpoint create
ENDPOINT_PATH="$BRANCH_PATH/endpoints/primary"
if ! databricks postgres get-endpoint "$ENDPOINT_PATH" -p hc-dev >/dev/null 2>&1; then
  databricks postgres create-endpoint "$BRANCH_PATH" primary \
    --json '{
      "spec": {
        "endpoint_type": "ENDPOINT_TYPE_READ_WRITE",
        "autoscaling_limit_min_cu": 0.5,
        "autoscaling_limit_max_cu": 2.0
      }
    }' -p hc-dev
fi

# Print connection info for the dev's .env
HOST=$(databricks postgres list-endpoints "$BRANCH_PATH" -p hc-dev -o json | jq -r '.[0].status.hosts.host')
echo "ENDPOINT_NAME=$ENDPOINT_PATH"
echo "PGHOST=$HOST"
```

The full annotated walkthrough is in [`references/cli-walkthrough.md`](references/cli-walkthrough.md). The Python SDK fallback (for use inside CI when `databricks` CLI isn't on PATH) is also there.

### Run schema migrations against the feature branch

```bash
cd services/$SERVICE
# .env is already pointed at the feature endpoint
uv run alembic upgrade head
```

This is the only place migrations should be applied during feature development. Migrations only run against `<svc>-test` / `<svc>-prod` from the deploy workflows, never from a developer machine.

### Deploy the bundle against the feature branch

Once the Lakebase branch exists and migrations have run, deploy the apps bound to it:

```bash
SLUG=$(./scripts/sanitize-branch-slug.sh "$(git branch --show-current)")
databricks bundle deploy -t dev --var "lakebase_branch=feat-$SLUG"
```

The `lakebase_branch` variable is what every per-service bundle resource file (`resources/<svc>.yml`) reads via `${var.lakebase_branch}` to bind its postgres app resource to your branch. Default is `production`; override only for per-feature dev deploys. See `hc-dab-deployment` for full deploy verbs.

### Tear down (called from PR close/merge workflow OR locally if the dev abandons a branch)

```bash
SERVICE=$1
SLUG=$2  # the slug from the branch, computed once and stored in PR labels
PROJECT="projects/$SERVICE-dev"
BRANCH_PATH="$PROJECT/branches/feat-$SLUG"

# Endpoint first (can't delete a branch with attached endpoints)
databricks postgres delete-endpoint "$BRANCH_PATH/endpoints/primary" -p hc-dev || true
databricks postgres delete-branch "$BRANCH_PATH" -p hc-dev || true
```

The `|| true` is intentional — teardown is idempotent and tolerant of "already gone". The platform's TTL covers anything we miss.

### List active feature branches

```bash
for svc in patient provider appointment lab prescription billing; do
  echo "=== $svc ==="
  databricks postgres list-branches "projects/$svc-dev" -p hc-dev -o json \
    | jq -r '.[] | select(.name | startswith("feat-") or startswith("hotfix-")) | .name'
done
```

Wrap this in a `make active-branches` target.

### Find orphans (branches with no matching open PR)

In CI, a nightly cleanup job fetches the list of open PRs from GitHub, computes the expected slug for each, and deletes any feature branch whose slug isn't in that set. See `.github/workflows/cleanup-stale-branches.yml` (deferred — separate skill or follow-up).

## Cost guardrails

| Lever | Setting | Why |
|---|---|---|
| `autoscaling_limit_min_cu` | `0.5` | minimum scale-to-zero floor |
| `autoscaling_limit_max_cu` | `2.0` | enough for integration tests, won't accidentally spin up a 32 CU branch on a typo |
| `no_expiry` | omitted (defaults to `false`) | platform TTL is the safety net |
| Storage | bounded by source-branch size + WAL of changes | feature branches are cheap unless the feature does massive bulk inserts |

## Failure modes & how to recover

| Symptom | Likely cause | Fix |
|---|---|---|
| `branch already exists` | Same code branch was branched twice, e.g. by the dev locally and by CI | The create call is idempotent if you use `get-branch` first (see snippet above). Just re-run. |
| `endpoint creation timed out` | Lakebase project hit org quota | `databricks postgres list-projects -p hc-dev` and clean up unused dev projects, or escalate quota |
| Migrations applied to wrong DB | `.env` is pointing at `production`, not the feature branch | `cat .env` and double-check `ENDPOINT_NAME`. Migrations on `production` are reversible; run `alembic downgrade <previous-rev>` immediately. |
| Preview app deployed but can't connect | `app.yaml` has hardcoded host/endpoint instead of the feature branch values | The PR workflow injects feature-branch env via `databricks bundle deploy --var <name>_endpoint=...`. If you're seeing this in local dev, fix `.env`. |

## Verification

After running the create flow:

```bash
psql "host=$PGHOST port=5432 dbname=databricks_postgres user=$(databricks current-user me -p hc-dev -o json | jq -r .userName) sslmode=require" \
  -c "SELECT current_database(), inet_server_addr();"
```

Should connect using your user identity (the OAuth token is the password, regenerated per session).

For the test branch specifically: connect, run the migration, run a sample insert/select, then delete the branch and re-create it — the data should be gone (proof of isolation).
