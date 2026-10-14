import hashlib
from pathlib import Path

from analyzers.base import BaseAnalyzer
from analyzers.python.parser import PythonAnalyzer
from core.graph import DependencyGraph
from core.models import FileRecord, IndexStatus, ParsedFile
from core.resolver import SymbolResolver
from storage.database import AnalysisDatabase
from storage.graph_store import build_graph_store


class RepositoryIndexer:
    """Scans, parses, resolves, and persists a repository index."""

    def __init__(self, database: AnalysisDatabase):
        self.database = database
        self.analyzers = [PythonAnalyzer()]
        self.graph_store = build_graph_store()

    def index_repository(self, repo_root: Path) -> dict[str, object]:
        repo_root = repo_root.resolve()
        repository = repo_root.as_posix()
        current_files = self._collect_file_hashes(repo_root)
        previous_files = self.database.get_file_hashes(repository)

        changed_files = sorted(
            {
                path
                for path, current_hash in current_files.items()
                if previous_files.get(path) != current_hash
            }
            | {path for path in previous_files if path not in current_files}
        )

        if not changed_files and self.database.repository_exists(repository):
            summary = self.database.get_repository_summary(repository)
            return {
                "repository": repository,
                "updated": False,
                "changed_files": [],
                **summary,
            }

        self.database.delete_repository(repository)
        parsed_files = self._parse_repository(repo_root)
        resolver = SymbolResolver(parsed_files, repo_root)
        resolved_files = resolver.resolve_all()

        self.database.replace_index(repository, resolved_files)

        dependency_graph = DependencyGraph()
        dependency_graph.build_from_parsed_files(resolved_files)
        dependency_edges = dependency_graph.to_dependency_edges()

        self.database.save_graph_edges(repository, dependency_edges)
        self.graph_store.clear_repository(repository)
        self.graph_store.persist(repository, dependency_edges)

        return {
            "repository": repository,
            "updated": True,
            "changed_files": changed_files,
            "files_indexed": len(resolved_files),
            "symbols_indexed": sum(len(item.symbols) for item in resolved_files),
            "references_indexed": sum(len(item.references) for item in resolved_files),
            "graph_nodes": dependency_graph.graph.number_of_nodes(),
            "graph_edges": dependency_graph.graph.number_of_edges(),
        }

    def _parse_repository(self, repo_root: Path) -> list[ParsedFile]:
        parsed_files: list[ParsedFile] = []

        for analyzer in self.analyzers:
            for parsed in analyzer.parse_repository(repo_root):
                absolute_path = repo_root / parsed.path
                file_hash = self._file_hash(absolute_path)

                self.database.upsert_file(
                    FileRecord(
                        path=parsed.path,
                        hash=file_hash,
                        language=analyzer.language,
                        indexing_status=IndexStatus.INDEXED,
                    ),
                    repo_root.as_posix(),
                )

                parsed_files.append(parsed)

        return parsed_files

    @staticmethod
    def _collect_file_hashes(repo_root: Path) -> dict[str, str]:
        hashes: dict[str, str] = {}
        analyzers = [PythonAnalyzer()]

        for path in sorted(repo_root.rglob("*")):
            if not path.is_file() or BaseAnalyzer._is_ignored(path):
                continue
            for analyzer in analyzers:
                if analyzer.supports_file(path):
                    hashes[path.relative_to(repo_root).as_posix()] = RepositoryIndexer._file_hash(path)
                    break
        return hashes

    @staticmethod
    def _file_hash(path: Path) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)

        return digest.hexdigest()
