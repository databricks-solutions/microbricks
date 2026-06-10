"""Typed BFF client for prescription-svc."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ._base import Page, _BaseSvcClient


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
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="prescription", branch=branch)

    async def get(self, prescription_id: UUID) -> Prescription:
        r = await self._client.get(f"/api/v1/prescriptions/{prescription_id}")
        r.raise_for_status()
        return Prescription.model_validate(r.json())

    async def list(
        self,
        *,
        q: str | None = None,
        status: str | None = None,
        patient_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Page[Prescription]:
        """Single page of prescriptions with filter+search."""
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if q:
            params["q"] = q
        if status:
            params["status"] = status
        if patient_id is not None:
            params["patient_id"] = str(patient_id)
        r = await self._client.get("/api/v1/prescriptions", params=params)
        r.raise_for_status()
        payload = r.json()
        return Page[Prescription](
            items=[Prescription.model_validate(x) for x in payload["items"]],
            total=int(payload["total"]),
            limit=int(payload["limit"]),
            offset=int(payload["offset"]),
        )

    async def list_active_for_patient(
        self, patient_id: UUID
    ) -> list[Prescription]:
        """Convenience helper for the patient-summary aggregator."""
        r = await self._client.get(
            "/api/v1/prescriptions",
            params={"patient_id": str(patient_id), "status": "active"},
        )
        r.raise_for_status()
        return [Prescription.model_validate(x) for x in r.json()["items"]]

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
        r = await self._client.get("/api/v1/prescriptions/count", params=params)
        r.raise_for_status()
        return int(r.json()["total"])
