#!/usr/bin/env bash
#
# deploy-clinic-sim.sh — build, deploy, and start the clinic-sim app on a
# single Databricks target.
#
# This is a focused wrapper around `bundle deploy` + `bundle run` that does
# the things you'd otherwise have to remember in order:
#
#   1. Pre-flight: profile auth, apx + bun + databricks CLI on PATH.
#   2. Build the clinic-sim React UI (apx frontend build → __dist__/).
#   3. `databricks bundle deploy -t <target>` so the resource list (apps +
#      Lakebase bindings) is up-to-date in the workspace.
#   4. `databricks bundle run -t <target> clinic_sim_app` — submits an app
#      deployment from the synced source and waits for ACTIVE.
#   5. Resolve the app's canonical workspace URL and print it.
#
# It does NOT seed Lakebase, run alembic, or deploy the six backend services.
# The simulator can't function without them, so the script will fail-fast if
# any backend service isn't already deployed.
#
# Usage:
#   scripts/deploy-clinic-sim.sh <dev|test|prod> [--feature] [--no-wait]
#                                                [--restart] [--skip-deploy]
#                                                [--skip-build]
#
# Flags:
#   --feature       Deploy as a per-feature-branch preview alongside trunk
#                   apps. Sets `app_name_suffix=-<slug>` and
#                   `lakebase_branch=<slug>` where <slug> is the output of
#                   `scripts/sanitize-branch-slug.sh` for the current git
#                   branch (already includes the `feat-` / `hotfix-`
#                   prefix). Provisions the matching Lakebase branches for
#                   all six services first if they don't already exist.
#   --skip-build    Skip `apx frontend build`. Use when the UI is already
#                   built and you're iterating only on the BFF.
#   --skip-deploy   Skip `bundle deploy` and only run the app. Use when the
#                   bundle is already deployed and you just want a fresh
#                   app deployment from updated source.
#   --no-wait       Pass through to `bundle run`. Submits the deployment
#                   and returns without waiting for ACTIVE.
#   --restart       Pass through to `bundle run`. Force-restart even if the
#                   app is already RUNNING.
#
# Examples:
#
#   # Plain trunk-dev deploy (assumes services + Lakebase branches already up)
#   scripts/deploy-clinic-sim.sh dev
#
#   # Per-feature-branch preview, lockstep with the current git branch
#   scripts/deploy-clinic-sim.sh dev --feature
#
#   # Rebuild + redeploy only the app (bundle resources unchanged)
#   scripts/deploy-clinic-sim.sh dev --skip-deploy --restart
#
# Requires: databricks (>=0.295.0), apx, bun, jq.
set -euo pipefail

# ---------------------------------------------------------------------------
# Repo + helper resolution. Independent of the caller's cwd.
# ---------------------------------------------------------------------------
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/.." &>/dev/null && pwd)
SLUG_SH="$SCRIPT_DIR/sanitize-branch-slug.sh"
BRANCH_UP="$SCRIPT_DIR/lakebase-branch-up.sh"

# Dynamically discover services from the filesystem. Used for optional
# `--feature` Lakebase branch provisioning AND the pre-flight check that
# every backend app already exists in the target workspace.
SERVICES=()
while IFS= read -r dir; do
  SERVICES+=("$dir")
done < <("$SCRIPT_DIR/discover-projects.sh" | jq -r '.service_dirs[]')

# Bundle resource key the script deploys. Must match resources/clinic-sim.yml.
APP_KEY="clinic_sim_app"

# ---------------------------------------------------------------------------
# Output formatting. No ANSI colors — grep-friendly for `tee deploy.log`.
# ---------------------------------------------------------------------------
log()  { printf '\n┃ %s\n' "$*"; }
step() { printf '\n▶ %s\n'  "$*"; }
ok()   { printf '  ✓ %s\n'  "$*"; }
err()  { printf '  ✗ %s\n'  "$*" >&2; }
die()  { err "$*"; exit 1; }

usage() {
  sed -n '4,55p' "${BASH_SOURCE[0]}"
  exit "${1:-2}"
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
target=""
feature_mode=0
no_wait=0
restart=0
skip_deploy=0
skip_build=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help|help) usage 0 ;;
    dev|test|prod)
      [[ -z "$target" ]] || die "target already set to '$target'; got '$1'"
      target="$1"; shift ;;
    --feature)     feature_mode=1; shift ;;
    --no-wait)     no_wait=1;      shift ;;
    --restart)     restart=1;      shift ;;
    --skip-deploy) skip_deploy=1;  shift ;;
    --skip-build)  skip_build=1;   shift ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
done

[[ -n "$target" ]] || die "target required: dev|test|prod (see --help)"

