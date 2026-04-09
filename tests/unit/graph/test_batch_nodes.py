from unittest.mock import MagicMock

from synapps.graph.nodes import (
    batch_upsert_files,
    batch_upsert_directories,
    batch_upsert_packages,
    batch_upsert_classes,
    batch_upsert_interfaces,
    batch_upsert_methods,
    batch_upsert_properties,
    batch_upsert_fields,
)


def _conn() -> MagicMock:
    return MagicMock()


# --- batch_upsert_files ---

def test_batch_upsert_files_empty_batch_does_nothing() -> None:
    conn = _conn()
    batch_upsert_files(conn, [])
    conn.execute.assert_not_called()


def test_batch_upsert_files_single_item_uses_unwind_merge() -> None:
    conn = _conn()
    batch_upsert_files(conn, [{"path": "/proj/foo.py", "name": "foo.py", "language": "python"}])
    conn.execute.assert_called_once()
    cypher, params = conn.execute.call_args[0]
    assert "UNWIND" in cypher
    assert "MERGE" in cypher
    assert ":File" in cypher
    assert "batch" in params
    assert "ts" in params


def test_batch_upsert_files_multiple_items_single_call() -> None:
    conn = _conn()
    batch = [
        {"path": "/proj/a.py", "name": "a.py", "language": "python"},
        {"path": "/proj/b.py", "name": "b.py", "language": "python"},
    ]
    batch_upsert_files(conn, batch)
    assert conn.execute.call_count == 1


def test_batch_upsert_files_sets_name_language_last_indexed() -> None:
    conn = _conn()
    batch_upsert_files(conn, [{"path": "/proj/foo.py", "name": "foo.py", "language": "python"}])
    cypher, _ = conn.execute.call_args[0]
    assert "name" in cypher
    assert "language" in cypher
    assert "last_indexed" in cypher


# --- batch_upsert_directories ---

def test_batch_upsert_directories_empty_batch_does_nothing() -> None:
    conn = _conn()
    batch_upsert_directories(conn, [])
    conn.execute.assert_not_called()


def test_batch_upsert_directories_single_item_uses_unwind_merge() -> None:
    conn = _conn()
    batch_upsert_directories(conn, [{"path": "/proj/src", "name": "src"}])
    conn.execute.assert_called_once()
    cypher, params = conn.execute.call_args[0]
    assert "UNWIND" in cypher
    assert "MERGE" in cypher
    assert ":Directory" in cypher
    assert "batch" in params


def test_batch_upsert_directories_multiple_items_single_call() -> None:
    conn = _conn()
    batch = [
        {"path": "/proj/src", "name": "src"},
        {"path": "/proj/tests", "name": "tests"},
    ]
    batch_upsert_directories(conn, batch)
    assert conn.execute.call_count == 1


def test_batch_upsert_directories_sets_name() -> None:
    conn = _conn()
    batch_upsert_directories(conn, [{"path": "/proj/src", "name": "src"}])
    cypher, _ = conn.execute.call_args[0]
    assert "name" in cypher


# --- batch_upsert_packages ---

def test_batch_upsert_packages_empty_batch_does_nothing() -> None:
    conn = _conn()
    batch_upsert_packages(conn, [])
    conn.execute.assert_not_called()


def test_batch_upsert_packages_single_item_uses_unwind_merge() -> None:
    conn = _conn()
    batch_upsert_packages(conn, [{"full_name": "MyApp.Services", "name": "Services"}])
    conn.execute.assert_called_once()
    cypher, params = conn.execute.call_args[0]
    assert "UNWIND" in cypher
    assert "MERGE" in cypher
    assert ":Package" in cypher
    assert "batch" in params


def test_batch_upsert_packages_multiple_items_single_call() -> None:
    conn = _conn()
    batch = [
        {"full_name": "MyApp.Services", "name": "Services"},
        {"full_name": "MyApp.Models", "name": "Models"},
    ]
    batch_upsert_packages(conn, batch)
    assert conn.execute.call_count == 1


def test_batch_upsert_packages_merges_on_full_name() -> None:
    conn = _conn()
    batch_upsert_packages(conn, [{"full_name": "MyApp.Services", "name": "Services"}])
    cypher, _ = conn.execute.call_args[0]
    assert "full_name" in cypher


# --- batch_upsert_classes ---

def test_batch_upsert_classes_empty_batch_does_nothing() -> None:
    conn = _conn()
    batch_upsert_classes(conn, [])
    conn.execute.assert_not_called()


