"""Tests for HTML lang attribute switching in build_site."""

import html
from pathlib import Path

import pytest

from llmwiki.build import build_site


@pytest.fixture
def minimal_raw(tmp_path, monkeypatch):
    """Set up a minimal raw/sessions tree so build_site doesn't abort."""
    import llmwiki.build as build_mod
    import llmwiki.convert as conv_mod

    monkeypatch.setattr(build_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(build_mod, "RAW_SESSIONS", tmp_path / "raw" / "sessions")
    monkeypatch.setattr(conv_mod, "REPO_ROOT", tmp_path)

    raw_sessions = tmp_path / "raw" / "sessions"
    raw_sessions.mkdir(parents=True)

    # One minimal session markdown
    session = raw_sessions / "testproj" / "2024-01-01-test.md"
    session.parent.mkdir(parents=True)
    session.write_text(
        '---\ntitle: "Test"\ntype: source\ntags: [test]\ndate: 2024-01-01\n'
        'source_file: raw/sessions/test.md\nproject: testproj\n---\n\n# Test\n',
        encoding="utf-8",
    )
    return tmp_path


class TestBuildLang:
    def test_default_lang_en(self, minimal_raw):
        out_dir = minimal_raw / "site"
        rc = build_site(out_dir=out_dir, lang="en")
        assert rc == 0

        index = out_dir / "index.html"
        assert index.is_file()
        text = index.read_text(encoding="utf-8")
        assert '<html lang="en"' in text

    def test_lang_de(self, minimal_raw):
        out_dir = minimal_raw / "site"
        rc = build_site(out_dir=out_dir, lang="de")
        assert rc == 0

        index = out_dir / "index.html"
        assert index.is_file()
        text = index.read_text(encoding="utf-8")
        assert '<html lang="de"' in text

    def test_session_page_lang_de(self, minimal_raw):
        out_dir = minimal_raw / "site"
        rc = build_site(out_dir=out_dir, lang="de")
        assert rc == 0

        session_html = out_dir / "sessions" / "testproj" / "2024-01-01-test.html"
        assert session_html.is_file()
        text = session_html.read_text(encoding="utf-8")
        assert '<html lang="de"' in text
        assert 'content="de"' in text

    def test_lang_is_escaped(self, minimal_raw):
        out_dir = minimal_raw / "site"
        # Pass a string that would break HTML if unescaped
        rc = build_site(out_dir=out_dir, lang='de" onclick="alert(1)')
        assert rc == 0

        index = out_dir / "index.html"
        text = index.read_text(encoding="utf-8")
        assert html.escape('de" onclick="alert(1)') in text
