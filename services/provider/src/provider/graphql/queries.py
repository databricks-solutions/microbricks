from __future__ import annotations

from uuid import UUID

import strawberry
from strawberry.types import Info

from .context import GraphQLContext
from .types import ProviderPage, ProviderType


@strawberry.type
class Query:
    @strawberry.field
    async def providers(
        self,
        info: Info[GraphQLContext, None],
        q: str | None = None,
        is_active: bool | None = None,
        ids: list[UUID] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ProviderPage:
        ctx = info.context
        safe_limit = max(1, min(limit, 200))
        safe_offset = max(0, offset)
        bind = {
            "q": q,
            "is_active": is_active,
            "ids": [str(i) for i in ids] if ids else None,
            "limit": safe_limit,
            "offset": safe_offset,
        }
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, npi, given_name, family_name, credential_suffix,
                       email, is_active, organization_id
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
                ProviderType(
                    id=r[0], npi=r[1], given_name=r[2], family_name=r[3],
                    credential_suffix=r[4], email=r[5], is_active=r[6],
                    organization_id=r[7],
                )
                for r in rows
            ],
            total=int(total_row[0]),
            limit=safe_limit,
            offset=safe_offset,
        )

    @strawberry.field
    async def provider(self, info: Info[GraphQLContext, None], id: UUID) -> ProviderType | None:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT id, npi, given_name, family_name, credential_suffix, "
                "email, is_active, organization_id "
                "FROM provider WHERE id = %s AND deleted_at IS NULL",
                (id,),
            )
            row = await cur.fetchone()
        if not row:
            return None
        return ProviderType(
            id=row[0], npi=row[1], given_name=row[2], family_name=row[3],
            credential_suffix=row[4], email=row[5], is_active=row[6],
            organization_id=row[7],
        )

    @strawberry.field
    async def provider_count(self, info: Info[GraphQLContext, None]) -> int:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM provider WHERE deleted_at IS NULL")
            row = await cur.fetchone()
        assert row is not None
        return int(row[0])
