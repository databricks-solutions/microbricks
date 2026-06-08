"""Test fixtures for hc-portal.

Unit tests stub the downstream services with `respx`. Integration tests
require deployed preview apps and a token; they're skipped automatically
when the env vars aren't set.
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _stub_svc_env(monkeypatch):
    """Stub the BFF's runtime env so `clients/_base.py:_resolve_base_url`
    can compose `https://<svc>-<workspace_suffix>` without a real Apps
    deploy. `respx` intercepts at the httpx transport layer, so the actual
    host is irrelevant — the URL just has to parse.

    `_own_app_suffix()` is `lru_cache`d: clear the cache so each test
    starts from this stub rather than a previous test's value."""
    from hc_portal.clients import _base as _base_mod

    _base_mod._own_app_suffix.cache_clear()
    monkeypatch.setenv(
        "DATABRICKS_APP_URL",
        "https://hc-portal-1234567890.test.databricksapps.com",
    )
    monkeypatch.setenv("DATABRICKS_WORKSPACE_ID", "1234567890")
    yield
    _base_mod._own_app_suffix.cache_clear()


# --- Integration fixtures (skip cleanly when not configured) ---


@pytest.fixture(scope="session")
def bff_base_url() -> str:
    url = os.environ.get("BFF_BASE_URL")
    if not url:
        pytest.skip("BFF_BASE_URL not set; integration tests skipped")
    return url


@pytest.fixture(scope="session")
def user_one_token() -> str:
    tok = os.environ.get("USER_ONE_TOKEN")
    if not tok:
        pytest.skip("USER_ONE_TOKEN not set; integration tests skipped")
    return tok


@pytest.fixture(scope="session")
def sample_patient_id() -> str:
    pid = os.environ.get("SAMPLE_PATIENT_ID")
    if not pid:
        pytest.skip("SAMPLE_PATIENT_ID not set; integration tests skipped")
    return pid
