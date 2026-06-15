"""Base class and shared shapes for typed per-service BFF clients.

Verbatim from `.claude/skills/hc-obo-auth/references/canonical-patterns.md`,
adapted to resolve downstream service URLs in this order:

  1. **Explicit override**: `<SVC>_SVC_URL` env var, e.g. `PATIENT_SVC_URL`.
     Set this in `frontend/hc-portal/app.yml` (`env:`) or in the bundle's
     `app.config.env` block when you need to point the BFF at a non-default
     host: local dev, a per-PR preview, an alternate region, or any
     scenario where the convention below doesn't fit.

  2. **Runtime-derived default**: compose from the BFF's own runtime
     context. Apps platform injects `DATABRICKS_APP_URL` on every running
     app, e.g. `https://hc-portal-<workspace-id>.aws.databricksapps.com`
     (trunk dev/test/prod) or
     `https://hc-portal-feat-<slug>-<workspace-id>.aws.databricksapps.com`
     (PR preview). Sibling services share the same `[-<suffix>]-<workspace_id>.<region>.databricksapps.com`
     tail — every app in this bundle is named `<svc>` (or `<svc>-feat-<slug>`
     for previews), so we strip our own `hc-portal` prefix off the host and
     prepend the service slug. This means a fresh-clone deploy works
     without any cross-app URL wiring in the bundle.

Every concrete client (`PatientClient`, `ProviderClient`, ...) extends this
and passes the bare service slug (`patient`, `provider`, ...).

The base enforces the BFF rules from `.claude/skills/hc-bff-pattern/SKILL.md`:

  - Per-request lifetime (use as `async with PatientClient(token) as p`).
  - Both `Authorization: Bearer <token>` AND `X-Forwarded-Access-Token`
    forwarded — the downstream service should be unable to tell whether the
    user called directly or via the BFF.
  - Bounded timeouts: connect=2s, read/write/pool=5s.
"""
from __future__ import annotations

import functools
import os
from typing import Generic, TypeVar
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Paginated list envelope returned by every backend list endpoint.

    `total` is the unfiltered row count for the current filter+search
    predicate (not the size of `items`). The BFF can drive a "page N of M"
    control without a second `/count` round-trip — and the dashboard's
    aggregate counts still come from the dedicated `/count` endpoints.
    """

    items: list[T]
    total: int
    limit: int
    offset: int

# Our own app name is `hc-portal` (or `hc-portal-feat-<slug>` for previews).
# Every sibling service is `<svc>` (or `<svc>-feat-<slug>`). We strip this
# prefix off our own host to recover the `[-feat-<slug>]-<workspace_suffix>`
# tail and prepend each service slug.
_OWN_APP_PREFIX = "hc-portal"


@functools.lru_cache(maxsize=1)
def _own_app_suffix() -> str:
    """Return the host tail shared by every app in this workspace.

    Examples:
        BFF at https://hc-portal-<workspace-id>.aws.databricksapps.com
            -> -<workspace-id>.aws.databricksapps.com
        BFF at https://hc-portal-feat-foo-<workspace-id>.aws.databricksapps.com
            -> -feat-foo-<workspace-id>.aws.databricksapps.com
    so callers can prepend a service slug like `patient`.

    Cached because it never changes within a process.
    """
    host = urlparse(os.environ["DATABRICKS_APP_URL"]).netloc
    if not host.startswith(f"{_OWN_APP_PREFIX}-"):
        raise RuntimeError(
            f"DATABRICKS_APP_URL host {host!r} does not start with "
            f"expected app prefix '{_OWN_APP_PREFIX}-'."
        )
    return host[len(_OWN_APP_PREFIX) :]  # leaves "[-feat-<slug>]-<workspace_suffix>"


def _resolve_base_url(service_slug: str) -> str:
    """Resolve the base URL for a downstream service.

    Order: explicit `<SVC>_SVC_URL` override → runtime-derived default.
    See module docstring for the contract.
    """
    override = os.environ.get(f"{service_slug.upper()}_SVC_URL")
    if override:
        return override
    return f"https://{service_slug}{_own_app_suffix()}"


class _BaseSvcClient:
    """Base for typed per-service clients. Always forwards the user's OBO token."""

    def __init__(self, user_token: str, service_slug: str, branch: str | None = None):
        self._client = httpx.AsyncClient(
            base_url=_resolve_base_url(service_slug),
            headers={
                "Authorization": f"Bearer {user_token}",
                "X-Forwarded-Access-Token": user_token,
            },
            params={"branch_name": branch} if branch else {},
            timeout=httpx.Timeout(connect=2.0, read=5.0, write=5.0, pool=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self._client.aclose()
