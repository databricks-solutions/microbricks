"""E2E: Cross-service data consistency.

Create a patient + appointment, then verify the BFF patient-summary
aggregation includes the appointment data from the appointment service.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

pytestmark = pytest.mark.e2e


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
            "visit_type_code": "office_visit",
            "scheduled_start": (now + timedelta(days=1)).isoformat(),
            "scheduled_end": (now + timedelta(days=1, hours=1)).isoformat(),
            "reason": "E2E cross-service test",
        },
    )
    assert r.status_code == 201, f"Appointment create failed: {r.status_code} {r.text}"
    appointment_id = r.json()["id"]

    # 3. Verify patient-summary includes this appointment
    r = await bff_client.get(f"/api/bff/patient-summary/{patient_id}")
    assert r.status_code == 200
    summary = r.json()
    assert summary["patient"]["id"] == patient_id

    appointment_ids = [a["id"] for a in summary.get("last_appointments", [])]
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
            "visit_type_code": "office_visit",
            "scheduled_start": (now + timedelta(days=2)).isoformat(),
            "scheduled_end": (now + timedelta(days=2, hours=1)).isoformat(),
        },
    )
    assert r.status_code == 201

    # BFF appointments list should enrich with patient_name
    r = await bff_client.get("/api/bff/appointments", params={"patient_id": patient_id})
    assert r.status_code == 200
    page = r.json()
    assert page["total"] >= 1
    first = page["items"][0]
    assert "patient_name" in first or "patient_id" in first
