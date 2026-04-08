"""Knowledge graph builder for llmwiki.

Walks every file under `wiki/` looking for `[[wikilink]]` references, builds a
node-and-edge list, writes `graph/graph.json`, and generates an interactive
`graph/graph.html` using vis.js loaded from a CDN (optional offline fallback).

Stdlib only — no networkx, no vis.js bundled.

Usage:

    python3 -m llmwiki graph              # writes graph/graph.json + graph.html
    python3 -m llmwiki graph --json       # json only
    python3 -m llmwiki graph --html       # html only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from llmwiki import REPO_ROOT

WIKI_DIR = REPO_ROOT / "wiki"
GRAPH_DIR = REPO_ROOT / "graph"

WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")


def scan_pages() -> dict[str, dict[str, Any]]:
    """Return a dict {slug: {path, type, title, out_links}}."""
    pages: dict[str, dict[str, Any]] = {}
    if not WIKI_DIR.exists():
        return pages
    for p in sorted(WIKI_DIR.rglob("*.md")):
        slug = p.stem
        if slug in ("README",):
            continue
        # Type = parent directory name when under sources/entities/concepts/etc.
        try:
            rel = p.relative_to(WIKI_DIR)
            type_ = rel.parts[0] if len(rel.parts) > 1 else "root"
        except ValueError:
            type_ = "root"
        title = slug
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        # Extract title from frontmatter if present
        title_match = re.search(r'^title:\s*"?([^"\n]+)', text, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip('"')
        # Extract wikilinks
        out_links = set(WIKILINK_RE.findall(text))
        pages[slug] = {
            "path": str(p.relative_to(REPO_ROOT)),
            "type": type_,
            "title": title,
            "out_links": out_links,
        }
    return pages


def build_graph() -> dict[str, Any]:
    pages = scan_pages()

    # Compute in-degree
    in_deg: dict[str, int] = {slug: 0 for slug in pages}
    for slug, page in pages.items():
        for target in page["out_links"]:
            if target in in_deg:
                in_deg[target] += 1

    # Nodes
    nodes = []
    for slug, page in pages.items():
        nodes.append(
            {
                "id": slug,
                "label": page["title"],
                "type": page["type"],
                "path": page["path"],
                "in_degree": in_deg.get(slug, 0),
                "out_degree": len(page["out_links"]),
            }
        )

    # Edges
    edges = []
    broken_edges = []
    for slug, page in pages.items():
        for target in page["out_links"]:
            if target in pages:
                edges.append({"source": slug, "target": target})
            else:
                broken_edges.append({"source": slug, "target": target, "broken": True})

    return {
        "nodes": nodes,
        "edges": edges,
        "broken_edges": broken_edges,
        "stats": {
            "total_pages": len(pages),
            "total_edges": len(edges),
            "broken_edges": len(broken_edges),
            "orphans": [n["id"] for n in nodes if n["in_degree"] == 0],
            "top_linked": sorted(nodes, key=lambda n: -n["in_degree"])[:5],
            "top_linking": sorted(nodes, key=lambda n: -n["out_degree"])[:5],
        },
    }


def write_json(graph: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>llmwiki knowledge graph</title>
<style>
  html, body { margin: 0; padding: 0; height: 100%; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0c0a1d; color: #e2e8f0; }
  #header { padding: 16px 24px; border-bottom: 1px solid #2d2b4a; background: #110f26; }
  #header h1 { margin: 0; font-size: 1.1rem; font-weight: 600; }
  #header .stats { font-size: 0.82rem; color: #94a3b8; margin-top: 4px; }
  #network { width: 100%; height: calc(100vh - 80px); }
  a { color: #a78bfa; }
</style>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
</head>
<body>
<div id="header">
  <h1>llmwiki — Knowledge Graph</h1>
  <div class="stats" id="stats"></div>
</div>
<div id="network"></div>
<script>
const GRAPH = __GRAPH_JSON__;
const colors = {source: '#7C3AED', entities: '#2563eb', concepts: '#059669', syntheses: '#d97706', root: '#64748b'};

document.getElementById('stats').textContent =
  `${GRAPH.stats.total_pages} pages · ${GRAPH.stats.total_edges} edges · ${GRAPH.stats.broken_edges} broken · ${GRAPH.stats.orphans.length} orphans`;

const nodes = new vis.DataSet(GRAPH.nodes.map(n => ({
  id: n.id,
  label: n.label,
  color: colors[n.type] || '#64748b',
  value: Math.max(n.in_degree, 1),
  title: `${n.type} · ${n.in_degree} in / ${n.out_degree} out`,
})));

const edges = new vis.DataSet(GRAPH.edges.map(e => ({
  from: e.source,
  to: e.target,
  arrows: 'to',
  color: {color: '#2d2b4a', opacity: 0.6},
})));

const container = document.getElementById('network');
const data = {nodes, edges};
const options = {
  nodes: {
    shape: 'dot',
    font: {color: '#e2e8f0', size: 12, face: 'system-ui'},
    scaling: {min: 8, max: 32, label: {enabled: true, min: 10, max: 18}},
  },
  edges: {smooth: {enabled: true, type: 'dynamic'}},
  physics: {
    barnesHut: {gravitationalConstant: -4000, springLength: 120, springConstant: 0.03},
    stabilization: {iterations: 200},
  },
  interaction: {hover: true, tooltipDelay: 120},
};
new vis.Network(container, data, options);
</script>
</body>
</html>
"""


def write_html(graph: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html = HTML_TEMPLATE.replace("__GRAPH_JSON__", json.dumps(graph))
    out_path.write_text(html, encoding="utf-8")


def build_and_report(write_json_flag: bool = True, write_html_flag: bool = True) -> int:
    graph = build_graph()
    if not graph["nodes"]:
        print(f"warning: no wiki pages found under {WIKI_DIR}", file=sys.stderr)
        return 1

    if write_json_flag:
        json_path = GRAPH_DIR / "graph.json"
        write_json(graph, json_path)
        print(f"  wrote {json_path.relative_to(REPO_ROOT)}")

    if write_html_flag:
        html_path = GRAPH_DIR / "graph.html"
        write_html(graph, html_path)
        print(f"  wrote {html_path.relative_to(REPO_ROOT)}")

    stats = graph["stats"]
    print()
    print(f"  {stats['total_pages']} pages · {stats['total_edges']} edges · "
          f"{stats['broken_edges']} broken · {len(stats['orphans'])} orphans")

    if stats["top_linked"]:
        print()
        print("  Top linked-to:")
        for n in stats["top_linked"]:
            if n["in_degree"] > 0:
                print(f"    {n['in_degree']:3} ← {n['id']}")

    if stats["top_linking"]:
        print()
        print("  Top linking-from:")
        for n in stats["top_linking"]:
            if n["out_degree"] > 0:
                print(f"    {n['out_degree']:3} → {n['id']}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Write graph.json only")
    parser.add_argument("--html", action="store_true", help="Write graph.html only")
    args = parser.parse_args(argv)
    # Default: write both
    if not args.json and not args.html:
        return build_and_report(True, True)
    return build_and_report(args.json, args.html)


if __name__ == "__main__":
    sys.exit(main())
