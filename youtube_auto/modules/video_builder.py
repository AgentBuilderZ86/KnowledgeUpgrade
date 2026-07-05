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

        # Mode silencieux : film contemplatif sans voix off (texte + musique).
        self.silent = bool(prod.get("silent_mode", False))
        self.target_duration = int(
            config.get("channel", {}).get("duree_cible_secondes", 480)
        )

        # Réglages d'encodage par défaut (mode qualité).
        self.codec = "libx264"
        self.encode_preset = "medium"

        # Mode TURBO : override pour accélérer fortement la génération.
        turbo = config.get("turbo", {})
        if turbo.get("enabled", False):
            t_res = turbo.get("resolution", [1280, 720])
            self.width, self.height = int(t_res[0]), int(t_res[1])
            if turbo.get("disable_ken_burns", True):
                self.ken_burns = False
            self.encode_preset = turbo.get("encode_preset", "ultrafast")
            if turbo.get("use_gpu", False):
                self.codec = "h264_nvenc"
            logger.info(
                "Mode TURBO actif : %dx%d, ken_burns=%s, codec=%s, preset=%s",
                self.width, self.height, self.ken_burns, self.codec, self.encode_preset,
            )

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

        # En mode silencieux, chaque segment dure une part egale de la cible.
        n_seg = max(1, len(segments))
        silent_seg_duration = self.target_duration / n_seg

        for idx, seg in enumerate(segments):
            images = image_files.get(idx, [])
            if not images:
                logger.warning("Segment %d sans image - ignore.", idx)
                continue

            if self.silent:
                # Pas de voix off : duree fixe, ambiance visuelle.
                duration = silent_seg_duration
                audio_clip = None
            else:
                audio_path = (
                    audio_files[idx] if idx < len(audio_files) else seg.audio_path
                )
                audio_clip = AudioFileClip(audio_path)
                duration = float(audio_clip.duration)

            per_image = duration / len(images)
            image_clips = [
                self._make_image_clip(path, per_image) for path in images
            ]
            video = concatenate_videoclips(image_clips, method="compose")
            video = video.set_duration(duration)
            if audio_clip is not None:
                video = video.set_audio(audio_clip)

            # Texte a l'ecran (rendu PIL, sans ImageMagick).
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
                if final.audio is None:
                    # Mode silencieux : la musique EST toute la bande-son
                    # (on remonte son volume car il n'y a pas de voix).
                    final = final.set_audio(music.volumex(6.0))
                else:
                    mixed = CompositeAudioClip([final.audio, music])
                    final = final.set_audio(mixed)

        # Intro fade-in / outro fade-out.
        final = final.fadein(self.intro_fade).fadeout(self.outro_fade)

        # NVENC (GPU) n'accepte pas les presets libx264 ; on adapte.
        nvenc_presets = {"ultrafast": "fast", "medium": "medium", "veryslow": "slow"}
        preset = (
            nvenc_presets.get(self.encode_preset, "fast")
            if self.codec == "h264_nvenc"
            else self.encode_preset
        )
        try:
            final.write_videofile(
                output_path,
                fps=self.fps,
                codec=self.codec,
                audio_codec="aac",
                preset=preset,
                threads=os.cpu_count() or 4,
                logger="bar",
            )
        except Exception as exc:
            # Repli automatique CPU si NVENC (GPU) indisponible sur le runtime.
            if self.codec == "h264_nvenc":
                logger.warning("NVENC indisponible (%s) - repli sur libx264 (CPU).", exc)
                self.codec = "libx264"
                final.write_videofile(
                    output_path,
                    fps=self.fps,
                    codec="libx264",
                    audio_codec="aac",
                    preset="ultrafast",
                    threads=os.cpu_count() or 4,
                    logger="bar",
                )
            else:
                raise
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
        """Superpose un texte à l'écran, rendu via PIL (aucune dépendance ImageMagick).

        En mode silencieux, le texte est centré (esthétique Serif minimaliste) et
        apparaît/disparaît en fondu ; sinon il est placé en bas du cadre.
        """
        import numpy as np
        from moviepy.editor import CompositeVideoClip, ImageClip
        from PIL import Image, ImageDraw, ImageFont

        try:
            overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            font = self._load_text_font(int(self.height * (0.055 if self.silent else 0.048)))

            wrapped = self._wrap_text(draw, text, font, int(self.width * 0.8))
            line_h = int(self.height * 0.075)
            block_h = line_h * len(wrapped)

            if self.silent:
                y = (self.height - block_h) // 2   # centré verticalement
            else:
                y = int(self.height * 0.78)

            for line in wrapped:
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                x = (self.width - w) // 2
                # Ombre douce pour la lisibilité sur photo.
                draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 160))
                draw.text((x, y), line, font=font, fill=(255, 255, 255, 235))
                y += line_h

            txt_clip = (
                ImageClip(np.array(overlay))
                .set_duration(duration)
                .set_position("center")
            )
            # Fondu lent pour l'esthétique contemplative.
            fade = min(1.2, duration / 3)
            txt_clip = txt_clip.crossfadein(fade).crossfadeout(fade)
            return CompositeVideoClip([video, txt_clip], size=(self.width, self.height))
        except Exception as exc:
            logger.warning("Rendu texte échoué (%s) - texte écran ignoré.", exc)
            return video

    @staticmethod
    def _load_text_font(size: int):
        """Charge une police (Serif de préférence) pour le texte à l'écran."""
        from PIL import ImageFont

        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "serif.ttf"),
            os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "title.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/Library/Fonts/Georgia.ttf",
            "C:\\Windows\\Fonts\\georgia.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()

    @staticmethod
    def _wrap_text(draw, text: str, font, max_width: int) -> list[str]:
        """Découpe le texte pour respecter une largeur maximale."""
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            trial = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), trial, font=font)
            if bbox[2] - bbox[0] <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [text]

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
