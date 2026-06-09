"""OBO token extraction. Identical shape to the per-service auth.py and to
`hc_portal.auth` — the BFF reads `X-Forwarded-Access-Token` exactly like a
service would, then forwards it on every downstream call.
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
