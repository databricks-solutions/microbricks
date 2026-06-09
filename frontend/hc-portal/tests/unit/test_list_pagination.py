"""Unit tests for the BFF list-route pagination + search/filter contract.

Pinned behaviour:

  - Every list endpoint accepts `q`, domain filters, `limit`, `offset` and
    returns `{items, total, limit, offset}`.
  - Filter params on the BFF route are forwarded verbatim to the owning
    service (no client-side filter that the user can override).
  - Name joins (patient/provider) are resolved per-page via the `ids` batch
    on patient-svc / provider-svc — we never fetch the whole directory just
    to enrich 50 rows.
  - `patient_q` on a list route resolves to a `patient_id` filter via
    patient-svc; an empty match-set short-circuits to an empty page (no
    downstream call to the primary service).
"""
from __future__ import annotations

import httpx
import respx
from fastapi.testclient import TestClient

from hc_portal.backend.app import app

client = TestClient(app)

_PATIENT_URL = "https://patient-1234567890.test.databricksapps.com/api/v1/patients"
_PROVIDER_URL = "https://provider-1234567890.test.databricksapps.com/api/v1/providers"
_APPOINTMENT_URL = "https://appointment-1234567890.test.databricksapps.com/api/v1/appointments"
_LAB_URL = "https://lab-1234567890.test.databricksapps.com/api/v1/lab-orders"
_BILLING_URL = "https://billing-1234567890.test.databricksapps.com/api/v1/invoices"

_PATIENT_ID = "11111111-1111-1111-1111-111111111111"
_PROVIDER_ID = "22222222-2222-2222-2222-222222222222"


def _page(items: list[dict], total: int | None = None, limit: int = 50, offset: int = 0) -> dict:
    return {
        "items": items,
        "total": total if total is not None else len(items),
        "limit": limit,
        "offset": offset,
    }


def _patient_row() -> dict:
    return {
        "id": _PATIENT_ID,
        "mrn": "MRN-001",
        "given_name": "Ada",
        "family_name": "Lovelace",
        "birth_date": "1815-12-10",
        "sex_at_birth": "F",
    }


def _provider_row() -> dict:
    return {
        "id": _PROVIDER_ID,
        "npi": "1234567890",
        "given_name": "Sarah",
        "family_name": "Lee",
        "credential_suffix": "MD",
        "email": "sarah@example.com",
        "is_active": True,
        "organization_id": "00000000-0000-0000-0000-000000000001",
    }


def _appointment_row() -> dict:
    return {
        "id": "33333333-3333-3333-3333-333333333333",
        "patient_id": _PATIENT_ID,
        "provider_id": _PROVIDER_ID,
        "visit_type_code": "follow-up",
        "scheduled_start": "2026-06-10T10:00:00",
        "scheduled_end": "2026-06-10T10:30:00",
        "status": "booked",
        "reason": "annual",
    }


