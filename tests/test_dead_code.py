from features.dead_code import DeadCodeService


def test_dead_code_detection_reports_unused_symbol():
    service = DeadCodeService.__new__(DeadCodeService)
    service.database = type(
        "FakeDatabase",
        (),
        {
            "all_symbols": lambda self, repo: [
                {
                    "id": "app:unused_function",
                    "name": "unused_function",
                    "qualified_name": "unused_function",
                    "kind": "function",
                    "file": "app.py",
                    "module": "app",
                    "start_line": 1,
                    "end_line": 2,
                }
            ],
            "all_edges": lambda self, repo: [],
            "all_references": lambda self, repo: [],
            "save_findings": lambda self, repo, findings: None,
        },
    )()

    result = service.detect("test")

    assert result["finding_count"] >= 1
    assert any(
        finding["rule"] == "potentially-unreferenced-symbol"
        for finding in result["findings"]
    )


def test_dead_code_ignores_ast_visitor_hooks():
    service = DeadCodeService.__new__(DeadCodeService)
    service.database = type(
        "FakeDatabase",
        (),
        {
            "all_symbols": lambda self, repo: [
                {
                    "id": "analyzers.python.symbols:SymbolVisitor",
                    "name": "SymbolVisitor",
                    "qualified_name": "SymbolVisitor",
                    "kind": "class",
                    "file": "analyzers/python/symbols.py",
                    "module": "analyzers.python.symbols",
                    "start_line": 1,
                    "end_line": 40,
                },
                {
                    "id": "analyzers.python.symbols:SymbolVisitor.visit_FunctionDef",
                    "name": "visit_FunctionDef",
                    "qualified_name": "SymbolVisitor.visit_FunctionDef",
                    "kind": "function",
                    "file": "analyzers/python/symbols.py",
                    "module": "analyzers.python.symbols",
                    "start_line": 13,
                    "end_line": 22,
                },
                {
                    "id": "analyzers.python.symbols:SymbolVisitor.visit_Assign",
                    "name": "visit_Assign",
                    "qualified_name": "SymbolVisitor.visit_Assign",
                    "kind": "function",
                    "file": "analyzers/python/symbols.py",
                    "module": "analyzers.python.symbols",
                    "start_line": 23,
                    "end_line": 32,
                },
            ],
            "all_edges": lambda self, repo: [],
            "all_references": lambda self, repo: [],
            "save_findings": lambda self, repo, findings: None,
        },
    )()

    result = service.detect("test")

    finding_ids = [finding["evidence"]["symbol_id"] for finding in result["findings"]]

    assert "analyzers.python.symbols:SymbolVisitor" not in finding_ids
    assert "analyzers.python.symbols:SymbolVisitor.visit_FunctionDef" not in finding_ids
    assert "analyzers.python.symbols:SymbolVisitor.visit_Assign" not in finding_ids
