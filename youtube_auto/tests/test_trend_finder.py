"""Tests unitaires pour TrendFinder (scoring et repli)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.trend_finder import TrendFinder  # noqa: E402


def test_fallback_topics_not_empty():
    topics = TrendFinder._fallback_topics("intelligence artificielle")
    assert len(topics) == 5
    assert all("topic" in t and "score" in t for t in topics)
    # Scores decroissants.
    scores = [t["score"] for t in topics]
    assert scores == sorted(scores, reverse=True)


def test_to_title():
    assert TrendFinder._to_title("  bonjour le monde ") == "Bonjour le monde"


def test_score_topic_length_bonus(monkeypatch):
    finder = TrendFinder()

    # Empeche tout appel reseau en forcant l'exception interne.
    def boom(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(finder, "_client", boom)

    short = finder.score_topic("IA")
    optimal = finder.score_topic("Les cinq metiers menaces par IA")
    assert optimal["score"] >= short["score"]
    assert optimal["recommended_title"]


def test_get_trending_topics_dedup(monkeypatch):
    finder = TrendFinder()

    def boom(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(finder, "_client", boom)
    topics = finder.get_trending_topics("intelligence artificielle")
    keys = [t["topic"].lower() for t in topics]
    assert len(keys) == len(set(keys))
