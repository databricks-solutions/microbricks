"""initial provider schema

Revision ID: 0001
Revises:
Create Date: 2026-06-05

Tables: organization, provider, provider_specialty.
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
        CREATE TABLE organization (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name            TEXT NOT NULL,
            kind            TEXT NOT NULL
                            CHECK (kind IN ('clinic','hospital','lab','pharmacy')),
            time_zone       TEXT NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by      TEXT NOT NULL,
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by      TEXT NOT NULL,
            deleted_at      TIMESTAMPTZ NULL
        )
        """
    )
    op.execute("CREATE INDEX ix_organization_kind ON organization(kind)")

    op.execute(
        """
        CREATE TABLE provider (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            npi                 TEXT UNIQUE NOT NULL,
            given_name          TEXT NOT NULL,
            family_name         TEXT NOT NULL,
            credential_suffix   TEXT NULL,
            email               TEXT NOT NULL,
            is_active           BOOLEAN NOT NULL DEFAULT true,
            organization_id     UUID NOT NULL REFERENCES organization(id),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by          TEXT NOT NULL,
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by          TEXT NOT NULL,
            deleted_at          TIMESTAMPTZ NULL
        )
        """
    )
    op.execute("CREATE INDEX ix_provider_npi ON provider(npi)")
    op.execute("CREATE INDEX ix_provider_email ON provider(email)")
    op.execute("CREATE INDEX ix_provider_name ON provider(family_name, given_name)")
    op.execute("CREATE INDEX ix_provider_organization_id ON provider(organization_id)")

    op.execute(
        """
        CREATE TABLE provider_specialty (
            provider_id     UUID NOT NULL REFERENCES provider(id) ON DELETE CASCADE,
            specialty_code  TEXT NOT NULL,
            is_primary      BOOLEAN NOT NULL DEFAULT false,
            PRIMARY KEY (provider_id, specialty_code)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_provider_specialty_code ON provider_specialty(specialty_code)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS provider_specialty")
    op.execute("DROP TABLE IF EXISTS provider")
    op.execute("DROP TABLE IF EXISTS organization")
