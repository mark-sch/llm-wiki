# llmwiki — Tasks

**Status Legend:** `[ ]` Not started · `[/]` In progress · `[x]` Done · `[-]` Cancelled

## Phase 1 — Validate
- [x] V1. Score /25 across Gap, Quality, Audience, Effort, Personal fit → **22/25 BUILD**
- [x] V2. Survey existing implementations and document the 10x gap

## Phase 2 — Brand
- [x] B1. Name: `llmwiki` (lowercase, one word — GitHub-friendly, no npm conflicts)
- [x] B2. Tagline: "LLM-powered knowledge base from your Claude Code and Codex CLI sessions"
- [x] B3. README header with badges (stars, license, Python version)
- [x] B4. LICENSE file (MIT)

## Phase 3 — Structure
- [x] S1. Define folder layout (`llmwiki/`, `bin/`, `docs/`, `.claude/commands/`, `.github/workflows/`)
- [x] S2. Decide stdlib + `markdown` only (no external deps by default, `pygments` optional)
- [x] S3. Adapter pattern for Claude Code + Codex CLI

## Phase 4 — Content
- [x] C1. Python package `llmwiki/` with `cli.py`, `convert.py`, `build.py`, `serve.py`
- [x] C2. Adapters: `adapters/claude_code.py`, `adapters/codex_cli.py` (stub), `adapters/base.py`
- [x] C3. God-level UI in `build.py` — Inter font, dark mode, search, keyboard shortcuts, breadcrumbs, syntax highlighting, collapsible sections
- [x] C4. CSS template (`templates/style.css`) and JS (`templates/script.js`) embedded as string constants
- [x] C5. One-click scripts: `setup.sh`, `setup.bat`, `build.sh`, `build.bat`, `sync.sh`, `sync.bat`, `serve.sh`, `serve.bat`
- [x] C6. `CLAUDE.md` schema for Claude Code with Ingest/Query/Lint workflows
- [x] C7. `AGENTS.md` schema for Codex CLI / other agents (same workflows, agent-agnostic phrasing)
- [x] C8. `.claude/commands/` slash commands (wiki-sync, wiki-build, wiki-serve, wiki-query, wiki-lint)
- [x] C9. `docs/` pages: getting-started, architecture, configuration, claude-code, codex-cli

## Phase 5 — Contribution
- [x] CT1. `CONTRIBUTING.md` with dev setup, PR rules
- [x] CT2. Issue templates (`.github/ISSUE_TEMPLATE/`)
- [x] CT3. PR template (`.github/PULL_REQUEST_TEMPLATE.md`)
- [x] CT4. CI workflow (`.github/workflows/ci.yml`) — Python lint + smoke test + build
- [x] CT5. `.gitignore` — framework files only, exclude user data

## Phase 5.5 — Pre-Launch QA
- [/] Q1. Run `setup.sh` end-to-end on a fresh copy of the repo
- [/] Q2. Verify `build.sh` produces a valid static site
- [/] Q3. Verify `serve.sh` binds to localhost and serves files
- [/] Q4. Link check README for broken URLs
- [ ] Q5. Test syntax highlighting with a real Python file
- [ ] Q6. Keyboard shortcuts work (`/` for search, `Cmd+K` for command palette)

## Phase 6 — Launch
- [ ] L1. `git init` with Pratiyush as author
- [ ] L2. Small atomic commits per file group
- [ ] L3. `gh repo create Pratiyush/llmwiki --public`
- [ ] L4. `git push origin master`
- [ ] L5. Git tag `v0.1.0` and GitHub prerelease

## Phase 7 — Grow
- [ ] G1. Dev.to launch post with screenshots
- [ ] G2. Reddit r/ClaudeAI + r/programming posts
- [ ] G3. Hacker News "Show HN"
- [ ] G4. X thread
- [ ] G5. Submit to `awesome-claude-code`

## Phase 8 — Maintain
- [ ] M1. Monthly: re-verify install scripts on macOS + Linux
- [ ] M2. Watch for Claude Code / Codex CLI format changes
- [ ] M3. Respond to issues within 48h

## Learning Log

- **2026-04-08**: Chose Python stdlib + `markdown` as the only mandatory deps. `pygments` for syntax highlighting is auto-detected but optional.
- **2026-04-08**: Codex CLI adapter shipped as a stub — will fill in when I have a Codex install to test against. Ships behind an adapter registry so adding a new agent is one file.
- **2026-04-08**: Karpathy's pattern requires `raw/` to be immutable and `wiki/` to be LLM-maintained. The HTML generator renders BOTH layers so partial wikis still work.
