"""E2E: Cross-service data consistency.

Create a patient + appointment, then verify the BFF patient-summary
aggregation includes the appointment data from the appointment service.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from tests.e2e.conftest import VISIT_TYPE_CODE

pytestmark = pytest.mark.e2e

PATIENT_SUMMARY_QUERY = """
    query PatientSummary($id: UUID!) {
        patientSummary(id: $id) {
            patient { id givenName familyName }
            lastAppointments { id }
            partial
        }
    }
"""

APPOINTMENTS_QUERY = """
    query Appointments($patientId: UUID, $limit: Int!, $offset: Int!) {
        appointments(patientId: $patientId, limit: $limit, offset: $offset) {
            items {
                id
                patient { givenName familyName }
            }
            total
        }
    }
"""


def _check_appointment_response(r: httpx.Response) -> None:
    """Skip test if appointment service DB isn't seeded with visit types."""
    if r.status_code == 422 and "visit_type_code" in r.text:
        pytest.skip("Appointment service visit_type table not seeded")


async def test_appointment_appears_in_patient_summary(
    patient_svc_client: httpx.AsyncClient,
    appointment_svc_client: httpx.AsyncClient,
    bff_client: httpx.AsyncClient,
):
    # 1. Create a patient
    unique_name = f"E2E-Cross-{uuid.uuid4().hex[:8]}"
    r = await patient_svc_client.post(
        "/api/v1/patients",
        json={
            "given_name": unique_name,
            "family_name": "CrossSvc",
            "birth_date": "1975-11-30",
            "sex_at_birth": "male",
        },
    )
    assert r.status_code == 201
    patient_id = r.json()["id"]

    # 2. Create an appointment for this patient
    now = datetime.now(timezone.utc)
    r = await appointment_svc_client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "provider_id": str(uuid.uuid4()),
            "visit_type_code": VISIT_TYPE_CODE,
            "scheduled_start": (now + timedelta(days=1)).isoformat(),
            "scheduled_end": (now + timedelta(days=1, hours=1)).isoformat(),
            "reason": "E2E cross-service test",
        },
    )
    _check_appointment_response(r)
    assert r.status_code == 201, f"Appointment create failed: {r.status_code} {r.text}"
    appointment_id = r.json()["id"]

    # 3. Verify patient-summary includes this appointment
    r = await bff_client.post(
        "/api/graphql",
        json={"query": PATIENT_SUMMARY_QUERY, "variables": {"id": patient_id}},
    )
    assert r.status_code == 200
    body = r.json()
    assert "errors" not in body, f"GraphQL errors: {body.get('errors')}"
    summary = body["data"]["patientSummary"]
    assert summary["patient"]["id"] == patient_id

    appointment_ids = [a["id"] for a in summary.get("lastAppointments", [])]
    assert appointment_id in appointment_ids, (
        f"Appointment {appointment_id} not found in patient-summary. "
        f"Got: {appointment_ids}"
    )


async def test_appointment_list_enriches_patient_name(
    patient_svc_client: httpx.AsyncClient,
    appointment_svc_client: httpx.AsyncClient,
    bff_client: httpx.AsyncClient,
):
    # Create a patient with a recognizable name
    unique_name = f"E2E-Enrich-{uuid.uuid4().hex[:8]}"
    r = await patient_svc_client.post(
        "/api/v1/patients",
        json={
            "given_name": unique_name,
            "family_name": "EnrichTest",
            "birth_date": "2000-01-01",
            "sex_at_birth": "female",
        },
    )
    assert r.status_code == 201
    patient_id = r.json()["id"]

    # Create an appointment
    now = datetime.now(timezone.utc)
    r = await appointment_svc_client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "provider_id": str(uuid.uuid4()),
            "visit_type_code": VISIT_TYPE_CODE,
            "scheduled_start": (now + timedelta(days=2)).isoformat(),
            "scheduled_end": (now + timedelta(days=2, hours=1)).isoformat(),
        },
    )
    _check_appointment_response(r)
    assert r.status_code == 201

    # BFF appointments query should resolve nested patient name
    r = await bff_client.post(
        "/api/graphql",
        json={
            "query": APPOINTMENTS_QUERY,
            "variables": {"patientId": patient_id, "limit": 10, "offset": 0},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "errors" not in body, f"GraphQL errors: {body.get('errors')}"
    page = body["data"]["appointments"]
    assert page["total"] >= 1
    first = page["items"][0]
    assert first["patient"]["givenName"] == unique_name
    assert first["patient"]["familyName"] == "EnrichTest"
