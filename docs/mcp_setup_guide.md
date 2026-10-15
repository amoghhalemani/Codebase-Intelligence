# 🔌 MCP Server Setup Guide

Connect **Codebase Intelligence** to **Claude Desktop**, **Cursor**, **VS Code**, or any Model Context Protocol (MCP) compatible AI assistant.

---

## ⚡ Quick Test via Command Line

You can test that the MCP server is working by running:
```powershell
python mcp_server.py
```
Or via the CLI:
```powershell
python cli.py mcp
```
The server speaks standard JSON-RPC 2.0 over standard input/output (`stdio`).

---

## 🤖 1. Connecting to Claude Desktop

1. Open your Claude Desktop configuration file:
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux:** `~/.config/Claude/claude_desktop_config.json`

2. Add `codebase-intelligence` under `mcpServers`:

```json
{
  "mcpServers": {
    "codebase-intelligence": {
      "command": "D:\\code\\Golang\\Codebase-Intelligence\\.venv\\Scripts\\python.exe",
      "args": [
        "D:\\code\\Golang\\Codebase-Intelligence\\mcp_server.py"
      ]
    }
  }
}
```

3. Restart Claude Desktop.
4. Look for the 🔌 hammer icon in Claude — you will see all **7 tools** available:
   - `index_repository`
   - `search_symbols`
   - `inspect_symbol`
   - `analyze_impact`
   - `find_dependency_path`
   - `recommend_tests`
   - `detect_dead_code`

---

## 💻 2. Connecting to Cursor

1. Open **Cursor Settings** $\rightarrow$ **Features** $\rightarrow$ **MCP**.
2. Click **+ Add New MCP Server**.
3. Fill in:
   - **Name:** `codebase-intelligence`
   - **Type:** `command`
   - **Command:** `D:\code\Golang\Codebase-Intelligence\.venv\Scripts\python.exe D:\code\Golang\Codebase-Intelligence\mcp_server.py`
4. Click Save. Cursor Composer and Chat can now automatically call graph analysis tools!

---

## 💬 3. Example Prompts You Can Ask Claude / Cursor

Once connected, you can ask natural language questions:

- *"Index my project at `D:/code/Golang/Belong/belong-api`"*
- *"Search for any symbol matching `matches` in `belong-api`"*
- *"Inspect `api.routes.matches:get_user_matches`. Who calls it and what does it depend on?"*
- *"If I change `calculate_vat` in `tax.py`, what other functions across the project will break? Give me the blast radius."*
- *"Show me the call chain from `OrderService.place_order` to `calculate_vat`."*
- *"Which tests should I run after editing `billing.py`?"*
- *"Are there any dead or unreferenced functions in my repository?"*
