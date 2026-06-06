"""Typed BFF client for prescription-svc."""
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


class PrescriptionClient(_BaseSvcClient):
    def __init__(self, user_token: str):
        super().__init__(user_token, service_slug="prescription")

    async def get(self, prescription_id: UUID) -> Prescription:
        r = await self._client.get(f"/api/v1/prescriptions/{prescription_id}")
        r.raise_for_status()
        return Prescription.model_validate(r.json())

    async def list(self) -> list[Prescription]:
        r = await self._client.get("/api/v1/prescriptions")
        r.raise_for_status()
        return [Prescription.model_validate(x) for x in r.json()]

    async def list_active_for_patient(
        self, patient_id: UUID
    ) -> list[Prescription]:
        r = await self._client.get(
            "/api/v1/prescriptions",
            params={"patient_id": str(patient_id), "status": "active"},
        )
        r.raise_for_status()
        return [Prescription.model_validate(x) for x in r.json()]
