from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from core.models import ParsedFile


class BaseAnalyzer(ABC):
    """Base interface for language-specific repository analyzers."""

    language: str = "generic"

    @abstractmethod
    def supports_file(self, path: Path) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse_file(self, path: Path, repo_root: Path) -> ParsedFile:
        raise NotImplementedError

    def parse_repository(self, repo_root: Path) -> list[ParsedFile]:
        parsed: list[ParsedFile] = []

        for path in sorted(repo_root.rglob("*")):
            if not path.is_file():
                continue

            if self._is_ignored(path):
                continue

            if self.supports_file(path):
                parsed.append(self.parse_file(path, repo_root))

        return parsed

    @staticmethod
    def _is_ignored(path: Path) -> bool:
        ignored_parts = {
            ".git",
            ".venv",
            ".codebase-intelligence",
            "venv",
            "__pycache__",
            ".mypy_cache",
            ".pytest_cache",
            "node_modules",
            "dist",
            "build",
        }
        if path.name == ".DS_Store":
            return True
        return bool(set(path.parts) & ignored_parts)
