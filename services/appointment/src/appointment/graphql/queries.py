from __future__ import annotations

from datetime import date
from uuid import UUID

import strawberry
from strawberry.types import Info

from .context import GraphQLContext
from .types import AppointmentPage, AppointmentType


@strawberry.type
class Query:
    @strawberry.field
    async def appointments(
        self,
        info: Info[GraphQLContext, None],
        patient_id: UUID | None = None,
        provider_id: UUID | None = None,
        status: str | None = None,
        visit_type_code: str | None = None,
        q: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
        order: str = "desc",
    ) -> AppointmentPage:
        ctx = info.context
        safe_limit = max(1, min(limit, 200))
        safe_offset = max(0, offset)
        direction = "ASC" if order.lower() == "asc" else "DESC"
        bind = {
            "patient_id": str(patient_id) if patient_id else None,
            "provider_id": str(provider_id) if provider_id else None,
            "status": status,
            "visit_type_code": visit_type_code,
            "q": q,
            "from_date": from_date,
            "to_date": to_date,
            "limit": safe_limit,
            "offset": safe_offset,
        }
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT id, patient_id, provider_id, visit_type_code,
                       scheduled_start, scheduled_end, status, reason
                FROM appointment
                WHERE deleted_at IS NULL
                  AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
                  AND (%(provider_id)s::uuid IS NULL OR provider_id = %(provider_id)s::uuid)
                  AND (%(status)s::text IS NULL OR status = %(status)s::text)
                  AND (%(visit_type_code)s::text IS NULL OR visit_type_code = %(visit_type_code)s::text)
                  AND (%(q)s::text IS NULL
                       OR reason ILIKE '%%' || %(q)s::text || '%%'
                       OR visit_type_code ILIKE '%%' || %(q)s::text || '%%')
                  AND (%(from_date)s::date IS NULL OR scheduled_start::date >= %(from_date)s::date)
                  AND (%(to_date)s::date IS NULL OR scheduled_start::date <= %(to_date)s::date)
                ORDER BY scheduled_start {direction}
                LIMIT %(limit)s OFFSET %(offset)s
                """,
                bind,
            )
            rows = await cur.fetchall()
            await cur.execute(
                """
                SELECT COUNT(*) FROM appointment
                WHERE deleted_at IS NULL
                  AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
                  AND (%(provider_id)s::uuid IS NULL OR provider_id = %(provider_id)s::uuid)
                  AND (%(status)s::text IS NULL OR status = %(status)s::text)
                  AND (%(visit_type_code)s::text IS NULL OR visit_type_code = %(visit_type_code)s::text)
                  AND (%(q)s::text IS NULL
                       OR reason ILIKE '%%' || %(q)s::text || '%%'
                       OR visit_type_code ILIKE '%%' || %(q)s::text || '%%')
                  AND (%(from_date)s::date IS NULL OR scheduled_start::date >= %(from_date)s::date)
                  AND (%(to_date)s::date IS NULL OR scheduled_start::date <= %(to_date)s::date)
                """,
                bind,
            )
            total_row = await cur.fetchone()
        assert total_row is not None
        return AppointmentPage(
            items=[
                AppointmentType(
                    id=r[0], patient_id=r[1], provider_id=r[2],
                    visit_type_code=r[3], scheduled_start=r[4],
                    scheduled_end=r[5], status=r[6], reason=r[7],
                )
                for r in rows
            ],
            total=int(total_row[0]),
            limit=safe_limit,
            offset=safe_offset,
        )

    @strawberry.field
    async def appointment(self, info: Info[GraphQLContext, None], id: UUID) -> AppointmentType | None:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT id, patient_id, provider_id, visit_type_code, "
                "scheduled_start, scheduled_end, status, reason "
                "FROM appointment WHERE id = %s AND deleted_at IS NULL",
                (id,),
            )
            row = await cur.fetchone()
        if not row:
            return None
        return AppointmentType(
            id=row[0], patient_id=row[1], provider_id=row[2],
            visit_type_code=row[3], scheduled_start=row[4],
            scheduled_end=row[5], status=row[6], reason=row[7],
        )

    @strawberry.field
    async def appointment_count(
        self,
        info: Info[GraphQLContext, None],
        patient_id: UUID | None = None,
        status: str | None = None,
    ) -> int:
        ctx = info.context
        bind = {
            "patient_id": str(patient_id) if patient_id else None,
            "status": status,
        }
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT COUNT(*) FROM appointment
                WHERE deleted_at IS NULL
                  AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
                  AND (%(status)s::text IS NULL OR status = %(status)s::text)
                """,
                bind,
            )
            row = await cur.fetchone()
        assert row is not None
        return int(row[0])
