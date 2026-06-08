#!/usr/bin/env bash
#
# Idempotently provision a Lakebase project (one per service per env).
#
# Why this is OUTSIDE the DAB bundle:
#   The bundle's `postgres_projects` resources used to live in
#   `resources/<svc>.yml` alongside the apps. That coupling meant every
#   `bundle deploy` (including per-PR previews with `app_name_suffix`
#   overrides) tracked the SHARED project in its terraform state, and a
#   `bundle destroy` of a preview would attempt to delete the project
#   (which got us in trouble — see git history of this file's introduction).
#   App resources reference projects by path string, not by bundle ref,
#   so the project doesn't need to be in the bundle at all.
#
# Each project has:
#   - A `production` branch (auto-created on project provision, then
#     marked `is_protected=true` here so it can't be deleted accidentally
#     and only protected branches can be `restore-target`s of recovery
#     operations).
#   - A `primary` endpoint on `production` (auto-created), 0.5/4 CU
#     scale-to-zero per the Phase 5 design.
# Per-feature branches are still managed by `lakebase-branch-{up,down}.sh`.
#
# Usage:
#   ./scripts/lakebase-project-up.sh <service> <env> [profile]
#     <service>  one of: patient provider appointment lab prescription billing
#     <env>      dev | test | prod
#     [profile]  CLI profile (default: hc-<env>)
#
# Idempotent: re-running on an existing project is a no-op.
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <service> <env> [profile]" >&2
  exit 2
fi

SERVICE="$1"
ENV="$2"
PROFILE="${3:-hc-$ENV}"

# Project ID is just the bare service name. Each env lives in its own
# workspace, so the Lakebase namespace is independent per env — there's no
# cross-env collision risk for a project named `patient`. `<env>` is kept
# in the script signature purely to derive the default profile.
PROJECT_ID="$SERVICE"
PROJECT_PATH="projects/$PROJECT_ID"

PRODUCTION_BRANCH_PATH="$PROJECT_PATH/branches/production"

>&2 echo "→ Ensuring Lakebase project $PROJECT_PATH (profile=$PROFILE)"

ensure_production_branch_protected() {
  # The `production` branch is auto-created with `is_protected=false`. We
  # always set it to true here so:
  #   - The branch can't be accidentally deleted (the API rejects deletion
  #     of protected branches).
  #   - Recovery / point-in-time-restore operations can target it as a
  #     `restore_target` (only protected branches qualify).
  # Field path is `spec.is_protected` (the `status.is_protected` value seen
  # in get-branch is the read-only mirror).
  local current
  current="$(databricks postgres get-branch "$PRODUCTION_BRANCH_PATH" -p "$PROFILE" -o json 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"].get("is_protected", False))' 2>/dev/null \
    || echo "False")"
  if [[ "$current" == "True" ]]; then
    >&2 echo "  production branch already protected"
    return 0
  fi
  >&2 echo "  protecting production branch"
  databricks postgres update-branch "$PRODUCTION_BRANCH_PATH" spec.is_protected \
    --json '{"spec":{"is_protected":true}}' \
    -p "$PROFILE" >/dev/null
}

if databricks postgres get-project "$PROJECT_PATH" -p "$PROFILE" >/dev/null 2>&1; then
  >&2 echo "  project $PROJECT_ID already exists, reusing"
  ensure_production_branch_protected
  exit 0
fi

# Same defaults the previous resources/<svc>.yml had, plus a 1h
# scale-to-zero (`suspend_timeout_duration`) instead of the platform
# default (24h). Reference workspace cost optimization — endpoints
# spin back up on the next connection.
#   pg_version 17, autoscale 0.5–4 CU, suspend after 3600s idle.
databricks postgres create-project "$PROJECT_ID" \
  --json "$(cat <<EOF
{
  "spec": {
    "pg_version": "17",
    "default_endpoint_settings": {
      "autoscaling_limit_min_cu": 0.5,
      "autoscaling_limit_max_cu": 4.0,
      "suspend_timeout_duration": "3600s"
    }
  }
}
EOF
)" -p "$PROFILE" >/dev/null

>&2 echo "  created $PROJECT_ID"

ensure_production_branch_protected
