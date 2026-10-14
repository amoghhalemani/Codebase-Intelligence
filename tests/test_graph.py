import sys

from core.graph import DependencyGraph
from core.models import DependencyEdge
from storage.graph_store import Neo4jGraphStore, NullGraphStore, build_graph_store


def test_dependency_graph_tracks_callers_and_dependencies():
    graph = DependencyGraph()
    graph.add_edge("app:<module>", "app:main", "defines")
    graph.add_edge("app:main", "billing:calculate_tax", "call")

    assert "billing:calculate_tax" in graph.dependencies("app:main")
    assert "app:main" in graph.dependents("billing:calculate_tax")
    assert graph.graph.number_of_edges() == 2


def test_graph_store_defaults_to_null_store_when_neo4j_is_unconfigured(monkeypatch):
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)

    store = build_graph_store()

    assert isinstance(store, NullGraphStore)
    store.clear_repository("demo")
    store.persist("demo", [])


def test_neo4j_store_serializes_nested_evidence_for_properties(monkeypatch):
    recorded = {}

    class FakeSession:
        def __init__(self):
            self.calls = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def run(self, query, **kwargs):
            recorded["query"] = query
            recorded["kwargs"] = kwargs
            return None

    class FakeDriver:
        def session(self, database=None):
            return FakeSession()

    class FakeModule:
        GraphDatabase = type(
            "GraphDatabase",
            (),
            {"driver": staticmethod(lambda uri, auth: FakeDriver())},
        )

    monkeypatch.setitem(sys.modules, "neo4j", FakeModule())

    store = Neo4jGraphStore(uri="bolt://localhost:7687", user="neo4j", password="secret")
    store.persist(
        "demo",
        [
            DependencyEdge(
                source_id="app:main",
                target_id="billing:calculate_tax",
                relationship="call",
                evidence={"raw": [{"file": "analyzers/base.py"}]},
                confidence=0.9,
            )
        ],
    )

    assert isinstance(recorded["kwargs"]["evidence"], str)
    assert '"file": "analyzers/base.py"' in recorded["kwargs"]["evidence"]


def test_dependency_graph_exposes_path_and_call_chain_queries():
    graph = DependencyGraph()
    graph.add_edge("app:main", "billing:calculate_tax", "call")
    graph.add_edge("app:main", "inventory:sync", "call")
    graph.add_edge("inventory:sync", "billing:calculate_tax", "call")

    paths = graph.find_paths("app:main", "billing:calculate_tax")
    assert any(path == ["app:main", "billing:calculate_tax"] for path in paths)
    assert any(path == ["app:main", "inventory:sync", "billing:calculate_tax"] for path in paths)

    shortest = graph.shortest_path("app:main", "billing:calculate_tax")
    assert shortest == ["app:main", "billing:calculate_tax"]

    call_chain = graph.call_chain("app:main", "billing:calculate_tax")
    assert call_chain == paths
