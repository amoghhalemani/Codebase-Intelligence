from typing import Any

from core.models import AnalysisFinding
from storage.database import AnalysisDatabase


class DeadCodeService:
    def __init__(self, database: AnalysisDatabase):
        self.database = database

    @staticmethod
    def _is_framework_visitor(symbol: dict[str, Any]) -> bool:
        name = str(symbol.get("name", ""))
        qualified_name = str(symbol.get("qualified_name", ""))

        if name.startswith("visit_") or name == "generic_visit":
            return True

        if name.endswith("Visitor"):
            return True

        if qualified_name.startswith("visit_") or ".visit_" in qualified_name:
            return True

        return False

    def detect(self, repository: str) -> dict[str, Any]:
        symbols = self.database.all_symbols(repository)
        edges = self.database.all_edges(repository)
        references = self.database.all_references(repository)

        referenced_targets = {
            edge["target_id"]
            for edge in edges
            if edge["relationship"] in {"call", "attribute", "import"}
        }

        referenced_targets.update(
            row["target_symbol_id"]
            for row in references
            if row["target_symbol_id"]
        )

        entry_points = {
            symbol["id"]
            for symbol in symbols
            if symbol["name"].startswith("test_")
            or symbol["name"] in {"main", "cli", "app"}
        }

        findings: list[AnalysisFinding] = []

        for symbol in symbols:
            if symbol["kind"] not in {"function", "async_function", "class"}:
                continue

            if symbol["id"] in referenced_targets or symbol["id"] in entry_points:
                continue

            if symbol["name"].startswith("__"):
                continue

            if self._is_framework_visitor(symbol):
                continue

            findings.append(
                AnalysisFinding(
                    rule="potentially-unreferenced-symbol",
                    location=f"{symbol['file']}:{symbol['start_line']}",
                    explanation=(
                        f"{symbol['kind']} '{symbol['qualified_name']}' has no "
                        "resolved incoming reference in the static index."
                    ),
                    evidence={
                        "symbol_id": symbol["id"],
                        "module": symbol["module"],
                        "kind": symbol["kind"],
                    },
                    confidence=0.65,
                    limitations=[
                        "Dynamic calls, framework registration, decorators, "
                        "exports, and external entry points can create false positives."
                    ],
                )
            )

        unused_imports = self._unused_imports(repository, symbols, references)

        findings.extend(unused_imports)

        self.database.save_findings(repository, findings)

        return {
            "finding_count": len(findings),
            "findings": [finding.__dict__ for finding in findings],
        }

    @staticmethod
    def _unused_imports(
        repository: str,
        symbols: list[dict[str, Any]],
        references: list[dict[str, Any]],
    ) -> list[AnalysisFinding]:
        used_names = {
            row["target_name"].split(".")[0]
            for row in references
            if row["reference_type"] in {"call", "attribute"}
        }

        findings: list[AnalysisFinding] = []

        for row in references:
            if row["reference_type"] != "import":
                continue

            local_name = row["target_name"].split(".")[-1]

            if local_name in used_names:
                continue

            findings.append(
                AnalysisFinding(
                    rule="unused-import",
                    location=f"{row['file']}:{row['line']}",
                    explanation=f"Import '{row['target_name']}' appears unused.",
                    evidence={
                        "import": row["target_name"],
                        "source_symbol": row["source_symbol_id"],
                    },
                    confidence=0.75,
                    limitations=[
                        "Re-exports, `__all__`, type-only usage, and dynamic "
                        "imports may be missed."
                    ],
                )
            )

        return findings
