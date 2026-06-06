# provider-svc

System of record for clinicians, organizations, and specialties.

**Owns:** `provider`, `organization`, `provider_specialty`
**References:** none (other services reference `provider.id`, never the other way)
**Lakebase project:** `projects/provider-{dev,test,prod}`

## Local development

```bash
# 1. Spin up a Lakebase feature branch (idempotent)
SLUG=$(./scripts/sanitize-branch-slug.sh "$(git branch --show-current)")
databricks postgres create-branch projects/provider-dev "feat-$SLUG" \
  --json '{"spec":{"source_branch":"projects/provider-dev/branches/production"}}' \
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
  http://localhost:8000/api/v1/providers
```

See:
- [Architecture](../../ARCHITECTURE.md)
- [Data model](../../HEALTHCARE_DATA_MODEL.md#2-provider-svc--provider_db)
- [Contributing](../../CONTRIBUTING.md)
- [OBO auth canonical patterns](../../.claude/skills/hc-obo-auth/references/canonical-patterns.md)
- [Lakebase branching](../../.claude/skills/hc-lakebase-branching/SKILL.md)

## Layout

```
src/provider/
├── app.py                 # FastAPI entrypoint with lifespan (closes per-user pools)
├── auth.py                # OBO token extraction (X-Forwarded-Access-Token → user)
├── db.py                  # Per-user AsyncConnectionPool (OAuthConnection)
└── routers/
    └── providers.py       # GET /providers, GET /providers/{id}

migrations/
├── env.py                 # Alembic env wired to OBO + Lakebase
└── versions/
    └── 0001_initial_provider_schema.py

tests/
├── unit/test_models.py    # No DB needed; runs in plain pytest
└── integration/test_obo.py  # Conformance: 401 without token, isolation across users

seed/
└── seed.py                # Idempotent synthetic-data loader (~5 providers, 2 orgs).
```

## Seeding

After `alembic upgrade head` against your dev project's `production` branch:

```bash
make seed-provider                   # this service only
# or
make seed-dev                        # all six services in dependency order
```

`seed/seed.py` populates `organization`, `provider`, and `provider_specialty`
deterministically. Re-running is safe (`ON CONFLICT (id) DO NOTHING`). See
[`scripts/seeds/_common.py`](../../scripts/seeds/_common.py) for the shared
helpers + cross-service ID derivation.
