---
description: Rule to enforce using the Codebase Intelligence MCP server for queries and context
globs: "*"
always_on: true
---

# Codebase Intelligence MCP Rule

When investigating code, exploring symbols, tracing dependencies, calculating blast radius, or finding tests in this repository:
1. **Never manually scan or grep arbitrarily through folders**.
2. **Query the project's Codebase Intelligence MCP server**:
   - `search_symbols` for discovering functions, classes, and variables.
   - `inspect_symbol` for inspecting definition, callers, and dependencies.
   - `analyze_impact` for determining downstream impact and blast radius of any changes.
   - `find_dependency_path` for tracing call graphs between symbols.
   - `recommend_tests` for identifying affected test suites.
   - `detect_dead_code` for identifying unused code.
3. **Walk through the MCP calls and results**: Explain to the user which tools were called, the symbol IDs queried, and the insights returned before making any modifications.
