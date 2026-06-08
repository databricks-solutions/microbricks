#!/usr/bin/env bash
#
# Canonical code-branch -> Lakebase-/preview-slug transform.
#
# Constraints from the two consumers:
#   - Databricks App names are capped at 30 chars total. App names follow
#     `<svc>[-<slug>]` (no `<target>` segment — see databricks.yml). The
#     longest service prefix is `prescription-` (13 chars including the
#     separator dash), so the slug must be ≤17 chars to keep the resulting
#     `<svc>-<slug>` ≤30.
#   - Lakebase resource IDs are 3-63 chars. The same slug is used for the
#     Lakebase branch name, but that's the looser constraint — bundling at
#     17 here also keeps Lakebase happy.
#   - Charset for both: lowercase letters, digits, dashes; must not start
#     or end with a dash.
#
# Output already includes the `feat-` (5 char) or `hotfix-` (7 char) prefix.
# Available characters for the user-meaningful tail: 17 - 5 = 12 chars after
# `feat-`, or 17 - 7 = 10 chars after `hotfix-`. Comfortably enough for a
# ticket id + a short hint like "hc-123-skew".
#
# Inputs accepted as $1 OR on stdin (the workflows pass $GITHUB_HEAD_REF as $1).
# Examples (cap=17):
#   feature/HC-123-add-allergies     -> feat-hc-123-add-a  (truncated)
#   hotfix/HC-456-rounding           -> hotfix-hc-456-rou  (truncated)
#   feature/HC-99                    -> feat-hc-99         (10 chars, fits)
#
# This is the single source of truth — the .github workflows and the
# `hc-lakebase-branching` skill both reference this exact transform. If you
# change the rules, update both places.
set -euo pipefail

input="${1:-$(cat)}"

if [[ -z "${input:-}" ]]; then
  echo "usage: $0 <branch-name>   (or pipe the branch name on stdin)" >&2
  exit 2
fi

# Hard cap derived from `prescription-` (13 chars) + slug = ≤30 (Apps limit).
SLUG_MAX=17

slug="$(printf '%s' "$input" \
  | tr '[:upper:]' '[:lower:]' \
  | sed -E 's|^feature/|feat-|; s|^hotfix/|hotfix-|' \
  | sed -E 's|[/_]+|-|g; s|[^a-z0-9-]||g; s|^-+||; s|-+$||' \
  | cut -c"1-$SLUG_MAX" \
  | sed -E 's|-+$||')"

if [[ -z "$slug" ]]; then
  echo "error: branch '$input' produced an empty slug" >&2
  exit 1
fi

printf '%s\n' "$slug"
