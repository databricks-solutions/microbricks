"""Routers depend on user_token via FastAPI Depends; never accept service-principal auth."""
from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import user_email, user_token
from ..db import get_pool

router = APIRouter(tags=["patients"])


class PatientOut(BaseModel):
    id: UUID
    mrn: str
    given_name: str
    family_name: str
    birth_date: date
    sex_at_birth: str


@router.get("/patients", response_model=list[PatientOut], operation_id="listPatients")
async def list_patients(email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)]):
    pool = await get_pool(email, token)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT id, mrn, given_name, family_name, birth_date, sex_at_birth "
            "FROM patient WHERE deleted_at IS NULL "
            "ORDER BY family_name, given_name LIMIT 200"
        )
        rows = await cur.fetchall()
    return [
        PatientOut(
            id=r[0],
            mrn=r[1],
            given_name=r[2],
            family_name=r[3],
            birth_date=r[4],
            sex_at_birth=r[5],
        )
        for r in rows
    ]


@router.get(
    "/patients/{patient_id}",
    response_model=PatientOut,
    operation_id="getPatient",
)
async def get_patient(
    patient_id: UUID,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
):
    pool = await get_pool(email, token)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT id, mrn, given_name, family_name, birth_date, sex_at_birth "
            "FROM patient WHERE id = %s AND deleted_at IS NULL",
            (patient_id,),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Patient not found")
    return PatientOut(
        id=row[0],
        mrn=row[1],
        given_name=row[2],
        family_name=row[3],
        birth_date=row[4],
        sex_at_birth=row[5],
    )
