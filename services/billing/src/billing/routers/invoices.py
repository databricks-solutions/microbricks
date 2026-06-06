"""Routers depend on user_token via FastAPI Depends; never accept service-principal auth."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import user_email, user_token
from ..db import get_pool

router = APIRouter(tags=["invoices"])


class InvoiceOut(BaseModel):
    id: UUID
    patient_id: UUID
    appointment_id: UUID | None
    total_amount_cents: int
    currency: str
    status: str
    issued_at: datetime
    due_at: datetime | None


@router.get(
    "/invoices",
    response_model=list[InvoiceOut],
    operation_id="listInvoices",
)
async def list_invoices(email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)]):
    pool = await get_pool(email, token)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT id, patient_id, appointment_id, total_amount_cents, currency, "
            "status, issued_at, due_at "
            "FROM invoice WHERE deleted_at IS NULL "
            "ORDER BY issued_at DESC LIMIT 200"
        )
        rows = await cur.fetchall()
    return [
        InvoiceOut(
            id=r[0],
            patient_id=r[1],
            appointment_id=r[2],
            total_amount_cents=r[3],
            currency=r[4],
            status=r[5],
            issued_at=r[6],
            due_at=r[7],
        )
        for r in rows
    ]


@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceOut,
    operation_id="getInvoice",
)
async def get_invoice(
    invoice_id: UUID,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
):
    pool = await get_pool(email, token)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT id, patient_id, appointment_id, total_amount_cents, currency, "
            "status, issued_at, due_at "
            "FROM invoice WHERE id = %s AND deleted_at IS NULL",
            (invoice_id,),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Invoice not found")
    return InvoiceOut(
        id=row[0],
        patient_id=row[1],
        appointment_id=row[2],
        total_amount_cents=row[3],
        currency=row[4],
        status=row[5],
        issued_at=row[6],
        due_at=row[7],
    )
