from collections import deque
from typing import Any, Optional

import networkx as nx

from core.models import DependencyEdge, ParsedFile


class DependencyGraph:
    """Directed graph of modules and symbols."""

    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def build_from_parsed_files(self, parsed_files: list[ParsedFile]) -> None:
        for parsed in parsed_files:
            module_node = f"{parsed.module_id}:<module>"
            self.graph.add_node(
                module_node,
                node_type="module",
                file=parsed.path,
                module=parsed.module_id,
            )

            for symbol in parsed.symbols:
                self.graph.add_node(
                    symbol.id,
                    node_type=symbol.kind,
                    file=symbol.file,
                    module=symbol.module,
                    name=symbol.name,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                )
                self.add_edge(
                    module_node,
                    symbol.id,
                    "defines",
                    {"file": parsed.path},
                )

            for imported in parsed.imports:
                self.add_edge(
                    module_node,
                    f"{imported.imported_path}:<module>",
                    "imports",
                    {
                        "file": parsed.path,
                        "line": imported.line,
                        "local_name": imported.local_name,
                    },
                    confidence=0.8,
                )

            for reference in parsed.references:
                if reference.target_symbol_id:
                    self.add_edge(
                        reference.source_symbol_id,
                        reference.target_symbol_id,
                        reference.reference_type,
                        {
                            "file": reference.file,
                            "line": reference.line,
                        },
                    )

    def add_edge(
        self,
        source: str,
        target: str,
        relationship: str,
        evidence: Optional[dict[str, Any]] = None,
        confidence: float = 1.0,
    ) -> None:
        self.graph.add_node(source)
        self.graph.add_node(target)

        if self.graph.has_edge(source, target):
            existing = self.graph[source][target]

            if relationship not in existing.get("relationships", ""):
                existing["relationships"] = (
                    f"{existing.get('relationships', relationship)},{relationship}"
                )

            existing.setdefault("evidence", []).append(evidence or {})
            existing["confidence"] = max(existing.get("confidence", 0), confidence)
        else:
            self.graph.add_edge(
                source,
                target,
                relationships=relationship,
                evidence=[evidence or {}],
                confidence=confidence,
            )

    def dependencies(self, node_id: str) -> list[str]:
        return list(self.graph.successors(node_id))

    def dependents(self, node_id: str) -> list[str]:
        return list(self.graph.predecessors(node_id))

    def impacted_nodes(self, changed_nodes: list[str], max_depth: int = 10) -> set[str]:
        impacted: set[str] = set()

        for changed_node in changed_nodes:
            if changed_node not in self.graph:
                continue

            queue = deque([(changed_node, 0)])

            while queue:
                current, depth = queue.popleft()

                if current in impacted:
                    continue

                impacted.add(current)

                if depth >= max_depth:
                    continue

                for dependent in self.graph.predecessors(current):
                    queue.append((dependent, depth + 1))

        impacted.difference_update(changed_nodes)
        return impacted

    def dependency_paths(
        self,
        source: str,
        target: str,
        cutoff: int = 5,
    ) -> list[list[str]]:
        if source not in self.graph or target not in self.graph:
            return []

        return list(nx.all_simple_paths(self.graph, source, target, cutoff=cutoff))

    def shortest_path(
        self,
        source: str,
        target: str,
        cutoff: Optional[int] = None,
    ) -> list[str]:
        if source not in self.graph or target not in self.graph:
            return []

        try:
            _ = cutoff
            return nx.shortest_path(self.graph, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def find_paths(
        self,
        source: str,
        target: str,
        cutoff: int = 5,
    ) -> list[list[str]]:
        return self.dependency_paths(source, target, cutoff=cutoff)

    def call_chain(
        self,
        source: str,
        target: str,
        cutoff: int = 5,
    ) -> list[list[str]]:
        return self.find_paths(source, target, cutoff=cutoff)

    def to_dependency_edges(self) -> list[DependencyEdge]:
        edges: list[DependencyEdge] = []

        for source, target, data in self.graph.edges(data=True):
            edges.append(
                DependencyEdge(
                    source_id=source,
                    target_id=target,
                    relationship=data.get("relationships", "depends_on"),
                    evidence={"raw": data.get("evidence", [])},
                    confidence=data.get("confidence", 1.0),
                )
            )

        return edges
