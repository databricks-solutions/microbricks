"""Base class for typed per-service BFF clients (clinic-sim flavor).

Verbatim from hc-portal's `_base.py` with one knob changed: `_OWN_APP_PREFIX`
is `clinic-sim` so the URL-derivation strips this app's hostname prefix
instead of `hc-portal`'s. Everything else (override env var, OBO header
forwarding, bounded timeouts) is identical so a service can't tell the
difference between a portal call and a simulator call.
"""
from __future__ import annotations

import functools
import os
from urllib.parse import urlparse

import httpx

_OWN_APP_PREFIX = "clinic-sim"


@functools.lru_cache(maxsize=1)
def _own_app_suffix() -> str:
    """Return the host tail shared by every app in this workspace."""
    host = urlparse(os.environ["DATABRICKS_APP_URL"]).netloc
    if not host.startswith(f"{_OWN_APP_PREFIX}-"):
        raise RuntimeError(
            f"DATABRICKS_APP_URL host {host!r} does not start with "
            f"expected app prefix '{_OWN_APP_PREFIX}-'."
        )
    return host[len(_OWN_APP_PREFIX) :]


def _resolve_base_url(service_slug: str) -> str:
    """Resolve the base URL for a downstream service.

    Order: explicit `<SVC>_SVC_URL` override → runtime-derived default.
    """
    override = os.environ.get(f"{service_slug.upper()}_SVC_URL")
    if override:
        return override
    return f"https://{service_slug}{_own_app_suffix()}"


class _BaseSvcClient:
    """Base for typed per-service clients. Always forwards the user's OBO token.

    Timeouts here are slightly more generous than hc-portal's (10s read) because
    the simulator's write operations involve a connection-pool open + an
    INSERT/UPDATE, whereas hc-portal mostly issues reads.
    """

    def __init__(self, user_token: str, service_slug: str):
        self._client = httpx.AsyncClient(
            base_url=_resolve_base_url(service_slug),
            headers={
                "Authorization": f"Bearer {user_token}",
                "X-Forwarded-Access-Token": user_token,
            },
            timeout=httpx.Timeout(connect=3.0, read=10.0, write=10.0, pool=10.0),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self._client.aclose()
