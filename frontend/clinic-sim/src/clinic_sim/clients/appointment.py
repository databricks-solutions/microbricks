"""Typed BFF client for appointment-svc with create + status transitions."""
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


class AppointmentCreatePayload(BaseModel):
    patient_id: UUID
    provider_id: UUID
    visit_type_code: str
    scheduled_start: datetime
    scheduled_end: datetime
    reason: str | None = None


class AppointmentClient(_BaseSvcClient):
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="appointment", branch=branch)

    async def create(self, payload: AppointmentCreatePayload) -> Appointment:
        r = await self._client.post(
            "/api/v1/appointments", json=payload.model_dump(mode="json")
        )
        r.raise_for_status()
        return Appointment.model_validate(r.json())

    async def update_status(self, appointment_id: UUID, status: str) -> Appointment:
        r = await self._client.patch(
            f"/api/v1/appointments/{appointment_id}/status",
            json={"status": status},
        )
        r.raise_for_status()
        return Appointment.model_validate(r.json())
