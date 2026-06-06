"""Unit tests for response models. No DB needed."""
from __future__ import annotations

from datetime import date
from uuid import uuid4

from patient.routers.patients import PatientOut


def test_patient_out_round_trip():
    p = PatientOut(
        id=uuid4(),
        mrn="MRN-9999",
        given_name="Maya",
        family_name="Okafor",
        birth_date=date(1989, 4, 12),
        sex_at_birth="female",
    )
    dumped = p.model_dump()
    assert dumped["mrn"] == "MRN-9999"
    assert dumped["sex_at_birth"] == "female"
    # round-trip through JSON-friendly form
    PatientOut.model_validate(p.model_dump(mode="json"))


def test_app_imports_cleanly():
    """Importing app must not require any DB or env at import time."""
    import patient.app as mod

    assert mod.app.title == "patient-svc"
    # /api/v1/healthz should be registered
    assert any(getattr(r, "path", None) == "/api/v1/healthz" for r in mod.app.routes)
