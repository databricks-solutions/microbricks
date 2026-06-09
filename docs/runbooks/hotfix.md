# Hotfix Flow

How to ship an urgent fix to production outside the normal release cadence.

## When to use

- A production bug needs a targeted fix faster than the next scheduled release.
- The `develop` branch has unreleased work that should NOT go to prod yet.

## Procedure

### 1. Branch from the current production tag

```bash
git fetch --tags
CURRENT_TAG=$(git tag --sort=-creatordate | head -1)  # e.g. v0.2.1
git checkout -b hotfix/HC-XXX-brief-description $CURRENT_TAG
```

### 2. Implement the fix

Make the minimal change. Keep scope tight — a hotfix is not the place for cleanup.

```bash
# Run affected service's tests
cd services/<svc>
uv run pytest -m 'not integration'
```

### 3. Open a PR against `main`

```bash
git push -u origin hotfix/HC-XXX-brief-description
gh pr create --base main --title "fix(<svc>): brief description" \
  --body "Hotfix for production issue. Branched from $CURRENT_TAG."
```

This triggers `pr-validate.yml` (path-scoped to the changed service). Wait for checks to pass, get review, merge.

### 4. Tag and deploy

Once merged to `main`:

```bash
git checkout main && git pull
# Bump patch version
git tag v0.2.2
git push origin v0.2.2
```

`deploy-prod.yml` fires. Approve the deployment in the `prod` GitHub environment.

### 5. Back-merge to develop

Ensure the fix lands in the normal development stream:

```bash
git checkout develop && git pull
git merge main
git push origin develop
```

If there are conflicts, resolve them — the hotfix takes precedence for the fixed code, develop takes precedence for new features.

### 6. Verify production

```bash
# Smoke-test the affected service
APP_URL=$(databricks apps get <svc> -p hc-prod -o json | jq -r '.url')
curl -fsS "$APP_URL/api/v1/healthz"
```

## Worked example

Scenario: `patient-svc` returns 500 on `GET /api/v1/patients/{id}` because a migration added a NOT NULL column without a default.

```bash
git checkout -b hotfix/HC-042-patient-null-column v0.2.1
# Fix: add ALTER COLUMN SET DEFAULT in a new migration
# Test locally, push, open PR against main
# Merge, tag v0.2.2, approve prod deploy
# Back-merge main → develop
```

## Important notes

- Hotfix branches MUST target `main`, not `develop`.
- Always back-merge after the tag lands — forgetting this causes develop to diverge.
- If the hotfix requires a migration, it runs automatically before deploy (same as normal releases).
- If the fix is configuration-only (env var, Lakebase parameter), consider whether a code deploy is needed at all — some changes can be applied via `databricks apps update` directly.
