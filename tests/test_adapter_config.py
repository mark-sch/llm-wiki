"""Tests for adapter config validation (v1.0, #177)."""

from __future__ import annotations

import pytest

from llmwiki.adapter_config import (
    ADAPTER_SCHEMAS,
    validate_adapter_config,
    validate_all_adapters,
    is_adapter_enabled,
    enabled_adapters,
    apply_defaults,
)


# ─── Schemas ───────────────────────────────────────────────────────────


def test_four_adapters_schemas_defined():
    assert set(ADAPTER_SCHEMAS.keys()) == {"pdf", "meeting", "jira", "web_clipper"}


def test_every_schema_has_required_fields():
    for name, schema in ADAPTER_SCHEMAS.items():
        assert "required_if_enabled" in schema
        assert "defaults" in schema
        assert "types" in schema


# ─── validate_adapter_config ─────────────────────────────────────────


def test_disabled_adapter_always_valid():
    config = {"jira": {"enabled": False}}
    errors = validate_adapter_config(config, "jira")
    assert errors == []


def test_missing_section_valid():
    """No config for an adapter is treated as disabled."""
    errors = validate_adapter_config({}, "meeting")
    assert errors == []


def test_enabled_meeting_without_source_dirs():
    config = {"meeting": {"enabled": True}}
    errors = validate_adapter_config(config, "meeting")
    assert len(errors) == 1
    assert "source_dirs" in errors[0]


def test_enabled_jira_missing_credentials():
    config = {"jira": {"enabled": True, "server": "https://jira.example.com"}}
    errors = validate_adapter_config(config, "jira")
    # email + api_token missing
    assert len(errors) == 2


def test_enabled_jira_empty_api_token():
    config = {
        "jira": {
            "enabled": True,
            "server": "https://jira.example.com",
            "email": "me@example.com",
            "api_token": "",
        }
    }
    errors = validate_adapter_config(config, "jira")
    assert any("api_token" in e and "empty" in e for e in errors)


def test_fully_configured_jira_valid():
    config = {
        "jira": {
            "enabled": True,
            "server": "https://jira.example.com",
            "email": "me@example.com",
            "api_token": "secret",
        }
    }
    errors = validate_adapter_config(config, "jira")
    assert errors == []


def test_wrong_type_flagged():
    config = {
        "meeting": {
            "enabled": True,
            "source_dirs": "/single/path",  # should be list
        }
    }
    errors = validate_adapter_config(config, "meeting")
    assert any("source_dirs" in e and "list" in e for e in errors)


def test_unknown_adapter():
    errors = validate_adapter_config({}, "bogus")
    assert len(errors) == 1
    assert "unknown adapter" in errors[0]


def test_non_dict_section_flagged():
    config = {"meeting": "not a dict"}
    errors = validate_adapter_config(config, "meeting")
    assert len(errors) == 1
    assert "JSON object" in errors[0]


# ─── is_adapter_enabled ───────────────────────────────────────────────


def test_is_enabled_true():
    assert is_adapter_enabled({"jira": {"enabled": True}}, "jira") is True


def test_is_enabled_false():
    assert is_adapter_enabled({"jira": {"enabled": False}}, "jira") is False


def test_is_enabled_missing():
    assert is_adapter_enabled({}, "jira") is False


def test_is_enabled_non_dict():
    assert is_adapter_enabled({"jira": "str"}, "jira") is False


# ─── enabled_adapters ─────────────────────────────────────────────────


def test_enabled_adapters_empty():
    assert enabled_adapters({}) == []


def test_enabled_adapters_some():
    config = {
        "pdf": {"enabled": True},
        "meeting": {"enabled": False},
        "jira": {"enabled": True},
    }
    result = enabled_adapters(config)
    assert set(result) == {"pdf", "jira"}


# ─── apply_defaults ───────────────────────────────────────────────────


def test_apply_defaults_fills_missing():
    config = {"meeting": {"enabled": True, "source_dirs": ["/foo"]}}
    result = apply_defaults(config, "meeting")
    assert result["extensions"] == [".vtt", ".srt"]  # default applied


def test_apply_defaults_preserves_user_values():
    config = {"meeting": {"enabled": True, "extensions": [".txt"]}}
    result = apply_defaults(config, "meeting")
    assert result["extensions"] == [".txt"]  # not overwritten


def test_apply_defaults_unknown_adapter():
    result = apply_defaults({}, "unknown")
    assert result == {}


# ─── validate_all_adapters ────────────────────────────────────────────


def test_validate_all_returns_entries_for_every_adapter():
    result = validate_all_adapters({})
    assert set(result.keys()) == {"pdf", "meeting", "jira", "web_clipper"}
    assert all(errors == [] for errors in result.values())


def test_validate_all_flags_misconfigured():
    config = {
        "pdf": {"enabled": True},  # missing source_dirs
        "jira": {"enabled": False},
    }
    result = validate_all_adapters(config)
    assert result["pdf"]  # errors
    assert result["jira"] == []  # disabled = valid
