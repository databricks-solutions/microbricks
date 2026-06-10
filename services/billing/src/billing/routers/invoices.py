"""Routers depend on user_token via FastAPI Depends; never accept service-principal auth."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import branch_name, user_email, user_token
from ..db import get_pool

router = APIRouter(tags=["invoices"])


InvoiceStatus = Literal["draft", "sent", "partially_paid", "paid", "void"]


class InvoiceOut(BaseModel):
    id: UUID
    patient_id: UUID
    appointment_id: UUID | None
    total_amount_cents: int
    currency: str
    status: str
    issued_at: datetime
    due_at: datetime | None


class InvoiceCreate(BaseModel):
    patient_id: UUID
    appointment_id: UUID | None = None
    total_amount_cents: int = Field(gt=0, le=10_000_000)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    status: InvoiceStatus = "draft"
    issued_at: datetime | None = None
    due_at: datetime | None = None


class InvoiceStatusUpdate(BaseModel):
    status: InvoiceStatus


class CountOut(BaseModel):
    total: int


class InvoicePage(BaseModel):
    """Paginated invoice list. `total` reflects the filter+search predicate
    so callers can drive a pagination control without a second `/count`
    round-trip."""

    items: list[InvoiceOut]
    total: int
    limit: int
    offset: int


@router.get(
    "/invoices",
    response_model=InvoicePage,
    operation_id="listInvoices",
)
async def list_invoices(
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
    patient_id: UUID | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List invoices with filter + search + offset pagination.

    `q` matches `currency` or the stringified amount on the cents column —
    patient-name search happens at the BFF (which knows the patient
    directory). All filters are gated by `<param> IS NULL OR ...` so SQL
    stays a single literal and omitted params short-circuit.
    """
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)
    bind = {
        "patient_id": patient_id,
        "status": status,
        "q": q,
        "limit": safe_limit,
        "offset": safe_offset,
    }
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            SELECT id, patient_id, appointment_id, total_amount_cents, currency,
                   status, issued_at, due_at
            FROM invoice
            WHERE deleted_at IS NULL
              AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
              AND (%(status)s::text IS NULL OR status = %(status)s::text)
              AND (%(q)s::text IS NULL
                   OR currency ILIKE '%%' || %(q)s::text || '%%'
                   OR total_amount_cents::text ILIKE '%%' || %(q)s::text || '%%')
            ORDER BY issued_at DESC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            bind,
        )
        rows = await cur.fetchall()
        await cur.execute(
            """
            SELECT COUNT(*) FROM invoice
            WHERE deleted_at IS NULL
              AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
              AND (%(status)s::text IS NULL OR status = %(status)s::text)
              AND (%(q)s::text IS NULL
                   OR currency ILIKE '%%' || %(q)s::text || '%%'
                   OR total_amount_cents::text ILIKE '%%' || %(q)s::text || '%%')
            """,
            bind,
        )
        total_row = await cur.fetchone()
    assert total_row is not None
    return InvoicePage(
        items=[
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
        ],
        total=int(total_row[0]),
        limit=safe_limit,
        offset=safe_offset,
    )


@router.get(
    "/invoices/count",
    response_model=CountOut,
    operation_id="countInvoices",
)
async def count_invoices(
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
    patient_id: UUID | None = None,
    status: str | None = None,
) -> CountOut:
    """Server-side row count with the same filter shape as the list endpoint.

    SQL is a single literal (ty-friendly); each filter is gated by
    `<param> IS NULL OR <col> = <param>` and short-circuits when omitted."""
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            SELECT COUNT(*) FROM invoice
            WHERE deleted_at IS NULL
              AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
              AND (%(status)s::text     IS NULL OR status     = %(status)s::text)
            """,
            {"patient_id": patient_id, "status": status},
        )
        row = await cur.fetchone()
    assert row is not None
    return CountOut(total=int(row[0]))


@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceOut,
    operation_id="getInvoice",
)
async def get_invoice(
    invoice_id: UUID,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
):
    pool = await get_pool(email, token, branch)
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


@router.post(
    "/invoices",
    response_model=InvoiceOut,
    status_code=201,
    operation_id="createInvoice",
)
async def create_invoice(
    payload: InvoiceCreate,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
) -> InvoiceOut:
    """Issue a new invoice."""
    issued_at = payload.issued_at or datetime.now(timezone.utc)
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            INSERT INTO invoice (
                patient_id, appointment_id, total_amount_cents, currency,
                status, issued_at, due_at, created_by, updated_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, patient_id, appointment_id, total_amount_cents,
                      currency, status, issued_at, due_at
            """,
            (
                payload.patient_id,
                payload.appointment_id,
                payload.total_amount_cents,
                payload.currency,
                payload.status,
                issued_at,
                payload.due_at,
                email,
                email,
            ),
        )
        row = await cur.fetchone()
        await conn.commit()
    assert row is not None
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


@router.patch(
    "/invoices/{invoice_id}/status",
    response_model=InvoiceOut,
    operation_id="updateInvoiceStatus",
)
async def update_invoice_status(
    invoice_id: UUID,
    payload: InvoiceStatusUpdate,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
) -> InvoiceOut:
    """Move an invoice through its lifecycle."""
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            UPDATE invoice
            SET status = %s, updated_at = now(), updated_by = %s
            WHERE id = %s AND deleted_at IS NULL
            RETURNING id, patient_id, appointment_id, total_amount_cents,
                      currency, status, issued_at, due_at
            """,
            (payload.status, email, invoice_id),
        )
        row = await cur.fetchone()
        await conn.commit()
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
