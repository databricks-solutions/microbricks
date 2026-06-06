# Convenience targets for the healthcare reference architecture.
#
# Most engineering loops use `uv` and per-service `apx dev start` directly.
# These targets exist for the cross-service operations that are awkward to
# script otherwise — currently just dev-environment seeding.

.PHONY: help seed-dev seed-patient seed-provider seed-appointment seed-lab seed-prescription seed-billing seed-tests

help:
	@echo "Available targets:"
	@echo "  seed-dev          — Seed all six dev Lakebase 'production' branches."
	@echo "                       Each step sources services/<svc>/.env, so create"
	@echo "                       those first (copy from .env.example and fill in"
	@echo "                       PGHOST + ENDPOINT_NAME from the dev project)."
	@echo "  seed-<service>    — Seed a single service. patient/provider must run"
	@echo "                       before the dependent ones for chronological sense,"
	@echo "                       though the IDs themselves are deterministic."
	@echo "  seed-tests        — Run the local seed unit tests (no DB required)."

# Order matters: patient + provider have no cross-service refs. Appointment,
# lab, prescription, billing all reference patient_id and/or provider_id —
# those are deterministic UUIDs derived from the entity ordinal, so the
# downstream seeds technically don't need the upstream rows to exist before
# they run, but seeding in this order keeps the demo readable.
seed-dev: seed-patient seed-provider seed-appointment seed-lab seed-prescription seed-billing
	@echo "✓ All six dev databases seeded."

seed-patient:
	@echo "→ Seeding patient_db..."
	@bash -c 'set -a; source services/patient/.env; set +a; uv run python services/patient/seed/seed.py'

seed-provider:
	@echo "→ Seeding provider_db..."
	@bash -c 'set -a; source services/provider/.env; set +a; uv run python services/provider/seed/seed.py'

seed-appointment:
	@echo "→ Seeding appointment_db..."
	@bash -c 'set -a; source services/appointment/.env; set +a; uv run python services/appointment/seed/seed.py'

seed-lab:
	@echo "→ Seeding lab_db..."
	@bash -c 'set -a; source services/lab/.env; set +a; uv run python services/lab/seed/seed.py'

seed-prescription:
	@echo "→ Seeding prescription_db..."
	@bash -c 'set -a; source services/prescription/.env; set +a; uv run python services/prescription/seed/seed.py'

seed-billing:
	@echo "→ Seeding billing_db..."
	@bash -c 'set -a; source services/billing/.env; set +a; uv run python services/billing/seed/seed.py'

seed-tests:
	@uv run pytest tests/seeds -v
