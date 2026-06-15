"""Typed BFF client for appointment-svc via GraphQL."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ._base import _BaseSvcClient, _camel_keys


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


_APPOINTMENT_FIELDS = """
    id
    patientId
    providerId
    visitTypeCode
    scheduledStart
    scheduledEnd
    status
    reason
"""

_CREATE_MUTATION = """
mutation CreateAppointment($input: AppointmentCreateInput!) {
    createAppointment(input: $input) {
        %s
    }
}
""" % _APPOINTMENT_FIELDS

_UPDATE_STATUS_MUTATION = """
mutation UpdateAppointmentStatus($id: UUID!, $status: String!) {
    updateAppointmentStatus(id: $id, status: $status) {
        %s
    }
}
""" % _APPOINTMENT_FIELDS


def _to_appointment(d: dict) -> Appointment:
    return Appointment(
        id=d["id"],
        patient_id=d["patientId"],
        provider_id=d["providerId"],
        visit_type_code=d["visitTypeCode"],
        scheduled_start=d["scheduledStart"],
        scheduled_end=d["scheduledEnd"],
        status=d["status"],
        reason=d["reason"],
    )


class AppointmentClient(_BaseSvcClient):
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="appointment", branch=branch)

    async def create(self, payload: AppointmentCreatePayload) -> Appointment:
        variables = {"input": _camel_keys(payload.model_dump(mode="json"))}
        data = await self._graphql(_CREATE_MUTATION, variables)
        return _to_appointment(data["createAppointment"])

    async def update_status(self, appointment_id: UUID, status: str) -> Appointment:
        variables = {"id": str(appointment_id), "status": status}
        data = await self._graphql(_UPDATE_STATUS_MUTATION, variables)
        return _to_appointment(data["updateAppointmentStatus"])
