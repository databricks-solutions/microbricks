"""Typed BFF client for prescription-svc with create + status transitions."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ._base import _BaseSvcClient


class Prescription(BaseModel):
    id: UUID
    patient_id: UUID
    prescribing_provider_id: UUID
    medication_code: str
    dose_text: str
    quantity: int
    refills_remaining: int
    status: str
    start_at: datetime
    end_at: datetime | None = None


class PrescriptionCreatePayload(BaseModel):
    patient_id: UUID
    prescribing_provider_id: UUID
    medication_code: str
    dose_text: str
    quantity: int
    refills_remaining: int = 0


class PrescriptionClient(_BaseSvcClient):
    def __init__(self, user_token: str):
        super().__init__(user_token, service_slug="prescription")

    async def create(self, payload: PrescriptionCreatePayload) -> Prescription:
        r = await self._client.post(
            "/api/v1/prescriptions", json=payload.model_dump(mode="json")
        )
        r.raise_for_status()
        return Prescription.model_validate(r.json())

    async def update_status(self, prescription_id: UUID, status: str) -> Prescription:
        r = await self._client.patch(
            f"/api/v1/prescriptions/{prescription_id}/status",
            json={"status": status},
        )
        r.raise_for_status()
        return Prescription.model_validate(r.json())
