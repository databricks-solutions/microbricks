# Lakebase branching — annotated CLI + SDK walkthrough

Detailed reference for [`../SKILL.md`](../SKILL.md). Read the SKILL first; this is the full-fidelity version with annotations and an SDK fallback.

## Prerequisites

```bash
# CLI version
databricks --version
# Must be ≥ 0.285.0 for `databricks postgres` (Lakebase Autoscale)
```

```bash
# Profile sanity check
databricks postgres list-projects -p hc-dev -o json | jq -r '.[].name' | head
```

## Anatomy of the resource paths

The Lakebase Autoscale CLI uses fully-qualified paths everywhere:

```
projects/<project-id>
projects/<project-id>/branches/<branch-id>
projects/<project-id>/branches/<branch-id>/endpoints/<endpoint-id>
```

Resource IDs: 3-63 chars, lowercase letters / digits / hyphens, must start with a lowercase letter. Our convention:

- Project: `<service>-<env>` (e.g. `patient-dev`)
- Branch: `production` (long-lived) or `feat-<slug>` / `hotfix-<slug>` (ephemeral)
- Endpoint: `primary` (the read-write endpoint), `read-replica` (optional, prod only)

## Full create flow with explanations

```bash
SERVICE=patient
SLUG=hc-123-add-allergies
PROFILE=hc-dev

PROJECT="projects/$SERVICE-dev"
BRANCH="$PROJECT/branches/feat-$SLUG"
ENDPOINT="$BRANCH/endpoints/primary"

# 1. Create branch from production. source_branch is required; we always branch off prod.
#    (Branching off another feature branch is technically supported but creates ordering pain — don't.)
databricks postgres create-branch "$PROJECT" "feat-$SLUG" \
  --json '{
    "spec": {
      "source_branch": "'"$PROJECT"'/branches/production"
    }
  }' \
  -p $PROFILE

# 2. Create the endpoint. ENDPOINT_TYPE_READ_WRITE is required for migrations.
#    autoscaling_limit_min_cu=0.5 enables scale-to-zero.
#    autoscaling_limit_max_cu=2.0 caps cost — this is more than enough for integration tests.
databricks postgres create-endpoint "$BRANCH" primary \
  --json '{
    "spec": {
      "endpoint_type": "ENDPOINT_TYPE_READ_WRITE",
      "autoscaling_limit_min_cu": 0.5,
      "autoscaling_limit_max_cu": 2.0
    }
  }' \
  -p $PROFILE

# 3. Look up the host for the endpoint
HOST=$(databricks postgres get-endpoint "$ENDPOINT" -p $PROFILE -o json \
  | jq -r '.status.hosts.host')

# 4. Look up the username (you, in dev — the email of your Databricks identity)
EMAIL=$(databricks current-user me -p $PROFILE -o json | jq -r '.userName')

# 5. Generate a fresh OAuth credential (the Postgres password, valid ~1h)
TOKEN=$(databricks postgres generate-database-credential "$ENDPOINT" -p $PROFILE -o json \
  | jq -r '.token')

# 6. Connect
PGPASSWORD="$TOKEN" psql "host=$HOST port=5432 dbname=databricks_postgres user=$EMAIL sslmode=require"
```

### Why we always branch from `production` not from another feature branch

Lakebase branches form a tree. Branching off another feature branch makes the new branch dependent on the old one's lifetime — if the parent gets deleted, the child gets orphaned. Branching from `production` keeps every feature branch independent.

### Why `autoscaling_limit_min_cu = 0.5`

It's the lowest setting that allows scale-to-zero. Idle feature branches cost effectively $0; an active branch ramps up on first connection (~5-15s cold start, acceptable for integration tests). If a feature does heavy schema/data work, bump max to 4.0 temporarily — but never the floor.

### Why we don't set `no_expiry: true`

Platform TTL (~24h of inactivity → delete) is our safety net for branches whose teardown workflow failed. `no_expiry: true` defeats this and is reserved for the long-lived `production` branch.

## SDK fallback (Python, for CI)

When the CI image doesn't have the CLI but does have `databricks-sdk`:

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.database import (
    DatabaseBranch,
    DatabaseBranchSpec,
    DatabaseEndpoint,
    DatabaseEndpointSpec,
)

