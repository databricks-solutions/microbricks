"""Unit tests for the dashboard_stats aggregation route.

The dashboard cards must source counts from each service's `/count` endpoint
— never from `len(list())`. The list endpoints are paginated (per-service
`LIMIT`) so counting them is silently wrong as soon as the row count grows
past the page size; the explicit count endpoints are the only source of
truth. These tests pin that contract.
"""
from __future__ import annotations

from datetime import date

import httpx
import respx
from fastapi.testclient import TestClient

from hc_portal.backend.app import app


client = TestClient(app)


_PATIENT_COUNT_URL = "https://patient-1234567890.test.databricksapps.com/api/v1/patients/count"
_PROVIDER_COUNT_URL = "https://provider-1234567890.test.databricksapps.com/api/v1/providers/count"
_APPOINTMENT_COUNT_URL = "https://appointment-1234567890.test.databricksapps.com/api/v1/appointments/count"
_RX_COUNT_URL = "https://prescription-1234567890.test.databricksapps.com/api/v1/prescriptions/count"
_LAB_COUNT_URL = "https://lab-1234567890.test.databricksapps.com/api/v1/lab-orders/count"
_BILLING_COUNT_URL = "https://billing-1234567890.test.databricksapps.com/api/v1/invoices/count"


@respx.mock
def test_dashboard_stats_uses_count_endpoints_and_forwards_token():
    """Every dashboard tile must come from a `/count` endpoint (not a
    list-and-len). Verifies the right URL is called for each tile and that
    the OBO token is forwarded as both header variants on every fan-out call."""
    captured: dict[str, httpx.Request] = {}

    def _hit(name: str, total: int):
        def hook(request):
            captured.setdefault(name, request)
            return httpx.Response(200, json={"total": total})
        return hook

    respx.get(_PATIENT_COUNT_URL).mock(side_effect=_hit("patients", 537))
    respx.get(_PROVIDER_COUNT_URL).mock(side_effect=_hit("providers", 12))
    respx.get(_APPOINTMENT_COUNT_URL).mock(side_effect=lambda req: (
        captured.setdefault(
            "appointments_today" if req.url.params.get("on_date") else "appointments_total",
            req,
        ),
        httpx.Response(
            200,
            json={"total": 17 if req.url.params.get("on_date") else 1042},
        ),
    )[1])
    respx.get(_RX_COUNT_URL).mock(side_effect=lambda req: (
        captured.setdefault(
            "rx_active" if req.url.params.get("status") == "active" else "rx_total",
            req,
        ),
        httpx.Response(
            200,
            json={"total": 281 if req.url.params.get("status") == "active" else 902},
        ),
    )[1])
    respx.get(_LAB_COUNT_URL).mock(side_effect=lambda req: (
        captured.setdefault(
            "labs_pending" if req.url.params.get_list("status") else "labs_total",
            req,
        ),
        httpx.Response(
            200,
            json={"total": 46 if req.url.params.get_list("status") else 1331},
        ),
    )[1])
    respx.get(_BILLING_COUNT_URL).mock(side_effect=_hit("invoices", 612))

    r = client.get(
        "/api/bff/dashboard-stats",
        headers={"X-Forwarded-Access-Token": "user-1-token"},
    )
    assert r.status_code == 200, r.text
    body = r.json()

    # Counts are the raw service responses, NOT the length of any list.
    assert body["total_patients"] == 537
    assert body["total_providers"] == 12
    assert body["total_appointments"] == 1042
    assert body["todays_appointments"] == 17
    assert body["total_prescriptions"] == 902
    assert body["active_prescriptions"] == 281
    assert body["total_lab_orders"] == 1331
    assert body["pending_labs"] == 46
    assert body["total_invoices"] == 612
    assert body["partial"] is False

    # All 9 count calls were made (no list calls).
    expected = {
        "patients",
        "providers",
        "appointments_total",
        "appointments_today",
        "rx_total",
        "rx_active",
        "labs_total",
        "labs_pending",
        "invoices",
    }
    assert set(captured) == expected, captured.keys()

    # Today's-appointment call must include the `on_date=<today>` filter.
    today_req = captured["appointments_today"]
    assert today_req.url.params["on_date"] == date.today().isoformat()

    # Pending-labs call must include BOTH `status=ordered` and `status=collected`.
    pending_req = captured["labs_pending"]
    assert pending_req.url.params.get_list("status") == ["ordered", "collected"]

    # Token forwarded as BOTH headers on every downstream call (BFF rule #4).
    for name, req in captured.items():
        assert req.headers["authorization"] == "Bearer user-1-token", name
        assert req.headers["x-forwarded-access-token"] == "user-1-token", name


@respx.mock
def test_dashboard_stats_partial_failure_degrades_to_zero():
    """A single peripheral count failure → 200 with `partial: true` and that
    tile reports 0. The other tiles still show real counts."""
    respx.get(_PATIENT_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 100}))
    respx.get(_PROVIDER_COUNT_URL).mock(return_value=httpx.Response(503, text="down"))
    respx.get(_APPOINTMENT_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 50}))
    respx.get(_RX_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 25}))
    respx.get(_LAB_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 10}))
    respx.get(_BILLING_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 5}))

    r = client.get(
        "/api/bff/dashboard-stats",
        headers={"X-Forwarded-Access-Token": "user-1-token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["partial"] is True
    assert body["total_providers"] == 0
    assert body["total_patients"] == 100
    assert body["total_invoices"] == 5


def test_dashboard_stats_fanout_uses_asyncio_gather():
    """Structural test: BFF rule #2 — fan-out must use `asyncio.gather` with
    `return_exceptions=True` so wall-clock is `max(per-call)` and a single
    failing tile degrades to 0 rather than 502-ing the whole page."""
    import inspect

    from hc_portal.backend.routers import aggregations

    src = inspect.getsource(aggregations.dashboard_stats)
    assert "asyncio.gather" in src, (
        "dashboard_stats must use asyncio.gather for concurrent fan-out — "
        "see hc-bff-pattern SKILL.md rule #2."
    )
    assert "return_exceptions=True" in src, (
        "dashboard_stats must pass return_exceptions=True so a single bad "
        "tile doesn't break the whole dashboard."
    )
