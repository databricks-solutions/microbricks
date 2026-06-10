#!/usr/bin/env bash
#
# Derive an e2e slug from a git ref name.
#
# Usage:
#   ./scripts/compute-e2e-slug.sh <ref>
#
# Examples:
#   release/1.2.0 → e2e-1-2-0
#   v1.2.0        → e2e-v1-2-0
#   main          → e2e-main
set -euo pipefail

input="${1:-}"
[[ -n "$input" ]] || { echo "usage: $0 <ref>" >&2; exit 2; }

slug=$(printf '%s' "$input" \
  | sed -E 's|^refs/tags/||; s|^refs/heads/||; s|^release/||' \
  | tr '[:upper:]' '[:lower:]' \
  | sed -E 's|[/_. ]+|-|g; s|[^a-z0-9-]||g; s|^-+||; s|-+$||')

printf 'e2e-%s\n' "$slug"
