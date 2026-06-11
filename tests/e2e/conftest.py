"""E2E test fixtures.

These tests run against deployed apps (ephemeral or stable). Required env vars:
  - BFF_BASE_URL: hc-portal BFF (e.g., https://hc-portal-pr-42-123.test.databricksapps.com)
  - USER_ONE_TOKEN: a valid Databricks access token

Optional (for direct service writes):
  - PATIENT_SVC_BASE_URL: patient service URL
  - APPOINTMENT_SVC_BASE_URL: appointment service URL

Optional (for Lakebase branch routing when services are not redeployed):
  - LAKEBASE_BRANCH: branch name to route requests to (e.g., pr-42)
    When a service is not redeployed with a slug, it runs its standard app
    but can route to a specific Lakebase branch via ?branch_name=<slug>.
"""
from __future__ import annotations

import os
from typing import AsyncGenerator

import httpx
import pytest


@pytest.fixture(scope="session")
def bff_base_url() -> str:
    url = os.environ.get("BFF_BASE_URL")
    if not url:
        pytest.skip("BFF_BASE_URL not set; e2e tests skipped")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def user_one_token() -> str:
    tok = os.environ.get("USER_ONE_TOKEN")
    if not tok:
        pytest.skip("USER_ONE_TOKEN not set; e2e tests skipped")
    return tok


@pytest.fixture(scope="session")
def lakebase_branch() -> str | None:
    """Lakebase branch for routing. None means use the app's default."""
    return os.environ.get("LAKEBASE_BRANCH")


@pytest.fixture(scope="session")
def branch_params(lakebase_branch: str | None) -> dict[str, str]:
    """Query params to inject branch routing into every request."""
    if lakebase_branch:
        return {"branch_name": lakebase_branch}
    return {}


@pytest.fixture(scope="session")
def auth_headers(user_one_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_one_token}"}


@pytest.fixture(scope="session")
def patient_svc_base_url() -> str:
    url = os.environ.get("PATIENT_SVC_BASE_URL")
    if not url:
        pytest.skip("PATIENT_SVC_BASE_URL not set")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def appointment_svc_base_url() -> str:
    url = os.environ.get("APPOINTMENT_SVC_BASE_URL")
    if not url:
        pytest.skip("APPOINTMENT_SVC_BASE_URL not set")
    return url.rstrip("/")


@pytest.fixture
async def bff_client(
    bff_base_url: str, auth_headers: dict[str, str], branch_params: dict[str, str]
) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(
        base_url=bff_base_url,
        headers=auth_headers,
        params=branch_params,
        timeout=30.0,
    ) as client:
        yield client


@pytest.fixture
async def patient_svc_client(
    patient_svc_base_url: str, user_one_token: str, branch_params: dict[str, str]
) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(
        base_url=patient_svc_base_url,
        headers={"X-Forwarded-Access-Token": user_one_token},
        params=branch_params,
        timeout=30.0,
    ) as client:
        yield client


@pytest.fixture
async def appointment_svc_client(
    appointment_svc_base_url: str, user_one_token: str, branch_params: dict[str, str]
) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(
        base_url=appointment_svc_base_url,
        headers={"X-Forwarded-Access-Token": user_one_token},
        params=branch_params,
        timeout=30.0,
    ) as client:
        yield client
