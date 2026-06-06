"""Routers depend on user_token via FastAPI Depends; never accept service-principal auth."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import user_email, user_token
from ..db import get_pool

router = APIRouter(tags=["appointments"])


class AppointmentOut(BaseModel):
    id: UUID
    patient_id: UUID
    provider_id: UUID
    visit_type_code: str
    scheduled_start: datetime
    scheduled_end: datetime
    status: str
    reason: str | None


@router.get(
    "/appointments",
    response_model=list[AppointmentOut],
    operation_id="listAppointments",
)
async def list_appointments(email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)]):
    pool = await get_pool(email, token)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT id, patient_id, provider_id, visit_type_code, scheduled_start, "
            "scheduled_end, status, reason "
            "FROM appointment WHERE deleted_at IS NULL "
            "ORDER BY scheduled_start DESC LIMIT 200"
        )
        rows = await cur.fetchall()
    return [
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
    ]


@router.get(
    "/appointments/{appointment_id}",
    response_model=AppointmentOut,
    operation_id="getAppointment",
)
async def get_appointment(
    appointment_id: UUID,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
):
    pool = await get_pool(email, token)
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
