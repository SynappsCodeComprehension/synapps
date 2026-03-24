from __future__ import annotations

import tree_sitter_typescript
from tree_sitter import Language, Parser

from synapse.indexer.typescript.typescript_http_extractor import TypeScriptHttpExtractor
from synapse.lsp.interface import IndexSymbol, SymbolKind

_lang = Language(tree_sitter_typescript.language_typescript())
_parser = Parser(_lang)


def _parse(source: str):
    return _parser.parse(bytes(source, "utf-8"))


def _symbols(pairs: list[tuple[str, str, int, int]]) -> list[IndexSymbol]:
    """Build IndexSymbol list from (name, full_name, line, end_line) tuples."""
    return [
        IndexSymbol(name=n, full_name=fn, kind=SymbolKind.METHOD, file_path="test.ts", line=ln, end_line=el)
        for n, fn, ln, el in pairs
    ]


def test_axios_style_get() -> None:
    source = """
function getItems() {
    return api.get('/items');
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("getItems", "mod.getItems", 2, 4)]))
    assert len(result.client_calls) == 1
    call = result.client_calls[0]
    assert call.route == "/items"
    assert call.http_method == "GET"
    assert call.caller_full_name == "mod.getItems"


def test_axios_style_post() -> None:
    source = """
function createItem(data) {
    return api.post('/items', data);
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("createItem", "mod.createItem", 2, 4)]))
    assert len(result.client_calls) == 1
    assert result.client_calls[0].http_method == "POST"


def test_fetch_with_method_option() -> None:
    source = """
function deleteItem(id) {
    return fetch('/items/' + id, { method: 'DELETE' });
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("deleteItem", "mod.deleteItem", 2, 4)]))
    assert len(result.client_calls) == 1
    assert result.client_calls[0].http_method == "DELETE"


def test_fetch_defaults_to_get() -> None:
    source = """
function getItems() {
    return fetch('/items');
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("getItems", "mod.getItems", 2, 4)]))
    assert len(result.client_calls) == 1
    assert result.client_calls[0].http_method == "GET"


def test_template_literal_parameterized() -> None:
    source = """
function getItem(id) {
    return api.get(`/items/${id}`);
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("getItem", "mod.getItem", 2, 4)]))
    assert len(result.client_calls) == 1
    assert result.client_calls[0].route == "/items/{id}"


def test_constant_reference() -> None:
    source = """
const ITEMS_ENDPOINT = '/items';

function getItems() {
    return api.get(ITEMS_ENDPOINT);
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("getItems", "mod.getItems", 4, 6)]))
    assert len(result.client_calls) == 1
    assert result.client_calls[0].route == "/items"


def test_false_positive_rejected_no_path() -> None:
    source = """
function lookup() {
    return map.get('some-key');
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("lookup", "mod.lookup", 2, 4)]))
    assert len(result.client_calls) == 0


def test_dynamic_url_skipped() -> None:
    source = """
function getData() {
    return api.get(buildUrl('items'));
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("getData", "mod.getData", 2, 4)]))
    assert len(result.client_calls) == 0


def test_no_server_defs_returned() -> None:
    source = """
function getItems() {
    return api.get('/items');
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("getItems", "mod.getItems", 2, 4)]))
    assert result.endpoint_defs == []


def test_empty_source() -> None:
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(""), [])
    assert result.client_calls == []
    assert result.endpoint_defs == []


def test_multiple_calls_in_one_function() -> None:
    source = """
async function sync() {
    await api.get('/items');
    await api.post('/items', data);
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("sync", "mod.sync", 2, 5)]))
    assert len(result.client_calls) == 2
    methods = {c.http_method for c in result.client_calls}
    assert methods == {"GET", "POST"}
