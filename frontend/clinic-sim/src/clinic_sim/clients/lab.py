"""Typed BFF client for lab-svc with create + status transitions."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ._base import _BaseSvcClient


class LabOrder(BaseModel):
    id: UUID
    patient_id: UUID
    ordering_provider_id: UUID
    appointment_id: UUID | None = None
    panel_code: str
    status: str
    ordered_at: datetime
    collected_at: datetime | None = None
    resulted_at: datetime | None = None


class LabOrderCreatePayload(BaseModel):
    patient_id: UUID
    ordering_provider_id: UUID
    appointment_id: UUID | None = None
    panel_code: str


class LabClient(_BaseSvcClient):
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="lab", branch=branch)

    async def create_order(self, payload: LabOrderCreatePayload) -> LabOrder:
        r = await self._client.post(
            "/api/v1/lab-orders", json=payload.model_dump(mode="json")
        )
        r.raise_for_status()
        return LabOrder.model_validate(r.json())

    async def update_order_status(self, lab_order_id: UUID, status: str) -> LabOrder:
        r = await self._client.patch(
            f"/api/v1/lab-orders/{lab_order_id}/status",
            json={"status": status},
        )
        r.raise_for_status()
        return LabOrder.model_validate(r.json())
