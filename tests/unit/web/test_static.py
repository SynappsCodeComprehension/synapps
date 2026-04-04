from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from synapps.web.app import create_app


def test_static_files_served_when_directory_exists():
    """When static dir exists with index.html, GET / returns it."""
    svc = MagicMock()
    # We need the static dir to actually exist for this test
    static_dir = Path(__file__).resolve().parents[3] / "src" / "synapps" / "web" / "static"
    if not static_dir.is_dir() or not (static_dir / "index.html").exists():
        import pytest
        pytest.skip("Static files not built yet — run scripts/build_spa.sh first")

    app = create_app(svc)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text or "<html" in response.text


def test_api_routes_not_shadowed_by_static():
    """API routes respond before the static files catch-all."""
    svc = MagicMock()
    svc.search_symbols.return_value = [{"full_name": "Test.Foo", "name": "Foo"}]
    app = create_app(svc)
    client = TestClient(app)
    response = client.get("/api/search_symbols?query=Foo")
    assert response.status_code == 200
    assert response.json()[0]["full_name"] == "Test.Foo"
