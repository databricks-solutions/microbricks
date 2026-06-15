"""Mutation resolvers for the patient service GraphQL API."""
from __future__ import annotations

import strawberry
from strawberry.types import Info

from .context import GraphQLContext
from .types import PatientCreateInput, PatientType


@strawberry.type
class Mutation:
    @strawberry.mutation(description="Register a new patient.")
    async def create_patient(
        self,
        info: Info[GraphQLContext, None],
        input: PatientCreateInput,
    ) -> PatientType:
        ctx = info.context
        pool = await ctx.pool()
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO patient (
                    mrn, given_name, family_name, birth_date,
                    sex_at_birth, gender_identity, preferred_language,
                    email, phone, created_by, updated_by
                ) VALUES (
                    COALESCE(%s, 'MRN-' || substr(replace(gen_random_uuid()::text, '-', ''), 1, 10)),
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id, mrn, given_name, family_name, birth_date, sex_at_birth
                """,
                (
                    input.mrn,
                    input.given_name,
                    input.family_name,
                    input.birth_date,
                    input.sex_at_birth,
                    input.gender_identity,
                    input.preferred_language,
                    input.email,
                    input.phone,
                    ctx.user_email,
                    ctx.user_email,
                ),
            )
            row = await cur.fetchone()
            await conn.commit()
        assert row is not None
        return PatientType(
            id=row[0],
            mrn=row[1],
            given_name=row[2],
            family_name=row[3],
            birth_date=row[4],
            sex_at_birth=row[5],
        )
