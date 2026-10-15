from pathlib import Path
import tempfile
import pytest

from analyzers.javascript.parser import JavaScriptAnalyzer
from core.indexing import RepositoryIndexer
from storage.database import AnalysisDatabase


def test_supports_file():
    analyzer = JavaScriptAnalyzer()
    assert analyzer.supports_file(Path("index.js"))
    assert analyzer.supports_file(Path("module.mjs"))
    assert analyzer.supports_file(Path("common.cjs"))
    assert analyzer.supports_file(Path("Component.jsx"))
    assert analyzer.supports_file(Path("service.ts"))
    assert analyzer.supports_file(Path("View.tsx"))
    assert not analyzer.supports_file(Path("script.py"))
    assert not analyzer.supports_file(Path("main.go"))


def test_parse_javascript_functions_classes_and_calls(tmp_path: Path):
    analyzer = JavaScriptAnalyzer()
    js_file = tmp_path / "math.js"
    js_file.write_text(
        """
import { formatCurrency } from './formatter.js';

function add(a, b) {
    return a + b;
}

const multiply = (x, y) => {
    return x * y;
};

class Calculator {
    calculateTotal(price, taxRate) {
        const subtotal = add(price, 0);
        const tax = multiply(subtotal, taxRate);
        return formatCurrency(subtotal + tax);
    }
}
""",
        encoding="utf-8",
    )

    parsed = analyzer.parse_file(js_file, tmp_path)

    symbol_names = {s.name for s in parsed.symbols}
    assert "add" in symbol_names
    assert "multiply" in symbol_names
    assert "Calculator" in symbol_names
    assert "calculateTotal" in symbol_names

    calc_method = next(s for s in parsed.symbols if s.name == "calculateTotal")
    assert calc_method.kind == "method"
    assert calc_method.qualified_name == "Calculator.calculateTotal"

    # Check calls inside calculateTotal
    call_targets = {r.target_name for r in parsed.references if r.reference_type == "call"}
    assert "add" in call_targets
    assert "multiply" in call_targets
    assert "formatCurrency" in call_targets

    # Check imports
    imported_paths = {i.imported_path for i in parsed.imports}
    assert any("formatter.formatCurrency" in p for p in imported_paths)


def test_parse_typescript_interfaces_and_types(tmp_path: Path):
    analyzer = JavaScriptAnalyzer()
    ts_file = tmp_path / "types.ts"
    ts_file.write_text(
        """
export interface UserPayload {
    id: string;
    username: string;
}

export type Status = 'active' | 'inactive';

export function createUser(payload: UserPayload): Status {
    return 'active';
}
""",
        encoding="utf-8",
    )

    parsed = analyzer.parse_file(ts_file, tmp_path)

    symbol_kinds = {s.name: s.kind for s in parsed.symbols}
    assert symbol_kinds.get("UserPayload") == "interface"
    assert symbol_kinds.get("Status") == "type"
    assert symbol_kinds.get("createUser") == "function"


def test_end_to_end_indexing_javascript_repository(tmp_path: Path):
    repo_root = tmp_path / "js_project"
    repo_root.mkdir()

    utils_file = repo_root / "utils.js"
    utils_file.write_text(
        """
function helper(x) {
    return x * 2;
}
""",
        encoding="utf-8",
    )

    app_file = repo_root / "app.js"
    app_file.write_text(
        """
import { helper } from './utils.js';

function main() {
    return helper(42);
}
""",
        encoding="utf-8",
    )

    db_path = tmp_path / "test.db"
    db = AnalysisDatabase(db_path)
    indexer = RepositoryIndexer(db)

    result = indexer.index_repository(repo_root)

    assert result["files_indexed"] == 2
    symbols = db.all_symbols(repo_root.resolve().as_posix())
    symbol_names = {s["name"] for s in symbols}
    assert "helper" in symbol_names
    assert "main" in symbol_names

    edges = db.all_edges(repo_root.resolve().as_posix())
    assert len(edges) > 0
