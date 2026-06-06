"""Typed BFF client for patient-svc.

Shapes match the canonical pattern in
`.claude/skills/hc-obo-auth/references/canonical-patterns.md`. Every method
is a thin wrapper over an HTTP call — when Orval is wired (Phase 4 follow-up),
the `Patient` model can be replaced by the generated one.
"""
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


class PatientClient(_BaseSvcClient):
    def __init__(self, user_token: str):
        super().__init__(user_token, service_slug="patient")

    async def get(self, patient_id: UUID) -> Patient:
        r = await self._client.get(f"/api/v1/patients/{patient_id}")
        r.raise_for_status()
        return Patient.model_validate(r.json())

    async def list(self) -> list[Patient]:
        r = await self._client.get("/api/v1/patients")
        r.raise_for_status()
        return [Patient.model_validate(x) for x in r.json()]
