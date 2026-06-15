"""Typed BFF client for patient-svc via GraphQL."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel

from ._base import _BaseSvcClient, _camel_keys


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


_LIST_QUERY = """
query ListPatients($limit: Int!) {
    patients(limit: $limit) {
        items {
            id
            mrn
            givenName
            familyName
            birthDate
            sexAtBirth
        }
    }
}
"""

_CREATE_MUTATION = """
mutation CreatePatient($input: PatientCreateInput!) {
    createPatient(input: $input) {
        id
        mrn
        givenName
        familyName
        birthDate
        sexAtBirth
    }
}
"""


def _to_patient(d: dict) -> Patient:
    return Patient(
        id=d["id"],
        mrn=d["mrn"],
        given_name=d["givenName"],
        family_name=d["familyName"],
        birth_date=d["birthDate"],
        sex_at_birth=d["sexAtBirth"],
    )


class PatientClient(_BaseSvcClient):
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="patient", branch=branch)

    async def list(self, *, limit: int = 200) -> list[Patient]:
        data = await self._graphql(_LIST_QUERY, {"limit": limit})
        return [_to_patient(p) for p in data["patients"]["items"]]

    async def create(self, payload: PatientCreatePayload) -> Patient:
        variables = {"input": _camel_keys(payload.model_dump(mode="json"))}
        data = await self._graphql(_CREATE_MUTATION, variables)
        return _to_patient(data["createPatient"])
