"""Unit tests for response models. No DB needed."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from appointment.routers.appointments import AppointmentOut


def test_appointment_out_round_trip():
    a = AppointmentOut(
        id=uuid4(),
        patient_id=uuid4(),
        provider_id=uuid4(),
        visit_type_code="FOLLOW_UP",
        scheduled_start=datetime(2026, 6, 10, 14, 30, tzinfo=timezone.utc),
        scheduled_end=datetime(2026, 6, 10, 14, 50, tzinfo=timezone.utc),
        status="completed",
        reason="medication review",
    )
    dumped = a.model_dump()
    assert dumped["visit_type_code"] == "FOLLOW_UP"
    assert dumped["status"] == "completed"
    # round-trip through JSON-friendly form
    AppointmentOut.model_validate(a.model_dump(mode="json"))


def test_app_imports_cleanly():
    """Importing app must not require any DB or env at import time."""
    import appointment.app as mod

    assert mod.app.title == "appointment-svc"
    # /api/v1/healthz should be registered
    assert any(getattr(r, "path", None) == "/api/v1/healthz" for r in mod.app.routes)
