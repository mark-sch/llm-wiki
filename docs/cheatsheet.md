---
title: "Command cheatsheet"
type: navigation
docs_shell: true
---

# Command cheatsheet

Everything you need on one page. Slash commands work inside Claude
Code / Codex CLI; CLI commands run at your terminal. `llmwiki serve`
starts the local browse.

## 30-second setup

```bash
cd your-project
llmwiki init          # scaffold raw/ wiki/ site/
llmwiki sync          # ingest sessions from every auto-detected agent
llmwiki build         # compile the static site
llmwiki serve --open  # browse at http://127.0.0.1:8765/
```

## Daily flow

| What you want | Slash command | CLI equivalent |
|---|---|---|
| Convert new session transcripts | `/wiki-sync` | `llmwiki sync` |
| Ingest a source file into the wiki | `/wiki-ingest <path>` | — (slash-driven workflow) |
| Ask the wiki a question | `/wiki-query <question>` | — (slash-driven workflow) |
| Edit one page surgically | `/wiki-update <page>` | — |
| Find orphans + broken links | `/wiki-lint` | `llmwiki lint` |
| Triage candidate pages | `/wiki-candidates` | `llmwiki candidates list` |
| Build / rebuild the site | `/wiki-build` | `llmwiki build` |
| Serve locally | `/wiki-serve` | `llmwiki serve --open` |
| Interactive graph | `/wiki-graph` | `llmwiki graph` |
| Slide deck from a topic | `/wiki-export-marp` | `llmwiki export-marp --topic …` |
| Self-reflection on wiki gaps | `/wiki-reflect` | — |

## Observability

| Question | Command |
|---|---|
| Who writes to wiki/? | `llmwiki log --limit 20` |
| Last sync results, per adapter | `llmwiki sync --status` |
| What sources failed? | `llmwiki quarantine list` |
| What references X? | `llmwiki references X` |
| Any near-duplicate tags? | `llmwiki tag check --threshold 0.85` |
| Cost of next synthesize run | `llmwiki synthesize --estimate` |

## Curate the tag space

```bash
llmwiki tag list                       # every tag + usage count
llmwiki tag rename obsidian Obsidian --dry-run   # preview
llmwiki tag rename obsidian Obsidian             # commit
llmwiki tag convention                 # projects use topics: / rest use tags:
```

## Curate backlinks

```bash
llmwiki backlinks --dry-run --verbose  # preview who would get backlinks
llmwiki backlinks                      # inject `## Referenced by` blocks
llmwiki backlinks --prune              # strip every block
```

## Adapters

```bash
llmwiki adapters --wide                # list every adapter + who fires on next sync
```

AI-session adapters (claude_code, codex_cli, cursor, copilot-chat,
gemini_cli, opencode, chatgpt, copilot-cli) fire by default. Non-AI
adapters (obsidian, jira, meeting, pdf) are opt-in — set
`{adapter}.enabled: true` in `sessions_config.json` to enable.

## Flags you'll actually use

| Flag | Command | What |
|---|---|---|
| `--since YYYY-MM-DD` | `sync`, `log` | Keep only entries after that date |
| `--project <slug>` | `sync` | Restrict to one project |
| `--force` | `sync`, `synthesize` | Ignore state file + raw-immutability guardrail |
| `--dry-run` | `sync`, `tag rename`, `backlinks` | Preview without writing |
| `--fail-on-errors` | `lint` | Non-zero exit on error-severity issues |
| `--vault <path>` | `sync`, `build` | Operate in-place on an Obsidian/Logseq vault |
| `--host 0.0.0.0` | `serve` | Bind LAN-accessible (default: loopback-only) |

## Config

| File | Purpose |
|---|---|
| `sessions_config.json` | Per-adapter enable + config (`{adapter: {enabled: true}}`) |
| `.llmwikiignore` | Exclude patterns (git-ignore format) |
| `.llmwiki-state.json` | Per-source mtime cache (auto; gitignored) |
| `.llmwiki-quarantine.json` | Convert failures (auto; gitignored) |
| `.env` | `ANTHROPIC_API_KEY` for API-mode synth |

## See also

- [CLI reference](reference/cli.md) — every flag of every subcommand
- [Slash commands reference](reference/slash-commands.md) — what each `/wiki-*` does
- [UI reference](reference/ui.md) — every screen on the compiled site
- [Upgrade guide](UPGRADING.md) — what changes between releases
