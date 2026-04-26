"""Tests for the Kimi CLI adapter."""

from __future__ import annotations

import json
from pathlib import Path

from llmwiki.adapters.contrib.kimi_cli import KimiCliAdapter


# ── adapter contract ──────────────────────────────────────────────────


def test_supported_schema_versions_declared():
    assert hasattr(KimiCliAdapter, "SUPPORTED_SCHEMA_VERSIONS")
    assert "v1" in KimiCliAdapter.SUPPORTED_SCHEMA_VERSIONS


# ── normalize_records ─────────────────────────────────────────────────


def test_normalize_skips_internal_records():
    adapter = KimiCliAdapter()
    raw = [
        {"role": "_system_prompt", "content": "You are Kimi…"},
        {"role": "_checkpoint", "id": 0},
        {"role": "_usage", "token_count": 42},
    ]
    assert adapter.normalize_records(raw) == []


def test_normalize_user_message():
    adapter = KimiCliAdapter()
    raw = [{"role": "user", "content": "hello"}]
    out = adapter.normalize_records(raw)
    assert len(out) == 1
    assert out[0]["type"] == "user"
    assert out[0]["message"]["role"] == "user"
    assert out[0]["message"]["content"] == "hello"


def test_normalize_assistant_text():
    adapter = KimiCliAdapter()
    raw = [{"role": "assistant", "content": "Hello world!"}]
    out = adapter.normalize_records(raw)
    assert len(out) == 1
    assert out[0]["type"] == "assistant"
    content = out[0]["message"]["content"]
    assert content == [{"type": "text", "text": "Hello world!"}]


def test_normalize_assistant_tool_call():
    adapter = KimiCliAdapter()
    raw = [{
        "role": "assistant",
        "content": [],
        "tool_calls": [{
            "type": "function",
            "id": "ReadFile:0",
            "function": {
                "name": "ReadFile",
                "arguments": '{"path": "sample.js"}',
            },
        }],
    }]
    out = adapter.normalize_records(raw)
    assert len(out) == 1
    assert out[0]["type"] == "assistant"
    blocks = out[0]["message"]["content"]
    assert len(blocks) == 1
    assert blocks[0]["type"] == "tool_use"
    assert blocks[0]["name"] == "ReadFile"
    assert blocks[0]["id"] == "ReadFile:0"
    assert blocks[0]["input"] == {"path": "sample.js"}


def test_normalize_tool_result_string():
    adapter = KimiCliAdapter()
    raw = [{
        "role": "tool",
        "content": "File written.",
        "tool_call_id": "WriteFile:1",
    }]
    out = adapter.normalize_records(raw)
    assert len(out) == 1
    assert out[0]["type"] == "user"
    blocks = out[0]["message"]["content"]
    assert blocks[0]["type"] == "tool_result"
    assert blocks[0]["tool_use_id"] == "WriteFile:1"
    assert blocks[0]["content"] == "File written."


def test_normalize_tool_result_blocks():
    adapter = KimiCliAdapter()
    raw = [{
        "role": "tool",
        "content": [
            {"type": "text", "text": "line 1"},
            {"type": "text", "text": "line 2"},
        ],
        "tool_call_id": "ReadFile:0",
    }]
    out = adapter.normalize_records(raw)
    blocks = out[0]["message"]["content"]
    assert blocks[0]["content"] == "line 1\nline 2"


def test_normalize_full_conversation():
    """End-to-end normalization of a realistic Kimi context.jsonl snippet."""
    adapter = KimiCliAdapter()
    raw = [
        {"role": "_system_prompt", "content": "system…"},
        {"role": "_checkpoint", "id": 0},
        {"role": "user", "content": "task"},
        {"role": "assistant", "content": [], "tool_calls": [{
            "type": "function",
            "id": "t1",
            "function": {"name": "Bash", "arguments": '{"command": "ls"}'},
        }]},
        {"role": "tool", "content": "foo.py\nbar.py", "tool_call_id": "t1"},
        {"role": "assistant", "content": "Done."},
    ]
    out = adapter.normalize_records(raw)
    assert len(out) == 4
    assert out[0]["type"] == "user"
    assert out[1]["type"] == "assistant"
    assert out[1]["message"]["content"][0]["type"] == "tool_use"
    assert out[2]["type"] == "user"
    assert out[2]["message"]["content"][0]["type"] == "tool_result"
    assert out[3]["type"] == "assistant"
    assert out[3]["message"]["content"][0]["text"] == "Done."


