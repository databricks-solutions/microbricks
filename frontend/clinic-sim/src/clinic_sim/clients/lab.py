"""Typed BFF client for lab-svc via GraphQL."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ._base import _BaseSvcClient, _camel_keys


class LabOrder(BaseModel):
    id: UUID
    patient_id: UUID
    ordering_provider_id: UUID
    appointment_id: UUID | None = None
    panel_code: str
    status: str
    ordered_at: datetime
    collected_at: datetime | None = None
    resulted_at: datetime | None = None


class LabOrderCreatePayload(BaseModel):
    patient_id: UUID
    ordering_provider_id: UUID
    appointment_id: UUID | None = None
    panel_code: str


_LAB_ORDER_FIELDS = """
    id
    patientId
    orderingProviderId
    appointmentId
    panelCode
    status
    orderedAt
    collectedAt
    resultedAt
"""

_CREATE_MUTATION = """
mutation CreateLabOrder($input: LabOrderCreateInput!) {
    createLabOrder(input: $input) {
        %s
    }
}
""" % _LAB_ORDER_FIELDS

_UPDATE_STATUS_MUTATION = """
mutation UpdateLabOrderStatus($id: UUID!, $status: String!) {
    updateLabOrderStatus(id: $id, status: $status) {
        %s
    }
}
""" % _LAB_ORDER_FIELDS


def _to_lab_order(d: dict) -> LabOrder:
    return LabOrder(
        id=d["id"],
        patient_id=d["patientId"],
        ordering_provider_id=d["orderingProviderId"],
        appointment_id=d["appointmentId"],
        panel_code=d["panelCode"],
        status=d["status"],
        ordered_at=d["orderedAt"],
        collected_at=d["collectedAt"],
        resulted_at=d["resultedAt"],
    )


class LabClient(_BaseSvcClient):
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="lab", branch=branch)

    async def create_order(self, payload: LabOrderCreatePayload) -> LabOrder:
        variables = {"input": _camel_keys(payload.model_dump(mode="json"))}
        data = await self._graphql(_CREATE_MUTATION, variables)
        return _to_lab_order(data["createLabOrder"])

    async def update_order_status(self, lab_order_id: UUID, status: str) -> LabOrder:
        variables = {"id": str(lab_order_id), "status": status}
        data = await self._graphql(_UPDATE_STATUS_MUTATION, variables)
        return _to_lab_order(data["updateLabOrderStatus"])
