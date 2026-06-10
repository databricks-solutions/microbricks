"""Typed BFF client for billing-svc."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ._base import Page, _BaseSvcClient


class Invoice(BaseModel):
    id: UUID
    patient_id: UUID
    appointment_id: UUID | None = None
    total_amount_cents: int
    currency: str
    status: str
    issued_at: datetime
    due_at: datetime | None = None


class BillingClient(_BaseSvcClient):
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="billing", branch=branch)

    async def get_invoice(self, invoice_id: UUID) -> Invoice:
        r = await self._client.get(f"/api/v1/invoices/{invoice_id}")
        r.raise_for_status()
        return Invoice.model_validate(r.json())

    async def list_invoices(
        self,
        *,
        q: str | None = None,
        status: str | None = None,
        patient_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Page[Invoice]:
        """Single page of invoices with filter+search."""
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if q:
            params["q"] = q
        if status:
            params["status"] = status
        if patient_id is not None:
            params["patient_id"] = str(patient_id)
        r = await self._client.get("/api/v1/invoices", params=params)
        r.raise_for_status()
        payload = r.json()
        return Page[Invoice](
            items=[Invoice.model_validate(x) for x in payload["items"]],
            total=int(payload["total"]),
            limit=int(payload["limit"]),
            offset=int(payload["offset"]),
        )

    async def list_outstanding_for_patient(
        self, patient_id: UUID
    ) -> list[Invoice]:
        """Convenience helper for the patient-summary aggregator. Returns
        bare `items` rather than the page envelope — used by per-patient
        joins where pagination is the caller's concern (typically <10
        rows)."""
        r = await self._client.get(
            "/api/v1/invoices",
            params={"patient_id": str(patient_id), "status": "outstanding"},
        )
        r.raise_for_status()
        return [Invoice.model_validate(x) for x in r.json()["items"]]

    async def count(
        self,
        *,
        patient_id: UUID | None = None,
        status: str | None = None,
    ) -> int:
        params: dict[str, str] = {}
        if patient_id is not None:
            params["patient_id"] = str(patient_id)
        if status is not None:
            params["status"] = status
        r = await self._client.get("/api/v1/invoices/count", params=params)
        r.raise_for_status()
        return int(r.json()["total"])
