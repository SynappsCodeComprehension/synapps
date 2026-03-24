from __future__ import annotations

from synapse.indexer.http.route_utils import normalize_route


def test_strips_type_constraints() -> None:
    assert normalize_route("{id:guid}") == "/{id}"
    assert normalize_route("{id:int}") == "/{id}"
    assert normalize_route("items/{slug:alpha}") == "/items/{slug}"


def test_strips_regex_constraints() -> None:
    assert normalize_route("{slug:[a-z]+}") == "/{slug}"


def test_ensures_leading_slash() -> None:
    assert normalize_route("api/items") == "/api/items"


def test_strips_trailing_slash() -> None:
    assert normalize_route("/api/items/") == "/api/items"


def test_collapses_double_slashes() -> None:
    assert normalize_route("/api//items") == "/api/items"


def test_preserves_case() -> None:
    assert normalize_route("/Api/Items") == "/Api/Items"


def test_empty_returns_root() -> None:
    assert normalize_route("") == "/"


def test_already_normalized() -> None:
    assert normalize_route("/api/items/{id}") == "/api/items/{id}"


def test_combines_class_and_method_route() -> None:
    assert normalize_route("api/items", "{id:guid}") == "/api/items/{id}"


def test_method_route_only() -> None:
    assert normalize_route("", "items/{id}") == "/items/{id}"


def test_tilde_override_ignores_class_route() -> None:
    assert normalize_route("api/items", "~/api/auth/me") == "/api/auth/me"


def test_multiple_params() -> None:
    assert normalize_route("api/{org:guid}/items/{id:int}") == "/api/{org}/items/{id}"
