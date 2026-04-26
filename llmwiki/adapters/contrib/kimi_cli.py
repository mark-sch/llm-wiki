"""Kimi CLI adapter (v1.0).

Kimi Code CLI stores session transcripts under:
    ~/.kimi/sessions/<md5(work_dir)>/<uuid>/context.jsonl

The ``context.jsonl`` file contains the conversation context in a
role-based JSONL format (user / assistant / tool / _system_prompt /
_checkpoint / _usage).  This adapter normalizes those records into the
shared Claude-style shape that ``llmwiki.convert`` expects.

Session metadata lives in the sibling ``state.json`` (title,
archived-flag, etc.) but is not required for ingestion.

The ``~/.kimi/kimi.json`` file maps working-directory paths to their
MD5 hash directory names; we use it to derive friendly project slugs.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llmwiki.adapters import register
from llmwiki.adapters.base import BaseAdapter


@register("kimi_cli")
class KimiCliAdapter(BaseAdapter):
    """Kimi CLI — reads ~/.kimi/sessions/**/context.jsonl"""

    SUPPORTED_SCHEMA_VERSIONS = ["v1"]

    session_store_path = Path.home() / ".kimi" / "sessions"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._work_dir_map: dict[str, str] | None = None

    # ── project slug resolution ───────────────────────────────────────

    def _load_work_dir_map(self) -> dict[str, str]:
        """Build {md5_hash: work_dir_path} from ~/.kimi/kimi.json."""
        if self._work_dir_map is not None:
            return self._work_dir_map

        mapping: dict[str, str] = {}
        kimi_json = Path.home() / ".kimi" / "kimi.json"
        try:
            with open(kimi_json, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._work_dir_map = mapping
            return mapping

        for entry in data.get("work_dirs", []):
            path = entry.get("path", "")
            if path:
                h = hashlib.md5(path.encode("utf-8")).hexdigest()
                mapping[h] = path

        self._work_dir_map = mapping
        return mapping

    def _parent_session_slug(self, jsonl_path: Path) -> str | None:
        """For sub-agent files, try to derive a slug from the parent session.

        Layouts::

            sessions/<md5>/test/subagents/<id>/context.jsonl
            sessions/<md5>/<uuid>/subagents/<id>/context.jsonl

        We walk up to the parent session directory and read ``state.json``
        for a ``custom_title``.  If that fails we use the parent dir name.
        """
        parts = jsonl_path.parts
        if "subagents" not in parts:
            return None
        # Find the directory *above* subagents
        try:
            idx = parts.index("subagents")
        except ValueError:
            return None
        if idx < 1:
            return None
        parent_dir = Path(*parts[:idx])
        state_file = parent_dir / "state.json"
        try:
            with open(state_file, encoding="utf-8") as f:
                state = json.load(f)
            title = state.get("custom_title") or state.get("title")
            if title:
                # Convert title to kebab-case slug
                slug = re.sub(r"[^\w\s]", "", title.strip().replace("\n", " "))
                slug = "-".join(slug.split()[:6]).lower()
                return slug[:40].rstrip("-") if len(slug) >= 3 else None
        except (OSError, json.JSONDecodeError):
            pass
        # Fallback: use the MD5 hash directory name (first component of the
        # session path) rather than the generic "test" directory name.
        # This gives a stable, unique identifier per project even when the
        # working directory is no longer in kimi.json.
        if idx >= 1:
            hash_dir = parts[0]
            if len(hash_dir) == 32 and all(c in "0123456789abcdef" for c in hash_dir):
                return f"kimi-{hash_dir[:8]}"
        return None

    def derive_project_slug(self, jsonl_path: Path) -> str:
        """Map the MD5 hash directory to a friendly project slug.

        The layout is ``sessions/<md5>/<uuid>/context.jsonl``.  We look up
        the md5 in ``~/.kimi/kimi.json`` and use the basename of the
        working directory.  Fallback to the hash itself if the mapping is
        missing.

        For sub-agent sessions we additionally try to read the parent
        session's ``state.json`` so the project slug is meaningful even
        when the original working directory is no longer in ``kimi.json``.
        """
        store = Path(self.session_store_path).expanduser()
        try:
            rel = jsonl_path.relative_to(store)
        except ValueError:
            return jsonl_path.parent.name

        if len(rel.parts) < 2:
            return jsonl_path.parent.name

        hash_dir = rel.parts[0]
        mapping = self._load_work_dir_map()
        work_dir = mapping.get(hash_dir)
        if work_dir:
            return Path(work_dir).name.lower().replace(" ", "-")

        # For sub-agents with an unknown hash, try to get a meaningful
        # name from the parent session's state.json.
        if self.is_subagent(jsonl_path):
            parent_slug = self._parent_session_slug(jsonl_path)
            if parent_slug:
                return parent_slug

        # Fallback: if the hash looks like an md5, use a shortened form
        if len(hash_dir) == 32 and all(c in "0123456789abcdef" for c in hash_dir):
            return f"kimi-{hash_dir[:8]}"

        return hash_dir

    # ── discovery ─────────────────────────────────────────────────────

    def _has_parent_session(self, jsonl_path: Path) -> bool:
        """Check whether a sub-agent file belongs to a real parent session.

        Sub-agents under ``test/subagents/`` or ``<uuid>/subagents/`` that
        have no sibling ``context.jsonl`` in the parent directory are
        considered orphaned (usually plan-mode leftovers or deleted projects).
        They are skipped so the wiki doesn't fill up with ghost sessions.
        """
        if "subagents" not in jsonl_path.parts:
            return True
        try:
            idx = jsonl_path.parts.index("subagents")
        except ValueError:
            return True
        if idx < 1:
            return True
        parent_dir = Path(*jsonl_path.parts[:idx])
        return (parent_dir / "context.jsonl").exists()

    def discover_sessions(self) -> list[Path]:
        """Return every ``context.jsonl`` under the session store.

        We intentionally ignore ``wire.jsonl`` (wire-protocol log) and
        ``user-history/*.jsonl`` because ``context.jsonl`` already holds
        the human-readable conversation transcript.

        Additionally we drop orphaned sub-agents whose parent session has
        no ``context.jsonl`` (plan-mode ghosts or deleted projects).
        """
        store = Path(self.session_store_path).expanduser()
        if not store.exists():
            return []
        return sorted(
            p for p in store.rglob("context.jsonl") if self._has_parent_session(p)
        )

    # ── subagent detection ────────────────────────────────────────────

    def is_subagent(self, jsonl_path: Path) -> bool:
        return "subagent" in jsonl_path.parts or "subagents" in jsonl_path.parts

    def _is_placeholder_session(self, records: list[dict[str, Any]]) -> bool:
        """Detect empty or placeholder sub-agent sessions.

        Kimi creates sub-agent context files that contain only:
        * ``_system_prompt`` / ``_checkpoint`` / ``_usage`` records
        * A single ``assistant`` record with repetitive ``x`` padding
        * No actual user messages or tool calls

        These should be skipped so they don't clutter the wiki.
        """
        non_internal = [
            r for r in records
            if isinstance(r, dict) and r.get("role") not in ("_system_prompt", "_checkpoint", "_usage")
        ]
        if not non_internal:
            return True
        # Single assistant record with only padding characters
        if len(non_internal) == 1 and non_internal[0].get("role") == "assistant":
            content = non_internal[0].get("content", "")
            if isinstance(content, str) and len(content) >= 10:
                if set(content).issubset({"x"}):
                    return True
            # Also check list-form content blocks
            if isinstance(content, list) and len(content) == 1:
                block = content[0]
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if len(text) >= 10 and set(text).issubset({"x"}):
                        return True
        return False

    # ── record normalization ──────────────────────────────────────────

    def normalize_records(
        self,
        records: list[dict[str, Any]],
        jsonl_path: Path | None = None,
    ) -> list[dict[str, Any]]:
        """Translate Kimi CLI ``context.jsonl`` into the shared Claude-style
        format.

        Kimi schema (observed)::

            {"role": "_system_prompt", "content": "…"}
            {"role": "_checkpoint",   "id": 0}
            {"role": "user",          "content": "…"}
            {"role": "assistant",     "content": "…"}
            {"role": "assistant",     "content": [], "tool_calls": [{"type":"function", …}]}
            {"role": "tool",          "content": [{"type":"text", "text":"…"}], "tool_call_id": "…"}
            {"role": "_usage",        "token_count": 123}

        Claude style::

            {"type": "user",     "message": {"role": "user",     "content": "…"}}
            {"type": "assistant","message": {"role": "assistant","content": [{"type":"text", …}, {"type":"tool_use", …}]}}
            {"type": "user",     "message": {"role": "user",     "content": [{"type":"tool_result", …}]}}

        Internal records (_system_prompt, _checkpoint, _usage) are skipped.

        Because Kimi records carry neither timestamps nor slugs, we inject
        them here when ``jsonl_path`` is provided:

        * ``timestamp`` — the file's mtime (the best proxy for session start).
        * ``slug`` — derived from the first user message so sessions don't
          all collide on the filename ``context``.
        """
        # Skip placeholder sub-agent sessions that contain no real conversation.
        if jsonl_path and self.is_subagent(jsonl_path) and self._is_placeholder_session(records):
            return []

        out: list[dict[str, Any]] = []

        # Extract timestamp from file mtime so convert.py can compute the
        # real session date instead of falling back to "now".
        file_ts: str | None = None
        if jsonl_path:
            try:
                mtime = jsonl_path.stat().st_mtime
                file_ts = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            except OSError:
                pass

        # Derive a meaningful slug from the first user message so we don't
        # end up with 300+ sessions all named "context".
        first_user_text = ""
        for rec in records:
            if isinstance(rec, dict) and rec.get("role") == "user":
                content = rec.get("content")
                if isinstance(content, str):
                    first_user_text = content
                break
        derived_slug = self._derive_slug(first_user_text, jsonl_path)

        for rec in records:
            if not isinstance(rec, dict):
                continue

            role = rec.get("role")
            content = rec.get("content")

            # Skip internal bookkeeping records
            if role in ("_system_prompt", "_checkpoint", "_usage"):
                continue

            if role == "user":
                text = content if isinstance(content, str) else ""
                user_rec: dict[str, Any] = {
                    "type": "user",
                    "message": {"role": "user", "content": text},
                }
                if file_ts:
                    user_rec["timestamp"] = file_ts
                # Attach the derived slug to the *first* user record so
                # convert.py's derive_session_slug() picks it up.
                if derived_slug and not any(r.get("slug") for r in out):
                    user_rec["slug"] = derived_slug
                if text:
                    out.append(user_rec)
                continue

            if role == "assistant":
                blocks: list[dict[str, Any]] = []

                # Text content (may be a string or a list of content blocks)
                if isinstance(content, str) and content:
                    blocks.append({"type": "text", "text": content})
                elif isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        btype = block.get("type")
                        if btype == "text":
                            text = block.get("text", "")
                            if text:
                                blocks.append({"type": "text", "text": text})
                        elif btype == "think":
                            # Skip thinking blocks by default (matches Claude)
                            continue

                # Tool calls are stored in a sibling field
                tool_calls = rec.get("tool_calls")
                if isinstance(tool_calls, list):
                    for call in tool_calls:
                        if not isinstance(call, dict):
                            continue
                        func = call.get("function", {})
                        name = func.get("name", "")
                        arguments = func.get("arguments", "{}")
                        call_id = call.get("id", "")
                        try:
                            inp = json.loads(arguments) if isinstance(arguments, str) else arguments
                        except json.JSONDecodeError:
                            inp = {"raw": arguments}
                        blocks.append({
                            "type": "tool_use",
                            "name": name,
                            "id": call_id,
                            "input": inp,
                        })

                if blocks:
                    out.append({
                        "type": "assistant",
                        "message": {"role": "assistant", "content": blocks},
                    })
                continue

            if role == "tool":
                tool_call_id = rec.get("tool_call_id", "")
                # Content may be a string or a list of blocks
                if isinstance(content, str):
                    tool_content = content
                elif isinstance(content, list):
                    parts: list[str] = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
                    tool_content = "\n".join(parts)
                else:
                    tool_content = ""

                if tool_call_id or tool_content:
                    out.append({
                        "type": "user",
                        "message": {
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": tool_call_id,
                                "content": tool_content,
                            }],
                        },
                    })
                continue

            # Unknown role — skip gracefully

        return out

    def _derive_slug(self, text: str, jsonl_path: Path | None) -> str:
        """Create a unique slug from the first user message or the path.

        Falls back to the parent directory name (session UUID) when the text
        is empty or too generic.
        """
        if text:
            # Take first ~40 chars, collapse whitespace, kebab-case
            snippet = text.strip().replace("\n", " ")[:40]
            # Remove non-alphanumeric chars except spaces
            snippet = re.sub(r"[^\w\s]", "", snippet)
            words = snippet.split()
            if len(words) >= 2:
                slug = "-".join(words[:6]).lower()
                # Max 40 chars to keep filenames readable
                slug = slug[:40].rstrip("-")
                if len(slug) >= 3:
                    return slug
        # Fallback: use the session UUID from the parent directory
        if jsonl_path:
            parent = jsonl_path.parent.name
            if parent and parent != "sessions":
                return parent[:12]
        return "context"
