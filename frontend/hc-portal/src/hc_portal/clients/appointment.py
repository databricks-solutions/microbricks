"""Typed BFF client for appointment-svc."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from ._base import Page, _BaseSvcClient


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
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="appointment", branch=branch)

    async def get(self, appointment_id: UUID) -> Appointment:
        r = await self._client.get(f"/api/v1/appointments/{appointment_id}")
        r.raise_for_status()
        return Appointment.model_validate(r.json())

    async def list(
        self,
        *,
        q: str | None = None,
        status: str | None = None,
        visit_type_code: str | None = None,
        patient_id: UUID | None = None,
        provider_id: UUID | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
        order: str = "desc",
    ) -> Page[Appointment]:
        """Single page of appointments with filter+search.

        Patient/provider name search is composed at the BFF — this method
        only knows about the fields appointment-svc owns.
        """
        params: dict[str, str | int] = {"limit": limit, "offset": offset, "order": order}
        if q:
            params["q"] = q
        if status:
            params["status"] = status
        if visit_type_code:
            params["visit_type_code"] = visit_type_code
        if patient_id is not None:
            params["patient_id"] = str(patient_id)
        if provider_id is not None:
            params["provider_id"] = str(provider_id)
        if from_date is not None:
            params["from_date"] = from_date.isoformat()
        if to_date is not None:
            params["to_date"] = to_date.isoformat()
        r = await self._client.get("/api/v1/appointments", params=params)
        r.raise_for_status()
        payload = r.json()
        return Page[Appointment](
            items=[Appointment.model_validate(x) for x in payload["items"]],
            total=int(payload["total"]),
            limit=int(payload["limit"]),
            offset=int(payload["offset"]),
        )

    async def list_for_patient(
        self,
        patient_id: UUID,
        *,
        limit: int = 3,
        order: str = "desc",
    ) -> list[Appointment]:
        """Convenience helper for the patient-summary aggregator. Returns
        bare `items` rather than the page envelope — the caller has no
        pagination concern."""
        r = await self._client.get(
            "/api/v1/appointments",
            params={"patient_id": str(patient_id), "limit": limit, "order": order},
        )
        r.raise_for_status()
        return [Appointment.model_validate(x) for x in r.json()["items"]]

    async def count(
        self,
        *,
        patient_id: UUID | None = None,
        status: str | None = None,
        on_date: date | None = None,
    ) -> int:
        params: dict[str, str] = {}
        if patient_id is not None:
            params["patient_id"] = str(patient_id)
        if status is not None:
            params["status"] = status
        if on_date is not None:
            params["on_date"] = on_date.isoformat()
        r = await self._client.get("/api/v1/appointments/count", params=params)
        r.raise_for_status()
        return int(r.json()["total"])
