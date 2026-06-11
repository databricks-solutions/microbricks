"""CRUD endpoints for patient addresses."""
from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import branch_name, user_email, user_token
from ..db import get_pool

router = APIRouter(tags=["addresses"])


class AddressOut(BaseModel):
    id: UUID
    patient_id: UUID
    kind: str
    line1: str | None
    line2: str | None
    city: str | None
    region: str | None
    postal_code: str | None
    country: str | None


class AddressCreate(BaseModel):
    kind: Literal["home", "work", "billing"]
    line1: str | None = Field(default=None, max_length=256)
    line2: str | None = Field(default=None, max_length=256)
    city: str | None = Field(default=None, max_length=128)
    region: str | None = Field(default=None, max_length=128)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=2)


class AddressUpdate(BaseModel):
    kind: Literal["home", "work", "billing"] | None = None
    line1: str | None = Field(default=None, max_length=256)
    line2: str | None = Field(default=None, max_length=256)
    city: str | None = Field(default=None, max_length=128)
    region: str | None = Field(default=None, max_length=128)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=2)


@router.get(
    "/patients/{patient_id}/addresses",
    response_model=list[AddressOut],
    operation_id="listAddresses",
)
async def list_addresses(
    patient_id: UUID,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
):
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            SELECT id, patient_id, kind, line1, line2, city, region, postal_code, country
            FROM patient_address
            WHERE patient_id = %s AND deleted_at IS NULL
            ORDER BY kind
            """,
            (patient_id,),
        )
        rows = await cur.fetchall()
    return [
        AddressOut(
            id=r[0],
            patient_id=r[1],
            kind=r[2],
            line1=r[3],
            line2=r[4],
            city=r[5],
            region=r[6],
            postal_code=r[7],
            country=r[8],
        )
        for r in rows
    ]


@router.post(
    "/patients/{patient_id}/addresses",
    response_model=AddressOut,
    status_code=201,
    operation_id="createAddress",
)
async def create_address(
    patient_id: UUID,
    payload: AddressCreate,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
) -> AddressOut:
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT 1 FROM patient WHERE id = %s AND deleted_at IS NULL",
            (patient_id,),
        )
        if not await cur.fetchone():
            raise HTTPException(404, "Patient not found")
        await cur.execute(
            """
            INSERT INTO patient_address (
                patient_id, kind, line1, line2, city, region, postal_code, country,
                created_by, updated_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, patient_id, kind, line1, line2, city, region, postal_code, country
            """,
            (
                patient_id,
                payload.kind,
                payload.line1,
                payload.line2,
                payload.city,
                payload.region,
                payload.postal_code,
                payload.country,
                email,
                email,
            ),
        )
        row = await cur.fetchone()
        await conn.commit()
    assert row is not None
    return AddressOut(
        id=row[0],
        patient_id=row[1],
        kind=row[2],
        line1=row[3],
        line2=row[4],
        city=row[5],
        region=row[6],
        postal_code=row[7],
        country=row[8],
    )


@router.put(
    "/patients/{patient_id}/addresses/{address_id}",
    response_model=AddressOut,
    operation_id="updateAddress",
)
async def update_address(
    patient_id: UUID,
    address_id: UUID,
    payload: AddressUpdate,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
) -> AddressOut:
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT 1 FROM patient_address WHERE id = %s AND patient_id = %s AND deleted_at IS NULL",
            (address_id, patient_id),
        )
        if not await cur.fetchone():
            raise HTTPException(404, "Address not found")

        sets: list[str] = ["updated_at = now()", "updated_by = %(email)s"]
        params: dict = {"email": email, "id": address_id, "patient_id": patient_id}

        for field in ("kind", "line1", "line2", "city", "region", "postal_code", "country"):
            value = getattr(payload, field)
            if value is not None:
                sets.append(f"{field} = %({field})s")
                params[field] = value

        await cur.execute(
            f"""
            UPDATE patient_address
            SET {', '.join(sets)}
            WHERE id = %(id)s AND patient_id = %(patient_id)s AND deleted_at IS NULL
            RETURNING id, patient_id, kind, line1, line2, city, region, postal_code, country
            """,
            params,
        )
        row = await cur.fetchone()
        await conn.commit()
    assert row is not None
    return AddressOut(
        id=row[0],
        patient_id=row[1],
        kind=row[2],
        line1=row[3],
        line2=row[4],
        city=row[5],
        region=row[6],
        postal_code=row[7],
        country=row[8],
    )


@router.delete(
    "/patients/{patient_id}/addresses/{address_id}",
    status_code=204,
    operation_id="deleteAddress",
)
async def delete_address(
    patient_id: UUID,
    address_id: UUID,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
):
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            UPDATE patient_address
            SET deleted_at = now(), updated_at = now(), updated_by = %s
            WHERE id = %s AND patient_id = %s AND deleted_at IS NULL
            """,
            (email, address_id, patient_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Address not found")
        await conn.commit()

