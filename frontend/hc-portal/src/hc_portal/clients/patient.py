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

from ._base import Page, _BaseSvcClient


class Patient(BaseModel):
    id: UUID
    mrn: str
    given_name: str
    family_name: str
    birth_date: date
    sex_at_birth: str


class PatientClient(_BaseSvcClient):
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="patient", branch=branch)

    async def get(self, patient_id: UUID) -> Patient:
        r = await self._client.get(f"/api/v1/patients/{patient_id}")
        r.raise_for_status()
        return Patient.model_validate(r.json())

    async def list(
        self,
        *,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Page[Patient]:
        """Single page of patients with optional search."""
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if q:
            params["q"] = q
        r = await self._client.get("/api/v1/patients", params=params)
        r.raise_for_status()
        payload = r.json()
        return Page[Patient](
            items=[Patient.model_validate(x) for x in payload["items"]],
            total=int(payload["total"]),
            limit=int(payload["limit"]),
            offset=int(payload["offset"]),
        )

    async def list_by_ids(self, ids: list[UUID]) -> list[Patient]:
        """Batch-resolve patients referenced by a paginated list elsewhere
        (e.g. an appointments page). Used by the BFF to enrich a page with
        names without fetching the whole patient table.

        Returns an empty list when `ids` is empty (no round-trip).
        """
        if not ids:
            return []
        params: list[tuple[str, str]] = [("ids", str(i)) for i in ids]
        params.append(("limit", str(min(200, len(ids)))))
        r = await self._client.get("/api/v1/patients", params=params)
        r.raise_for_status()
        return [Patient.model_validate(x) for x in r.json()["items"]]

    async def count(self) -> int:
        r = await self._client.get("/api/v1/patients/count")
        r.raise_for_status()
        return int(r.json()["total"])
