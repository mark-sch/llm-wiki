# Contributing to llmwiki

Thanks for wanting to contribute. This project follows strict rules about commits, PRs, and privacy — please read this before opening a PR.

## Table of contents

- [Code of conduct](#code-of-conduct)
- [Dev setup](#dev-setup)
- [Project structure](#project-structure)
- [Commit + PR rules](#commit--pr-rules)
- [Adding a new adapter](#adding-a-new-adapter)
- [Privacy rules](#privacy-rules)
- [Testing](#testing)
- [Releases](#releases)

## Code of conduct

Be kind. Respect privacy. Prefer plain English to jargon. No scope creep.

## Dev setup

```bash
git clone https://github.com/Pratiyush/llm-wiki.git
cd llm-wiki
./setup.sh                # installs markdown + pygments, scaffolds raw/ wiki/ site/
python3 -m pytest tests/ -q
```

Requirements:

- Python ≥ 3.9
- `markdown` (required)
- `pygments` (optional — syntax highlighting)
- `ruff` (dev — lint)
- `pytest` (dev — tests)

No other runtime deps. That's a hard rule.

## Project structure

See [docs/architecture.md](docs/architecture.md) for the full breakdown. TL;DR:

```
llmwiki/              # Python package
├── cli.py            # argparse entry (init/sync/build/serve/adapters/version)
├── convert.py        # .jsonl → markdown
├── build.py          # markdown → HTML (god-level UI)
├── serve.py          # localhost HTTP server
├── adapters/         # session-store adapters (one per agent)
└── mcp/              # MCP server stub

.claude/              # Claude Code plugin surface
.claude-plugin/       # plugin.json + marketplace.json
.kiro/steering/       # always-loaded rules
docs/                 # user-facing + framework docs
tests/                # fixtures + snapshot tests
```

## Commit + PR rules

Adapted from the parent [Open Source Project Framework](docs/framework.md):

### Identity

- `git config user.name "Pratiyush"` (on this fork — you should use your own name on your fork)
- **Never** add `Co-authored-by: Claude`, `Co-authored-by: AI`, or similar AI attribution lines. Commits from this project are human-authored.

### PR size

- **One concern per PR.** Don't mix "add a new adapter" with "fix a CSS bug".
- **One file per PR preferred** unless the change is strictly atomic (e.g. test fixture + snapshot that must move together).
- **Small commits.** Each commit should tell a clear story.

### PR title format

- `add: <feature>` — new functionality
- `fix: <what>` — bug fix
- `docs: <what>` — docs only
- `chore: <what>` — refactor, dep bump, CI
- `test: <what>` — tests only

### PR body checklist

- What problem does this solve?
- How does this solution work?
- Which files changed and why?
- How did you test it?
- Any follow-up work left for a later PR?

### Branch protection

- Default branch is `master`.
- CI must pass before merge.

## Adding a new adapter

See [docs/framework.md §5.25 Adapter Flow](docs/framework.md) for the full contract. Minimum requirements:

1. **One file** under `llmwiki/adapters/<agent>.py` that:
   - Subclasses `BaseAdapter`
   - Registers itself via `@register("<agent>")`
   - Sets `session_store_path` to the agent's default location(s)
   - Declares `SUPPORTED_SCHEMA_VERSIONS`

2. **At least one fixture** under `tests/fixtures/<agent>/minimal.jsonl` — synthetic or heavily redacted.

3. **One snapshot test** under `tests/snapshots/<agent>/minimal.md` — the expected markdown output.

4. **One test** under `tests/test_<agent>_adapter.py` that runs the converter against the fixture and diffs against the snapshot.

5. **One documentation page** at `docs/adapters/<agent>.md`.

6. **A CHANGELOG entry** under `## [Unreleased]`.

7. **One line** in `README.md` under "Works with".

### Review checklist for adapter PRs

- [ ] Adapter declares `SUPPORTED_SCHEMA_VERSIONS`
- [ ] Fixture is under 50 KB and contains **no real PII**
- [ ] Snapshot test passes locally
- [ ] `docs/adapters/<agent>.md` exists and is linked from README
- [ ] Graceful degradation: unknown record types are skipped, not crashed on
- [ ] No new runtime deps introduced

## Privacy rules

llmwiki processes session transcripts that may contain PII, API keys, file paths, and secrets. These rules are **non-negotiable**:

1. **Redaction is on by default.** Username, API keys, tokens, passwords, and emails are redacted before anything hits `raw/`.
2. **Never commit real session data.** `raw/` is gitignored. Fixtures under `tests/fixtures/` must be synthetic or heavily redacted.
3. **Never commit machine-specific paths.** No `.claude/settings.local.json`, no `.ingestion-state.json`, no `.framework/`, no `.temp/`.
4. **Privacy grep** runs in CI: `grep -r "<real_username>" .` must return zero hits in committed files.
5. **No telemetry, ever.** The tool never calls home.
6. **Localhost-only binding by default.** The server binds to `127.0.0.1` unless the user explicitly passes `--host 0.0.0.0`.

## Testing

```bash
python3 -m pytest tests/ -q             # all tests
python3 -m pytest tests/test_convert.py # one file
python3 -m llmwiki build                # smoke test build
python3 -m llmwiki --version            # version check
```

Every adapter must ship with:

- A fixture (synthetic or heavily redacted)
- A snapshot test
- A graceful-degradation test (passes an unknown record type)

## Releases

`v0.x` is pre-production. API, schema, and file layout may change.

Release flow (Phase 6 of the framework):

1. Bump version in `llmwiki/__init__.py`
2. Update `CHANGELOG.md`
3. `git tag v0.x.y && git push origin v0.x.y`
4. Create a GitHub Release (mark pre-release for 0.x)
5. `.github/workflows/pages.yml` auto-deploys the demo site

## Questions?

Open an issue with the `question` label. Or ping [@Pratiyush](https://github.com/Pratiyush) on X.