if (( feature_mode )) && [[ "$target" != "dev" ]]; then
  die "--feature is only valid with -t dev (test/prod always use the production branch)"
fi

profile="hc-$target"

# ---------------------------------------------------------------------------
# Pre-flight: every tool the rest of the script will call. Fail-fast with a
# specific install hint rather than letting a missing binary deep-fail later.
# ---------------------------------------------------------------------------
step "Pre-flight checks"

command -v databricks >/dev/null \
  || die "databricks CLI not on PATH. Install: https://docs.databricks.com/aws/en/dev-tools/cli/install"
command -v jq >/dev/null \
  || die "jq not on PATH. Install: brew install jq"

if (( ! skip_build )); then
  command -v apx >/dev/null \
    || die "apx not on PATH. Install: curl -fsSL https://databricks-solutions.github.io/apx/install.sh | sh"
  command -v bun >/dev/null \
    || die "bun not on PATH. Install: curl -fsSL https://bun.sh/install | bash"
fi

databricks auth describe -p "$profile" >/dev/null 2>&1 \
  || die "Profile '$profile' missing or invalid. Run: databricks auth login -p $profile"
ok "auth profile '$profile' OK"

[[ -d "$REPO_ROOT/frontend/clinic-sim" ]] \
  || die "frontend/clinic-sim/ not found at $REPO_ROOT — wrong repo?"
[[ -f "$REPO_ROOT/resources/clinic-sim.yml" ]] \
  || die "resources/clinic-sim.yml not found — clinic-sim resource was never wired into the bundle"
ok "repo layout looks right"

# ---------------------------------------------------------------------------
# Resolve --feature variables. We hold off on creating Lakebase branches
# until *after* the build step so a typo in the slug doesn't burn the
# `branch-up.sh` round-trip.
# ---------------------------------------------------------------------------
declare -a passthrough_vars=()
slug=""

if (( feature_mode )); then
  [[ -x "$SLUG_SH" ]] || die "sanitize-branch-slug.sh missing/not executable"
  branch=$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || true)
  [[ -n "$branch" ]] || die "git branch could not be resolved; --feature requires a checked-out branch"
  # sanitize-branch-slug.sh already emits the `feat-`/`hotfix-` prefix
  # (see comments in that script). Passing it through verbatim — prepending
  # another `feat-` would produce `feat-feat-<name>` and break the Lakebase
  # branch lookup (which is created by `lakebase-branch-up.sh` using this
  # same un-prefixed slug).
  slug=$("$SLUG_SH" "$branch")
  [[ -n "$slug" ]] || die "branch slug came back empty (branch was '$branch')"
  passthrough_vars+=(
    --var "app_name_suffix=-$slug"
    --var "lakebase_branch=$slug"
  )
  ok "feature mode → app_name_suffix=-$slug, lakebase_branch=$slug"
fi

# Final app name as it will appear in the workspace — used both for the URL
# resolution at the end AND for the dependency check below.
app_name="clinic-sim"
if (( feature_mode )); then
  app_name="clinic-sim-$slug"
fi

# ---------------------------------------------------------------------------
# Pre-flight: every backend app must already exist in the target workspace.
# The simulator's BFF has no useful behavior without all six. We use
# `databricks apps get <name> -o json` and tolerate the trunk vs feature
# naming difference.
# ---------------------------------------------------------------------------
step "Checking that every backend app already exists in '$target'"

backend_suffix=""
(( feature_mode )) && backend_suffix="-$slug"

missing=()
for svc in "${SERVICES[@]}"; do
  name="${svc}${backend_suffix}"
  if databricks apps get "$name" -p "$profile" -o json >/dev/null 2>&1; then
    ok "$name"
  else
    err "$name (not found)"
    missing+=("$name")
  fi
done

