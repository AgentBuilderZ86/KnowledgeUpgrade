"""Generation (faster-whisper) et incrustation (FFmpeg) des sous-titres."""
from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class SubtitleEngine:
    """Transcrit l'audio en SRT puis incruste les sous-titres dans la video."""

    def __init__(self, model_size: str = "small", language: str = "fr") -> None:
        """Initialise le moteur de sous-titres.

        Args:
            model_size: Taille du modele faster-whisper (tiny..large-v3).
            language: Langue de transcription (ex. "fr").
        """
        self.model_size = model_size
        self.language = language
        self._model: Any | None = None

    def _load_model(self) -> Any:
        """Charge (paresseusement) le modele faster-whisper sur CPU."""
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_size, device="cpu", compute_type="int8"
            )
        return self._model

    def generate_srt(self, audio_path: str, output_srt: str) -> str:
        """Transcrit un fichier audio et genere un .srt avec timestamps.

        Args:
            audio_path: Chemin de l'audio (ou de la video) a transcrire.
            output_srt: Chemin du fichier .srt de sortie.

        Returns:
            Le chemin du fichier .srt genere.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_srt)), exist_ok=True)
        model = self._load_model()
        segments, _info = model.transcribe(
            audio_path, language=self.language, word_timestamps=True
        )

        lines: list[str] = []
        for i, seg in enumerate(segments, start=1):
            start = self._format_ts(seg.start)
            end = self._format_ts(seg.end)
            text = seg.text.strip()
            lines.append(f"{i}\n{start} --> {end}\n{text}\n")

        with open(output_srt, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))

        logger.info("Sous-titres generes : %s (%d segments).", output_srt, len(lines))
        return output_srt

    def burn_subtitles(
        self, video_path: str, srt_path: str, output_path: str
    ) -> str:
        """Incruste les sous-titres dans la video via FFmpeg.

        Style : blanc, bordure noire, centre en bas, taille 28.

        Args:
            video_path: Video source.
            srt_path: Fichier .srt a incruster.
            output_path: Video de sortie.

        Returns:
            Le chemin de la video sous-titree (ou la source si echec).
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Echappement du chemin pour le filtre subtitles (compatible OS).
        srt_escaped = self._escape_for_filter(os.path.abspath(srt_path))
        style = (
            "FontSize=28,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,Outline=2,Alignment=2,MarginV=40"
        )
        vf = f"subtitles='{srt_escaped}':force_style='{style}'"

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vf",
            vf,
            "-c:a",
            "copy",
            output_path,
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            logger.info("Sous-titres incrustes : %s", output_path)
            return output_path
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            stderr = getattr(exc, "stderr", b"")
            detail = stderr.decode("utf-8", "ignore") if stderr else str(exc)
            logger.warning("Echec de l'incrustation FFmpeg (%s).", detail[-300:])
            return video_path

    @staticmethod
    def _format_ts(seconds: float) -> str:
        """Formate des secondes en timestamp SRT ``HH:MM:SS,mmm``."""
        if seconds is None:
            seconds = 0.0
        millis = int(round(seconds * 1000))
        h, millis = divmod(millis, 3_600_000)
        m, millis = divmod(millis, 60_000)
        s, millis = divmod(millis, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{millis:03d}"

    @staticmethod
    def _escape_for_filter(path: str) -> str:
        """Echappe un chemin pour le filtre ``subtitles`` de FFmpeg."""
        # Sous Windows, ':' (lettre de lecteur) et '\' doivent etre echappes.
        path = path.replace("\\", "/")
        path = path.replace(":", "\\:")
        return path
