"""Typed BFF client for patient-svc with create support."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel

from ._base import _BaseSvcClient


class Patient(BaseModel):
    id: UUID
    mrn: str
    given_name: str
    family_name: str
    birth_date: date
    sex_at_birth: str


class PatientCreatePayload(BaseModel):
    mrn: str | None = None
    given_name: str
    family_name: str
    birth_date: date
    sex_at_birth: str
    gender_identity: str | None = None
    preferred_language: str | None = None
    email: str | None = None
    phone: str | None = None


class PatientClient(_BaseSvcClient):
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="patient", branch=branch)

    async def list(self, *, limit: int = 200) -> list[Patient]:
        """All patients (up to one page) for the simulator's directory cache.

        patient-svc returns the paginated envelope
        `{items, total, limit, offset}` — caps `limit` at 200 (the svc max).
        The simulator only needs the directory snapshot, not pagination state.
        """
        r = await self._client.get(
            "/api/v1/patients", params={"limit": limit}
        )
        r.raise_for_status()
        return [Patient.model_validate(x) for x in r.json()["items"]]

    async def create(self, payload: PatientCreatePayload) -> Patient:
        r = await self._client.post(
            "/api/v1/patients", json=payload.model_dump(mode="json")
        )
        r.raise_for_status()
        return Patient.model_validate(r.json())
