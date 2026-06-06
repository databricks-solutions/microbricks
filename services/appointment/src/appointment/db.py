"""Per-user Lakebase connection pool. Identical across services except for env var names.

Per-user OBO at the DB layer: each request opens (or reuses) a pool keyed on
the user's email (`X-Forwarded-Email`). The user's OAuth token mints a
short-lived Lakebase credential, used as the Postgres password for a role
the user owns (`databricks_create_role(<email>, 'USER')`). This means
Postgres-level access control — including row/column policies and
ownership — apply to the calling user, not the app's service principal.

PGHOST/PGDATABASE/PGPORT/PGSSLMODE are auto-injected by the Apps platform
from the postgres app resource. We override PGUSER per request because the
auto-injected value is the SP's client ID, but we want to connect as the
user.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import time
from typing import Any

import psycopg
from databricks.sdk import WorkspaceClient
from psycopg_pool import AsyncConnectionPool


class OAuthConnection(psycopg.AsyncConnection):
    """psycopg connection subclass that swaps in a Lakebase OAuth token as the password."""

    @classmethod
    async def connect(cls, conninfo: str = "", **kwargs: Any) -> "OAuthConnection":
        token: str | None = kwargs.pop("_user_token", None)
        if not token:
            raise RuntimeError("OAuthConnection requires _user_token kwarg")
        endpoint = os.environ["ENDPOINT_NAME"]
        # auth_type="pat" forces the SDK to use ONLY the explicit user token; without
        # this it sees DATABRICKS_CLIENT_ID/SECRET (auto-injected for the app's SP)
        # and refuses ambiguous oauth+pat config.
        ws = WorkspaceClient(token=token, auth_type="pat")
        cred = ws.postgres.generate_database_credential(endpoint=endpoint)
        kwargs["password"] = cred.token
        return await super().connect(conninfo, **kwargs)


_POOL_TTL = 2700  # seconds — same as max_lifetime
_POOL_MAX = 256   # eviction cap, prevents unbounded growth from many distinct tokens
# `AsyncConnectionPool` is generic over its connection class. We pin it to
# `OAuthConnection` so `_pools` and `get_pool`'s return type stay in sync —
# the bare `AsyncConnectionPool` annotation matched `dict[..., AsyncConnection]`
# at runtime but `ty` rejects that as a default-parameter mismatch.
_pools: dict[str, tuple[AsyncConnectionPool[OAuthConnection], float]] = {}
_lock = asyncio.Lock()


def _key(user_email: str, user_token: str) -> str:
    # Email is stable across token refreshes; token still hashed in so a token
    # rotation while the pool is open doesn't reuse a stale per-connection token.
    return hashlib.sha256(f"{user_email}:{user_token}".encode()).hexdigest()


async def _evict_expired() -> None:
    now = time.monotonic()
    expired = [k for k, (_, exp) in _pools.items() if exp <= now]
    for k in expired:
        pool, _ = _pools.pop(k)
        await pool.close()


async def get_pool(user_email: str, user_token: str) -> AsyncConnectionPool[OAuthConnection]:
    """Return a (cached) connection pool bound to the user's identity."""
    key = _key(user_email, user_token)
    async with _lock:
        await _evict_expired()
        cached = _pools.get(key)
        if cached:
            return cached[0]

        if len(_pools) >= _POOL_MAX:
            oldest_key = min(_pools, key=lambda k: _pools[k][1])
            old_pool, _ = _pools.pop(oldest_key)
            await old_pool.close()

        host = os.environ["PGHOST"]
        port = os.environ.get("PGPORT", "5432")
        dbname = os.environ.get("PGDATABASE", "databricks_postgres")
        sslmode = os.environ.get("PGSSLMODE", "require")

        pool = AsyncConnectionPool(
            # user=user_email — the calling user's Postgres role, not PGUSER
            # (which the platform auto-injects as the SP's client ID).
            conninfo=f"host={host} port={port} dbname={dbname} user={user_email} sslmode={sslmode}",
            connection_class=OAuthConnection,
            max_lifetime=_POOL_TTL,
            min_size=0,
            max_size=4,
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
