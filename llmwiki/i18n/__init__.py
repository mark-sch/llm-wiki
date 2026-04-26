"""i18n helpers — load translated prompts and seed files by language.

Supported languages: en, de.
To add a language, create the corresponding sub-directories under
llmwiki/i18n/prompts/ and llmwiki/i18n/seeds/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_I18N_ROOT = Path(__file__).parent


def available_languages() -> list[str]:
    """Return the list of languages that have at least a prompt directory."""
    prompts_dir = _I18N_ROOT / "prompts"
    if not prompts_dir.is_dir():
        return ["en"]
    return sorted(
        p.name
        for p in prompts_dir.iterdir()
        if p.is_dir() and (p / "source_page.md").is_file()
    )


def load_prompt_template(lang: str = "en") -> str:
    """Load the synthesis prompt template for *lang*.

    Falls back to English if the requested language has no prompt file.
    """
    path = _I18N_ROOT / "prompts" / lang / "source_page.md"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    fallback = _I18N_ROOT / "prompts" / "en" / "source_page.md"
    if fallback.is_file():
        return fallback.read_text(encoding="utf-8")
    raise FileNotFoundError(f"No prompt template found for {lang!r} or fallback en")


def load_seed(name: str, lang: str = "en") -> str:
    """Load a seed file by name and language.

    *name* is the filename including extension, e.g. ``"SOUL.md"``.
    Falls back to English if the translated version is missing.
    """
    path = _I18N_ROOT / "seeds" / lang / name
    if path.is_file():
        return path.read_text(encoding="utf-8")
    fallback = _I18N_ROOT / "seeds" / "en" / name
    if fallback.is_file():
        return fallback.read_text(encoding="utf-8")
    raise FileNotFoundError(f"No seed file {name!r} found for {lang!r} or fallback en")


def load_config_template(lang: str = "en") -> str:
    """Load the JSON config template for *lang*.

    Falls back to English if the requested language has no template.
    """
    path = _I18N_ROOT / "config" / f"{lang}.json"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    fallback = _I18N_ROOT / "config" / "en.json"
    if fallback.is_file():
        return fallback.read_text(encoding="utf-8")
    raise FileNotFoundError(f"No config template found for {lang!r} or fallback en")


def seed_exists(name: str, lang: str = "en") -> bool:
    """Return whether a seed file exists for the given language (or fallback)."""
    path = _I18N_ROOT / "seeds" / lang / name
    if path.is_file():
        return True
    fallback = _I18N_ROOT / "seeds" / "en" / name
    return fallback.is_file()
