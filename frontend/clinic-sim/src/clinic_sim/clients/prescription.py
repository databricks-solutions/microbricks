"""Typed BFF client for prescription-svc via GraphQL."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ._base import _BaseSvcClient, _camel_keys


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


_PRESCRIPTION_FIELDS = """
    id
    patientId
    prescribingProviderId
    medicationCode
    doseText
    quantity
    refillsRemaining
    status
    startAt
    endAt
"""

_CREATE_MUTATION = """
mutation CreatePrescription($input: PrescriptionCreateInput!) {
    createPrescription(input: $input) {
        %s
    }
}
""" % _PRESCRIPTION_FIELDS

_UPDATE_STATUS_MUTATION = """
mutation UpdatePrescriptionStatus($id: UUID!, $status: String!) {
    updatePrescriptionStatus(id: $id, status: $status) {
        %s
    }
}
""" % _PRESCRIPTION_FIELDS


def _to_prescription(d: dict) -> Prescription:
    return Prescription(
        id=d["id"],
        patient_id=d["patientId"],
        prescribing_provider_id=d["prescribingProviderId"],
        medication_code=d["medicationCode"],
        dose_text=d["doseText"],
        quantity=d["quantity"],
        refills_remaining=d["refillsRemaining"],
        status=d["status"],
        start_at=d["startAt"],
        end_at=d["endAt"],
    )


class PrescriptionClient(_BaseSvcClient):
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="prescription", branch=branch)

    async def create(self, payload: PrescriptionCreatePayload) -> Prescription:
        variables = {"input": _camel_keys(payload.model_dump(mode="json"))}
        data = await self._graphql(_CREATE_MUTATION, variables)
        return _to_prescription(data["createPrescription"])

    async def update_status(self, prescription_id: UUID, status: str) -> Prescription:
        variables = {"id": str(prescription_id), "status": status}
        data = await self._graphql(_UPDATE_STATUS_MUTATION, variables)
        return _to_prescription(data["updatePrescriptionStatus"])
