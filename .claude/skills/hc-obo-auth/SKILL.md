---
name: hc-obo-auth
description: Wire OBO (On-Behalf-Of) authentication into a service or BFF route. Use when the user asks to "add a route", "wire OBO", "set up authentication", "connect to Lakebase as the user", "extract user identity", or anything about user-passthrough auth. Enforces the canonical pattern where every Postgres connection is opened with the calling user's OAuth credential and Unity Catalog enforces access at the data layer.
---

# hc-obo-auth

The non-negotiable auth rule in this architecture: **every Postgres session opens with the calling user's OAuth credential.** No service-principal fallback in production code, no shortcuts.

This skill is the source of truth for the canonical patterns. Any deviation needs to be argued for in a PR description.

## When to use

- "Add a new route to `patient-svc` that lists allergies"
- "Wire OBO into the BFF client for `lab-svc`"
- "How do I connect to Lakebase as the user?"
- "Set up `db.py` for the new service"
- The user is touching anything that crosses the trust boundary (HTTP route, DB connection, downstream service call)

## When NOT to use

- The user is writing pure unit tests against a mock — OBO doesn't apply.
- The user is writing a one-off ETL script — script auth is its own thing, use a service principal there but document it as outside the OBO trust path.

## The four pillars

1. **Token in.** Every backend route reads `X-Forwarded-Access-Token` from the request — Databricks Apps injects this on every call.
2. **Token to UC.** When the service needs UC operations, it builds `WorkspaceClient(token=user_token)`, never `WorkspaceClient()` without a token in production.
3. **Token to Lakebase.** When the service connects to Postgres, it calls `WorkspaceClient(token=user_token, auth_type="pat").postgres.generate_database_credential(endpoint=ENDPOINT_NAME)` and uses the returned token as the Postgres password. The `auth_type="pat"` is required when the code runs inside a Databricks App: the platform auto-injects `DATABRICKS_CLIENT_ID` + `DATABRICKS_CLIENT_SECRET` for the app's service principal, and the SDK refuses ambiguous oauth+pat config unless one method is forced. Connections are pooled with `max_lifetime=2700` (45 min) so a stale token never lives longer than 1h.
4. **Token forward.** When the BFF or any service calls another service, it copies the user token into both `Authorization: Bearer ...` and `X-Forwarded-Access-Token` headers. The downstream service treats it as if the user called directly.

The detailed canonical code (drop-in copies for every service) lives in [`references/canonical-patterns.md`](references/canonical-patterns.md).

## Quick patterns

### Extracting the user token in a FastAPI route

```python
from fastapi import Header, HTTPException

async def user_token(
    x_forwarded_access_token: str | None = Header(default=None, alias="X-Forwarded-Access-Token"),
) -> str:
    if not x_forwarded_access_token:
        raise HTTPException(401, "Missing X-Forwarded-Access-Token")
    return x_forwarded_access_token
```

Use it as a dependency:

```python
@router.get("/patients", response_model=list[PatientOut], operation_id="listPatients")
async def list_patients(token: str = Depends(user_token)):
    async with patient_db_pool(token).connection() as conn:
        ...
```

### Building a per-request DB pool

Don't build one global pool. Build one *per user token*, cached briefly. The full helper is in [`references/canonical-patterns.md`](references/canonical-patterns.md), but the shape:

