"""initial appointment schema

Revision ID: 0001
Revises:
Create Date: 2026-06-05

Tables: visit_type, appointment_slot, appointment.
Schema rules from HEALTHCARE_DATA_MODEL.md:
  - UUID PK on every table (gen_random_uuid()).
  - Audit cols: created_at/_by, updated_at/_by, deleted_at.
  - Within-DB FKs are fine; no cross-DB FKs (patient_id / provider_id stored
    as bare UUID without REFERENCES).
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
        CREATE TABLE visit_type (
            code                        TEXT PRIMARY KEY,
            display_name                TEXT NOT NULL,
            default_duration_minutes    INT NOT NULL
        )
        """
    )

    op.execute(
        """
        CREATE TABLE appointment_slot (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider_id     UUID NOT NULL,
            start_at        TIMESTAMPTZ NOT NULL,
            end_at          TIMESTAMPTZ NOT NULL,
            is_available    BOOLEAN NOT NULL DEFAULT true,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by      TEXT NOT NULL,
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by      TEXT NOT NULL,
            deleted_at      TIMESTAMPTZ NULL,
            CONSTRAINT uq_slot_provider_start UNIQUE (provider_id, start_at)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_appointment_slot_provider_id ON appointment_slot(provider_id)"
    )
    op.execute(
        "CREATE INDEX ix_appointment_slot_start_at ON appointment_slot(start_at)"
    )

    op.execute(
        """
        CREATE TABLE appointment (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id          UUID NOT NULL,
            provider_id         UUID NOT NULL,
            slot_id             UUID NULL REFERENCES appointment_slot(id),
            visit_type_code     TEXT NOT NULL REFERENCES visit_type(code),
            scheduled_start     TIMESTAMPTZ NOT NULL,
            scheduled_end       TIMESTAMPTZ NOT NULL,
            status              TEXT NOT NULL
                                CHECK (status IN ('booked','arrived','in_progress','completed','cancelled','no_show')),
            reason              TEXT NULL,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by          TEXT NOT NULL,
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by          TEXT NOT NULL,
            deleted_at          TIMESTAMPTZ NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_appointment_patient_scheduled "
        "ON appointment(patient_id, scheduled_start DESC)"
    )
    op.execute(
        "CREATE INDEX ix_appointment_provider_scheduled "
        "ON appointment(provider_id, scheduled_start)"
    )
    op.execute(
        "CREATE INDEX ix_appointment_active_status ON appointment(status) "
        "WHERE status IN ('booked','arrived','in_progress')"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS appointment")
    op.execute("DROP TABLE IF EXISTS appointment_slot")
    op.execute("DROP TABLE IF EXISTS visit_type")
