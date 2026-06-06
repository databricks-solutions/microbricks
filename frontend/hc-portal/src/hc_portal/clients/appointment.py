"""Typed BFF client for appointment-svc."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ._base import _BaseSvcClient


class Appointment(BaseModel):
    id: UUID
    patient_id: UUID
    provider_id: UUID
    visit_type_code: str
    scheduled_start: datetime
    scheduled_end: datetime
    status: str
    reason: str | None = None


class AppointmentClient(_BaseSvcClient):
    def __init__(self, user_token: str):
        super().__init__(user_token, service_slug="appointment")

    async def get(self, appointment_id: UUID) -> Appointment:
        r = await self._client.get(f"/api/v1/appointments/{appointment_id}")
        r.raise_for_status()
        return Appointment.model_validate(r.json())

    async def list(self) -> list[Appointment]:
        r = await self._client.get("/api/v1/appointments")
        r.raise_for_status()
        return [Appointment.model_validate(x) for x in r.json()]

    async def list_for_patient(
        self,
        patient_id: UUID,
        *,
        limit: int = 3,
        order: str = "desc",
    ) -> list[Appointment]:
        r = await self._client.get(
            "/api/v1/appointments",
            params={"patient_id": str(patient_id), "limit": limit, "order": order},
        )
        r.raise_for_status()
        return [Appointment.model_validate(x) for x in r.json()]
