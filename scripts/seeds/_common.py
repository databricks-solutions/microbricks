"""Shared seed primitives used by every services/<svc>/seed/seed.py.

The seed scripts are run by `make seed-dev` against the dev environment's
`production` Lakebase branches, with the operator's CLI OBO token (so audit
columns get a real `created_by` email).

Three things live here:

1. `connect()` — synchronous psycopg connection, password is a Lakebase OAuth
   credential minted from the user's Databricks token. Mirrors the shape of
   `services/<svc>/src/<svc>/db.py:OAuthConnection` but synchronous because
   seed scripts are batch one-shots, not request handlers.

2. `ID` — deterministic UUIDv5 helper. The same key produces the same UUID in
   every process. This is the contract that lets `appointment.seed.py` write
   `patient_id = ID.patient(0)` without consulting `patient_db`. It's the
   *only* coupling between service seeds, and it's by-name not by-row.

3. Generators — Mimesis-backed name/address/phone/etc. The healthcare provider
   has its own preferred-language and demographic mix; the catalogs (lab
   panels, medications, payers, visit types) are hand-authored constants
   because they're tiny and fixed.

Importable from outside the uv workspace (this package is not a workspace
member) — seed scripts inject the repo root onto sys.path before importing.
"""
from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Iterator

import psycopg
from databricks.sdk import WorkspaceClient

# Stable namespace for deterministic UUID derivation. Changing this regenerates
# every cross-service ID — never change it once seeds have run anywhere.
_SEED_NS = uuid.UUID("11111111-2222-3333-4444-555555555555")


class ID:
    """Deterministic UUID factory keyed on (entity, ordinal).

    Cross-service consumers (appointment-svc seeding patient_id) must call
    `ID.patient(i)` with the same `i` the patient seed used. The patient seed
    iterates 0..N-1; downstream seeds pick from the same range.
    """

    @staticmethod
    def _u(prefix: str, i: int) -> uuid.UUID:
        return uuid.uuid5(_SEED_NS, f"{prefix}:{i}")

    @classmethod
    def patient(cls, i: int) -> uuid.UUID:
        return cls._u("patient", i)

    @classmethod
    def provider(cls, i: int) -> uuid.UUID:
        return cls._u("provider", i)

    @classmethod
    def organization(cls, i: int) -> uuid.UUID:
        return cls._u("organization", i)

    @classmethod
    def appointment(cls, i: int) -> uuid.UUID:
        return cls._u("appointment", i)

    @classmethod
    def lab_order(cls, i: int) -> uuid.UUID:
        return cls._u("lab_order", i)

    @classmethod
    def lab_result(cls, i: int) -> uuid.UUID:
        return cls._u("lab_result", i)

    @classmethod
    def reference_range(cls, i: int) -> uuid.UUID:
        return cls._u("reference_range", i)

    @classmethod
    def prescription(cls, i: int) -> uuid.UUID:
        return cls._u("prescription", i)

    @classmethod
    def refill(cls, i: int) -> uuid.UUID:
        return cls._u("refill", i)

    @classmethod
    def invoice(cls, i: int) -> uuid.UUID:
        return cls._u("invoice", i)

    @classmethod
    def payer(cls, i: int) -> uuid.UUID:
        return cls._u("payer", i)

    @classmethod
    def claim(cls, i: int) -> uuid.UUID:
        return cls._u("claim", i)

    @classmethod
    def payment(cls, i: int) -> uuid.UUID:
        return cls._u("payment", i)


def derived_id(prefix: str, key: str | int) -> uuid.UUID:
    """Deterministic id for entities that don't have a slot on `ID` yet.

    Use for within-service rows whose key is a composite (e.g. consent rows
    keyed on patient + kind) — anything cross-service should get a first-class
    method on `ID` so the contract is explicit.
    """
    return uuid.uuid5(_SEED_NS, f"{prefix}:{key}")


