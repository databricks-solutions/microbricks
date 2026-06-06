# Canonical OBO patterns — copy into your service

Drop-in code for the four pillars described in [`../SKILL.md`](../SKILL.md). Adapt the names; do not change the shapes.

## `services/<svc>/src/<svc>/auth.py`

```python
"""OBO token extraction. Identical across every service."""
from __future__ import annotations
import os
from fastapi import Header, HTTPException

_LOCAL_DEV = os.environ.get("LOCAL_DEV_TOKEN_FROM_CLI") == "true"


async def user_token(
    x_forwarded_access_token: str | None = Header(
        default=None, alias="X-Forwarded-Access-Token"
    ),
    authorization: str | None = Header(default=None),
) -> str:
    """Return the calling user's OAuth access token.

    Priority:
      1. X-Forwarded-Access-Token (injected by Databricks Apps in production)
      2. Authorization: Bearer <token> (set by BFF or other upstream)
      3. Local dev fallback (only if LOCAL_DEV_TOKEN_FROM_CLI=true)
    """
    if x_forwarded_access_token:
        return x_forwarded_access_token

    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1]

    if _LOCAL_DEV:
        # apx lakebase addon writes the dev's CLI token here at process start
        local = os.environ.get("LOCAL_DEV_TOKEN")
        if local:
            return local

    raise HTTPException(401, "Missing user token")
```

## `services/<svc>/src/<svc>/db.py`

```python
"""Per-user Lakebase connection pool. Identical across services except for env var names."""
from __future__ import annotations
import asyncio
import hashlib
import os
import time
from typing import Any

import psycopg
from psycopg_pool import AsyncConnectionPool
from databricks.sdk import WorkspaceClient

# ---- OAuthConnection ----------------------------------------------------------

class OAuthConnection(psycopg.AsyncConnection):
    """psycopg connection subclass that swaps in a Lakebase OAuth token as the password.

    The token is generated *per connection*, scoped to the calling user's identity.
    Pool max_lifetime ≤ 2700s ensures we never hold a connection long enough for the
    token to expire (1h default).
    """

    @classmethod
    async def connect(cls, conninfo: str = "", **kwargs: Any) -> "OAuthConnection":
        token: str | None = kwargs.pop("_user_token", None)
        if not token:
            raise RuntimeError("OAuthConnection requires _user_token kwarg")
        endpoint = os.environ["ENDPOINT_NAME"]
        # auth_type="pat" forces the SDK to use ONLY the explicit user token.
        # Without it the SDK sees DATABRICKS_CLIENT_ID/SECRET (auto-injected
        # for the app's SP) and refuses ambiguous oauth+pat config.
        ws = WorkspaceClient(token=token, auth_type="pat")
        cred = ws.postgres.generate_database_credential(endpoint=endpoint)
        kwargs["password"] = cred.token
        return await super().connect(conninfo, **kwargs)


# ---- Per-user pool cache ------------------------------------------------------

_POOL_TTL = 2700  # seconds — same as max_lifetime
_POOL_MAX = 256   # eviction cap, prevents unbounded growth from many distinct tokens
_pools: dict[str, tuple[AsyncConnectionPool, float]] = {}
_lock = asyncio.Lock()


def _key(user_token: str) -> str:
    # Don't put the raw token in a dict key; hash it.
    return hashlib.sha256(user_token.encode()).hexdigest()


async def _evict_expired() -> None:
    now = time.monotonic()
    expired = [k for k, (_, exp) in _pools.items() if exp <= now]
    for k in expired:
        pool, _ = _pools.pop(k)
        await pool.close()


async def get_pool(user_token: str) -> AsyncConnectionPool:
    """Return a (cached) connection pool bound to the user's token."""
    key = _key(user_token)
    async with _lock:
        await _evict_expired()
        cached = _pools.get(key)
        if cached:
            return cached[0]

        if len(_pools) >= _POOL_MAX:
            # LRU-ish: evict oldest
            oldest_key = min(_pools, key=lambda k: _pools[k][1])
            old_pool, _ = _pools.pop(oldest_key)
            await old_pool.close()

        host = os.environ["PGHOST"]
        user = os.environ["PGUSER"]
        port = os.environ.get("PGPORT", "5432")
        dbname = os.environ.get("PGDATABASE", "databricks_postgres")
        sslmode = os.environ.get("PGSSLMODE", "require")

        pool = AsyncConnectionPool(
            conninfo=f"host={host} port={port} dbname={dbname} user={user} sslmode={sslmode}",
            connection_class=OAuthConnection,
            max_lifetime=_POOL_TTL,
            min_size=0,
            max_size=4,  # plenty per user
            kwargs={"_user_token": user_token},
            open=False,
        )
        await pool.open()
        _pools[key] = (pool, time.monotonic() + _POOL_TTL)
        return pool


async def close_all_pools() -> None:
    """Call on app shutdown."""
    async with _lock:
        for pool, _ in _pools.values():
            await pool.close()
        _pools.clear()
```

## `services/<svc>/src/<svc>/app.py`

```python
"""FastAPI entrypoint. Wires shutdown of the per-user pools."""
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .db import close_all_pools
from .routers import patients  # add other routers here


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_all_pools()


app = FastAPI(
    title="<svc>-svc",
    version="1.0.0",
    lifespan=lifespan,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)

app.include_router(patients.router, prefix="/api/v1")


@app.get("/api/v1/healthz")
async def healthz():
    return {"ok": True}
```

