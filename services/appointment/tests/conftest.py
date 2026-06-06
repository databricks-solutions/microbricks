"""Test fixtures shared across unit and integration suites.

Integration tests require:
  - SVC_BASE_URL pointing at a running appointment-svc instance.
  - USER_ONE_TOKEN and USER_TWO_TOKEN for the conformance test in test_obo.py.
    These are tokens for two test SPs (or two test users) with deliberately
    divergent UC grants. The repo's root conftest.py will eventually own the
    creation of these fixtures; for now we read them from env so the test can
    be skipped cleanly when not configured.
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def svc_base_url() -> str:
    url = os.environ.get("SVC_BASE_URL")
    if not url:
        pytest.skip("SVC_BASE_URL not set; integration tests skipped")
    return url


@pytest.fixture(scope="session")
def user_one_token() -> str:
    tok = os.environ.get("USER_ONE_TOKEN")
    if not tok:
        pytest.skip("USER_ONE_TOKEN not set; isolation test skipped")
    return tok


@pytest.fixture(scope="session")
def user_two_token() -> str:
    tok = os.environ.get("USER_TWO_TOKEN")
    if not tok:
        pytest.skip("USER_TWO_TOKEN not set; isolation test skipped")
    return tok
