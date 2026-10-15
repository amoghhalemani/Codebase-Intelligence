from pathlib import Path

from features.test_selection import TestSelectionService


def test_discover_tests_finds_test_functions(tmp_path: Path):
    test_file = tmp_path / "test_billing.py"
    test_file.write_text(
        """
def test_calculate_tax():
    assert True

async def test_async_flow():
    assert True
""",
        encoding="utf-8",
    )

    service = TestSelectionService.__new__(TestSelectionService)
    service.database = type("DummyDatabase", (), {"all_symbols": lambda self, repo: []})()
    tests = service.discover_tests(tmp_path)

    assert {test.name for test in tests} == {
        "test_calculate_tax",
        "test_async_flow",
    }
