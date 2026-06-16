"""Tests unitaires pour YouTubeUploader (normalisation des dates)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.youtube_uploader import YouTubeUploader  # noqa: E402


def test_iso8601_from_iso():
    out = YouTubeUploader._to_iso8601("2026-06-16T09:00:00")
    assert out.endswith("Z")


def test_iso8601_from_simple_format():
    out = YouTubeUploader._to_iso8601("2026-06-16 09:00")
    assert out.endswith("Z")
    assert out.startswith("2026-06-16")
