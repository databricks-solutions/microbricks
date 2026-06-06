"""Seed provider_db with synthetic organizations, providers, and specialties.

Run from repo root:

    set -a; source services/provider/.env; set +a
    uv run python services/provider/seed/seed.py

Idempotent: every INSERT uses `ON CONFLICT DO NOTHING`.

Disclaimer: Every row is fabricated. See HEALTHCARE_DATA_MODEL.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.seeds._common import (  # noqa: E402
    NUM_ORGANIZATIONS,
    NUM_PROVIDERS,
    connect,
    operator_email,
    organization_row,
    provider_row,
)


# Stable specialty rotation. Position N gets these specialties.
SPECIALTIES = [
    [("FAM", True)],                       # provider 0: family medicine
    [("FAM", True), ("ENDO", False)],      # provider 1
    [("CARDIO", True)],                    # provider 2
    [("PEDS", True), ("FAM", False)],      # provider 3
    [("INT", True), ("ENDO", False)],      # provider 4
]


def seed_providers() -> None:
    operator = operator_email()
    with connect() as conn:
        with conn.cursor() as cur:
            for i in range(NUM_ORGANIZATIONS):
                org = organization_row(i)
                cur.execute(
                    """
                    INSERT INTO organization (
                        id, name, kind, time_zone, created_by, updated_by
                    ) VALUES (%(id)s, %(name)s, %(kind)s, %(time_zone)s,
                              %(operator)s, %(operator)s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    {**org, "operator": operator},
                )

            for i in range(NUM_PROVIDERS):
                prv = provider_row(i)
                cur.execute(
                    """
                    INSERT INTO provider (
                        id, npi, given_name, family_name, credential_suffix,
                        email, is_active, organization_id,
                        created_by, updated_by
                    ) VALUES (
                        %(id)s, %(npi)s, %(given_name)s, %(family_name)s,
                        %(credential_suffix)s, %(email)s, %(is_active)s,
                        %(organization_id)s, %(operator)s, %(operator)s
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    {**prv, "operator": operator},
                )

                for code, is_primary in SPECIALTIES[i % len(SPECIALTIES)]:
                    cur.execute(
                        """
                        INSERT INTO provider_specialty (
                            provider_id, specialty_code, is_primary
                        ) VALUES (%s, %s, %s)
                        ON CONFLICT (provider_id, specialty_code) DO NOTHING
                        """,
                        (prv["id"], code, is_primary),
                    )

        conn.commit()
        print(  # noqa: T201
            f"provider seed: {NUM_ORGANIZATIONS} orgs + {NUM_PROVIDERS} "
            f"providers ensured."
        )


if __name__ == "__main__":
    seed_providers()
