"""Seed prescription_db with medication catalog, prescriptions, and refill requests.

Run from repo root:

    set -a; source services/prescription/.env; set +a
    uv run python services/prescription/seed/seed.py

Cross-service IDs (`patient_id`, `prescribing_provider_id`,
`decided_by_provider_id`) come from `ID.patient(i)` / `ID.provider(i)`,
matching the patient and provider seed scripts.

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
    MEDICATION_CATALOG,
    NUM_PATIENTS,
    NUM_PRESCRIPTIONS,
    NUM_PROVIDERS,
    NUM_REFILLS,
    SEED_NOW,
    connect,
    operator_email,
)


# Status mix — most prescriptions are active.
RX_STATUSES = ["active"] * 6 + ["completed", "cancelled", "expired"]
# Doses cycle through a small pool keyed on medication index.
DOSES = [
    "500 mg PO BID",
    "20 mg PO QD",
    "10 mg PO QD",
    "1 patch q72h",
    "5 mL PO TID",
    "1 cap PO QHS",
]


def seed_prescriptions() -> None:
    operator = operator_email()
    with connect() as conn:
        with conn.cursor() as cur:
            for code, display, form, controlled in MEDICATION_CATALOG:
                cur.execute(
                    """
                    INSERT INTO medication_catalog (
                        code, display_name, default_form, is_controlled
                    ) VALUES (%s, %s, %s, %s)
                    ON CONFLICT (code) DO NOTHING
                    """,
                    (code, display, form, controlled),
                )

            for i in range(NUM_PRESCRIPTIONS):
                rx_id = ID.prescription(i)
                patient_id = ID.patient(i % NUM_PATIENTS)
                provider_id = ID.provider(i % NUM_PROVIDERS)
                med_code, _display, _form, _ctrl = MEDICATION_CATALOG[
                    i % len(MEDICATION_CATALOG)
                ]
                status = RX_STATUSES[i % len(RX_STATUSES)]
                start_at = SEED_NOW - timedelta(days=(i * 7) % 180)
                end_at = (
                    start_at + timedelta(days=90)
                    if status in ("completed", "expired")
                    else None
                )

                cur.execute(
                    """
                    INSERT INTO prescription (
                        id, patient_id, prescribing_provider_id, medication_code,
                        dose_text, quantity, refills_remaining, status,
                        start_at, end_at, created_by, updated_by
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        rx_id,
                        patient_id,
                        provider_id,
                        med_code,
                        DOSES[i % len(DOSES)],
                        30 + (i % 4) * 30,
                        max(0, 5 - (i % 6)),
                        status,
                        start_at,
                        end_at,
                        operator,
                        operator,
                    ),
                )

            # Refill requests reference the first NUM_REFILLS active prescriptions.
            # `decided_by_provider_id` is the same provider that prescribed it (i % NUM_PROVIDERS).
            for i in range(NUM_REFILLS):
                refill_status_cycle = ["pending", "approved", "approved", "denied"]
                status = refill_status_cycle[i % len(refill_status_cycle)]
                requested_at = SEED_NOW - timedelta(days=(i * 5) + 1)
                decided_provider = (
                    ID.provider(i % NUM_PROVIDERS) if status != "pending" else None
                )
                decided_at = (
                    requested_at + timedelta(hours=12) if status != "pending" else None
                )

                cur.execute(
                    """
                    INSERT INTO refill_request (
                        id, prescription_id, requested_at, status,
                        decided_by_provider_id, decided_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        ID.refill(i),
                        ID.prescription(i % NUM_PRESCRIPTIONS),
                        requested_at,
                        status,
                        decided_provider,
                        decided_at,
                    ),
                )

        conn.commit()
        print(  # noqa: T201
            f"prescription seed: {len(MEDICATION_CATALOG)} meds + "
            f"{NUM_PRESCRIPTIONS} prescriptions + {NUM_REFILLS} refill "
            f"requests ensured."
        )


if __name__ == "__main__":
    seed_prescriptions()
