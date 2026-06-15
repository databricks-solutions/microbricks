from __future__ import annotations

from uuid import UUID

import strawberry
from strawberry.types import Info

from .context import GraphQLContext
from .types import LabOrderCreateInput, LabOrderType


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_lab_order(
        self,
        info: Info[GraphQLContext, None],
        input: LabOrderCreateInput,
    ) -> LabOrderType:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO lab_order (
                    patient_id, ordering_provider_id, appointment_id,
                    panel_code, status, ordered_at, created_by, updated_by
                ) VALUES (%s, %s, %s, %s, 'ordered', COALESCE(%s, now()), %s, %s)
                RETURNING id, patient_id, ordering_provider_id, appointment_id,
                          panel_code, status, ordered_at, collected_at, resulted_at
                """,
                (
                    input.patient_id, input.ordering_provider_id,
                    input.appointment_id, input.panel_code, input.ordered_at,
                    ctx.user_email, ctx.user_email,
                ),
            )
            row = await cur.fetchone()
            await conn.commit()
        assert row is not None
        return LabOrderType(
            id=row[0], patient_id=row[1], ordering_provider_id=row[2],
            appointment_id=row[3], panel_code=row[4], status=row[5],
            ordered_at=row[6], collected_at=row[7], resulted_at=row[8],
        )

    @strawberry.mutation
    async def update_lab_order_status(
        self,
        info: Info[GraphQLContext, None],
        id: UUID,
        status: str,
    ) -> LabOrderType | None:
        ctx = info.context
        extras = ""
        if status == "collected":
            extras = ", collected_at = COALESCE(collected_at, now())"
        elif status == "resulted":
            extras = ", collected_at = COALESCE(collected_at, now()), resulted_at = COALESCE(resulted_at, now())"
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                f"""
                UPDATE lab_order
                SET status = %s, updated_at = now(), updated_by = %s{extras}
                WHERE id = %s AND deleted_at IS NULL
                RETURNING id, patient_id, ordering_provider_id, appointment_id,
                          panel_code, status, ordered_at, collected_at, resulted_at
                """,
                (status, ctx.user_email, id),
            )
            row = await cur.fetchone()
            await conn.commit()
        if not row:
            return None
        return LabOrderType(
            id=row[0], patient_id=row[1], ordering_provider_id=row[2],
            appointment_id=row[3], panel_code=row[4], status=row[5],
            ordered_at=row[6], collected_at=row[7], resulted_at=row[8],
        )
