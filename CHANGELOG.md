# Changelog

All notable changes to **llmwiki** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versions below 1.0 are pre-production — API and file formats may change.

## [Unreleased]

## [0.1.0] — 2026-04-08

Initial public release.

### Added

- Python CLI (`python3 -m llmwiki`) with `sync`, `build`, `serve`, `init` subcommands
- Claude Code adapter (`llmwiki.adapters.claude_code`) — converts `~/.claude/projects/*/*.jsonl` to markdown
- Codex CLI adapter stub (`llmwiki.adapters.codex_cli`) — scaffold for v0.2
- Karpathy-style wiki schema in `CLAUDE.md` and `AGENTS.md`
- God-level HTML generator (`llmwiki.build`)
  - Inter + JetBrains Mono typography
  - Light/dark theme toggle with `data-theme` attribute + system preference
  - Global search via pre-built JSON index
  - Cmd+K command palette
  - Keyboard shortcuts (`/` search, `g h` home, `j/k` next/prev session)
  - Syntax highlighting via Pygments (optional dep)
  - Collapsible tool-result sections (click to expand, auto-collapse > 500 chars)
  - Breadcrumbs on session pages
  - Reading progress bar on long pages
  - Sticky table headers on the sessions index
  - Copy-as-markdown and copy-code buttons (with `document.execCommand` fallback for HTTP)
  - Mobile-responsive breakpoints
  - Print-friendly CSS
- One-click scripts for macOS/Linux (`setup.sh`, `build.sh`, `sync.sh`, `serve.sh`)
- One-click scripts for Windows (`setup.bat`, `build.bat`, `sync.bat`, `serve.bat`)
- `.claude/commands/` slash commands: `wiki-sync`, `wiki-build`, `wiki-serve`, `wiki-query`, `wiki-lint`
- `.claude/skills/llmwiki-sync/SKILL.md` — global skill for auto-discovery
- GitHub Actions CI workflow (`.github/workflows/ci.yml`) — lint + build smoke test
- Documentation: getting-started, architecture, configuration, claude-code, codex-cli
- Redaction config with username, API key, token, and email patterns
- Idempotent incremental sync via `.ingestion-state.json` mtime tracking
- Live-session detection — skips sessions with activity in the last 60 minutes
- Sub-agent session support — rendered as separate pages linked from parent
