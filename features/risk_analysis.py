from typing import Any

from core.graph import DependencyGraph
from storage.database import AnalysisDatabase


class RiskAnalysisService:
    def __init__(self, database: AnalysisDatabase):
        self.database = database

    def assess_change(
        self,
        repository: str,
        changed_symbols: list[str],
        co_changed_files: list[str],
    ) -> dict[str, Any]:
        graph = self._load_graph(repository)
        impacted = graph.impacted_nodes(changed_symbols)

        dependency_risk = min(len(impacted) / 20.0, 1.0)
        co_change_risk = min(len(co_changed_files) / 10.0, 1.0)
        unresolved_reference_count = sum(
            1
            for row in self.database.all_references(repository)
            if row["resolution_status"] == "unresolved"
        )
        resolution_risk = min(unresolved_reference_count / 500.0, 1.0)

        risk_score = (
            dependency_risk * 0.5
            + co_change_risk * 0.3
            + resolution_risk * 0.2
        )

        return {
            "risk_score": round(risk_score, 3),
            "risk_level": self._risk_level(risk_score),
            "signals": {
                "impacted_symbol_count": len(impacted),
                "dependency_risk": round(dependency_risk, 3),
                "co_changed_files": co_changed_files,
                "co_change_risk": round(co_change_risk, 3),
                "unresolved_reference_count": unresolved_reference_count,
                "resolution_risk": round(resolution_risk, 3),
            },
            "limitations": [
                "This is a heuristic score, not a defect prediction.",
                "Git co-change frequency and test coverage should be added for "
                "more reliable risk estimation.",
            ],
        }

    @staticmethod
    def _risk_level(score: float) -> str:
        if score >= 0.7:
            return "high"

        if score >= 0.4:
            return "medium"

        return "low"

    def _load_graph(self, repository: str) -> DependencyGraph:
        graph = DependencyGraph()

        for edge in self.database.all_edges(repository):
            graph.add_edge(
                edge["source_id"],
                edge["target_id"],
                edge["relationship"],
                edge["evidence"],
                edge["confidence"],
            )

        return graph
