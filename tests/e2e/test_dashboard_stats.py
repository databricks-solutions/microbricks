"""E2E: Dashboard stats correctness via GraphQL."""
from __future__ import annotations

import uuid

import httpx
import pytest

pytestmark = pytest.mark.e2e

DASHBOARD_STATS_QUERY = """
    query {
        dashboardStats {
            totalPatients
            totalAppointments
            totalProviders
            totalPrescriptions
            totalLabOrders
            totalInvoices
            partial
        }
    }
"""


async def test_dashboard_stats_structure(bff_client: httpx.AsyncClient):
    r = await bff_client.post("/api/graphql", json={"query": DASHBOARD_STATS_QUERY})
    assert r.status_code == 200
    body = r.json()
    assert "errors" not in body, f"GraphQL errors: {body.get('errors')}"
    stats = body["data"]["dashboardStats"]

    assert "totalPatients" in stats
    assert "totalAppointments" in stats
    assert isinstance(stats["totalPatients"], int)
    assert isinstance(stats["totalAppointments"], int)
    assert stats["totalPatients"] >= 0
    assert stats["totalAppointments"] >= 0


async def test_dashboard_stats_increment_after_create(
    patient_svc_client: httpx.AsyncClient,
    bff_client: httpx.AsyncClient,
):
    # Baseline
    r = await bff_client.post("/api/graphql", json={"query": DASHBOARD_STATS_QUERY})
    assert r.status_code == 200
    body = r.json()
    assert "errors" not in body, f"GraphQL errors: {body.get('errors')}"
    stats = body["data"]["dashboardStats"]
    if stats.get("partial"):
        pytest.skip("Dashboard reports partial data — services not fully connected")
    before = stats["totalPatients"]

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
    r = await bff_client.post("/api/graphql", json={"query": DASHBOARD_STATS_QUERY})
    assert r.status_code == 200
    after = r.json()["data"]["dashboardStats"]["totalPatients"]

    assert after == before + 1
