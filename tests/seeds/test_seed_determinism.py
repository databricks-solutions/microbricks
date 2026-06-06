"""Local checks for the seed primitives — no Lakebase required.

These tests exist because the cross-service ID contract is silent: nothing
in the runtime code asserts that `appointment.patient_id` is the same UUID
that `patient.id` was inserted with. If `_common.ID.patient` ever changes
shape, every downstream seed silently writes to the wrong patient. The
tests below pin the exact UUIDs, so any drift is loud.

The synthetic-data shape tests guard the "no real PHI" promise — they
catch the obvious mistakes (someone hardcoding their own name, MRN
collisions, age distribution collapsing).
"""
from __future__ import annotations

import re
import sys
import uuid
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from scripts.seeds._common import (  # noqa: E402
    FAMILY_NAMES,
    GIVEN_NAMES,
    ID,
    NUM_PATIENTS,
    SEED_NOW,
    derived_id,
    patient_address_row,
    patient_row,
    provider_row,
)


# ---------------------------------------------------------------------------
# Deterministic ID contract
# ---------------------------------------------------------------------------
class TestIDDeterminism:
    """The cross-service ID factory must be stable across runs / processes."""

    def test_patient_id_is_stable(self) -> None:
        # Pinning these values makes drift in the namespace UUID or the key
        # format an immediate test failure rather than a silently broken seed.
        assert str(ID.patient(0)) == "a5694656-df4a-57a1-9d6b-26312d9b36cc"
        assert str(ID.patient(49)) == "8d737f13-726c-573b-b608-22f879d47371"
        assert str(ID.provider(0)) == "5b912d82-543f-5de8-a29f-3a7b5423c3d0"
        assert ID.patient(0) != ID.patient(1)

    def test_each_entity_has_distinct_namespace(self) -> None:
        # If two entities collided, downstream seeds would write rows to the
        # wrong table-row pairing. Verify the 5 most-used factories produce
        # disjoint UUID streams across i = 0..49.
        seen: dict[uuid.UUID, str] = {}
        factories = {
            "patient": ID.patient,
            "provider": ID.provider,
            "organization": ID.organization,
            "appointment": ID.appointment,
            "lab_order": ID.lab_order,
            "prescription": ID.prescription,
            "invoice": ID.invoice,
        }
        for name, factory in factories.items():
            for i in range(NUM_PATIENTS):
                u = factory(i)
                assert u not in seen, (
                    f"collision: {name}({i}) == {seen[u]} produced same UUID {u}"
                )
                seen[u] = f"{name}({i})"

    def test_derived_id_is_namespaced_by_prefix(self) -> None:
        # Different prefixes → different ids, even with same key.
        a = derived_id("foo", 0)
        b = derived_id("bar", 0)
        assert a != b
        # Same prefix + key → identical id.
        assert derived_id("foo", 0) == a

    def test_cross_service_id_stability(self) -> None:
        """Smoke test the contract appointment-svc relies on.

        The seed for appointment-svc writes:
            patient_id  = ID.patient(i % NUM_PATIENTS)
            provider_id = ID.provider(i % NUM_PROVIDERS)

        Re-deriving those values here must produce the exact same UUIDs the
        patient-svc and provider-svc seeds inserted. If this test fails,
        every downstream seed is pointing at non-existent rows.
        """
        # patient seed inserts patients[0..NUM_PATIENTS-1].
        # appointment seed for i=0..199 references patient(i % NUM_PATIENTS).
        for i in range(0, 200, 17):  # arbitrary stride to cover the range
            referenced_pid = ID.patient(i % NUM_PATIENTS)
            inserted_pid = patient_row(i % NUM_PATIENTS)["id"]
            assert referenced_pid == inserted_pid

    def test_provider_row_id_matches_factory(self) -> None:
        # Sanity: the row builder uses the factory, not a fresh uuid4().
        for i in range(5):
            assert provider_row(i)["id"] == ID.provider(i)


# ---------------------------------------------------------------------------
# Synthetic-data shape
# ---------------------------------------------------------------------------
class TestSyntheticDataShape:
    def test_mrn_is_unique_and_well_formed(self) -> None:
        seen = set()
        for i in range(NUM_PATIENTS):
            mrn = patient_row(i)["mrn"]
            assert re.fullmatch(r"MRN-\d{4}", mrn), mrn
            assert mrn not in seen, f"MRN collision at i={i}"
            seen.add(mrn)

    def test_no_obvious_real_pii_in_name_pool(self) -> None:
        # Lightweight guard: anyone editing the name pool to slip in real
        # names would notice this list growing. Not a strong guarantee,
        # but a tripwire.
        forbidden = {
            "Emanuele",  # repo author
            "Rinaldi",
            "Anthropic",
            "Databricks",
        }
        leaked = forbidden.intersection(GIVEN_NAMES) | forbidden.intersection(FAMILY_NAMES)
        assert not leaked, f"Real-name leak in synthetic pool: {leaked}"

    def test_birth_dates_span_a_reasonable_range(self) -> None:
        # If everyone is the same age, the demo looks fake in a different way.
        ages = []
        for i in range(NUM_PATIENTS):
            row = patient_row(i)
            age_days = (SEED_NOW.date() - row["birth_date"]).days
            ages.append(age_days // 365)
        # Pediatric and geriatric should both be represented in a 50-row pool.
        assert min(ages) <= 18, f"min age = {min(ages)}; expected at least one pediatric"
        assert max(ages) >= 60, f"max age = {max(ages)}; expected at least one geriatric"

    def test_sex_at_birth_uses_only_allowed_values(self) -> None:
        allowed = {"female", "male", "other", "unknown"}
        for i in range(NUM_PATIENTS):
            assert patient_row(i)["sex_at_birth"] in allowed

    def test_email_is_lowercased_and_uses_example_org(self) -> None:
        for i in range(NUM_PATIENTS):
            email = patient_row(i)["email"]
            assert email.endswith("@example.org"), email
            assert email == email.lower()

    def test_address_kind_is_home(self) -> None:
        # Only seeding home addresses for now; if we add work/billing the
        # CHECK constraint enforces correctness, but pin the seed shape too.
        for i in range(5):
            row = patient_address_row(i, ID.patient(i))
            assert row["kind"] == "home"
            assert row["country"] == "USA"


@pytest.mark.parametrize(
    "factory_name,index",
    [
        ("patient", 0),
        ("provider", 4),
        ("appointment", 199),
        ("lab_order", 59),
        ("prescription", 29),
        ("invoice", 99),
    ],
)
def test_factory_produces_uuid(factory_name: str, index: int) -> None:
    """Every factory returns a uuid.UUID, not a string."""
    factory = getattr(ID, factory_name)
    result = factory(index)
    assert isinstance(result, uuid.UUID)
    # Version 5 — derived from namespace + name, not random.
    assert result.version == 5
