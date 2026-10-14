import json
import os
from abc import ABC, abstractmethod
from typing import Any, Iterable

from core.models import DependencyEdge


class GraphStore(ABC):
    @abstractmethod
    def persist(self, repository: str, edges: Iterable[DependencyEdge]) -> None:
        raise NotImplementedError

    @abstractmethod
    def clear_repository(self, repository: str) -> None:
        raise NotImplementedError

    def query_paths(self, repository: str, source: str, target: str, cutoff: int = 5) -> list[list[str]]:
        return []

    def query_shortest_path(self, repository: str, source: str, target: str, cutoff: int = 5) -> list[str]:
        paths = self.query_paths(repository, source, target, cutoff=cutoff)
        return paths[0] if paths else []

    def query_call_chain(self, repository: str, source: str, target: str, cutoff: int = 5) -> list[list[str]]:
        return self.query_paths(repository, source, target, cutoff=cutoff)

    def query_neighbors(self, repository: str, node_id: str) -> list[dict[str, Any]]:
        return []


class NullGraphStore(GraphStore):
    def persist(self, repository: str, edges: Iterable[DependencyEdge]) -> None:
        return None

    def clear_repository(self, repository: str) -> None:
        return None


class Neo4jGraphStore(GraphStore):
    """Optional Neo4j-backed graph store for production graph queries."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self.uri = uri or os.getenv("NEO4J_URI")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self._driver = None

        if not self.uri or not self.password:
            raise ValueError(
                "Neo4j graph store requires NEO4J_URI and NEO4J_PASSWORD environment variables."
            )

    def _connect(self):
        if self._driver is None:
            try:
                from neo4j import GraphDatabase
            except ImportError as exc:  # pragma: no cover - dependency guard
                raise RuntimeError("neo4j package is required for Neo4jGraphStore") from exc

            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver

    def persist(self, repository: str, edges: Iterable[DependencyEdge]) -> None:
        driver = self._connect()
        with driver.session(database="neo4j") as session:
            session.run(
                "MATCH (n {repository: $repository}) DETACH DELETE n",
                repository=repository,
            )

            for edge in edges:
                session.run(
                    """
                    MERGE (source:Symbol {id: $source_id, repository: $repository})
                    MERGE (target:Symbol {id: $target_id, repository: $repository})
                    MERGE (source)-[r:DEPENDS_ON {relationship: $relationship, repository: $repository, confidence: $confidence, evidence: $evidence}]->(target)
                    RETURN count(r)
                    """,
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    repository=repository,
                    relationship=edge.relationship,
                    confidence=edge.confidence,
                    evidence=json.dumps(edge.evidence, sort_keys=True),
                )

    def clear_repository(self, repository: str) -> None:
        driver = self._connect()
        with driver.session(database="neo4j") as session:
            session.run(
                "MATCH (n {repository: $repository}) DETACH DELETE n",
                repository=repository,
            )

    def query_paths(self, repository: str, source: str, target: str, cutoff: int = 5) -> list[list[str]]:
        driver = self._connect()
        with driver.session(database="neo4j") as session:
            rows = session.run(
                """
                MATCH p = (source:Symbol {repository: $repository, id: $source})
                -[:DEPENDS_ON*1..$cutoff]->
                (target:Symbol {repository: $repository, id: $target})
                RETURN [n in nodes(p) | n.id] as path
                ORDER BY length(p)
                """,
                repository=repository,
                source=source,
                target=target,
                cutoff=cutoff,
            )
            return [list(row["path"]) for row in rows]

    def query_shortest_path(self, repository: str, source: str, target: str, cutoff: int = 5) -> list[str]:
        driver = self._connect()
        with driver.session(database="neo4j") as session:
            row = session.run(
                """
                MATCH p = shortestPath((source:Symbol {repository: $repository, id: $source})
                -[:DEPENDS_ON*1..$cutoff]->(target:Symbol {repository: $repository, id: $target}))
                RETURN [n in nodes(p) | n.id] as path
                """,
                repository=repository,
                source=source,
                target=target,
                cutoff=cutoff,
            ).single()
            return list(row["path"]) if row else []

    def query_call_chain(self, repository: str, source: str, target: str, cutoff: int = 5) -> list[list[str]]:
        return self.query_paths(repository, source, target, cutoff=cutoff)

    def query_neighbors(self, repository: str, node_id: str) -> list[dict[str, Any]]:
        driver = self._connect()
        with driver.session(database="neo4j") as session:
            rows = session.run(
                """
                MATCH (node:Symbol {repository: $repository, id: $node_id})
                OPTIONAL MATCH (node)-[r]->(neighbor)
                RETURN neighbor.id AS id, type(r) AS relationship, neighbor.repository AS repository
                """,
                repository=repository,
                node_id=node_id,
            )
            return [dict(row) for row in rows]


def build_graph_store() -> GraphStore:
    uri = os.getenv("NEO4J_URI")
    password = os.getenv("NEO4J_PASSWORD")
    if uri and password:
        return Neo4jGraphStore(uri=uri, user=os.getenv("NEO4J_USER", "neo4j"), password=password)
    return NullGraphStore()