```python
from psycopg_pool import AsyncConnectionPool
import psycopg
from databricks.sdk import WorkspaceClient
import os, asyncio

_pools: dict[str, AsyncConnectionPool] = {}
_lock = asyncio.Lock()

class OAuthConnection(psycopg.AsyncConnection):
    @classmethod
    async def connect(cls, conninfo: str = "", **kwargs):
        token = kwargs.pop("_user_token", None)
        if not token:
            raise RuntimeError("OAuthConnection requires _user_token kwarg")
        # auth_type="pat" disambiguates from the SP credentials Apps auto-injects.
        ws = WorkspaceClient(token=token, auth_type="pat")
        cred = ws.postgres.generate_database_credential(endpoint=os.environ["ENDPOINT_NAME"])
        kwargs["password"] = cred.token
        return await super().connect(conninfo, **kwargs)

def patient_db_pool(user_token: str) -> AsyncConnectionPool:
    # Cache pools per token (short-lived). In production you'd cache by token's iss+sub claim
    # to avoid leaking memory if many distinct tokens hit the service.
    if user_token not in _pools:
        host = os.environ["PGHOST"]
        user = os.environ["PGUSER"]
        _pools[user_token] = AsyncConnectionPool(
            conninfo=f"host={host} port=5432 dbname=databricks_postgres user={user} sslmode=require",
            connection_class=OAuthConnection,
            max_lifetime=2700,
            kwargs={"_user_token": user_token},
            open=False,
        )
    return _pools[user_token]
```

> ⚠️ The `_pools[token]` cache leaks if many distinct tokens hit the service. The full pattern in `references/` uses an LRU keyed by `hash(token)` with a TTL.

### Forwarding the token from the BFF

URL resolution: explicit `<SVC>_SVC_URL` override → runtime-derived from `DATABRICKS_APP_URL`. See `references/canonical-patterns.md` for the full `_BaseSvcClient` shape.

```python
class PatientClient(_BaseSvcClient):
    def __init__(self, user_token: str):
        super().__init__(user_token, service_slug="patient")
```

The BFF route extracts the token the same way as services and constructs one client per request:

```python
@router.get("/patient-summary/{patient_id}", operation_id="getPatientSummary")
async def patient_summary(patient_id: str, token: str = Depends(user_token)):
    async with PatientClient(token) as p, AppointmentClient(token) as a:
        patient, appts = await asyncio.gather(
            p.get(patient_id),
            a.list_for_patient(patient_id, limit=3),
        )
    return {"patient": patient, "appointments": appts}
```

## Local development

When running `apx dev start` outside Databricks Apps, there's no `X-Forwarded-Access-Token` injected. Two options, both supported:

1. **Pass-through from the dev's CLI auth.** The `apx` lakebase addon can inject the dev's token into the env so requests pretend to be OBO. The dev's identity is then used for Lakebase. Set `LOCAL_DEV_TOKEN_FROM_CLI=true` in `.env` and the canonical pattern reads it.

2. **Explicit header.** When testing with `curl`, include `-H "X-Forwarded-Access-Token: $(databricks auth token -p hc-dev | jq -r .access_token)"`.

What the canonical pattern **does not** support: a service-principal fallback when running locally. Local dev still uses the developer's user identity to talk to Lakebase. This keeps prod-vs-dev behavior identical and prevents "works on my machine, fails in prod" auth bugs.

## Anti-patterns to reject in code review

| Pattern | Why it's wrong |
|---|---|
| `WorkspaceClient()` (no token) in route handlers | Falls back to the app's service principal, defeats OBO |
| Storing a connection pool keyed only on env (one global pool) | All users share one connection → all queries run as the SP |
| Reading the token from a query param or cookie instead of the header | The header is what Databricks Apps injects; anything else is a different trust path |
| Forwarding the token but stripping `Authorization` and only sending `X-Forwarded-Access-Token` | Some downstream libraries only check `Authorization` — send both |
| Caching `generate_database_credential` results across requests | Tokens are user-bound — caching them across users leaks identity |

## Verification

After wiring OBO into a route:

1. `curl -H "X-Forwarded-Access-Token: <user-1-token>" .../patients/me` returns user-1's data.
2. `curl -H "X-Forwarded-Access-Token: <user-2-token>" .../patients/me` returns user-2's data, not user-1's.
3. `curl .../patients/me` (no header) returns 401.
4. In Lakebase, `SELECT current_user;` from the route returns the calling user's email, not the app's service principal email. Add a debug route that echoes `current_user` to confirm during initial wiring.

## Pointer

Full canonical code (`db.py`, `auth.py`, BFF client) is in [`references/canonical-patterns.md`](references/canonical-patterns.md). Copy from there into the service; do not invent new shapes.
