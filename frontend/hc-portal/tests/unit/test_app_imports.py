"""The BFF app must import cleanly without any env vars set.

This catches the common error of doing module-level work that requires the
runtime env to be populated. Per the canonical pattern, all stateful work
happens inside route handlers.
"""
from __future__ import annotations


def test_app_imports_cleanly():
    from hc_portal.backend.app import app

    routes = {r.path for r in app.router.routes}
    assert "/api/bff/healthz" in routes
    assert "/api/bff/patients" in routes
    assert "/api/bff/patient-summary/{patient_id}" in routes


def test_clients_module_exposes_all_six():
    from hc_portal import clients

    assert hasattr(clients, "PatientClient")
    assert hasattr(clients, "ProviderClient")
    assert hasattr(clients, "AppointmentClient")
    assert hasattr(clients, "LabClient")
    assert hasattr(clients, "PrescriptionClient")
    assert hasattr(clients, "BillingClient")
