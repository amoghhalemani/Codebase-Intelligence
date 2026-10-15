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

### Option C: 🌐 Interactive Web Dashboard (Visual Graph & Analysis UI)

You can launch the full interactive web dashboard with graph visualization, search, blast radius analysis, dead code auditing, and smart test selection.

#### ⚡ 1-Click Startup Scripts:

**Windows (PowerShell or Command Prompt):**
```powershell
# Index demo_project and open dashboard in browser:
.\run_dashboard.bat

# Or index and open ANY repository:
.\run_dashboard.bat "D:\path\to\your-project"
```

**Linux / macOS:**
```bash
# Make executable (first time only):
chmod +x run_dashboard.sh

# Index demo_project and open dashboard in browser:
./run_dashboard.sh

# Or index and open ANY repository:
./run_dashboard.sh /path/to/your-project
```

#### 🛠️ Manual Step-by-Step Commands:
```powershell
# Step 1: Index your target repository
python cli.py index "demo_project"

# Step 2: Start the interactive dashboard server
python demo_dashboard/server.py
```
> The dashboard will start and automatically open in your default browser at **`http://127.0.0.1:5050`**.

#### 🎯 Features Available in the Web UI:
- **🔍 Symbol Search & Filter:** Real-time type-ahead search with category filters (**Functions**, **Classes**, **Modules**).
- **💥 Blast Radius Analysis:** Click any node (or select from search) and run blast radius analysis. Downstream callers highlight in glowing red while non-affected code dims.
- **🎯 Smart Test Selection:** Highlights only the unit test cases that cover the active function in glowing green.
- **🧹 Dead Code Audit:** Scans the whole repository and highlights all unreferenced orphan functions in glowing purple with 0 incoming callers.
- **📋 Inspector Drawer:** Displays code location, function signature, incoming callers, and outgoing dependencies.

---

### Option D: 🤖 Adding MCP Server to AI Coding Agents

Codebase Intelligence includes a built-in **Model Context Protocol (MCP)** server that exposes deep code graph queries directly to AI assistants.

#### 🧰 Tools Exposed to AI Agents:
| Tool | Purpose |
| :--- | :--- |
| `index_repository` | Indexes/re-indexes a repository and extracts dependency graphs. |
| `search_symbols` | Finds functions, classes, and variables by name or regex query. |
| `inspect_symbol` | Gets symbol location, signature, incoming callers, and callees. |
| `analyze_impact` | Computes downstream blast radius and risk level for proposed code changes. |
| `find_dependency_path`| Finds the shortest call/dependency chain between two symbols. |
| `recommend_tests` | Recommends the minimal test suite needed to validate a code change. |
| `detect_dead_code` | Discovers unused/orphan functions with zero callers across the codebase. |

---

#### 🔌 Agent Configuration Setup:

##### 1. Google Antigravity IDE
Create or update `.agents/mcp_config.json` in your workspace root (or globally at `%USERPROFILE%\.gemini\config\mcp_config.json`):
```json
{
  "mcpServers": {
    "codebase-intelligence": {
      "command": "d:\\code\\Golang\\Codebase-Intelligence\\.venv\\Scripts\\python.exe",
      "args": [
        "d:\\code\\Golang\\Codebase-Intelligence\\mcp_server.py"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
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
      "command": "d:\\code\\Golang\\Codebase-Intelligence\\.venv\\Scripts\\python.exe",
      "args": [
        "d:\\code\\Golang\\Codebase-Intelligence\\mcp_server.py"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

##### 3. Cursor
1. Open **Cursor Settings** $\rightarrow$ **Features** $\rightarrow$ **MCP**.
2. Click **+ Add New MCP Server**.
3. Fill in the fields:
   - **Name:** `codebase-intelligence`
   - **Type:** `command`
   - **Command:** `D:\code\Golang\Codebase-Intelligence\.venv\Scripts\python.exe D:\code\Golang\Codebase-Intelligence\mcp_server.py`

##### 4. VS Code (Cline / Roo Code / Continue)
Add to your extension's MCP settings (e.g. `cline_mcp_settings.json`):
```json
{
  "mcpServers": {
    "codebase-intelligence": {
      "command": "d:\\code\\Golang\\Codebase-Intelligence\\.venv\\Scripts\\python.exe",
      "args": [
        "d:\\code\\Golang\\Codebase-Intelligence\\mcp_server.py"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

##### 5. Windsurf
Add to `~/.codeium/windsurf/mcp_config.json`:
```json
{
  "mcpServers": {
    "codebase-intelligence": {
      "command": "d:\\code\\Golang\\Codebase-Intelligence\\.venv\\Scripts\\python.exe",
      "args": [
        "d:\\code\\Golang\\Codebase-Intelligence\\mcp_server.py"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

> **Tip (Windows UTF-8):** Always include `"env": { "PYTHONIOENCODING": "utf-8" }` to prevent Windows cp1252 character map issues during JSON-RPC communication.

---

#### 💬 Example Prompts to Test with Your AI Agent:
- *"Use `codebase-intelligence` to find all callers of `calculate_vat` in `demo_project`."*
- *"Analyze the blast radius if I refactor `PaymentProcessor.process_payment` in `demo_project`."*
- *"Detect any dead code or unreferenced functions in `demo_project`."*
- *"Recommend test cases that cover changes to `tax_calculator:calculate_vat`."*

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