# ---------------------------------------------------------------------------
# Volume knobs — single source of truth so seed counts stay in sync across
# services. Override per-script via env vars if you need a smaller smoke run.
# ---------------------------------------------------------------------------
NUM_ORGANIZATIONS = int(os.environ.get("SEED_NUM_ORGS", "2"))
NUM_PROVIDERS = int(os.environ.get("SEED_NUM_PROVIDERS", "5"))
NUM_PATIENTS = int(os.environ.get("SEED_NUM_PATIENTS", "50"))
NUM_APPOINTMENTS = int(os.environ.get("SEED_NUM_APPOINTMENTS", "200"))
NUM_LAB_ORDERS = int(os.environ.get("SEED_NUM_LAB_ORDERS", "60"))
NUM_PRESCRIPTIONS = int(os.environ.get("SEED_NUM_PRESCRIPTIONS", "30"))
NUM_REFILLS = int(os.environ.get("SEED_NUM_REFILLS", "10"))
NUM_INVOICES = int(os.environ.get("SEED_NUM_INVOICES", "100"))


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    """Open a sync psycopg connection to a Lakebase endpoint.

    Reads PGHOST/PGUSER/PGPORT/PGDATABASE/PGSSLMODE/ENDPOINT_NAME from env
    (exactly like the runtime `db.py`), and mints a fresh OAuth credential
    using the operator's CLI token.

    Token resolution order:
      1) LOCAL_DEV_TOKEN — explicit override (mirrors migrations/env.py)
      2) DATABRICKS_TOKEN — picked up by the SDK's default auth chain
      3) Default `WorkspaceClient()` config (profile, OIDC, etc.)
    """
    host = os.environ["PGHOST"]
    user = os.environ["PGUSER"]
    port = os.environ.get("PGPORT", "5432")
    dbname = os.environ.get("PGDATABASE", "databricks_postgres")
    sslmode = os.environ.get("PGSSLMODE", "require")
    endpoint = os.environ["ENDPOINT_NAME"]

    token = os.environ.get("LOCAL_DEV_TOKEN") or os.environ.get("DATABRICKS_TOKEN")
    ws_host = os.environ.get("DATABRICKS_HOST")
    if token and ws_host:
        ws = WorkspaceClient(host=ws_host, token=token)
    else:
        ws = WorkspaceClient()

    cred = ws.postgres.generate_database_credential(endpoint=endpoint)

    conn = psycopg.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=cred.token,
        sslmode=sslmode,
    )
    try:
        yield conn
    finally:
        conn.close()


def operator_email() -> str:
    """Email used in audit columns. Falls back to a marker that an SA can
    grep for to find seeded rows."""
    return os.environ.get("SEED_OPERATOR_EMAIL", "seed-script@hc-demo.local")


# ---------------------------------------------------------------------------
# Synthetic data — names, dates, etc.
# ---------------------------------------------------------------------------
# Reference time: every "now" in the seeded world is anchored to this.
# Concrete value (not Date.now()) so seeds are reproducible and the synthetic
# appointment/invoice timestamps don't drift relative to the demo date.
SEED_NOW = datetime(2026, 6, 5, 12, 0, 0, tzinfo=timezone.utc)


# Demographically diverse name pool. Hand-curated to avoid Mimesis pulling in
# anything resembling a public figure — none of these are intended to match
# real individuals. Order is fixed so derived data is reproducible.
GIVEN_NAMES = [
    "Maya", "Hiroshi", "Aaliyah", "Mateo", "Riley", "Priya", "Jamal", "Saoirse",
    "Wei", "Layla", "Tomás", "Ngozi", "Anders", "Yui", "Diego", "Aisha",
    "Kofi", "Sanne", "Joaquín", "Mei", "Eitan", "Aroha", "Idris", "Linnea",
    "Rashid", "Camila", "Bjorn", "Zara", "Hassan", "Fiona",
    "Arjun", "Naledi", "Theo", "Inès", "Kenji", "Amara", "Soren", "Yara",
    "Esteban", "Hana", "Olu", "Greta", "Tariq", "Min-jun", "Nia", "Felipe",
    "Saskia", "Levi", "Imani", "Beatriz",
]

FAMILY_NAMES = [
    "Okafor", "Tanaka", "Greene", "Vargas", "Kim", "Patel", "Boateng",
    "O'Connor", "Chen", "Hassan", "Costa", "Adeyemi", "Lindqvist", "Sato",
    "Morales", "Mahmood", "Mensah", "de Vries", "Reyes", "Yamamoto",
    "Cohen", "Te Awe Awe", "Achebe", "Eriksson", "Karim", "Silva",
    "Hansen", "Mwangi", "Khan", "Walsh",
    "Singh", "Nkosi", "Romanov", "Dubois", "Watanabe", "Diallo", "Norden",
    "Haddad", "Mendoza", "Ito", "Olawale", "Andersson", "Yousef", "Park",
    "Achterberg", "Souza", "Larsen", "Ahmed", "Castillo", "Nakamura",
]

LANGUAGES = ["en-US", "es-MX", "ja-JP", "zh-CN", "ar-SA", "fr-CA", "pt-BR", "hi-IN"]

CITIES = [
    ("San Francisco", "CA", "94102", "USA"),
    ("Oakland", "CA", "94601", "USA"),
    ("Berkeley", "CA", "94704", "USA"),
    ("San Jose", "CA", "95110", "USA"),
    ("Los Angeles", "CA", "90001", "USA"),
    ("Sacramento", "CA", "95814", "USA"),
    ("Fresno", "CA", "93650", "USA"),
    ("Santa Rosa", "CA", "95401", "USA"),
]


