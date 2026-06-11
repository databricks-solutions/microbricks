"""E2E: Auth enforcement at the BFF layer."""
from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.e2e


async def test_no_token_returns_401(bff_base_url: str):
    async with httpx.AsyncClient(base_url=bff_base_url, timeout=15.0) as c:
        r = await c.get("/api/bff/patients")
    assert r.status_code in (401, 403)


async def test_invalid_token_returns_401(bff_base_url: str):
    async with httpx.AsyncClient(
        base_url=bff_base_url,
        headers={"Authorization": "Bearer totally-invalid-token"},
        timeout=15.0,
    ) as c:
        r = await c.get("/api/bff/patients")
    assert r.status_code in (401, 403)


async def test_valid_token_returns_200(bff_client: httpx.AsyncClient):
    r = await bff_client.get("/api/bff/dashboard-stats")
    assert r.status_code == 200
