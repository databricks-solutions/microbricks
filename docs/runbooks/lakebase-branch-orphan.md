# Lakebase Branch Orphan Cleanup

How to identify and remove leaked Lakebase feature branches that no longer have an associated open PR.

## Background

Each PR provisions up to six Lakebase feature branches (one per service: `feat-<slug>/patient`, `feat-<slug>/provider`, etc.). These are torn down automatically by:

1. **`pr-cleanup.yml`** — runs on PR close (merged or abandoned).
2. **`nightly-orphan-cleanup.yml`** — cron job that GCs branches whose PR no longer exists.
3. **Platform TTL** — Lakebase auto-deletes branches after 24h of inactivity (scale-to-zero → expiry).

If all three fail (workflow error, cron disabled, TTL extended), orphan branches accumulate and consume quota.

## Identifying orphans

### List all feature branches across services

```bash
PROFILE=hc-dev
for svc in patient provider appointment lab prescription billing; do
  echo "=== $svc ==="
  databricks postgres list-branches $svc -p $PROFILE -o json \
    | jq -r '.[] | select(.name != "production") | .name'
done
```

### Cross-reference with open PRs

```bash
# Get all open PR slugs
OPEN_SLUGS=$(gh pr list --state open --json headRefName \
  | jq -r '.[].headRefName' \
  | xargs -I{} ./scripts/sanitize-branch-slug.sh {} \
  | sort -u)

# Compare — branches NOT in the open-PR list are orphans
```

## Manual cleanup

Use the existing teardown script for each orphan:

```bash
SLUG="feat-old-branch"
PROFILE=hc-dev

for svc in patient provider appointment lab prescription billing; do
  ./scripts/lakebase-branch-down.sh $svc $SLUG $PROFILE
done
```

The script is idempotent — safe to re-run if partially completed.

## Bulk cleanup

For multiple orphans:

```bash
ORPHANS="feat-stale-one feat-stale-two feat-gone-three"
PROFILE=hc-dev

for slug in $ORPHANS; do
  for svc in patient provider appointment lab prescription billing; do
    ./scripts/lakebase-branch-down.sh $svc $slug $PROFILE &
  done
  wait
done
```

## Verifying cleanup

```bash
# Confirm no branches remain for a given slug
for svc in patient provider appointment lab prescription billing; do
  databricks postgres list-branches $svc -p hc-dev -o json \
    | jq --arg slug "feat-stale-one" '.[] | select(.name == $slug)'
done
# Should produce no output
```

## Preventing future orphans

- Ensure `pr-cleanup.yml` is not disabled in the repo settings.
- The `nightly-orphan-cleanup.yml` cron runs at 03:00 UTC daily. Check **Actions > nightly-orphan-cleanup** for recent failures.
- If a PR is force-deleted (not closed normally), the `pull_request: closed` event may not fire. The nightly job is the safety net for this case.

## When NOT to delete

- Branches named `production` — these are the trunk branches, never delete them.
- Branches actively used by a running preview app — check `databricks apps list -p hc-dev` for apps with the slug suffix before tearing down.
- If unsure whether a branch is in use, check: `databricks postgres get-branch <project> <branch> -p hc-dev -o json | jq '.endpoint.state'` — if `RUNNING` or `STARTING`, someone may be using it.
