# 🧠 Codebase Intelligence

**Codebase Intelligence** is a local developer tool and static analysis engine that extracts dependency graphs and intelligence metrics from Python repositories. It enables impact analysis, symbol navigation, test selection, dead code detection, interactive visual graph exploration, and native Model Context Protocol (MCP) server support for AI coding assistants.

---

## ⚡ Quick Start & Setup

### 1. Prerequisites
- Python 3.10+ installed
- Git installed

### 2. Environment Setup

**Windows (PowerShell):**
```powershell
# 1. Create virtual environment
python -m venv .venv

# 2. Activate virtual environment
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
# 1. Create virtual environment
python3 -m venv .venv

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Running the Tool

### Option A: Interactive CLI Mode (Recommended for Beginners)
Launch the interactive terminal menu:
```powershell
python cli.py interactive --repo-root repository
```
From the interactive menu, you can clone GitHub repositories, index local code, search symbols, inspect dependencies, run impact analysis, and detect dead code.

---

### Option B: Direct CLI Commands

```powershell
# 1. Index a repository
python cli.py index "D:\path\to\your-repo"

# 2. Search for symbols (functions, classes, variables)
python cli.py find "D:\path\to\your-repo" "calculate_tax"

# 3. Inspect symbol details, callers, and outgoing dependencies
python cli.py symbol "D:\path\to\your-repo" "billing:calculate_tax"

# 4. Multi-hop blast-radius impact analysis
python cli.py impact "D:\path\to\your-repo" "billing:calculate_tax"

# 5. Recommend test cases for modified code
python cli.py tests "D:\path\to\your-repo" "billing:calculate_tax"

# 6. Detect unused / dead code candidates
python cli.py dead-code "D:\path\to\your-repo"
```

---

### Option C: 🌐 Interactive Visual Graph (Zero-Docker)
Generate a standalone, interactive HTML dependency graph and open it in your browser:
```powershell
python cli.py visualize "D:\path\to\your-repo"
```
- **Features in Browser:** Interactive Cytoscape.js canvas with zoom & pan, live search bar, color-coded node types (Classes, Functions, Modules, Variables), side drawer with code signatures, and a **"Trace Blast Radius"** button.
- **Zero external dependencies:** Runs completely locally without Docker or Neo4j.

---

### Option D: 🤖 Model Context Protocol (MCP) Server for AI Assistants
Start the MCP server over standard I/O (`stdio`):
```powershell
python mcp_server.py
# or
python cli.py mcp
```

#### Connecting to AI Assistants:

##### 1. Google Antigravity
Create or update `.agents/mcp_config.json` in your project root (or globally in `%USERPROFILE%\.gemini\config\mcp_config.json`):
```json
{
  "mcpServers": {
    "codebase-intelligence": {
      "command": "D:\\code\\Golang\\Codebase-Intelligence\\.venv\\Scripts\\python.exe",
      "args": ["D:\\code\\Golang\\Codebase-Intelligence\\mcp_server.py"]
    }
  }
}
```

##### 2. Claude Desktop
Add to `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):
```json
{
  "mcpServers": {
    "codebase-intelligence": {
      "command": "D:\\code\\Golang\\Codebase-Intelligence\\.venv\\Scripts\\python.exe",
      "args": ["D:\\code\\Golang\\Codebase-Intelligence\\mcp_server.py"]
    }
  }
}
```

##### 3. Cursor
Open **Cursor Settings** $\rightarrow$ **Features** $\rightarrow$ **MCP** $\rightarrow$ **Add New MCP Server**:
- **Name:** `codebase-intelligence`
- **Type:** `command`
- **Command:** `D:\code\Golang\Codebase-Intelligence\.venv\Scripts\python.exe D:\code\Golang\Codebase-Intelligence\mcp_server.py`

*See [**`docs/mcp_setup_guide.md`**](file:///d:/code/Golang/Codebase-Intelligence/docs/mcp_setup_guide.md) for full details and example prompts.*

---

### Option E: REST API Server (FastAPI)
Run the headless REST API service:
```powershell
uvicorn api.routes:router --reload --port 8000
```
Interactive Swagger API documentation will be available at `http://127.0.0.1:8000/docs`.

---

## 💾 Where is Data Stored?

Codebase Intelligence uses a **partitioned SQLite storage model**. Each repository receives an isolated database file:

```text
.codebase-intelligence/
├── index.db                       # Unused default shell
├── repositories/                  # 📂 Isolated repository database root
│   └── <repo_name>/
│       └── <sha256_hash>.db       # 💾 Dedicated SQLite DB (files, symbols, edges, findings)
└── visualizations/
    └── <repo_name>_graph.html     # 🌐 Standalone interactive visual graph
```

- Each database contains: `files`, `symbols`, `references_table`, `dependency_edges`, and `findings`.
- *See [**`docs/database_schema.md`**](file:///d:/code/Golang/Codebase-Intelligence/docs/database_schema.md) for full ER diagrams, DDL, and table specifications.*

---

## 🧪 Running Tests

Run the full automated test suite:
```powershell
# Run with Pytest (15 tests: unit + end-to-end)
pytest

# Or run the comprehensive E2E test suite standalone:
python tests/test_end_to_end.py
```
*Generates an execution report in [**`reports/e2e_test_report.md`**](file:///d:/code/Golang/Codebase-Intelligence/reports/e2e_test_report.md).*

---

## 📑 In-Depth Documentation

| Document | Topic | Description |
| :--- | :--- | :--- |
| [**1. System Architecture**](file:///d:/code/Golang/Codebase-Intelligence/docs/01_system_architecture.md) | Architecture | Layer breakdown (CLI $\rightarrow$ Service $\rightarrow$ Engine $\rightarrow$ AST $\rightarrow$ Storage) and sequence diagrams. |
| [**2. Python Indexer Pipeline & AST**](file:///d:/code/Golang/Codebase-Intelligence/docs/02_indexer_pipeline_and_ast.md) | Indexer Flow | AST visitors, symbol resolution algorithms, and step-by-step code walkthrough. |
| [**3. Data Persistence & Storage**](file:///d:/code/Golang/Codebase-Intelligence/docs/03_data_persistence_and_storage.md) | Persistence | SQLite storage architecture and optional Neo4j property graph synchronization. |
| [**4. Database Schema Reference**](file:///d:/code/Golang/Codebase-Intelligence/docs/database_schema.md) | Database Schema | Complete ER diagram, DDL tables, column types, and SQL query cheat sheet. |
| [**5. Implementation Plan**](file:///d:/code/Golang/Codebase-Intelligence/docs/implementation_plan.md) | Roadmap | Implementation specifications for Visual Graph Exporter and MCP Server. |
| [**6. MCP Server Setup Guide**](file:///d:/code/Golang/Codebase-Intelligence/docs/mcp_setup_guide.md) | MCP Integration | Setup instructions and copy-paste JSON configurations for Claude Desktop, Cursor, and Antigravity. |
