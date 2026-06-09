#!/usr/bin/env bash
#
# ci-local.sh — emulate the GitHub Actions workflows from a developer's
# machine. Same logical pipelines as `.github/workflows/*.yml`, just with
# auth resolved through `~/.databrickscfg` profiles (`hc-dev`/`hc-test`/
# `hc-prod`) instead of GitHub-injected env-secrets — which is what
# unblocks us today, since FE-VM's IP allowlist on the dev workspace
# blocks GH-hosted runner egress (see `github-runner-ip-acl` memory note).
#
# This script intentionally mirrors the workflow files closely so the only
# delta when CI eventually unblocks is the auth shape. If you change
# behavior here, update the matching `.github/workflows/<name>.yml` step
# and vice versa.
#
# Subcommands:
#
#   ci-local.sh pr-validate [--no-deploy]
#       Mirror `pr-validate.yml`. Path-detect changed services from the
#       committed diff against `develop`, lint + unit-test each changed
#       service, validate the bundle, provision Lakebase feature branches
#       for all six services, run alembic on changed services, build
#       both frontend UIs (hc-portal + clinic-sim), deploy a preview,
#       bundle run + wait + smoke-test all 8 apps.
#       --no-deploy stops after lint+test+bundle-validate (fast loop).
#
#       Note: detect-changes reads `git diff origin/develop...HEAD`, which
#       sees only COMMITTED changes. Working-tree edits do not count. A
#       warning is printed if uncommitted CI-relevant paths exist; commit
#       them first if you want per-service tests / migrations to run.
#
#   ci-local.sh pr-cleanup [SLUG]
#       Mirror `pr-cleanup.yml`. Destroy the preview deploy (all 8 apps)
#       and tear down all six per-feature Lakebase branches. SLUG
#       defaults to the slug of the current git branch.
#
#   ci-local.sh deploy <dev|test|prod> [--skip-tests]
#       Mirror `deploy-{dev,test,prod}.yml`. Run all unit tests across
#       the six services + hc-portal, alembic each service against the
#       env's `production` Lakebase branch, `bundle deploy -t <env>`,
#       bundle run + wait + smoke-test all 8 apps.
#       --skip-tests skips the unit-test phase (e.g. when re-running a
#       deploy after a known-good test run).
#
#   ci-local.sh nightly-cleanup
#       Mirror `nightly-orphan-cleanup.yml`. List every Lakebase feature
#       branch in dev and tear down anything not matching an open PR.
#       Uses `gh` to fetch the open-PR list.
#
# All subcommands are idempotent and re-runnable on failure.
#
# Requires: databricks (>=0.295.0), uv, gh, jq, python3.
set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve repo root + helpers regardless of where the script is invoked from.
# ---------------------------------------------------------------------------
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/.." &>/dev/null && pwd)
SLUG_SH="$SCRIPT_DIR/sanitize-branch-slug.sh"
BRANCH_UP="$SCRIPT_DIR/lakebase-branch-up.sh"
BRANCH_DOWN="$SCRIPT_DIR/lakebase-branch-down.sh"
BUILD_FRONTENDS="$SCRIPT_DIR/build-frontends.sh"

# Hardcoded service list — same six everywhere in the workflows. If a
# seventh service is added, update both this and the matching workflows.
SERVICES=(patient provider appointment lab prescription billing)

# ---------------------------------------------------------------------------
# Pretty-print helpers — no colors so the output is grep-friendly in
# `tee ci.log` and similar.
# ---------------------------------------------------------------------------
log()  { printf '\n┃ %s\n' "$*"; }
step() { printf '\n▶ %s\n'  "$*"; }
ok()   { printf '  ✓ %s\n'  "$*"; }
err()  { printf '  ✗ %s\n'  "$*" >&2; }

die() { err "$*"; exit 1; }