def patient_row(i: int) -> dict:
    """Return a deterministic synthetic patient record."""
    given = GIVEN_NAMES[i % len(GIVEN_NAMES)]
    family = FAMILY_NAMES[(i * 7) % len(FAMILY_NAMES)]
    # Spread birthdates between ~1 and ~85 years before SEED_NOW.
    age_years = 1 + (i * 13) % 85
    bday = SEED_NOW.date() - timedelta(days=age_years * 365 + (i * 11) % 365)
    sex_choices = ["female", "male", "other", "unknown"]
    sex = sex_choices[i % 4]
    gender_choices = [None, "female", "male", "non-binary", None]
    gender = gender_choices[(i * 3) % 5]
    return {
        "id": ID.patient(i),
        "mrn": f"MRN-{1000 + i:04d}",
        "given_name": given,
        "family_name": family,
        "birth_date": bday,
        "sex_at_birth": sex,
        "gender_identity": gender,
        "preferred_language": LANGUAGES[i % len(LANGUAGES)],
        "email": f"{given.lower()}.{family.lower().replace(' ', '').replace(chr(39), '')}@example.org",
        "phone": f"+14155550{(100 + i) % 1000:03d}",
    }


def patient_address_row(i: int, patient_id: uuid.UUID) -> dict:
    city, region, postal, country = CITIES[i % len(CITIES)]
    return {
        # Seed-stable id for ON CONFLICT idempotency.
        "id": uuid.uuid5(_SEED_NS, f"patient_address:{i}"),
        "patient_id": patient_id,
        "kind": "home",
        "line1": f"{100 + i} Mission Street",
        "line2": None,
        "city": city,
        "region": region,
        "postal_code": postal,
        "country": country,
    }


def provider_row(i: int) -> dict:
    given = GIVEN_NAMES[(i * 11) % len(GIVEN_NAMES)]
    family = FAMILY_NAMES[(i * 5) % len(FAMILY_NAMES)]
    suffixes = ["MD", "MD", "NP", "PA-C", "RN"]
    return {
        "id": ID.provider(i),
        "npi": f"{1000000000 + i:010d}",
        "given_name": given,
        "family_name": family,
        "credential_suffix": suffixes[i % len(suffixes)],
        "email": f"{given.lower()}.{family.lower().replace(' ', '').replace(chr(39), '')}@bayhealth.example",
        "is_active": True,
        # Round-robin providers across orgs for a tiny multi-org demo.
        "organization_id": ID.organization(i % NUM_ORGANIZATIONS),
    }


ORGANIZATIONS = [
    {"name": "Bay Family Health", "kind": "clinic", "time_zone": "America/Los_Angeles"},
    {"name": "Riverside Diagnostics", "kind": "lab", "time_zone": "America/New_York"},
    {"name": "Northgate Hospital", "kind": "hospital", "time_zone": "America/Los_Angeles"},
]


def organization_row(i: int) -> dict:
    base = ORGANIZATIONS[i % len(ORGANIZATIONS)]
    return {"id": ID.organization(i), **base}


# Shared catalogs — fixed across envs.
VISIT_TYPES = [
    ("NEW_PATIENT", "New patient intake", 45),
    ("FOLLOW_UP", "Follow-up visit", 20),
    ("TELEHEALTH", "Telehealth visit", 30),
    ("ANNUAL", "Annual physical", 60),
]

LAB_PANELS = [
    ("LP-CBC", "Complete Blood Count", "heme"),
    ("LP-LIPID", "Lipid panel", "chem"),
    ("LP-A1C", "Hemoglobin A1c", "endo"),
    ("LP-BMP", "Basic Metabolic Panel", "chem"),
    ("LP-TSH", "Thyroid stimulating hormone", "endo"),
]

MEDICATION_CATALOG = [
    ("MED-METFORMIN", "Metformin 500 mg", "tablet", False),
    ("MED-ATORVA", "Atorvastatin 20 mg", "tablet", False),
    ("MED-AMOX", "Amoxicillin 500 mg", "capsule", False),
    ("MED-LISINOPRIL", "Lisinopril 10 mg", "tablet", False),
    ("MED-OMEPRAZOLE", "Omeprazole 20 mg", "capsule", False),
    ("MED-OXYCODONE", "Oxycodone 5 mg", "tablet", True),
]

PAYERS = [
    {"name": "Blue Shield", "kind": "commercial"},
    {"name": "Aetna", "kind": "commercial"},
    {"name": "Medicare", "kind": "medicare"},
    {"name": "Medi-Cal", "kind": "medicaid"},
    {"name": "Self-Pay", "kind": "self_pay"},
]


__all__ = [
    "ID",
    "derived_id",
    "NUM_ORGANIZATIONS",
    "NUM_PROVIDERS",
    "NUM_PATIENTS",
    "NUM_APPOINTMENTS",
    "NUM_LAB_ORDERS",
    "NUM_PRESCRIPTIONS",
    "NUM_REFILLS",
    "NUM_INVOICES",
    "SEED_NOW",
    "VISIT_TYPES",
    "LAB_PANELS",
    "MEDICATION_CATALOG",
    "PAYERS",
    "ORGANIZATIONS",
    "GIVEN_NAMES",
    "FAMILY_NAMES",
    "LANGUAGES",
    "CITIES",
    "connect",
    "operator_email",
    "patient_row",
    "patient_address_row",
    "provider_row",
    "organization_row",
]
