"""Routers depend on user_token via FastAPI Depends; never accept service-principal auth."""
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

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


class PatientCreate(BaseModel):
    """Payload for POST /patients. MRN omitted = the service generates one."""

    mrn: str | None = Field(default=None, max_length=64)
    given_name: str = Field(min_length=1, max_length=128)
    family_name: str = Field(min_length=1, max_length=128)
    birth_date: date
    sex_at_birth: Literal["female", "male", "other", "unknown"]
    gender_identity: str | None = None
    preferred_language: str | None = None
    email: str | None = None
    phone: str | None = None


class CountOut(BaseModel):
    total: int


class PatientPage(BaseModel):
    """Paginated patient list. `total` is the *unfiltered* row count for the
    current filter + search predicate (not the size of `items`), so callers
    can drive a pagination control without a second `/count` round-trip."""

    items: list[PatientOut]
    total: int
    limit: int
    offset: int


@router.get(
    "/patients",
    response_model=PatientPage,
    operation_id="listPatients",
)
async def list_patients(
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    q: str | None = None,
    ids: Annotated[list[UUID] | None, Query()] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List patients with optional case-insensitive search and offset
    pagination.

    - `q` matches `given_name`, `family_name`, OR `mrn` via `ILIKE '%q%'`.
    - `ids` is a repeatable batch-resolve filter (`?ids=...&ids=...`) used by
      the BFF to look up just the patients referenced in a page of another
      service's list (e.g. appointments) — avoids fetching the whole table
      to join names.
    - `limit` is hard-capped at 200; offset has no upper bound.
    - SQL is a single literal (ty-friendly); each filter is gated by
      `<param> IS NULL OR ...` so omitted params short-circuit.
    """
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)
    bind = {
        "q": q,
        "ids": [str(i) for i in ids] if ids else None,
        "limit": safe_limit,
        "offset": safe_offset,
    }
    pool = await get_pool(email, token)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            SELECT id, mrn, given_name, family_name, birth_date, sex_at_birth
            FROM patient
            WHERE deleted_at IS NULL
              AND (%(q)s::text IS NULL
                   OR given_name  ILIKE '%%' || %(q)s::text || '%%'
                   OR family_name ILIKE '%%' || %(q)s::text || '%%'
                   OR mrn         ILIKE '%%' || %(q)s::text || '%%')
              AND (%(ids)s::uuid[] IS NULL OR id = ANY(%(ids)s::uuid[]))
            ORDER BY family_name, given_name
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            bind,
        )
        rows = await cur.fetchall()
        await cur.execute(
            """
            SELECT COUNT(*) FROM patient
            WHERE deleted_at IS NULL
              AND (%(q)s::text IS NULL
                   OR given_name  ILIKE '%%' || %(q)s::text || '%%'
                   OR family_name ILIKE '%%' || %(q)s::text || '%%'
                   OR mrn         ILIKE '%%' || %(q)s::text || '%%')
              AND (%(ids)s::uuid[] IS NULL OR id = ANY(%(ids)s::uuid[]))
            """,
            bind,
        )
        total_row = await cur.fetchone()
    assert total_row is not None
    return PatientPage(
        items=[
            PatientOut(
                id=r[0],
                mrn=r[1],
                given_name=r[2],
                family_name=r[3],
                birth_date=r[4],
                sex_at_birth=r[5],
            )
            for r in rows
        ],
        total=int(total_row[0]),
        limit=safe_limit,
        offset=safe_offset,
    )


@router.get("/patients/count", response_model=CountOut, operation_id="countPatients")
async def count_patients(
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
) -> CountOut:
    """Server-side row count so callers (BFF dashboard) don't have to
    pull the full list to get an accurate total."""
    pool = await get_pool(email, token)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute("SELECT COUNT(*) FROM patient WHERE deleted_at IS NULL")
        row = await cur.fetchone()
    assert row is not None
    return CountOut(total=int(row[0]))


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


@router.post(
    "/patients",
    response_model=PatientOut,
    status_code=201,
    operation_id="createPatient",
)
async def create_patient(
    payload: PatientCreate,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
) -> PatientOut:
    """Register a new patient.

    Audit columns (`created_by`, `updated_by`) are set to the calling user's
    email — never accept caller-supplied audit values. Caller-supplied MRN is
    optional; on omit, the DB-side gen_random_uuid() is mapped through a
    short, sortable string the human admin can read.
    """
    pool = await get_pool(email, token)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            INSERT INTO patient (
                mrn, given_name, family_name, birth_date,
                sex_at_birth, gender_identity, preferred_language,
                email, phone, created_by, updated_by
            ) VALUES (
                COALESCE(%s, 'MRN-' || substr(replace(gen_random_uuid()::text, '-', ''), 1, 10)),
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id, mrn, given_name, family_name, birth_date, sex_at_birth
            """,
            (
                payload.mrn,
                payload.given_name,
                payload.family_name,
                payload.birth_date,
                payload.sex_at_birth,
                payload.gender_identity,
                payload.preferred_language,
                payload.email,
                payload.phone,
                email,
                email,
            ),
        )
        row = await cur.fetchone()
        await conn.commit()
    assert row is not None
    return PatientOut(
        id=row[0],
        mrn=row[1],
        given_name=row[2],
        family_name=row[3],
        birth_date=row[4],
        sex_at_birth=row[5],
    )
