import re
from pathlib import Path
from typing import Any

from analyzers.base import BaseAnalyzer
from core.graph import DependencyGraph
from core.models import TestCase
from storage.database import AnalysisDatabase


class TestSelectionService:
    __test__ = False

    def __init__(self, database: AnalysisDatabase):
        self.database = database

    def discover_tests(self, repo_root: Path, repository: str | None = None) -> list[TestCase]:
        tests: list[TestCase] = []

        for path in sorted(BaseAnalyzer.iter_files(repo_root)):
            if not path.name.startswith("test_") or not path.name.endswith(".py"):
                continue
            relative_path = path.relative_to(repo_root).as_posix()
            content = path.read_text(encoding="utf-8", errors="replace")

            for match in re.finditer(r"^(?:async\s+)?def\s+(test_[A-Za-z0-9_]+)", content, re.MULTILINE):
                test_name = match.group(1)
                line = content[: match.start()].count("\n") + 1

                tests.append(
                    TestCase(
                        test_id=f"{relative_path}:{test_name}",
                        file=relative_path,
                        name=test_name,
                        associated_symbols=self._symbols_in_file(relative_path, repository),
                    )
                )

        return tests

    def recommend_tests(
        self,
        repository: str,
        repo_root: Path,
        changed_symbols: list[str],
        max_tests: int = 20,
    ) -> dict[str, Any]:
        tests = self.discover_tests(repo_root, repository=repository)
        graph = self._load_graph(repository)
        impacted = graph.impacted_nodes(changed_symbols)
        candidate_set = set(changed_symbols) | impacted

        scored: list[dict[str, Any]] = []

        for test in tests:
            score = 0.0
            reasons: list[str] = []

            if test.file in {symbol.split(":", 1)[0] for symbol in changed_symbols}:
                score += 5.0
                reasons.append("Test file is directly changed")

            for associated in test.associated_symbols:
                if associated in candidate_set:
                    score += 3.0
                    reasons.append(f"Associated symbol affected: {associated}")

            if test.test_id in candidate_set:
                score += 4.0
                reasons.append(f"Test symbol directly impacted in dependency graph")

            for changed_symbol in changed_symbols:
                if self._shares_module(test, changed_symbol):
                    score += 1.0
                    reasons.append(f"Shares module with {changed_symbol}")

            if score > 0:
                scored.append(
                    {
                        "test_id": test.test_id,
                        "file": test.file,
                        "name": test.name,
                        "score": score,
                        "reasons": reasons,
                    }
                )

        scored.sort(key=lambda item: (-item["score"], item["test_id"]))

        return {
            "changed_symbols": changed_symbols,
            "recommended_tests": scored[:max_tests],
            "total_candidates": len(tests),
            "limitations": [
                "Test selection currently uses naming, file/module overlap, and "
                "static dependency relationships.",
                "Coverage data is not yet integrated; add coverage.py output for "
                "stronger recommendations.",
            ],
        }

    def _symbols_in_file(self, file_path: str, repository: str | None = None) -> list[str]:
        if not hasattr(self, "database") or self.database is None:
            return []

        all_syms = self.database.all_symbols(repository) if repository else self.database.all_symbols("current")
        return [
            row["id"]
            for row in all_syms
            if row["file"] == file_path
        ]

    @staticmethod
    def _shares_module(test: TestCase, symbol_id: str) -> bool:
        module = symbol_id.rsplit(":", 1)[0]
        return test.file.replace("/", ".").removesuffix(".py") == module

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
