import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from git_analysis.history import GitHistoryAnalyzer
from services.analysis_service import AnalysisService


def repo_database_path(repo_root: Path) -> Path:
    repo_root = Path(repo_root).resolve()
    repo_name = re.sub(r"[^A-Za-z0-9._-]+", "_", repo_root.name) or "repository"
    repo_key = hashlib.sha256(str(repo_root).encode("utf-8")).hexdigest()[:12]
    db_path = Path(".codebase-intelligence") / "repositories" / repo_name / f"{repo_key}.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def resolve_repo_target(repo_root: Path, repo_url: str) -> Path:
    repo_root = Path(repo_root).resolve()
    parsed = urlparse(repo_url)
    raw_path = parsed.path.strip("/")

    if raw_path:
        repo_name = raw_path.rsplit("/", 1)[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        if repo_name:
            return repo_root / repo_name

    return repo_root / "repository"


def list_repositories(repo_root: Path) -> list[Path]:
    repo_root = Path(repo_root).resolve()
    if not repo_root.exists():
        return []

    return sorted(
        path for path in repo_root.iterdir() if path.is_dir()
    )


def add_github_repo(repo_url: str, repo_root: Path = Path("repository")) -> dict:
    repo_root = Path(repo_root).resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    target = resolve_repo_target(repo_root, repo_url)

    if target.exists():
        return {
            "repository_url": repo_url,
            "path": target.as_posix(),
            "status": "exists",
        }

    clone_path = GitHistoryAnalyzer.clone_repository(repo_url, target)
    return {
        "repository_url": repo_url,
        "path": clone_path.as_posix(),
        "status": "cloned",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codebase-intelligence",
        description="Index, analyze, and inspect Python repositories.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    clone_parser = subparsers.add_parser(
        "clone",
        help="Clone a Git repository and build its index.",
    )
    clone_parser.add_argument("repository_url")
    clone_parser.add_argument("destination", type=Path)
    clone_parser.add_argument("--branch", type=str, default=None)

    index_parser = subparsers.add_parser(
        "index",
        help="Index an existing local repository.",
    )
    index_parser.add_argument("repository", type=Path)

    find_parser = subparsers.add_parser(
        "find",
        help="Find symbols by name or qualified name.",
    )
    find_parser.add_argument("repository", type=Path)
    find_parser.add_argument("query")

    details_parser = subparsers.add_parser(
        "symbol",
        help="Show a symbol, its callers, and dependencies.",
    )
    details_parser.add_argument("repository", type=Path)
    details_parser.add_argument("symbol_id")

    impact_parser = subparsers.add_parser(
        "impact",
        help="Analyze the impact of changed symbols.",
    )
    impact_parser.add_argument("repository", type=Path)
    impact_parser.add_argument("symbols", nargs="+")
    impact_parser.add_argument("--base", default=None)

    tests_parser = subparsers.add_parser(
        "tests",
        help="Recommend tests for changed symbols.",
    )
    tests_parser.add_argument("repository", type=Path)
    tests_parser.add_argument("symbols", nargs="+")

    dead_code_parser = subparsers.add_parser(
        "dead-code",
        help="Find potentially unreferenced symbols and unused imports.",
    )
    dead_code_parser.add_argument("repository", type=Path)

    interactive_parser = subparsers.add_parser(
        "interactive",
        help="Launch the interactive repository CLI.",
    )
    interactive_parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("repository"),
        help="Directory containing cloned repositories.",
    )

    return parser


def prompt_choice(prompt: str, choices: list[str]) -> str:
    while True:
        value = input(prompt).strip()
        if value in choices:
            return value
        print(f"Choose one of: {', '.join(choices)}")


