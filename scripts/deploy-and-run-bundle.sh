#!/usr/bin/env bash
#
# deploy-and-run-bundle.sh — `bundle deploy` and then actually START the apps.
#
# `databricks bundle deploy` syncs the source tree into the workspace and
# materializes each app *resource* (registers the app, attaches Lakebase /
# cross-app permissions, plumbs env vars). It does NOT trigger an app
# DEPLOYMENT — i.e. the unit that the Apps platform pulls from the synced
# source path and starts running. So a fresh `bundle deploy` against a never-
# deployed workspace leaves every app in `UNAVAILABLE` until something kicks
# off a deployment.
#
# `databricks bundle run -t <target> <app_key>` does that kick. For an app
# resource it: (1) submits a new app deployment from the bundle's
# `source_code_path`, (2) starts/updates the running app, (3) blocks until
# the app reaches ACTIVE (or fails). Run it once per app key after
# `bundle deploy` and the apps are live.
#
# This script wraps that into one verb so devs and CI don't have to remember
# to re-run seven `bundle run` calls every time. It mirrors `ci-local.sh`'s
# auth/var shape so the same overrides work for trunk and PR-preview deploys.
#
# Subcommands and flags are intentionally a thin layer over the underlying
# CLI — anything you need to tune (timeout, --no-wait, --restart) flows
# through to `bundle run` via the same flag names. See `databricks bundle run
# --help`.
#
# Usage:
#
#   deploy-and-run-bundle.sh <dev|test|prod> [--skip-deploy] [--no-wait]
#                                            [--restart] [--only=<app,app,...>]
#                                            [--var KEY=VALUE]...
#
# Flags:
#   --skip-deploy        Skip `bundle deploy` and only run the apps. Use when
#                        the bundle is already deployed and you just want to
#                        roll a new app deployment (e.g. after editing app
#                        source under services/<svc>/).
#   --no-wait            Pass through to `bundle run`. Submits each app
#                        deployment and returns immediately. Without this,
#                        the script waits for each app to reach ACTIVE before
#                        moving to the next one.
#   --restart            Pass through to `bundle run`. Force-restarts an app
#                        already in COMPUTE_STATUS_RUNNING.
#   --only=patient,lab   Restrict to a comma-separated list of app keys
#                        (matching the bundle resource keys, e.g.
#                        `patient_app`, `lab_app`, `hc_portal_app`). Useful
#                        for per-PR re-runs of one service. Accepts both
#                        full keys (`patient_app`) and short names
#                        (`patient`).
#   --var KEY=VALUE      Pass through to both `bundle deploy` and
#                        `bundle run`. Repeatable. Use to drive the
#                        per-PR preview shape:
#                          --var app_name_suffix=-feat-<slug>
#                          --var lakebase_branch=feat-<slug>
#
# Examples:
#
#   # Plain trunk-dev: deploy bundle, then start all seven apps
#   scripts/deploy-and-run-bundle.sh dev
#
#   # Already deployed, just (re)launch every app
#   scripts/deploy-and-run-bundle.sh dev --skip-deploy --restart
#
#   # PR-preview shape (matches ci-local.sh pr-validate's deploy)
#   SLUG=$(./scripts/sanitize-branch-slug.sh "$(git branch --show-current)")
#   scripts/deploy-and-run-bundle.sh dev \
#     --var "app_name_suffix=-feat-$SLUG" \
#     --var "lakebase_branch=feat-$SLUG"
#
#   # Just patient + lab (e.g. iterating on those two services)
#   scripts/deploy-and-run-bundle.sh dev --only=patient,lab
#
# Requires: databricks CLI (>= 0.295.0), python3.
set -euo pipefail

# ---------------------------------------------------------------------------
# Repo + helpers. Resolved relative to this script so the caller can be
# anywhere.
# ---------------------------------------------------------------------------
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/.." &>/dev/null && pwd)

# Dynamically discover all bundle resource keys from the filesystem.
# Services come first (alphabetical), then frontends — so the BFFs can
# ACL-attach to running siblings.
APP_KEYS=()
while IFS= read -r key; do
  APP_KEYS+=("$key")
done < <("$SCRIPT_DIR/discover-projects.sh" | jq -r '.all_bundle_keys[]')

