#!/usr/bin/env bash
#
# Permanently delete a Lakebase project. PURGES (hard delete) — no soft
# delete recovery.
#
# DANGER: this destroys all data in the project's branches. Asks for
# confirmation unless `FORCE=1` is set in the environment.
#
# Usage:
#   ./scripts/lakebase-project-down.sh <service> <env> [profile]
#
# This is the rare verb; most teardown is per-feature branches via
# `lakebase-branch-down.sh`. Use this only when you genuinely want the
# whole project gone (e.g. tearing down a workspace, or cleaning up after
# the destructive incident this script's existence is documented against
# in `dev-bundle-destroy-disaster` memory note).
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <service> <env> [profile]   (set FORCE=1 to skip confirmation)" >&2
  exit 2
fi

SERVICE="$1"
ENV="$2"
PROFILE="${3:-hc-$ENV}"

# Project ID matches lakebase-project-up.sh — bare service name, no `<env>`
# suffix. The `<env>` arg is kept for the default-profile derivation only.
PROJECT_ID="$SERVICE"
PROJECT_PATH="projects/$PROJECT_ID"

if ! databricks postgres get-project "$PROJECT_PATH" -p "$PROFILE" >/dev/null 2>&1; then
  >&2 echo "  project $PROJECT_ID does not exist, nothing to do"
  exit 0
fi

if [[ "${FORCE:-0}" != "1" ]]; then
  >&2 echo "About to PERMANENTLY DELETE $PROJECT_ID in $PROFILE."
  >&2 echo "All branch data, all endpoint history, all attached resources gone."
  read -r -p "Type the project ID to confirm: " confirm
  if [[ "$confirm" != "$PROJECT_ID" ]]; then
    >&2 echo "  abort: confirmation did not match"
    exit 1
  fi
fi

# `--purge` skips the soft-delete grace period — necessary because the
# soft-deleted state still owns the project_id and prevents a same-name
# recreate. The non-purge path leaves the project in a state where
# `bundle deploy` errors with "project with such id already exists" while
# `list-projects` returns it empty. Always purge.
databricks postgres delete-project "$PROJECT_PATH" --purge -p "$PROFILE" >/dev/null

>&2 echo "  purged $PROJECT_ID"
