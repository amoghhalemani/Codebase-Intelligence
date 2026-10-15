"""Dedicated Interactive Visualizer Server for CodeMap Demonstrations.

Serves an interactive web dashboard with:
- Full interactive dependency graph
- One-click Blast Radius / Impact analysis visualization
- One-click Dead Code detection and highlighting
- Smart Test Selection visualization
- Node inspection panel (callers, dependencies, source lines)
"""

import json
import mimetypes
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cli import repo_database_path
from services.analysis_service import AnalysisService

DASHBOARD_DIR = Path(__file__).resolve().parent
PORT = 5050


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress noisy logs
        pass

    def _send_json(self, data: dict | list, status: int = 200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _get_service(self, repo_param: str) -> tuple[AnalysisService, Path]:
        repo_path = Path(repo_param)
        if not repo_path.is_absolute():
            repo_path = (PROJECT_ROOT / repo_path).resolve()
        db_path = repo_database_path(repo_path)
        return AnalysisService(db_path), repo_path

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        params = parse_qs(parsed_url.query)

        # -------------------------------------------------------------
        # API: /api/graph
        # -------------------------------------------------------------
        if path == "/api/graph":
            repo_param = params.get("repo", ["demo_project"])[0]
            try:
                service, repo_path = self._get_service(repo_param)
                repo_str = repo_path.as_posix()
                symbols = service.database.all_symbols(repo_str)
                edges = service.database.all_edges(repo_str)

                nodes = []
                node_ids = set()
                for s in symbols:
                    nid = s["id"]
                    node_ids.add(nid)
                    kind = s.get("kind", "symbol")

                    raw_name = s.get("name") or ""
                    if raw_name == "<module>" or nid.endswith(":<module>"):
                        file_name = s.get("file", "").split("/")[-1] if s.get("file") else ""
                        mod_name = s.get("module") or nid.split(":")[0]
                        label = file_name or mod_name.split(".")[-1] or mod_name
                        kind = "module"
                    else:
                        label = raw_name or nid.split(":")[-1]

                    nodes.append(
                        {
                            "data": {
                                "id": nid,
                                "label": label,
                                "qualified_name": s.get("qualified_name", s.get("name")),
                                "kind": kind,
                                "file": s.get("file", ""),
                                "module": s.get("module", ""),
                                "start_line": s.get("start_line", 0),
                                "end_line": s.get("end_line", 0),
                                "signature": s.get("signature") or "",
                            }
                        }
                    )

                cy_edges = []
                for idx, e in enumerate(edges):
                    src = e["source_id"]
                    tgt = e["target_id"]
                    # Add module node if missing
                    for n in (src, tgt):
                        if n not in node_ids:
                            node_ids.add(n)
                            kind = "module" if n.endswith(":<module>") else "symbol"
                            mod_name = n.split(":")[0].split(".")[-1]
                            nodes.append(
                                {
                                    "data": {
                                        "id": n,
                                        "label": mod_name if n.endswith(":<module>") else n.split(":")[-1],
                                        "qualified_name": n,
                                        "kind": kind,
                                        "file": "",
                                        "module": n.split(":")[0],
                                        "start_line": 0,
                                        "end_line": 0,
                                        "signature": "",
                                    }
                                }
                            )
                    cy_edges.append(
                        {
                            "data": {
                                "id": f"e{idx}",
                                "source": src,
                                "target": tgt,
                                "relationship": e.get("relationship", "call"),
                            }
                        }
                    )

                service.close()
                self._send_json({"nodes": nodes, "edges": cy_edges, "repo": str(repo_path)})
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return

        # -------------------------------------------------------------
        # API: /api/impact
        # -------------------------------------------------------------
        if path == "/api/impact":
            repo_param = params.get("repo", ["demo_project"])[0]
            symbol_id = params.get("symbol", ["tax_calculator:calculate_vat"])[0]
            try:
                service, repo_path = self._get_service(repo_param)
                res = service.analyze_change(repo_path, [symbol_id])
                service.close()
                self._send_json(res)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return

        # -------------------------------------------------------------
        # API: /api/dead-code
        # -------------------------------------------------------------
        if path == "/api/dead-code":
            repo_param = params.get("repo", ["demo_project"])[0]
            try:
                service, repo_path = self._get_service(repo_param)
                res = service.detect_dead_code(repo_path)
                service.close()
                self._send_json(res)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return

        # -------------------------------------------------------------
        # API: /api/tests
        # -------------------------------------------------------------
        if path == "/api/tests":
            repo_param = params.get("repo", ["demo_project"])[0]
            symbol_id = params.get("symbol", ["tax_calculator:calculate_vat"])[0]
            try:
                service, repo_path = self._get_service(repo_param)
                res = service.test_selection.recommend_tests(
                    repo_path.as_posix(),
                    repo_path.resolve(),
                    [symbol_id],
                )
                service.close()
                self._send_json(res)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return

        # -------------------------------------------------------------
        # API: /api/symbols
        # -------------------------------------------------------------
        if path == "/api/symbols":
            repo_param = params.get("repo", ["demo_project"])[0]
            try:
                service, repo_path = self._get_service(repo_param)
                symbols = service.database.all_symbols(repo_path.as_posix())
                service.close()
                self._send_json(symbols)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return

        # -------------------------------------------------------------
        # Static files (index.html, etc.)
        # -------------------------------------------------------------
        if path == "/" or path == "/index.html":
            file_path = DASHBOARD_DIR / "index.html"
        else:
            file_path = DASHBOARD_DIR / path.lstrip("/")

        if file_path.is_file():
            mime_type, _ = mimetypes.guess_type(str(file_path))
            content = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime_type or "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.end_headers()


def run_server(port: int = PORT, open_browser: bool = False):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"\n=======================================================")
    print(f"[+] CodeMap Visualizer Dashboard running at:")
    print(f"    --> {url}")
    print(f"=======================================================")
    print(f"[*] Serving demo_project with Blast Radius & Dead Code UI")
    print(f"[*] Press Ctrl+C to stop.")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Stopping server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    should_open = "--no-browser" not in sys.argv
    run_server(open_browser=should_open)
