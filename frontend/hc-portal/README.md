# hc-portal

BFF + React UI for the healthcare reference architecture. The **only** Databricks App that fans out to multiple backend services — every other app owns one service and talks to one database.

> Owner: TBD · See [`CODEOWNERS`](../../CODEOWNERS) and [`ARCHITECTURE.md`](../../ARCHITECTURE.md#bff-shape).

## What this app is

```
React UI ──/api/bff/...──▶ FastAPI BFF ──╭─▶ patient-svc
                                          ├─▶ provider-svc
                                          ├─▶ appointment-svc
                                          ├─▶ lab-svc
                                          ├─▶ prescription-svc
                                          ╰─▶ billing-svc
```

The BFF holds **no state** (no DB, no Redis, no module-level cache). Per-request typed clients fan out concurrently with `asyncio.gather`. The user's OBO token is forwarded into every downstream call so Unity Catalog row-level policy is enforced consistently.

See [`.claude/skills/hc-bff-pattern/SKILL.md`](../../.claude/skills/hc-bff-pattern/SKILL.md) for the full canonical pattern.

## Local development

```bash
apx dev start          # runs the FastAPI BFF, the Vite UI dev server, and openapi watcher
```

This requires:
- All six backend services running on ports 8001-8006 (run `apx dev start` from each `services/<svc>/` in another terminal). For Phase 3 — when no services are yet deployed — the BFF still boots; routes that fan out will 502 until the services are up, but `/api/bff/healthz` and the static UI work fine.
- A `.env` populated from `.env.example`, including `LOCAL_DEV_TOKEN` from `databricks auth token -p hc-dev | jq -r .access_token`.

## Routes

| BFF route | Purpose |
|---|---|
| `GET /api/bff/healthz` | Liveness probe — does NOT touch downstream services. |
| `GET /api/bff/patients` | Read-only proxy used by the patients index page. |
| `GET /api/bff/patient-summary/{id}` | Canonical aggregation: patient + last 3 appointments + active Rx + recent labs + outstanding invoices, fanned out concurrently. |

## Tests

```bash
pytest -m "not integration"   # unit tests with respx-mocked downstream services
pytest -m integration         # integration tests against deployed preview apps
```

Integration tests require `BFF_BASE_URL`, `USER_ONE_TOKEN`, and a known sample patient ID in env.

## Deploy

This is part of the root DAB (Phase 5 lands `resources/hc-portal.yml`). Don't run `databricks bundle deploy` from this directory — run it from the repo root once Phase 5 lands.
