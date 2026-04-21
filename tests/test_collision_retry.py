"""Integration test for the collision-retry branch in ``convert_all`` (#339).

When two distinct source jsonls would write to the same output path
(subagent sharing its parent's start-time + slug, or two top-level
sessions that happen to start in the same minute), the retry appends
a source-path hash so both files land side-by-side rather than one
getting quarantined.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from llmwiki import convert as c


def _write_jsonl(path: Path, session_id: str, iso_ts: str,
                 slug: str = "shared-slug") -> None:
    """Seed a minimal claude_code-shaped jsonl.

    ``slug`` on the first record pins derive_session_slug so two
    sources can deliberately collide on the canonical filename.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "type": "user",
            "sessionId": session_id,
            "slug": slug,
            "timestamp": iso_ts,
            "cwd": "/tmp",
            "gitBranch": "main",
            "message": {"role": "user", "content": "hi"},
        }) + "\n"
        + json.dumps({
            "type": "assistant",
            "sessionId": session_id,
            "timestamp": iso_ts,
            "message": {"role": "assistant", "content": "hello"},
        }) + "\n",
        encoding="utf-8",
    )


def _seed_env(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Seed a tmp_path repo + fake ~/.claude/projects/ source tree.

    Returns ``(home, project_dir, out_dir, state)``.  ``project_dir`` is
    already one level inside the store root so the adapter derives a
    stable project slug for every file under it.
    """
    home = tmp_path / "home"
    home.mkdir()
    # Store root (what the adapter scans) AND the project-dir within it.
    store_root = home / ".claude" / "projects"
    project_dir = store_root / "my-proj"
    out_dir = tmp_path / "repo" / "raw" / "sessions"
    state = tmp_path / "state.json"
    return home, project_dir, out_dir, state


def _patch(monkeypatch, home, out_dir, state):
    # ClaudeCodeAdapter.session_store_path is a class-level attribute
    # evaluated at class-definition time, so we have to patch the class
    # itself instead of relying on Path.home monkeypatching.  Point it
    # at the `projects/` directory so `derive_project_slug()` resolves
    # every file under it against that prefix.
    from llmwiki.adapters.claude_code import ClaudeCodeAdapter
    store = home / ".claude" / "projects"
    monkeypatch.setattr(
        ClaudeCodeAdapter, "session_store_path", store, raising=False,
    )
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(c, "DEFAULT_STATE_FILE", state)
    monkeypatch.setattr(c, "REPO_ROOT", home.parent / "repo")


def test_subagent_collision_is_resolved_with_hash_suffix(tmp_path, monkeypatch):
    """Parent + subagent that share start-time + slug both land on disk."""
    home, proj, out_dir, state = _seed_env(tmp_path)

    ts = "2026-04-16T10:00:00Z"
    parent = proj / "parent.jsonl"
    sub = proj / "subagents" / "agent-aprompt-abc.jsonl"
    _write_jsonl(parent, "sess-uuid-1111", ts, slug="shared-slug")
    _write_jsonl(sub, "sess-uuid-1111", ts, slug="shared-slug")

    _patch(monkeypatch, home, out_dir, state)

    c.discover_adapters()
    rc = c.convert_all(
        adapters=["claude_code"],
        out_dir=out_dir,
        state_file=state,
        include_current=True,  # include even very-recent test files
        force=False,
    )
    assert rc in (0, 1)

    outs = sorted(out_dir.rglob("*.md"))
    disambig = [p for p in outs if "--" in p.name]
    canonical = [p for p in outs if "--" not in p.name]
    assert canonical, f"canonical name missing; got {outs}"
    assert disambig, f"disambiguated file missing; got {outs}"


def test_second_source_with_identical_canonical_name_gets_hash(tmp_path, monkeypatch):
    """Two sources produce the same canonical name; second gets a hash."""
    home, proj, out_dir, state = _seed_env(tmp_path)
    ts = "2026-04-16T10:00:00Z"

    # Both directly in the project dir so derive_project_slug gives the
    # same value for both, AND both carry the same pinned slug so
    # flat_output_name produces identical canonical filenames.
    s1 = proj / "session-a.jsonl"
    s2 = proj / "session-b.jsonl"
    _write_jsonl(s1, "same-session-id", ts, slug="shared-slug")
    _write_jsonl(s2, "same-session-id", ts, slug="shared-slug")

    _patch(monkeypatch, home, out_dir, state)

    c.discover_adapters()
    c.convert_all(adapters=["claude_code"], out_dir=out_dir,
                  state_file=state, include_current=True)

    outs = sorted(out_dir.rglob("*.md"))
    canonical = [p for p in outs if "--" not in p.name]
    disambig = [p for p in outs if "--" in p.name]
    assert len(outs) >= 2
    assert canonical, f"no canonical file: {outs}"
    assert disambig, f"no disambiguated file: {outs}"


def test_resync_same_source_is_idempotent(tmp_path, monkeypatch):
    """Re-running sync on the same jsonl doesn't explode into
    <canonical> + <hash1> + <hash2> — the state key protects us."""
    home, proj, out_dir, state = _seed_env(tmp_path)
    _write_jsonl(proj / "s.jsonl", "x", "2026-04-16T10:00:00Z")
    _patch(monkeypatch, home, out_dir, state)

    c.discover_adapters()
    c.convert_all(adapters=["claude_code"], out_dir=out_dir,
                  state_file=state, include_current=True)
    first = sorted(out_dir.rglob("*.md"))
    c.convert_all(adapters=["claude_code"], out_dir=out_dir,
                  state_file=state, include_current=True)
    second = sorted(out_dir.rglob("*.md"))
    assert first == second, f"re-sync grew the tree: {first} → {second}"
