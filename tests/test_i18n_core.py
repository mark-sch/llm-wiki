"""Tests for llmwiki.i18n core helpers."""

import pytest

from llmwiki.i18n import available_languages, load_prompt_template, load_seed


class TestLoadPromptTemplate:
    def test_english_prompt_loads(self):
        text = load_prompt_template("en")
        assert "Karpathy-style LLM Wiki" in text
        assert "{body}" in text
        assert "{meta}" in text

    def test_german_prompt_loads(self):
        text = load_prompt_template("de")
        assert "Karpathy-style LLM Wiki" in text
        assert "{body}" in text
        assert "{meta}" in text
        # German-specific wording
        assert "Du pflegst" in text or "du pflegst" in text

    def test_unknown_language_falls_back_to_english(self):
        text = load_prompt_template("xx")
        assert "Karpathy-style LLM Wiki" in text


class TestLoadSeed:
    def test_english_seed_loads(self):
        text = load_seed("SOUL.md", "en")
        assert "Wiki Identity" in text

    def test_german_seed_loads(self):
        text = load_seed("SOUL.md", "de")
        assert "Wiki-Identität" in text

    def test_unknown_language_falls_back_to_english(self):
        text = load_seed("SOUL.md", "xx")
        assert "Wiki Identity" in text

    def test_nonexistent_seed_raises(self):
        with pytest.raises(FileNotFoundError):
            load_seed("NONEXISTENT.md", "en")


class TestAvailableLanguages:
    def test_lists_en_and_de(self):
        langs = available_languages()
        assert "en" in langs
        assert "de" in langs
