#!/usr/bin/env bash
#
# Idempotently tear down a Lakebase feature-branch endpoint + branch.
#
# Mirrors the teardown workflow in `.claude/skills/hc-lakebase-branching`.
# Used by:
#   - .github/workflows/pr-cleanup.yml on PR close (merged or not), and
#   - .github/workflows/nightly-orphan-cleanup.yml as the GC verb, and
#   - Local devs cleaning up an abandoned feature.
#
# Usage:
#   ./scripts/lakebase-branch-down.sh <service> <slug> [profile]
#
# Tolerant of "already gone" — every sub-call is `|| true` because the
# platform's 24h TTL means we routinely race the auto-cleaner and that's
# fine: re-running is the recovery procedure.
#
# Order matters: an endpoint must be deleted before its branch.
set -uo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <service> <slug> [profile]" >&2
  exit 2
fi

SERVICE="$1"
SLUG="$2"
PROFILE="${3:-hc-dev}"

case "$SLUG" in
  feat-*|hotfix-*) BRANCH="$SLUG" ;;
  *)               BRANCH="feat-$SLUG" ;;
esac

PROJECT="projects/$SERVICE-dev"
BRANCH_PATH="$PROJECT/branches/$BRANCH"
ENDPOINT_PATH="$BRANCH_PATH/endpoints/primary"

>&2 echo "→ Tearing down Lakebase branch $BRANCH_PATH (profile=$PROFILE)"

databricks postgres delete-endpoint "$ENDPOINT_PATH" -p "$PROFILE" >/dev/null 2>&1 || true
databricks postgres delete-branch    "$BRANCH_PATH"   -p "$PROFILE" >/dev/null 2>&1 || true

# Verify nothing remains. We treat "still exists" as a soft failure (exit 0)
# because the most likely cause is a transient API error and the platform TTL
# will sweep it up; the workflow surfaces the warning in the PR comment.
if databricks postgres get-branch "$BRANCH_PATH" -p "$PROFILE" >/dev/null 2>&1; then
  >&2 echo "  warning: branch still present after delete; relying on platform TTL"
else
  >&2 echo "  branch removed"
fi
