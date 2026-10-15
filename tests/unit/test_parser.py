from pathlib import Path

from analyzers.python.parser import PythonAnalyzer
from core.indexing import RepositoryIndexer
from core.resolver import SymbolResolver
from storage.database import AnalysisDatabase


def test_python_parser_extracts_symbols_imports_and_calls(tmp_path: Path):
    source = tmp_path / "billing.py"
    source.write_text(
        """
import json

def calculate_tax(amount):
    return amount * 0.18

def format_invoice(amount):
    return json.dumps({"tax": calculate_tax(amount)})
""",
        encoding="utf-8",
    )

    parsed = PythonAnalyzer().parse_file(source, tmp_path)

    assert parsed.module_id == "billing"
    assert any(symbol.name == "calculate_tax" for symbol in parsed.symbols)
    assert any(imported.imported_path == "json" for imported in parsed.imports)
    assert any(
        reference.target_name == "calculate_tax"
        for reference in parsed.references
        if reference.reference_type == "call"
    )


def test_symbol_resolver_resolves_self_and_cls_methods(tmp_path: Path):
    source = tmp_path / "service.py"
    source.write_text(
        """
class Calculator:
    def total(self, amount):
        return self._double(amount)

    @classmethod
    def build(cls, amount):
        return cls._normalize(amount)

    def _double(self, amount):
        return amount * 2

    @classmethod
    def _normalize(cls, amount):
        return amount + 1
""",
        encoding="utf-8",
    )

    parsed = PythonAnalyzer().parse_file(source, tmp_path)
    resolved = SymbolResolver([parsed], tmp_path).resolve_all()[0]

    target_ids = {
        ref.target_name: ref.target_symbol_id
        for ref in resolved.references
        if ref.target_name in {"self._double", "cls._normalize"}
    }

    assert target_ids["self._double"] == "service:Calculator._double"
    assert target_ids["cls._normalize"] == "service:Calculator._normalize"


def test_incremental_indexing_tracks_changed_files(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source = repo_root / "service.py"
    source.write_text("def answer():\n    return 42\n", encoding="utf-8")

    db = AnalysisDatabase(tmp_path / "index.db")
    indexer = RepositoryIndexer(db)

    first = indexer.index_repository(repo_root)
    second = indexer.index_repository(repo_root)

    assert first["updated"] is True
    assert second["updated"] is False
    assert second["changed_files"] == []

    source.write_text("def answer():\n    return 43\n", encoding="utf-8")
    third = indexer.index_repository(repo_root)

    assert third["updated"] is True
    assert third["changed_files"] == ["service.py"]


def test_symbol_resolver_resolves_inherited_methods(tmp_path: Path):
    base = tmp_path / "base.py"
    child = tmp_path / "child.py"

    base.write_text(
        """
class BaseService:
    def ping(self):
        return "pong"
""",
        encoding="utf-8",
    )
    child.write_text(
        """
from base import BaseService

class ChildService(BaseService):
    def run(self):
        return self.ping()
""",
        encoding="utf-8",
    )

    parsed_files = [
        PythonAnalyzer().parse_file(base, tmp_path),
        PythonAnalyzer().parse_file(child, tmp_path),
    ]
    resolved = SymbolResolver(parsed_files, tmp_path).resolve_all()

    refs = {
        ref.target_name: ref.target_symbol_id
        for parsed in resolved
        for ref in parsed.references
        if ref.target_name in {"self.ping"}
    }

    assert refs["self.ping"] == "child:ChildService.ping" or refs["self.ping"] == "base:BaseService.ping"
