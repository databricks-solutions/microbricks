#!/usr/bin/env bash
#
# Canonical code-branch -> Lakebase-/preview-slug transform.
#
# Constraints from the two consumers:
#   - Databricks App names are capped at 30 chars total. With the longest
#     service prefix (`prescription-dev-` = 17 chars), the slug must be ≤13
#     chars to keep the resulting `<svc>-<target>-<slug>` ≤30.
#   - Lakebase resource IDs are 3-63 chars. The same slug is used for the
#     Lakebase branch name, but that's the looser constraint — bundling at
#     13 here also keeps Lakebase happy.
#   - Charset for both: lowercase letters, digits, dashes; must not start
#     or end with a dash.
#
# Output already includes the `feat-` (5 char) or `hotfix-` (7 char) prefix.
# Available characters for the user-meaningful tail: 13 - 5 = 8 chars after
# `feat-`, or 13 - 7 = 6 chars after `hotfix-`. That's tight but enough for
# a ticket id like "hc-123" (6 chars) or "hc-1234" (7 chars).
#
# Inputs accepted as $1 OR on stdin (the workflows pass $GITHUB_HEAD_REF as $1).
# Examples (cap=13):
#   feature/HC-123-add-allergies     -> feat-hc-123-a    (truncated)
#   hotfix/HC-456-rounding           -> hotfix-hc-456    (truncated, fits)
#   feature/HC-99                    -> feat-hc-99       (10 chars, fits)
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

# Hard cap derived from `prescription-dev-` (17 chars) + slug = ≤30 (Apps limit).
SLUG_MAX=13

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
