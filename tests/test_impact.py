from core.graph import DependencyGraph
from core.models import DependencyEdge
from features.impact_analysis import ImpactAnalysisService
from services.analysis_service import AnalysisService


def test_impact_analysis_finds_dependents():
    graph = DependencyGraph()
    graph.add_edge("app:main", "billing:calculate_tax", "call")

    database = type("DummyDatabase", (), {"all_edges": lambda self, repository: [{
        "source_id": "app:main",
        "target_id": "billing:calculate_tax",
        "relationship": "call",
        "evidence": {},
        "confidence": 1.0,
    }]})()
    service = ImpactAnalysisService(database)
    result = service.analyze_change("test", ["billing:calculate_tax"])

    assert "app:main" in result["impacted_symbols"]


def test_analysis_service_handles_non_git_repository(tmp_path):
    service = AnalysisService(tmp_path / "index.db")
    repo_root = tmp_path / "plain-repo"
    repo_root.mkdir()
    service.database.save_graph_edges(
        repo_root.as_posix(),
        [
            DependencyEdge(
                source_id="app:main",
                target_id="billing:calculate_tax",
                relationship="call",
                confidence=1.0,
            )
        ],
    )

    result = service.analyze_change(repo_root, ["billing:calculate_tax"])

    assert result["repository"] == repo_root.as_posix()
    assert result["revision"] is None
    assert result["git_available"] is False
    assert "app:main" in result["impact"]["impacted_symbols"]
    service.close()
