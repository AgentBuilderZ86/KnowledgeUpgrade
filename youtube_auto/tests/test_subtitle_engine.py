"""Tests unitaires pour SubtitleEngine (formatage timestamps & echappement)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.subtitle_engine import SubtitleEngine  # noqa: E402


def test_format_ts_zero():
    assert SubtitleEngine._format_ts(0) == "00:00:00,000"


def test_format_ts_precise():
    assert SubtitleEngine._format_ts(3661.5) == "01:01:01,500"


def test_format_ts_none():
    assert SubtitleEngine._format_ts(None) == "00:00:00,000"


def test_escape_for_filter_backslash():
    escaped = SubtitleEngine._escape_for_filter("C:\\videos\\out.srt")
    assert "\\:" in escaped
    assert "\\\\" not in escaped  # backslashes convertis en /
