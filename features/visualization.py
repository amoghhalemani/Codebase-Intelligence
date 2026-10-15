import json
from pathlib import Path
from typing import Any

from storage.database import AnalysisDatabase


class GraphVisualizer:
    """Generates an interactive, zero-dependency HTML graph visualization using Cytoscape.js."""

    def __init__(self, database: AnalysisDatabase, repository: str):
        self.database = database
        self.repository = repository

    def build_elements(self, max_nodes: int = 1500) -> dict[str, list[dict[str, Any]]]:
        """Constructs Cytoscape.js node and edge definitions from the SQLite database."""
        symbols = self.database.all_symbols(self.repository)
        edges = self.database.all_edges(self.repository)

        nodes: list[dict[str, Any]] = []
        cy_edges: list[dict[str, Any]] = []
        node_ids: set[str] = set()

        # 1. Add symbol nodes
        for sym in symbols[:max_nodes]:
            node_id = sym["id"]
            node_ids.add(node_id)
            kind = sym.get("kind", "symbol")
            nodes.append(
                {
                    "data": {
                        "id": node_id,
                        "label": sym.get("name") or node_id.split(":")[-1],
                        "qualified_name": sym.get("qualified_name", sym.get("name", "")),
                        "kind": kind,
                        "file": sym.get("file", ""),
                        "module": sym.get("module", ""),
                        "start_line": sym.get("start_line", 0),
                        "end_line": sym.get("end_line", 0),
                        "signature": sym.get("signature") or "",
                    }
                }
            )

        # 2. Add edges connecting existing nodes
        for idx, edge in enumerate(edges):
            source = edge["source_id"]
            target = edge["target_id"]

            # If module node is missing from symbols, add it dynamically
            for nid in (source, target):
                if nid not in node_ids:
                    node_ids.add(nid)
                    kind = "module" if nid.endswith(":<module>") else "symbol"
                    nodes.append(
                        {
                            "data": {
                                "id": nid,
                                "label": nid.split(":")[-1].replace("<module>", nid.split(":")[0].split(".")[-1]),
                                "qualified_name": nid,
                                "kind": kind,
                                "file": "",
                                "module": nid.split(":")[0],
                                "start_line": 0,
                                "end_line": 0,
                                "signature": "",
                            }
                        }
                    )

            cy_edges.append(
                {
                    "data": {
                        "id": f"edge_{idx}",
                        "source": source,
                        "target": target,
                        "relationship": edge.get("relationship", "depends_on"),
                        "confidence": edge.get("confidence", 1.0),
                    }
                }
            )

        return {"nodes": nodes, "edges": cy_edges}

    def generate_html(self, title: str | None = None) -> str:
        """Generates the full self-contained HTML page string."""
        title = title or f"Codebase Graph — {Path(self.repository).name}"
        elements = self.build_elements()
        elements_json = json.dumps(elements)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: #0b0f19;
      color: #e2e8f0;
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    /* Top Header */
    header {{
      background: #111827;
      border-bottom: 1px solid #1f2937;
      padding: 12px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      z-index: 10;
    }}
    .header-title {{
      font-size: 16px;
      font-weight: 700;
      color: #38bdf8;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .stats-pill {{
      font-size: 12px;
      background: #1f2937;
      color: #94a3b8;
      padding: 4px 10px;
      border-radius: 9999px;
      border: 1px solid #374151;
    }}
    .controls-bar {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .search-input {{
      background: #1f2937;
      border: 1px solid #374151;
      color: #f8fafc;
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 13px;
      width: 240px;
      outline: none;
      transition: border-color 0.2s;
    }}
    .search-input:focus {{
      border-color: #38bdf8;
    }}
    select, button {{
      background: #1f2937;
      border: 1px solid #374151;
      color: #e2e8f0;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 13px;
      cursor: pointer;
      outline: none;
      transition: background 0.2s, border-color 0.2s;
    }}
    select:hover, button:hover {{
      background: #374151;
      border-color: #4b5563;
    }}
    button.btn-primary {{
      background: #0284c7;
      border-color: #0369a1;
      color: #ffffff;
      font-weight: 500;
    }}
    button.btn-primary:hover {{
      background: #0369a1;
    }}

    /* Main Area */
    .main-container {{
      flex: 1;
      position: relative;
      display: flex;
    }}
    #cy {{
      flex: 1;
      height: 100%;
      background: radial-gradient(circle, #131b2e 0%, #0b0f19 100%);
    }}

    /* Sidebar Drawer */
    #sidebar {{
      width: 340px;
      background: #111827;
      border-left: 1px solid #1f2937;
      padding: 20px;
      overflow-y: auto;
      display: none;
      flex-direction: column;
      gap: 14px;
      box-shadow: -4px 0 20px rgba(0,0,0,0.5);
      z-index: 20;
    }}
    .sidebar-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 1px solid #1f2937;
      padding-bottom: 10px;
    }}
    .badge {{
      display: inline-block;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      padding: 2px 8px;
      border-radius: 4px;
      margin-bottom: 6px;
    }}
    .badge.function {{ background: #0369a1; color: #bae6fd; }}
    .badge.async_function {{ background: #0284c7; color: #e0f2fe; }}
    .badge.class {{ background: #6b21a8; color: #f3e8ff; }}
    .badge.module {{ background: #065f46; color: #d1fae5; }}
    .badge.variable {{ background: #854d0e; color: #fef08a; }}

    .property-label {{
      font-size: 11px;
      font-weight: 600;
      color: #64748b;
      text-transform: uppercase;
      margin-bottom: 2px;
    }}
    .property-value {{
      font-size: 13px;
      color: #cbd5e1;
      word-break: break-all;
      background: #1f2937;
      padding: 6px 10px;
      border-radius: 4px;
      font-family: monospace;
    }}
    .item-list {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      max-height: 140px;
      overflow-y: auto;
    }}
    .list-item {{
      background: #1f2937;
      padding: 6px 8px;
      border-radius: 4px;
      font-size: 12px;
      cursor: pointer;
      color: #93c5fd;
      border: 1px solid transparent;
    }}
    .list-item:hover {{
      border-color: #3b82f6;
      background: #252f44;
    }}

    /* Legend Overlay */
    .legend {{
      position: absolute;
      bottom: 20px;
      left: 20px;
      background: rgba(17, 24, 39, 0.85);
      backdrop-filter: blur(8px);
      border: 1px solid #374151;
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      z-index: 5;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .legend-dot {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-title">
      <span>🕸️</span>
      <span>{title}</span>
      <span class="stats-pill" id="stats-pill">Loading graph...</span>
    </div>

    <div class="controls-bar">
      <input type="text" id="search-box" class="search-input" placeholder="🔍 Search symbol (e.g. get_user)..." />
      <select id="layout-select">
        <option value="cose">Force-Directed Layout</option>
        <option value="breadthfirst">Hierarchical Tree</option>
        <option value="concentric">Concentric Rings</option>
        <option value="circle">Circular Layout</option>
      </select>
      <button id="btn-fit">Fit View</button>
      <button id="btn-reset" class="btn-primary">Reset Filters</button>
    </div>
  </header>

  <div class="main-container">
    <div id="cy"></div>

    <div class="legend">
      <div style="font-weight: 600; color: #94a3b8; margin-bottom: 2px;">Legend</div>
      <div class="legend-item"><div class="legend-dot" style="background: #0284c7;"></div> Function / Async</div>
      <div class="legend-item"><div class="legend-dot" style="background: #9333ea;"></div> Class</div>
      <div class="legend-item"><div class="legend-dot" style="background: #10b981;"></div> Module</div>
      <div class="legend-item"><div class="legend-dot" style="background: #eab308;"></div> Variable</div>
      <div class="legend-item"><div class="legend-dot" style="background: #ef4444;"></div> Impacted (Blast Radius)</div>
    </div>

    <div id="sidebar">
      <div class="sidebar-header">
        <div>
          <span id="side-badge" class="badge function">Function</span>
          <h3 id="side-name" style="font-size: 16px; color: #f8fafc;">Symbol Name</h3>
        </div>
        <button id="side-close" style="padding: 2px 8px; font-size: 11px;">✕</button>
      </div>

      <div>
        <div class="property-label">ID</div>
        <div class="property-value" id="side-id">-</div>
      </div>

      <div>
        <div class="property-label">File & Lines</div>
        <div class="property-value" id="side-location">-</div>
      </div>

      <div id="side-sig-container">
        <div class="property-label">Signature</div>
        <div class="property-value" id="side-signature">-</div>
      </div>

      <button id="btn-blast-radius" class="btn-primary" style="margin-top: 4px;">💥 Highlight Blast Radius</button>

      <div>
        <div class="property-label">Direct Callers (<span id="side-callers-count">0</span>)</div>
        <div class="item-list" id="side-callers"></div>
      </div>

      <div>
        <div class="property-label">Dependencies Called (<span id="side-deps-count">0</span>)</div>
        <div class="item-list" id="side-deps"></div>
      </div>
    </div>
  </div>

  <script>
    const graphData = {elements_json};

    document.getElementById('stats-pill').innerText = 
      `${{graphData.nodes.length}} Nodes • ${{graphData.edges.length}} Edges`;

    const cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: graphData,
      style: [
        {{
          selector: 'node',
          style: {{
            'label': 'data(label)',
            'color': '#f1f5f9',
            'font-size': '11px',
            'font-family': 'sans-serif',
            'text-valign': 'bottom',
            'text-margin-y': 5,
            'background-color': '#0284c7',
            'width': 22,
            'height': 22,
            'border-width': 2,
            'border-color': '#0369a1',
            'transition-property': 'background-color, border-color, width, height',
            'transition-duration': '0.2s'
          }}
        }},
        {{
          selector: 'node[kind = "class"]',
          style: {{
            'background-color': '#9333ea',
            'border-color': '#7e22ce',
            'shape': 'round-rectangle',
            'width': 28,
            'height': 28
          }}
        }},
        {{
          selector: 'node[kind = "module"]',
          style: {{
            'background-color': '#10b981',
            'border-color': '#059669',
            'shape': 'hexagon',
            'width': 32,
            'height': 32
          }}
        }},
        {{
          selector: 'node[kind = "variable"]',
          style: {{
            'background-color': '#eab308',
            'border-color': '#ca8a04',
            'width': 16,
            'height': 16
          }}
        }},
        {{
          selector: 'node:selected',
          style: {{
            'border-color': '#38bdf8',
            'border-width': 4,
            'width': 34,
            'height': 34
          }}
        }},
        {{
          selector: 'node.highlighted',
          style: {{
            'border-color': '#facc15',
            'border-width': 4
          }}
        }},
        {{
          selector: 'node.impacted',
          style: {{
            'background-color': '#ef4444',
            'border-color': '#b91c1c',
            'border-width': 4
          }}
        }},
        {{
          selector: 'edge',
          style: {{
            'width': 1.5,
            'line-color': '#475569',
            'target-arrow-color': '#475569',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 0.8,
            'opacity': 0.6
          }}
        }},
        {{
          selector: 'edge[relationship = "call"]',
          style: {{
            'line-color': '#38bdf8',
            'target-arrow-color': '#38bdf8',
            'opacity': 0.8
          }}
        }},
        {{
          selector: 'edge[relationship = "imports"]',
          style: {{
            'line-color': '#10b981',
            'target-arrow-color': '#10b981',
            'line-style': 'dashed'
          }}
        }},
        {{
          selector: 'edge[relationship = "defines"]',
          style: {{
            'line-color': '#64748b',
            'target-arrow-color': '#64748b',
            'opacity': 0.3
          }}
        }},
        {{
          selector: 'edge.highlighted',
          style: {{
            'line-color': '#facc15',
            'target-arrow-color': '#facc15',
            'width': 3,
            'opacity': 1.0
          }}
        }}
      ],
      layout: {{
        name: 'cose',
        animate: false,
        nodeDimensionsIncludeLabels: true,
        idealEdgeLength: 100,
        nodeOverlap: 20
      }}
    }});

    // Selection & Sidebar
    let activeNode = null;

    cy.on('tap', 'node', function(evt) {{
      activeNode = evt.target;
      const data = activeNode.data();

      document.getElementById('sidebar').style.display = 'flex';
      document.getElementById('side-name').innerText = data.label;
      document.getElementById('side-id').innerText = data.id;
      document.getElementById('side-location').innerText = data.file ? `${{data.file}}:${{data.start_line}}-${{data.end_line}}` : 'Global';
      
      const badge = document.getElementById('side-badge');
      badge.className = `badge ${{data.kind}}`;
      badge.innerText = data.kind;

      const sigContainer = document.getElementById('side-sig-container');
      if (data.signature) {{
        sigContainer.style.display = 'block';
        document.getElementById('side-signature').innerText = data.signature;
      }} else {{
        sigContainer.style.display = 'none';
      }}

      // Incoming Callers (Predecessors)
      const callersList = document.getElementById('side-callers');
      callersList.innerHTML = '';
      const incoming = activeNode.incomers('edge[relationship = "call"]').sources();
      document.getElementById('side-callers-count').innerText = incoming.length;
      incoming.forEach(node => {{
        const item = document.createElement('div');
        item.className = 'list-item';
        item.innerText = node.data('label');
        item.onclick = () => {{ cy.center(node); node.select(); }};
        callersList.appendChild(item);
      }});

      // Outgoing Dependencies (Successors)
      const depsList = document.getElementById('side-deps');
      depsList.innerHTML = '';
      const outgoing = activeNode.outgoers('edge[relationship = "call"]').targets();
      document.getElementById('side-deps-count').innerText = outgoing.length;
      outgoing.forEach(node => {{
        const item = document.createElement('div');
        item.className = 'list-item';
        item.innerText = node.data('label');
        item.onclick = () => {{ cy.center(node); node.select(); }};
        depsList.appendChild(item);
      }});

      // Highlight direct neighbors
      cy.elements().removeClass('highlighted');
      activeNode.addClass('highlighted');
      activeNode.connectedEdges().addClass('highlighted');
    }});

    // Blast Radius Button
    document.getElementById('btn-blast-radius').onclick = function() {{
      if (!activeNode) return;
      cy.elements().removeClass('impacted');
      
      // BFS backwards along incoming edges
      const visited = new Set();
      const queue = [activeNode];
      visited.add(activeNode.id());

      while (queue.length > 0) {{
        const curr = queue.shift();
        curr.addClass('impacted');
        curr.incomers('edge').sources().forEach(neighbor => {{
          if (!visited.has(neighbor.id())) {{
            visited.add(neighbor.id());
            queue.push(neighbor);
          }}
        }});
      }}
    }};

    document.getElementById('side-close').onclick = () => {{
      document.getElementById('sidebar').style.display = 'none';
      cy.elements().removeClass('highlighted');
      activeNode = null;
    }};

    // Search bar
    document.getElementById('search-box').addEventListener('input', function(e) {{
      const query = e.target.value.trim().toLowerCase();
      if (!query) {{
        cy.elements().removeClass('highlighted');
        return;
      }}
      const matches = cy.nodes().filter(n => 
        (n.data('label') || '').toLowerCase().includes(query) ||
        (n.data('id') || '').toLowerCase().includes(query)
      );
      cy.elements().removeClass('highlighted');
      matches.addClass('highlighted');
      if (matches.length > 0) {{
        cy.center(matches[0]);
      }}
    }});

    // Layout Selector
    document.getElementById('layout-select').onchange = function(e) {{
      cy.layout({{ name: e.target.value, animate: true }}).run();
    }};

    // Controls
    document.getElementById('btn-fit').onclick = () => cy.fit();
    document.getElementById('btn-reset').onclick = () => {{
      cy.elements().removeClass('highlighted impacted');
      document.getElementById('sidebar').style.display = 'none';
      document.getElementById('search-box').value = '';
      cy.fit();
    }};
  </script>
</body>
</html>"""

    def render_to_file(self, output_path: Path) -> Path:
        """Saves the interactive visualization HTML to disk and returns the resolved path."""
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        html_content = self.generate_html()
        output_path.write_text(html_content, encoding="utf-8")
        return output_path
