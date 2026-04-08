---
title: "Session: curious-parsing-ada — 2026-04-01"
type: source
tags: [claude-code, session-transcript, demo]
date: 2026-04-01
source_file: raw/sessions/demo-alpha/2026-04-01-curious-parsing-ada.md
sessionId: demo-alpha-001
slug: curious-parsing-ada
project: demo-alpha
started: 2026-04-01T09:15:00+00:00
ended: 2026-04-01T09:42:18+00:00
cwd: /Users/USER/Desktop/demo-alpha
gitBranch: master
permissionMode: default
model: claude-sonnet-4-6
user_messages: 3
tool_calls: 5
tools_used: [Bash, Read, Write]
is_subagent: false
---

# Session: curious-parsing-ada — 2026-04-01

**Project:** `demo-alpha` · **Branch:** `master` · **Mode:** `default` · **Model:** `claude-sonnet-4-6`

**Stats:** 3 user messages, 5 tool calls, tools used: Bash, Read, Write.

## Conversation

### Turn 1 — User

Set up a small Python project with a CLI entry point and a pyproject.toml.

### Turn 1 — Assistant

I'll scaffold a minimal Python project with a CLI entry and a pyproject.toml.

**Tools used:**

- `Bash`: `mkdir -p /Users/USER/Desktop/demo-alpha/src/democli`
- `Write`: `/Users/USER/Desktop/demo-alpha/pyproject.toml` (412 chars)

```toml
[project]
name = "democli"
version = "0.1.0"
description = "A tiny demo CLI"
requires-python = ">=3.9"

[project.scripts]
democli = "democli.cli:main"

[build-system]
requires = ["setuptools>=64"]
build-backend = "setuptools.build_meta"
```

**Tools used:**

- `Write`: `/Users/USER/Desktop/demo-alpha/src/democli/__init__.py` (38 chars)

```python
"""democli — a tiny demo CLI."""
__version__ = "0.1.0"
```

**Tools used:**

- `Write`: `/Users/USER/Desktop/demo-alpha/src/democli/cli.py` (256 chars)

```python
import argparse

def main() -> int:
    parser = argparse.ArgumentParser(prog="democli")
    parser.add_argument("--name", default="world")
    args = parser.parse_args()
    print(f"hello, {args.name}")
    return 0
```

Project scaffolded. You can install it in editable mode with `pip install -e .` and run `democli --name alice`.

### Turn 2 — User

Add a test file that runs the CLI and checks output.

### Turn 2 — Assistant

**Tools used:**

- `Write`: `/Users/USER/Desktop/demo-alpha/tests/test_cli.py` (228 chars)

```python
import subprocess, sys

def test_hello_default():
    r = subprocess.run([sys.executable, "-m", "democli.cli"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "hello, world" in r.stdout
```

Test added. Run with `pytest tests/ -q` after editable install.

### Turn 3 — User

Thanks, that's enough for today.

### Turn 3 — Assistant

All set. Session summary: a minimal Python CLI package with pyproject.toml, a single `main()` entry point, and one smoke test. Next session can add argparse subcommands or publish to PyPI.
