from unittest.mock import MagicMock, patch

from synapps.indexer.indexer import Indexer
from synapps.lsp.interface import IndexSymbol, SymbolKind
from synapps.plugin.java import JavaPlugin


def _mock_lsp(files: list[str], symbols_by_file: dict[str, list[IndexSymbol]]) -> MagicMock:
    lsp = MagicMock()
    lsp.get_workspace_files.return_value = files
    lsp.get_document_symbols.side_effect = lambda f: symbols_by_file.get(f, [])
    lsp.language_server = MagicMock()
    return lsp


def test_index_project_calls_set_attributes(tmp_path) -> None:
    cs_file = tmp_path / "Test.cs"
    cs_file.write_text("""
[ApiController]
public class TaskController {
    [HttpGet]
    public void Get() { }
}
""")
    file_path = str(cs_file)
    symbols = [
        IndexSymbol(
            name="TaskController", full_name="Ns.TaskController", kind=SymbolKind.CLASS,
            file_path=file_path, line=2, end_line=6, signature="", is_abstract=False, is_static=False,
        ),
        IndexSymbol(
            name="Get", full_name="Ns.TaskController.Get", kind=SymbolKind.METHOD,
            file_path=file_path, line=4, end_line=5, signature="void Get()", is_abstract=False, is_static=False,
        ),
    ]
    lsp = _mock_lsp([file_path], {file_path: symbols})
    conn = MagicMock()

    with patch("synapps.indexer.indexer.SymbolResolver"), \
         patch("synapps.indexer.indexer.MethodImplementsIndexer"):
        indexer = Indexer(conn, lsp)
        indexer.index_project(str(tmp_path), "csharp")

    # Verify set_attributes was called for both attributed symbols
    set_attr_calls = [
        c for c in conn.execute.call_args_list
        if "attributes" in str(c)
    ]
    assert len(set_attr_calls) >= 2, f"Expected at least 2 set_attributes calls, got {len(set_attr_calls)}"


def test_reindex_file_calls_set_attributes(tmp_path) -> None:
    cs_file = tmp_path / "Test.cs"
    cs_file.write_text("""
[Serializable]
public class Foo { }
""")
    file_path = str(cs_file)
    symbols = [
        IndexSymbol(
            name="Foo", full_name="Ns.Foo", kind=SymbolKind.CLASS,
            file_path=file_path, line=2, end_line=3, signature="", is_abstract=False, is_static=False,
        ),
    ]
    lsp = _mock_lsp([file_path], {file_path: symbols})
    conn = MagicMock()

    with patch("synapps.indexer.indexer.SymbolResolver"), \
         patch("synapps.indexer.indexer.MethodImplementsIndexer"):
        indexer = Indexer(conn, lsp)
        indexer.reindex_file(file_path, str(tmp_path))

    set_attr_calls = [
        c for c in conn.execute.call_args_list
        if "attributes" in str(c)
    ]
    assert len(set_attr_calls) >= 1, f"Expected at least 1 set_attributes call, got {len(set_attr_calls)}"


def test_index_project_java_attributes(tmp_path) -> None:
    """Java method-level annotations and modifiers are resolved via name_to_full lookup."""
    java_file = tmp_path / "AnimalService.java"
    java_file.write_text("""
package com.test;

public class AnimalService {
    @Deprecated
    public static synchronized void legacyMethod() {
        // Legacy code
    }
}
""")
    file_path = str(java_file)
    # Java full_names for methods include parentheses per Java indexer convention
    symbols = [
        IndexSymbol(
            name="AnimalService", full_name="com.test.AnimalService", kind=SymbolKind.CLASS,
            file_path=file_path, line=4, end_line=9, signature="", is_abstract=False, is_static=False,
        ),
        IndexSymbol(
            name="legacyMethod", full_name="com.test.AnimalService.legacyMethod()", kind=SymbolKind.METHOD,
            file_path=file_path, line=6, end_line=8, signature="void legacyMethod()",
            is_abstract=False, is_static=True, parent_full_name="com.test.AnimalService",
        ),
    ]
    plugin = JavaPlugin()
    lsp = _mock_lsp([file_path], {file_path: symbols})
    conn = MagicMock()

    with patch("synapps.indexer.indexer.SymbolResolver"), \
         patch("synapps.indexer.indexer.MethodImplementsIndexer"):
        indexer = Indexer(conn, lsp, plugin=plugin)
        indexer.index_project(str(tmp_path), "java")

    # Verify set_attributes was called for legacyMethod (deprecated, static, synchronized)
    set_attr_calls = [
        c for c in conn.execute.call_args_list
        if "attributes" in str(c)
    ]
    assert len(set_attr_calls) >= 1, (
        f"Expected at least 1 set_attributes call for Java attributes, got {len(set_attr_calls)}"
    )
    # The call args should reference the Java full_name with parentheses
    all_call_strs = " ".join(str(c) for c in set_attr_calls)
    assert "legacyMethod" in all_call_strs, (
        "Expected set_attributes to be called with legacyMethod full_name"
    )


def test_index_project_java_class_attributes(tmp_path) -> None:
    """Java class-level annotations are resolved via name_to_full lookup."""
    java_file = tmp_path / "MyService.java"
    java_file.write_text("""
package com.test;

public abstract class MyService {
    public abstract void process();
}
""")
    file_path = str(java_file)
    symbols = [
        IndexSymbol(
            name="MyService", full_name="com.test.MyService", kind=SymbolKind.CLASS,
            file_path=file_path, line=4, end_line=7, signature="", is_abstract=True, is_static=False,
        ),
        IndexSymbol(
            name="process", full_name="com.test.MyService.process()", kind=SymbolKind.METHOD,
            file_path=file_path, line=5, end_line=5, signature="abstract void process()",
            is_abstract=True, is_static=False, parent_full_name="com.test.MyService",
        ),
    ]
    plugin = JavaPlugin()
    lsp = _mock_lsp([file_path], {file_path: symbols})
    conn = MagicMock()

    with patch("synapps.indexer.indexer.SymbolResolver"), \
         patch("synapps.indexer.indexer.MethodImplementsIndexer"):
        indexer = Indexer(conn, lsp, plugin=plugin)
        indexer.index_project(str(tmp_path), "java")

    # The abstract modifier on MyService class and process method should produce attribute writes
    set_attr_calls = [
        c for c in conn.execute.call_args_list
        if "attributes" in str(c)
    ]
    assert len(set_attr_calls) >= 1, (
        f"Expected at least 1 set_attributes call for abstract class/method, got {len(set_attr_calls)}"
    )
    all_call_strs = " ".join(str(c) for c in set_attr_calls)
    assert "MyService" in all_call_strs or "process" in all_call_strs, (
        "Expected set_attributes to reference MyService or process"
    )
