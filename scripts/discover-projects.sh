#!/usr/bin/env bash
#
# discover-projects.sh — enumerate services and frontends from the filesystem.
#
# Scans `services/*/` and `frontend/*/` for projects containing a
# `pyproject.toml` with `[tool.apx.metadata]`. Outputs structured JSON
# suitable for GH Actions matrices and bash loops.
#
# Modes:
#   (default)        → JSON object to stdout (see below)
#   --path-filters   → YAML for dorny/paths-filter to stdout
#   --service-dirs   → newline-separated service directory names
#   --frontend-dirs  → newline-separated frontend directory names
#   --bundle-keys    → newline-separated bundle resource keys
#   --app-names      → newline-separated app names (as deployed)
#
# JSON output shape:
#   {
#     "services": [{"dir","app_name","app_slug","bundle_key","healthz"},...],
#     "frontends": [{"dir","app_name","app_slug","bundle_key","healthz"},...],
#     "service_dirs": ["patient",...],
#     "frontend_dirs": ["hc-portal",...],
#     "all_bundle_keys": ["patient_app",...,"hc_portal_app",...],
#     "all_app_names": ["patient",...,"hc-portal",...]
#   }
#
# Prereqs: python3 (>= 3.11, for tomllib)
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/.." &>/dev/null && pwd)

MODE="${1:-json}"

exec python3 - "$MODE" "$REPO_ROOT" <<'PYTHON'
import json
import sys
import os
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

mode = sys.argv[1]
repo_root = Path(sys.argv[2])


def read_apx_metadata(pyproject_path: Path) -> dict | None:
    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        meta = data.get("tool", {}).get("apx", {}).get("metadata", {})
        if not meta.get("app-name"):
            return None
        return meta
    except Exception:
        return None


def discover_projects(base_dir: Path, project_type: str) -> list[dict]:
    projects = []
    if not base_dir.is_dir():
        return projects
    for child in sorted(base_dir.iterdir()):
        if not child.is_dir():
            continue
        pyproject = child / "pyproject.toml"
        if not pyproject.exists():
            continue
        meta = read_apx_metadata(pyproject)
        if meta is None:
            continue
        app_name = meta["app-name"]
        app_slug = meta.get("app-slug", app_name.replace("-", "_"))
        api_prefix = meta.get("api-prefix", "/api/v1")
        bundle_key = app_slug.replace("-", "_") + "_app"

        if "healthz" in meta:
            healthz = meta["healthz"]
        elif project_type == "service":
            healthz = f"{api_prefix}/healthz"
        else:
            healthz = f"{api_prefix}/bff/healthz"

        projects.append({
            "dir": child.name,
            "app_name": app_name,
            "app_slug": app_slug,
            "bundle_key": bundle_key,
            "healthz": healthz,
        })
    return projects


services = discover_projects(repo_root / "services", "service")
frontends = discover_projects(repo_root / "frontend", "frontend")

if mode == "--path-filters":
    lines = []
    lines.append("services:")
    lines.append("  - 'services/**'")
    for svc in services:
        lines.append(f"{svc['dir']}: 'services/{svc['dir']}/**'")
    lines.append("frontends:")
    lines.append("  - 'frontend/**'")
    for fe in frontends:
        lines.append(f"{fe['dir']}: 'frontend/{fe['dir']}/**'")
    lines.append("infra:")
    lines.append("  - 'databricks.yml'")
    lines.append("  - 'resources/**'")
    lines.append("  - 'scripts/**'")
    lines.append("  - '.github/workflows/**'")
    print("\n".join(lines))
elif mode == "--service-dirs":
    for svc in services:
        print(svc["dir"])
elif mode == "--frontend-dirs":
    for fe in frontends:
        print(fe["dir"])
elif mode == "--bundle-keys":
    for p in services + frontends:
        print(p["bundle_key"])
elif mode == "--app-names":
    for p in services + frontends:
        print(p["app_name"])
else:
    output = {
        "services": services,
        "frontends": frontends,
        "service_dirs": [s["dir"] for s in services],
        "frontend_dirs": [f["dir"] for f in frontends],
        "all_bundle_keys": [p["bundle_key"] for p in services + frontends],
        "all_app_names": [p["app_name"] for p in services + frontends],
    }
    json.dump(output, sys.stdout, indent=2)
    print()
PYTHON
