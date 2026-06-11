"""E2E: Dashboard stats correctness."""
from __future__ import annotations

import uuid

import httpx
import pytest

pytestmark = pytest.mark.e2e


async def test_dashboard_stats_structure(bff_client: httpx.AsyncClient):
    r = await bff_client.get("/api/bff/dashboard-stats")
    assert r.status_code == 200
    stats = r.json()

    assert "total_patients" in stats
    assert "total_appointments" in stats
    assert isinstance(stats["total_patients"], int)
    assert isinstance(stats["total_appointments"], int)
    assert stats["total_patients"] >= 0
    assert stats["total_appointments"] >= 0


async def test_dashboard_stats_increment_after_create(
    patient_svc_client: httpx.AsyncClient,
    bff_client: httpx.AsyncClient,
):
    # Baseline
    r = await bff_client.get("/api/bff/dashboard-stats")
    assert r.status_code == 200
    stats = r.json()
    if stats.get("partial"):
        pytest.skip("Dashboard reports partial data — services not fully connected")
    before = stats["total_patients"]

    # Create a patient
    r = await patient_svc_client.post(
        "/api/v1/patients",
        json={
            "given_name": f"E2E-Stats-{uuid.uuid4().hex[:8]}",
            "family_name": "StatsTest",
            "birth_date": "1992-04-10",
            "sex_at_birth": "unknown",
        },
    )
    assert r.status_code == 201, f"Create failed: {r.status_code} {r.text}"

    # After
    r = await bff_client.get("/api/bff/dashboard-stats")
    assert r.status_code == 200
    after = r.json()["total_patients"]

    assert after == before + 1
