from __future__ import annotations

from uuid import UUID

import strawberry
from strawberry.types import Info

from .context import GraphQLContext
from .types import AppointmentCreateInput, AppointmentType


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_appointment(
        self,
        info: Info[GraphQLContext, None],
        input: AppointmentCreateInput,
    ) -> AppointmentType:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO appointment (
                    patient_id, provider_id, visit_type_code,
                    scheduled_start, scheduled_end, status, reason,
                    created_by, updated_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, patient_id, provider_id, visit_type_code,
                          scheduled_start, scheduled_end, status, reason
                """,
                (
                    input.patient_id, input.provider_id, input.visit_type_code,
                    input.scheduled_start, input.scheduled_end, input.status,
                    input.reason, ctx.user_email, ctx.user_email,
                ),
            )
            row = await cur.fetchone()
            await conn.commit()
        assert row is not None
        return AppointmentType(
            id=row[0], patient_id=row[1], provider_id=row[2],
            visit_type_code=row[3], scheduled_start=row[4],
            scheduled_end=row[5], status=row[6], reason=row[7],
        )

    @strawberry.mutation
    async def update_appointment_status(
        self,
        info: Info[GraphQLContext, None],
        id: UUID,
        status: str,
    ) -> AppointmentType | None:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE appointment
                SET status = %s, updated_at = now(), updated_by = %s
                WHERE id = %s AND deleted_at IS NULL
                RETURNING id, patient_id, provider_id, visit_type_code,
                          scheduled_start, scheduled_end, status, reason
                """,
                (status, ctx.user_email, id),
            )
            row = await cur.fetchone()
            await conn.commit()
        if not row:
            return None
        return AppointmentType(
            id=row[0], patient_id=row[1], provider_id=row[2],
            visit_type_code=row[3], scheduled_start=row[4],
            scheduled_end=row[5], status=row[6], reason=row[7],
        )
