from __future__ import annotations

from uuid import UUID

import strawberry
from strawberry.types import Info

from .context import GraphQLContext
from .types import InvoiceCreateInput, InvoiceType


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_invoice(
        self,
        info: Info[GraphQLContext, None],
        input: InvoiceCreateInput,
    ) -> InvoiceType:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO invoice (
                    patient_id, appointment_id, total_amount_cents, currency,
                    status, issued_at, due_at, created_by, updated_by
                ) VALUES (%s, %s, %s, %s, %s, COALESCE(%s, now()), %s, %s, %s)
                RETURNING id, patient_id, appointment_id, total_amount_cents,
                          currency, status, issued_at, due_at
                """,
                (
                    input.patient_id, input.appointment_id,
                    input.total_amount_cents, input.currency, input.status,
                    input.issued_at, input.due_at,
                    ctx.user_email, ctx.user_email,
                ),
            )
            row = await cur.fetchone()
            await conn.commit()
        assert row is not None
        return InvoiceType(
            id=row[0], patient_id=row[1], appointment_id=row[2],
            total_amount_cents=row[3], currency=row[4], status=row[5],
            issued_at=row[6], due_at=row[7],
        )

    @strawberry.mutation
    async def update_invoice_status(
        self,
        info: Info[GraphQLContext, None],
        id: UUID,
        status: str,
    ) -> InvoiceType | None:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE invoice
                SET status = %s, updated_at = now(), updated_by = %s
                WHERE id = %s AND deleted_at IS NULL
                RETURNING id, patient_id, appointment_id, total_amount_cents,
                          currency, status, issued_at, due_at
                """,
                (status, ctx.user_email, id),
            )
            row = await cur.fetchone()
            await conn.commit()
        if not row:
            return None
        return InvoiceType(
            id=row[0], patient_id=row[1], appointment_id=row[2],
            total_amount_cents=row[3], currency=row[4], status=row[5],
            issued_at=row[6], due_at=row[7],
        )