if (( ${#missing[@]} > 0 )); then
  echo
  err "Missing backend apps in '$target': ${missing[*]}"
  err "The simulator BFF will return 5xx for every journey until they exist."
  if (( feature_mode )); then
    err "Deploy the full bundle first, e.g.:"
    err "  scripts/deploy-and-run-bundle.sh $target \\"
    err "    --var app_name_suffix=-$slug --var lakebase_branch=$slug"
  else
    err "Deploy the full bundle first:  scripts/deploy-and-run-bundle.sh $target"
  fi
  exit 1
fi

# ---------------------------------------------------------------------------
# --feature: provision the matching Lakebase branch for each service. The
# branch must exist BEFORE `bundle deploy` because the deploy resolves the
# postgres resource against it.
# ---------------------------------------------------------------------------
if (( feature_mode )); then
  step "Ensuring Lakebase feature branches exist ($slug × ${#SERVICES[@]} services)"
  [[ -x "$BRANCH_UP" ]] || die "lakebase-branch-up.sh missing/not executable"
  # lakebase-branch-up.sh signature is `<service> <slug> [profile]`.
  # The script normalizes both bare and prefixed slugs, so $slug
  # (already `feat-...`) goes in verbatim.
  for svc in "${SERVICES[@]}"; do
    if "$BRANCH_UP" "$svc" "$slug" "$profile" >/dev/null 2>&1; then
      ok "$svc → $slug"
    else
      die "$svc → $slug failed (re-run with output: scripts/lakebase-branch-up.sh $svc $slug $profile)"
    fi
  done
fi

# ---------------------------------------------------------------------------
# Build the clinic-sim React bundle. This writes `__dist__/` under
# `src/clinic_sim/`, which is gitignored and only populated by this script
# or by `apx dev`. The bundle's `sync.include` glob force-includes it on
# `bundle deploy`.
# ---------------------------------------------------------------------------
if (( ! skip_build )); then
  step "Building clinic-sim frontend (apx frontend build)"
  (
    cd "$REPO_ROOT/frontend/clinic-sim"
    apx frontend build
  )
  if [[ ! -d "$REPO_ROOT/frontend/clinic-sim/src/clinic_sim/__dist__" ]]; then
    die "apx finished but __dist__/ wasn't produced. Inspect the apx output above."
  fi
  ok "UI built → frontend/clinic-sim/src/clinic_sim/__dist__/"
else
  step "Skipping frontend build (--skip-build)"
  [[ -d "$REPO_ROOT/frontend/clinic-sim/src/clinic_sim/__dist__" ]] \
    || die "--skip-build requested but no __dist__/ exists yet. Run once without --skip-build."
fi

# ---------------------------------------------------------------------------
# `bundle deploy -t <target>`. We deploy the FULL bundle, not just the
# clinic-sim resource — `databricks bundle deploy` doesn't support filtering
# to a single app, and partial deploys would leave bundle state out-of-sync
# anyway. This is safe because the rest of the bundle is idempotent.
# ---------------------------------------------------------------------------
if (( ! skip_deploy )); then
  step "databricks bundle deploy -t $target (full bundle, idempotent)"
  (
    cd "$REPO_ROOT"
    databricks bundle deploy -t "$target" -p "$profile" "${passthrough_vars[@]}"
  )
  ok "bundle deployed"
else
  step "Skipping bundle deploy (--skip-deploy)"
fi

# ---------------------------------------------------------------------------
# `bundle run <APP_KEY>` — this is the verb that actually flips the app from
# UNAVAILABLE → ACTIVE by submitting a new app deployment from the synced
# source. Without `--no-wait` it blocks until the app reports ACTIVE.
# ---------------------------------------------------------------------------
declare -a run_flags=()
(( no_wait )) && run_flags+=(--no-wait)
(( restart )) && run_flags+=(--restart)

step "databricks bundle run $APP_KEY (-t $target)"
(
  cd "$REPO_ROOT"
  databricks bundle run -t "$target" -p "$profile" \
    "${run_flags[@]}" "${passthrough_vars[@]}" "$APP_KEY"
)
ok "clinic-sim app is live"

# ---------------------------------------------------------------------------
# Resolve and print the canonical app URL. The platform embeds the workspace
# ID in the hostname so the URL can't be constructed client-side.
# `--no-wait` exits before the URL is stable so we skip this step in that
# mode.
# ---------------------------------------------------------------------------
if (( ! no_wait )); then
  step "Resolving canonical URL"
  app_json=$(databricks apps get "$app_name" -p "$profile" -o json 2>/dev/null || true)
  if [[ -z "$app_json" ]]; then
    err "Could not fetch $app_name — the app started but its metadata isn't queryable yet."
  else
    app_url=$(printf '%s' "$app_json" | jq -r '.url // empty')
    app_status=$(printf '%s' "$app_json" | jq -r '.compute_status.state // .status // "?"')
    if [[ -n "$app_url" ]]; then
      log "clinic-sim ($app_status) is live at:"
      printf '  %s\n' "$app_url"
      log "Smoke-test (uses your CLI token as OBO):"
      cat <<EOF
  TOKEN=\$(databricks auth token -p $profile | jq -r .access_token)
  curl -fsS -H "Authorization: Bearer \$TOKEN" "$app_url/api/sim/healthz"
  curl -fsS -H "Authorization: Bearer \$TOKEN" "$app_url/api/sim/stream?count=3"

EOF
    else
      err "App responded but didn't expose a .url field. Try: databricks apps get $app_name -p $profile"
    fi
  fi
fi

log "Done."