usage() {
  # Render the header docstring as plain text:
  #   - line 3 is the tagline (`ci-local.sh — emulate ...`); start there
  #     so the help opens with the script's identity, not mid-sentence.
  #   - stop at the first non-`#` line that immediately follows the
  #     docstring (in practice `set -euo pipefail`). The sentinel keeps
  #     usage() and the docstring in sync — extending the docstring
  #     just works; an accidental shift won't truncate or over-print.
  #   - strip the leading `# ` (or bare `#`) so the rendered text reads
  #     like prose, not a shell snippet.
  # awk (not sed) because BSD sed on macOS handles {…} grouping with
  # `s///` differently from GNU sed and silently drops the substitution.
  awk '
    NR == 1 { next }                 # skip shebang
    NR == 2 { next }                 # skip leading `#` separator
    /^[^#]/ { exit }                 # first non-comment line ends the docstring
    { sub(/^# ?/, ""); print }
  ' "${BASH_SOURCE[0]}"
  exit "${1:-2}"
}

# ---------------------------------------------------------------------------
# Auth precheck. The user's ~/.databrickscfg is the source of truth — fail
# fast if a profile is missing or invalid rather than letting the first
# bundle/api call mid-pipeline produce a confusing error.
# ---------------------------------------------------------------------------
require_profile() {
  local profile="$1"
  databricks auth describe -p "$profile" >/dev/null 2>&1 \
    || die "Profile '$profile' missing or invalid. Run: databricks auth login -p $profile"
}

# Compute the slug for the current branch (for pr-validate / pr-cleanup).
current_slug() {
  local branch="${GH_BRANCH:-$(git -C "$REPO_ROOT" branch --show-current)}"
  [[ -n "$branch" ]] || die "Could not determine current git branch"
  "$SLUG_SH" "$branch"
}

# ---------------------------------------------------------------------------
# Path-scoped change detection. Mirrors dorny/paths-filter from
# pr-validate.yml's `detect-changes` job. Compares the working tree against
# `origin/develop` (the merge target). If origin isn't fetched recently,
# results may lag — same caveat as CI.
#
# Emits one line per matching key so callers can grep:
#   patient
#   provider
#   ...
#   portal
#   infra
# ---------------------------------------------------------------------------
detect_changes() {
  local base_ref="${BASE_REF:-origin/develop}"
  git -C "$REPO_ROOT" fetch --quiet origin develop 2>/dev/null || true

  if ! git -C "$REPO_ROOT" rev-parse "$base_ref" >/dev/null 2>&1; then
    err "Base ref '$base_ref' not found; falling back to comparing against HEAD~1"
    base_ref="HEAD~1"
  fi

  local files
  files=$(git -C "$REPO_ROOT" diff --name-only "$base_ref"...HEAD)

  for svc in "${SERVICES[@]}"; do
    if grep -qE "^services/$svc/" <<<"$files"; then
      echo "$svc"
    fi
  done
  grep -qE '^frontend/hc-portal/' <<<"$files" && echo portal || true
  grep -qE '^(databricks\.yml|resources/|scripts/|\.github/workflows/)' <<<"$files" && echo infra || true
}

# ---------------------------------------------------------------------------
# detect-changes only sees COMMITTED changes (it diffs against
# origin/develop). That's correct for CI parity, but in local dev it
# silently skips per-service tests + migrations whenever the developer
# has WIP they haven't committed yet. This helper warns when uncommitted
# changes exist in any CI-relevant path so the developer is told
# explicitly that pr-validate won't lint/migrate/etc. that code.
#
# Categorizes WIP into the same buckets detect_changes emits so the
# warning maps 1:1 onto what would otherwise have been executed.
# Informational only — never blocks the run.
# ---------------------------------------------------------------------------
warn_wip_outside_diff() {
  # `git status --porcelain` lists ALL working-tree changes — modified,
  # staged, untracked. Path is in columns 4+. We don't care about the
  # status bytes for this warning.
  local porcelain
  porcelain=$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null || true)
  [[ -z "$porcelain" ]] && return 0

  local paths
  paths=$(awk '{ $1=""; sub(/^ /,""); print }' <<<"$porcelain")

  local -a wip_services=()
  for svc in "${SERVICES[@]}"; do
    grep -qE "^services/$svc/" <<<"$paths" && wip_services+=("$svc")
  done
  local wip_portal=0 wip_clinic=0 wip_infra=0
  grep -qE '^frontend/hc-portal/' <<<"$paths" && wip_portal=1
  grep -qE '^frontend/clinic-sim/' <<<"$paths" && wip_clinic=1
  grep -qE '^(databricks\.yml|resources/|scripts/|\.github/workflows/)' <<<"$paths" && wip_infra=1

  # Nothing CI-relevant uncommitted? Quiet exit.
  if (( ${#wip_services[@]} == 0 && wip_portal == 0 && wip_clinic == 0 && wip_infra == 0 )); then
    return 0
  fi

  printf '\n┃ WARNING: uncommitted WIP in CI-relevant paths\n'
  printf '  detect-changes diffs origin/develop...HEAD and sees COMMITTED code only.\n'
  printf '  Working-tree changes are invisible to it. The following will be SKIPPED\n'
  printf '  unless you commit first:\n'
  if (( ${#wip_services[@]} > 0 )); then
    printf '    - per-service lint+tests + alembic migrations for: %s\n' "${wip_services[*]}"
  fi
  (( wip_portal )) && printf '    - hc-portal lint+tests\n'
  (( wip_clinic )) && printf '    - clinic-sim (no test suite yet; build still runs)\n'
  (( wip_infra  )) && printf '    - infra-tagged paths (databricks.yml / resources/ / scripts/ / .github/workflows/)\n'
  printf '  Bundle validate + build + deploy + run + smoke STILL execute against\n'
  printf '  whatever is on disk (apx build syncs the working tree). Continuing...\n'
}

# ---------------------------------------------------------------------------
# Per-service lint + unit tests. Mirrors `service-checks` matrix in
# pr-validate.yml.
# ---------------------------------------------------------------------------
service_checks() {
  local svc="$1"
  step "service-checks ($svc)"
  (
    cd "$REPO_ROOT/services/$svc"
    uv sync --all-groups --quiet
    if uv run ty --help >/dev/null 2>&1; then
      uv run ty check src
    else
      uv run python -m compileall -q src
    fi
    uv run pytest -m 'not integration' -q
  )
  ok "service-checks ($svc) passed"
}

portal_checks() {
  step "portal-checks"
  (
    cd "$REPO_ROOT/frontend/hc-portal"
    uv sync --all-groups --quiet
    uv run pytest -m 'not integration' -q
  )
  ok "portal-checks passed"
}

# ---------------------------------------------------------------------------
# Build every apx project's React UI under `frontend/`. Mirrors the
# "Build all frontend UIs" step in `.github/workflows/*.yml`. Must run
# before `databricks bundle deploy` because:
#   - the deploy syncs source files only, no build step;
#   - the FastAPI factory only mounts the SPA when `src/<pkg>/__dist__/`
#     exists at runtime;
#   - that directory is gitignored, so a fresh checkout has no UI built.
# `databricks.yml`'s `sync.include` then force-includes the dist folders
# in the deploy.
# ---------------------------------------------------------------------------
build_frontends() {
  step "build all frontend UIs"
  "$BUILD_FRONTENDS"
  ok "frontend UIs built"
}

# ---------------------------------------------------------------------------
# Bundle validate. Mirrors `bundle-validate` job — same `--var` shape as a
# preview deploy so we catch the same parse errors CI would.
# ---------------------------------------------------------------------------
bundle_validate_preview() {
  local slug="$1"
  step "bundle validate (preview shape)"
  (
    cd "$REPO_ROOT"
    databricks bundle validate -t dev \
      --var "app_name_suffix=-$slug" \
      --var "lakebase_branch=$slug"
  )
  ok "bundle validate OK"
}

# ---------------------------------------------------------------------------
# alembic against a Lakebase endpoint. Mirrors the migrations step in
# pr-validate / deploy-*. The minted token is short-lived; the function
# is meant to be called per-service inside one shell session.
# ---------------------------------------------------------------------------
run_migrations() {
  # `project_target` is unused in the path now (project IDs dropped the
  # `-<env>` suffix); kept in the signature so callers don't have to change.
  local svc="$1" project_target="$2" branch="$3" profile="$4"
  step "alembic upgrade head: $svc against $branch (profile=$profile)"

  local endpoint host user
  endpoint="projects/$svc/branches/$branch/endpoints/primary"
  host=$(databricks postgres get-endpoint "$endpoint" -p "$profile" -o json \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"]["hosts"]["host"])')
  user=$(databricks current-user me -p "$profile" -o json \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["userName"])')

  (
    cd "$REPO_ROOT/services/$svc"
    uv sync --all-groups --quiet
    LOCAL_DEV_TOKEN=$(databricks auth token -p "$profile" -o json \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])') \
    DATABRICKS_HOST=$(databricks auth describe -p "$profile" -o json \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["details"]["host"])') \
    PGHOST="$host" \
    PGPORT=5432 \
    PGDATABASE=databricks_postgres \
    PGUSER="$user" \
    PGSSLMODE=require \
    ENDPOINT_NAME="$endpoint" \
    uv run alembic upgrade head
  )
  ok "alembic $svc OK"
}

# ---------------------------------------------------------------------------
# `bundle run` every app IN PARALLEL so the platform actually submits a new
# app deployment per resource. `bundle deploy` alone only syncs source and
# resource specs — without `bundle run`, the platform keeps serving the
# previous code (or stays UNAVAILABLE on first deploy). See the docs:
#   https://docs.databricks.com/aws/en/dev-tools/databricks-apps/cicd-github-actions
#
# All 7 are kicked in parallel: cross-app CAN_USE ACLs were wired by
# `bundle deploy` (deploy-time, not run-time) and the Apps platform allows
# concurrent deployments across distinct apps. Total wall time becomes
# max(app startup) rather than sum(app startup) — typically 5× faster than
# sequential.
#
# Each background run logs to its own file under a tmpdir so the on-screen
# output stays readable; on failure the failing app's full log is dumped.
#
# Extra args (e.g. `--var app_name_suffix=-feat-foo`) are passed through so
# the PR-preview shape resolves against the same root_path as the deploy.
# ---------------------------------------------------------------------------
bundle_run_apps() {
  local target="$1" profile="$2"
  shift 2
  local extra_args=("$@")
  step "bundle run (all apps in parallel, -t $target)"

  local log_dir
  log_dir=$(mktemp -d)
  local -a keys pids
  keys=(patient_app provider_app appointment_app lab_app prescription_app billing_app hc_portal_app clinic_sim_app)
  pids=()
  for key in "${keys[@]}"; do
    (
      cd "$REPO_ROOT"
      databricks bundle run -t "$target" -p "$profile" "${extra_args[@]}" "$key"
    ) > "$log_dir/$key.log" 2>&1 &
    local pid=$!
    pids+=("$pid")
    printf '  → kicked %s (pid=%s)\n' "$key" "$pid"
  done

  local fail=0 i key
  for i in "${!keys[@]}"; do
    key="${keys[$i]}"
    if wait "${pids[$i]}"; then
      ok "$key"
    else
      err "$key failed; full log:"
      cat "$log_dir/$key.log" >&2
      fail=1
    fi
  done
  rm -rf "$log_dir"
  (( fail == 0 )) || return 1
}

# ---------------------------------------------------------------------------
# Poll `apps get` until every app reaches RUNNING. `bundle run` returns once
# the deployment is signaled but the app may still be initializing — this is
# the explicit gate per Databricks' "Wait for app to be healthy" guidance.
# ---------------------------------------------------------------------------
wait_for_running() {
  local profile="$1" suffix="$2"
  step "wait for RUNNING (suffix='$suffix', profile=$profile)"
  for app in patient provider appointment lab prescription billing hc-portal clinic-sim; do
    local name="$app$suffix"
    local i state
    for i in $(seq 1 20); do
      state=$(databricks apps get "$name" -p "$profile" -o json 2>/dev/null \
        | python3 -c 'import json,sys; print(json.load(sys.stdin).get("app_status",{}).get("state",""))' 2>/dev/null || echo "")
      printf '  %s attempt %s/20: state=%s\n' "$name" "$i" "$state"
      if [[ "$state" == "RUNNING" ]]; then
        break
      fi
      if (( i == 20 )); then
        err "$name did not reach RUNNING within 5 minutes"
        return 1
      fi
      sleep 15
    done
  done
  ok "all 8 apps RUNNING"
}

# ---------------------------------------------------------------------------
# Honest /healthz smoke for every deployed app. The platform OBO gateway
# intercepts every request — without an SP Bearer token we'd either be
# 302'd to the OAuth login page or get an HTML login body with status 200,
# both of which `curl -fsS` silently passes. So we:
#   - mint an SP token via `databricks auth token` (M2M-compatible in
#     CLI >= 0.213),
#   - assert HTTP 200 exactly (not <400),
#   - assert body == {"ok":true} (the literal app/BFF healthz response).
#
# Services mount the route at /api/v1/healthz; hc-portal at /api/bff/healthz;
# clinic-sim at /api/sim/healthz (see
# frontend/clinic-sim/src/clinic_sim/backend/routers/simulator.py).
# See services/<svc>/src/<svc>/app.py and
# frontend/hc-portal/src/hc_portal/backend/routers/aggregations.py.
# ---------------------------------------------------------------------------
smoke_apps() {
  # `target` only labels the log line — app names dropped the `-<target>`
  # suffix; the deployed name is just `<svc>` (or `<svc><suffix>` for PR
  # previews where suffix is `-feat-<slug>`).
  local target="$1" suffix="$2" profile="$3"
  step "smoke test ($target$suffix)"

  local token
  token=$(databricks auth token -p "$profile" -o json \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

  _assert_healthz() {
    local name="$1" path="$2" url body_file http_code body
    url=$(databricks apps get "$name" -p "$profile" -o json 2>/dev/null \
      | python3 -c 'import json,sys; print(json.load(sys.stdin).get("url",""))' 2>/dev/null || echo "")
    if [[ -z "$url" ]]; then
      err "  $name: no URL (deploy may have failed)"
      return 1
    fi
    body_file=$(mktemp)
    http_code=$(curl -sS -o "$body_file" -w '%{http_code}' --max-time 30 \
      -H "Authorization: Bearer $token" \
      "$url$path" 2>/dev/null || echo "000")
    body=$(cat "$body_file"); rm -f "$body_file"
    if [[ "$http_code" != "200" ]]; then
      err "  $name $path -> HTTP $http_code (expected 200)"
      err "    body (first 300): $(printf '%s' "$body" | head -c 300)"
      return 1
    fi
    if [[ "$body" != '{"ok":true}' ]]; then
      err "  $name $path -> 200 but body mismatch:"
      err "    body (first 300): $(printf '%s' "$body" | head -c 300)"
      return 1
    fi
    printf '  ✓ %s %s -> 200 %s\n' "$name" "$path" "$body"
  }

  local fail=0
  for app in patient provider appointment lab prescription billing; do
    _assert_healthz "$app$suffix" "/api/v1/healthz" || fail=1
  done
  _assert_healthz "hc-portal$suffix" "/api/bff/healthz" || fail=1
  _assert_healthz "clinic-sim$suffix" "/api/sim/healthz" || fail=1

  if (( fail == 0 )); then
    ok "all 8 apps return 200 {\"ok\":true}"
  else
    return 1
  fi
}

# ===========================================================================
# Subcommand: pr-validate
# ===========================================================================
cmd_pr_validate() {
  local no_deploy=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-deploy) no_deploy=1; shift ;;
      *) die "unknown flag for pr-validate: $1" ;;
    esac
  done

  local slug
  slug=$(current_slug)
  # $slug already includes the `feat-` / `hotfix-` prefix (see
  # sanitize-branch-slug.sh) so it goes into the banner verbatim.
  log "pr-validate (slug=$slug)"

  warn_wip_outside_diff

  step "detect-changes"
  local changes_file
  changes_file=$(mktemp)
  # `${var:-}` so set -u doesn't complain if the trap fires before assignment
  # (e.g. mktemp failure) or in a subshell where the var is unbound.
  trap 'rm -f "${changes_file:-}"' EXIT
  detect_changes >"$changes_file"
  local changed_services=()
  local has_portal=0 has_infra=0
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    case "$line" in
      portal) has_portal=1 ;;
      infra)  has_infra=1 ;;
      *)      changed_services+=("$line") ;;
    esac
  done <"$changes_file"
  ok "services=${changed_services[*]:-(none)} portal=$has_portal infra=$has_infra"

  # `"${arr[@]+"${arr[@]}"}"` is the bash-3.2-safe empty-array expansion.
  # Bare `"${changed_services[@]}"` triggers "unbound variable" under
  # `set -u` when the array is empty (e.g. a PR that only touches
  # `frontend/`), even though the array IS declared on line above.
  for svc in "${changed_services[@]+"${changed_services[@]}"}"; do
    service_checks "$svc"
  done
  if (( has_portal )); then
    portal_checks
  fi

  require_profile hc-dev
  bundle_validate_preview "$slug"

  if (( no_deploy )); then
    log "pr-validate complete (lint + tests + bundle-validate; --no-deploy stop)"
    return 0
  fi

  # Ensure the underlying projects exist. They normally already do (created
  # by `ci-local.sh deploy dev`), but a fresh workspace's first PR would
  # otherwise hit "project not found". Idempotent.
  step "ensuring Lakebase projects (idempotent)"
  for svc in "${SERVICES[@]}"; do
    "$SCRIPT_DIR/lakebase-project-up.sh" "$svc" dev hc-dev
  done

  step "provision Lakebase feature branches (all six)"
  for svc in "${SERVICES[@]}"; do
    "$BRANCH_UP" "$svc" "$slug" hc-dev >/dev/null
    ok "  $slug ready in $svc-dev"
  done

  for svc in "${changed_services[@]+"${changed_services[@]}"}"; do
    run_migrations "$svc" dev "$slug" hc-dev
  done

  build_frontends

  step "bundle deploy preview (-t dev)"
  (
    cd "$REPO_ROOT"
    databricks bundle deploy -t dev \
      --var "app_name_suffix=-$slug" \
      --var "lakebase_branch=$slug"
  )
  ok "preview deployed"

  bundle_run_apps dev hc-dev \
    --var "app_name_suffix=-$slug" \
    --var "lakebase_branch=$slug"

  wait_for_running hc-dev "-$slug"

  smoke_apps dev "-$slug" hc-dev

  log "pr-validate complete — preview at https://hc-portal-$slug.<workspace>.databricksapps.com (simulator: clinic-sim-$slug.<workspace>.databricksapps.com)"
}

# ===========================================================================
# Subcommand: pr-cleanup
# ===========================================================================
cmd_pr_cleanup() {
  local slug="${1:-$(current_slug)}"
  # $slug already carries the `feat-`/`hotfix-` prefix from
  # sanitize-branch-slug.sh.
  log "pr-cleanup (slug=$slug)"

  require_profile hc-dev

  step "destroy preview bundle"
  (
    cd "$REPO_ROOT"
    # Tolerant of "nothing to destroy" — the script is idempotent.
    if ! databricks bundle destroy -t dev \
        --var "app_name_suffix=-$slug" \
        --var "lakebase_branch=$slug" \
        --auto-approve; then
      err "  bundle destroy returned non-zero (likely nothing to destroy)"
    fi
  )

  step "tear down Lakebase feature branches"
  for svc in "${SERVICES[@]}"; do
    "$BRANCH_DOWN" "$svc" "$slug" hc-dev || true
  done
  ok "cleanup done for $slug"
}

# ===========================================================================
# Subcommand: deploy
# ===========================================================================
cmd_deploy() {
  local target="${1:-}"
  shift || true
  local skip_tests=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --skip-tests) skip_tests=1; shift ;;
      *) die "unknown flag for deploy: $1" ;;
    esac
  done
  case "$target" in
    dev|test|prod) ;;
    *) die "deploy: target must be one of dev|test|prod" ;;
  esac

  local profile="hc-$target"
  log "deploy -t $target (profile=$profile)"
  require_profile "$profile"

  if (( ! skip_tests )); then
    for svc in "${SERVICES[@]}"; do
      service_checks "$svc"
    done
    portal_checks
  else
    step "skipping unit tests (--skip-tests)"
  fi

  # Project lifecycle is managed OUTSIDE the bundle (see resources/patient.yml
  # for the rationale). Make sure each project exists before the bundle
  # deploy tries to attach app->postgres resources.
  step "ensuring Lakebase projects (idempotent)"
  for svc in "${SERVICES[@]}"; do
    "$SCRIPT_DIR/lakebase-project-up.sh" "$svc" "$target" "$profile"
  done

  for svc in "${SERVICES[@]}"; do
    run_migrations "$svc" "$target" production "$profile"
  done

  build_frontends

  step "bundle deploy -t $target"
  (
    cd "$REPO_ROOT"
    databricks bundle deploy -t "$target"
  )
  ok "bundle deployed"

  bundle_run_apps "$target" "$profile"

  wait_for_running "$profile" ""

  smoke_apps "$target" "" "$profile"

  log "deploy -t $target complete"
}

