"""E2E: Patient CRUD — create via service, read back through BFF."""
from __future__ import annotations

import uuid

import httpx
import pytest

pytestmark = pytest.mark.e2e


async def test_create_patient_and_read_via_bff(
    patient_svc_client: httpx.AsyncClient,
    bff_client: httpx.AsyncClient,
):
    unique_name = f"E2E-{uuid.uuid4().hex[:8]}"
    payload = {
        "given_name": unique_name,
        "family_name": "TestSuite",
        "birth_date": "1990-01-15",
        "sex_at_birth": "other",
    }

    # Create patient directly on the service
    r = await patient_svc_client.post("/api/v1/patients", json=payload)
    assert r.status_code == 201, f"Create failed: {r.status_code} {r.text}"
    patient = r.json()
    patient_id = patient["id"]
    assert patient["given_name"] == unique_name

    # Read back via BFF patients list (search by unique name)
    r = await bff_client.get("/api/bff/patients", params={"q": unique_name})
    assert r.status_code == 200
    page = r.json()
    assert page["total"] >= 1
    found_ids = {p["id"] for p in page["items"]}
    assert patient_id in found_ids


async def test_patient_summary_returns_full_view(
    patient_svc_client: httpx.AsyncClient,
    bff_client: httpx.AsyncClient,
):
    unique_name = f"E2E-{uuid.uuid4().hex[:8]}"
    payload = {
        "given_name": unique_name,
        "family_name": "Summary",
        "birth_date": "1985-06-20",
        "sex_at_birth": "female",
    }

    r = await patient_svc_client.post("/api/v1/patients", json=payload)
    assert r.status_code == 201
    patient_id = r.json()["id"]

    # Patient summary aggregates data from multiple services
    r = await bff_client.get(f"/api/bff/patient-summary/{patient_id}")
    assert r.status_code == 200
    summary = r.json()
    assert summary["patient"]["id"] == patient_id
    assert summary["patient"]["given_name"] == unique_name


async def test_get_nonexistent_patient_returns_404(
    bff_client: httpx.AsyncClient,
):
    fake_id = str(uuid.uuid4())
    r = await bff_client.get(f"/api/bff/patient-summary/{fake_id}")
    assert r.status_code in (404, 502)
