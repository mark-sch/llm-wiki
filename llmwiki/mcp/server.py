"""MCP server stub for llmwiki.

Protocol: Model Context Protocol, stdio transport.
Reference: https://modelcontextprotocol.io/

This is a **v0.1 stub**. It implements the minimum handshake so MCP clients
can connect without errors. The full tool surface (wiki_query, wiki_ingest,
wiki_search, wiki_lint, wiki_sync, wiki_list_sources) ships in v0.2.

Ships as a standalone Python file — no third-party MCP SDK dependency — so
the stdlib-first rule stays intact. When v0.2 adds the full surface, we'll
consider pulling in the official `mcp` package as an optional dep.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from llmwiki import REPO_ROOT, __version__


SERVER_INFO = {
    "name": "llmwiki",
    "version": __version__,
}

PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "wiki_query",
        "description": (
            "Read the llmwiki's index.md and return the catalog. "
            "v0.1 stub — full query + synthesis arrives in v0.2."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to answer from the wiki.",
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "wiki_list_sources",
        "description": "List all source files under raw/sessions/ with their metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def read_index() -> str:
    index = REPO_ROOT / "wiki" / "index.md"
    if not index.exists():
        return "(wiki/index.md does not exist yet — run `llmwiki init` and `/wiki-sync` first)"
    return index.read_text(encoding="utf-8")


def list_sources() -> list[dict[str, Any]]:
    raw_sessions = REPO_ROOT / "raw" / "sessions"
    if not raw_sessions.exists():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(raw_sessions.rglob("*.md")):
        try:
            size = p.stat().st_size
        except OSError:
            continue
        out.append(
            {
                "path": str(p.relative_to(REPO_ROOT)),
                "project": p.parent.name,
                "size_bytes": size,
            }
        )
    return out


def handle_initialize(params: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "serverInfo": SERVER_INFO,
        "capabilities": {
            "tools": {},
        },
    }


def handle_tools_list(params: dict[str, Any]) -> dict[str, Any]:
    return {"tools": TOOLS}


def handle_tools_call(params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    args = params.get("arguments", {}) or {}

    if name == "wiki_query":
        question = args.get("question", "")
        body = (
            f"Question: {question}\n\n"
            "v0.1 stub — returning the current wiki index. Full query + "
            "synthesis ships in v0.2.\n\n"
            + read_index()
        )
        return {
            "content": [{"type": "text", "text": body}],
            "isError": False,
        }

    if name == "wiki_list_sources":
        sources = list_sources()
        return {
            "content": [{"type": "text", "text": json.dumps(sources, indent=2)}],
            "isError": False,
        }

    return {
        "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
        "isError": True,
    }


HANDLERS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
}


def send(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def error(req_id: Any, code: int, message: str) -> dict[str, Any]:
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
                send(error(None, -32700, "Parse error"))
                continue

            method = req.get("method", "")
            req_id = req.get("id")
            params = req.get("params", {}) or {}

            handler = HANDLERS.get(method)
            if handler is None:
                # Notifications don't get a response
                if req_id is None:
                    continue
                send(error(req_id, -32601, f"Method not found: {method}"))
                continue

            try:
                result = handler(params)
            except Exception as e:
                send(error(req_id, -32603, f"Internal error: {e}"))
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
