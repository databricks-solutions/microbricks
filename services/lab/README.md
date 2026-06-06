# lab-svc

System of record for lab orders, results, and reference ranges.

**Owns:** `lab_panel`, `reference_range`, `lab_order`, `lab_result`
**References (by ID, no FK):** `patient_id` (patient_db), `provider_id` (provider_db), `appointment_id` (appointment_db)
**Lakebase project:** `projects/lab-{dev,test,prod}`

## Local development

```bash
# 1. Spin up a Lakebase feature branch (idempotent)
SLUG=$(./scripts/sanitize-branch-slug.sh "$(git branch --show-current)")
databricks postgres create-branch projects/lab-dev "feat-$SLUG" \
  --json '{"spec":{"source_branch":"projects/lab-dev/branches/production"}}' \
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
  http://localhost:8000/api/v1/lab-orders
```

See:
- [Architecture](../../ARCHITECTURE.md)
- [Data model](../../HEALTHCARE_DATA_MODEL.md#4-lab-svc--lab_db)
- [Contributing](../../CONTRIBUTING.md)
- [OBO auth canonical patterns](../../.claude/skills/hc-obo-auth/references/canonical-patterns.md)
- [Lakebase branching](../../.claude/skills/hc-lakebase-branching/SKILL.md)

## Layout

```
src/lab/
├── app.py                 # FastAPI entrypoint with lifespan (closes per-user pools)
├── auth.py                # OBO token extraction (X-Forwarded-Access-Token → user)
├── db.py                  # Per-user AsyncConnectionPool (OAuthConnection)
└── routers/
    └── lab_orders.py      # GET /lab-orders, GET /lab-orders/{id}

migrations/
├── env.py                 # Alembic env wired to OBO + Lakebase
└── versions/
    └── 0001_initial_lab_schema.py

tests/
├── unit/test_models.py    # No DB needed; runs in plain pytest
└── integration/test_obo.py  # Conformance: 401 without token, isolation across users

seed/
└── seed.py                # Idempotent synthetic-data loader (~60 lab orders).
```

## Seeding

After `alembic upgrade head` against your dev project's `production` branch:

```bash
make seed-lab                        # this service only
# or
make seed-dev                        # all six services in dependency order
```

`seed/seed.py` populates `lab_panel`, `reference_range`, `lab_order`, and
`lab_result` with deterministic IDs that reference the same patients,
providers, and appointments as the other seeds. Re-running is safe (`ON
CONFLICT (id) DO NOTHING`).
