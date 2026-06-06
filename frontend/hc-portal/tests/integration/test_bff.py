"""Integration tests for hc-portal — run against deployed preview apps.

Skipped when env vars aren't set (see conftest.py). The bff-pattern skill
requires that fan-out latency stays close to `max(per-call)`, not the sum.
"""
from __future__ import annotations

import time

import httpx
import pytest


@pytest.mark.integration
async def test_healthz(bff_base_url: str):
    async with httpx.AsyncClient(base_url=bff_base_url) as c:
        r = await c.get("/api/bff/healthz")
        assert r.status_code == 200
        assert r.json() == {"ok": True}


@pytest.mark.integration
async def test_patient_summary_concurrent(
    bff_base_url: str, user_one_token: str, sample_patient_id: str
):
    t0 = time.monotonic()
    async with httpx.AsyncClient(base_url=bff_base_url, timeout=10.0) as c:
        r = await c.get(
            f"/api/bff/patient-summary/{sample_patient_id}",
            headers={"X-Forwarded-Access-Token": user_one_token},
        )
    elapsed = time.monotonic() - t0
    assert r.status_code == 200
    body = r.json()
    assert body["patient"]["id"] == sample_patient_id
    # Concurrent fan-out: 5 services, conservatively under 6s end-to-end.
    assert elapsed < 6.0, f"BFF took {elapsed:.1f}s — fan-out is probably sequential"


@pytest.mark.integration
async def test_unauthenticated_request_is_rejected(bff_base_url: str):
    async with httpx.AsyncClient(base_url=bff_base_url) as c:
        # Hit the BFF with no token at all
        r = await c.get("/api/bff/patients")
        # Either 401 from our auth.py, or 403 from Databricks Apps' own auth
        # gate — both are valid "not authenticated" outcomes.
        assert r.status_code in (401, 403)
