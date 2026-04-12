"""
E2E tests for the search-to-graph workflow.

Covers E2E-03: search_symbols returns table results,
find_callees triggers graph visualization.

Requires: live Memgraph + indexed SynappsTest fixture.
Run with: pytest tests/e2e/test_search_workflow.py -v -m e2e --timeout=60
"""
from __future__ import annotations

import pytest
from playwright.sync_api import expect

pytestmark = [pytest.mark.e2e, pytest.mark.timeout(60)]


def test_search_symbols_shows_table(app_page) -> None:
    page = app_page
    page.locator("[data-testid='tool-btn-search_symbols']").click()
    page.locator("[data-testid='param-query']").fill("TaskService")
    page.locator("[data-testid='tool-submit']").click()
    page.wait_for_selector("[data-testid='result-table']", timeout=10000)
    expect(page.locator("[data-testid='result-panel']")).to_be_visible()
    assert page.locator("[data-testid='result-table'] tr").count() > 0


def test_find_callees_shows_graph(app_page) -> None:
    page = app_page
    page.locator("[data-testid='tool-btn-find_callees']").click()
    page.locator("[data-testid='param-full_name']").fill("SynappsTest.Services.TaskService.CreateTaskAsync")
    page.locator("[data-testid='tool-submit']").click()
    page.wait_for_selector("[data-testid='graph-svg'] g.node", timeout=15000)
    assert page.locator("[data-testid='graph-svg'] g.node").count() > 0
    expect(page.locator("[data-testid='result-panel']")).to_be_visible()
