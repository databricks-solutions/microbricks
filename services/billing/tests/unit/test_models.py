"""Unit tests for response models. No DB needed."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from billing.routers.invoices import InvoiceOut


def test_invoice_out_round_trip():
    inv = InvoiceOut(
        id=uuid4(),
        patient_id=uuid4(),
        appointment_id=uuid4(),
        total_amount_cents=18500,
        currency="USD",
        status="sent",
        issued_at=datetime(2026, 6, 10, tzinfo=timezone.utc),
        due_at=datetime(2026, 7, 10, tzinfo=timezone.utc),
    )
    dumped = inv.model_dump()
    assert dumped["total_amount_cents"] == 18500
    assert dumped["status"] == "sent"
    assert dumped["currency"] == "USD"
    # round-trip through JSON-friendly form
    InvoiceOut.model_validate(inv.model_dump(mode="json"))


def test_invoice_out_no_appointment():
    inv = InvoiceOut(
        id=uuid4(),
        patient_id=uuid4(),
        appointment_id=None,
        total_amount_cents=4200,
        currency="USD",
        status="partially_paid",
        issued_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        due_at=None,
    )
    assert inv.appointment_id is None
    assert inv.due_at is None


def test_app_imports_cleanly():
    """Importing app must not require any DB or env at import time."""
    import billing.app as mod

    assert mod.app.title == "billing-svc"
    # /api/v1/healthz should be registered
    assert any(getattr(r, "path", None) == "/api/v1/healthz" for r in mod.app.routes)
