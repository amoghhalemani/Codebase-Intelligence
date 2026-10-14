import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from core.models import (
    AnalysisFinding,
    FileRecord,
    IndexStatus,
    ParsedFile,
    ResolutionStatus,
)
from core.models import DependencyEdge


class AnalysisDatabase:
    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path)
        self._connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS files (
                    repository TEXT NOT NULL,
                    path TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    language TEXT NOT NULL,
                    indexing_status TEXT NOT NULL,
                    PRIMARY KEY (repository, path)
                );

                CREATE TABLE IF NOT EXISTS symbols (
                    repository TEXT NOT NULL,
                    id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    qualified_name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    file TEXT NOT NULL,
                    module TEXT NOT NULL,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    signature TEXT,
                    PRIMARY KEY (repository, id)
                );

                CREATE TABLE IF NOT EXISTS references_table (
                    repository TEXT NOT NULL,
                    source_symbol_id TEXT NOT NULL,
                    target_name TEXT NOT NULL,
                    target_symbol_id TEXT,
                    reference_type TEXT NOT NULL,
                    resolution_status TEXT NOT NULL,
                    file TEXT NOT NULL,
                    line INTEGER NOT NULL,
                    evidence TEXT NOT NULL,
                    PRIMARY KEY (
                        repository, source_symbol_id, target_name,
                        reference_type, file, line
                    )
                );

                CREATE TABLE IF NOT EXISTS dependency_edges (
                    repository TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relationship TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    PRIMARY KEY (repository, source_id, target_id, relationship)
                );

                CREATE TABLE IF NOT EXISTS findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repository TEXT NOT NULL,
                    rule TEXT NOT NULL,
                    location TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    limitations TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_symbols_file
                ON symbols(repository, file);

                CREATE INDEX IF NOT EXISTS idx_symbols_name
                ON symbols(repository, name);

                CREATE INDEX IF NOT EXISTS idx_edges_target
                ON dependency_edges(repository, target_id);
                """
            )

    def upsert_file(self, file_record: FileRecord, repository: str = "") -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT OR REPLACE INTO files
                (repository, path, hash, language, indexing_status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    repository,
                    file_record.path,
                    file_record.hash,
                    file_record.language,
                    file_record.indexing_status.value,
                ),
            )

    def get_file_hashes(self, repository: str) -> dict[str, str]:
        rows = self._connection.execute(
            "SELECT path, hash FROM files WHERE repository = ?",
            (repository,),
        ).fetchall()
        return {row["path"]: row["hash"] for row in rows}

    def get_repository_summary(self, repository: str) -> dict[str, int]:
        summary = {
            "files_indexed": self._connection.execute(
                "SELECT COUNT(*) FROM files WHERE repository = ?",
                (repository,),
            ).fetchone()[0],
            "symbols_indexed": self._connection.execute(
                "SELECT COUNT(*) FROM symbols WHERE repository = ?",
                (repository,),
            ).fetchone()[0],
            "references_indexed": self._connection.execute(
                "SELECT COUNT(*) FROM references_table WHERE repository = ?",
                (repository,),
            ).fetchone()[0],
            "graph_nodes": self._connection.execute(
                "SELECT COUNT(DISTINCT source_id) FROM dependency_edges WHERE repository = ? UNION ALL SELECT COUNT(DISTINCT target_id) FROM dependency_edges WHERE repository = ?",
                (repository, repository),
            ).fetchall(),
            "graph_edges": self._connection.execute(
                "SELECT COUNT(*) FROM dependency_edges WHERE repository = ?",
                (repository,),
            ).fetchone()[0],
        }
        summary["graph_nodes"] = sum(int(row[0]) for row in summary["graph_nodes"]) if summary["graph_nodes"] else 0
        return summary

    def repository_exists(self, repository: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM files WHERE repository = ? LIMIT 1",
            (repository,),
        ).fetchone()
        return row is not None

    def delete_repository(self, repository: str) -> None:
        with self._connection:
            for table in [
                "symbols",
                "references_table",
                "dependency_edges",
                "findings",
                "files",
            ]:
                self._connection.execute(f"DELETE FROM {table} WHERE repository = ?", (repository,))

    def replace_index(self, repository: str, parsed_files: list[ParsedFile]) -> None:
        with self._connection:
            self._connection.executemany(
                "DELETE FROM symbols WHERE repository = ?",
                [(repository,)],
            )
            self._connection.executemany(
                "DELETE FROM references_table WHERE repository = ?",
                [(repository,)],
            )

            for parsed in parsed_files:
                for symbol in parsed.symbols:
                    self._connection.execute(
                        """
                        INSERT OR REPLACE INTO symbols
                        (repository, id, name, qualified_name, kind, file,
                         module, start_line, end_line, signature)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            repository,
                            symbol.id,
                            symbol.name,
                            symbol.qualified_name,
                            symbol.kind,
                            symbol.file,
                            symbol.module,
                            symbol.start_line,
                            symbol.end_line,
                            symbol.signature,
                        ),
                    )

                for reference in parsed.references:
                    self._connection.execute(
                        """
                        INSERT OR REPLACE INTO references_table
                        (repository, source_symbol_id, target_name,
                         target_symbol_id, reference_type, resolution_status,
                         file, line, evidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            repository,
                            reference.source_symbol_id,
                            reference.target_name,
                            reference.target_symbol_id,
                            reference.reference_type,
                            reference.resolution_status.value,
                            reference.file,
                            reference.line,
                            json.dumps(reference.evidence),
                        ),
                    )

    def save_graph_edges(
        self,
        repository: str,
        edges: list[DependencyEdge],
    ) -> None:
        with self._connection:
            self._connection.executemany(
                "DELETE FROM dependency_edges WHERE repository = ?",
                [(repository,)],
            )

            self._connection.executemany(
                """
                INSERT OR REPLACE INTO dependency_edges
                (repository, source_id, target_id, relationship, evidence, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        repository,
                        edge.source_id,
                        edge.target_id,
                        edge.relationship,
                        json.dumps(edge.evidence),
                        edge.confidence,
                    )
                    for edge in edges
                ],
            )

    def find_symbols(self, repository: str, query: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """
            SELECT * FROM symbols
            WHERE repository = ?
              AND (name LIKE ? OR qualified_name LIKE ? OR id LIKE ?)
            ORDER BY kind, qualified_name
            """,
            (repository, f"%{query}%", f"%{query}%", f"%{query}%"),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_symbol(self, repository: str, symbol_id: str) -> Optional[dict[str, Any]]:
        row = self._connection.execute(
            "SELECT * FROM symbols WHERE repository = ? AND id = ?",
            (repository, symbol_id),
        ).fetchone()
        return dict(row) if row else None

    def get_callers(self, repository: str, symbol_id: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """
            SELECT source_id, relationship, evidence, confidence
            FROM dependency_edges
            WHERE repository = ? AND target_id = ?
            """,
            (repository, symbol_id),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_dependencies(self, repository: str, symbol_id: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            """
            SELECT target_id, relationship, evidence, confidence
            FROM dependency_edges
            WHERE repository = ? AND source_id = ?
            """,
            (repository, symbol_id),
        ).fetchall()
        return [dict(row) for row in rows]

    def all_symbols(self, repository: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT * FROM symbols WHERE repository = ?",
            (repository,),
        ).fetchall()
        return [dict(row) for row in rows]

    def all_edges(self, repository: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT * FROM dependency_edges WHERE repository = ?",
            (repository,),
        ).fetchall()
        return [dict(row) for row in rows]

    def all_references(self, repository: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT * FROM references_table WHERE repository = ?",
            (repository,),
        ).fetchall()
        return [dict(row) for row in rows]

    def save_findings(self, repository: str, findings: list[AnalysisFinding]) -> None:
        with self._connection:
            self._connection.executemany(
                """
                INSERT INTO findings
                (repository, rule, location, explanation, evidence,
                 confidence, limitations)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        repository,
                        finding.rule,
                        finding.location,
                        finding.explanation,
                        json.dumps(finding.evidence),
                        finding.confidence,
                        json.dumps(finding.limitations),
                    )
                    for finding in findings
                ],
            )

    def close(self) -> None:
        self._connection.close()
