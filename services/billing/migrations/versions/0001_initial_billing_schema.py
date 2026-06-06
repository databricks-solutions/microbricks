"""initial billing schema

Revision ID: 0001
Revises:
Create Date: 2026-06-05

Tables: payer, invoice, claim, payment.
Schema rules from HEALTHCARE_DATA_MODEL.md:
  - UUID PK on every table (gen_random_uuid()).
  - Audit cols: created_at/_by, updated_at/_by, deleted_at.
  - Within-DB FKs are fine; no cross-DB FKs (patient_id / appointment_id
    stored as bare UUID without REFERENCES).
  - CHECK constraints for enum-like columns.
  - All money stored as INT cents.
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
        CREATE TABLE payer (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name            TEXT NOT NULL,
            kind            TEXT NOT NULL
                            CHECK (kind IN ('commercial','medicare','medicaid','self_pay','other'))
        )
        """
    )

    op.execute(
        """
        CREATE TABLE invoice (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id          UUID NOT NULL,
            appointment_id      UUID NULL,
            total_amount_cents  INT NOT NULL,
            currency            TEXT NOT NULL DEFAULT 'USD',
            status              TEXT NOT NULL
                                CHECK (status IN ('draft','sent','partially_paid','paid','void')),
            issued_at           TIMESTAMPTZ NOT NULL,
            due_at              TIMESTAMPTZ NULL,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by          TEXT NOT NULL,
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by          TEXT NOT NULL,
            deleted_at          TIMESTAMPTZ NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_invoice_patient_issued ON invoice(patient_id, issued_at DESC)"
    )
    op.execute("CREATE INDEX ix_invoice_status ON invoice(status)")
    op.execute(
        "CREATE INDEX ix_invoice_outstanding ON invoice(patient_id) "
        "WHERE status IN ('sent','partially_paid')"
    )

    op.execute(
        """
        CREATE TABLE claim (
            id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            invoice_id                  UUID NOT NULL REFERENCES invoice(id) ON DELETE CASCADE,
            payer_id                    UUID NOT NULL REFERENCES payer(id),
            submitted_at                TIMESTAMPTZ NULL,
            status                      TEXT NOT NULL
                                        CHECK (status IN ('draft','submitted','accepted','denied','partially_paid')),
            adjudicated_amount_cents    INT NULL
        )
        """
    )
    op.execute("CREATE INDEX ix_claim_invoice_id ON claim(invoice_id)")
    op.execute("CREATE INDEX ix_claim_payer_id ON claim(payer_id)")

    op.execute(
        """
        CREATE TABLE payment (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            invoice_id      UUID NOT NULL REFERENCES invoice(id) ON DELETE CASCADE,
            claim_id        UUID NULL REFERENCES claim(id),
            amount_cents    INT NOT NULL,
            method          TEXT NOT NULL
                            CHECK (method IN ('card','ach','check','cash','adjustment')),
            received_at     TIMESTAMPTZ NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by      TEXT NOT NULL,
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by      TEXT NOT NULL,
            deleted_at      TIMESTAMPTZ NULL
        )
        """
    )
    op.execute("CREATE INDEX ix_payment_invoice_id ON payment(invoice_id)")
    op.execute("CREATE INDEX ix_payment_received_at ON payment(received_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS payment")
    op.execute("DROP TABLE IF EXISTS claim")
    op.execute("DROP TABLE IF EXISTS invoice")
    op.execute("DROP TABLE IF EXISTS payer")
