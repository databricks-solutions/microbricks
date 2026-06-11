from __future__ import annotations

from uuid import UUID

import strawberry
from strawberry.types import Info

from .context import GraphQLContext
from .types import InvoicePage, InvoiceType


@strawberry.type
class Query:
    @strawberry.field
    async def invoices(
        self,
        info: Info[GraphQLContext, None],
        patient_id: UUID | None = None,
        status: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> InvoicePage:
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
                SELECT id, patient_id, appointment_id, total_amount_cents,
                       currency, status, issued_at, due_at
                FROM invoice
                WHERE deleted_at IS NULL
                  AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
                  AND (%(status)s::text IS NULL OR status = %(status)s::text)
                  AND (%(q)s::text IS NULL
                       OR currency ILIKE '%%' || %(q)s::text || '%%'
                       OR total_amount_cents::text ILIKE '%%' || %(q)s::text || '%%')
                ORDER BY issued_at DESC
                LIMIT %(limit)s OFFSET %(offset)s
                """,
                bind,
            )
            rows = await cur.fetchall()
            await cur.execute(
                """
                SELECT COUNT(*) FROM invoice
                WHERE deleted_at IS NULL
                  AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
                  AND (%(status)s::text IS NULL OR status = %(status)s::text)
                  AND (%(q)s::text IS NULL
                       OR currency ILIKE '%%' || %(q)s::text || '%%'
                       OR total_amount_cents::text ILIKE '%%' || %(q)s::text || '%%')
                """,
                bind,
            )
            total_row = await cur.fetchone()
        assert total_row is not None
        return InvoicePage(
            items=[
                InvoiceType(
                    id=r[0], patient_id=r[1], appointment_id=r[2],
                    total_amount_cents=r[3], currency=r[4], status=r[5],
                    issued_at=r[6], due_at=r[7],
                )
                for r in rows
            ],
            total=int(total_row[0]),
            limit=safe_limit,
            offset=safe_offset,
        )

    @strawberry.field
    async def invoice(self, info: Info[GraphQLContext, None], id: UUID) -> InvoiceType | None:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT id, patient_id, appointment_id, total_amount_cents, "
                "currency, status, issued_at, due_at "
                "FROM invoice WHERE id = %s AND deleted_at IS NULL",
                (id,),
            )
            row = await cur.fetchone()
        if not row:
            return None
        return InvoiceType(
            id=row[0], patient_id=row[1], appointment_id=row[2],
            total_amount_cents=row[3], currency=row[4], status=row[5],
            issued_at=row[6], due_at=row[7],
        )

    @strawberry.field
    async def invoice_count(
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
                SELECT COUNT(*) FROM invoice
                WHERE deleted_at IS NULL
                  AND (%(patient_id)s::uuid IS NULL OR patient_id = %(patient_id)s::uuid)
                  AND (%(status)s::text IS NULL OR status = %(status)s::text)
                """,
                bind,
            )
            row = await cur.fetchone()
        assert row is not None
        return int(row[0])
