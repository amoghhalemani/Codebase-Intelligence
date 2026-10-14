from typing import Any

from storage.database import AnalysisDatabase


class NavigationService:
    def __init__(self, database: AnalysisDatabase):
        self.database = database

    def find_definitions(self, repository: str, query: str) -> list[dict[str, Any]]:
        return self.database.find_symbols(repository, query)

    def get_symbol_details(self, repository: str, symbol_id: str) -> dict[str, Any]:
        symbol = self.database.get_symbol(repository, symbol_id)

        if not symbol:
            return {"error": "Symbol not found", "symbol_id": symbol_id}

        return {
            "symbol": symbol,
            "callers": self.database.get_callers(repository, symbol_id),
            "dependencies": self.database.get_dependencies(repository, symbol_id),
        }

    def find_references(self, repository: str, symbol_id: str) -> list[dict[str, Any]]:
        references = []

        for row in self.database.all_references(repository):
            if row["target_symbol_id"] == symbol_id:
                references.append(
                    {
                        "source_symbol_id": row["source_symbol_id"],
                        "reference_type": row["reference_type"],
                        "file": row["file"],
                        "line": row["line"],
                        "resolution_status": row["resolution_status"],
                    }
                )

        return references
