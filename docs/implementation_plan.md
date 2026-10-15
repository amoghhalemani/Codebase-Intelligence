# 🚀 Implementation Plan: Visual Graph & MCP Server

This document outlines the detailed architecture and technical specifications for implementing the **Zero-Docker Interactive Visual Graph** and the **Production MCP (Model Context Protocol) Server** for Codebase Intelligence.

---

## 🎯 High-Level Objectives

1. **Zero-Docker Interactive Visual Graph (`cli.py visualize`)**:
   - Directly transforms SQLite graph edges into a standalone, beautiful HTML graph viewer powered by **Cytoscape.js**.
   - Requires zero external services or Docker containers; opens directly in any web browser.
2. **Production-Ready MCP Server (`mcp_server.py`)**:
   - Exposes static analysis, symbol navigation, impact blast radius, and test selection as standardized MCP tools via standard I/O (`stdio`).
   - Seamlessly connects to **Claude Desktop**, **Cursor**, **VS Code**, and **Antigravity**.

---

## 🛠️ Complete MCP Tool Specifications

The MCP server will expose **7 core tools**. Each tool provides structured inputs, typed responses, and descriptive schemas:

### 1. `index_repository`
- **Description**: Scans, parses, and indexes a local Python repository into its isolated SQLite database.
- **Parameters**:
  - `repository_path` (`string`, required): Absolute or relative filesystem path to the Python project root.
  - `force_reindex` (`boolean`, optional, default `false`): If true, ignores cached file hashes and re-parses all files.
- **Returns**: JSON object containing:
  - `files_indexed` (`int`), `symbols_indexed` (`int`), `graph_nodes` (`int`), `graph_edges` (`int`), `changed_files` (`list[string]`).

### 2. `search_symbols`
- **Description**: Fast substring and qualified-name search for functions, classes, methods, and variables across the indexed repository.
- **Parameters**:
  - `repository_path` (`string`, required): Repository path.
  - `query` (`string`, required): Substring to match against symbol names (e.g., `"get_user"`, `"tax"`, `"OrderService"`).
- **Returns**: List of matching symbols with:
  - `id`, `name`, `qualified_name`, `kind` (`class`/`function`/`async_function`/`variable`), `file`, `start_line`, `end_line`, `signature`.

### 3. `inspect_symbol`
- **Description**: Retrieves full metadata for a specific symbol, including its declaration location, parameter signature, direct callers ($u \to \text{symbol}$), and outgoing dependencies ($\text{symbol} \to v$).
- **Parameters**:
  - `repository_path` (`string`, required): Repository path.
  - `symbol_id` (`string`, required): Unique symbol ID (e.g. `"api.routes.matches:get_user_matches"`).
- **Returns**: JSON object with:
  - `symbol`: Full symbol definition record.
  - `callers`: List of direct callers with file, line, and confidence.
  - `dependencies`: List of direct outgoing symbols called/accessed.

### 4. `analyze_impact`
- **Description**: Performs reverse graph reachability (blast radius calculation) to determine all functions, classes, and modules impacted if a symbol is modified.
- **Parameters**:
  - `repository_path` (`string`, required): Repository path.
  - `symbol_id` (`string`, required): Symbol to analyze for blast radius.
  - `max_depth` (`integer`, optional, default `10`): Maximum hops to traverse backwards.
- **Returns**: JSON object with:
  - `changed_symbol` (`string`).
  - `impacted_symbols` (`list[string]`): All downstream affected symbols.
  - `total_impacted` (`int`).
  - `risk_assessment`: Heuristic risk score (`low`, `medium`, `high`).

### 5. `find_dependency_path`
- **Description**: Finds the shortest execution or dependency call chain connecting a source symbol to a target symbol.
- **Parameters**:
  - `repository_path` (`string`, required): Repository path.
  - `source_symbol_id` (`string`, required): Origin symbol ID.
  - `target_symbol_id` (`string`, required): Destination symbol ID.
  - `cutoff` (`integer`, optional, default `5`): Maximum path depth.
- **Returns**: JSON object with:
  - `shortest_path` (`list[string]`): Ordered list of symbols forming the call chain.
  - `all_paths` (`list[list[string]]`): Alternative execution paths found within the cutoff.

### 6. `recommend_tests`
- **Description**: Identifies and ranks relevant test cases across the test suite that should be executed to verify modifications to a specific symbol.
- **Parameters**:
  - `repository_path` (`string`, required): Repository path.
  - `symbol_id` (`string`, required): Modified symbol.
  - `max_tests` (`integer`, optional, default `10`): Max test recommendations to return.
- **Returns**: JSON object with:
  - `recommended_tests`: List of test objects (`test_id`, `file`, `name`, `score`, `reasons`).

### 7. `detect_dead_code`
- **Description**: Identifies potentially unreferenced functions, classes, and variables with zero incoming calls or imports across the codebase.
- **Parameters**:
  - `repository_path` (`string`, required): Repository path.
- **Returns**: JSON object with:
  - `finding_count` (`int`).
  - `findings`: List of dead code candidates with file locations, confidence scores, and limitations.

---

## 🎨 Interactive Visual Graph Specifications

### Output: Self-Contained `graph.html`
- **Technology**: Single self-contained HTML file using CDN-loaded **Cytoscape.js** (or embedded fallback).
- **Theme & Aesthetics**: Premium dark mode theme with glassmorphic controls and responsive canvas.
- **Features**:
  1. **Color Palette by Node Kind**:
     - 🟣 Classes: `#9d4edd` (Purple)
     - 🔵 Functions / Async Functions: `#00b4d8` (Cyan / Blue)
     - 🟢 Modules: `#2ec4b6` (Teal / Green)
     - 🟡 Variables: `#ffb703` (Gold)
  2. **Interactive Controls**:
     - 🔍 **Live Search Bar**: Autocomplete search that highlights and pans to the selected node.
     - 🎚️ **Layout Selector**: Toggle between Force-Directed (`cose`), Breadthfirst (`hierarchical`), and Concentric layouts.
     - 🏷️ **Edge Filtering**: Checkboxes to toggle `defines`, `imports`, and `call` relationships on/off.
     - 📋 **Inspection Drawer**: Clicking any node opens a floating side panel displaying its signature, file, callers, and dependencies.
     - 💥 **Blast Radius Button**: Click "Trace Impact" on any node to color all its callers in crimson red.

---

## 📂 File Modifications Breakdown

| File | Purpose |
| :--- | :--- |
| **`features/visualization.py`** | *(New)* Generates the interactive Cytoscape.js HTML from SQLite edges. |
| **`mcp_server.py`** | *(Updated)* Implements standard JSON-RPC 2.0 stdio protocol with all 7 tools. |
| **`cli.py`** | *(Updated)* Adds `visualize` and `mcp` subcommands + interactive REPL menu option. |
| **`services/analysis_service.py`** | *(Updated)* Adds helper for visual export and path utilities. |
| **`tests/test_end_to_end.py`** | *(Updated)* Adds automated test cases validating visual HTML generation and MCP tool calls. |
| **`docs/mcp_setup_guide.md`** | *(New)* Copy-paste integration guide for Claude Desktop, Cursor, and VS Code. |

---

## ⏱️ Execution Milestones

- **Milestone 1**: Create `features/visualization.py` and hook it into `cli.py visualize`.
- **Milestone 2**: Implement full JSON-RPC stdio protocol and all 7 tools in `mcp_server.py`.
- **Milestone 3**: Add MCP setup guide in `docs/mcp_setup_guide.md`.
- **Milestone 4**: Update `tests/test_end_to_end.py` and execute the full test suite to guarantee 100% pass rate.
