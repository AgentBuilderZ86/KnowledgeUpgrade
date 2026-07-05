"""Generation du script video via Claude API ou Ollama local."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Tu es un scenariste YouTube expert en videos educatives virales.
Genere un script complet pour une video YouTube faceless.

CONTRAINTES STRICTES :
- Duree cible : {duree} secondes de narration
- Style : {style}
- Langue : {langue}
- Accroche dans les 15 premieres secondes (hook fort)
- Chaque segment doit avoir un timestamp et une query image associee
- Terminer par un call-to-action (like + abonnement)
- Ton : conversationnel, informatif, jamais robotique

FORMAT DE SORTIE JSON OBLIGATOIRE (aucun texte hors du JSON) :
{{
  "titre_video": "...",
  "description_youtube": "... (500 mots SEO-optimise)",
  "tags": ["tag1", "tag2"],
  "segments": [
    {{
      "timestamp_debut": 0,
      "timestamp_fin": 25,
      "texte_narration": "...",
      "image_query": "mot-cle anglais pour Pexels",
      "texte_ecran": "texte court affiche sur la video (optionnel)"
    }}
  ],
  "titre_miniature": "texte court percutant pour la miniature"
}}"""

USER_PROMPT = """Sujet de la video : {topic}

Genere le script JSON complet pour ce sujet en respectant scrupuleusement le
format demande. La somme des durees des segments doit avoisiner {duree} secondes."""


@dataclass
class Segment:
    """Un segment du script avec sa narration et ses metadonnees visuelles."""

    timestamp_debut: float
    timestamp_fin: float
    texte_narration: str
    image_query: str
    texte_ecran: str = ""
    audio_path: str | None = None
    duree_reelle: float | None = None

    @property
    def duree(self) -> float:
        """Duree theorique du segment en secondes."""
        return max(0.0, self.timestamp_fin - self.timestamp_debut)


@dataclass
class Script:
    """Script video complet retourne par le generateur."""

    titre_video: str
    description_youtube: str
    tags: list[str]
    segments: list[Segment]
    titre_miniature: str
    topic: str = ""

    def as_metadata(self) -> dict[str, Any]:
        """Metadonnees pretes pour l'upload YouTube."""
        return {
            "title": self.titre_video,
            "description": self.description_youtube,
            "tags": self.tags,
        }


class ScriptGenerator:
    """Genere un script structure via Claude (cloud) ou Ollama (local)."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise le generateur a partir de la configuration.

        Args:
            config: Dictionnaire de configuration complet (config.yaml resolu).
        """
        self.config = config
        api_cfg = config.get("api", {})
        self.use_ollama: bool = bool(api_cfg.get("use_ollama", False))
        self.claude_key: str = api_cfg.get("claude_key", "") or ""
        self.claude_model: str = api_cfg.get("claude_model", "claude-haiku-4-5-20251001")
        self.ollama_model: str = api_cfg.get("ollama_model", "llama3")
        self.ollama_host: str = api_cfg.get("ollama_host", "http://localhost:11434")

    def generate(self, topic: str, config: dict[str, Any] | None = None) -> Script:
        """Genere et valide un script complet pour un sujet donne.

        Args:
            topic: Le sujet de la video.
            config: Configuration optionnelle ; par defaut celle de l'instance.

        Returns:
            Un objet ``Script`` valide.
        """
        cfg = config or self.config
        channel = cfg.get("channel", {})
        duree = channel.get("duree_cible_secondes", 480)
        style = channel.get("style", "informatif-dynamique")
        langue = channel.get("langue", "fr")

        system = SYSTEM_PROMPT.format(duree=duree, style=style, langue=langue)
        user = USER_PROMPT.format(topic=topic, duree=duree)

        if self.use_ollama or not self.claude_key:
            if not self.use_ollama and not self.claude_key:
                logger.warning(
                    "Aucune cle Claude detectee - bascule automatique sur Ollama (%s).",
                    self.ollama_model,
                )
            raw = self._call_ollama(system, user)
        else:
            raw = self._call_claude(system, user)

        data = self._parse_json(raw)
        script = self._build_script(data, topic)
        self._validate(script, duree)
        logger.info(
            "Script genere : '%s' (%d segments).", script.titre_video, len(script.segments)
        )
        return script

    def _call_claude(self, system: str, user: str) -> str:
        """Appelle l'API Claude et retourne le texte brut de la reponse."""
        import anthropic
        import os

        # Force UTF-8 sur les headers HTTP
        os.environ['LC_ALL'] = 'C.UTF-8'
        os.environ['LANG'] = 'C.UTF-8'

        # Encode explicitement en UTF-8
        system = system.encode('utf-8').decode('utf-8') if isinstance(system, str) else system
        user = user.encode('utf-8').decode('utf-8') if isinstance(user, str) else user

        client = anthropic.Anthropic(api_key=self.claude_key)
        message = client.messages.create(
            model=self.claude_model,
            max_tokens=8192,
            temperature=0.8,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )

    def _call_ollama(self, system: str, user: str) -> str:
        """Appelle Ollama en local et retourne le texte brut de la reponse."""
        import requests

        url = f"{self.ollama_host.rstrip('/')}/api/generate"
        payload = {
            "model": self.ollama_model,
            "prompt": f"{system}\n\n{user}",
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.8},
        }
        resp = requests.post(url, json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json().get("response", "")

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        """Extrait et parse le bloc JSON d'une reponse LLM."""
        raw = raw.strip()
        # Retire d'eventuelles balises markdown ```json ... ```
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Tente d'isoler le premier objet JSON complet.
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise ValueError("Impossible de parser le JSON renvoye par le LLM.")

    @staticmethod
    def _build_script(data: dict[str, Any], topic: str) -> Script:
        """Construit un objet ``Script`` a partir du dictionnaire parse."""
        segments = [
            Segment(
                timestamp_debut=float(seg.get("timestamp_debut", 0)),
                timestamp_fin=float(seg.get("timestamp_fin", 0)),
                texte_narration=str(seg.get("texte_narration", "")).strip(),
                image_query=str(seg.get("image_query", topic)).strip(),
                texte_ecran=str(seg.get("texte_ecran", "")).strip(),
            )
            for seg in data.get("segments", [])
        ]
        return Script(
            titre_video=str(data.get("titre_video", topic)).strip(),
            description_youtube=str(data.get("description_youtube", "")).strip(),
            tags=[str(t).strip() for t in data.get("tags", []) if str(t).strip()],
            segments=segments,
            titre_miniature=str(data.get("titre_miniature", topic)).strip(),
            topic=topic,
        )

    @staticmethod
    def _validate(script: Script, duree_cible: int) -> None:
        """Valide la coherence du script (segments, timestamps)."""
        if not script.segments:
            raise ValueError("Le script genere ne contient aucun segment.")

        # Corrige les timestamps croissants et non chevauchants.
        cursor = 0.0
        for seg in script.segments:
            if seg.timestamp_fin <= seg.timestamp_debut:
                # Estime ~150 mots/minute si timestamp incoherent.
                words = max(1, len(seg.texte_narration.split()))
                seg.timestamp_debut = cursor
                seg.timestamp_fin = cursor + words / 150 * 60
            cursor = seg.timestamp_fin

        total = script.segments[-1].timestamp_fin
        if total < duree_cible * 0.3:
            logger.warning(
                "Duree totale du script (%.0fs) tres inferieure a la cible (%ds).",
                total,
                duree_cible,
            )
