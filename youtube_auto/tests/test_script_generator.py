"""Tests unitaires pour ScriptGenerator (parsing et validation)."""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.script_generator import ScriptGenerator, Script  # noqa: E402


@pytest.fixture()
def config() -> dict:
    return {
        "channel": {
            "duree_cible_secondes": 120,
            "style": "explicatif",
            "langue": "fr",
        },
        "api": {"use_ollama": False, "claude_key": ""},
    }


def test_parse_json_plain():
    raw = '{"titre_video": "Test", "segments": []}'
    data = ScriptGenerator._parse_json(raw)
    assert data["titre_video"] == "Test"


def test_parse_json_with_markdown_fence():
    raw = '```json\n{"titre_video": "Test"}\n```'
    data = ScriptGenerator._parse_json(raw)
    assert data["titre_video"] == "Test"


def test_parse_json_embedded():
    raw = 'Voici le script :\n{"titre_video": "Test", "segments": []}\nMerci.'
    data = ScriptGenerator._parse_json(raw)
    assert data["titre_video"] == "Test"


def test_build_and_validate(config):
    gen = ScriptGenerator(config)
    data = {
        "titre_video": "Titre",
        "description_youtube": "desc",
        "tags": ["a", "b"],
        "titre_miniature": "Mini",
        "segments": [
            {
                "timestamp_debut": 0,
                "timestamp_fin": 30,
                "texte_narration": "Bonjour tout le monde",
                "image_query": "hello",
                "texte_ecran": "Intro",
            }
        ],
    }
    script = gen._build_script(data, "topic")
    assert isinstance(script, Script)
    gen._validate(script, 120)
    assert len(script.segments) == 1
    assert script.segments[0].duree == 30


def test_validate_fixes_bad_timestamps(config):
    gen = ScriptGenerator(config)
    data = {
        "titre_video": "T",
        "segments": [
            {
                "timestamp_debut": 0,
                "timestamp_fin": 0,  # incoherent
                "texte_narration": " ".join(["mot"] * 150),
                "image_query": "q",
            }
        ],
    }
    script = gen._build_script(data, "topic")
    gen._validate(script, 120)
    assert script.segments[0].timestamp_fin > 0


def test_validate_raises_on_empty(config):
    gen = ScriptGenerator(config)
    script = gen._build_script({"segments": []}, "topic")
    with pytest.raises(ValueError):
        gen._validate(script, 120)
