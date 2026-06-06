"""Routers depend on user_token via FastAPI Depends; never accept service-principal auth."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import user_email, user_token
from ..db import get_pool

router = APIRouter(tags=["prescriptions"])


class PrescriptionOut(BaseModel):
    id: UUID
    patient_id: UUID
    prescribing_provider_id: UUID
    medication_code: str
    dose_text: str
    quantity: int
    refills_remaining: int
    status: str
    start_at: datetime
    end_at: datetime | None


@router.get(
    "/prescriptions",
    response_model=list[PrescriptionOut],
    operation_id="listPrescriptions",
)
async def list_prescriptions(email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)]):
    pool = await get_pool(email, token)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT id, patient_id, prescribing_provider_id, medication_code, "
            "dose_text, quantity, refills_remaining, status, start_at, end_at "
            "FROM prescription WHERE deleted_at IS NULL "
            "ORDER BY start_at DESC LIMIT 200"
        )
        rows = await cur.fetchall()
    return [
        PrescriptionOut(
            id=r[0],
            patient_id=r[1],
            prescribing_provider_id=r[2],
            medication_code=r[3],
            dose_text=r[4],
            quantity=r[5],
            refills_remaining=r[6],
            status=r[7],
            start_at=r[8],
            end_at=r[9],
        )
        for r in rows
    ]


@router.get(
    "/prescriptions/{prescription_id}",
    response_model=PrescriptionOut,
    operation_id="getPrescription",
)
async def get_prescription(
    prescription_id: UUID,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
):
    pool = await get_pool(email, token)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT id, patient_id, prescribing_provider_id, medication_code, "
            "dose_text, quantity, refills_remaining, status, start_at, end_at "
            "FROM prescription WHERE id = %s AND deleted_at IS NULL",
            (prescription_id,),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Prescription not found")
    return PrescriptionOut(
        id=row[0],
        patient_id=row[1],
        prescribing_provider_id=row[2],
        medication_code=row[3],
        dose_text=row[4],
        quantity=row[5],
        refills_remaining=row[6],
        status=row[7],
        start_at=row[8],
        end_at=row[9],
    )
