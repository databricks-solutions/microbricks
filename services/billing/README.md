# billing-svc

System of record for invoices, payer claims, and payments.

**Owns:** `payer`, `invoice`, `claim`, `payment`
**References (by ID, no FK):** `patient_id` (patient_db), `appointment_id` (appointment_db)
**Lakebase project:** `projects/billing-{dev,test,prod}`

## Local development

```bash
# 1. Spin up a Lakebase feature branch (idempotent)
SLUG=$(./scripts/sanitize-branch-slug.sh "$(git branch --show-current)")
databricks postgres create-branch projects/billing-dev "feat-$SLUG" \
  --json '{"spec":{"source_branch":"projects/billing-dev/branches/production"}}' \
  -p hc-dev

# 2. Configure env
cp .env.example .env
# edit .env — set PGHOST and ENDPOINT_NAME from the create-branch output

# 3. Apply migrations to the feature branch
uv run alembic upgrade head

# 4. Start the dev server
apx dev start

# 5. Smoke check
curl http://localhost:8000/api/v1/healthz
curl -H "X-Forwarded-Access-Token: $(databricks auth token -p hc-dev | jq -r .access_token)" \
  http://localhost:8000/api/v1/invoices
```

See:
- [Architecture](../../ARCHITECTURE.md)
- [Data model](../../HEALTHCARE_DATA_MODEL.md#6-billing-svc--billing_db)
- [Contributing](../../CONTRIBUTING.md)
- [OBO auth canonical patterns](../../.claude/skills/hc-obo-auth/references/canonical-patterns.md)
- [Lakebase branching](../../.claude/skills/hc-lakebase-branching/SKILL.md)

## Layout

```
src/billing/
├── app.py                 # FastAPI entrypoint with lifespan (closes per-user pools)
├── auth.py                # OBO token extraction (X-Forwarded-Access-Token → user)
├── db.py                  # Per-user AsyncConnectionPool (OAuthConnection)
└── routers/
    └── invoices.py        # GET /invoices, GET /invoices/{id}

migrations/
├── env.py                 # Alembic env wired to OBO + Lakebase
└── versions/
    └── 0001_initial_billing_schema.py

tests/
├── unit/test_models.py    # No DB needed; runs in plain pytest
└── integration/test_obo.py  # Conformance: 401 without token, isolation across users

seed/
└── seed.py                # Idempotent synthetic-data loader (~100 invoices + claims + payments).
```

## Seeding

After `alembic upgrade head` against your dev project's `production` branch:

```bash
make seed-billing                    # this service only
# or
make seed-dev                        # all six services in dependency order
```

`seed/seed.py` populates `payer`, `invoice`, `claim`, and `payment` with
deterministic IDs that reference the same patients and appointments as the
other seeds. Re-running is safe (`ON CONFLICT (id) DO NOTHING`).
