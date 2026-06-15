"""Query resolvers for the patient service GraphQL API."""
from __future__ import annotations

from uuid import UUID

import strawberry
from strawberry.types import Info

from .context import GraphQLContext
from .types import PatientPage, PatientType


@strawberry.type
class Query:
    @strawberry.field(description="Paginated patient list with optional search and batch resolve.")
    async def patients(
        self,
        info: Info[GraphQLContext, None],
        q: str | None = None,
        ids: list[UUID] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PatientPage:
        ctx = info.context
        safe_limit = max(1, min(limit, 200))
        safe_offset = max(0, offset)
        bind = {
            "q": q,
            "ids": [str(i) for i in ids] if ids else None,
            "limit": safe_limit,
            "offset": safe_offset,
        }
        pool = await ctx.pool()
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
                PatientType(
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

    @strawberry.field(description="Get a single patient by ID.")
    async def patient(
        self,
        info: Info[GraphQLContext, None],
        id: UUID,
    ) -> PatientType | None:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT id, mrn, given_name, family_name, birth_date, sex_at_birth "
                "FROM patient WHERE id = %s AND deleted_at IS NULL",
                (id,),
            )
            row = await cur.fetchone()
        if not row:
            return None
        return PatientType(
            id=row[0],
            mrn=row[1],
            given_name=row[2],
            family_name=row[3],
            birth_date=row[4],
            sex_at_birth=row[5],
        )

    @strawberry.field(description="Total patient count (unfiltered).")
    async def patient_count(self, info: Info[GraphQLContext, None]) -> int:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM patient WHERE deleted_at IS NULL")
            row = await cur.fetchone()
        assert row is not None
        return int(row[0])
