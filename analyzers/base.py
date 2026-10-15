import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterator

from core.models import ParsedFile


class BaseAnalyzer(ABC):
    """Base interface for language-specific repository analyzers."""

    language: str = "generic"

    IGNORED_DIRS = {
        ".git",
        ".venv",
        ".codebase-intelligence",
        ".codebase_intelligence",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        "node_modules",
        "dist",
        "build",
        "repository",
    }

    @abstractmethod
    def supports_file(self, path: Path) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse_file(self, path: Path, repo_root: Path) -> ParsedFile:
        raise NotImplementedError

    @classmethod
    def iter_files(cls, repo_root: Path) -> Iterator[Path]:
        """Walks the repository files, pruning ignored directories in-place so they are never traversed."""
        for root, dirs, files in os.walk(repo_root):
            # Prune directories in-place to avoid descending into ignored folders
            dirs[:] = [
                d for d in dirs
                if d not in cls.IGNORED_DIRS and not d.startswith(".codebase-intelligence")
            ]
            for file in files:
                if file == ".DS_Store":
                    continue
                path = Path(root) / file
                if not cls._is_ignored(path):
                    yield path

    def parse_repository(self, repo_root: Path) -> list[ParsedFile]:
        parsed: list[ParsedFile] = []

        for path in sorted(self.iter_files(repo_root)):
            if self.supports_file(path):
                parsed.append(self.parse_file(path, repo_root))

        return parsed

    @classmethod
    def _is_ignored(cls, path: Path) -> bool:
        if path.name == ".DS_Store":
            return True
        return bool(set(path.parts) & cls.IGNORED_DIRS)
