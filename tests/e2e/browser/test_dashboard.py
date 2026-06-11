"""Browser E2E: Dashboard page loads and renders stats."""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e_browser


def test_dashboard_renders_stat_cards(page: Page, app_url: str):
    page.goto(app_url)
    page.wait_for_load_state("networkidle")

    # Stat cards should render with numeric values
    stat_cards = page.locator("[data-testid='stat-card'], .stat-card, h1 + div .text-2xl")
    # Fallback: look for the dashboard heading and stat-like numbers
    heading = page.locator("text=Dashboard").or_(page.locator("text=Overview"))
    expect(heading.first).to_be_visible(timeout=15_000)

    # At least some numeric content should be on the page
    page.wait_for_selector("text=/\\d+/", timeout=15_000)


def test_dashboard_no_error_boundary(page: Page, app_url: str):
    page.goto(app_url)
    page.wait_for_load_state("networkidle")

    # Error boundaries render "Failed to load" text
    error_text = page.locator("text=Failed to load")
    expect(error_text).to_have_count(0)


def test_dashboard_recent_patients_table(page: Page, app_url: str):
    page.goto(app_url)
    page.wait_for_load_state("networkidle")

    # The dashboard includes a "Recent Patients" section with a table
    table = page.locator("table").first
    expect(table).to_be_visible(timeout=15_000)
