"""E2E: Pagination and search correctness through the BFF."""
from __future__ import annotations

import uuid

import httpx
import pytest

pytestmark = pytest.mark.e2e


async def test_pagination_returns_different_pages(
    patient_svc_client: httpx.AsyncClient,
    bff_client: httpx.AsyncClient,
):
    # Ensure at least 3 patients exist
    for i in range(3):
        r = await patient_svc_client.post(
            "/api/v1/patients",
            json={
                "given_name": f"E2E-Page-{uuid.uuid4().hex[:6]}",
                "family_name": "Pagination",
                "birth_date": "1980-01-01",
                "sex_at_birth": "other",
            },
        )
        assert r.status_code == 201, f"Create patient failed: {r.status_code} {r.text}"

    # Page 1
    r = await bff_client.get("/api/bff/patients", params={"limit": 2, "offset": 0})
    assert r.status_code == 200
    page1 = r.json()
    assert len(page1["items"]) == 2
    assert page1["total"] >= 3

    # Page 2
    r = await bff_client.get("/api/bff/patients", params={"limit": 2, "offset": 2})
    assert r.status_code == 200
    page2 = r.json()
    assert len(page2["items"]) >= 1

    # Pages contain different items
    ids_1 = {p["id"] for p in page1["items"]}
    ids_2 = {p["id"] for p in page2["items"]}
    assert ids_1.isdisjoint(ids_2)


async def test_total_is_consistent_across_pages(bff_client: httpx.AsyncClient):
    r1 = await bff_client.get("/api/bff/patients", params={"limit": 1, "offset": 0})
    r2 = await bff_client.get("/api/bff/patients", params={"limit": 1, "offset": 1})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["total"] == r2.json()["total"]


async def test_search_filters_results(
    patient_svc_client: httpx.AsyncClient,
    bff_client: httpx.AsyncClient,
):
    unique_name = f"E2E-Search-{uuid.uuid4().hex[:8]}"
    await patient_svc_client.post(
        "/api/v1/patients",
        json={
            "given_name": unique_name,
            "family_name": "Searchable",
            "birth_date": "1995-07-22",
            "sex_at_birth": "male",
        },
    )

    # Search should find only our patient (unique name)
    r = await bff_client.get("/api/bff/patients", params={"q": unique_name})
    assert r.status_code == 200
    page = r.json()
    assert page["total"] >= 1
    assert all(unique_name in p["given_name"] for p in page["items"])
