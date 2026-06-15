"""Unit tests for the GraphQL endpoint.

These verify that the /api/graphql route resolves queries correctly,
fans out to downstream services via the typed clients, and handles
partial failures gracefully.
"""
from __future__ import annotations

import httpx
import respx
from starlette.testclient import TestClient

from hc_portal.backend.app import app

client = TestClient(app)

_PATIENT_URL = "https://patient-1234567890.test.databricksapps.com/api/v1/patients"
_PROVIDER_URL = "https://provider-1234567890.test.databricksapps.com/api/v1/providers"
_APPOINTMENT_URL = "https://appointment-1234567890.test.databricksapps.com/api/v1/appointments"
_LAB_URL = "https://lab-1234567890.test.databricksapps.com/api/v1/lab-orders"
_RX_URL = "https://prescription-1234567890.test.databricksapps.com/api/v1/prescriptions"
_BILLING_URL = "https://billing-1234567890.test.databricksapps.com/api/v1/invoices"

_PATIENT_COUNT_URL = "https://patient-1234567890.test.databricksapps.com/api/v1/patients/count"
_PROVIDER_COUNT_URL = "https://provider-1234567890.test.databricksapps.com/api/v1/providers/count"
_APPOINTMENT_COUNT_URL = "https://appointment-1234567890.test.databricksapps.com/api/v1/appointments/count"
_LAB_COUNT_URL = "https://lab-1234567890.test.databricksapps.com/api/v1/lab-orders/count"
_RX_COUNT_URL = "https://prescription-1234567890.test.databricksapps.com/api/v1/prescriptions/count"
_BILLING_COUNT_URL = "https://billing-1234567890.test.databricksapps.com/api/v1/invoices/count"

_PATIENT_ID = "00000000-0000-0000-0000-000000000001"
_PROVIDER_ID = "00000000-0000-0000-0000-000000000002"


def _page(items, total=None, limit=50, offset=0):
    return {
        "items": items,
        "total": total if total is not None else len(items),
        "limit": limit,
        "offset": offset,
    }


def _gql(query: str, variables: dict | None = None, token: str = "user-1-token"):
    body: dict = {"query": query}
    if variables:
        body["variables"] = variables
    return client.post(
        "/api/graphql",
        json=body,
        headers={"X-Forwarded-Access-Token": token},
    )


# --- Schema introspection ---


def test_graphql_endpoint_returns_schema():
    r = _gql("{ __schema { queryType { name } } }")
    assert r.status_code == 200
    data = r.json()
    assert data["data"]["__schema"]["queryType"]["name"] == "Query"


# --- Dashboard stats ---


@respx.mock
def test_dashboard_stats_query():
    respx.get(_PATIENT_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 100}))
    respx.get(_PROVIDER_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 12}))
    respx.get(_APPOINTMENT_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 50}))
    respx.get(_RX_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 25}))
    respx.get(_LAB_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 10}))
    respx.get(_BILLING_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 5}))

    r = _gql("""
        query {
            dashboardStats {
                totalPatients
                totalProviders
                totalAppointments
                partial
            }
        }
    """)
    assert r.status_code == 200
    data = r.json()["data"]["dashboardStats"]
    assert data["totalPatients"] == 100
    assert data["totalProviders"] == 12
    assert data["partial"] is False


@respx.mock
def test_dashboard_stats_partial_failure():
    respx.get(_PATIENT_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 100}))
    respx.get(_PROVIDER_COUNT_URL).mock(return_value=httpx.Response(503, text="down"))
    respx.get(_APPOINTMENT_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 50}))
    respx.get(_RX_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 25}))
    respx.get(_LAB_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 10}))
    respx.get(_BILLING_COUNT_URL).mock(return_value=httpx.Response(200, json={"total": 5}))

    r = _gql("""
        query {
            dashboardStats {
                totalPatients
                totalProviders
                partial
            }
        }
    """)
    assert r.status_code == 200
    data = r.json()["data"]["dashboardStats"]
    assert data["totalPatients"] == 100
    assert data["totalProviders"] is None
    assert data["partial"] is True


# --- Patients list ---


@respx.mock
def test_patients_list_query():
    respx.get(_PATIENT_URL).mock(
        return_value=httpx.Response(200, json=_page([
            {
                "id": _PATIENT_ID,
                "mrn": "MRN-001",
                "given_name": "Ada",
                "family_name": "Lovelace",
                "birth_date": "1815-12-10",
                "sex_at_birth": "female",
            }
        ], total=1))
    )

    r = _gql("""
        query {
            patients(q: "ada", limit: 10, offset: 0) {
                items { id givenName familyName mrn }
                total
            }
        }
    """)
    assert r.status_code == 200
    data = r.json()["data"]["patients"]
    assert data["total"] == 1
    assert data["items"][0]["givenName"] == "Ada"
    assert data["items"][0]["familyName"] == "Lovelace"


# --- Providers list with isActive filter ---


@respx.mock
def test_providers_list_active_filter():
    respx.get(_PROVIDER_URL).mock(
        return_value=httpx.Response(200, json=_page([
            {
                "id": _PROVIDER_ID,
                "npi": "1234567890",
                "given_name": "Sarah",
                "family_name": "Lee",
                "credential_suffix": "MD",
                "email": "sarah@example.com",
                "is_active": True,
                "organization_id": "00000000-0000-0000-0000-000000000099",
            }
        ], total=1))
    )

    r = _gql("""
        query {
            providers(isActive: true, limit: 10, offset: 0) {
                items { id givenName familyName isActive credentialSuffix }
                total
            }
        }
    """)
    assert r.status_code == 200
    data = r.json()["data"]["providers"]
    assert data["total"] == 1
    assert data["items"][0]["isActive"] is True
    assert data["items"][0]["credentialSuffix"] == "MD"