# ── graceful degradation ──────────────────────────────────────────────


def test_normalize_skips_unknown_roles():
    """Unknown record types are skipped, not crashed on."""
    adapter = KimiCliAdapter()
    raw = [
        {"role": "user", "content": "ok"},
        {"role": "future_magic_role", "content": "??"},
        {"role": "assistant", "content": "hi"},
    ]
    out = adapter.normalize_records(raw)
    assert len(out) == 2
    assert out[0]["type"] == "user"
    assert out[1]["type"] == "assistant"


# ── subagent detection ────────────────────────────────────────────────


def test_is_subagent():
    adapter = KimiCliAdapter()
    from pathlib import Path
    assert adapter.is_subagent(Path("sessions/h/s/subagents/a/context.jsonl"))
    assert adapter.is_subagent(Path("sessions/h/s/subagent/context.jsonl"))
    assert not adapter.is_subagent(Path("sessions/h/s/context.jsonl"))


def test_has_parent_session_true(tmp_path: Path):
    adapter = KimiCliAdapter()
    # Normal session (not a subagent)
    assert adapter._has_parent_session(tmp_path / "sessions" / "h" / "s" / "context.jsonl")
    # Subagent with parent context.jsonl
    parent = tmp_path / "sessions" / "h" / "s"
    parent.mkdir(parents=True)
    (parent / "context.jsonl").write_text("{}")
    assert adapter._has_parent_session(parent / "subagents" / "a" / "context.jsonl")


def test_has_parent_session_false(tmp_path: Path):
    adapter = KimiCliAdapter()
    # Create a fake session store structure
    store = tmp_path / "sessions" / "abc123"
    subagent = store / "test" / "subagents" / "ag1" / "context.jsonl"
    subagent.parent.mkdir(parents=True)
    subagent.write_text("{}")
    # Parent has NO context.jsonl → orphaned
    assert not adapter._has_parent_session(subagent)


def test_discover_sessions_skips_orphans(tmp_path: Path):
    adapter = KimiCliAdapter()
    # Override session store path
    store = tmp_path / "sessions"
    adapter.session_store_path = store

    # Orphaned subagent (no parent context.jsonl)
    orphan = store / "hash1" / "test" / "subagents" / "ag1" / "context.jsonl"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("{}")

    # Real session with parent context.jsonl
    real = store / "hash2" / "uuid" / "context.jsonl"
    real.parent.mkdir(parents=True)
    real.write_text("{}")
    # And its subagent
    real_sub = store / "hash2" / "uuid" / "subagents" / "ag2" / "context.jsonl"
    real_sub.parent.mkdir(parents=True)
    real_sub.write_text("{}")

    found = adapter.discover_sessions()
    assert len(found) == 2
    assert orphan not in found
    assert real in found
    assert real_sub in found


def test_is_placeholder_session_empty():
    adapter = KimiCliAdapter()
    assert adapter._is_placeholder_session([])
    assert adapter._is_placeholder_session([
        {"role": "_system_prompt", "content": "system"},
        {"role": "_checkpoint", "id": 0},
    ])


def test_is_placeholder_session_x_padding():
    adapter = KimiCliAdapter()
    records = [
        {"role": "_system_prompt", "content": "system"},
        {"role": "assistant", "content": "x" * 50},
    ]
    assert adapter._is_placeholder_session(records)


def test_is_placeholder_session_real_content():
    adapter = KimiCliAdapter()
    records = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    assert not adapter._is_placeholder_session(records)


def test_normalize_filters_placeholder_subagent():
    adapter = KimiCliAdapter()
    records = [
        {"role": "_system_prompt", "content": "system"},
        {"role": "assistant", "content": "x" * 50},
    ]
    path = Path("sessions/h/s/subagents/a/context.jsonl")
    result = adapter.normalize_records(records, jsonl_path=path)
    assert result == []


def test_normalize_keeps_real_subagent():
    adapter = KimiCliAdapter()
    records = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    path = Path("sessions/h/s/subagents/a/context.jsonl")
    result = adapter.normalize_records(records, jsonl_path=path)
    assert len(result) == 2


