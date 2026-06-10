"""Routers depend on user_token via FastAPI Depends; never accept service-principal auth."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import branch_name, user_email, user_token
from ..db import get_pool

router = APIRouter(tags=["prescriptions"])


PrescriptionStatus = Literal["active", "completed", "cancelled", "expired"]


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


class PrescriptionCreate(BaseModel):
    patient_id: UUID
    prescribing_provider_id: UUID
    medication_code: str = Field(min_length=1, max_length=64)
    dose_text: str = Field(min_length=1, max_length=256)
    quantity: int = Field(gt=0, le=1000)
    refills_remaining: int = Field(default=0, ge=0, le=12)
    start_at: datetime | None = None
    end_at: datetime | None = None


class PrescriptionStatusUpdate(BaseModel):
    status: PrescriptionStatus


class CountOut(BaseModel):
    total: int


class PrescriptionPage(BaseModel):
    """Paginated prescription list. `total` reflects the filter+search
    predicate so callers can drive a pagination control without a second
    `/count` round-trip."""

    items: list[PrescriptionOut]
    total: int
    limit: int
    offset: int


@router.get(
    "/prescriptions",
    response_model=PrescriptionPage,
    operation_id="listPrescriptions",
)
async def list_prescriptions(
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
    patient_id: UUID | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List prescriptions with filter + search + offset pagination.

    `q` matches `medication_code` or `dose_text` — patient-name search
    happens at the BFF.
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
            SELECT id, patient_id, prescribing_provider_id, medication_code,
                   dose_text, quantity, refills_remaining, status, start_at, end_at
            FROM prescription
            WHERE deleted_at IS NULL
              AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
              AND (%(status)s::text     IS NULL OR status     = %(status)s::text)
              AND (%(q)s::text IS NULL
                   OR medication_code ILIKE '%%' || %(q)s::text || '%%'
                   OR dose_text       ILIKE '%%' || %(q)s::text || '%%')
            ORDER BY start_at DESC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            bind,
        )
        rows = await cur.fetchall()
        await cur.execute(
            """
            SELECT COUNT(*) FROM prescription
            WHERE deleted_at IS NULL
              AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
              AND (%(status)s::text     IS NULL OR status     = %(status)s::text)
              AND (%(q)s::text IS NULL
                   OR medication_code ILIKE '%%' || %(q)s::text || '%%'
                   OR dose_text       ILIKE '%%' || %(q)s::text || '%%')
            """,
            bind,
        )
        total_row = await cur.fetchone()
    assert total_row is not None
    return PrescriptionPage(
        items=[
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
        ],
        total=int(total_row[0]),
        limit=safe_limit,
        offset=safe_offset,
    )


@router.get(
    "/prescriptions/count",
    response_model=CountOut,
    operation_id="countPrescriptions",
)
async def count_prescriptions(
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
            SELECT COUNT(*) FROM prescription
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
    "/prescriptions/{prescription_id}",
    response_model=PrescriptionOut,
    operation_id="getPrescription",
)
async def get_prescription(
    prescription_id: UUID,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
):
    pool = await get_pool(email, token, branch)
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


@router.post(
    "/prescriptions",
    response_model=PrescriptionOut,
    status_code=201,
    operation_id="createPrescription",
)
async def create_prescription(
    payload: PrescriptionCreate,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
) -> PrescriptionOut:
    """Issue a new prescription.

    `medication_code` must reference an existing row in `medication_catalog`
    (seeded via services/prescription/seed/seed.py).
    """
    start_at = payload.start_at or datetime.now(timezone.utc)
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        try:
            await cur.execute(
                """
                INSERT INTO prescription (
                    patient_id, prescribing_provider_id, medication_code,
                    dose_text, quantity, refills_remaining, status,
                    start_at, end_at, created_by, updated_by
                ) VALUES (%s, %s, %s, %s, %s, %s, 'active', %s, %s, %s, %s)
                RETURNING id, patient_id, prescribing_provider_id, medication_code,
                          dose_text, quantity, refills_remaining, status,
                          start_at, end_at
                """,
                (
                    payload.patient_id,
                    payload.prescribing_provider_id,
                    payload.medication_code,
                    payload.dose_text,
                    payload.quantity,
                    payload.refills_remaining,
                    start_at,
                    payload.end_at,
                    email,
                    email,
                ),
            )
            row = await cur.fetchone()
            await conn.commit()
        except Exception as exc:
            await conn.rollback()
            if "medication_catalog" in str(exc):
                raise HTTPException(
                    422, f"Unknown medication_code: {payload.medication_code}"
                ) from exc
            raise
    assert row is not None
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


@router.patch(
    "/prescriptions/{prescription_id}/status",
    response_model=PrescriptionOut,
    operation_id="updatePrescriptionStatus",
)
async def update_prescription_status(
    prescription_id: UUID,
    payload: PrescriptionStatusUpdate,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
) -> PrescriptionOut:
    """Cancel/complete/expire a prescription."""
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            UPDATE prescription
            SET status = %s, updated_at = now(), updated_by = %s
            WHERE id = %s AND deleted_at IS NULL
            RETURNING id, patient_id, prescribing_provider_id, medication_code,
                      dose_text, quantity, refills_remaining, status,
                      start_at, end_at
            """,
            (payload.status, email, prescription_id),
        )
        row = await cur.fetchone()
        await conn.commit()
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
