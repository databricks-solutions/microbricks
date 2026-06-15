"""Typed BFF client for billing-svc via GraphQL."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ._base import _BaseSvcClient, _camel_keys


class Invoice(BaseModel):
    id: UUID
    patient_id: UUID
    appointment_id: UUID | None = None
    total_amount_cents: int
    currency: str
    status: str
    issued_at: datetime
    due_at: datetime | None = None


class InvoiceCreatePayload(BaseModel):
    patient_id: UUID
    appointment_id: UUID | None = None
    total_amount_cents: int
    currency: str = "USD"
    status: str = "draft"


_INVOICE_FIELDS = """
    id
    patientId
    appointmentId
    totalAmountCents
    currency
    status
    issuedAt
    dueAt
"""

_CREATE_MUTATION = """
mutation CreateInvoice($input: InvoiceCreateInput!) {
    createInvoice(input: $input) {
        %s
    }
}
""" % _INVOICE_FIELDS

_UPDATE_STATUS_MUTATION = """
mutation UpdateInvoiceStatus($id: UUID!, $status: String!) {
    updateInvoiceStatus(id: $id, status: $status) {
        %s
    }
}
""" % _INVOICE_FIELDS


def _to_invoice(d: dict) -> Invoice:
    return Invoice(
        id=d["id"],
        patient_id=d["patientId"],
        appointment_id=d["appointmentId"],
        total_amount_cents=d["totalAmountCents"],
        currency=d["currency"],
        status=d["status"],
        issued_at=d["issuedAt"],
        due_at=d["dueAt"],
    )


class BillingClient(_BaseSvcClient):
    def __init__(self, user_token: str, branch: str | None = None):
        super().__init__(user_token, service_slug="billing", branch=branch)

    async def create_invoice(self, payload: InvoiceCreatePayload) -> Invoice:
        variables = {"input": _camel_keys(payload.model_dump(mode="json"))}
        data = await self._graphql(_CREATE_MUTATION, variables)
        return _to_invoice(data["createInvoice"])

    async def update_invoice_status(self, invoice_id: UUID, status: str) -> Invoice:
        variables = {"id": str(invoice_id), "status": status}
        data = await self._graphql(_UPDATE_STATUS_MUTATION, variables)
        return _to_invoice(data["updateInvoiceStatus"])
