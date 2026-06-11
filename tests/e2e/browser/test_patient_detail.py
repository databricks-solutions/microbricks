"""Browser E2E: Patient detail page — multi-service aggregation view."""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e_browser


def test_patient_detail_renders_from_list(page: Page, app_url: str):
    page.goto(f"{app_url}/patients")
    page.wait_for_load_state("networkidle")

    # Click the first patient link in the table
    first_patient_link = page.locator("table tbody tr a").first
    expect(first_patient_link).to_be_visible(timeout=15_000)
    first_patient_link.click()

    # Should navigate to patient detail page
    page.wait_for_load_state("networkidle")

    # Patient detail shows name/MRN/DOB
    page.wait_for_selector("text=/MRN/", timeout=15_000)


def test_patient_detail_shows_tabs(page: Page, app_url: str):
    page.goto(f"{app_url}/patients")
    page.wait_for_load_state("networkidle")

    first_patient_link = page.locator("table tbody tr a").first
    expect(first_patient_link).to_be_visible(timeout=15_000)
    first_patient_link.click()
    page.wait_for_load_state("networkidle")

    # Detail page should have tab-like navigation (appointments, labs, etc.)
    tabs = page.locator("[role='tablist'] [role='tab'], button:has-text('Appointment'), button:has-text('Timeline')")
    expect(tabs.first).to_be_visible(timeout=15_000)


def test_patient_detail_no_error_state(page: Page, app_url: str):
    page.goto(f"{app_url}/patients")
    page.wait_for_load_state("networkidle")

    first_patient_link = page.locator("table tbody tr a").first
    expect(first_patient_link).to_be_visible(timeout=15_000)
    first_patient_link.click()
    page.wait_for_load_state("networkidle")

    # No error boundaries should fire
    error_text = page.locator("text=Failed to load")
    expect(error_text).to_have_count(0)