## `services/<svc>/src/<svc>/routers/<entity>.py`

Example: a `patients` router. The shape is the same for every entity in every service.

```python
"""Routers depend on user_token via FastAPI Depends; never accept service-principal auth."""
from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID

from ..auth import user_token
from ..db import get_pool

router = APIRouter(tags=["patients"])


class PatientOut(BaseModel):
    id: UUID
    mrn: str
    given_name: str
    family_name: str


@router.get("/patients", response_model=list[PatientOut], operation_id="listPatients")
async def list_patients(token: Annotated[str, Depends(user_token)]):
    pool = await get_pool(token)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT id, mrn, given_name, family_name FROM patient WHERE deleted_at IS NULL ORDER BY family_name LIMIT 200"
        )
        rows = await cur.fetchall()
    return [PatientOut(id=r[0], mrn=r[1], given_name=r[2], family_name=r[3]) for r in rows]


@router.get("/patients/{patient_id}", response_model=PatientOut, operation_id="getPatient")
async def get_patient(patient_id: UUID, token: Annotated[str, Depends(user_token)]):
    pool = await get_pool(token)
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT id, mrn, given_name, family_name FROM patient WHERE id = %s AND deleted_at IS NULL",
            (patient_id,),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Patient not found")
    return PatientOut(id=row[0], mrn=row[1], given_name=row[2], family_name=row[3])
```

Note: the route handler doesn't manually filter by tenant or by user-permitted IDs. Unity Catalog row-level policies on the underlying tables handle that. If a user can't see patient X, the `WHERE id = %s` query simply returns 0 rows and the route returns 404.

## `frontend/hc-portal/src/hc_portal/clients/_base.py`

The base client all per-service clients extend. URL resolution prefers an explicit `<SVC>_SVC_URL` override; otherwise it strips the BFF's own `hc-portal` prefix off `DATABRICKS_APP_URL` and prepends the per-service slug, exploiting the fact that every app in a workspace+target shares the same `<wsid>.<region>.databricksapps.com` tail.

```python
from __future__ import annotations
import functools
import os
from urllib.parse import urlparse

import httpx

_OWN_APP_PREFIX = "hc-portal"


@functools.lru_cache(maxsize=1)
def _own_app_suffix() -> str:
    host = urlparse(os.environ["DATABRICKS_APP_URL"]).netloc
    if not host.startswith(f"{_OWN_APP_PREFIX}-"):
        raise RuntimeError(
            f"DATABRICKS_APP_URL host {host!r} does not start with "
            f"expected app prefix '{_OWN_APP_PREFIX}-'."
        )
    return host[len(_OWN_APP_PREFIX) :]  # "-<target>-<wsid>.<region>.databricksapps.com"


def _resolve_base_url(service_slug: str) -> str:
    override = os.environ.get(f"{service_slug.upper()}_SVC_URL")
    if override:
        return override
    return f"https://{service_slug}{_own_app_suffix()}"


class _BaseSvcClient:
    """Base for typed per-service clients. Always forwards the user's OBO token."""

    def __init__(self, user_token: str, service_slug: str):
        self._client = httpx.AsyncClient(
            base_url=_resolve_base_url(service_slug),
            headers={
                "Authorization": f"Bearer {user_token}",
                "X-Forwarded-Access-Token": user_token,
            },
            timeout=httpx.Timeout(connect=2.0, read=5.0, write=5.0, pool=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self._client.aclose()
```

## `frontend/hc-portal/src/hc_portal/clients/patient.py`

Example concrete client. Methods are thin wrappers around HTTP calls — types come from the OpenAPI-generated models if you wire Orval, otherwise hand-typed Pydantic models.

```python
from __future__ import annotations
from uuid import UUID
from pydantic import BaseModel
from ._base import _BaseSvcClient


class Patient(BaseModel):
    id: UUID
    mrn: str
    given_name: str
    family_name: str


class PatientClient(_BaseSvcClient):
    def __init__(self, user_token: str):
        super().__init__(user_token, service_slug="patient")

    async def get(self, patient_id: UUID) -> Patient:
        r = await self._client.get(f"/api/v1/patients/{patient_id}")
        r.raise_for_status()
        return Patient.model_validate(r.json())

    async def list(self) -> list[Patient]:
        r = await self._client.get("/api/v1/patients")
        r.raise_for_status()
        return [Patient.model_validate(x) for x in r.json()]
```

## Conformance test (every service should have one)

`services/<svc>/tests/integration/test_obo.py`:

```python
import os
import httpx
import pytest


@pytest.mark.integration
async def test_route_requires_token():
    async with httpx.AsyncClient(base_url=os.environ["SVC_BASE_URL"]) as c:
        r = await c.get("/api/v1/patients")
        assert r.status_code == 401


@pytest.mark.integration
async def test_route_isolates_users(user_one_token: str, user_two_token: str):
    async with httpx.AsyncClient(base_url=os.environ["SVC_BASE_URL"]) as c:
        r1 = await c.get("/api/v1/patients", headers={"X-Forwarded-Access-Token": user_one_token})
        r2 = await c.get("/api/v1/patients", headers={"X-Forwarded-Access-Token": user_two_token})
    # Two users with different UC permissions should see different rows
    assert {p["id"] for p in r1.json()} != {p["id"] for p in r2.json()}
```

The fixtures `user_one_token` / `user_two_token` are session-scoped fixtures that return tokens for two test SPs with deliberately-divergent UC grants. Defined once in the root `conftest.py`.
