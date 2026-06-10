"""Routers depend on user_token via FastAPI Depends; never accept service-principal auth."""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import branch_name, user_email, user_token
from ..db import get_pool

router = APIRouter(tags=["appointments"])


# `appointment.status` check constraint values, kept in lock-step with migration 0001.
APPOINTMENT_STATUSES = (
    "booked",
    "arrived",
    "in_progress",
    "completed",
    "cancelled",
    "no_show",
)
AppointmentStatus = Literal[
    "booked", "arrived", "in_progress", "completed", "cancelled", "no_show"
]


class AppointmentOut(BaseModel):
    id: UUID
    patient_id: UUID
    provider_id: UUID
    visit_type_code: str
    scheduled_start: datetime
    scheduled_end: datetime
    status: str
    reason: str | None


class AppointmentCreate(BaseModel):
    patient_id: UUID
    provider_id: UUID
    visit_type_code: str = Field(min_length=1, max_length=64)
    scheduled_start: datetime
    scheduled_end: datetime
    reason: str | None = None
    status: AppointmentStatus = "booked"


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus


class CountOut(BaseModel):
    total: int


class AppointmentPage(BaseModel):
    """Paginated appointment list. `total` reflects the filter+search
    predicate so the caller can drive a pagination control without a second
    `/count` round-trip."""

    items: list[AppointmentOut]
    total: int
    limit: int
    offset: int


@router.get(
    "/appointments",
    response_model=AppointmentPage,
    operation_id="listAppointments",
)
async def list_appointments(
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
    patient_id: UUID | None = None,
    provider_id: UUID | None = None,
    status: AppointmentStatus | None = None,
    visit_type_code: str | None = None,
    q: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = 50,
    offset: int = 0,
    order: str = "desc",
):
    """List appointments with filter + search + offset pagination.

    Filters are AND-composed and gated by `<param> IS NULL OR ...` so the
    SQL stays a single literal (ty-friendly) and omitted params
    short-circuit. `q` matches `reason` OR `visit_type_code` (the only
    text fields this service owns — patient/provider name search happens at
    the BFF, which combines this list with the patient/provider services).
    `from_date`/`to_date` are inclusive on `scheduled_start::date`.
    """
    direction = "ASC" if order.lower() == "asc" else "DESC"
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)
    bind = {
        "patient_id": patient_id,
        "provider_id": provider_id,
        "status": status,
        "visit_type_code": visit_type_code,
        "q": q,
        "from_date": from_date,
        "to_date": to_date,
        "limit": safe_limit,
        "offset": safe_offset,
    }

    list_sql = f"""
        SELECT id, patient_id, provider_id, visit_type_code, scheduled_start,
               scheduled_end, status, reason
        FROM appointment
        WHERE deleted_at IS NULL
          AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
          AND (%(provider_id)s::uuid IS NULL OR provider_id = %(provider_id)s::uuid)
          AND (%(status)s::text IS NULL OR status = %(status)s::text)
          AND (%(visit_type_code)s::text IS NULL OR visit_type_code = %(visit_type_code)s::text)
          AND (%(q)s::text IS NULL
               OR reason          ILIKE '%%' || %(q)s::text || '%%'
               OR visit_type_code ILIKE '%%' || %(q)s::text || '%%')
          AND (%(from_date)s::date IS NULL OR scheduled_start::date >= %(from_date)s::date)
          AND (%(to_date)s::date   IS NULL OR scheduled_start::date <= %(to_date)s::date)
        ORDER BY scheduled_start {direction}
        LIMIT %(limit)s OFFSET %(offset)s
    """

    count_sql = """
        SELECT COUNT(*) FROM appointment
        WHERE deleted_at IS NULL
          AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
          AND (%(provider_id)s::uuid IS NULL OR provider_id = %(provider_id)s::uuid)
          AND (%(status)s::text IS NULL OR status = %(status)s::text)
          AND (%(visit_type_code)s::text IS NULL OR visit_type_code = %(visit_type_code)s::text)
          AND (%(q)s::text IS NULL
               OR reason          ILIKE '%%' || %(q)s::text || '%%'
               OR visit_type_code ILIKE '%%' || %(q)s::text || '%%')
          AND (%(from_date)s::date IS NULL OR scheduled_start::date >= %(from_date)s::date)
          AND (%(to_date)s::date   IS NULL OR scheduled_start::date <= %(to_date)s::date)
    """

    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(list_sql, bind)
        rows = await cur.fetchall()
        await cur.execute(count_sql, bind)
        total_row = await cur.fetchone()
    assert total_row is not None
    return AppointmentPage(
        items=[
            AppointmentOut(
                id=r[0],
                patient_id=r[1],
                provider_id=r[2],
                visit_type_code=r[3],
                scheduled_start=r[4],
                scheduled_end=r[5],
                status=r[6],
                reason=r[7],
            )
            for r in rows
        ],
        total=int(total_row[0]),
        limit=safe_limit,
        offset=safe_offset,
    )


