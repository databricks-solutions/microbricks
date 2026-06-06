"""Unit tests for response models. No DB needed."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from prescription.routers.prescriptions import PrescriptionOut


def test_prescription_out_round_trip():
    p = PrescriptionOut(
        id=uuid4(),
        patient_id=uuid4(),
        prescribing_provider_id=uuid4(),
        medication_code="MED-METFORMIN",
        dose_text="500 mg PO BID",
        quantity=60,
        refills_remaining=5,
        status="active",
        start_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
        end_at=None,
    )
    dumped = p.model_dump()
    assert dumped["medication_code"] == "MED-METFORMIN"
    assert dumped["status"] == "active"
    assert dumped["refills_remaining"] == 5
    # round-trip through JSON-friendly form
    PrescriptionOut.model_validate(p.model_dump(mode="json"))


def test_app_imports_cleanly():
    """Importing app must not require any DB or env at import time."""
    import prescription.app as mod

    assert mod.app.title == "prescription-svc"
    # /api/v1/healthz should be registered
    assert any(getattr(r, "path", None) == "/api/v1/healthz" for r in mod.app.routes)
