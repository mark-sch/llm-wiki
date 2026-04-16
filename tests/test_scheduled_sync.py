"""Tests for configurable scheduled sync generation (v1.0, #162)."""

from __future__ import annotations

import pytest

from llmwiki.scheduled_sync import (
    load_sync_schedule,
    detect_platform,
    render_launchd_plist,
    render_systemd_service,
    render_systemd_timer,
    render_windows_task,
    generate,
    install_instructions,
)


# ─── Config loading ──────────────────────────────────────────────────


def test_defaults():
    sched = load_sync_schedule({})
    assert sched["enabled"] is False
    assert sched["cadence"] == "daily"
    assert sched["hour"] == 3
    assert sched["minute"] == 0


def test_custom_cadence():
    sched = load_sync_schedule({
        "scheduled_sync": {"cadence": "weekly", "hour": 9, "minute": 30}
    })
    assert sched["cadence"] == "weekly"
    assert sched["hour"] == 9
    assert sched["minute"] == 30


def test_cadence_lowercased():
    sched = load_sync_schedule({"scheduled_sync": {"cadence": "WEEKLY"}})
    assert sched["cadence"] == "weekly"


# ─── Platform detection ──────────────────────────────────────────────


def test_detect_platform_returns_valid():
    plat = detect_platform()
    assert plat in {"macos", "linux", "windows", "unknown"}


# ─── launchd ─────────────────────────────────────────────────────────


def test_launchd_plist_has_shebang():
    plist = render_launchd_plist(load_sync_schedule({}))
    assert plist.startswith("<?xml")
    assert "<plist" in plist


def test_launchd_daily_uses_calendar():
    plist = render_launchd_plist(load_sync_schedule({
        "scheduled_sync": {"cadence": "daily", "hour": 5, "minute": 15}
    }))
    assert "StartCalendarInterval" in plist
    assert "<integer>5</integer>" in plist
    assert "<integer>15</integer>" in plist


def test_launchd_weekly_includes_weekday():
    plist = render_launchd_plist(load_sync_schedule({
        "scheduled_sync": {"cadence": "weekly", "weekday": 3}
    }))
    assert "Weekday" in plist
    assert "<integer>3</integer>" in plist


def test_launchd_hourly_uses_interval():
    plist = render_launchd_plist(load_sync_schedule({
        "scheduled_sync": {"cadence": "hourly"}
    }))
    assert "StartInterval" in plist
    assert "<integer>3600</integer>" in plist


def test_launchd_includes_binary_path():
    plist = render_launchd_plist(load_sync_schedule({
        "scheduled_sync": {"llmwiki_bin": "/opt/custom/bin/llmwiki"}
    }))
    assert "/opt/custom/bin/llmwiki" in plist


# ─── systemd ─────────────────────────────────────────────────────────


def test_systemd_service_shape():
    svc = render_systemd_service(load_sync_schedule({}))
    assert "[Service]" in svc
    assert "ExecStart=" in svc
    assert "[Install]" in svc


def test_systemd_timer_daily():
    timer = render_systemd_timer(load_sync_schedule({
        "scheduled_sync": {"cadence": "daily", "hour": 4, "minute": 30}
    }))
    assert "OnCalendar=" in timer
    assert "04:30" in timer


def test_systemd_timer_hourly():
    timer = render_systemd_timer(load_sync_schedule({
        "scheduled_sync": {"cadence": "hourly"}
    }))
    assert "OnCalendar=hourly" in timer


def test_systemd_timer_weekly():
    timer = render_systemd_timer(load_sync_schedule({
        "scheduled_sync": {"cadence": "weekly", "weekday": 1}  # Monday
    }))
    assert "Mon" in timer


# ─── Windows Task Scheduler ──────────────────────────────────────────


def test_windows_task_shape():
    task = render_windows_task(load_sync_schedule({}))
    assert task.startswith("<?xml")
    assert "<Task" in task
    assert "<Actions" in task


def test_windows_daily_calendar_trigger():
    task = render_windows_task(load_sync_schedule({
        "scheduled_sync": {"cadence": "daily"}
    }))
    assert "ScheduleByDay" in task


def test_windows_weekly_calendar_trigger():
    task = render_windows_task(load_sync_schedule({
        "scheduled_sync": {"cadence": "weekly"}
    }))
    assert "ScheduleByWeek" in task


def test_windows_hourly_repetition():
    task = render_windows_task(load_sync_schedule({
        "scheduled_sync": {"cadence": "hourly"}
    }))
    assert "Repetition" in task
    assert "PT1H" in task


# ─── generate + install_instructions ────────────────────────────────


def test_generate_macos():
    outputs = generate("macos", {})
    assert "com.llmwiki.sync.plist" in outputs


def test_generate_linux_has_both_units():
    outputs = generate("linux", {})
    assert "llmwiki-sync.service" in outputs
    assert "llmwiki-sync.timer" in outputs


def test_generate_windows():
    outputs = generate("windows", {})
    assert "llmwiki-sync-task.xml" in outputs


def test_generate_unsupported():
    assert generate("plan9", {}) == {}


def test_install_instructions_macos():
    inst = install_instructions("macos")
    assert "launchctl" in inst
    assert "LaunchAgents" in inst


def test_install_instructions_linux():
    inst = install_instructions("linux")
    assert "systemctl" in inst
    assert "timer" in inst


def test_install_instructions_windows():
    inst = install_instructions("windows")
    assert "schtasks" in inst


def test_install_instructions_unknown():
    inst = install_instructions("plan9")
    assert "Unsupported" in inst
