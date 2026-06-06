"""Routers depend on user_token via FastAPI Depends; never accept service-principal auth."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import user_email, user_token
from ..db import get_pool

router = APIRouter(tags=["lab-orders"])


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


@router.get(
    "/lab-orders",
    response_model=list[LabOrderOut],
    operation_id="listLabOrders",
)
async def list_lab_orders(email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)]):
    pool = await get_pool(email, token)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT id, patient_id, ordering_provider_id, appointment_id, panel_code, "
            "status, ordered_at, collected_at, resulted_at "
            "FROM lab_order WHERE deleted_at IS NULL "
            "ORDER BY ordered_at DESC LIMIT 200"
        )
        rows = await cur.fetchall()
    return [
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
    ]


@router.get(
    "/lab-orders/{lab_order_id}",
    response_model=LabOrderOut,
    operation_id="getLabOrder",
)
async def get_lab_order(
    lab_order_id: UUID,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
):
    pool = await get_pool(email, token)
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
