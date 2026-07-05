"""Synthese vocale via edge-tts (gratuit) avec repli gTTS."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class TTSEngine:
    """Genere la voix off des segments via edge-tts, avec repli gTTS.

    ``edge-tts`` fournit des voix Microsoft naturelles et gratuites. Si le
    service est indisponible (reseau, blocage), le moteur bascule
    automatiquement sur ``gTTS`` (Google Translate TTS, gratuit).
    """

    def __init__(self, langue: str = "fr") -> None:
        """Initialise le moteur TTS.

        Args:
            langue: Code langue ISO (ex. "fr", "en") pour le repli gTTS.
        """
        self.langue = langue

    async def generate_audio(
        self, text: str, output_path: str, voice: str, speed: float = 1.0
    ) -> float:
        """Genere un fichier audio a partir d'un texte.

        Args:
            text: Le texte a synthetiser.
            output_path: Chemin du fichier MP3 de sortie.
            voice: Nom de la voix edge-tts (ex. "fr-FR-DeniseNeural").
            speed: Facteur de vitesse (1.0 = normal).

        Returns:
            La duree reelle de l'audio genere, en secondes.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        try:
            await self._edge_tts(text, output_path, voice, speed)
        except Exception as exc:
            logger.warning("edge-tts a echoue (%s) - repli sur gTTS.", exc)
            self._gtts(text, output_path)
        return self._audio_duration(output_path)

    async def _edge_tts(self, text: str, output_path: str, voice: str, speed: float) -> None:
        """Synthese via edge-tts."""
        import edge_tts

        # edge-tts attend un taux relatif (+0% par defaut).
        rate_pct = int(round((speed - 1.0) * 100))
        rate = f"{'+' if rate_pct >= 0 else ''}{rate_pct}%"
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
        await communicate.save(output_path)

    def _gtts(self, text: str, output_path: str) -> None:
        """Synthese de repli via gTTS."""
        from gtts import gTTS

        tts = gTTS(text=text, lang=self.langue)
        tts.save(output_path)

    @staticmethod
    def _audio_duration(path: str) -> float:
        """Retourne la duree d'un fichier audio en secondes."""
        try:
            from moviepy.editor import AudioFileClip

            clip = AudioFileClip(path)
            duration = float(clip.duration)
            clip.close()
            return duration
        except Exception as exc:  # pragma: no cover
            logger.warning("Impossible de mesurer la duree de %s (%s).", path, exc)
            return 0.0

    def generate_all_segments(self, segments: list, output_dir: str) -> list:
        """Genere un fichier audio par segment et met a jour les durees reelles.

        Args:
            segments: Liste d'objets ``Segment``.
            output_dir: Repertoire de sortie des fichiers audio.

        Returns:
            La liste des segments avec ``audio_path`` et ``duree_reelle`` remplis.
        """
        os.makedirs(output_dir, exist_ok=True)
        voice = "fr-FR-DeniseNeural"
        speed = 1.0
        # Recupere voix/vitesse depuis la config si disponible via attributs.
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            for idx, seg in enumerate(segments):
                out = os.path.join(output_dir, f"segment_{idx:03d}.mp3")
                duration = loop.run_until_complete(
                    self.generate_audio(seg.texte_narration, out, voice, speed)
                )
                seg.audio_path = out
                seg.duree_reelle = duration
                logger.info("Audio segment %d genere (%.1fs).", idx, duration)
        finally:
            loop.close()
        return segments

    def synthesize_segments(
        self, segments: list, output_dir: str, voice: str, speed: float = 1.0
    ) -> list:
        """Variante explicite de ``generate_all_segments`` avec voix/vitesse.

        Args:
            segments: Liste d'objets ``Segment``.
            output_dir: Repertoire de sortie.
            voice: Voix edge-tts a utiliser.
            speed: Facteur de vitesse.

        Returns:
            La liste des segments mise a jour.
        """
        os.makedirs(output_dir, exist_ok=True)
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            for idx, seg in enumerate(segments):
                out = os.path.join(output_dir, f"segment_{idx:03d}.mp3")
                duration = loop.run_until_complete(
                    self.generate_audio(seg.texte_narration, out, voice, speed)
                )
                seg.audio_path = out
                seg.duree_reelle = duration
                logger.info("Audio segment %d genere (%.1fs).", idx, duration)
        finally:
            loop.close()
        return segments
