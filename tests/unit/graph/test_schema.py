from unittest.mock import MagicMock
from synapps.graph.schema import _INDEX_DEFS, ensure_schema


def test_ensure_schema_memgraph_creates_indices() -> None:
    conn = MagicMock()
    conn.dialect = "memgraph"
    ensure_schema(conn)
    calls = [c[0][0] for c in conn.execute_implicit.call_args_list]
    # Memgraph syntax: CREATE INDEX ON :Label(prop)
    assert any("CREATE INDEX ON :File" in c for c in calls)
    assert any("CREATE INDEX ON :Class" in c for c in calls)
    assert any("CREATE INDEX ON :Method" in c for c in calls)


def test_ensure_schema_neo4j_creates_indices() -> None:
    conn = MagicMock()
    conn.dialect = "neo4j"
    ensure_schema(conn)
    calls = [c[0][0] for c in conn.execute_implicit.call_args_list]
    # Neo4j syntax: CREATE INDEX FOR (n:Label) ON (n.prop)
    assert any("CREATE INDEX FOR (n:File)" in c for c in calls)
    assert any("CREATE INDEX FOR (n:Class)" in c for c in calls)
    assert any("CREATE INDEX FOR (n:Method)" in c for c in calls)


def test_schema_includes_package_index() -> None:
    conn = MagicMock()
    conn.dialect = "memgraph"
    ensure_schema(conn)
    calls = [c[0][0] for c in conn.execute_implicit.call_args_list]
    assert any(":Package" in c for c in calls)


def test_schema_includes_interface_index() -> None:
    conn = MagicMock()
    conn.dialect = "memgraph"
    ensure_schema(conn)
    calls = [c[0][0] for c in conn.execute_implicit.call_args_list]
    assert any(":Interface" in c for c in calls)


def test_schema_does_not_include_namespace_index() -> None:
    conn = MagicMock()
    conn.dialect = "memgraph"
    ensure_schema(conn)
    calls = [c[0][0] for c in conn.execute_implicit.call_args_list]
    assert not any(":Namespace" in c for c in calls)


def test_schema_creates_index_for_each_node_type() -> None:
    """Schema creates indices for all node types used in the graph."""
    conn = MagicMock()
    conn.dialect = "memgraph"
    ensure_schema(conn)
    calls = [c[0][0] for c in conn.execute_implicit.call_args_list]
    for label in ["Repository", "Directory", "File", "Package",
                  "Class", "Interface", "Method", "Property", "Field", "Endpoint"]:
        assert any(f":{label}" in c for c in calls), f"Missing index for :{label}"


def test_class_file_path_index_exists() -> None:
    assert ("Class", "file_path") in _INDEX_DEFS


def test_interface_file_path_index_exists() -> None:
    assert ("Interface", "file_path") in _INDEX_DEFS


def test_property_name_index_exists() -> None:
    assert ("Property", "name") in _INDEX_DEFS


def test_field_name_index_exists() -> None:
    assert ("Field", "name") in _INDEX_DEFS


def test_all_existing_indexes_preserved() -> None:
    """Existing indexes must not be removed."""
    required = [
        ("Repository", "path"), ("Directory", "path"), ("File", "path"),
        ("Package", "full_name"), ("Class", "full_name"), ("Class", "name"),
        ("Interface", "full_name"), ("Interface", "name"),
        ("Method", "full_name"), ("Method", "name"), ("Method", "file_path"),
        ("Property", "full_name"), ("Field", "full_name"), ("Endpoint", "route"),
    ]
    for entry in required:
        assert entry in _INDEX_DEFS, f"Missing required index: {entry}"
