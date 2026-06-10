"""Routers depend on user_token via FastAPI Depends; never accept service-principal auth."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import sql
from pydantic import BaseModel, Field

from ..auth import branch_name, user_email, user_token
from ..db import get_pool

router = APIRouter(tags=["lab-orders"])


LabOrderStatus = Literal["ordered", "collected", "resulted", "cancelled"]


class LabOrderOut(BaseModel):
    id: UUID
    patient_id: UUID
    ordering_provider_id: UUID
    appointment_id: UUID | None
    panel_code: str
    status: str
    ordered_at: datetime
    collected_at: datetime | None
    resulted_at: datetime | None


class LabOrderCreate(BaseModel):
    patient_id: UUID
    ordering_provider_id: UUID
    appointment_id: UUID | None = None
    panel_code: str = Field(min_length=1, max_length=64)
    ordered_at: datetime | None = None


class LabOrderStatusUpdate(BaseModel):
    status: LabOrderStatus


class CountOut(BaseModel):
    total: int


class LabOrderPage(BaseModel):
    """Paginated lab-order list. `total` reflects the filter+search
    predicate so callers can drive a pagination control without a second
    `/count` round-trip."""

    items: list[LabOrderOut]
    total: int
    limit: int
    offset: int


@router.get(
    "/lab-orders",
    response_model=LabOrderPage,
    operation_id="listLabOrders",
)
async def list_lab_orders(
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
    patient_id: UUID | None = None,
    status: Annotated[list[str] | None, Query()] = None,
    panel_code: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List lab orders with filter + search + offset pagination.

    `status` is repeatable (`?status=ordered&status=collected`) so the
    "pending" tab on the UI can combine both in a single round-trip.
    `q` matches `panel_code` — patient-name search happens at the BFF.
    """
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)
    bind = {
        "patient_id": patient_id,
        "status": status or None,
        "panel_code": panel_code,
        "q": q,
        "limit": safe_limit,
        "offset": safe_offset,
    }
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            SELECT id, patient_id, ordering_provider_id, appointment_id,
                   panel_code, status, ordered_at, collected_at, resulted_at
            FROM lab_order
            WHERE deleted_at IS NULL
              AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
              AND (%(status)s::text[]   IS NULL OR status     = ANY(%(status)s::text[]))
              AND (%(panel_code)s::text IS NULL OR panel_code = %(panel_code)s::text)
              AND (%(q)s::text IS NULL OR panel_code ILIKE '%%' || %(q)s::text || '%%')
            ORDER BY ordered_at DESC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            bind,
        )
        rows = await cur.fetchall()
        await cur.execute(
            """
            SELECT COUNT(*) FROM lab_order
            WHERE deleted_at IS NULL
              AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
              AND (%(status)s::text[]   IS NULL OR status     = ANY(%(status)s::text[]))
              AND (%(panel_code)s::text IS NULL OR panel_code = %(panel_code)s::text)
              AND (%(q)s::text IS NULL OR panel_code ILIKE '%%' || %(q)s::text || '%%')
            """,
            bind,
        )
        total_row = await cur.fetchone()
    assert total_row is not None
    return LabOrderPage(
        items=[
            LabOrderOut(
                id=r[0],
                patient_id=r[1],
                ordering_provider_id=r[2],
                appointment_id=r[3],
                panel_code=r[4],
                status=r[5],
                ordered_at=r[6],
                collected_at=r[7],
                resulted_at=r[8],
            )
            for r in rows
        ],
        total=int(total_row[0]),
        limit=safe_limit,
        offset=safe_offset,
    )


