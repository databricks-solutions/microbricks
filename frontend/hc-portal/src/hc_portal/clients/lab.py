"""Typed BFF client for lab-svc."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ._base import Page, _BaseSvcClient


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
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="lab", branch=branch)

    async def get_order(self, lab_order_id: UUID) -> LabOrder:
        r = await self._client.get(f"/api/v1/lab-orders/{lab_order_id}")
        r.raise_for_status()
        return LabOrder.model_validate(r.json())

    async def list_orders(
        self,
        *,
        q: str | None = None,
        status: list[str] | None = None,
        panel_code: str | None = None,
        patient_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Page[LabOrder]:
        """Single page of lab orders with filter+search.

        `status` is repeatable so the UI's "pending" tab (ordered + collected)
        is a single round-trip.
        """
        params: list[tuple[str, str]] = [("limit", str(limit)), ("offset", str(offset))]
        if q:
            params.append(("q", q))
        for s in status or []:
            params.append(("status", s))
        if panel_code:
            params.append(("panel_code", panel_code))
        if patient_id is not None:
            params.append(("patient_id", str(patient_id)))
        r = await self._client.get("/api/v1/lab-orders", params=params)
        r.raise_for_status()
        payload = r.json()
        return Page[LabOrder](
            items=[LabOrder.model_validate(x) for x in payload["items"]],
            total=int(payload["total"]),
            limit=int(payload["limit"]),
            offset=int(payload["offset"]),
        )

    async def list_orders_for_patient(
        self,
        patient_id: UUID,
        *,
        status: str | None = None,
        limit: int = 5,
    ) -> list[LabOrder]:
        """Convenience helper for the patient-summary aggregator."""
        params: dict[str, str | int] = {"patient_id": str(patient_id), "limit": limit}
        if status:
            params["status"] = status
        r = await self._client.get("/api/v1/lab-orders", params=params)
        r.raise_for_status()
        return [LabOrder.model_validate(x) for x in r.json()["items"]]

    async def count(
        self,
        *,
        patient_id: UUID | None = None,
        status: list[str] | None = None,
    ) -> int:
        params: list[tuple[str, str]] = []
        if patient_id is not None:
            params.append(("patient_id", str(patient_id)))
        for s in status or []:
            params.append(("status", s))
        r = await self._client.get("/api/v1/lab-orders/count", params=params)
        r.raise_for_status()
        return int(r.json()["total"])
