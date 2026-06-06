"""Routers depend on user_token via FastAPI Depends; never accept service-principal auth."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import user_email, user_token
from ..db import get_pool

router = APIRouter(tags=["providers"])


class ProviderOut(BaseModel):
    id: UUID
    npi: str
    given_name: str
    family_name: str
    credential_suffix: str | None
    email: str
    is_active: bool
    organization_id: UUID


@router.get("/providers", response_model=list[ProviderOut], operation_id="listProviders")
async def list_providers(email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)]):
    pool = await get_pool(email, token)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT id, npi, given_name, family_name, credential_suffix, email, "
            "is_active, organization_id "
            "FROM provider WHERE deleted_at IS NULL "
            "ORDER BY family_name, given_name LIMIT 200"
        )
        rows = await cur.fetchall()
    return [
        ProviderOut(
            id=r[0],
            npi=r[1],
            given_name=r[2],
            family_name=r[3],
            credential_suffix=r[4],
            email=r[5],
            is_active=r[6],
            organization_id=r[7],
        )
        for r in rows
    ]


@router.get(
    "/providers/{provider_id}",
    response_model=ProviderOut,
    operation_id="getProvider",
)
async def get_provider(
    provider_id: UUID,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
):
    pool = await get_pool(email, token)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT id, npi, given_name, family_name, credential_suffix, email, "
            "is_active, organization_id "
            "FROM provider WHERE id = %s AND deleted_at IS NULL",
            (provider_id,),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Provider not found")
    return ProviderOut(
        id=row[0],
        npi=row[1],
        given_name=row[2],
        family_name=row[3],
        credential_suffix=row[4],
        email=row[5],
        is_active=row[6],
        organization_id=row[7],
    )
