"""Full MCP server for llmwiki (v0.2).

Exposes llmwiki operations as Model Context Protocol tools that any MCP
client (Claude Desktop, Claude Code, Codex, Cline, Cursor, ChatGPT desktop)
can call directly via stdio.

v0.2 tool surface (6 production tools):

- `wiki_query(question)` — search the wiki's index and return relevant
  content from the matching pages
- `wiki_search(term)` — raw grep over the whole wiki (no synthesis)
- `wiki_list_sources(project?)` — list raw source files, optionally filtered
- `wiki_read_page(path)` — return the full content of a single wiki page
- `wiki_lint()` — run the lint workflow and return the report
- `wiki_sync(dry_run?)` — trigger a converter sync

Protocol: Model Context Protocol, stdio transport, JSON-RPC 2.0.
Reference: https://modelcontextprotocol.io/

Ships as stdlib-only Python — no MCP SDK dependency.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from llmwiki import REPO_ROOT, __version__


SERVER_INFO = {
    "name": "llmwiki",
    "version": __version__,
}

PROTOCOL_VERSION = "2024-11-05"

# ─── Tool definitions ─────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "wiki_query",
        "description": (
            "Search the llmwiki by keyword and return relevant page content. "
            "Reads wiki/index.md, wiki/overview.md, and any matching pages. "
            "Use for questions like 'what did I decide about X' or 'what's my "
            "preferred approach to Y'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Natural-language question or keyword(s) to search for.",
                },
                "max_pages": {
                    "type": "integer",
                    "description": "Maximum pages to return (default 5).",
                    "default": 5,
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "wiki_search",
        "description": (
            "Raw grep search across wiki/ and raw/sessions/. No synthesis — "
            "just returns file:line matches. Use when you want the literal "
            "text without LLM interpretation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "term": {
                    "type": "string",
                    "description": "Search term (literal substring match).",
                },
                "include_raw": {
                    "type": "boolean",
                    "description": "Also search raw/sessions/ (default false — only wiki/).",
                    "default": False,
                },
            },
            "required": ["term"],
        },
    },
    {
        "name": "wiki_list_sources",
        "description": "List all raw source markdown files under raw/sessions/ with their metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Optional project slug to filter by.",
                },
            },
        },
    },
    {
        "name": "wiki_read_page",
        "description": (
            "Return the full content of one wiki or raw page. Path is relative "
            "to the repo root (e.g. 'wiki/sources/clever-munching-parnas.md')."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Page path relative to the repo root.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "wiki_lint",
        "description": (
            "Run the lint workflow over the wiki: find orphan pages, broken "
            "wikilinks, contradictions, and stale summaries. Returns a JSON "
            "report."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "wiki_sync",
        "description": (
            "Run the session-transcript converter to pull in any new sessions "
            "from the agent's session store into raw/sessions/. Returns the "
            "converter's summary line."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, preview without writing.",
                    "default": False,
                },
            },
        },
    },
    {
        "name": "wiki_export",
        "description": (
            "Dump the entire wiki in a machine-readable format for AI agents. "
            "Returns the requested format as text. Use 'llms-txt' for the "
            "short llms.txt index, 'llms-full-txt' for the flattened content "
            "dump, 'jsonld' for the schema.org JSON-LD graph, 'sitemap' for "
            "the sitemap.xml, or 'list' to list every available export."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["llms-txt", "llms-full-txt", "jsonld", "sitemap", "rss", "manifest", "list"],
                    "description": "Which export format to return.",
                },
            },
            "required": ["format"],
        },
    },
]


# ─── Tool implementations ─────────────────────────────────────────────────


def _safe_path(rel: str) -> Path | None:
    """Resolve a user-supplied path relative to REPO_ROOT and refuse if it
    escapes the repo (path traversal guard)."""
    if not rel:
        return None
    p = (REPO_ROOT / rel).resolve()
    try:
        p.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return None
    return p


def tool_wiki_query(args: dict[str, Any]) -> dict[str, Any]:
    question = (args.get("question") or "").strip()
    max_pages = int(args.get("max_pages", 5))
    if not question:
        return _err("question is required")

    wiki = REPO_ROOT / "wiki"
    if not wiki.exists():
        return _ok(
            "wiki/ does not exist yet — run `llmwiki init` and `/wiki-sync` first"
        )

    # Read the index + overview
    index = (wiki / "index.md").read_text(encoding="utf-8") if (wiki / "index.md").exists() else ""
    overview = (wiki / "overview.md").read_text(encoding="utf-8") if (wiki / "overview.md").exists() else ""

    # Scan every .md under wiki/ for matches on title + body
    query_lower = question.lower()
    tokens = [t for t in re.split(r"\W+", query_lower) if t]
    matches: list[tuple[int, Path, str]] = []
    for page in wiki.rglob("*.md"):
        try:
            content = page.read_text(encoding="utf-8")
        except OSError:
            continue
        content_lower = content.lower()
        score = 0
        if query_lower in content_lower:
            score += 50
        score += sum(10 for t in tokens if t in content_lower)
        # Title bonus
        title_match = re.search(r'^title:\s*"?([^"\n]+)', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).lower()
            if query_lower in title:
                score += 100
            score += sum(20 for t in tokens if t in title)
        if score > 0:
            snippet = _extract_snippet(content, tokens, max_chars=400)
            matches.append((score, page, snippet))

    matches.sort(key=lambda x: -x[0])
    top = matches[:max_pages]

    out = [f"# Query: {question}\n"]
    if not top:
        out.append("No matching pages found.\n")
        out.append("\n## wiki/index.md\n\n" + index[:1500])
    else:
        for score, page, snippet in top:
            rel = page.relative_to(REPO_ROOT)
            out.append(f"## `{rel}` (score: {score})\n")
            out.append(snippet)
            out.append("")
    out.append("---\n")
    out.append("## Overview context\n")
    out.append(overview[:1000] if overview else "(no overview.md)")

    return _ok("\n".join(out))


def _extract_snippet(content: str, tokens: list[str], max_chars: int = 400) -> str:
    """Return a ±max_chars window around the first token match, or the first
    max_chars of the body if no match."""
    content_lower = content.lower()
    for t in tokens:
        idx = content_lower.find(t)
        if idx >= 0:
            start = max(0, idx - max_chars // 2)
            end = min(len(content), idx + max_chars // 2)
            prefix = "…" if start > 0 else ""
            suffix = "…" if end < len(content) else ""
            return prefix + content[start:end] + suffix
    return content[:max_chars] + ("…" if len(content) > max_chars else "")


def tool_wiki_search(args: dict[str, Any]) -> dict[str, Any]:
    term = (args.get("term") or "").strip()
    include_raw = bool(args.get("include_raw", False))
    if not term:
        return _err("term is required")

    roots = [REPO_ROOT / "wiki"]
    if include_raw:
        roots.append(REPO_ROOT / "raw" / "sessions")

    hits: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.md"):
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                if term in line or term.lower() in line.lower():
                    hits.append(
                        {
                            "path": str(p.relative_to(REPO_ROOT)),
                            "line": i,
                            "text": line.strip()[:200],
                        }
                    )
                    if len(hits) >= 200:
                        break
            if len(hits) >= 200:
                break
    return _ok(json.dumps({"term": term, "matches": hits, "truncated": len(hits) >= 200}, indent=2))


def tool_wiki_list_sources(args: dict[str, Any]) -> dict[str, Any]:
    project_filter = args.get("project")
    raw_sessions = REPO_ROOT / "raw" / "sessions"
    if not raw_sessions.exists():
        return _ok(json.dumps([], indent=2))
    out = []
    for p in sorted(raw_sessions.rglob("*.md")):
        project = p.parent.name
        if project_filter and project_filter not in project:
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        out.append(
            {
                "path": str(p.relative_to(REPO_ROOT)),
                "project": project,
                "filename": p.name,
                "size_bytes": size,
            }
        )
    return _ok(json.dumps(out, indent=2))


def tool_wiki_read_page(args: dict[str, Any]) -> dict[str, Any]:
    rel = args.get("path")
    if not rel:
        return _err("path is required")
    p = _safe_path(rel)
    if p is None:
        return _err(f"path escapes repo root: {rel!r}")
    if not p.exists():
        return _err(f"path does not exist: {rel}")
    if not p.is_file():
        return _err(f"path is not a file: {rel}")
    try:
        content = p.read_text(encoding="utf-8")
    except OSError as e:
        return _err(f"read error: {e}")
    return _ok(content)


def tool_wiki_lint(args: dict[str, Any]) -> dict[str, Any]:
    """Run a basic lint pass over wiki/ and return a JSON report.

    This is the programmatic equivalent of the /wiki-lint slash command — but
    without any LLM synthesis. It just walks the files and reports structural
    issues.
    """
    wiki = REPO_ROOT / "wiki"
    if not wiki.exists():
        return _err("wiki/ does not exist")

    # 1. Collect all pages and their slugs
    pages: dict[str, Path] = {}
    for p in wiki.rglob("*.md"):
        slug = p.stem
        pages[slug] = p

    # 2. Collect all wikilinks
    wikilink_re = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
    out_links: dict[str, set[str]] = {}
    all_links: set[str] = set()
    for slug, path in pages.items():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        links = set(wikilink_re.findall(text))
        out_links[slug] = links
        all_links.update(links)

    # 3. Compute in-degree
    in_deg: dict[str, int] = {slug: 0 for slug in pages}
    for slug, links in out_links.items():
        for target in links:
            if target in in_deg:
                in_deg[target] += 1

    orphans = [slug for slug, d in in_deg.items() if d == 0 and slug not in ("index", "overview", "log")]
    broken_links: list[dict[str, str]] = []
    for slug, links in out_links.items():
        for target in links:
            if target not in pages:
                broken_links.append({"page": slug, "broken_link": target})

    report = {
        "total_pages": len(pages),
        "orphans": orphans[:50],
        "orphan_count": len(orphans),
        "broken_links": broken_links[:50],
        "broken_link_count": len(broken_links),
    }
    return _ok(json.dumps(report, indent=2))


def tool_wiki_sync(args: dict[str, Any]) -> dict[str, Any]:
    dry_run = bool(args.get("dry_run", False))
    cmd = [sys.executable, "-m", "llmwiki", "sync"]
    if dry_run:
        cmd.append("--dry-run")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=120,
        )
    except subprocess.TimeoutExpired:
        return _err("sync timed out after 120s")
    except Exception as e:
        return _err(f"sync failed: {e}")
    output = result.stdout + (f"\n--- stderr ---\n{result.stderr}" if result.stderr else "")
    return _ok(output or "(no output)")


def tool_wiki_export(args: dict[str, Any]) -> dict[str, Any]:
    """Return one of the AI-consumable export files (v0.4)."""
    fmt = args.get("format")
    site_dir = REPO_ROOT / "site"

    if fmt == "list":
        candidates = [
            "llms.txt",
            "llms-full.txt",
            "graph.jsonld",
            "sitemap.xml",
            "rss.xml",
            "robots.txt",
            "ai-readme.md",
            "manifest.json",
            "search-index.json",
        ]
        out = []
        for name in candidates:
            p = site_dir / name
            if p.exists():
                out.append({"format": name, "size_bytes": p.stat().st_size, "url": name})
        return _ok(json.dumps(out, indent=2))

    mapping = {
        "llms-txt": "llms.txt",
        "llms-full-txt": "llms-full.txt",
        "jsonld": "graph.jsonld",
        "sitemap": "sitemap.xml",
        "rss": "rss.xml",
        "manifest": "manifest.json",
    }
    filename = mapping.get(fmt)
    if not filename:
        return _err(f"unknown format: {fmt}. Valid: {sorted(mapping.keys())} + 'list'")
    p = site_dir / filename
    if not p.exists():
        return _err(f"{filename} does not exist. Run 'llmwiki build' first.")
    try:
        content = p.read_text(encoding="utf-8")
    except OSError as e:
        return _err(f"read error: {e}")
    # Cap response size at 200 KB to keep MCP responses sane
    if len(content) > 200 * 1024:
        content = content[: 200 * 1024] + f"\n\n…(truncated at 200 KB; full file is {p.stat().st_size} bytes at /{filename})"
    return _ok(content)


def _ok(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": False}


def _err(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": True}


TOOL_IMPLS = {
    "wiki_query": tool_wiki_query,
    "wiki_search": tool_wiki_search,
    "wiki_list_sources": tool_wiki_list_sources,
    "wiki_read_page": tool_wiki_read_page,
    "wiki_lint": tool_wiki_lint,
    "wiki_sync": tool_wiki_sync,
    "wiki_export": tool_wiki_export,
}


# ─── JSON-RPC plumbing ────────────────────────────────────────────────────


def handle_initialize(params: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "serverInfo": SERVER_INFO,
        "capabilities": {"tools": {}},
    }


def handle_tools_list(params: dict[str, Any]) -> dict[str, Any]:
    return {"tools": TOOLS}


def handle_tools_call(params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    args = params.get("arguments", {}) or {}
    impl = TOOL_IMPLS.get(name)
    if impl is None:
        return _err(f"Unknown tool: {name}")
    try:
        return impl(args)
    except Exception as e:
        return _err(f"Internal error in {name}: {e}")


HANDLERS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
}


def send(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def error_response(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }


def main() -> int:
    """Run the MCP server on stdin/stdout."""
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                send(error_response(None, -32700, "Parse error"))
                continue

            method = req.get("method", "")
            req_id = req.get("id")
            params = req.get("params", {}) or {}

            handler = HANDLERS.get(method)
            if handler is None:
                if req_id is None:
                    continue  # notifications don't get a response
                send(error_response(req_id, -32601, f"Method not found: {method}"))
                continue

            try:
                result = handler(params)
            except Exception as e:
                send(error_response(req_id, -32603, f"Internal error: {e}"))
                continue

            if req_id is not None:
                send({"jsonrpc": "2.0", "id": req_id, "result": result})
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        sys.stderr.write(f"MCP server error: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
