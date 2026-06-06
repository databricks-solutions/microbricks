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
#   - A `production` branch (auto-created on project provision).
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

PROJECT_ID="$SERVICE-$ENV"
PROJECT_PATH="projects/$PROJECT_ID"

>&2 echo "→ Ensuring Lakebase project $PROJECT_PATH (profile=$PROFILE)"

if databricks postgres get-project "$PROJECT_PATH" -p "$PROFILE" >/dev/null 2>&1; then
  >&2 echo "  project $PROJECT_ID already exists, reusing"
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
