<!--
llmwiki PR template

Rules (from CONTRIBUTING.md):
- One concern per PR
- One file per PR preferred
- No `Co-authored-by: Claude` / AI attribution lines
- PR title format: add:/fix:/docs:/chore:/test: <short description>
-->

## What this PR does

<!-- 1-2 sentences -->

## Why

<!-- What problem does this solve? -->

## How

<!-- Brief summary of the approach. Link to an issue if there is one. -->

Closes #

## Files changed

<!-- Group by layer if multiple files -->

- `llmwiki/…` —
- `docs/…` —
- `tests/…` —

## How I tested this

- [ ] `python3 -m llmwiki --version`
- [ ] `python3 -m llmwiki adapters`
- [ ] `python3 -m pytest tests/ -q`
- [ ] `python3 -m llmwiki build` (smoke)
- [ ] Privacy grep clean: `grep -r "<my_username>" site/ wiki/` returns zero
- [ ] Manually verified in the browser at `http://127.0.0.1:8765/` (if UI changes)

## Checklist

- [ ] I read `CONTRIBUTING.md`
- [ ] CHANGELOG updated under `## [Unreleased]`
- [ ] Docs updated (if this changes behaviour)
- [ ] No new runtime deps added (or justified in the description)
- [ ] No AI co-authored-by lines in commits
- [ ] Branch targets `master`
