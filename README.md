# Codebase Intelligence

A Python repository intelligence tool for indexing local repositories, resolving symbols, exploring dependency graphs, and analyzing impact, dead code, and test recommendations.

This project is designed to help you inspect a codebase with a lightweight static-analysis pipeline and a graph-oriented understanding of references, calls, and dependencies.

## What this project does

- Indexes Python repositories from disk
- Extracts symbols, functions, classes, imports, and references
- Builds an in-memory and persisted dependency graph
- Supports symbol search and symbol detail lookup
- Analyzes change impact across repository code
- Suggests relevant tests for changed symbols
- Detects potentially unreferenced symbols and unused imports
- Supports a repo-scoped SQLite database layout for isolated indexing per repository

## Why this exists

The goal is to make repository analysis feel like a local code intelligence layer:

- understand what code exists
- see how symbols connect
- evaluate which code is impacted by a change
- find likely dead or weakly connected symbols
- maintain repo-specific indexes without mixing all repos into one database

## Project architecture

The project is organized into a few main components:

- `cli.py` — command-line entrypoint and interactive menu
- `services/analysis_service.py` — orchestration layer for indexing and queries
- `core/indexing.py` — repository scanning and indexing logic
- `core/graph.py` — dependency graph representation and path queries
- `analyzers/` — static analysis code for Python parsing and symbol extraction
- `features/` — impact analysis, dead code, navigation, risk, and test selection
- `storage/` — database persistence
- `git_analysis/` — git-aware analysis helpers

## Requirements

- Python 3.10+
- Git installed locally
- Optional: Neo4j for graph-native query storage

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Optional Neo4j setup

This project supports optional Neo4j-backed graph storage. If you want graph-native persistence, set the environment variables before running:

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=codeintel123
```

If Neo4j is not available, the system will fall back gracefully to SQLite-backed graph data.

## Repository layout

The project expects a local repository folder for cloned repos.

Example:

```text
codebase-intelligence/
  repository/
    Anchor/
    Vision/
  .codebase-intelligence/
    repositories/
      Anchor/
        <hash>.db
      Vision/
        <hash>.db
```

This gives each repo its own database file and avoids mixing repository data together in one global index.

## Quick start

### 1) Prepare a repo folder

```bash
mkdir -p repository
```

### 2) Add or clone a repo

```bash
python3 cli.py clone https://github.com/owner/repo.git repository/RepoName
```

Or if the repo already exists locally:

```bash
python3 cli.py index repository/RepoName
```

### 3) Run interactive mode

```bash
python3 cli.py interactive --repo-root repository
```

From the menu you can:

1. Add GitHub repo
2. Index repo
3. Search symbols
4. Symbol details
5. Impact analysis
6. Dead code
7. List repos
8. Exit

## CLI commands

### Index a local repository

```bash
python3 cli.py index repository/Anchor
```

### Search symbols

```bash
python3 cli.py find repository/Anchor "hello"
```

### Look up symbol details

```bash
python3 cli.py symbol repository/Anchor "module_name:hello"
```

### Impact analysis

```bash
python3 cli.py impact repository/Anchor "hello"
```

### Dead code analysis

```bash
python3 cli.py dead-code repository/Anchor
```

### Run tests recommendation

```bash
python3 cli.py tests repository/Anchor "hello"
```

## Example usage workflow

```bash
cd /Users/reipapa/codebase-intelligence
python3 cli.py interactive --repo-root repository
```

Then choose a repo and run:

- index repo
- search symbol
- inspect symbol details
- run impact analysis
- run dead-code scan

## Notes on dead-code detection

The dead-code feature is heuristic. It identifies "potentially unreferenced symbols" using static analysis and graph edges. This can produce false positives for:

- framework entry points
- decorators and registries
- exported API handlers
- dynamic call patterns
- server/tool registration

Treat the output as a review list rather than a guaranteed deletion list.

## Testing

Run the project tests with:

```bash
pytest -q
```

For CLI-focused validation, the repo includes tests for parser, graph, impact, and dead-code behavior.

## Project status

This project is a working static-analysis prototype for repository intelligence. It is suitable for:

- local repo exploration
- code impact analysis
- static graph building
- repo-by-repo indexing workflows

It is not yet a full production-grade code intelligence platform, but it is structured to grow into one.

## License

This project is provided as-is for local repository intelligence and analysis work.

## Contributing

If you want to extend the project, good next areas are:

- better symbol resolution across imports and inheritance
- incremental indexing
- graph-native query improvements
- richer repo metadata and search UX
- multi-repo orchestration and batch analysis

## Quick repository summary

```text
Codebase Intelligence
- static analysis for Python repos
- graph-backed dependency tracking
- impact and test recommendations
- dead-code heuristics
- repo-scoped SQLite indexing
```
