
import subprocess
from pathlib import Path
from typing import Optional

from git import InvalidGitRepositoryError, Repo


class GitHistoryAnalyzer:
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()
        self.repo = None

        try:
            self.repo = Repo(self.repo_path)
        except (InvalidGitRepositoryError, ValueError):
            self.repo = None

    @classmethod
    def clone_repository(
        cls,
        repository_url: str,
        destination: Path,
        branch: Optional[str] = None,
    ) -> Path:
        destination = Path(destination).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists() and (destination / ".git").exists():
            repo = Repo(destination)
            repo.remotes.origin.fetch()
        else:
            repo = Repo.clone_from(repository_url, destination)

        if branch:
            repo.git.checkout(branch)

        return destination

    def current_revision(self) -> Optional[str]:
        if self.repo is None:
            return None
        return self.repo.head.commit.hexsha

    def changed_files(
        self,
        base_revision: Optional[str] = None,
        include_uncommitted: bool = True,
    ) -> list[str]:
        if self.repo is None:
            return []

        changed: set[str] = set()

        if base_revision:
            diffs = self.repo.head.commit.diff(base_revision)
        else:
            diffs = self.repo.head.commit.diff(None)

        for diff in diffs:
            for path in (diff.a_path, diff.b_path):
                if path:
                    changed.add(path)

        if include_uncommitted:
            changed.update(
                item.a_path
                for item in self.repo.index.diff(None)
                if item.a_path
            )

        return sorted(changed)

    def co_changed_files(self, target_file: str, max_commits: int = 200) -> list[str]:
        if self.repo is None:
            return []

        result = subprocess.run(
            [
                "git",
                "-C",
                str(self.repo_path),
                "log",
                f"-{max_commits}",
                "--name-only",
                "--pretty=format:",
                "--",
                target_file,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        commits: list[list[str]] = []
        current: list[str] = []

        for line in result.stdout.splitlines():
            stripped = line.strip()

            if not stripped:
                if current:
                    commits.append(current)
                    current = []
                continue

            current.append(stripped)

        if current:
            commits.append(current)

        co_changes: dict[str, int] = {}

        for files in commits:
            if target_file not in files:
                continue

            for file_path in files:
                if file_path != target_file:
                    co_changes[file_path] = co_changes.get(file_path, 0) + 1

        return [
            path
            for path, _ in sorted(
                co_changes.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

    def file_change_frequency(self, file_path: str, max_commits: int = 500) -> int:
        if self.repo is None:
            return 0

        result = subprocess.run(
            [
                "git",
                "-C",
                str(self.repo_path),
                "rev-list",
                f"--count",
                "HEAD",
                "--",
                file_path,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        try:
            return int(result.stdout.strip())
        except ValueError:
            return 0
