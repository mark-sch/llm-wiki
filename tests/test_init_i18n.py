"""Tests for llmwiki init --language integration."""

import json
from argparse import Namespace
from pathlib import Path

import pytest

from llmwiki.cli import cmd_init


@pytest.fixture
def isolated_repo(tmp_path, monkeypatch):
    """Create a temporary repo root and monkeypatch REPO_ROOT."""
    import llmwiki.cli as cli_mod
    import llmwiki.convert as conv_mod
    import llmwiki.synth.pipeline as pipe_mod

    monkeypatch.setattr(cli_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(conv_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pipe_mod, "REPO_ROOT", tmp_path)

    # Also patch build.py if needed
    try:
        import llmwiki.build as build_mod
        monkeypatch.setattr(build_mod, "REPO_ROOT", tmp_path)
    except Exception:
        pass

    return tmp_path


class TestInitLanguageDe:
    def test_creates_config_json_with_language_de(self, isolated_repo):
        args = Namespace(language="de")
        rc = cmd_init(args)
        assert rc == 0

        config_path = isolated_repo / "config.json"
        assert config_path.is_file()
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        assert cfg["language"] == "de"

    def test_creates_wiki_prompts_source_page_md(self, isolated_repo):
        args = Namespace(language="de")
        rc = cmd_init(args)
        assert rc == 0

        prompt_path = isolated_repo / "wiki" / "prompts" / "source_page.md"
        assert prompt_path.is_file()
        text = prompt_path.read_text(encoding="utf-8")
        assert "Du pflegst" in text or "du pflegst" in text

    def test_seeds_german_soul_md(self, isolated_repo):
        args = Namespace(language="de")
        rc = cmd_init(args)
        assert rc == 0

        soul_path = isolated_repo / "wiki" / "SOUL.md"
        assert soul_path.is_file()
        text = soul_path.read_text(encoding="utf-8")
        assert "Wiki-Identität" in text

    def test_seeds_german_critical_facts_md(self, isolated_repo):
        args = Namespace(language="de")
        rc = cmd_init(args)
        assert rc == 0

        facts_path = isolated_repo / "wiki" / "CRITICAL_FACTS.md"
        assert facts_path.is_file()
        text = facts_path.read_text(encoding="utf-8")
        assert "unveränderlich" in text


class TestInitLanguageEn:
    def test_creates_config_json_with_language_en(self, isolated_repo):
        args = Namespace(language="en")
        rc = cmd_init(args)
        assert rc == 0

        config_path = isolated_repo / "config.json"
        assert config_path.is_file()
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        assert cfg["language"] == "en"

    def test_does_not_create_wiki_prompts_for_english(self, isolated_repo):
        args = Namespace(language="en")
        rc = cmd_init(args)
        assert rc == 0

        prompt_path = isolated_repo / "wiki" / "prompts" / "source_page.md"
        assert not prompt_path.exists()

    def test_seeds_english_soul_md(self, isolated_repo):
        args = Namespace(language="en")
        rc = cmd_init(args)
        assert rc == 0

        soul_path = isolated_repo / "wiki" / "SOUL.md"
        assert soul_path.is_file()
        text = soul_path.read_text(encoding="utf-8")
        assert "Wiki Identity" in text


class TestInitIdempotency:
    def test_does_not_overwrite_existing_config(self, isolated_repo):
        config_path = isolated_repo / "config.json"
        config_path.write_text(json.dumps({"language": "fr", "custom": True}), encoding="utf-8")

        args = Namespace(language="de")
        rc = cmd_init(args)
        assert rc == 0

        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        assert cfg["language"] == "fr"
        assert cfg["custom"] is True

    def test_does_not_overwrite_existing_seeds(self, isolated_repo):
        soul_path = isolated_repo / "wiki" / "SOUL.md"
        soul_path.parent.mkdir(parents=True, exist_ok=True)
        soul_path.write_text("# Custom SOUL\n", encoding="utf-8")

        args = Namespace(language="de")
        rc = cmd_init(args)
        assert rc == 0

        text = soul_path.read_text(encoding="utf-8")
        assert text == "# Custom SOUL\n"
