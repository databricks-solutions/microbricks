from __future__ import annotations

from uuid import UUID

import strawberry
from strawberry.types import Info

from .context import GraphQLContext
from .types import LabOrderPage, LabOrderType


@strawberry.type
class Query:
    @strawberry.field
    async def lab_orders(
        self,
        info: Info[GraphQLContext, None],
        patient_id: UUID | None = None,
        status: list[str] | None = None,
        panel_code: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> LabOrderPage:
        ctx = info.context
        safe_limit = max(1, min(limit, 200))
        safe_offset = max(0, offset)
        bind = {
            "patient_id": str(patient_id) if patient_id else None,
            "status": status if status else None,
            "panel_code": panel_code,
            "q": q,
            "limit": safe_limit,
            "offset": safe_offset,
        }
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, patient_id, ordering_provider_id, appointment_id,
                       panel_code, status, ordered_at, collected_at, resulted_at
                FROM lab_order
                WHERE deleted_at IS NULL
                  AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
                  AND (%(status)s::text[] IS NULL OR status = ANY(%(status)s::text[]))
                  AND (%(panel_code)s::text IS NULL OR panel_code = %(panel_code)s::text)
                  AND (%(q)s::text IS NULL OR panel_code ILIKE '%%' || %(q)s::text || '%%')
                ORDER BY ordered_at DESC
                LIMIT %(limit)s OFFSET %(offset)s
                """,
                bind,
            )
            rows = await cur.fetchall()
            await cur.execute(
                """
                SELECT COUNT(*) FROM lab_order
                WHERE deleted_at IS NULL
                  AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
                  AND (%(status)s::text[] IS NULL OR status = ANY(%(status)s::text[]))
                  AND (%(panel_code)s::text IS NULL OR panel_code = %(panel_code)s::text)
                  AND (%(q)s::text IS NULL OR panel_code ILIKE '%%' || %(q)s::text || '%%')
                """,
                bind,
            )
            total_row = await cur.fetchone()
        assert total_row is not None
        return LabOrderPage(
            items=[
                LabOrderType(
                    id=r[0], patient_id=r[1], ordering_provider_id=r[2],
                    appointment_id=r[3], panel_code=r[4], status=r[5],
                    ordered_at=r[6], collected_at=r[7], resulted_at=r[8],
                )
                for r in rows
            ],
            total=int(total_row[0]),
            limit=safe_limit,
            offset=safe_offset,
        )

    @strawberry.field
    async def lab_order(self, info: Info[GraphQLContext, None], id: UUID) -> LabOrderType | None:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT id, patient_id, ordering_provider_id, appointment_id, "
                "panel_code, status, ordered_at, collected_at, resulted_at "
                "FROM lab_order WHERE id = %s AND deleted_at IS NULL",
                (id,),
            )
            row = await cur.fetchone()
        if not row:
            return None
        return LabOrderType(
            id=row[0], patient_id=row[1], ordering_provider_id=row[2],
            appointment_id=row[3], panel_code=row[4], status=row[5],
            ordered_at=row[6], collected_at=row[7], resulted_at=row[8],
        )

    @strawberry.field
    async def lab_order_count(
        self,
        info: Info[GraphQLContext, None],
        patient_id: UUID | None = None,
        status: list[str] | None = None,
    ) -> int:
        ctx = info.context
        bind = {
            "patient_id": str(patient_id) if patient_id else None,
            "status": status if status else None,
        }
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT COUNT(*) FROM lab_order
                WHERE deleted_at IS NULL
                  AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
                  AND (%(status)s::text[] IS NULL OR status = ANY(%(status)s::text[]))
                """,
                bind,
            )
            row = await cur.fetchone()
        assert row is not None
        return int(row[0])