# --- Appointments with nested patient/provider ---


@respx.mock
def test_appointments_with_nested_resolvers():
    respx.get(_APPOINTMENT_URL).mock(
        return_value=httpx.Response(200, json=_page([
            {
                "id": "00000000-0000-0000-0000-000000000010",
                "patient_id": _PATIENT_ID,
                "provider_id": _PROVIDER_ID,
                "visit_type_code": "follow-up",
                "scheduled_start": "2026-06-10T09:00:00",
                "scheduled_end": "2026-06-10T09:30:00",
                "status": "booked",
                "reason": "Annual checkup",
            }
        ], total=1))
    )
    respx.get(_PATIENT_URL).mock(
        return_value=httpx.Response(200, json=_page([
            {
                "id": _PATIENT_ID,
                "mrn": "MRN-001",
                "given_name": "Ada",
                "family_name": "Lovelace",
                "birth_date": "1815-12-10",
                "sex_at_birth": "female",
            }
        ]))
    )
    respx.get(_PROVIDER_URL).mock(
        return_value=httpx.Response(200, json=_page([
            {
                "id": _PROVIDER_ID,
                "npi": "1234567890",
                "given_name": "Sarah",
                "family_name": "Lee",
                "credential_suffix": "MD",
                "email": "sarah@example.com",
                "is_active": True,
                "organization_id": "00000000-0000-0000-0000-000000000099",
            }
        ]))
    )

    r = _gql("""
        query {
            appointments(limit: 10, offset: 0) {
                items {
                    id
                    status
                    visitTypeCode
                    patient { givenName familyName }
                    provider { givenName familyName credentialSuffix }
                }
                total
            }
        }
    """)
    assert r.status_code == 200
    data = r.json()["data"]["appointments"]
    assert data["total"] == 1
    appt = data["items"][0]
    assert appt["status"] == "booked"
    assert appt["patient"]["givenName"] == "Ada"
    assert appt["provider"]["familyName"] == "Lee"


# --- Patient summary (concurrent fan-out) ---


@respx.mock
def test_patient_summary_query():
    respx.get(f"{_PATIENT_URL}/{_PATIENT_ID}").mock(
        return_value=httpx.Response(200, json={
            "id": _PATIENT_ID,
            "mrn": "MRN-001",
            "given_name": "Ada",
            "family_name": "Lovelace",
            "birth_date": "1815-12-10",
            "sex_at_birth": "female",
        })
    )
    respx.get(_APPOINTMENT_URL).mock(
        return_value=httpx.Response(200, json=_page([]))
    )
    respx.get(_LAB_URL).mock(
        return_value=httpx.Response(200, json=_page([]))
    )
    respx.get(_RX_URL).mock(
        return_value=httpx.Response(200, json=_page([]))
    )
    respx.get(_BILLING_URL).mock(
        return_value=httpx.Response(200, json=_page([]))
    )
    respx.get(_PROVIDER_URL).mock(
        return_value=httpx.Response(200, json=_page([]))
    )

    r = _gql(
        """
        query PatientSummary($id: UUID!) {
            patientSummary(id: $id) {
                patient { givenName familyName mrn }
                lastAppointments { id }
                activePrescriptions { id }
                recentLabOrders { id }
                outstandingInvoices { id }
                partial
            }
        }
        """,
        variables={"id": _PATIENT_ID},
    )
    assert r.status_code == 200
    data = r.json()["data"]["patientSummary"]
    assert data["patient"]["givenName"] == "Ada"
    assert data["partial"] is False


@respx.mock
def test_patient_summary_partial_failure():
    respx.get(f"{_PATIENT_URL}/{_PATIENT_ID}").mock(
        return_value=httpx.Response(200, json={
            "id": _PATIENT_ID,
            "mrn": "MRN-001",
            "given_name": "Ada",
            "family_name": "Lovelace",
            "birth_date": "1815-12-10",
            "sex_at_birth": "female",
        })
    )
    respx.get(_APPOINTMENT_URL).mock(
        return_value=httpx.Response(200, json=_page([]))
    )
    respx.get(_LAB_URL).mock(
        return_value=httpx.Response(503, text="lab down")
    )
    respx.get(_RX_URL).mock(
        return_value=httpx.Response(200, json=_page([]))
    )
    respx.get(_BILLING_URL).mock(
        return_value=httpx.Response(200, json=_page([]))
    )
    respx.get(_PROVIDER_URL).mock(
        return_value=httpx.Response(200, json=_page([]))
    )

    r = _gql(
        """
        query PatientSummary($id: UUID!) {
            patientSummary(id: $id) {
                patient { givenName familyName }
                recentLabOrders { id }
                partial
            }
        }
        """,
        variables={"id": _PATIENT_ID},
    )
    assert r.status_code == 200
    data = r.json()["data"]["patientSummary"]
    assert data["partial"] is True
    assert data["recentLabOrders"] == []


# --- Missing auth token returns 401 ---


def test_graphql_missing_token_returns_401(monkeypatch):
    monkeypatch.delenv("LOCAL_DEV_TOKEN", raising=False)
    r = client.post(
        "/api/graphql",
        json={"query": "{ __schema { queryType { name } } }"},
    )
    assert r.status_code == 401