# ===========================================================================
# Subcommand: nightly-cleanup
# ===========================================================================
cmd_nightly_cleanup() {
  log "nightly-cleanup (dev workspace)"
  require_profile hc-dev
  command -v gh >/dev/null || die "gh CLI required for open-PR allowlist"

  step "computing open-PR slug allowlist"
  local allow
  allow=$(mktemp)
  trap 'rm -f "${allow:-}"' EXIT
  for state in open merged closed; do
    while IFS= read -r ref; do
      [[ -z "$ref" ]] && continue
      slug=$("$SLUG_SH" "$ref")
      printf 'feat-%s\nhotfix-%s\n' "$slug" "$slug"
    done < <(gh pr list \
      --state "$state" \
      --search "updated:>=$(date -u -v-1d +%Y-%m-%d 2>/dev/null || date -u -d '24 hours ago' +%Y-%m-%d)" \
      --json headRefName --jq '.[].headRefName' 2>/dev/null || true)
  done | sort -u >"$allow"
  ok "allowlist size $(wc -l <"$allow")"

  for svc in "${SERVICES[@]}"; do
    step "scanning projects/$svc"
    local branches
    branches=$(databricks postgres list-branches "projects/$svc" -p hc-dev -o json 2>/dev/null \
      | python3 -c 'import json,sys; [print(b["name"]) for b in json.load(sys.stdin)]' \
      | grep -E '^(feat|hotfix)-' || true)
    while IFS= read -r branch; do
      [[ -z "$branch" ]] && continue
      if grep -qx "$branch" "$allow"; then
        printf '  keep %s\n' "$branch"
      else
        printf '  REAP %s\n' "$branch"
        "$BRANCH_DOWN" "$svc" "$branch" hc-dev || true
      fi
    done <<<"$branches"
  done
  ok "nightly-cleanup done"
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
sub="${1:-}"
shift || true
case "$sub" in
  pr-validate)     cmd_pr_validate     "$@" ;;
  pr-cleanup)      cmd_pr_cleanup      "$@" ;;
  deploy)          cmd_deploy          "$@" ;;
  nightly-cleanup) cmd_nightly_cleanup "$@" ;;
  -h|--help|help|"") usage 0 ;;
  *) usage 2 ;;
esac
