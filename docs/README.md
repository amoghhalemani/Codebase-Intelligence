# 📚 Codebase Intelligence Documentation

Welcome to the comprehensive technical documentation for **Codebase Intelligence**, a local developer tool and static analysis engine that extracts dependency graphs and intelligence metrics from Python codebases.

---

## 📑 Documentation Index

| Document | Topic | Description |
| :--- | :--- | :--- |
| [**1. System Architecture**](file:///d:/code/Golang/Codebase-Intelligence/docs/01_system_architecture.md) | High-Level Architecture | Component decomposition, modular layers, data flows, and interactive interfaces (CLI, REST API, MCP). |
| [**2. Python Indexer Pipeline & AST Flow**](file:///d:/code/Golang/Codebase-Intelligence/docs/02_indexer_pipeline_and_ast.md) | Indexer Deep Dive | Step-by-step pipeline walkthrough, AST visitors, symbol resolution algorithms, and end-to-end AST code examples. |
| [**3. Data Persistence & Storage**](file:///d:/code/Golang/Codebase-Intelligence/docs/03_data_persistence_and_storage.md) | Persistence Layer | SQLite relational schema, per-repository database isolation, indexing transactions, and optional Neo4j graph store synchronization. |
| [**4. Database Schema Reference**](file:///d:/code/Golang/Codebase-Intelligence/docs/database_schema.md) | Complete Schema Spec | Full ER diagram, DDL definitions, table-by-table column types, real belong-api examples, indexes, and SQL queries. |
| [**5. Implementation Plan**](file:///d:/code/Golang/Codebase-Intelligence/docs/implementation_plan.md) | Visual Graph & MCP Server | Concrete roadmap, detailed specifications for all 7 MCP tools, and interactive visual graph architecture. |
| [**6. MCP Server Setup Guide**](file:///d:/code/Golang/Codebase-Intelligence/docs/mcp_setup_guide.md) | Integration Guide | Copy-paste configurations for Claude Desktop, Cursor, and VS Code. |

---

## 🧭 System Overview at a Glance

```mermaid
flowchart TD
    subgraph UI ["User Interfaces"]
        CLI["CLI & Interactive REPL\n(cli.py)"]
        API["REST API\n(FastAPI / api/routes.py)"]
        MCP["MCP Server\n(mcp_server.py)"]
    end

    subgraph ServiceLayer ["Service Layer"]
        SVC["AnalysisService\n(services/analysis_service.py)"]
    end

    subgraph Features ["Intelligence Features"]
        NAV["Symbol Navigation"]
        IMP["Impact Analysis"]
        TEST["Test Selection"]
        DEAD["Dead Code Detection"]
        RISK["Risk Scoring"]
    end

    subgraph CoreEngine ["Core Engine"]
        IDX["RepositoryIndexer"]
        RES["SymbolResolver"]
        GRAPH["DependencyGraph (NetworkX)"]
    end

    subgraph Analyzers ["AST Analysis Layer"]
        BASE["BaseAnalyzer"]
        PY["PythonAnalyzer\n(Symbols, Imports, Calls)"]
    end

    subgraph Storage ["Storage Layer"]
        SQLITE[("Local SQLite DB\n(.codebase-intelligence/)")]
        NEO4J[("Neo4j Graph DB\n(Optional)")]
    end

    UI --> SVC
    SVC --> Features
    SVC --> CoreEngine
    CoreEngine --> Analyzers
    CoreEngine --> Storage
    Features --> Storage
```
