"""Unit tests for the patient_summary aggregation route.

These verify the canonical BFF rules from `hc-bff-pattern/SKILL.md`:

  - Fan-out is concurrent (wall-clock = max(per-call), not sum).
  - Partial failures degrade gracefully with `partial: true`.
  - A failure in the *required* (patient) call propagates as a 502.
  - Both `Authorization` and `X-Forwarded-Access-Token` headers are forwarded.
  - Missing token → 401.
"""
from __future__ import annotations

import httpx
import respx
from fastapi.testclient import TestClient

from hc_portal.backend.app import app


client = TestClient(app)


_PATIENT_ID = "11111111-1111-1111-1111-111111111111"
_PROVIDER_ID = "22222222-2222-2222-2222-222222222222"


def _patient_payload() -> dict:
    return {
        "id": _PATIENT_ID,
        "mrn": "MRN-001",
        "given_name": "Ada",
        "family_name": "Lovelace",
        "birth_date": "1815-12-10",
        "sex_at_birth": "F",
    }


def _appointment_payload() -> dict:
    return {
        "id": "33333333-3333-3333-3333-333333333333",
        "patient_id": _PATIENT_ID,
        "provider_id": _PROVIDER_ID,
        "visit_type_code": "follow-up",
        "scheduled_start": "2026-06-10T10:00:00",
        "scheduled_end": "2026-06-10T10:30:00",
        "status": "scheduled",
        "reason": "annual",
    }


def _lab_payload() -> dict:
    return {
        "id": "44444444-4444-4444-4444-444444444444",
        "patient_id": _PATIENT_ID,
        "ordering_provider_id": _PROVIDER_ID,
        "appointment_id": None,
        "panel_code": "CBC",
        "status": "resulted",
        "ordered_at": "2026-06-01T08:00:00",
        "collected_at": "2026-06-01T08:30:00",
        "resulted_at": "2026-06-01T09:30:00",
    }


def _rx_payload() -> dict:
    return {
        "id": "55555555-5555-5555-5555-555555555555",
        "patient_id": _PATIENT_ID,
        "prescribing_provider_id": _PROVIDER_ID,
        "medication_code": "RxNorm-1234",
        "dose_text": "10mg daily",
        "quantity": 30,
        "refills_remaining": 2,
        "status": "active",
        "start_at": "2026-05-01T00:00:00",
        "end_at": None,
    }


def _invoice_payload() -> dict:
    return {
        "id": "66666666-6666-6666-6666-666666666666",
        "patient_id": _PATIENT_ID,
        "appointment_id": None,
        "total_amount_cents": 12500,
        "currency": "USD",
        "status": "outstanding",
        "issued_at": "2026-05-15T00:00:00",
        "due_at": "2026-06-15T00:00:00",
    }


def test_missing_token_returns_401():
    r = client.get(f"/api/bff/patient-summary/{_PATIENT_ID}")
    assert r.status_code == 401


