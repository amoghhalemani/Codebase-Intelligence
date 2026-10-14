from pathlib import Path

from cli import resolve_repo_target


def test_resolve_repo_target_from_github_url():
    repo_root = Path("repository").resolve()

    target = resolve_repo_target(repo_root, "https://github.com/octo/sample.git")

    assert target == repo_root / "sample"

    target = resolve_repo_target(repo_root, "https://github.com/octo/another-repo")
    assert target == repo_root / "another-repo"
