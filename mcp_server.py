"""Model Context Protocol (MCP) Server for Codebase Intelligence.

Provides a standard JSON-RPC 2.0 stdio server compliant with the Model Context
Protocol specification, enabling AI assistants (Claude Desktop, Cursor, VS Code,
Antigravity) to query codebase intelligence graphs, symbols, impact blast radiuses,
and test recommendations.
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Callable

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cli import repo_database_path
from services.analysis_service import AnalysisService

# Setup error logging to stderr so stdout remains pure JSON-RPC
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mcp_server")


def get_service_for_repo(repo_path: str | Path) -> AnalysisService:
    """Instantiates an AnalysisService connected to the target repository's isolated database."""
    target_path = Path(repo_path).resolve()
    db_path = repo_database_path(target_path)
    return AnalysisService(db_path)


# ===========================================================================
# Tool Definitions & Handlers
# ===========================================================================

def handle_index_repository(arguments: dict[str, Any]) -> dict[str, Any]:
    repo_path = Path(arguments["repository_path"]).resolve()
    service = get_service_for_repo(repo_path)
    try:
        return service.index_local_repository(repo_path)
    finally:
        service.close()


def handle_search_symbols(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    repo_path = Path(arguments["repository_path"]).resolve()
    query = str(arguments.get("query", "")).strip()
    service = get_service_for_repo(repo_path)
    try:
        return service.find_symbol(repo_path, query)
    finally:
        service.close()


def handle_inspect_symbol(arguments: dict[str, Any]) -> dict[str, Any]:
    repo_path = Path(arguments["repository_path"]).resolve()
    symbol_id = str(arguments["symbol_id"])
    service = get_service_for_repo(repo_path)
    try:
        return service.symbol_details(repo_path, symbol_id)
    finally:
        service.close()


def handle_analyze_impact(arguments: dict[str, Any]) -> dict[str, Any]:
    repo_path = Path(arguments["repository_path"]).resolve()
    symbol_id = str(arguments["symbol_id"])
    max_depth = int(arguments.get("max_depth", 10))
    service = get_service_for_repo(repo_path)
    try:
        impact = service.impact.analyze_change(repo_path.as_posix(), [symbol_id], max_depth=max_depth)
        risk = service.risk.assess_change(repo_path.as_posix(), [symbol_id], [])
        return {
            "changed_symbol": symbol_id,
            "impacted_symbols": impact.get("impacted_symbols", []),
            "total_impacted": len(impact.get("impacted_symbols", [])),
            "impact_paths": impact.get("impact_paths", []),
            "risk_assessment": risk,
        }
    finally:
        service.close()


def handle_find_dependency_path(arguments: dict[str, Any]) -> dict[str, Any]:
    repo_path = Path(arguments["repository_path"]).resolve()
    source = str(arguments["source_symbol_id"])
    target = str(arguments["target_symbol_id"])
    cutoff = int(arguments.get("cutoff", 5))
    service = get_service_for_repo(repo_path)
    try:
        return service.graph_paths(repo_path, source=source, target=target, cutoff=cutoff)
    finally:
        service.close()


def handle_recommend_tests(arguments: dict[str, Any]) -> dict[str, Any]:
    repo_path = Path(arguments["repository_path"]).resolve()
    symbol_id = str(arguments["symbol_id"])
    max_tests = int(arguments.get("max_tests", 10))
    service = get_service_for_repo(repo_path)
    try:
        return service.test_selection.recommend_tests(
            repository=repo_path.as_posix(),
            repo_root=repo_path,
            changed_symbols=[symbol_id],
            max_tests=max_tests,
        )
    finally:
        service.close()


def handle_detect_dead_code(arguments: dict[str, Any]) -> dict[str, Any]:
    repo_path = Path(arguments["repository_path"]).resolve()
    service = get_service_for_repo(repo_path)
    try:
        return service.detect_dead_code(repo_path)
    finally:
        service.close()


TOOLS: dict[str, dict[str, Any]] = {
    "index_repository": {
        "description": "Scans, parses, and indexes a local Python repository into its isolated graph database.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository_path": {
                    "type": "string",
                    "description": "Filesystem path to the Python repository root.",
                },
                "force_reindex": {
                    "type": "boolean",
                    "description": "If true, ignores file hash cache and re-indexes all files.",
                    "default": False,
                },
            },
            "required": ["repository_path"],
        },
        "handler": handle_index_repository,
    },
    "search_symbols": {
        "description": "Finds classes, functions, methods, and variables by name substring across the codebase.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository_path": {
                    "type": "string",
                    "description": "Filesystem path to the repository.",
                },
                "query": {
                    "type": "string",
                    "description": "Symbol name or substring to search for (e.g., 'get_user', 'calculate_tax').",
                },
            },
            "required": ["repository_path", "query"],
        },
        "handler": handle_search_symbols,
    },
    "inspect_symbol": {
        "description": "Retrieves comprehensive details for a symbol: file location, signature, incoming callers, and outgoing dependencies.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository_path": {
                    "type": "string",
                    "description": "Filesystem path to the repository.",
                },
                "symbol_id": {
                    "type": "string",
                    "description": "Unique symbol identifier (e.g., 'api.routes.matches:get_user_matches').",
                },
            },
            "required": ["repository_path", "symbol_id"],
        },
        "handler": handle_inspect_symbol,
    },
    "analyze_impact": {
        "description": "Computes reverse graph reachability (blast radius) to identify all symbols that break if a given symbol is modified.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository_path": {
                    "type": "string",
                    "description": "Filesystem path to the repository.",
                },
                "symbol_id": {
                    "type": "string",
                    "description": "The symbol ID that is being changed.",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum traversal depth for predecessor hops.",
                    "default": 10,
                },
            },
            "required": ["repository_path", "symbol_id"],
        },
        "handler": handle_analyze_impact,
    },
    "find_dependency_path": {
        "description": "Finds the shortest dependency or call chain connecting a source symbol to a target symbol.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository_path": {
                    "type": "string",
                    "description": "Filesystem path to the repository.",
                },
                "source_symbol_id": {
                    "type": "string",
                    "description": "Originating caller symbol ID.",
                },
                "target_symbol_id": {
                    "type": "string",
                    "description": "Target destination symbol ID.",
                },
                "cutoff": {
                    "type": "integer",
                    "description": "Maximum path depth.",
                    "default": 5,
                },
            },
            "required": ["repository_path", "source_symbol_id", "target_symbol_id"],
        },
        "handler": handle_find_dependency_path,
    },
    "recommend_tests": {
        "description": "Recommends exact unit test cases across test files that should be run to verify changes to a symbol.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository_path": {
                    "type": "string",
                    "description": "Filesystem path to the repository.",
                },
                "symbol_id": {
                    "type": "string",
                    "description": "The modified symbol ID.",
                },
                "max_tests": {
                    "type": "integer",
                    "description": "Maximum number of test recommendations to return.",
                    "default": 10,
                },
            },
            "required": ["repository_path", "symbol_id"],
        },
        "handler": handle_recommend_tests,
    },
    "detect_dead_code": {
        "description": "Detects unreferenced functions, classes, and variables with zero incoming calls or imports across the project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository_path": {
                    "type": "string",
                    "description": "Filesystem path to the repository.",
                },
            },
            "required": ["repository_path"],
        },
        "handler": handle_detect_dead_code,
    },
}


