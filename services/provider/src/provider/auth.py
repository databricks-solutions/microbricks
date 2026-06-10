"""OBO token + user-identity extraction. Identical across every service."""
from __future__ import annotations

import os

from fastapi import Header, HTTPException, Query

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
        local = os.environ.get("LOCAL_DEV_TOKEN")
        if local:
            return local

    raise HTTPException(401, "Missing user token")


async def user_email(
    x_forwarded_email: str | None = Header(
        default=None, alias="X-Forwarded-Email"
    ),
) -> str:
    """Return the calling user's email.

    Databricks Apps injects `X-Forwarded-Email` from the IdP for every
    authenticated request. The email is also the Postgres role name created
    by `databricks_create_role(<email>, 'USER')`, so we use it directly as
    PGUSER when opening Lakebase connections — that's how per-user OBO at
    the DB layer works.

    Local dev: falls back to LOCAL_DEV_USER_EMAIL or DATABRICKS_USER (the
    operator's email pulled from `databricks current-user me`).
    """
    if x_forwarded_email:
        return x_forwarded_email

    if _LOCAL_DEV:
        local = os.environ.get("LOCAL_DEV_USER_EMAIL") or os.environ.get(
            "DATABRICKS_USER"
        )
        if local:
            return local

    raise HTTPException(401, "Missing user email")


async def branch_name(
    branch_name: str | None = Query(default=None),
) -> str | None:
    """Optional Lakebase branch override.

    When set, the service connects to
    `projects/{SERVICE_NAME}/branches/{branch_name}/endpoints/primary` instead
    of the default ENDPOINT_NAME from the environment. This allows frontends
    deployed against a feature branch to reuse production services while
    targeting non-production data.
    """
    return branch_name
