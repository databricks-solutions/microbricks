"""Unit tests for response models. No DB needed."""
from __future__ import annotations

from uuid import uuid4

from provider.routers.providers import ProviderOut


def test_provider_out_round_trip():
    p = ProviderOut(
        id=uuid4(),
        npi="1234567890",
        given_name="Sara",
        family_name="Levine",
        credential_suffix="MD",
        email="sara.levine@bayhealth.example",
        is_active=True,
        organization_id=uuid4(),
    )
    dumped = p.model_dump()
    assert dumped["npi"] == "1234567890"
    assert dumped["credential_suffix"] == "MD"
    # round-trip through JSON-friendly form
    ProviderOut.model_validate(p.model_dump(mode="json"))


def test_app_imports_cleanly():
    """Importing app must not require any DB or env at import time."""
    import provider.app as mod

    assert mod.app.title == "provider-svc"
    # /api/v1/healthz should be registered
    assert any(getattr(r, "path", None) == "/api/v1/healthz" for r in mod.app.routes)