def test_batch_upsert_classes_single_item_uses_unwind_merge() -> None:
    conn = _conn()
    batch_upsert_classes(conn, [{"full_name": "MyApp.Foo", "name": "Foo", "kind": "class", "file_path": "/proj/Foo.cs", "line": 1, "end_line": 20, "language": "csharp"}])
    conn.execute.assert_called_once()
    cypher, params = conn.execute.call_args[0]
    assert "UNWIND" in cypher
    assert "MERGE" in cypher
    assert ":Class" in cypher
    assert "batch" in params


def test_batch_upsert_classes_multiple_items_single_call() -> None:
    conn = _conn()
    batch = [
        {"full_name": "MyApp.Foo", "name": "Foo", "kind": "class", "file_path": "/proj/Foo.cs", "line": 1, "end_line": 20, "language": "csharp"},
        {"full_name": "MyApp.Bar", "name": "Bar", "kind": "class", "file_path": "/proj/Bar.cs", "line": 1, "end_line": 30, "language": "csharp"},
    ]
    batch_upsert_classes(conn, batch)
    assert conn.execute.call_count == 1


def test_batch_upsert_classes_sets_all_fields() -> None:
    conn = _conn()
    batch_upsert_classes(conn, [{"full_name": "MyApp.Foo", "name": "Foo", "kind": "class", "file_path": "/proj/Foo.cs", "line": 1, "end_line": 20, "language": "csharp"}])
    cypher, _ = conn.execute.call_args[0]
    assert "kind" in cypher
    assert "file_path" in cypher
    assert "line" in cypher
    assert "end_line" in cypher
    assert "language" in cypher


# --- batch_upsert_interfaces ---

def test_batch_upsert_interfaces_empty_batch_does_nothing() -> None:
    conn = _conn()
    batch_upsert_interfaces(conn, [])
    conn.execute.assert_not_called()


def test_batch_upsert_interfaces_single_item_uses_unwind_merge() -> None:
    conn = _conn()
    batch_upsert_interfaces(conn, [{"full_name": "MyApp.IFoo", "name": "IFoo", "file_path": "/proj/IFoo.cs", "line": 1, "end_line": 10, "language": "csharp"}])
    conn.execute.assert_called_once()
    cypher, params = conn.execute.call_args[0]
    assert "UNWIND" in cypher
    assert "MERGE" in cypher
    assert ":Interface" in cypher
    assert "batch" in params


def test_batch_upsert_interfaces_multiple_items_single_call() -> None:
    conn = _conn()
    batch = [
        {"full_name": "MyApp.IFoo", "name": "IFoo", "file_path": "/proj/IFoo.cs", "line": 1, "end_line": 10, "language": "csharp"},
        {"full_name": "MyApp.IBar", "name": "IBar", "file_path": "/proj/IBar.cs", "line": 1, "end_line": 15, "language": "csharp"},
    ]
    batch_upsert_interfaces(conn, batch)
    assert conn.execute.call_count == 1


def test_batch_upsert_interfaces_sets_kind_to_interface() -> None:
    conn = _conn()
    batch_upsert_interfaces(conn, [{"full_name": "MyApp.IFoo", "name": "IFoo", "file_path": "", "line": 0, "end_line": 0, "language": ""}])
    cypher, _ = conn.execute.call_args[0]
    assert "'interface'" in cypher


# --- batch_upsert_methods ---

def test_batch_upsert_methods_empty_batch_does_nothing() -> None:
    conn = _conn()
    batch_upsert_methods(conn, [])
    conn.execute.assert_not_called()


def test_batch_upsert_methods_single_item_uses_unwind_merge() -> None:
    conn = _conn()
    batch_upsert_methods(conn, [{
        "full_name": "MyApp.Foo.Bar()",
        "name": "Bar",
        "signature": "void Bar()",
        "is_abstract": False,
        "is_static": False,
        "file_path": "/proj/Foo.cs",
        "line": 5,
        "end_line": 15,
        "language": "csharp",
        "is_classmethod": False,
        "is_async": False,
        "stub": False,
    }])
    conn.execute.assert_called_once()
    cypher, params = conn.execute.call_args[0]
    assert "UNWIND" in cypher
    assert "MERGE" in cypher
    assert ":Method" in cypher
    assert "batch" in params


def test_batch_upsert_methods_multiple_items_single_call() -> None:
    conn = _conn()
    item = {
        "full_name": "MyApp.Foo.Bar()",
        "name": "Bar",
        "signature": "void Bar()",
        "is_abstract": False,
        "is_static": False,
        "file_path": "/proj/Foo.cs",
        "line": 5,
        "end_line": 15,
        "language": "csharp",
        "is_classmethod": False,
        "is_async": False,
        "stub": False,
    }
    batch_upsert_methods(conn, [item, {**item, "full_name": "MyApp.Foo.Baz()"}])
    assert conn.execute.call_count == 1


