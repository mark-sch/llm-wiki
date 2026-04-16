"""Tests for the Jira REST API adapter (v1.0, #147).

These tests mock the jira library so they run without a Jira server.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from llmwiki.adapters.jira_adapter import (
    JiraAdapter,
    convert_jira_description,
    render_ticket_markdown,
    _jira_available,
)


# ─── Jira description conversion ──────────────────────────────────────


def test_convert_empty_description():
    assert convert_jira_description("") == ""


def test_convert_none_description():
    assert convert_jira_description("") == ""


def test_convert_code_blocks():
    text = convert_jira_description("{code:java}public class Foo{}{code}")
    assert "```" in text


def test_convert_headings():
    text = convert_jira_description("h1. Title\nh2. Subtitle")
    assert "# Title" in text
    assert "## Subtitle" in text


def test_convert_links():
    text = convert_jira_description("[Google|https://google.com]")
    assert "[Google](https://google.com)" in text


def test_convert_noformat():
    text = convert_jira_description("{noformat}some text{noformat}")
    assert "```" in text


# ─── Ticket markdown rendering ────────────────────────────────────────


SAMPLE_TICKET = {
    "key": "PROJ-123",
    "summary": "Fix login timeout bug",
    "status": "In Progress",
    "assignee": "alice",
    "reporter": "bob",
    "created": "2026-04-10T10:30:00Z",
    "updated": "2026-04-15T14:00:00Z",
    "description": "The login page times out after 30 seconds.",
    "labels": ["bug", "auth"],
    "priority": "High",
    "issue_type": "Bug",
    "project": "PROJ",
}


def test_render_ticket_frontmatter():
    md = render_ticket_markdown(SAMPLE_TICKET)
    assert md.startswith("---\n")
    assert "type: source" in md
    assert "jira_key: PROJ-123" in md
    assert "jira_status: In Progress" in md


def test_render_ticket_title():
    md = render_ticket_markdown(SAMPLE_TICKET)
    assert "# PROJ-123: Fix login timeout bug" in md


def test_render_ticket_labels():
    md = render_ticket_markdown(SAMPLE_TICKET)
    assert "**Labels:** bug, auth" in md


def test_render_ticket_description():
    md = render_ticket_markdown(SAMPLE_TICKET)
    assert "## Description" in md
    assert "login page times out" in md


def test_render_ticket_connections():
    md = render_ticket_markdown(SAMPLE_TICKET)
    assert "## Connections" in md


def test_render_ticket_no_description():
    ticket = {**SAMPLE_TICKET, "description": ""}
    md = render_ticket_markdown(ticket)
    assert "## Description" not in md


def test_render_ticket_no_labels():
    ticket = {**SAMPLE_TICKET, "labels": []}
    md = render_ticket_markdown(ticket)
    assert "**Labels:**" not in md


def test_render_ticket_date_in_frontmatter():
    md = render_ticket_markdown(SAMPLE_TICKET)
    assert "date: 2026-04-10" in md


# ─── Adapter class ────────────────────────────────────────────────────


def test_adapter_not_available_by_default():
    assert JiraAdapter.is_available() is False


def test_adapter_discover_returns_empty():
    adapter = JiraAdapter()
    assert adapter.discover_sessions() == []


def test_adapter_config_parsing():
    adapter = JiraAdapter(config={
        "jira": {
            "enabled": True,
            "server": "https://jira.example.com",
            "email": "user@example.com",
            "api_token": "secret",
            "jql": "project = DEMO",
            "max_results": 100,
        }
    })
    assert adapter._enabled is True
    assert adapter._server == "https://jira.example.com"
    assert adapter._jql == "project = DEMO"
    assert adapter._max_results == 100


def test_adapter_available_without_jira_lib():
    """Even with config, unavailable if jira lib not installed."""
    adapter = JiraAdapter(config={
        "jira": {
            "enabled": True,
            "server": "https://jira.example.com",
            "email": "x",
            "api_token": "x",
        }
    })
    with patch("llmwiki.adapters.jira_adapter._jira_available", return_value=False):
        assert adapter.is_available_with_config() is False


def test_adapter_available_with_everything():
    adapter = JiraAdapter(config={
        "jira": {
            "enabled": True,
            "server": "https://jira.example.com",
            "email": "x",
            "api_token": "x",
        }
    })
    with patch("llmwiki.adapters.jira_adapter._jira_available", return_value=True):
        assert adapter.is_available_with_config() is True


def test_adapter_missing_server():
    adapter = JiraAdapter(config={
        "jira": {"enabled": True, "email": "x", "api_token": "x"}
    })
    with patch("llmwiki.adapters.jira_adapter._jira_available", return_value=True):
        assert adapter.is_available_with_config() is False
