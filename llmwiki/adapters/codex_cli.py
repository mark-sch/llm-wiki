"""Codex CLI session-store adapter (stub).

Status: v0.1 stub. This adapter scaffolds the interface; the exact .jsonl
schema and directory layout will be confirmed against a real Codex CLI install
in v0.2. For now it discovers .jsonl files under the expected path so
installations that already have sessions will sync without code changes.

Expected layout (to be confirmed):
    ~/.codex/sessions/<something>/*.jsonl

If you have Codex CLI installed and want to help finalise this adapter, please
open an issue at https://github.com/Pratiyush/llmwiki with a sample session
file (redacted) so we can tune the parser.
"""

from __future__ import annotations

from pathlib import Path

from llmwiki.adapters import register
from llmwiki.adapters.base import BaseAdapter


@register("codex_cli")
class CodexCliAdapter(BaseAdapter):
    """Codex CLI — reads ~/.codex/sessions/**/*.jsonl (v0.1 stub)"""

    session_store_path = [
        Path.home() / ".codex" / "sessions",
        Path.home() / ".codex" / "projects",  # alternate layout
    ]

    def derive_project_slug(self, jsonl_path: Path) -> str:
        # Default: use immediate parent dir
        return super().derive_project_slug(jsonl_path)
