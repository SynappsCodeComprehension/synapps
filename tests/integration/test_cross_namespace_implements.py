"""
Integration test for cross-namespace IMPLEMENTS edge isolation.

Indexes a fixture with 3 C# projects that each define identical ICache/Cache
pairs under different namespaces (AlphaCache, BetaCache, GammaCache).

Each Cache class must have exactly ONE :IMPLEMENTS edge pointing to its own
namespace's ICache — not to any other namespace's ICache.

Requires Memgraph on localhost:7687 and .NET SDK.
Run with: pytest tests/integration/test_cross_namespace_implements.py -v -m integration
"""
from __future__ import annotations

import pathlib

import pytest

from synapps.graph.connection import GraphConnection
from synapps.graph.schema import ensure_schema
from synapps.service import SynappsService

FIXTURE_PATH = str(
    (pathlib.Path(__file__).parent.parent / "fixtures" / "SynappsCrossNamespace").resolve()
)

NAMESPACES = ["AlphaCache", "BetaCache", "GammaCache"]


def _delete_project(conn: GraphConnection, path: str) -> None:
    conn.execute(
        "MATCH (r:Repository {path: $path})-[:CONTAINS*]->(n) DETACH DELETE n",
        {"path": path},
    )
    conn.execute(
        "MATCH (r:Repository {path: $path}) DELETE r",
        {"path": path},
    )


@pytest.fixture(scope="module")
def cross_ns_service():
    conn = GraphConnection.create(database="memgraph")
    ensure_schema(conn)
    _delete_project(conn, FIXTURE_PATH)

    svc = SynappsService(conn=conn)
    svc.index_project(FIXTURE_PATH, "csharp")

    yield svc, conn

    _delete_project(conn, FIXTURE_PATH)


@pytest.mark.integration
@pytest.mark.timeout(120)
def test_each_cache_implements_only_its_own_icache(cross_ns_service) -> None:
    """Each Cache class has exactly one IMPLEMENTS edge to its own ICache."""
    _, conn = cross_ns_service

    for ns in NAMESPACES:
        cache_full = f"{ns}.Cache"
        expected_iface = f"{ns}.ICache"

        results = conn.query(
            "MATCH (c {full_name: $cache})-[:IMPLEMENTS]->(i) "
            "RETURN i.full_name AS iface",
            {"cache": cache_full},
        )

        ifaces = [r["iface"] for r in results]
        assert len(ifaces) == 1, (
            f"{cache_full} should implement exactly 1 interface, "
            f"got {len(ifaces)}: {ifaces}"
        )
        assert ifaces[0] == expected_iface, (
            f"{cache_full} should implement {expected_iface}, "
            f"got {ifaces[0]}"
        )


@pytest.mark.integration
@pytest.mark.timeout(120)
def test_no_cross_namespace_implements_edges(cross_ns_service) -> None:
    """No IMPLEMENTS edge connects a Cache to an ICache from a different namespace."""
    _, conn = cross_ns_service

    results = conn.query(
        "MATCH (c)-[:IMPLEMENTS]->(i) "
        "WHERE c.full_name ENDS WITH '.Cache' "
        "  AND i.full_name ENDS WITH '.ICache' "
        "  AND split(c.full_name, '.')[0] <> split(i.full_name, '.')[0] "
        "RETURN c.full_name AS cache, i.full_name AS iface",
    )

    assert len(results) == 0, (
        f"Found cross-namespace IMPLEMENTS edges: "
        f"{[(r['cache'], r['iface']) for r in results]}"
    )


@pytest.mark.integration
@pytest.mark.timeout(120)
def test_total_implements_edge_count(cross_ns_service) -> None:
    """Exactly 3 IMPLEMENTS edges exist for the Cache classes (one per namespace)."""
    _, conn = cross_ns_service

    results = conn.query(
        "MATCH (c)-[:IMPLEMENTS]->(i) "
        "WHERE c.full_name ENDS WITH '.Cache' "
        "  AND i.full_name ENDS WITH '.ICache' "
        "RETURN count(*) AS cnt",
    )

    assert results[0]["cnt"] == 3, (
        f"Expected exactly 3 IMPLEMENTS edges (one per namespace), "
        f"got {results[0]['cnt']}"
    )


@pytest.mark.integration
@pytest.mark.timeout(120)
def test_all_three_icache_interfaces_exist(cross_ns_service) -> None:
    """All three ICache interfaces are indexed as separate nodes."""
    _, conn = cross_ns_service

    results = conn.query(
        "MATCH (i:Interface) "
        "WHERE i.full_name ENDS WITH '.ICache' "
        "RETURN i.full_name AS name ORDER BY name",
    )

    names = [r["name"] for r in results]
    assert names == ["AlphaCache.ICache", "BetaCache.ICache", "GammaCache.ICache"], (
        f"Expected 3 distinct ICache interfaces, got: {names}"
    )


@pytest.mark.integration
@pytest.mark.timeout(120)
def test_all_three_cache_classes_exist(cross_ns_service) -> None:
    """All three Cache classes are indexed as separate nodes."""
    _, conn = cross_ns_service

    results = conn.query(
        "MATCH (c:Class) "
        "WHERE c.full_name ENDS WITH '.Cache' "
        "RETURN c.full_name AS name ORDER BY name",
    )

    names = [r["name"] for r in results]
    assert names == ["AlphaCache.Cache", "BetaCache.Cache", "GammaCache.Cache"], (
        f"Expected 3 distinct Cache classes, got: {names}"
    )