w = WorkspaceClient(profile="hc-dev")  # or use env-injected OAuth credential

project = "patient-dev"
slug = "hc-123-add-allergies"
branch_name = f"feat-{slug}"

# Idempotent create
branch_path = f"projects/{project}/branches/{branch_name}"
try:
    w.postgres.get_branch(name=branch_path)
except Exception:
    w.postgres.create_branch(
        parent=f"projects/{project}",
        branch_id=branch_name,
        branch=DatabaseBranch(
            spec=DatabaseBranchSpec(
                source_branch=f"projects/{project}/branches/production",
            )
        ),
    )

endpoint_path = f"{branch_path}/endpoints/primary"
try:
    w.postgres.get_endpoint(name=endpoint_path)
except Exception:
    w.postgres.create_endpoint(
        parent=branch_path,
        endpoint_id="primary",
        endpoint=DatabaseEndpoint(
            spec=DatabaseEndpointSpec(
                endpoint_type="ENDPOINT_TYPE_READ_WRITE",
                autoscaling_limit_min_cu=0.5,
                autoscaling_limit_max_cu=2.0,
            )
        ),
    )

ep = w.postgres.get_endpoint(name=endpoint_path)
print(f"ENDPOINT_NAME={endpoint_path}")
print(f"PGHOST={ep.status.hosts.host}")
```

The exact import paths above mirror the SDK as of CLI 0.285.0; if the SDK structure has shifted (Lakebase Autoscale was preview when this was written), grep `databricks-sdk` for `class DatabaseBranch` and adapt.

## Teardown

```bash
SERVICE=patient
SLUG=hc-123-add-allergies
PROFILE=hc-dev
BRANCH="projects/$SERVICE-dev/branches/feat-$SLUG"

# Endpoints first — branch deletion fails if any endpoint is attached
databricks postgres delete-endpoint "$BRANCH/endpoints/primary" -p $PROFILE 2>/dev/null || true
databricks postgres delete-branch "$BRANCH" -p $PROFILE 2>/dev/null || true
```

The `2>/dev/null || true` makes the teardown idempotent and lets it run safely from the workflow even if the user has already cleaned up locally.

## Listing for housekeeping

```bash
# All feature branches across all services in dev
for svc in patient provider appointment lab prescription billing; do
  databricks postgres list-branches "projects/$svc-dev" -p hc-dev -o json \
    | jq -r --arg svc "$svc" '.[] | select(.name | test("(feat|hotfix)-")) | "\($svc) \(.name) \(.spec.source_branch) \(.create_time)"'
done | column -t
```

## Cost back-of-envelope

- Idle feature branch (no connections in 5min): scaled to zero, **$0**.
- Active feature branch during a test run: ~30s of 1-2 CU = **fractions of a cent**.
- Storage: copy-on-write deltas. A schema-only feature branch is < 1 MB.

A team running 50 active feature branches simultaneously across all 6 services consumes < $1/day if the branches are mostly idle, which they are.

## Common gotchas

1. **Slug too long.** Lakebase resource IDs cap at 63 chars. Our slug is capped at 50 to leave room for the `feat-` prefix; longer code branch names are silently truncated. If your slug ends mid-word, that's fine — Lakebase only cares that it's a valid identifier.

2. **Identifier collision after truncation.** If two long branch names truncate to the same slug, the second one silently re-uses the first one's branch. Mitigation: ticket prefix at the front (`HC-123`) makes collisions almost impossible in practice; CI should fail loudly if `get-branch` returns an existing branch with a different `source_branch` than expected.

3. **Forgot to set `ENDPOINT_NAME` after switching code branches.** A common dev-time bug: switch from `feature/A` to `feature/B`, forget to update `.env`, run migrations against branch A's DB. Mitigation: a `direnv` `.envrc` that derives `ENDPOINT_NAME` from `git branch --show-current` automatically.

4. **CI race: branch created concurrently by parallel jobs.** If two services in one PR both try to create branches at the same moment, the API may return 409. The `get-branch` precheck eliminates this in practice.
