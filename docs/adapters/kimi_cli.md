---
title: "Kimi CLI adapter"
type: navigation
docs_shell: true
---

# Kimi CLI adapter

Reads session transcripts written by [Kimi Code CLI](https://www.moonshot.cn/).

**AI-session adapter** (`is_ai_session = True`) — fires by default when its
session store is present on disk.

## Session store

Kimi CLI stores sessions under a dot-directory on all platforms:

```
~/.kimi/sessions/<md5(work_dir)>/<uuid>/
├── context.jsonl   ← conversation transcript (ingested)
├── state.json      ← session metadata (title, archived, etc.)
└── wire.jsonl      ← wire-protocol log (ignored)
```

The `<md5(work_dir)>` directory name is the MD5 hash of the absolute path of
the working directory where the session was started. The adapter resolves this
hash back to a human-readable project name via `~/.kimi/kimi.json`, which maps
`path → last_session_id`.

Sub-agent sessions are stored under `<uuid>/subagents/<agent_id>/context.jsonl`
and are tagged with `is_subagent: true`.

## What it reads

The adapter ingests `context.jsonl` only (not `wire.jsonl`). Each line is a
JSON object with a `role` field:

| `role` | What it is | How we handle it |
|---|---|---|
| `user` | Real user prompt | Rendered as `### Turn N — User` |
| `assistant` | Model response | Rendered as `### Turn N — Assistant` with text + tool calls |
| `tool` | Tool execution result | Rendered under `**Tool results:**` |
| `_system_prompt` | System instructions | Dropped |
| `_checkpoint` | Checkpoint marker | Dropped |
| `_usage` | Token usage stats | Dropped |

Unknown roles are skipped gracefully — the converter never crashes on a record
it doesn't recognise.

## Record normalisation

Kimi's native schema uses top-level `role` and `content` fields, with tool calls
in a sibling `tool_calls` array. `normalize_records()` translates this into the
Claude-style `{type, message: {role, content}}` shape that the shared renderer
expects:

| Kimi role | Claude-style type | Notes |
|---|---|---|
| `user` | `user` | String content passed through |
| `assistant` | `assistant` | Text blocks + `tool_use` blocks extracted from `tool_calls` |
| `tool` | `user` | Converted to `tool_result` blocks |

## Enable it

Works out-of-the-box if Kimi CLI is installed on this machine. To explicitly
disable:

```jsonc
// sessions_config.json
{ "kimi_cli": { "enabled": false } }
```

## Output layout

Standard `raw/sessions/<YYYY-MM-DDTHH-MM>-<project>-<slug>.md`.

## Schema versions supported

```python
SUPPORTED_SCHEMA_VERSIONS = ["v1"]
```

The adapter is tested against the current Kimi CLI session format (observed
April 2026).

## Code

- `llmwiki/adapters/contrib/kimi_cli.py`
- Tests: `tests/test_adapter_kimi_cli.py`
- Fixture: `tests/fixtures/kimi_cli/minimal.jsonl`
- Snapshot: `tests/snapshots/kimi_cli/minimal.md`

## Skills

Kimi CLI discovers project-level skills automatically. After cloning or updating the repo, run:

```bash
python3 -m llmwiki install-skills
```

This copies the llmwiki skills into `.kimi/skills/` (among other targets). Kimi CLI loads them under `### Project` scope.

For reliable discovery, set in `~/.kimi/config.toml`:

```toml
merge_all_available_skills = true
```

The available skills are:

| Skill | Purpose |
|---|---|
| `llmwiki-sync` | Sync session transcripts and ingest them into the wiki |
| `llmwiki-ingest` | Ingest a single source file or folder |
| `llmwiki-query` | Answer questions from the wiki |
| `project-maintainer` | Ongoing project-keeping chores |
| `self-learn` | Extract lessons and update framework docs |
| `wiki-all` | Run the complete pipeline |

All skills are agent-agnostic — they work in Kimi CLI, Claude Code, and Codex CLI.

## See also

- [All adapters](../../README.md#works-with) — comparison table of every agent
  adapter llmwiki supports out of the box.
