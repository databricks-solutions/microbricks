#!/usr/bin/env bash
#
# Idempotently provision a Lakebase feature-branch + endpoint for one service.
#
# Mirrors the workflow documented in `.claude/skills/hc-lakebase-branching`.
# Used by both:
#   - Local devs (CONTRIBUTING.md "Branch the database (per service you're
#     changing)" step), and
#   - .github/workflows/pr-validate.yml (per-PR preview).
#
# Usage:
#   ./scripts/lakebase-branch-up.sh <service> <slug> [profile]
#
#   <service>  one of: patient provider appointment lab prescription billing
#   <slug>     output of scripts/sanitize-branch-slug.sh "$BRANCH"
#              (the script auto-prefixes with `feat-` if missing)
#   [profile]  Databricks CLI profile to target. Default: hc-dev.
#              Per the branch -> environment map, only hc-dev makes sense for
#              feature branches. The arg exists so future cross-env scripts
#              can reuse this entry-point without duplicating the body.
#
# Outputs (on stdout, key=value, one per line) the values the caller drops
# into a `.env` file or sets as DAB --var overrides:
#   ENDPOINT_NAME=projects/<svc>/branches/feat-<slug>/endpoints/primary
#   PGHOST=<host>
#   LAKEBASE_BRANCH=feat-<slug>
#
# Idempotent: re-running with the same inputs is a no-op (returns same values).
# Failures are NOT swallowed — for teardown idempotency see lakebase-branch-down.sh.
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <service> <slug> [profile]" >&2
  exit 2
fi

SERVICE="$1"
SLUG="$2"
PROFILE="${3:-hc-dev}"

# Allow callers to pass either the bare slug ("hc-123-foo") or the prefixed
# form ("feat-hc-123-foo"); normalize to the prefixed form here.
case "$SLUG" in
  feat-*|hotfix-*) BRANCH="$SLUG" ;;
  *)               BRANCH="feat-$SLUG" ;;
esac

# Project name is just `<svc>` (no `${bundle.target}` suffix) — the contract
# from `resources/<svc>.yml`. Feature branches always live in the dev
# workspace; the `production` source branch in that workspace is the seed.
PROJECT="projects/$SERVICE"
BRANCH_PATH="$PROJECT/branches/$BRANCH"
ENDPOINT_PATH="$BRANCH_PATH/endpoints/primary"

>&2 echo "→ Ensuring Lakebase branch $BRANCH_PATH (profile=$PROFILE)"

# 1. Create branch if missing. `databricks postgres get-branch` exits non-zero
# when the branch doesn't exist, so we use it as the existence probe.
if ! databricks postgres get-branch "$BRANCH_PATH" -p "$PROFILE" >/dev/null 2>&1; then
  # `ttl: 86400s` (24h) — feature branches are explicitly ephemeral. The
  # platform requires an `expire_time`, `ttl`, OR `no_expiry: true` per
  # the create-branch API; we pick `ttl` so the platform GCs the branch
  # automatically if pr-cleanup never runs (force-deleted PR, killed
  # workflow, etc.). The nightly-orphan-cleanup workflow + manual
  # lakebase-branch-down.sh both still work; this is just a safety net.
  databricks postgres create-branch "$PROJECT" "$BRANCH" \
    --json "$(cat <<EOF
{
  "spec": {
    "source_branch": "$PROJECT/branches/production",
    "ttl": "86400s"
  }
}
EOF
)" -p "$PROFILE" >/dev/null
  >&2 echo "  created branch $BRANCH (24h TTL)"
else
  >&2 echo "  branch $BRANCH already exists, reusing"
fi

# 2. Create read-write endpoint if missing. Cost guardrails come from
# `hc-lakebase-branching`: 0.5 min CU (scale-to-zero), 2 max CU,
# 1h suspend timeout for cost optimization on a reference workspace.
# (Lakebase auto-creates a `primary` endpoint when a branch is created
# in newer API versions; we still attempt the create for older API
# behavior, and the get-endpoint check ensures idempotency.)
if ! databricks postgres get-endpoint "$ENDPOINT_PATH" -p "$PROFILE" >/dev/null 2>&1; then
  databricks postgres create-endpoint "$BRANCH_PATH" primary \
    --json '{
      "spec": {
        "endpoint_type": "ENDPOINT_TYPE_READ_WRITE",
        "autoscaling_limit_min_cu": 0.5,
        "autoscaling_limit_max_cu": 2.0,
        "suspend_timeout_duration": "3600s"
      }
    }' -p "$PROFILE" >/dev/null
  >&2 echo "  created endpoint primary"
else
  >&2 echo "  endpoint primary already exists, reusing"
fi

# 3. Read host back so callers can `eval $(...)` the output into their env.
HOST=$(databricks postgres get-endpoint "$ENDPOINT_PATH" -p "$PROFILE" -o json \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"]["hosts"]["host"])')

cat <<EOF
ENDPOINT_NAME=$ENDPOINT_PATH
PGHOST=$HOST
LAKEBASE_BRANCH=$BRANCH
EOF
