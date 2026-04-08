"""llmwiki MCP server.

Exposes llmwiki operations as Model Context Protocol (MCP) tools that any
MCP-capable client (Claude Desktop, Claude Code, Codex, Cline, Cursor, ChatGPT
desktop, etc.) can call directly.

v0.1 status: **stub**. The server implements the protocol handshake and a
single `wiki_query` tool that returns the contents of `wiki/index.md` plus a
message saying full tool surface is coming in v0.2.

In v0.2 this will expose:

    - wiki_query(question)   — search + synthesise from wiki/
    - wiki_ingest(path)      — ingest one source
    - wiki_search(term)      — raw grep over raw/ + wiki/
    - wiki_lint()            — run the lint workflow
    - wiki_sync()            — trigger a sync from session stores
    - wiki_list_sources()    — list all sources with metadata

See the MCP spec at: https://modelcontextprotocol.io/

Run with:

    python3 -m llmwiki.mcp
"""

from __future__ import annotations

from llmwiki.mcp.server import main

__all__ = ["main"]
