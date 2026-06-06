"""Seed appointment_db with visit types and synthetic appointments.

Run from repo root:

    set -a; source services/appointment/.env; set +a
    uv run python services/appointment/seed/seed.py

`patient_id` / `provider_id` come from `ID.patient(i)` / `ID.provider(i)` in
scripts/seeds/_common.py — same algorithm patient-svc and provider-svc seed
with, so the IDs match without any cross-DB query.

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
    NUM_PATIENTS,
    NUM_PROVIDERS,
    SEED_NOW,
    VISIT_TYPES,
    connect,
    operator_email,
)


# Status mix. Mostly completed (history) and booked (future); a few cancellations.
STATUS_MIX = (
    ["completed"] * 10
    + ["booked"] * 5
    + ["cancelled"] * 2
    + ["no_show"] * 1
    + ["arrived"] * 1
    + ["in_progress"] * 1
)


def seed_appointments() -> None:
    operator = operator_email()
    with connect() as conn:
        with conn.cursor() as cur:
            for code, display, duration in VISIT_TYPES:
                cur.execute(
                    """
                    INSERT INTO visit_type (code, display_name, default_duration_minutes)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (code) DO NOTHING
                    """,
                    (code, display, duration),
                )

            for i in range(NUM_APPOINTMENTS):
                appt_id = ID.appointment(i)
                patient_id = ID.patient(i % NUM_PATIENTS)
                provider_id = ID.provider(i % NUM_PROVIDERS)
                visit_code, _, duration = VISIT_TYPES[i % len(VISIT_TYPES)]
                status = STATUS_MIX[i % len(STATUS_MIX)]

                # Spread appointments: half in the past, half in the future.
                # Use a deterministic offset keyed on `i`.
                day_offset = (i - NUM_APPOINTMENTS // 2) * 1
                hour = 9 + (i % 8)  # 9 AM through 4 PM clinic hours
                start = SEED_NOW + timedelta(days=day_offset, hours=hour - 12)
                end = start + timedelta(minutes=duration)

                # Future appointments shouldn't be 'completed' / 'no_show'; map
                # them back to 'booked'. Keeps the demo data internally consistent.
                if start > SEED_NOW and status in ("completed", "no_show", "in_progress", "arrived"):
                    status = "booked"
                if start < SEED_NOW and status == "booked":
                    status = "completed"

                cur.execute(
                    """
                    INSERT INTO appointment (
                        id, patient_id, provider_id, slot_id, visit_type_code,
                        scheduled_start, scheduled_end, status, reason,
                        created_by, updated_by
                    ) VALUES (
                        %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        appt_id,
                        patient_id,
                        provider_id,
                        visit_code,
                        start,
                        end,
                        status,
                        f"seed appointment #{i}",
                        operator,
                        operator,
                    ),
                )

        conn.commit()
        print(  # noqa: T201
            f"appointment seed: {len(VISIT_TYPES)} visit types + "
            f"{NUM_APPOINTMENTS} appointments ensured."
        )


if __name__ == "__main__":
    seed_appointments()