def interactive_cli(repo_root: Path = Path("repository")) -> None:
    repo_root = Path(repo_root).resolve()
    repo_root.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            print("\n=== Codebase Intelligence CLI ===")
            print("1) Add GitHub repo")
            print("2) Index repo")
            print("3) Search symbols")
            print("4) Symbol details")
            print("5) Impact analysis")
            print("6) Dead code")
            print("7) List repos")
            print("8) Exit")

            choice = prompt_choice("Select an option: ", ["1", "2", "3", "4", "5", "6", "7", "8"])

            if choice == "1":
                url = input("GitHub repository URL: ").strip()
                if not url:
                    print("Repository URL is required.")
                    continue
                result = add_github_repo(url, repo_root)
                print(json.dumps(result, indent=2, default=str))
            elif choice == "2":
                repos = list_repositories(repo_root)
                if not repos:
                    print("No repositories found in the repository folder.")
                    continue
                for index, repo in enumerate(repos, start=1):
                    print(f"{index}) {repo.name} ({repo.as_posix()})")
                selected = input("Choose repository number: ").strip()
                try:
                    chosen = repos[int(selected) - 1]
                except (ValueError, IndexError):
                    print("Invalid repository selection.")
                    continue
                service = AnalysisService(repo_database_path(chosen))
                try:
                    result = service.index_local_repository(chosen)
                    print(json.dumps(result, indent=2, default=str))
                finally:
                    service.close()
            elif choice == "3":
                repos = list_repositories(repo_root)
                if not repos:
                    print("No repositories found in the repository folder.")
                    continue
                for index, repo in enumerate(repos, start=1):
                    print(f"{index}) {repo.name}")
                selected = input("Choose repository number: ").strip()
                try:
                    chosen = repos[int(selected) - 1]
                except (ValueError, IndexError):
                    print("Invalid repository selection.")
                    continue
                query = input("Search query: ").strip()
                if not query:
                    print("Query must not be empty.")
                    continue
                service = AnalysisService(repo_database_path(chosen))
                try:
                    result = service.find_symbol(chosen, query)
                    print(json.dumps({"results": result}, indent=2, default=str))
                finally:
                    service.close()
            elif choice == "4":
                repos = list_repositories(repo_root)
                if not repos:
                    print("No repositories found in the repository folder.")
                    continue
                for index, repo in enumerate(repos, start=1):
                    print(f"{index}) {repo.name}")
                selected = input("Choose repository number: ").strip()
                try:
                    chosen = repos[int(selected) - 1]
                except (ValueError, IndexError):
                    print("Invalid repository selection.")
                    continue
                symbol_id = input("Symbol id: ").strip()
                service = AnalysisService(repo_database_path(chosen))
                try:
                    result = service.symbol_details(chosen, symbol_id)
                    print(json.dumps(result, indent=2, default=str))
                finally:
                    service.close()
            elif choice == "5":
                repos = list_repositories(repo_root)
                if not repos:
                    print("No repositories found in the repository folder.")
                    continue
                for index, repo in enumerate(repos, start=1):
                    print(f"{index}) {repo.name}")
                selected = input("Choose repository number: ").strip()
                try:
                    chosen = repos[int(selected) - 1]
                except (ValueError, IndexError):
                    print("Invalid repository selection.")
                    continue
                symbols = input("Changed symbols (comma-separated): ").strip()
                changed_symbols = [item.strip() for item in symbols.split(",") if item.strip()]
                if not changed_symbols:
                    print("At least one symbol is required.")
                    continue
                service = AnalysisService(repo_database_path(chosen))
                try:
                    result = service.analyze_change(chosen, changed_symbols)
                    print(json.dumps(result, indent=2, default=str))
                finally:
                    service.close()
            elif choice == "6":
                repos = list_repositories(repo_root)
                if not repos:
                    print("No repositories found in the repository folder.")
                    continue
                for index, repo in enumerate(repos, start=1):
                    print(f"{index}) {repo.name}")
                selected = input("Choose repository number: ").strip()
                try:
                    chosen = repos[int(selected) - 1]
                except (ValueError, IndexError):
                    print("Invalid repository selection.")
                    continue
                service = AnalysisService(repo_database_path(chosen))
                try:
                    result = service.detect_dead_code(chosen)
                    print(json.dumps(result, indent=2, default=str))
                finally:
                    service.close()
            elif choice == "7":
                repos = list_repositories(repo_root)
                if not repos:
                    print("No repositories found in the repository folder.")
                    continue
                for repo in repos:
                    print(repo.as_posix())
            elif choice == "8":
                print("Goodbye.")
                break
    finally:
        service.close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    service = AnalysisService(Path(".codebase-intelligence/index.db"))

    try:
        if args.command == "clone":
            service = AnalysisService(repo_database_path(args.destination))
            result = service.clone_and_index(
                args.repository_url,
                args.destination,
                args.branch,
            )
        elif args.command == "index":
            service = AnalysisService(repo_database_path(args.repository))
            result = service.index_local_repository(args.repository)
        elif args.command == "find":
            service = AnalysisService(repo_database_path(args.repository))
            result = {"results": service.find_symbol(args.repository, args.query)}
        elif args.command == "symbol":
            service = AnalysisService(repo_database_path(args.repository))
            result = service.symbol_details(args.repository, args.symbol_id)
        elif args.command == "impact":
            service = AnalysisService(repo_database_path(args.repository))
            result = service.analyze_change(
                args.repository,
                args.symbols,
                args.base,
            )
        elif args.command == "tests":
            service = AnalysisService(repo_database_path(args.repository))
            result = service.test_selection.recommend_tests(
                args.repository.as_posix(),
                args.repository.resolve(),
                args.symbols,
            )
        elif args.command == "dead-code":
            service = AnalysisService(repo_database_path(args.repository))
            result = service.detect_dead_code(args.repository)
        elif args.command == "interactive":
            interactive_cli(args.repo_root)
            return
        else:
            parser.error(f"Unknown command: {args.command}")
            return

        print(json.dumps(result, indent=2, default=str))
    finally:
        if 'service' in locals():
            service.close()


if __name__ == "__main__":
    main()
