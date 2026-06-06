"""Seed patient_db with synthetic patients, addresses, and consent rows.

Run from repo root:

    set -a; source services/patient/.env; set +a
    uv run python services/patient/seed/seed.py

Or via the root Makefile target `seed-dev`. Idempotent: every INSERT uses
`ON CONFLICT (id) DO NOTHING`.

Disclaimer: Every row is fabricated. See HEALTHCARE_DATA_MODEL.md.
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

# Inject repo root onto sys.path so the seed helper imports without making
# scripts/seeds a uv workspace member.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.seeds._common import (  # noqa: E402
    NUM_PATIENTS,
    SEED_NOW,
    connect,
    derived_id,
    operator_email,
    patient_address_row,
    patient_row,
)


def seed_patients() -> None:
    operator = operator_email()
    with connect() as conn:
        with conn.cursor() as cur:
            for i in range(NUM_PATIENTS):
                p = patient_row(i)
                cur.execute(
                    """
                    INSERT INTO patient (
                        id, mrn, given_name, family_name, birth_date,
                        sex_at_birth, gender_identity, preferred_language,
                        email, phone, created_by, updated_by
                    ) VALUES (
                        %(id)s, %(mrn)s, %(given_name)s, %(family_name)s,
                        %(birth_date)s, %(sex_at_birth)s, %(gender_identity)s,
                        %(preferred_language)s, %(email)s, %(phone)s,
                        %(operator)s, %(operator)s
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    {**p, "operator": operator},
                )

                addr = patient_address_row(i, p["id"])
                cur.execute(
                    """
                    INSERT INTO patient_address (
                        id, patient_id, kind, line1, line2, city, region,
                        postal_code, country, created_by, updated_by
                    ) VALUES (
                        %(id)s, %(patient_id)s, %(kind)s, %(line1)s, %(line2)s,
                        %(city)s, %(region)s, %(postal_code)s, %(country)s,
                        %(operator)s, %(operator)s
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    {**addr, "operator": operator},
                )

                # Two consent rows per patient: lab share + billing share.
                # Consent ids are derived deterministically so re-runs are no-ops.
                for kind in ("share_with_lab", "share_with_billing"):
                    cid = derived_id("patient_consent", f"{i}:{kind}")
                    cur.execute(
                        """
                        INSERT INTO patient_consent (
                            id, patient_id, kind, granted, effective_at,
                            created_by, updated_by
                        ) VALUES (
                            %s, %s, %s, true, %s, %s, %s
                        )
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (
                            cid,
                            p["id"],
                            kind,
                            SEED_NOW - timedelta(days=30),
                            operator,
                            operator,
                        ),
                    )

        conn.commit()
        print(f"patient seed: {NUM_PATIENTS} patients ensured "  # noqa: T201
              f"(plus addresses + consents).")


if __name__ == "__main__":
    seed_patients()
