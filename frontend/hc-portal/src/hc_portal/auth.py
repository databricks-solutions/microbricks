"""OBO token extraction. Identical shape to the per-service auth.py.

The BFF reads `X-Forwarded-Access-Token` the same way services do, then
forwards it (in both `Authorization: Bearer ...` and `X-Forwarded-Access-Token`)
to each downstream service via `_BaseSvcClient`.

This module is intentionally a copy of `services/<svc>/src/<svc>/auth.py` —
keeping the auth surface identical means the BFF can be reasoned about as
"another service that happens to fan out" rather than as a special-case.
"""
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
      2. Authorization: Bearer <token> (set by an upstream proxy in tests)
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