@respx.mock
def test_patients_list_forwards_search_and_pagination():
    """`q`, `limit`, `offset` all flow from BFF → patient-svc untouched."""
    captured: list[httpx.Request] = []

    def hook(req):
        captured.append(req)
        return httpx.Response(200, json=_page([_patient_row()], total=137, limit=25, offset=50))

    respx.get(_PATIENT_URL).mock(side_effect=hook)

    r = client.get(
        "/api/bff/patients?q=ada&limit=25&offset=50",
        headers={"X-Forwarded-Access-Token": "tok"},
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["items"][0]["mrn"] == "MRN-001"
    assert body["total"] == 137
    assert body["limit"] == 25
    assert body["offset"] == 50

    assert len(captured) == 1
    qs = captured[0].url.params
    assert qs["q"] == "ada"
    assert qs["limit"] == "25"
    assert qs["offset"] == "50"


@respx.mock
def test_patients_list_clamps_limit_to_max_200():
    """Caller-supplied `limit` > 200 is clamped at the BFF, not at the
    user's whim — prevents accidental "give me 1M rows" DOS."""
    respx.get(_PATIENT_URL).mock(
        return_value=httpx.Response(200, json=_page([], total=0, limit=200, offset=0))
    )

    r = client.get(
        "/api/bff/patients?limit=9999",
        headers={"X-Forwarded-Access-Token": "tok"},
    )
    assert r.status_code == 200
    assert r.json()["limit"] == 200


@respx.mock
def test_appointments_list_resolves_names_via_batch_ids_only():
    """The BFF must NOT pull the whole patient/provider directory to enrich
    a page of appointments. Verify the patient & provider calls include an
    `ids` filter scoped to *only* the IDs on this page."""
    appt_capture: list[httpx.Request] = []
    patient_capture: list[httpx.Request] = []
    provider_capture: list[httpx.Request] = []

    def appt_hook(req):
        appt_capture.append(req)
        return httpx.Response(200, json=_page([_appointment_row()], total=1))

    def patient_hook(req):
        patient_capture.append(req)
        return httpx.Response(200, json=_page([_patient_row()]))

    def provider_hook(req):
        provider_capture.append(req)
        return httpx.Response(200, json=_page([_provider_row()]))

    respx.get(_APPOINTMENT_URL).mock(side_effect=appt_hook)
    respx.get(_PATIENT_URL).mock(side_effect=patient_hook)
    respx.get(_PROVIDER_URL).mock(side_effect=provider_hook)

    r = client.get(
        "/api/bff/appointments?limit=50",
        headers={"X-Forwarded-Access-Token": "tok"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items"][0]["patient_name"] == "Ada Lovelace"
    assert body["items"][0]["provider_name"] == "Sarah Lee, MD"

    # Patient + provider calls happened exactly once and were scoped to the
    # IDs on this page (not a full-table sweep).
    assert len(patient_capture) == 1
    p_qs = patient_capture[0].url.params
    assert p_qs.get_list("ids") == [_PATIENT_ID]

    assert len(provider_capture) == 1
    pv_qs = provider_capture[0].url.params
    assert pv_qs.get_list("ids") == [_PROVIDER_ID]


@respx.mock
def test_appointments_status_filter_forwarded_to_service():
    """Domain filters travel verbatim from the BFF to the owning service."""
    captured: list[httpx.Request] = []

    def hook(req):
        captured.append(req)
        return httpx.Response(200, json=_page([], total=0))

    respx.get(_APPOINTMENT_URL).mock(side_effect=hook)

    r = client.get(
        "/api/bff/appointments?status=cancelled&visit_type_code=follow-up",
        headers={"X-Forwarded-Access-Token": "tok"},
    )
    assert r.status_code == 200
    qs = captured[0].url.params
    assert qs["status"] == "cancelled"
    assert qs["visit_type_code"] == "follow-up"


@respx.mock
def test_appointments_patient_q_short_circuits_on_no_match():
    """`patient_q` with zero matches must NOT call appointment-svc at all
    — saves a wasted round-trip and avoids returning a misleading empty
    page that doesn't reflect the user's intent."""
    appt_capture: list[httpx.Request] = []
    respx.get(_PATIENT_URL).mock(
        return_value=httpx.Response(200, json=_page([], total=0))
    )

    def appt_hook(req):
        appt_capture.append(req)
        return httpx.Response(200, json=_page([_appointment_row()]))

    respx.get(_APPOINTMENT_URL).mock(side_effect=appt_hook)

    r = client.get(
        "/api/bff/appointments?patient_q=nobody",
        headers={"X-Forwarded-Access-Token": "tok"},
    )
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0, "limit": 50, "offset": 0, "partial": False}
    assert appt_capture == [], "appointment-svc was called despite an empty patient match-set"


@respx.mock
def test_labs_list_status_param_is_repeatable():
    """`status` is repeatable so the "pending" UI tab (ordered + collected)
    is one round-trip. URL builders that comma-join would break this."""
    captured: list[httpx.Request] = []

    def hook(req):
        captured.append(req)
        return httpx.Response(200, json=_page([], total=0))

    respx.get(_LAB_URL).mock(side_effect=hook)
    respx.get(_PATIENT_URL).mock(return_value=httpx.Response(200, json=_page([])))
    respx.get(_PROVIDER_URL).mock(return_value=httpx.Response(200, json=_page([])))

    r = client.get(
        "/api/bff/labs?status=ordered&status=collected",
        headers={"X-Forwarded-Access-Token": "tok"},
    )
    assert r.status_code == 200
    assert captured[0].url.params.get_list("status") == ["ordered", "collected"]


@respx.mock
def test_providers_list_active_filter_forwarded():
    captured: list[httpx.Request] = []

    def hook(req):
        captured.append(req)
        return httpx.Response(200, json=_page([_provider_row()], total=1))

    respx.get(_PROVIDER_URL).mock(side_effect=hook)

    r = client.get(
        "/api/bff/providers?is_active=true&q=lee",
        headers={"X-Forwarded-Access-Token": "tok"},
    )
    assert r.status_code == 200
    qs = captured[0].url.params
    assert qs["is_active"] == "true"
    assert qs["q"] == "lee"


@respx.mock
def test_billing_overview_aging_is_server_computed_not_page_len():
    """`total_outstanding_cents` and the aging counts must reflect ALL
    outstanding invoices, not just the page the user is viewing.

    We mock a single page of 3 outstanding invoices: page=50, so the BFF's
    aging walker exits after one page. Verify the aging totals match the
    full ledger (3 × 100) regardless of `limit=10`.
    """
    issued_at = "2026-05-01T00:00:00"
    overdue_at = "2026-05-02T00:00:00"  # past
    invoices = [
        {
            "id": f"00000000-0000-0000-0000-00000000000{i}",
            "patient_id": _PATIENT_ID,
            "appointment_id": None,
            "total_amount_cents": 100,
            "currency": "USD",
            "status": "outstanding",
            "issued_at": issued_at,
            "due_at": overdue_at,
        }
        for i in range(3)
    ]

    respx.get(_BILLING_URL).mock(
        return_value=httpx.Response(200, json=_page(invoices, total=3, limit=200))
    )
    respx.get(_PATIENT_URL).mock(return_value=httpx.Response(200, json=_page([_patient_row()])))

    r = client.get(
        "/api/bff/billing-overview?limit=10",
        headers={"X-Forwarded-Access-Token": "tok"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_outstanding_cents"] == 300
    assert body["overdue_count"] == 3
