"""E2E: Auth enforcement at the BFF GraphQL layer."""
from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.e2e

INTROSPECTION_QUERY = '{ __schema { queryType { name } } }'
DASHBOARD_QUERY = "{ dashboardStats { totalPatients } }"


async def test_no_token_returns_401(bff_base_url: str):
    async with httpx.AsyncClient(base_url=bff_base_url, timeout=15.0) as c:
        r = await c.post("/api/graphql", json={"query": DASHBOARD_QUERY})
    assert r.status_code in (401, 403)


async def test_invalid_token_returns_401(bff_base_url: str):
    async with httpx.AsyncClient(
        base_url=bff_base_url,
        headers={"Authorization": "Bearer totally-invalid-token"},
        timeout=15.0,
    ) as c:
        r = await c.post("/api/graphql", json={"query": DASHBOARD_QUERY})
    assert r.status_code in (401, 403)


async def test_valid_token_returns_200(bff_client: httpx.AsyncClient):
    r = await bff_client.post("/api/graphql", json={"query": DASHBOARD_QUERY})
    assert r.status_code == 200
    body = r.json()
    assert "errors" not in body
    assert body["data"]["dashboardStats"]["totalPatients"] is not None
