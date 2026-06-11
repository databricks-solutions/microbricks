from __future__ import annotations

from uuid import UUID

import strawberry
from strawberry.types import Info

from .context import GraphQLContext
from .types import PrescriptionCreateInput, PrescriptionType


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_prescription(
        self,
        info: Info[GraphQLContext, None],
        input: PrescriptionCreateInput,
    ) -> PrescriptionType:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO prescription (
                    patient_id, prescribing_provider_id, medication_code,
                    dose_text, quantity, refills_remaining, status,
                    start_at, end_at, created_by, updated_by
                ) VALUES (%s, %s, %s, %s, %s, %s, 'active', COALESCE(%s, now()), %s, %s, %s)
                RETURNING id, patient_id, prescribing_provider_id, medication_code,
                          dose_text, quantity, refills_remaining, status, start_at, end_at
                """,
                (
                    input.patient_id, input.prescribing_provider_id,
                    input.medication_code, input.dose_text, input.quantity,
                    input.refills_remaining, input.start_at, input.end_at,
                    ctx.user_email, ctx.user_email,
                ),
            )
            row = await cur.fetchone()
            await conn.commit()
        assert row is not None
        return PrescriptionType(
            id=row[0], patient_id=row[1], prescribing_provider_id=row[2],
            medication_code=row[3], dose_text=row[4], quantity=row[5],
            refills_remaining=row[6], status=row[7], start_at=row[8], end_at=row[9],
        )

    @strawberry.mutation
    async def update_prescription_status(
        self,
        info: Info[GraphQLContext, None],
        id: UUID,
        status: str,
    ) -> PrescriptionType | None:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE prescription
                SET status = %s, updated_at = now(), updated_by = %s
                WHERE id = %s AND deleted_at IS NULL
                RETURNING id, patient_id, prescribing_provider_id, medication_code,
                          dose_text, quantity, refills_remaining, status, start_at, end_at
                """,
                (status, ctx.user_email, id),
            )
            row = await cur.fetchone()
            await conn.commit()
        if not row:
            return None
        return PrescriptionType(
            id=row[0], patient_id=row[1], prescribing_provider_id=row[2],
            medication_code=row[3], dose_text=row[4], quantity=row[5],
            refills_remaining=row[6], status=row[7], start_at=row[8], end_at=row[9],
        )
