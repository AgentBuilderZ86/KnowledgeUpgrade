"""Assemblage de la video finale avec MoviePy + FFmpeg."""
from __future__ import annotations

import glob
import logging
import os
import random
from typing import Any

logger = logging.getLogger(__name__)


class VideoBuilder:
    """Construit la video finale a partir des segments, audios et images."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise le constructeur video depuis la configuration.

        Args:
            config: Configuration complete (config.yaml resolu).
        """
        prod = config.get("production", {})
        res = prod.get("resolution", [1920, 1080])
        self.width, self.height = int(res[0]), int(res[1])
        self.fps = int(prod.get("fps", 30))
        self.use_music = bool(prod.get("fond_musique", True))
        self.music_volume = float(prod.get("volume_musique", 0.08))
        self.ken_burns = bool(prod.get("ken_burns", True))
        self.intro_fade = float(prod.get("intro_fade_seconds", 0.5))
        self.outro_fade = float(prod.get("outro_fade_seconds", 1.0))
        self.assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")

    def build(
        self,
        segments: list,
        audio_files: list[str],
        image_files: dict[int, list[str]],
        config: dict[str, Any],
        output_path: str,
    ) -> str:
        """Assemble la video complete.

        Args:
            segments: Liste d'objets ``Segment`` (avec durees reelles).
            audio_files: Chemins audio par segment (ordonnes).
            image_files: ``{index_segment: [chemins images]}``.
            config: Configuration complete.
            output_path: Chemin du MP4 final.

        Returns:
            Le chemin du fichier MP4 genere.
        """
        from moviepy.editor import (
            AudioFileClip,
            CompositeAudioClip,
            CompositeVideoClip,
            concatenate_videoclips,
        )

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        segment_clips = []

        for idx, seg in enumerate(segments):
            audio_path = (
                audio_files[idx] if idx < len(audio_files) else seg.audio_path
            )
            images = image_files.get(idx, [])
            if not images:
                logger.warning("Segment %d sans image - ignore.", idx)
                continue

            audio_clip = AudioFileClip(audio_path)
            duration = float(audio_clip.duration)

            per_image = duration / len(images)
            image_clips = [
                self._make_image_clip(path, per_image) for path in images
            ]
            video = concatenate_videoclips(image_clips, method="compose")
            video = video.set_duration(duration).set_audio(audio_clip)

            # Texte a l'ecran (optionnel).
            if getattr(seg, "texte_ecran", ""):
                video = self._overlay_text(video, seg.texte_ecran, duration)

            segment_clips.append(video)
            logger.info("Segment %d assemble (%.1fs).", idx, duration)

        if not segment_clips:
            raise RuntimeError("Aucun segment video n'a pu etre assemble.")

        final = concatenate_videoclips(segment_clips, method="compose")

        # Musique de fond.
        if self.use_music:
            music = self._load_music(final.duration)
            if music is not None:
                mixed = CompositeAudioClip([final.audio, music])
                final = final.set_audio(mixed)

        # Intro fade-in / outro fade-out.
        final = final.fadein(self.intro_fade).fadeout(self.outro_fade)

        final.write_videofile(
            output_path,
            fps=self.fps,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=os.cpu_count() or 4,
            logger=None,
        )
        # Liberation des ressources.
        final.close()
        for clip in segment_clips:
            clip.close()

        logger.info("Video assemblee : %s", output_path)
        return output_path

    def _make_image_clip(self, path: str, duration: float):
        """Cree un ImageClip avec effet Ken Burns (zoom lent 1.0 -> 1.05)."""
        from moviepy.editor import ImageClip

        clip = ImageClip(path).set_duration(duration)
        clip = clip.resize(height=self.height) if clip.h < self.height else clip
        # Recadrage/redimensionnement plein cadre.
        clip = clip.resize(self._fit_resize(clip))
        clip = clip.set_position("center")

        if self.ken_burns:
            zoom_target = 1.05
            clip = clip.resize(
                lambda t: 1.0 + (zoom_target - 1.0) * (t / max(0.01, duration))
            )

        from moviepy.editor import CompositeVideoClip

        return CompositeVideoClip(
            [clip.set_position("center")], size=(self.width, self.height)
        ).set_duration(duration)

    def _fit_resize(self, clip) -> float:
        """Facteur de redimensionnement pour couvrir le cadre (cover)."""
        scale_w = self.width / clip.w
        scale_h = self.height / clip.h
        return max(scale_w, scale_h)

    def _overlay_text(self, video, text: str, duration: float):
        """Superpose un texte court en bas du cadre."""
        from moviepy.editor import CompositeVideoClip, TextClip

        try:
            txt = (
                TextClip(
                    text,
                    fontsize=int(self.height * 0.05),
                    color="white",
                    stroke_color="black",
                    stroke_width=2,
                    method="caption",
                    size=(int(self.width * 0.8), None),
                )
                .set_duration(duration)
                .set_position(("center", int(self.height * 0.78)))
            )
            return CompositeVideoClip([video, txt], size=(self.width, self.height))
        except Exception as exc:  # pragma: no cover - ImageMagick requis
            logger.warning("TextClip indisponible (%s) - texte ecran ignore.", exc)
            return video

    def _load_music(self, duration: float):
        """Charge et boucle une musique de fond depuis assets/music."""
        from moviepy.editor import AudioFileClip, afx

        patterns = [os.path.join(self.assets_dir, "music", ext) for ext in ("*.mp3", "*.wav")]
        files: list[str] = []
        for pat in patterns:
            files.extend(glob.glob(pat))
        if not files:
            logger.info("Aucune musique de fond trouvee dans assets/music.")
            return None
        try:
            track = AudioFileClip(random.choice(files))
            track = track.fx(afx.audio_loop, duration=duration)
            track = track.volumex(self.music_volume)
            return track
        except Exception as exc:  # pragma: no cover
            logger.warning("Impossible de charger la musique (%s).", exc)
            return None
