"""initial lab schema

Revision ID: 0001
Revises:
Create Date: 2026-06-05

Tables: lab_panel, reference_range, lab_order, lab_result.
Schema rules from HEALTHCARE_DATA_MODEL.md:
  - UUID PK on every table (gen_random_uuid()).
  - Audit cols: created_at/_by, updated_at/_by, deleted_at.
  - Within-DB FKs are fine; no cross-DB FKs (patient_id / provider_id /
    appointment_id stored as bare UUID without REFERENCES).
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
        CREATE TABLE lab_panel (
            code            TEXT PRIMARY KEY,
            display_name    TEXT NOT NULL,
            category        TEXT NOT NULL
                            CHECK (category IN ('chem','heme','endo','micro','other'))
        )
        """
    )

    op.execute(
        """
        CREATE TABLE reference_range (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            panel_code      TEXT NOT NULL REFERENCES lab_panel(code),
            unit            TEXT NOT NULL,
            low             NUMERIC NULL,
            high            NUMERIC NULL,
            sex_filter      TEXT NULL CHECK (sex_filter IN ('female','male')),
            min_age_years   INT NULL,
            max_age_years   INT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_reference_range_panel_code ON reference_range(panel_code)"
    )

    op.execute(
        """
        CREATE TABLE lab_order (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id              UUID NOT NULL,
            ordering_provider_id    UUID NOT NULL,
            appointment_id          UUID NULL,
            panel_code              TEXT NOT NULL REFERENCES lab_panel(code),
            status                  TEXT NOT NULL
                                    CHECK (status IN ('ordered','collected','resulted','cancelled')),
            ordered_at              TIMESTAMPTZ NOT NULL,
            collected_at            TIMESTAMPTZ NULL,
            resulted_at             TIMESTAMPTZ NULL,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by              TEXT NOT NULL,
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by              TEXT NOT NULL,
            deleted_at              TIMESTAMPTZ NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_lab_order_patient_ordered "
        "ON lab_order(patient_id, ordered_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_lab_order_provider_id ON lab_order(ordering_provider_id)"
    )
    op.execute("CREATE INDEX ix_lab_order_status ON lab_order(status)")

    op.execute(
        """
        CREATE TABLE lab_result (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            lab_order_id    UUID NOT NULL REFERENCES lab_order(id) ON DELETE CASCADE,
            analyte_code    TEXT NOT NULL,
            value_numeric   NUMERIC NULL,
            value_text      TEXT NULL,
            unit            TEXT NULL,
            flag            TEXT NULL
                            CHECK (flag IN ('low','high','critical_low','critical_high')),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by      TEXT NOT NULL,
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by      TEXT NOT NULL,
            deleted_at      TIMESTAMPTZ NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_lab_result_lab_order_id ON lab_result(lab_order_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS lab_result")
    op.execute("DROP TABLE IF EXISTS lab_order")
    op.execute("DROP TABLE IF EXISTS reference_range")
    op.execute("DROP TABLE IF EXISTS lab_panel")
