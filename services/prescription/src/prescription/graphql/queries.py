from __future__ import annotations

from uuid import UUID

import strawberry
from strawberry.types import Info

from .context import GraphQLContext
from .types import PrescriptionPage, PrescriptionType


@strawberry.type
class Query:
    @strawberry.field
    async def prescriptions(
        self,
        info: Info[GraphQLContext, None],
        patient_id: UUID | None = None,
        status: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PrescriptionPage:
        ctx = info.context
        safe_limit = max(1, min(limit, 200))
        safe_offset = max(0, offset)
        bind = {
            "patient_id": str(patient_id) if patient_id else None,
            "status": status,
            "q": q,
            "limit": safe_limit,
            "offset": safe_offset,
        }
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, patient_id, prescribing_provider_id, medication_code,
                       dose_text, quantity, refills_remaining, status, start_at, end_at
                FROM prescription
                WHERE deleted_at IS NULL
                  AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
                  AND (%(status)s::text IS NULL OR status = %(status)s::text)
                  AND (%(q)s::text IS NULL
                       OR medication_code ILIKE '%%' || %(q)s::text || '%%'
                       OR dose_text ILIKE '%%' || %(q)s::text || '%%')
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
                  AND (%(status)s::text IS NULL OR status = %(status)s::text)
                  AND (%(q)s::text IS NULL
                       OR medication_code ILIKE '%%' || %(q)s::text || '%%'
                       OR dose_text ILIKE '%%' || %(q)s::text || '%%')
                """,
                bind,
            )
            total_row = await cur.fetchone()
        assert total_row is not None
        return PrescriptionPage(
            items=[
                PrescriptionType(
                    id=r[0], patient_id=r[1], prescribing_provider_id=r[2],
                    medication_code=r[3], dose_text=r[4], quantity=r[5],
                    refills_remaining=r[6], status=r[7], start_at=r[8], end_at=r[9],
                )
                for r in rows
            ],
            total=int(total_row[0]),
            limit=safe_limit,
            offset=safe_offset,
        )

    @strawberry.field
    async def prescription(self, info: Info[GraphQLContext, None], id: UUID) -> PrescriptionType | None:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT id, patient_id, prescribing_provider_id, medication_code, "
                "dose_text, quantity, refills_remaining, status, start_at, end_at "
                "FROM prescription WHERE id = %s AND deleted_at IS NULL",
                (id,),
            )
            row = await cur.fetchone()
        if not row:
            return None
        return PrescriptionType(
            id=row[0], patient_id=row[1], prescribing_provider_id=row[2],
            medication_code=row[3], dose_text=row[4], quantity=row[5],
            refills_remaining=row[6], status=row[7], start_at=row[8], end_at=row[9],
        )

    @strawberry.field
    async def prescription_count(
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
                SELECT COUNT(*) FROM prescription
                WHERE deleted_at IS NULL
                  AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
                  AND (%(status)s::text IS NULL OR status = %(status)s::text)
                """,
                bind,
            )
            row = await cur.fetchone()
        assert row is not None
        return int(row[0])