@router.get(
    "/appointments/count",
    response_model=CountOut,
    operation_id="countAppointments",
)
async def count_appointments(
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
    patient_id: UUID | None = None,
    status: AppointmentStatus | None = None,
    on_date: date | None = None,
) -> CountOut:
    """Server-side row count with the same filter shape as the list endpoint,
    plus an `on_date` filter for the dashboard's "scheduled today" tile.
    Avoids pulling the whole list just to count it.

    SQL is a single literal so ty's `LiteralString` check stays happy; each
    filter is gated by `<param> IS NULL OR <col> = <param>` and short-circuits
    when the caller omits it.
    """
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            SELECT COUNT(*) FROM appointment
            WHERE deleted_at IS NULL
              AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
              AND (%(status)s::text   IS NULL OR status     = %(status)s::text)
              AND (%(on_date)s::date  IS NULL OR scheduled_start::date = %(on_date)s::date)
            """,
            {"patient_id": patient_id, "status": status, "on_date": on_date},
        )
        row = await cur.fetchone()
    assert row is not None
    return CountOut(total=int(row[0]))


@router.get(
    "/appointments/{appointment_id}",
    response_model=AppointmentOut,
    operation_id="getAppointment",
)
async def get_appointment(
    appointment_id: UUID,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
):
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT id, patient_id, provider_id, visit_type_code, scheduled_start, "
            "scheduled_end, status, reason "
            "FROM appointment WHERE id = %s AND deleted_at IS NULL",
            (appointment_id,),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Appointment not found")
    return AppointmentOut(
        id=row[0],
        patient_id=row[1],
        provider_id=row[2],
        visit_type_code=row[3],
        scheduled_start=row[4],
        scheduled_end=row[5],
        status=row[6],
        reason=row[7],
    )


@router.post(
    "/appointments",
    response_model=AppointmentOut,
    status_code=201,
    operation_id="createAppointment",
)
async def create_appointment(
    payload: AppointmentCreate,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
) -> AppointmentOut:
    """Book an appointment.

    `visit_type_code` must reference an existing row in `visit_type` (seeded
    via services/appointment/seed/seed.py). `patient_id` and `provider_id` are
    cross-DB references — we don't validate them here.
    """
    if payload.scheduled_end <= payload.scheduled_start:
        raise HTTPException(422, "scheduled_end must be after scheduled_start")

    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        try:
            await cur.execute(
                """
                INSERT INTO appointment (
                    patient_id, provider_id, visit_type_code,
                    scheduled_start, scheduled_end, status, reason,
                    created_by, updated_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, patient_id, provider_id, visit_type_code,
                          scheduled_start, scheduled_end, status, reason
                """,
                (
                    payload.patient_id,
                    payload.provider_id,
                    payload.visit_type_code,
                    payload.scheduled_start,
                    payload.scheduled_end,
                    payload.status,
                    payload.reason,
                    email,
                    email,
                ),
            )
            row = await cur.fetchone()
            await conn.commit()
        except Exception as exc:
            await conn.rollback()
            msg = str(exc)
            if "visit_type" in msg:
                raise HTTPException(422, f"Unknown visit_type_code: {payload.visit_type_code}") from exc
            raise
    assert row is not None
    return AppointmentOut(
        id=row[0],
        patient_id=row[1],
        provider_id=row[2],
        visit_type_code=row[3],
        scheduled_start=row[4],
        scheduled_end=row[5],
        status=row[6],
        reason=row[7],
    )


@router.patch(
    "/appointments/{appointment_id}/status",
    response_model=AppointmentOut,
    operation_id="updateAppointmentStatus",
)
async def update_appointment_status(
    appointment_id: UUID,
    payload: AppointmentStatusUpdate,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
) -> AppointmentOut:
    """Transition an appointment through its lifecycle.

    We don't enforce a state machine here (booked → arrived → in_progress →
    completed) — the DB CHECK constraint enforces the value set; clinical
    workflow ordering is the caller's responsibility.
    """
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            UPDATE appointment
            SET status = %s, updated_at = now(), updated_by = %s
            WHERE id = %s AND deleted_at IS NULL
            RETURNING id, patient_id, provider_id, visit_type_code,
                      scheduled_start, scheduled_end, status, reason
            """,
            (payload.status, email, appointment_id),
        )
        row = await cur.fetchone()
        await conn.commit()
    if not row:
        raise HTTPException(404, "Appointment not found")
    return AppointmentOut(
        id=row[0],
        patient_id=row[1],
        provider_id=row[2],
        visit_type_code=row[3],
        scheduled_start=row[4],
        scheduled_end=row[5],
        status=row[6],
        reason=row[7],
    )
