"""Browser E2E: Patient list — search and pagination."""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e_browser


def test_patients_page_renders_table(page: Page, app_url: str):
    page.goto(f"{app_url}/patients")
    page.wait_for_load_state("networkidle")

    heading = page.locator("text=Patients")
    expect(heading.first).to_be_visible(timeout=15_000)

    # Table with patient rows
    table = page.locator("table")
    expect(table).to_be_visible(timeout=15_000)
    rows = page.locator("table tbody tr")
    expect(rows.first).to_be_visible(timeout=15_000)


def test_search_filters_patients(page: Page, app_url: str):
    page.goto(f"{app_url}/patients")
    page.wait_for_load_state("networkidle")

    # Wait for initial load
    rows_before = page.locator("table tbody tr")
    expect(rows_before.first).to_be_visible(timeout=15_000)

    # Type a search query that likely matches fewer results
    search_input = page.locator("input[placeholder*='Search']")
    expect(search_input).to_be_visible()
    search_input.fill("zzz-nonexistent-name-xyz")
    # Wait for debounce + re-fetch
    page.wait_for_timeout(500)
    page.wait_for_load_state("networkidle")

    # Either no rows or "No results" / empty state
    rows_after = page.locator("table tbody tr")
    count = rows_after.count()
    assert count == 0 or page.locator("text=/[Nn]o (results|patients)/").count() > 0


def test_clear_search_restores_results(page: Page, app_url: str):
    page.goto(f"{app_url}/patients")
    page.wait_for_load_state("networkidle")

    search_input = page.locator("input[placeholder*='Search']")
    expect(search_input).to_be_visible(timeout=15_000)

    # Type something, then clear
    search_input.fill("test")
    page.wait_for_timeout(500)
    search_input.fill("")
    page.wait_for_timeout(500)
    page.wait_for_load_state("networkidle")

    # Table should have rows again
    rows = page.locator("table tbody tr")
    expect(rows.first).to_be_visible(timeout=10_000)
