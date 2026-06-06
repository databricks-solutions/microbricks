"""Unit tests for `clients/_base.py:_resolve_base_url`.

The BFF resolves downstream URLs in two ways:

  1. Explicit `<SVC>_SVC_URL` env override (highest priority).
  2. Runtime composition from `DATABRICKS_APP_URL` + service slug.

Override is the contract the bundle / app.yml use when a downstream lives
somewhere non-canonical (PR preview, local dev, cross-region).
"""
from __future__ import annotations

import pytest

from hc_portal.clients import _base


@pytest.fixture(autouse=True)
def _clear_cache():
    _base._own_app_suffix.cache_clear()
    yield
    _base._own_app_suffix.cache_clear()


def test_default_runtime_derivation_uses_app_url(monkeypatch):
    monkeypatch.setenv(
        "DATABRICKS_APP_URL",
        "https://hc-portal-dev-7474643727449861.aws.databricksapps.com",
    )
    monkeypatch.delenv("PATIENT_SVC_URL", raising=False)

    assert _base._resolve_base_url("patient") == (
        "https://patient-dev-7474643727449861.aws.databricksapps.com"
    )


def test_explicit_override_beats_runtime_derivation(monkeypatch):
    monkeypatch.setenv(
        "DATABRICKS_APP_URL",
        "https://hc-portal-dev-7474643727449861.aws.databricksapps.com",
    )
    monkeypatch.setenv(
        "PATIENT_SVC_URL", "https://patient-pr-1234.previews.example"
    )

    assert (
        _base._resolve_base_url("patient")
        == "https://patient-pr-1234.previews.example"
    )


def test_override_for_one_service_does_not_affect_others(monkeypatch):
    monkeypatch.setenv(
        "DATABRICKS_APP_URL",
        "https://hc-portal-dev-7474643727449861.aws.databricksapps.com",
    )
    monkeypatch.setenv("PATIENT_SVC_URL", "http://localhost:8001")
    monkeypatch.delenv("PROVIDER_SVC_URL", raising=False)

    assert _base._resolve_base_url("patient") == "http://localhost:8001"
    assert _base._resolve_base_url("provider") == (
        "https://provider-dev-7474643727449861.aws.databricksapps.com"
    )


def test_runtime_derivation_rejects_unexpected_app_prefix(monkeypatch):
    monkeypatch.setenv(
        "DATABRICKS_APP_URL",
        "https://some-other-app-7474643727449861.aws.databricksapps.com",
    )
    monkeypatch.delenv("PATIENT_SVC_URL", raising=False)

    with pytest.raises(RuntimeError, match="hc-portal-"):
        _base._resolve_base_url("patient")
