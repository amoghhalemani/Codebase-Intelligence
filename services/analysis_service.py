from pathlib import Path
from typing import Any, Optional

from core.indexing import RepositoryIndexer
from features.dead_code import DeadCodeService
from features.impact_analysis import ImpactAnalysisService
from features.navigation import NavigationService
from features.risk_analysis import RiskAnalysisService
from features.test_selection import TestSelectionService
from git_analysis.history import GitHistoryAnalyzer
from storage.database import AnalysisDatabase


class AnalysisService:
    """Shared service layer for CLI and API."""

    def __init__(self, database_path: Path):
        self.database = AnalysisDatabase(database_path)
        self.indexer = RepositoryIndexer(self.database)
        self.navigation = NavigationService(self.database)
        self.impact = ImpactAnalysisService(self.database)
        self.test_selection = TestSelectionService(self.database)
        self.dead_code = DeadCodeService(self.database)
        self.risk = RiskAnalysisService(self.database)

    def _load_graph(self, repository: str) -> Any:
        from core.graph import DependencyGraph

        graph = DependencyGraph()

        for edge in self.database.all_edges(repository):
            evidence = edge["evidence"]
            if isinstance(evidence, str):
                import json

                evidence = json.loads(evidence)

            graph.add_edge(
                edge["source_id"],
                edge["target_id"],
                edge["relationship"],
                evidence,
                edge["confidence"],
            )

        return graph

    def graph_paths(
        self,
        repo_root: Path,
        source: str,
        target: str,
        cutoff: int = 5,
    ) -> dict[str, Any]:
        repository = Path(repo_root).resolve().as_posix()
        graph_store = self.indexer.graph_store
        paths = graph_store.query_paths(repository, source, target, cutoff=cutoff)

        if not paths:
            graph = self._load_graph(repository)
            paths = graph.find_paths(source, target, cutoff=cutoff)

        return {
            "repository": repository,
            "source": source,
            "target": target,
            "cutoff": cutoff,
            "paths": paths,
            "shortest_path": (paths[0] if paths else []),
        }

    def graph_call_chain(
        self,
        repo_root: Path,
        source: str,
        target: str,
        cutoff: int = 5,
    ) -> dict[str, Any]:
        return self.graph_paths(repo_root, source, target, cutoff=cutoff)

    def graph_neighbors(self, repo_root: Path, node_id: str) -> dict[str, Any]:
        repository = Path(repo_root).resolve().as_posix()
        graph_store = self.indexer.graph_store
        neighbors = graph_store.query_neighbors(repository, node_id)

        if not neighbors:
            graph = self._load_graph(repository)
            neighbors = [
                {"id": neighbor, "relationship": "depends_on", "repository": repository}
                for neighbor in graph.dependencies(node_id)
            ]

        return {
            "repository": repository,
            "node_id": node_id,
            "neighbors": neighbors,
        }

    def clone_and_index(
        self,
        repository_url: str,
        destination: Path,
        branch: Optional[str] = None,
    ) -> dict[str, Any]:
        repo_root = GitHistoryAnalyzer.clone_repository(
            repository_url,
            destination,
            branch,
        )
        index_result = self.indexer.index_repository(repo_root)
        return {"repository_path": repo_root.as_posix(), **index_result}

    def index_local_repository(self, repo_root: Path) -> dict[str, Any]:
        return self.indexer.index_repository(Path(repo_root).resolve())

    def analyze_change(
        self,
        repo_root: Path,
        changed_symbols: list[str],
        base_revision: Optional[str] = None,
    ) -> dict[str, Any]:
        repo_root = Path(repo_root).resolve()
        repository = repo_root.as_posix()

        git = GitHistoryAnalyzer(repo_root)
        changed_files = git.changed_files(base_revision=base_revision)
        co_changed_files: list[str] = []

        if git.repo is not None:
            for changed_file in changed_files:
                co_changed_files.extend(git.co_changed_files(changed_file))

        impact = self.impact.analyze_change(repository, changed_symbols)
        tests = self.test_selection.recommend_tests(
            repository,
            repo_root,
            changed_symbols,
        )
        risk = self.risk.assess_change(
            repository,
            changed_symbols,
            sorted(set(co_changed_files)),
        )

        return {
            "repository": repository,
            "revision": git.current_revision(),
            "git_available": git.repo is not None,
            "changed_files": changed_files,
            "impact": impact,
            "recommended_tests": tests,
            "risk": risk,
        }

    def find_symbol(self, repo_root: Path, query: str) -> list[dict[str, Any]]:
        repository = Path(repo_root).resolve().as_posix()
        return self.navigation.find_definitions(repository, query)

    def symbol_details(self, repo_root: Path, symbol_id: str) -> dict[str, Any]:
        repository = Path(repo_root).resolve().as_posix()
        return self.navigation.get_symbol_details(repository, symbol_id)

    def detect_dead_code(self, repo_root: Path) -> dict[str, Any]:
        repository = Path(repo_root).resolve().as_posix()
        return self.dead_code.detect(repository)

    def visualize(self, repo_root: Path, output_path: Optional[Path] = None) -> Path:
        from features.visualization import GraphVisualizer

        repository = Path(repo_root).resolve().as_posix()
        repo_name = Path(repo_root).name or "repository"
        target_path = output_path or (Path(".codebase-intelligence") / "visualizations" / f"{repo_name}_graph.html")
        visualizer = GraphVisualizer(self.database, repository)
        return visualizer.render_to_file(target_path)

    def close(self) -> None:
        self.database.close()
