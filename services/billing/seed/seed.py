"""Seed billing_db with payers, invoices, claims, and payments.

Run from repo root:

    set -a; source services/billing/.env; set +a
    uv run python services/billing/seed/seed.py

Cross-service IDs (`patient_id`, `appointment_id`) come from `ID.patient(i)`
/ `ID.appointment(i)`, matching the patient and appointment seed scripts.

Idempotent: `ON CONFLICT DO NOTHING` on every insert.
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.seeds._common import (  # noqa: E402
    ID,
    NUM_APPOINTMENTS,
    NUM_INVOICES,
    NUM_PATIENTS,
    PAYERS,
    SEED_NOW,
    connect,
    operator_email,
)


INVOICE_STATUSES = (
    ["paid"] * 4 + ["sent"] * 3 + ["partially_paid"] * 2 + ["draft", "void"]
)
PAYMENT_METHODS = ["card", "ach", "check", "cash"]


def seed_billing() -> None:
    operator = operator_email()
    with connect() as conn:
        with conn.cursor() as cur:
            for i, p in enumerate(PAYERS):
                cur.execute(
                    """
                    INSERT INTO payer (id, name, kind)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (ID.payer(i), p["name"], p["kind"]),
                )

            for i in range(NUM_INVOICES):
                inv_id = ID.invoice(i)
                patient_id = ID.patient(i % NUM_PATIENTS)
                # Tie ~80% of invoices to an appointment.
                appointment_id = (
                    ID.appointment(i % NUM_APPOINTMENTS) if i % 5 != 0 else None
                )
                # Amount: between $42 and $850.
                amount_cents = 4200 + (i * 1731) % 80800
                status = INVOICE_STATUSES[i % len(INVOICE_STATUSES)]
                issued_at = SEED_NOW - timedelta(days=(i * 4) % 180)
                due_at = issued_at + timedelta(days=30)

                cur.execute(
                    """
                    INSERT INTO invoice (
                        id, patient_id, appointment_id, total_amount_cents,
                        currency, status, issued_at, due_at,
                        created_by, updated_by
                    ) VALUES (
                        %s, %s, %s, %s, 'USD', %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        inv_id,
                        patient_id,
                        appointment_id,
                        amount_cents,
                        status,
                        issued_at,
                        due_at,
                        operator,
                        operator,
                    ),
                )

                # One claim per invoice (except self-pay and draft / void).
                payer_kind = PAYERS[i % len(PAYERS)]["kind"]
                if status not in ("draft", "void") and payer_kind != "self_pay":
                    claim_status_cycle = [
                        "submitted",
                        "accepted",
                        "partially_paid",
                        "denied",
                    ]
                    claim_status = claim_status_cycle[i % len(claim_status_cycle)]
                    submitted_at = (
                        issued_at + timedelta(days=1)
                        if claim_status != "draft"
                        else None
                    )
                    adjudicated = (
                        int(amount_cents * 0.85)
                        if claim_status in ("accepted", "partially_paid")
                        else None
                    )
                    cur.execute(
                        """
                        INSERT INTO claim (
                            id, invoice_id, payer_id, submitted_at, status,
                            adjudicated_amount_cents
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (
                            ID.claim(i),
                            inv_id,
                            ID.payer(i % len(PAYERS)),
                            submitted_at,
                            claim_status,
                            adjudicated,
                        ),
                    )

                # One payment for paid / partially_paid invoices.
                if status in ("paid", "partially_paid"):
                    paid_cents = (
                        amount_cents
                        if status == "paid"
                        else int(amount_cents * 0.5)
                    )
                    cur.execute(
                        """
                        INSERT INTO payment (
                            id, invoice_id, claim_id, amount_cents, method,
                            received_at, created_by, updated_by
                        ) VALUES (%s, %s, NULL, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (
                            ID.payment(i),
                            inv_id,
                            paid_cents,
                            PAYMENT_METHODS[i % len(PAYMENT_METHODS)],
                            issued_at + timedelta(days=10),
                            operator,
                            operator,
                        ),
                    )

        conn.commit()
        print(  # noqa: T201
            f"billing seed: {len(PAYERS)} payers + {NUM_INVOICES} invoices "
            f"ensured (with claims + payments)."
        )


if __name__ == "__main__":
    seed_billing()
