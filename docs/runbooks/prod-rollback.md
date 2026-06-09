# Production Rollback

How to redeploy a previous version when a production release introduces a regression.

## When to use

- A `v*` tag deploy succeeded but the app is misbehaving in production.
- You need to revert to the last-known-good state quickly.

## Procedure

### 1. Identify the last-known-good tag

```bash
git tag --sort=-creatordate | head -5
# e.g. v0.2.1, v0.2.0, v0.1.9 ...
```

Pick the tag you want to roll back to (e.g. `v0.2.0`).

### 2. Re-tag and push

Create a new tag pointing at the old commit. This re-triggers `deploy-prod.yml` with its manual-approval gate.

```bash
git checkout v0.2.0
git tag v0.2.0-rollback
git push origin v0.2.0-rollback
```

The `deploy-prod.yml` workflow fires because the tag matches `v*`. A required reviewer must approve the deployment in the `prod` GitHub environment before it proceeds.

### 3. Approve the deployment

Go to **Actions > deploy-prod > Waiting for review** and approve.

### 4. Verify

Once the workflow completes:

```bash
databricks apps get patient -p hc-prod -o json | jq '.app_status.state'
# Should be "RUNNING"

curl -fsS "$(databricks apps get hc-portal -p hc-prod -o json | jq -r '.url')/api/bff/healthz"
# {"ok":true}
```

### 5. Investigate and fix forward

Rollback buys time. Open a hotfix branch (see `hotfix.md`) to address the root cause, then deploy a proper new tag.

## Migration rollback (if needed)

If the bad release included a database migration that must be undone:

```bash
# Find the target revision (one before the bad migration)
uv run alembic -c services/<svc>/migrations/alembic.ini history

# Downgrade
uv run alembic -c services/<svc>/migrations/alembic.ini downgrade <target_revision>
```

Run this against the production Lakebase endpoint BEFORE redeploying the old tag (the old code expects the old schema).

## Important notes

- `deploy-prod.yml` uses `concurrency: { group: deploy-prod, cancel-in-progress: false }` — if a deploy is already running, the rollback queues behind it.
- Never force-delete a tag that CI already processed; create a new one instead.
- If the issue is data-layer only (bad seed, corrupt row), a rollback won't help — investigate the DB directly.
