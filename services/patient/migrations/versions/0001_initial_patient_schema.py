"""initial patient schema

Revision ID: 0001
Revises:
Create Date: 2026-06-05

Tables: patient, patient_address, patient_consent.
Schema rules from HEALTHCARE_DATA_MODEL.md:
  - UUID PK on every table (gen_random_uuid()).
  - Audit cols: created_at/_by, updated_at/_by, deleted_at.
  - Within-DB FKs are fine; no cross-DB FKs.
  - CHECK constraints for enum-like columns.
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.execute(
        """
        CREATE TABLE patient (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            mrn             TEXT UNIQUE NOT NULL,
            given_name      TEXT NOT NULL,
            family_name     TEXT NOT NULL,
            birth_date      DATE NOT NULL,
            sex_at_birth    TEXT NOT NULL
                            CHECK (sex_at_birth IN ('female','male','other','unknown')),
            gender_identity TEXT NULL,
            preferred_language TEXT NULL,
            email           TEXT NULL,
            phone           TEXT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by      TEXT NOT NULL,
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by      TEXT NOT NULL,
            deleted_at      TIMESTAMPTZ NULL
        )
        """
    )
    op.execute("CREATE INDEX ix_patient_mrn ON patient(mrn)")
    op.execute("CREATE INDEX ix_patient_name ON patient(family_name, given_name)")
    op.execute("CREATE INDEX ix_patient_birth_date ON patient(birth_date)")

    op.execute(
        """
        CREATE TABLE patient_address (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id      UUID NOT NULL REFERENCES patient(id) ON DELETE CASCADE,
            kind            TEXT NOT NULL
                            CHECK (kind IN ('home','work','billing')),
            line1           TEXT NULL,
            line2           TEXT NULL,
            city            TEXT NULL,
            region          TEXT NULL,
            postal_code     TEXT NULL,
            country         TEXT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by      TEXT NOT NULL,
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by      TEXT NOT NULL,
            deleted_at      TIMESTAMPTZ NULL
        )
        """
    )
    op.execute("CREATE INDEX ix_patient_address_patient_id ON patient_address(patient_id)")

    op.execute(
        """
        CREATE TABLE patient_consent (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id      UUID NOT NULL REFERENCES patient(id) ON DELETE CASCADE,
            kind            TEXT NOT NULL
                            CHECK (kind IN ('share_with_lab','share_with_billing','marketing','research')),
            granted         BOOLEAN NOT NULL,
            effective_at    TIMESTAMPTZ NOT NULL,
            expires_at      TIMESTAMPTZ NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by      TEXT NOT NULL,
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by      TEXT NOT NULL,
            deleted_at      TIMESTAMPTZ NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_patient_consent_patient_id ON patient_consent(patient_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS patient_consent")
    op.execute("DROP TABLE IF EXISTS patient_address")
    op.execute("DROP TABLE IF EXISTS patient")