# ── project slug ──────────────────────────────────────────────────────


def test_derive_project_slug_uses_kimi_json():
    adapter = KimiCliAdapter()
    from pathlib import Path
    # Build a fake path using a hash we control
    fake_hash = "a" * 32
    p = adapter.session_store_path / fake_hash / "uuid" / "context.jsonl"
    # Without kimi.json mapping the fallback is used
    slug = adapter.derive_project_slug(p)
    assert slug.startswith("kimi-")


# ── integration: fixture → converter ──────────────────────────────────


def test_fixture_renders_to_snapshot():
    """Load the synthetic fixture, normalize, render, and diff against snapshot."""
    from llmwiki.convert import render_session_markdown, Redactor, parse_jsonl

    fixture = Path(__file__).parent.parent / "tests" / "fixtures" / "kimi_cli" / "minimal.jsonl"
    snapshot = Path(__file__).parent.parent / "tests" / "snapshots" / "kimi_cli" / "minimal.md"

    assert fixture.exists(), f"fixture missing: {fixture}"
    assert snapshot.exists(), f"snapshot missing: {snapshot}"

    records = parse_jsonl(fixture)
    adapter = KimiCliAdapter()
    records = adapter.normalize_records(records)

    redact = Redactor({})
    md, slug, started = render_session_markdown(
        records, fixture, "kimi-fixture", redact, {}, False, "kimi_cli"
    )

    # Normalize dynamic timestamps so the diff is stable
    snapshot_text = snapshot.read_text(encoding="utf-8")
    # Replace variable timestamps with a fixed placeholder for comparison
    import re
    md_norm = re.sub(r"started: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+\d{2}:\d{2}",
                     "started: TIMESTAMP", md)
    snap_norm = re.sub(r"started: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+\d{2}:\d{2}",
                       "started: TIMESTAMP", snapshot_text)
    md_norm = re.sub(r"ended: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+\d{2}:\d{2}",
                     "ended: TIMESTAMP", md_norm)
    snap_norm = re.sub(r"ended: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+\d{2}:\d{2}",
                       "ended: TIMESTAMP", snap_norm)
    md_norm = re.sub(r"date: \d{4}-\d{2}-\d{2}", "date: DATE", md_norm)
    snap_norm = re.sub(r"date: \d{4}-\d{2}-\d{2}", "date: DATE", snap_norm)
    md_norm = re.sub(r'title: "Session: minimal — \d{4}-\d{2}-\d{2}"',
                     'title: "Session: minimal — DATE"', md_norm)
    snap_norm = re.sub(r'title: "Session: minimal — \d{4}-\d{2}-\d{2}"',
                       'title: "Session: minimal — DATE"', snap_norm)
    md_norm = re.sub(r"source_file: raw/sessions/\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-[^\s]+\.md",
                     "source_file: raw/sessions/DATE-TIME-SLUG.md", md_norm)
    snap_norm = re.sub(r"source_file: raw/sessions/\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-[^\s]+\.md",
                       "source_file: raw/sessions/DATE-TIME-SLUG.md", snap_norm)
    # Normalize dynamic slug derived from first user message
    md_norm = re.sub(r'slug: [^\s]+', 'slug: SLUG', md_norm)
    snap_norm = re.sub(r'slug: [^\s]+', 'slug: SLUG', snap_norm)
    md_norm = re.sub(r'title: "Session: [^"]+ — \d{4}-\d{2}-\d{2}"',
                     'title: "Session: SLUG — DATE"', md_norm)
    snap_norm = re.sub(r'title: "Session: [^"]+ — \d{4}-\d{2}-\d{2}"',
                       'title: "Session: SLUG — DATE"', snap_norm)
    md_norm = re.sub(r"# Session: [^\n]+ — \d{4}-\d{2}-\d{2}",
                     "# Session: SLUG — DATE", md_norm)
    snap_norm = re.sub(r"# Session: [^\n]+ — \d{4}-\d{2}-\d{2}",
                       "# Session: SLUG — DATE", snap_norm)

    assert md_norm == snap_norm, f"Rendered markdown differs from snapshot.\n\n--- rendered ---\n{md_norm}\n\n--- snapshot ---\n{snap_norm}"