def test_batch_upsert_methods_sets_all_fields() -> None:
    conn = _conn()
    batch_upsert_methods(conn, [{
        "full_name": "MyApp.Foo.Bar()",
        "name": "Bar",
        "signature": "void Bar()",
        "is_abstract": True,
        "is_static": False,
        "file_path": "/proj/Foo.cs",
        "line": 5,
        "end_line": 15,
        "language": "csharp",
        "is_classmethod": False,
        "is_async": True,
        "stub": False,
    }])
    cypher, _ = conn.execute.call_args[0]
    assert "signature" in cypher
    assert "is_abstract" in cypher
    assert "is_static" in cypher
    assert "file_path" in cypher
    assert "line" in cypher
    assert "end_line" in cypher
    assert "language" in cypher
    assert "is_classmethod" in cypher
    assert "is_async" in cypher
    assert "stub" in cypher


# --- batch_upsert_properties ---

def test_batch_upsert_properties_empty_batch_does_nothing() -> None:
    conn = _conn()
    batch_upsert_properties(conn, [])
    conn.execute.assert_not_called()


def test_batch_upsert_properties_single_item_uses_unwind_merge() -> None:
    conn = _conn()
    batch_upsert_properties(conn, [{"full_name": "MyApp.Foo.Name", "name": "Name", "type_name": "string", "file_path": "/proj/Foo.cs", "line": 5, "end_line": 5, "language": "csharp"}])
    conn.execute.assert_called_once()
    cypher, params = conn.execute.call_args[0]
    assert "UNWIND" in cypher
    assert "MERGE" in cypher
    assert ":Property" in cypher
    assert "batch" in params


def test_batch_upsert_properties_multiple_items_single_call() -> None:
    conn = _conn()
    batch = [
        {"full_name": "MyApp.Foo.Name", "name": "Name", "type_name": "string", "file_path": "/proj/Foo.cs", "line": 5, "end_line": 5, "language": "csharp"},
        {"full_name": "MyApp.Foo.Age", "name": "Age", "type_name": "int", "file_path": "/proj/Foo.cs", "line": 6, "end_line": 6, "language": "csharp"},
    ]
    batch_upsert_properties(conn, batch)
    assert conn.execute.call_count == 1


def test_batch_upsert_properties_sets_type_name_and_location() -> None:
    conn = _conn()
    batch_upsert_properties(conn, [{"full_name": "MyApp.Foo.Name", "name": "Name", "type_name": "string", "file_path": "/proj/Foo.cs", "line": 5, "end_line": 5, "language": "csharp"}])
    cypher, _ = conn.execute.call_args[0]
    assert "type_name" in cypher
    assert "file_path" in cypher
    assert "line" in cypher
    assert "end_line" in cypher
    assert "language" in cypher


# --- batch_upsert_fields ---

def test_batch_upsert_fields_empty_batch_does_nothing() -> None:
    conn = _conn()
    batch_upsert_fields(conn, [])
    conn.execute.assert_not_called()


def test_batch_upsert_fields_single_item_uses_unwind_merge() -> None:
    conn = _conn()
    batch_upsert_fields(conn, [{"full_name": "MyApp.Foo._count", "name": "_count", "type_name": "int", "file_path": "/proj/Foo.cs", "line": 3, "end_line": 3, "language": "csharp"}])
    conn.execute.assert_called_once()
    cypher, params = conn.execute.call_args[0]
    assert "UNWIND" in cypher
    assert "MERGE" in cypher
    assert ":Field" in cypher
    assert "batch" in params


def test_batch_upsert_fields_multiple_items_single_call() -> None:
    conn = _conn()
    batch = [
        {"full_name": "MyApp.Foo._count", "name": "_count", "type_name": "int", "file_path": "/proj/Foo.cs", "line": 3, "end_line": 3, "language": "csharp"},
        {"full_name": "MyApp.Foo._name", "name": "_name", "type_name": "string", "file_path": "/proj/Foo.cs", "line": 4, "end_line": 4, "language": "csharp"},
    ]
    batch_upsert_fields(conn, batch)
    assert conn.execute.call_count == 1


def test_batch_upsert_fields_sets_type_name_and_location() -> None:
    conn = _conn()
    batch_upsert_fields(conn, [{"full_name": "MyApp.Foo._count", "name": "_count", "type_name": "int", "file_path": "/proj/Foo.cs", "line": 3, "end_line": 3, "language": "csharp"}])
    cypher, _ = conn.execute.call_args[0]
    assert "type_name" in cypher
    assert "file_path" in cypher
    assert "line" in cypher
    assert "end_line" in cypher
    assert "language" in cypher
