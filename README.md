# llmwiki

> **LLM-powered knowledge base from your Claude Code and Codex CLI sessions.**
> Built on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Works with Claude Code](https://img.shields.io/badge/Claude%20Code-✓-7C3AED.svg)](https://claude.com/claude-code)
[![Works with Codex CLI](https://img.shields.io/badge/Codex%20CLI-✓-7C3AED.svg)](https://github.com/openai/codex)

---

Every Claude Code and Codex CLI session writes a full transcript to disk. You already have hundreds of them and never look at them again.

**llmwiki** turns that dormant history into a beautiful, searchable, interlinked knowledge base — locally, in two commands.

```bash
./setup.sh                         # one-time install
./build.sh && ./serve.sh           # build + serve at http://127.0.0.1:8765
```

## What you get

- **All your sessions**, converted from `.jsonl` to clean, redacted markdown
- **A Karpathy-style wiki** — `sources/`, `entities/`, `concepts/`, linked with `[[wikilinks]]`
- **A beautiful static site** you can browse locally or deploy to GitHub Pages
  - Global search (Cmd+K command palette)
  - Syntax highlighting (Pygments)
  - Dark mode (system-aware + manual toggle)
  - Keyboard shortcuts (`/` search, `g h` home, `j/k` next/prev)
  - Collapsible tool-result sections
  - Copy-as-markdown + copy-code buttons
  - Mobile-responsive
- **SessionStart hook** — auto-syncs new sessions in the background on every Claude Code launch
- **No servers, no database, no npm** — Python stdlib + `markdown`

## How it works

```
┌─────────────────────────────────────┐
│  ~/.claude/projects/*/*.jsonl       │  ← Claude Code sessions
│  ~/.codex/sessions/**/*.jsonl       │  ← Codex CLI sessions
└──────────────┬──────────────────────┘
               │
               ▼   python3 -m llmwiki sync
┌─────────────────────────────────────┐
│  raw/sessions/<project>/            │  ← immutable markdown (Karpathy layer 1)
│     2026-04-08-<slug>.md            │
└──────────────┬──────────────────────┘
               │
               ▼   /wiki-ingest  (your coding agent)
┌─────────────────────────────────────┐
│  wiki/sources/<slug>.md             │  ← LLM-generated wiki (Karpathy layer 2)
│  wiki/entities/<Name>.md            │
│  wiki/concepts/<Name>.md            │
│  wiki/index.md, overview.md, log.md │
└──────────────┬──────────────────────┘
               │
               ▼   python3 -m llmwiki build
┌─────────────────────────────────────┐
│  site/                              │  ← static HTML site
│     index.html, style.css, ...      │
└─────────────────────────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for the full Karpathy three-layer breakdown.

## Install

### macOS / Linux

```bash
git clone https://github.com/Pratiyush/llmwiki.git
cd llmwiki
./setup.sh
```

### Windows

```cmd
git clone https://github.com/Pratiyush/llmwiki.git
cd llmwiki
setup.bat
```

### What setup does

1. Creates `raw/`, `wiki/`, `site/` data directories
2. Installs the `llmwiki` Python package in-place (no `pip install` needed — just stdlib)
3. Detects Claude Code and/or Codex CLI and enables the matching adapter
4. Optionally offers to install the `SessionStart` hook into `~/.claude/settings.json` for auto-sync
5. Runs a first sync so you see output immediately

## Commands

All commands are one-click shell scripts. Under the hood they call `python3 -m llmwiki <subcommand>`.

| Command | What it does | Shell | Windows |
|---|---|---|---|
| Install | Bootstrap + first sync | `./setup.sh` | `setup.bat` |
| Sync | Convert new `.jsonl` → markdown | `./sync.sh` | `sync.bat` |
| Build | Compile wiki + HTML | `./build.sh` | `build.bat` |
| Serve | Start local HTTP server | `./serve.sh` | `serve.bat` |
| Query (agent) | Ask your wiki | `/wiki-query ...` | `/wiki-query ...` |
| Lint | Check orphans / stale pages | `/wiki-lint` | `/wiki-lint` |

See [docs/getting-started.md](docs/getting-started.md) for full usage.

## Works with

| Agent | Adapter | Status |
|---|---|---|
| [Claude Code](https://claude.com/claude-code) | `llmwiki.adapters.claude_code` | ✅ Production |
| [Codex CLI](https://github.com/openai/codex) | `llmwiki.adapters.codex_cli` | 🚧 Stub (v0.2) |
| Gemini CLI | `llmwiki.adapters.gemini_cli` | ⏳ Planned |
| OpenCode | `llmwiki.adapters.opencode` | ⏳ Planned |

Adding a new agent is [one small file](docs/architecture.md#adding-an-adapter).

## Configuration

Single JSON config at `examples/sessions_config.json`. Copy to `config.json` and edit:

```json
{
  "filters": {
    "live_session_minutes": 60,
    "exclude_projects": []
  },
  "redaction": {
    "real_username": "YOUR_USERNAME",
    "replacement_username": "USER",
    "extra_patterns": [
      "(?i)(api[_-]?key|secret|token|bearer|password)...",
      "sk-[A-Za-z0-9]{20,}"
    ]
  },
  "truncation": {
    "tool_result_chars": 500,
    "bash_stdout_lines": 5
  }
}
```

All paths, regexes, and truncation limits are tunable. See [docs/configuration.md](docs/configuration.md).

## Karpathy's LLM Wiki pattern

This project follows the three-layer structure described in [Karpathy's gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f):

1. **Raw sources** (`raw/`) — immutable. Session transcripts converted from `.jsonl`.
2. **The wiki** (`wiki/`) — LLM-generated. One page per entity, concept, source. Interlinked via `[[wikilinks]]`.
3. **The schema** (`CLAUDE.md`, `AGENTS.md`) — tells your agent how to ingest and query.

See [docs/architecture.md](docs/architecture.md) for the full breakdown and how it maps to the file tree.

## Design principles

- **Stdlib first** — only mandatory runtime dep is `markdown`. `pygments` is optional.
- **Works offline** — no CDN, no fonts from Google by default (use system fonts).
- **Redact by default** — username, API keys, tokens, emails all get redacted before entering the wiki.
- **Idempotent everything** — re-running any command is safe and cheap.
- **Agent-agnostic core** — the converter doesn't know which agent produced the `.jsonl`; adapters translate.

## Acknowledgements

- [Andrej Karpathy](https://twitter.com/karpathy) for [the LLM Wiki idea](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [SamurAIGPT/llm-wiki-agent](https://github.com/SamurAIGPT/llm-wiki-agent), [lucasastorian/llmwiki](https://github.com/lucasastorian/llmwiki), [xoai/sage-wiki](https://github.com/xoai/sage-wiki), and [bashiraziz/llm-wiki-template](https://github.com/bashiraziz/llm-wiki-template) — prior art that shaped this.
- [Python Markdown](https://python-markdown.github.io/) and [Pygments](https://pygments.org/) for the rendering pipeline.

## License

[MIT](LICENSE) © Pratiyush
