"""E2E: Patient CRUD — create via service, read back through BFF GraphQL."""
from __future__ import annotations

import uuid

import httpx
import pytest

pytestmark = pytest.mark.e2e

PATIENTS_SEARCH_QUERY = """
    query Patients($q: String!, $limit: Int!, $offset: Int!) {
        patients(q: $q, limit: $limit, offset: $offset) {
            items { id givenName familyName }
            total
        }
    }
"""

PATIENT_SUMMARY_QUERY = """
    query PatientSummary($id: UUID!) {
        patientSummary(id: $id) {
            patient { id givenName familyName }
            lastAppointments { id }
            activePrescriptions { id }
            recentLabOrders { id }
            outstandingInvoices { id }
            partial
        }
    }
"""


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

    # Read back via BFF GraphQL patients query (search by unique name)
    r = await bff_client.post(
        "/api/graphql",
        json={
            "query": PATIENTS_SEARCH_QUERY,
            "variables": {"q": unique_name, "limit": 10, "offset": 0},
        },
    )
    assert r.status_code == 200, f"BFF GraphQL failed: {r.status_code} {r.text}"
    body = r.json()
    assert "errors" not in body, f"GraphQL errors: {body.get('errors')}"
    page = body["data"]["patients"]
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

    # Patient summary via GraphQL
    r = await bff_client.post(
        "/api/graphql",
        json={"query": PATIENT_SUMMARY_QUERY, "variables": {"id": patient_id}},
    )
    assert r.status_code == 200
    body = r.json()
    assert "errors" not in body, f"GraphQL errors: {body.get('errors')}"
    summary = body["data"]["patientSummary"]
    assert summary["patient"]["id"] == patient_id
    assert summary["patient"]["givenName"] == unique_name


async def test_get_nonexistent_patient_returns_null(
    bff_client: httpx.AsyncClient,
):
    fake_id = str(uuid.uuid4())
    r = await bff_client.post(
        "/api/graphql",
        json={"query": PATIENT_SUMMARY_QUERY, "variables": {"id": fake_id}},
    )
    assert r.status_code == 200
    body = r.json()
    # GraphQL may return data=null with errors, or a null patient inside the summary
    data = body.get("data")
    if data is None:
        assert "errors" in body
    else:
        summary = data.get("patientSummary")
        if summary is not None:
            assert summary["patient"] is None
