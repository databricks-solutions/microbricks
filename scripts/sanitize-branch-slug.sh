#!/usr/bin/env bash
#
# Code-branch -> sanitized slug transform.
#
# NOTE: PR workflows now use `pr-<number>` as the slug (computed directly in
# the workflow YAML), which is always short enough for the 30-char app-name
# limit. This script is retained for local/manual use and the orphan-cleanup
# fallback, but is NO LONGER the canonical slug source for CI.
#
# Constraints:
#   - Databricks App names are capped at 30 chars total. The longest app
#     prefix is `microbricks-deck-` (17 chars including the dash), so slugs
#     must be ≤13 chars. The `pr-<number>` format (e.g. `pr-21` = 5 chars)
#     always satisfies this.
#   - Lakebase resource IDs are 3-63 chars — not the binding constraint.
#   - Charset: lowercase letters, digits, dashes; must not start/end with dash.
#
# Inputs accepted as $1 OR on stdin.
# Examples (cap=13):
#   feature/HC-123-add-allergies     -> feat-hc-123-a  (truncated)
#   hotfix/HC-456-rounding           -> hotfix-hc-456  (truncated)
#   feature/HC-99                    -> feat-hc-99     (fits)
#   dev                              -> feat-dev       (bare branch)
set -euo pipefail

input="${1:-$(cat)}"

if [[ -z "${input:-}" ]]; then
  echo "usage: $0 <branch-name>   (or pipe the branch name on stdin)" >&2
  exit 2
fi

# Hard cap derived from `microbricks-deck-` (17 chars) + slug = ≤30 (Apps limit).
SLUG_MAX=13

# Step 1: lowercase, map conventional prefixes, and clean the charset. We do
# NOT truncate yet — the prefix must be applied to the un-truncated body so
# that the 17-char budget includes it.
slug="$(printf '%s' "$input" \
  | tr '[:upper:]' '[:lower:]' \
  | sed -E 's|^feature/|feat-|; s|^hotfix/|hotfix-|' \
  | sed -E 's|[/_]+|-|g; s|[^a-z0-9-]||g; s|^-+||; s|-+$||')"

# Step 2: enforce the `feat-`/`hotfix-` prefix contract. Any branch that
# didn't match `feature/...` or `hotfix/...` at step 1 (e.g. `dev`,
# `release/1.0`, a bare topic branch) is defaulted to `feat-` so every
# downstream consumer sees the same prefixed slug.
case "$slug" in
  feat-*|hotfix-*) ;;
  *) slug="feat-$slug" ;;
esac

# Step 3: now truncate the prefixed slug to the App-name budget and strip
# any trailing dash the cut may have left behind.
slug="$(printf '%s' "$slug" | cut -c"1-$SLUG_MAX" | sed -E 's|-+$||')"

if [[ -z "$slug" ]]; then
  echo "error: branch '$input' produced an empty slug" >&2
  exit 1
fi

printf '%s\n' "$slug"