log()  { printf '\n┃ %s\n' "$*"; }
step() { printf '\n▶ %s\n'  "$*"; }
ok()   { printf '  ✓ %s\n'  "$*"; }
err()  { printf '  ✗ %s\n'  "$*" >&2; }
die()  { err "$*"; exit 1; }

usage() {
  sed -n '4,60p' "${BASH_SOURCE[0]}"
  exit "${1:-2}"
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
target=""
skip_deploy=0
no_wait=0
restart=0
only_filter=""
declare -a passthrough_vars=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help|help) usage 0 ;;
    dev|test|prod)
      [[ -z "$target" ]] || die "target already set to '$target'; got '$1'"
      target="$1"; shift ;;
    --skip-deploy) skip_deploy=1; shift ;;
    --no-wait)     no_wait=1;     shift ;;
    --restart)     restart=1;     shift ;;
    --only=*)      only_filter="${1#--only=}"; shift ;;
    --only)        only_filter="${2:-}"; shift 2 ;;
    --var)
      # `--var KEY=VALUE` (two tokens) — match `databricks bundle deploy`.
      [[ $# -ge 2 ]] || die "--var requires KEY=VALUE"
      passthrough_vars+=(--var "$2")
      shift 2 ;;
    --var=*)
      passthrough_vars+=(--var "${1#--var=}")
      shift ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
done

[[ -n "$target" ]] || die "target required: dev|test|prod (see --help)"

profile="hc-$target"

# ---------------------------------------------------------------------------
# Auth precheck. Same shape as ci-local.sh — fail fast on a missing/invalid
# profile rather than letting `bundle deploy` produce a confusing later error.
# ---------------------------------------------------------------------------
databricks auth describe -p "$profile" >/dev/null 2>&1 \
  || die "Profile '$profile' missing or invalid. Run: databricks auth login -p $profile"

# ---------------------------------------------------------------------------
# Resolve which app keys to act on.
# ---------------------------------------------------------------------------
declare -a selected_keys
if [[ -n "$only_filter" ]]; then
  IFS=',' read -r -a tokens <<<"$only_filter"
  selected_keys=()
  for raw in "${tokens[@]}"; do
    name="${raw// /}"
    [[ -z "$name" ]] && continue
    # Accept both `patient` and `patient_app`.
    [[ "$name" == *_app ]] || name="${name}_app"
    case "$name" in
      hc-portal_app|hcportal_app) name="hc_portal_app" ;;
    esac
    found=0
    for key in "${APP_KEYS[@]}"; do
      if [[ "$key" == "$name" ]]; then
        selected_keys+=("$key")
        found=1
        break
      fi
    done
    (( found )) || die "unknown app in --only: '$raw' (valid: ${APP_KEYS[*]})"
  done
  [[ ${#selected_keys[@]} -gt 0 ]] || die "--only matched zero apps"
else
  selected_keys=("${APP_KEYS[@]}")
fi

log "deploy-and-run -t $target (profile=$profile, apps=${selected_keys[*]})"

# ---------------------------------------------------------------------------
# Step 1: bundle deploy (unless --skip-deploy).
# ---------------------------------------------------------------------------
if (( ! skip_deploy )); then
  step "bundle deploy -t $target"
  (
    cd "$REPO_ROOT"
    databricks bundle deploy -t "$target" -p "$profile" "${passthrough_vars[@]}"
  )
  ok "bundle deployed"
else
  step "skipping bundle deploy (--skip-deploy)"
fi

# ---------------------------------------------------------------------------
# Step 2: run each app. `bundle run` against an app key both submits a new
# app deployment from the synced source AND starts the app, so this is the
# verb that flips a freshly-deployed bundle from `UNAVAILABLE` to `ACTIVE`.
#
# We run them sequentially. Apps platform allows concurrent deployments
# across distinct apps, but per-app `bundle run` is exclusive — and the
# logs are easier to read sequential. Pass `--no-wait` if you want to
# fire-and-forget.
# ---------------------------------------------------------------------------
declare -a run_flags=()
(( no_wait )) && run_flags+=(--no-wait)
(( restart )) && run_flags+=(--restart)

for key in "${selected_keys[@]}"; do
  step "bundle run $key (-t $target)"
  (
    cd "$REPO_ROOT"
    databricks bundle run -t "$target" -p "$profile" \
      "${run_flags[@]}" "${passthrough_vars[@]}" "$key"
  )
  ok "$key is live"
done

log "deploy-and-run -t $target complete (${#selected_keys[@]} app(s))"
