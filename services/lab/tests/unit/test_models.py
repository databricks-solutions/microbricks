"""Unit tests for response models. No DB needed."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from lab.routers.lab_orders import LabOrderOut


def test_lab_order_out_round_trip():
    o = LabOrderOut(
        id=uuid4(),
        patient_id=uuid4(),
        ordering_provider_id=uuid4(),
        appointment_id=uuid4(),
        panel_code="LP-A1C",
        status="resulted",
        ordered_at=datetime(2026, 6, 10, 14, 35, tzinfo=timezone.utc),
        collected_at=datetime(2026, 6, 10, 14, 50, tzinfo=timezone.utc),
        resulted_at=datetime(2026, 6, 11, 9, 14, tzinfo=timezone.utc),
    )
    dumped = o.model_dump()
    assert dumped["panel_code"] == "LP-A1C"
    assert dumped["status"] == "resulted"
    # round-trip through JSON-friendly form
    LabOrderOut.model_validate(o.model_dump(mode="json"))


def test_lab_order_out_optional_fields():
    o = LabOrderOut(
        id=uuid4(),
        patient_id=uuid4(),
        ordering_provider_id=uuid4(),
        appointment_id=None,
        panel_code="LP-LIPID",
        status="ordered",
        ordered_at=datetime(2026, 6, 12, 9, 30, tzinfo=timezone.utc),
        collected_at=None,
        resulted_at=None,
    )
    assert o.appointment_id is None
    assert o.collected_at is None


def test_app_imports_cleanly():
    """Importing app must not require any DB or env at import time."""
    import lab.app as mod

    assert mod.app.title == "lab-svc"
    # /api/v1/healthz should be registered
    assert any(getattr(r, "path", None) == "/api/v1/healthz" for r in mod.app.routes)
