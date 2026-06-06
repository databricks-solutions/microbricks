"""OBO conformance test. Verifies the trust path end-to-end against a running service.

Requires SVC_BASE_URL pointing at a deployed (or local apx dev) lab-svc.
The two-user isolation test additionally requires USER_ONE_TOKEN and USER_TWO_TOKEN.
"""
from __future__ import annotations

import httpx
import pytest


@pytest.mark.integration
async def test_route_requires_token(svc_base_url: str):
    async with httpx.AsyncClient(base_url=svc_base_url) as c:
        r = await c.get("/api/v1/lab-orders")
    assert r.status_code == 401


@pytest.mark.integration
async def test_route_isolates_users(
    svc_base_url: str, user_one_token: str, user_two_token: str
):
    async with httpx.AsyncClient(base_url=svc_base_url) as c:
        r1 = await c.get(
            "/api/v1/lab-orders",
            headers={"X-Forwarded-Access-Token": user_one_token},
        )
        r2 = await c.get(
            "/api/v1/lab-orders",
            headers={"X-Forwarded-Access-Token": user_two_token},
        )
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Two users with different UC permissions should see different rows.
    assert {p["id"] for p in r1.json()} != {p["id"] for p in r2.json()}


@pytest.mark.integration
async def test_healthz(svc_base_url: str):
    async with httpx.AsyncClient(base_url=svc_base_url) as c:
        r = await c.get("/api/v1/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
