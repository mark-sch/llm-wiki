# Idea Brief: llmwiki

**Date:** 2026-04-08
**Framework phase:** 0 Capture

## One-line pitch

> **llmwiki** turns your Claude Code and Codex CLI session transcripts into a beautiful, searchable, self-hosted knowledge base — following Andrej Karpathy's LLM Wiki pattern.

## The problem

Every developer using Claude Code, Codex CLI, or similar coding agents ends up with a large, invisible archive of session transcripts (`~/.claude/projects/*/*.jsonl`, `~/.codex/sessions/`, etc.). These transcripts contain enormous value — every decision made, every library evaluated, every bug hit — but they're:

- **Unsearchable** — no tool reads across all of them.
- **Unrevisitable** — you can't browse your own history easily.
- **Unlearned** — nothing compiles them into reusable knowledge.
- **Scattered** — session-search tools exist but don't build a wiki on top.

Meanwhile, existing "LLM wiki" implementations ([SamurAIGPT/llm-wiki-agent](https://github.com/SamurAIGPT/llm-wiki-agent), [lucasastorian/llmwiki](https://github.com/lucasastorian/llmwiki), [xoai/sage-wiki](https://github.com/xoai/sage-wiki)) treat sources as generic markdown — none of them know about Claude Code `.jsonl` or Codex CLI session formats.

**The gap:** Nothing bridges agent session history → Karpathy-style compiled wiki.

## The solution

A Python CLI + static site generator that:

1. **Ingests** session transcripts from any supported agent via a pluggable adapter layer.
2. **Converts** each session into clean, redacted, frontmatter-tagged markdown under `raw/sessions/`.
3. **Compiles** a Karpathy-style wiki (`wiki/sources/`, `wiki/entities/`, `wiki/concepts/`) either via your coding agent's `/wiki-ingest` slash command OR via a pure-Python fallback.
4. **Renders** a beautiful static HTML site with search, syntax highlighting, keyboard shortcuts, dark mode, and mobile responsiveness.
5. **Serves** it via a one-line `python3 -m http.server` or exports to GitHub Pages.

## Why me, why now

- I (Pratiyush) maintain 278+ session transcripts across 12 projects spanning a few weeks — already at the scale where this pays off.
- My workstation has no global `npm` or `brew` — so the tool must be Python-only.
- I already use Claude Code and plan to add Codex CLI.
- Karpathy's gist made the pattern popular in early 2026 — the timing is right for a clean, agent-aware implementation.

## What makes this 10x better than existing options

| Existing | Gap | llmwiki |
|---|---|---|
| SamurAIGPT/llm-wiki-agent | Generic markdown, no `.jsonl` awareness | Native Claude Code + Codex CLI adapters |
| lucasastorian/llmwiki | Requires Supabase + S3 + MCP server | Zero dependencies beyond Python stdlib + `markdown` |
| search-sessions, claude-history | Raw search only, no wiki compilation | Full Karpathy 3-layer wiki on top |
| claude-ops | Proprietary observability SaaS | Fully local, open source, self-hosted |
| Notion/Obsidian + manual import | Manual labour | Auto-sync on SessionStart hook |

## Target users

1. **Heavy Claude Code users** (primary) — 50+ sessions, many projects, want to search across them.
2. **Codex CLI users** (secondary — after adapter ships).
3. **Developers managing multiple agents** (future — Gemini CLI, OpenCode, Cline, Cursor).
4. **Solo devs who want to publish a public LLM wiki** via GitHub Pages.

## Non-goals (explicit)

- ❌ Semantic search with embeddings — Karpathy explicitly argues against RAG for this.
- ❌ Multi-user SaaS — self-hosted and per-machine only.
- ❌ Replace your agent's memory system — complements it, doesn't replace.
- ❌ Cloud sync — everything is local; user controls if/when to publish.

## Success metrics (Phase 6-8)

- v0.1.0 launches with Claude Code adapter working end-to-end
- 10+ stars in first week (soft goal)
- 100+ stars in first month (stretch goal)
- Codex CLI adapter ships in v0.2.0
- Listed on `awesome-claude-code` within 2 weeks
