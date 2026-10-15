"""End-to-End Test Suite for Codebase Intelligence.

Runs all core queries, static analysis pipelines, and developer use cases
end-to-end, validating results against real code and generating a comprehensive
markdown execution report.

Can be run via:
    pytest tests/test_end_to_end.py
or directly as a standalone script:
    python tests/test_end_to_end.py
"""

import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path for direct script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from core.models import AnalysisFinding
from services.analysis_service import AnalysisService


@dataclass
class UseCaseResult:
    name: str
    category: str
    status: str  # PASS / FAIL
    duration_ms: float
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class E2ETestRunner:
    """Orchestrates all end-to-end use cases and generates a structured report."""

    def __init__(self, workspace_dir: Path):
        self.workspace = workspace_dir
        self.repo_dir = self.workspace / "sample_project"
        self.db_path = self.workspace / "e2e_index.db"
        self.results: list[UseCaseResult] = []
        self.start_time: float = 0.0
        self.end_time: float = 0.0

    def setup_sample_repository(self) -> Path:
        """Creates a realistic multi-module Python repository with dependencies, tests, and dead code."""
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        (self.repo_dir / "tests").mkdir(exist_ok=True)

        # 1. Base Tax Module
        (self.repo_dir / "tax.py").write_text(
            '''"""Tax computation module."""

def calculate_vat(amount: float) -> float:
    """Calculates VAT at 20%."""
    return round(amount * 0.20, 2)

def calculate_discount(amount: float, rate: float = 0.05) -> float:
    """Calculates promotional discount."""
    return round(amount * rate, 2)
''',
            encoding="utf-8",
        )

        # 2. Billing Module (depends on tax.py)
        (self.repo_dir / "billing.py").write_text(
            '''"""Billing service module."""
from tax import calculate_vat, calculate_discount

def prepare_invoice(base_amount: float) -> dict[str, float]:
    """Prepares an invoice with tax and discount applied."""
    tax = calculate_vat(base_amount)
    discount = calculate_discount(base_amount)
    total = base_amount + tax - discount
    return {"base": base_amount, "tax": tax, "discount": discount, "total": total}
''',
            encoding="utf-8",
        )

        # 3. Order Processing Module (depends on billing.py)
        (self.repo_dir / "orders.py").write_text(
            '''"""Order management module."""
from billing import prepare_invoice

class OrderService:
    """High-level order orchestrator."""
    def __init__(self, currency: str = "USD"):
        self.currency = currency

    def place_order(self, amount: float) -> dict:
        """Processes order checkout."""
        invoice = prepare_invoice(amount)
        return {"status": "confirmed", "currency": self.currency, "invoice": invoice}
''',
            encoding="utf-8",
        )

        # 4. Utilities Module (contains dead code / unreferenced function)
        (self.repo_dir / "utils.py").write_text(
            '''"""General utilities."""
import os

def get_platform_info() -> str:
    """Active utility."""
    return os.name

def orphaned_dead_function():
    """Unused function with 0 incoming calls or imports."""
    return "This should be flagged as dead code."
''',
            encoding="utf-8",
        )

        # 5. Unit Tests Module (matches billing functions)
        (self.repo_dir / "tests" / "test_billing.py").write_text(
            '''"""Unit tests for billing."""
from billing import prepare_invoice

def test_prepare_invoice():
    invoice = prepare_invoice(100.0)
    assert invoice["total"] > 0
''',
            encoding="utf-8",
        )

        return self.repo_dir

    def run_use_case(self, name: str, category: str, func, *args, **kwargs) -> Any:
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            duration = (time.perf_counter() - start) * 1000
            self.results.append(
                UseCaseResult(
                    name=name,
                    category=category,
                    status="PASS",
                    duration_ms=round(duration, 2),
                    summary=result.get("_summary", "Completed successfully"),
                    details={k: v for k, v in result.items() if k != "_summary"},
                )
            )
            return result
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            self.results.append(
                UseCaseResult(
                    name=name,
                    category=category,
                    status="FAIL",
                    duration_ms=round(duration, 2),
                    summary=f"Failed: {exc}",
                    error=str(exc),
                )
            )
            raise

    def run_all(self) -> str:
        """Executes all queries and use cases end-to-end and returns the markdown report."""
        self.start_time = time.perf_counter()
        self.setup_sample_repository()

        service = AnalysisService(self.db_path)
        repo_root = self.repo_dir

        try:
            # ---------------------------------------------------------
            # USE CASE 1: Clean Repository Indexing
            # ---------------------------------------------------------
            def uc_index_clean():
                res = service.index_local_repository(repo_root)
                assert res["updated"] is True
                assert res["files_indexed"] >= 5
                assert res["symbols_indexed"] >= 6
                assert res["graph_edges"] >= 5
                return {
                    "_summary": f"Indexed {res['files_indexed']} files, {res['symbols_indexed']} symbols, {res['graph_edges']} edges",
                    "files_indexed": res["files_indexed"],
                    "symbols_indexed": res["symbols_indexed"],
                    "graph_nodes": res["graph_nodes"],
                    "graph_edges": res["graph_edges"],
                }

            self.run_use_case("1. Clean Repository Indexing", "Indexing", uc_index_clean)

            # ---------------------------------------------------------
            # USE CASE 2: Incremental Indexing (Hash Caching)
            # ---------------------------------------------------------
            def uc_index_cached():
                # Second run with no file modifications
                res1 = service.index_local_repository(repo_root)
                assert res1["updated"] is False
                assert res1["changed_files"] == []

                # Now modify a single file
                tax_file = repo_root / "tax.py"
                tax_file.write_text(tax_file.read_text(encoding="utf-8") + "\n# Modified comment\n", encoding="utf-8")
                res2 = service.index_local_repository(repo_root)
                assert res2["updated"] is True
                assert "tax.py" in res2["changed_files"]

                return {
                    "_summary": "Zero changes detected on unchanged run; exact modified file detected on edit",
                    "unchanged_run_updated": res1["updated"],
                    "modified_run_changed_files": res2["changed_files"],
                }

            self.run_use_case("2. Incremental Indexing & Hash Cache", "Indexing", uc_index_cached)

            # ---------------------------------------------------------
            # USE CASE 3: Symbol Search & Navigation Query
            # ---------------------------------------------------------
            def uc_symbol_search():
                matches = service.find_symbol(repo_root, query="vat")
                assert len(matches) >= 1
                vat_symbol = matches[0]
                assert vat_symbol["name"] == "calculate_vat"
                assert vat_symbol["kind"] == "function"

                # Inspect details, callers, and dependencies
                details = service.symbol_details(repo_root, vat_symbol["id"])
                assert details["symbol"]["id"] == vat_symbol["id"]
                assert any("billing:prepare_invoice" in caller["source_id"] for caller in details["callers"])

                return {
                    "_summary": f"Found symbol '{vat_symbol['id']}' with {len(details['callers'])} incoming caller(s)",
                    "symbol_id": vat_symbol["id"],
                    "kind": vat_symbol["kind"],
                    "signature": vat_symbol["signature"],
                    "callers": [c["source_id"] for c in details["callers"]],
                }

            self.run_use_case("3. Symbol Search & Detail Navigation", "Navigation", uc_symbol_search)

            # ---------------------------------------------------------
            # USE CASE 4: Graph Path & Call-Chain Traversal
            # ---------------------------------------------------------
            def uc_graph_paths():
                # Trace path from OrderService.place_order -> calculate_vat
                source = "orders:OrderService.place_order"
                target = "tax:calculate_vat"
                path_info = service.graph_paths(repo_root, source=source, target=target, cutoff=5)
                
                paths = path_info.get("paths", [])
                shortest = path_info.get("shortest_path", [])
                
                assert len(paths) >= 1
                assert shortest[0] == source
                assert shortest[-1] == target

                # Test neighbor queries
                neighbor_info = service.graph_neighbors(repo_root, "billing:prepare_invoice")
                neighbor_ids = [n["id"] for n in neighbor_info.get("neighbors", [])]

                return {
                    "_summary": f"Discovered call chain from '{source}' to '{target}' (length {len(shortest)})",
                    "source": source,
                    "target": target,
                    "shortest_path": shortest,
                    "neighbors_of_billing": neighbor_ids,
                }

            self.run_use_case("4. Graph Path & Call-Chain Query", "Graph Traversal", uc_graph_paths)

            # ---------------------------------------------------------
            # USE CASE 5: Impact Analysis (Reverse Blast Radius)
            # ---------------------------------------------------------
            def uc_impact_analysis():
                # If calculate_vat changes, what is impacted?
                changed = ["tax:calculate_vat"]
                impact = service.impact.analyze_change(repo_root.as_posix(), changed)

                impacted = impact["impacted_symbols"]
                # Must reach prepare_invoice and OrderService.place_order
                assert any("billing:prepare_invoice" in s for s in impacted)
                assert any("orders:OrderService.place_order" in s for s in impacted)

                return {
                    "_summary": f"Calculated blast radius: {len(impacted)} symbols impacted across {len(impact.get('impact_paths', []))} path(s)",
                    "changed_symbol": changed[0],
                    "impacted_symbols": impacted,
                    "impact_paths": impact.get("impact_paths", []),
                }

            self.run_use_case("5. Multi-Hop Impact Analysis", "Impact Analysis", uc_impact_analysis)

            # ---------------------------------------------------------
            # USE CASE 6: Test Selection & Recommendation
            # ---------------------------------------------------------
            def uc_test_selection():
                # If calculate_vat changes, recommend tests that verify it
                changed = ["tax:calculate_vat"]
                rec = service.test_selection.recommend_tests(
                    repository=repo_root.as_posix(),
                    repo_root=repo_root,
                    changed_symbols=changed,
                )

                recommended = rec.get("recommended_tests", [])
                assert len(recommended) >= 1
                assert any("test_billing.py" in t["file"] for t in recommended)

                return {
                    "_summary": f"Recommended {len(recommended)} relevant test case(s) for changed symbol",
                    "changed_symbols": changed,
                    "recommended_test_files": [t["file"] for t in recommended],
                    "recommended_test_names": [t["name"] for t in recommended],
                }

            self.run_use_case("6. Impact-Driven Test Selection", "Test Selection", uc_test_selection)

            # ---------------------------------------------------------
            # USE CASE 7: Dead Code Detection
            # ---------------------------------------------------------
            def uc_dead_code():
                findings = service.detect_dead_code(repo_root)
                finding_list = findings.get("findings", [])
                
                # Check that orphaned_dead_function is flagged
                dead_symbol_ids = [
                    f["evidence"].get("symbol_id", "")
                    for f in finding_list
                ]
                assert any("orphaned_dead_function" in s for s in dead_symbol_ids)

                return {
                    "_summary": f"Detected {len(finding_list)} unreferenced symbol finding(s); successfully flagged orphaned_dead_function",
                    "total_findings": len(finding_list),
                    "flagged_symbols": dead_symbol_ids,
                }

            self.run_use_case("7. Dead Code Detection", "Quality & Hygiene", uc_dead_code)

            # ---------------------------------------------------------
            # USE CASE 8: Change Risk Scoring
            # ---------------------------------------------------------
            def uc_risk_analysis():
                assessment = service.analyze_change(
                    repo_root=repo_root,
                    changed_symbols=["tax:calculate_vat"],
                )

                risk = assessment.get("risk", {})
                assert "risk_score" in risk
                assert "risk_level" in risk  # LOW, MEDIUM, HIGH

                return {
                    "_summary": f"Risk assessment: score {risk.get('risk_score')}/100, level: {risk.get('risk_level')}",
                    "risk_score": risk.get("risk_score"),
                    "risk_level": risk.get("risk_level"),
                    "factors": risk.get("factors", {}),
                }

            self.run_use_case("8. Change Risk Scoring", "Risk Assessment", uc_risk_analysis)

        finally:
            service.close()
            self.end_time = time.perf_counter()

        return self.generate_report()

    def generate_report(self) -> str:
        """Renders the execution results into an exhaustive GitHub Markdown report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.status == "PASS")
        failed_tests = total_tests - passed_tests
        total_duration = round((self.end_time - self.start_time) * 1000, 2)

        report_lines = [
            "# 🧪 Codebase Intelligence — End-to-End Test Execution Report",
            "",
            f"**Execution Timestamp:** `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`  ",
            f"**Total Suite Duration:** `{total_duration} ms`  ",
            f"**Overall Status:** `{'✅ ALL PASSED' if failed_tests == 0 else '❌ FAILURES DETECTED'}`",
            "",
            "---",
            "",
            "## 📊 Executive Summary",
            "",
            "| Total Use Cases | Passed | Failed | Pass Rate | Total Duration |",
            "| :---: | :---: | :---: | :---: | :---: |",
            f"| **{total_tests}** | **{passed_tests}** | **{failed_tests}** | **{(passed_tests/total_tests)*100:.1f}%** | **{total_duration} ms** |",
            "",
            "---",
            "",
            "## 📋 Detailed Use Case Results",
            "",
            "| # | Use Case Name | Category | Status | Duration | Summary |",
            "| :--- | :--- | :--- | :---: | :---: | :--- |",
        ]

        for idx, res in enumerate(self.results, 1):
            badge = "✅ PASS" if res.status == "PASS" else "❌ FAIL"
            report_lines.append(
                f"| {idx} | **{res.name}** | `{res.category}` | {badge} | `{res.duration_ms} ms` | {res.summary} |"
            )

        report_lines.extend([
            "",
            "---",
            "",
            "## 🔍 Deep Dive by Query & Use Case",
            "",
        ])

        for res in self.results:
            report_lines.extend([
                f"### {res.name}",
                f"- **Category:** `{res.category}`",
                f"- **Status:** `{'PASS' if res.status == 'PASS' else 'FAIL'}`",
                f"- **Execution Time:** `{res.duration_ms} ms`",
                f"- **Summary:** {res.summary}",
                "",
                "```json",
                json.dumps(res.details, indent=2),
                "```",
                "",
            ])

        report_content = "\n".join(report_lines)

        # Persist report to reports directory in the project
        report_dir = Path("reports")
        report_dir.mkdir(exist_ok=True)
        report_path = report_dir / "e2e_test_report.md"
        report_path.write_text(report_content, encoding="utf-8")

        return report_content


# ---------------------------------------------------------------------------
# Pytest Test Hook
# ---------------------------------------------------------------------------
def test_all_queries_and_use_cases_end_to_end(tmp_path: Path):
    """Pytest entrypoint that executes the full end-to-end test suite."""
    runner = E2ETestRunner(tmp_path)
    report = runner.run_all()

    # Assert 100% pass rate
    assert all(r.status == "PASS" for r in runner.results)
    assert len(runner.results) == 8


# ---------------------------------------------------------------------------
# Standalone CLI Entrypoint (python tests/test_end_to_end.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import tempfile

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    with tempfile.TemporaryDirectory() as temp_dir:
        print("\n[*] Running Codebase Intelligence End-to-End Test Suite...\n")
        runner = E2ETestRunner(Path(temp_dir))
        report_text = runner.run_all()

        print("=" * 80)
        print("[SUCCESS] E2E TEST SUITE EXECUTION COMPLETE!")
        print(f"Report written to: {Path('reports/e2e_test_report.md').resolve()}")
        print("=" * 80)
        for r in runner.results:
            print(f"[{r.status}] {r.name:42} ({r.duration_ms:6.2f} ms) - {r.summary}")
        print("=" * 80)
