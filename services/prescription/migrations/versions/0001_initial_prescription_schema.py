"""initial prescription schema

Revision ID: 0001
Revises:
Create Date: 2026-06-05

Tables: medication_catalog, prescription, refill_request.
Schema rules from HEALTHCARE_DATA_MODEL.md:
  - UUID PK on every table (gen_random_uuid()).
  - Audit cols: created_at/_by, updated_at/_by, deleted_at.
  - Within-DB FKs are fine; no cross-DB FKs (patient_id /
    prescribing_provider_id / decided_by_provider_id stored as bare UUID).
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
        CREATE TABLE medication_catalog (
            code            TEXT PRIMARY KEY,
            display_name    TEXT NOT NULL,
            default_form    TEXT NOT NULL
                            CHECK (default_form IN ('tablet','capsule','liquid','injection','patch','other')),
            is_controlled   BOOLEAN NOT NULL DEFAULT false
        )
        """
    )

    op.execute(
        """
        CREATE TABLE prescription (
            id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id                  UUID NOT NULL,
            prescribing_provider_id     UUID NOT NULL,
            medication_code             TEXT NOT NULL REFERENCES medication_catalog(code),
            dose_text                   TEXT NOT NULL,
            quantity                    INT NOT NULL,
            refills_remaining           INT NOT NULL DEFAULT 0,
            status                      TEXT NOT NULL
                                        CHECK (status IN ('active','completed','cancelled','expired')),
            start_at                    TIMESTAMPTZ NOT NULL,
            end_at                      TIMESTAMPTZ NULL,
            created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by                  TEXT NOT NULL,
            updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by                  TEXT NOT NULL,
            deleted_at                  TIMESTAMPTZ NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_prescription_patient_status "
        "ON prescription(patient_id, status)"
    )
    op.execute(
        "CREATE INDEX ix_prescription_provider_id "
        "ON prescription(prescribing_provider_id)"
    )
    op.execute(
        "CREATE INDEX ix_prescription_active "
        "ON prescription(patient_id) WHERE status = 'active'"
    )

    op.execute(
        """
        CREATE TABLE refill_request (
            id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            prescription_id             UUID NOT NULL REFERENCES prescription(id) ON DELETE CASCADE,
            requested_at                TIMESTAMPTZ NOT NULL,
            status                      TEXT NOT NULL
                                        CHECK (status IN ('pending','approved','denied')),
            decided_by_provider_id      UUID NULL,
            decided_at                  TIMESTAMPTZ NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_refill_request_prescription_id "
        "ON refill_request(prescription_id)"
    )
    op.execute(
        "CREATE INDEX ix_refill_request_status ON refill_request(status)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS refill_request")
    op.execute("DROP TABLE IF EXISTS prescription")
    op.execute("DROP TABLE IF EXISTS medication_catalog")