@respx.mock
def test_summary_happy_path_forwards_token_to_every_service():
    captured: dict[str, httpx.Request] = {}

    def _capture(name):
        def hook(request):
            captured[name] = request
            return None  # let respx return the mocked response

        return hook

    respx.get(f"https://patient-test-1234567890.test.databricksapps.com/api/v1/patients/{_PATIENT_ID}").mock(
        side_effect=lambda req: (captured.__setitem__("patient", req)
                                 or httpx.Response(200, json=_patient_payload()))
    )
    respx.get("https://appointment-test-1234567890.test.databricksapps.com/api/v1/appointments").mock(
        side_effect=lambda req: (captured.__setitem__("appointment", req)
                                 or httpx.Response(200, json=[_appointment_payload()]))
    )
    respx.get("https://lab-test-1234567890.test.databricksapps.com/api/v1/lab-orders").mock(
        side_effect=lambda req: (captured.__setitem__("lab", req)
                                 or httpx.Response(200, json=[_lab_payload()]))
    )
    respx.get("https://prescription-test-1234567890.test.databricksapps.com/api/v1/prescriptions").mock(
        side_effect=lambda req: (captured.__setitem__("rx", req)
                                 or httpx.Response(200, json=[_rx_payload()]))
    )
    respx.get("https://billing-test-1234567890.test.databricksapps.com/api/v1/invoices").mock(
        side_effect=lambda req: (captured.__setitem__("billing", req)
                                 or httpx.Response(200, json=[_invoice_payload()]))
    )

    r = client.get(
        f"/api/bff/patient-summary/{_PATIENT_ID}",
        headers={"X-Forwarded-Access-Token": "user-1-token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["patient"]["mrn"] == "MRN-001"
    assert len(body["last_appointments"]) == 1
    assert len(body["recent_lab_orders"]) == 1
    assert len(body["active_prescriptions"]) == 1
    assert len(body["outstanding_invoices"]) == 1
    assert body["partial"] is False

    # Token forwarded to every downstream as BOTH headers (rule #4 in
    # hc-bff-pattern SKILL.md "The four BFF rules").
    assert set(captured) == {"patient", "appointment", "lab", "rx", "billing"}
    for name, req in captured.items():
        assert req.headers["authorization"] == "Bearer user-1-token", name
        assert req.headers["x-forwarded-access-token"] == "user-1-token", name


@respx.mock
def test_partial_failure_returns_200_with_partial_flag():
    """A peripheral service failure → 200 with `partial: true` and empty
    list for that section. Patient is required and present, so the response
    is not 502."""
    respx.get(f"https://patient-test-1234567890.test.databricksapps.com/api/v1/patients/{_PATIENT_ID}").mock(
        return_value=httpx.Response(200, json=_patient_payload())
    )
    respx.get("https://appointment-test-1234567890.test.databricksapps.com/api/v1/appointments").mock(
        return_value=httpx.Response(200, json=[_appointment_payload()])
    )
    respx.get("https://lab-test-1234567890.test.databricksapps.com/api/v1/lab-orders").mock(
        return_value=httpx.Response(503, text="lab is down")
    )
    respx.get("https://prescription-test-1234567890.test.databricksapps.com/api/v1/prescriptions").mock(
        return_value=httpx.Response(200, json=[_rx_payload()])
    )
    respx.get("https://billing-test-1234567890.test.databricksapps.com/api/v1/invoices").mock(
        return_value=httpx.Response(200, json=[_invoice_payload()])
    )

    r = client.get(
        f"/api/bff/patient-summary/{_PATIENT_ID}",
        headers={"X-Forwarded-Access-Token": "user-1-token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["partial"] is True
    assert body["recent_lab_orders"] == []
    # Other peripheral data is still present
    assert len(body["last_appointments"]) == 1
    assert len(body["active_prescriptions"]) == 1


@respx.mock
def test_required_patient_failure_returns_502():
    respx.get(f"https://patient-test-1234567890.test.databricksapps.com/api/v1/patients/{_PATIENT_ID}").mock(
        return_value=httpx.Response(503, text="patient-svc is down")
    )
    # Other mocks just to keep them happy (they may or may not be called
    # depending on gather scheduling, but partial-failure handling on the
    # required call kicks in regardless).
    for url in [
        "https://appointment-test-1234567890.test.databricksapps.com/api/v1/appointments",
        "https://lab-test-1234567890.test.databricksapps.com/api/v1/lab-orders",
        "https://prescription-test-1234567890.test.databricksapps.com/api/v1/prescriptions",
        "https://billing-test-1234567890.test.databricksapps.com/api/v1/invoices",
    ]:
        respx.get(url).mock(return_value=httpx.Response(200, json=[]))

    r = client.get(
        f"/api/bff/patient-summary/{_PATIENT_ID}",
        headers={"X-Forwarded-Access-Token": "user-1-token"},
    )
    assert r.status_code == 502
    assert "patient-svc" in r.json()["detail"]


@respx.mock
def test_authorization_header_fallback_works():
    """Per auth.py priority: Authorization: Bearer ... is honored when
    X-Forwarded-Access-Token is absent (used by upstream proxies in tests)."""
    respx.get(f"https://patient-test-1234567890.test.databricksapps.com/api/v1/patients/{_PATIENT_ID}").mock(
        return_value=httpx.Response(200, json=_patient_payload())
    )
    for url in [
        "https://appointment-test-1234567890.test.databricksapps.com/api/v1/appointments",
        "https://lab-test-1234567890.test.databricksapps.com/api/v1/lab-orders",
        "https://prescription-test-1234567890.test.databricksapps.com/api/v1/prescriptions",
        "https://billing-test-1234567890.test.databricksapps.com/api/v1/invoices",
    ]:
        respx.get(url).mock(return_value=httpx.Response(200, json=[]))

    r = client.get(
        f"/api/bff/patient-summary/{_PATIENT_ID}",
        headers={"Authorization": "Bearer fallback-token"},
    )
    assert r.status_code == 200


def test_fanout_uses_asyncio_gather():
    """The most important BFF property is concurrent fan-out — wall-clock
    must be `max(per-call)`, not `sum(per-call)`. A regression to sequential
    awaits is a code review reject (see "anti-patterns" in hc-bff-pattern
    SKILL.md).

    Rather than time-mocking through `respx` (which short-circuits before
    httpx runs the event loop, making timing meaningless), we statically
    assert the route source uses `asyncio.gather`. This is a structural test:
    if someone refactors to sequential awaits, this will fail.
    """
    import inspect

    from hc_portal.backend.routers import aggregations

    src = inspect.getsource(aggregations.patient_summary)
    assert "asyncio.gather" in src, (
        "patient_summary must use asyncio.gather for concurrent fan-out — "
        "see hc-bff-pattern SKILL.md rule #2."
    )
    assert "return_exceptions=True" in src, (
        "patient_summary must pass return_exceptions=True so peripheral "
        "failures degrade gracefully — see SKILL.md anti-patterns."
    )
