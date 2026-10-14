from typing import Any

from core.graph import DependencyGraph
from storage.database import AnalysisDatabase


class ImpactAnalysisService:
    def __init__(self, database: AnalysisDatabase):
        self.database = database

    def analyze_change(
        self,
        repository: str,
        changed_symbols: list[str],
        max_depth: int = 10,
    ) -> dict[str, Any]:
        graph = self._load_graph(repository)
        impacted = graph.impacted_nodes(changed_symbols, max_depth=max_depth)

        paths: dict[str, list[list[str]]] = {}

        for symbol in changed_symbols:
            paths[symbol] = []

            for affected in impacted:
                candidate_paths = graph.dependency_paths(affected, symbol, cutoff=max_depth)

                if candidate_paths:
                    paths[symbol].extend(candidate_paths[:3])

        return {
            "changed_symbols": changed_symbols,
            "impacted_symbols": sorted(impacted),
            "impact_count": len(impacted),
            "dependency_paths": paths,
            "limitations": [
                "Dynamic dispatch, reflection, string-based imports, and "
                "unresolved references may be missed.",
                "Impact follows static dependency edges; runtime behavior can differ.",
            ],
        }

    def _load_graph(self, repository: str) -> DependencyGraph:
        graph = DependencyGraph()

        for edge in self.database.all_edges(repository):
            graph.add_edge(
                edge["source_id"],
                edge["target_id"],
                edge["relationship"],
                json.loads(edge["evidence"]) if isinstance(edge["evidence"], str) else edge["evidence"],
                edge["confidence"],
            )

        return graph


import json  # noqa: E402
