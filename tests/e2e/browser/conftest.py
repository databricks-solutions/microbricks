"""Playwright browser E2E fixtures.

Auth in Databricks Apps is handled by the platform (X-Forwarded-Access-Token
injected from the app proxy). For E2E browser tests against deployed apps,
we inject the Bearer token as an extra HTTP header on the browser context.

When services are not redeployed with a slug, requests go to the standard app
but must include ?branch_name=<slug> to route to the correct Lakebase branch.
We intercept all /api/* fetch requests in the browser and append branch_name.
"""
from __future__ import annotations

import os
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

import pytest
from playwright.sync_api import BrowserContext, Route


@pytest.fixture(scope="session")
def app_url() -> str:
    url = os.environ.get("BFF_BASE_URL")
    if not url:
        pytest.skip("BFF_BASE_URL not set; browser e2e tests skipped")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def lakebase_branch() -> str:
    branch = os.environ.get("LAKEBASE_BRANCH")
    if not branch:
        pytest.skip(
            "LAKEBASE_BRANCH not set; browser e2e tests require an isolated branch"
        )
    return branch


@pytest.fixture(scope="session")
def user_token() -> str:
    tok = os.environ.get("USER_ONE_TOKEN")
    if not tok:
        pytest.skip("USER_ONE_TOKEN not set; browser e2e tests skipped")
    return tok


@pytest.fixture(scope="session")
def browser_context_args(user_token: str) -> dict:
    """Inject auth header into all browser requests."""
    return {
        "extra_http_headers": {
            "Authorization": f"Bearer {user_token}",
        },
    }


@pytest.fixture(autouse=True)
def _inject_branch_param(context: BrowserContext, lakebase_branch: str):
    """Intercept all /api/* requests and append ?branch_name=<slug>.

    This ensures the BFF forwards requests to the correct Lakebase branch
    even when the app itself wasn't redeployed with a slug.
    """

    def _append_branch(route: Route):
        request = route.request
        parsed = urlparse(request.url)
        qs = parse_qs(parsed.query)
        if "branch_name" not in qs:
            qs["branch_name"] = [lakebase_branch]
            new_query = urlencode(qs, doseq=True)
            new_url = urlunparse(parsed._replace(query=new_query))
            route.continue_(url=new_url)
        else:
            route.continue_()

    context.route("**/api/**", _append_branch)
    yield
    context.unroute("**/api/**", _append_branch)
