"""Typed BFF client for billing-svc with create + status transitions."""
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


class InvoiceCreatePayload(BaseModel):
    patient_id: UUID
    appointment_id: UUID | None = None
    total_amount_cents: int
    currency: str = "USD"
    status: str = "draft"


class BillingClient(_BaseSvcClient):
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="billing", branch=branch)

    async def create_invoice(self, payload: InvoiceCreatePayload) -> Invoice:
        r = await self._client.post(
            "/api/v1/invoices", json=payload.model_dump(mode="json")
        )
        r.raise_for_status()
        return Invoice.model_validate(r.json())

    async def update_invoice_status(self, invoice_id: UUID, status: str) -> Invoice:
        r = await self._client.patch(
            f"/api/v1/invoices/{invoice_id}/status",
            json={"status": status},
        )
        r.raise_for_status()
        return Invoice.model_validate(r.json())