@router.get(
    "/lab-orders/count",
    response_model=CountOut,
    operation_id="countLabOrders",
)
async def count_lab_orders(
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
    patient_id: UUID | None = None,
    status: Annotated[list[str] | None, Query()] = None,
) -> CountOut:
    """Server-side row count. `status` is repeatable so the BFF can ask for
    e.g. `?status=ordered&status=collected` ("pending") in one round-trip.

    SQL is a single literal (ty-friendly); each filter is gated by
    `<param> IS NULL OR ...` so omitted params short-circuit."""
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            SELECT COUNT(*) FROM lab_order
            WHERE deleted_at IS NULL
              AND (%(patient_id)s::uuid   IS NULL OR patient_id = %(patient_id)s::uuid)
              AND (%(status)s::text[]     IS NULL OR status     = ANY(%(status)s::text[]))
            """,
            {"patient_id": patient_id, "status": status or None},
        )
        row = await cur.fetchone()
    assert row is not None
    return CountOut(total=int(row[0]))


@router.get(
    "/lab-orders/{lab_order_id}",
    response_model=LabOrderOut,
    operation_id="getLabOrder",
)
async def get_lab_order(
    lab_order_id: UUID,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
):
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT id, patient_id, ordering_provider_id, appointment_id, panel_code, "
            "status, ordered_at, collected_at, resulted_at "
            "FROM lab_order WHERE id = %s AND deleted_at IS NULL",
            (lab_order_id,),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Lab order not found")
    return LabOrderOut(
        id=row[0],
        patient_id=row[1],
        ordering_provider_id=row[2],
        appointment_id=row[3],
        panel_code=row[4],
        status=row[5],
        ordered_at=row[6],
        collected_at=row[7],
        resulted_at=row[8],
    )


@router.post(
    "/lab-orders",
    response_model=LabOrderOut,
    status_code=201,
    operation_id="createLabOrder",
)
async def create_lab_order(
    payload: LabOrderCreate,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
) -> LabOrderOut:
    """Order a lab panel.

    `panel_code` must reference an existing row in `lab_panel` (seeded via
    services/lab/seed/seed.py).
    """
    ordered_at = payload.ordered_at or datetime.now(timezone.utc)
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        try:
            await cur.execute(
                """
                INSERT INTO lab_order (
                    patient_id, ordering_provider_id, appointment_id,
                    panel_code, status, ordered_at, created_by, updated_by
                ) VALUES (%s, %s, %s, %s, 'ordered', %s, %s, %s)
                RETURNING id, patient_id, ordering_provider_id, appointment_id,
                          panel_code, status, ordered_at, collected_at, resulted_at
                """,
                (
                    payload.patient_id,
                    payload.ordering_provider_id,
                    payload.appointment_id,
                    payload.panel_code,
                    ordered_at,
                    email,
                    email,
                ),
            )
            row = await cur.fetchone()
            await conn.commit()
        except Exception as exc:
            await conn.rollback()
            if "lab_panel" in str(exc):
                raise HTTPException(422, f"Unknown panel_code: {payload.panel_code}") from exc
            raise
    assert row is not None
    return LabOrderOut(
        id=row[0],
        patient_id=row[1],
        ordering_provider_id=row[2],
        appointment_id=row[3],
        panel_code=row[4],
        status=row[5],
        ordered_at=row[6],
        collected_at=row[7],
        resulted_at=row[8],
    )


@router.patch(
    "/lab-orders/{lab_order_id}/status",
    response_model=LabOrderOut,
    operation_id="updateLabOrderStatus",
)
async def update_lab_order_status(
    lab_order_id: UUID,
    payload: LabOrderStatusUpdate,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
) -> LabOrderOut:
    """Move a lab order through its lifecycle.

    On `collected`, set collected_at = now(). On `resulted`, set resulted_at.
    Cancellation just records the status; no soft delete.
    """
    now = datetime.now(timezone.utc)
    set_clauses: list[sql.SQL] = [
        sql.SQL("status = %s"),
        sql.SQL("updated_at = now()"),
        sql.SQL("updated_by = %s"),
    ]
    args: list[object] = [payload.status, email]
    if payload.status == "collected":
        set_clauses.append(sql.SQL("collected_at = COALESCE(collected_at, %s)"))
        args.append(now)
    elif payload.status == "resulted":
        set_clauses.append(sql.SQL("collected_at = COALESCE(collected_at, %s)"))
        set_clauses.append(sql.SQL("resulted_at = COALESCE(resulted_at, %s)"))
        args.append(now)
        args.append(now)
    args.append(lab_order_id)

    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            sql.SQL("""
            UPDATE lab_order
            SET {}
            WHERE id = %s AND deleted_at IS NULL
            RETURNING id, patient_id, ordering_provider_id, appointment_id,
                      panel_code, status, ordered_at, collected_at, resulted_at
            """).format(sql.SQL(", ").join(set_clauses)),
            tuple(args),
        )
        row = await cur.fetchone()
        await conn.commit()
    if not row:
        raise HTTPException(404, "Lab order not found")
    return LabOrderOut(
        id=row[0],
        patient_id=row[1],
        ordering_provider_id=row[2],
        appointment_id=row[3],
        panel_code=row[4],
        status=row[5],
        ordered_at=row[6],
        collected_at=row[7],
        resulted_at=row[8],
    )
