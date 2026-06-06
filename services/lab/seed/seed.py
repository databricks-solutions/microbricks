"""Seed lab_db with panels, reference ranges, orders, and results.

Run from repo root:

    set -a; source services/lab/.env; set +a
    uv run python services/lab/seed/seed.py

Cross-service IDs (`patient_id`, `ordering_provider_id`, `appointment_id`)
match the patterns used by patient-svc, provider-svc, appointment-svc seeds.

Idempotent: `ON CONFLICT DO NOTHING` on every insert.
"""
from __future__ import annotations

import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.seeds._common import (  # noqa: E402
    ID,
    LAB_PANELS,
    NUM_APPOINTMENTS,
    NUM_LAB_ORDERS,
    NUM_PATIENTS,
    NUM_PROVIDERS,
    SEED_NOW,
    connect,
    operator_email,
)


# (panel_code, unit, low, high, sex_filter, min_age, max_age)
REFERENCE_RANGES = [
    ("LP-A1C", "%", Decimal("4.0"), Decimal("5.6"), None, None, None),
    ("LP-LIPID", "mg/dL", Decimal("0"), Decimal("200"), None, None, None),
    ("LP-CBC", "10^9/L", Decimal("4.0"), Decimal("11.0"), None, None, None),
    ("LP-BMP", "mmol/L", Decimal("3.5"), Decimal("5.1"), None, None, None),
    ("LP-TSH", "mIU/L", Decimal("0.4"), Decimal("4.0"), None, None, None),
]

# (panel_code, analyte, value_numeric, unit, flag)
SAMPLE_RESULTS = {
    "LP-A1C": ("4548-4", Decimal("6.8"), "%", "high"),
    "LP-LIPID": ("2093-3", Decimal("180"), "mg/dL", None),
    "LP-CBC": ("6690-2", Decimal("7.5"), "10^9/L", None),
    "LP-BMP": ("2823-3", Decimal("4.2"), "mmol/L", None),
    "LP-TSH": ("3016-3", Decimal("2.1"), "mIU/L", None),
}

ORDER_STATUSES = ["resulted"] * 7 + ["ordered", "collected", "cancelled"]


def seed_labs() -> None:
    operator = operator_email()
    with connect() as conn:
        with conn.cursor() as cur:
            for code, display, category in LAB_PANELS:
                cur.execute(
                    """
                    INSERT INTO lab_panel (code, display_name, category)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (code) DO NOTHING
                    """,
                    (code, display, category),
                )

            for i, (panel_code, unit, low, high, sex_filter, min_age, max_age) in enumerate(REFERENCE_RANGES):
                cur.execute(
                    """
                    INSERT INTO reference_range (
                        id, panel_code, unit, low, high, sex_filter,
                        min_age_years, max_age_years
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        ID.reference_range(i),
                        panel_code,
                        unit,
                        low,
                        high,
                        sex_filter,
                        min_age,
                        max_age,
                    ),
                )

            for i in range(NUM_LAB_ORDERS):
                order_id = ID.lab_order(i)
                patient_id = ID.patient(i % NUM_PATIENTS)
                provider_id = ID.provider(i % NUM_PROVIDERS)
                # Tie about half of orders to an appointment.
                appointment_id = (
                    ID.appointment(i % NUM_APPOINTMENTS) if i % 2 == 0 else None
                )
                panel_code, _display, _cat = LAB_PANELS[i % len(LAB_PANELS)]
                status = ORDER_STATUSES[i % len(ORDER_STATUSES)]

                ordered_at = SEED_NOW - timedelta(days=(i * 3) % 90)
                collected_at = (
                    ordered_at + timedelta(hours=2)
                    if status in ("collected", "resulted")
                    else None
                )
                resulted_at = (
                    ordered_at + timedelta(hours=24)
                    if status == "resulted"
                    else None
                )

                cur.execute(
                    """
                    INSERT INTO lab_order (
                        id, patient_id, ordering_provider_id, appointment_id,
                        panel_code, status, ordered_at, collected_at,
                        resulted_at, created_by, updated_by
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        order_id,
                        patient_id,
                        provider_id,
                        appointment_id,
                        panel_code,
                        status,
                        ordered_at,
                        collected_at,
                        resulted_at,
                        operator,
                        operator,
                    ),
                )

                # One result per resulted order.
                if status == "resulted":
                    analyte, value, unit, flag = SAMPLE_RESULTS[panel_code]
                    cur.execute(
                        """
                        INSERT INTO lab_result (
                            id, lab_order_id, analyte_code, value_numeric,
                            value_text, unit, flag, created_by, updated_by
                        ) VALUES (
                            %s, %s, %s, %s, NULL, %s, %s, %s, %s
                        )
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (
                            ID.lab_result(i),
                            order_id,
                            analyte,
                            value,
                            unit,
                            flag,
                            operator,
                            operator,
                        ),
                    )

        conn.commit()
        print(  # noqa: T201
            f"lab seed: {len(LAB_PANELS)} panels + "
            f"{len(REFERENCE_RANGES)} ranges + {NUM_LAB_ORDERS} orders ensured."
        )


if __name__ == "__main__":
    seed_labs()
