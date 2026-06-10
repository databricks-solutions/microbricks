"""Routers depend on user_token via FastAPI Depends; never accept service-principal auth."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth import branch_name, user_email, user_token
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


class CountOut(BaseModel):
    total: int


class ProviderPage(BaseModel):
    """Paginated provider list. `total` reflects the filter+search predicate
    so callers can render a page count without a second `/count` round-trip."""

    items: list[ProviderOut]
    total: int
    limit: int
    offset: int


@router.get(
    "/providers",
    response_model=ProviderPage,
    operation_id="listProviders",
)
async def list_providers(
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
    q: str | None = None,
    is_active: bool | None = None,
    ids: Annotated[list[UUID] | None, Query()] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List providers with optional search, active-filter, and batch-by-id
    resolution.

    - `q` matches `given_name`, `family_name`, `npi`, OR `email` via ILIKE.
    - `is_active` filters on the activity flag.
    - `ids` lets the BFF batch-resolve providers referenced in another
      service's paginated list (e.g. appointments) without fetching the
      whole table.
    - `limit` is capped at 200.
    """
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)
    bind = {
        "q": q,
        "is_active": is_active,
        "ids": [str(i) for i in ids] if ids else None,
        "limit": safe_limit,
        "offset": safe_offset,
    }
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            SELECT id, npi, given_name, family_name, credential_suffix, email,
                   is_active, organization_id
            FROM provider
            WHERE deleted_at IS NULL
              AND (%(q)s::text IS NULL
                   OR given_name  ILIKE '%%' || %(q)s::text || '%%'
                   OR family_name ILIKE '%%' || %(q)s::text || '%%'
                   OR npi         ILIKE '%%' || %(q)s::text || '%%'
                   OR email       ILIKE '%%' || %(q)s::text || '%%')
              AND (%(is_active)s::bool IS NULL OR is_active = %(is_active)s::bool)
              AND (%(ids)s::uuid[] IS NULL OR id = ANY(%(ids)s::uuid[]))
            ORDER BY family_name, given_name
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            bind,
        )
        rows = await cur.fetchall()
        await cur.execute(
            """
            SELECT COUNT(*) FROM provider
            WHERE deleted_at IS NULL
              AND (%(q)s::text IS NULL
                   OR given_name  ILIKE '%%' || %(q)s::text || '%%'
                   OR family_name ILIKE '%%' || %(q)s::text || '%%'
                   OR npi         ILIKE '%%' || %(q)s::text || '%%'
                   OR email       ILIKE '%%' || %(q)s::text || '%%')
              AND (%(is_active)s::bool IS NULL OR is_active = %(is_active)s::bool)
              AND (%(ids)s::uuid[] IS NULL OR id = ANY(%(ids)s::uuid[]))
            """,
            bind,
        )
        total_row = await cur.fetchone()
    assert total_row is not None
    return ProviderPage(
        items=[
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
        ],
        total=int(total_row[0]),
        limit=safe_limit,
        offset=safe_offset,
    )


@router.get(
    "/providers/count", response_model=CountOut, operation_id="countProviders"
)
async def count_providers(
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
) -> CountOut:
    """Server-side row count so callers (BFF dashboard) don't have to
    pull the full list to get an accurate total."""
    pool = await get_pool(email, token, branch)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute("SELECT COUNT(*) FROM provider WHERE deleted_at IS NULL")
        row = await cur.fetchone()
    assert row is not None
    return CountOut(total=int(row[0]))


@router.get(
    "/providers/{provider_id}",
    response_model=ProviderOut,
    operation_id="getProvider",
)
async def get_provider(
    provider_id: UUID,
    email: Annotated[str, Depends(user_email)],
    token: Annotated[str, Depends(user_token)],
    branch: Annotated[str | None, Depends(branch_name)],
):
    pool = await get_pool(email, token, branch)
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
