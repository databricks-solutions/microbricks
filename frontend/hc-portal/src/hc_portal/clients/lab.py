"""Typed BFF client for lab-svc."""
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


class LabClient(_BaseSvcClient):
    def __init__(self, user_token: str):
        super().__init__(user_token, service_slug="lab")

    async def get_order(self, lab_order_id: UUID) -> LabOrder:
        r = await self._client.get(f"/api/v1/lab-orders/{lab_order_id}")
        r.raise_for_status()
        return LabOrder.model_validate(r.json())

    async def list_orders(self) -> list[LabOrder]:
        r = await self._client.get("/api/v1/lab-orders")
        r.raise_for_status()
        return [LabOrder.model_validate(x) for x in r.json()]

    async def list_orders_for_patient(
        self,
        patient_id: UUID,
        *,
        status: str | None = None,
        limit: int = 5,
    ) -> list[LabOrder]:
        params: dict[str, str | int] = {"patient_id": str(patient_id), "limit": limit}
        if status:
            params["status"] = status
        r = await self._client.get("/api/v1/lab-orders", params=params)
        r.raise_for_status()
        return [LabOrder.model_validate(x) for x in r.json()]
