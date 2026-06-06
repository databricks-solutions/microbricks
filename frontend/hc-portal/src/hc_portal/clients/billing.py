"""Typed BFF client for billing-svc."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ._base import _BaseSvcClient


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
    def __init__(self, user_token: str):
        super().__init__(user_token, service_slug="billing")

    async def get_invoice(self, invoice_id: UUID) -> Invoice:
        r = await self._client.get(f"/api/v1/invoices/{invoice_id}")
        r.raise_for_status()
        return Invoice.model_validate(r.json())

    async def list_invoices(self) -> list[Invoice]:
        r = await self._client.get("/api/v1/invoices")
        r.raise_for_status()
        return [Invoice.model_validate(x) for x in r.json()]

    async def list_outstanding_for_patient(
        self, patient_id: UUID
    ) -> list[Invoice]:
        r = await self._client.get(
            "/api/v1/invoices",
            params={"patient_id": str(patient_id), "status": "outstanding"},
        )
        r.raise_for_status()
        return [Invoice.model_validate(x) for x in r.json()]
