---
title: "Use with Kimi CLI"
type: tutorial
docs_shell: true
---

# Use llmwiki with Kimi CLI

[Kimi Code CLI](https://www.moonshot.cn/) is a fully supported agent. This guide shows how to set up llmwiki so that Kimi CLI can load its skills and maintain the wiki.

## What you need

- Kimi CLI installed and configured (`kimi --version` works)
- A cloned llmwiki repo
- Python 3.9+ and `uv` (or `pip`) for the llmwiki package

## Step 1 — Install dependencies

```bash
cd /path/to/llmwiki
uv pip install -e .          # or: pip install -e .
```

## Step 2 — Scaffold the wiki (once)

```bash
python3 -m llmwiki init --language en   # or --language de
```

This creates `raw/`, `wiki/`, `site/`, and seeds the navigation files.

## Step 3 — Install skills for Kimi CLI

```bash
python3 -m llmwiki install-skills
```

This copies the llmwiki skills into `.kimi/skills/` (and other agent targets). Kimi CLI discovers them automatically when you start a session inside the repo.

## Step 4 — Configure Kimi CLI (recommended)

Edit `~/.kimi/config.toml`:

```toml
merge_all_available_skills = true
```

This ensures Kimi CLI merges all discovered skill directories instead of stopping at the first one.

## Step 5 — Sync your Kimi sessions

```bash
python3 -m llmwiki sync --adapter kimi_cli
```

This converts `~/.kimi/sessions/` transcripts into `raw/sessions/` markdown.

## Step 6 — Ingest via Kimi CLI

Start Kimi CLI inside the repo:

```bash
cd /path/to/llmwiki
kimi
```

Then say:

```
sync the wiki
```

Kimi CLI loads the `llmwiki-sync` skill, runs `python3 -m llmwiki sync`, and ingests the new sources into `wiki/sources/`, `wiki/entities/`, and `wiki/concepts/`.

## Multi-agent sync (Claude Code + Kimi CLI + Codex CLI)

If you use multiple agents, run sync without `--adapter` to auto-detect all session stores:

```bash
python3 -m llmwiki sync
```

llmwiki will convert sessions from every agent that has a session store on disk (Claude Code, Kimi CLI, Codex CLI, Cursor, etc.).

## Build and serve

```bash
python3 -m llmwiki build
python3 -m llmwiki serve
```

Open `http://127.0.0.1:8765` to browse the static site.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Skills not showing up in Kimi | Run `python3 -m llmwiki install-skills` again. Check that `.kimi/skills/` exists. |
| `merge_all_available_skills = false` ignores `.kimi/skills/` | Set it to `true` in `~/.kimi/config.toml`, or ensure no `.agents/skills/` exists in the project. |
| Overview synthesis fails with "claude CLI not found" | The `--synthesize` flag requires the Claude CLI. Use `python3 -m llmwiki synthesize` with a configured LLM backend instead. |
| Kimi sessions not found | Verify `~/.kimi/sessions/` exists and contains `context.jsonl` files. |

## Next steps

- [Query your wiki](05-querying-your-wiki.md)
- [Set up an Obsidian vault](../guides/existing-vault.md)
- [Configure the LLM synthesis backend](../reference/prompt-caching.md)