# ===========================================================================
# JSON-RPC Dispatcher
# ===========================================================================

def dispatch_rpc_request(request: dict[str, Any]) -> dict[str, Any] | None:
    """Dispatches a single JSON-RPC 2.0 request and returns the response dictionary."""
    req_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    logger.debug("Received request: method=%s, id=%s", method, req_id)

    # 1. MCP Handshake: initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "codebase-intelligence",
                    "version": "1.0.0",
                },
            },
        }

    # 2. MCP Handshake: notifications/initialized
    if method == "notifications/initialized":
        logger.info("MCP client initialized successfully.")
        return None

    # 3. Tool Discovery: tools/list
    if method == "tools/list":
        tool_list = [
            {
                "name": name,
                "description": defn["description"],
                "inputSchema": defn["inputSchema"],
            }
            for name, defn in TOOLS.items()
        ]
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tool_list},
        }

    # 4. Tool Invocation: tools/call
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in TOOLS:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: '{tool_name}'",
                },
            }

        try:
            handler = TOOLS[tool_name]["handler"]
            output = handler(arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(output, indent=2, default=str),
                        }
                    ],
                    "isError": False,
                },
            }
        except Exception as exc:
            logger.exception("Error executing tool %s: %s", tool_name, exc)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error executing tool '{tool_name}': {exc}",
                        }
                    ],
                    "isError": True,
                },
            }

    # 5. Ping / Health check
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    # Unknown method
    if req_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: '{method}'",
            },
        }

    return None


def run_stdio_server() -> None:
    """Runs the synchronous JSON-RPC stdio event loop."""
    logger.info("Starting Codebase Intelligence MCP Server over stdio...")
    # Force UTF-8 on Windows stdout/stdin
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            request = json.loads(line)
            response = dispatch_rpc_request(request)

            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError as err:
            logger.error("JSON decode error: %s", err)
            err_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            sys.stdout.write(json.dumps(err_response) + "\n")
            sys.stdout.flush()
        except KeyboardInterrupt:
            break
        except Exception as exc:
            logger.exception("Unhandled error in MCP loop: %s", exc)


if __name__ == "__main__":
    run_stdio_server()
