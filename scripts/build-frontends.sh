#!/usr/bin/env bash
#
# build-frontends.sh — build the React UI of every apx project under `frontend/`.
#
# An apx project is detected by having BOTH `pyproject.toml` and `package.json`
# at the root of `frontend/<name>/`. That's the canonical apx layout (Python
# BFF + React UI) — see `frontend/hc-portal/` for the reference shape.
# Anything else under `frontend/` (loose docs, future non-apx static sites,
# `.gitkeep`, etc.) is skipped, so adding a sibling apx project is a pure
# `frontend/<new>/` directory drop with no edits to this script or to the
# four `.github/workflows/*.yml` callers.
#
# `apx frontend build` runs vite under the hood (config implied by
# `[tool.apx.ui]` in each project's pyproject.toml) and writes to
# `src/<package_slug>/__dist__/` — gitignored, so it's only ever populated
# by THIS script (CI before `bundle deploy`) or by a developer's local
# `apx build` / `apx dev`. The bundle itself force-includes the dist
# folders via `sync.include` in `databricks.yml` — see that file for the
# matching glob pattern.
#
# Prereqs:
#   - `apx` on PATH (https://databricks-solutions.github.io/apx/install.sh)
#   - `bun` on PATH (apx delegates JS install + vite invocation to it)
#
# Idempotent — re-running rebuilds in place. Safe to call from CI and from
# `scripts/ci-local.sh`.
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/.." &>/dev/null && pwd)

cd "$REPO_ROOT"

if [[ ! -d frontend ]]; then
  echo "No frontend/ directory at $REPO_ROOT — nothing to build."
  exit 0
fi

# Hard prereq checks. Failing here with a clear message is much friendlier
# than letting `apx frontend build` deep-stack-trace on a missing tool.
command -v apx >/dev/null \
  || { echo "error: apx not on PATH. Install: curl -fsSL https://databricks-solutions.github.io/apx/install.sh | sh" >&2; exit 1; }
command -v bun >/dev/null \
  || { echo "error: bun not on PATH. Install: curl -fsSL https://bun.sh/install | bash" >&2; exit 1; }

shopt -s nullglob
PROJECTS=()
for dir in frontend/*/; do
  proj="${dir%/}"
  # Both files = apx project. Either alone = something else (e.g. a
  # backend-only colocated package, a docs site, a placeholder dir).
  if [[ -f "$proj/pyproject.toml" && -f "$proj/package.json" ]]; then
    PROJECTS+=("$proj")
  fi
done

if (( ${#PROJECTS[@]} == 0 )); then
  echo "No apx projects found under frontend/ — nothing to build."
  exit 0
fi

echo "Found ${#PROJECTS[@]} apx project(s) to build:"
printf '  - %s\n' "${PROJECTS[@]}"

LOG_DIR=$(mktemp -d)
PIDS=()

for proj in "${PROJECTS[@]}"; do
  echo "▶ Building UI for $proj (background)"
  (
    cd "$proj" && bun install --frozen-lockfile && apx frontend build
  ) > "$LOG_DIR/${proj##*/}.log" 2>&1 &
  PIDS+=("$!")
done

FAIL=0
for i in "${!PROJECTS[@]}"; do
  proj="${PROJECTS[$i]}"
  pid="${PIDS[$i]}"
  if wait "$pid"; then
    echo "  ✓ $proj"
  else
    echo "  ✗ $proj failed" >&2
    cat "$LOG_DIR/${proj##*/}.log" >&2
    FAIL=1
  fi
done

rm -rf "$LOG_DIR"

if (( FAIL != 0 )); then
  echo
  echo "::error::one or more frontend builds failed" >&2
  exit 1
fi

echo
echo "All frontend UIs built."
