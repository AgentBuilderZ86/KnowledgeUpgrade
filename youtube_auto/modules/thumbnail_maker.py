"""Generation de la miniature YouTube optimisee CTR avec Pillow."""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class ThumbnailMaker:
    """Cree une miniature 1280x720 a fort contraste pour maximiser le CTR."""

    SIZE = (1280, 720)

    def __init__(self, badge_text: str = "TECH", watermark: str = "") -> None:
        """Initialise le generateur de miniatures.

        Args:
            badge_text: Texte du badge categorie (bas gauche).
            watermark: Filigrane discret (bas droite), ex. nom de la chaine.
        """
        self.badge_text = badge_text
        self.watermark = watermark

    def create(
        self, titre: str, image_background: str | None, output_path: str
    ) -> str:
        """Genere la miniature.

        Args:
            titre: Titre court et percutant a afficher.
            image_background: Image de fond (sera floutee) ou None.
            output_path: Chemin du PNG de sortie.

        Returns:
            Le chemin de la miniature generee.
        """
        from PIL import Image, ImageDraw, ImageFilter

        width, height = self.SIZE
        background = self._build_background(image_background, width, height)

        # Overlay sombre semi-transparent pour la lisibilite.
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 110))
        background = Image.alpha_composite(background.convert("RGBA"), overlay)

        draw = ImageDraw.Draw(background)
        self._draw_title(draw, titre, width, height)
        self._draw_badge(draw, width, height)
        if self.watermark:
            self._draw_watermark(draw, width, height)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        background.convert("RGB").save(output_path, quality=92)
        logger.info("Miniature generee : %s", output_path)
        return output_path

    def _build_background(self, image_path: str | None, width: int, height: int):
        """Construit le fond : image floutee ou degrade de secours."""
        from PIL import Image, ImageFilter

        if image_path and os.path.exists(image_path):
            try:
                img = Image.open(image_path).convert("RGB")
                img = self._cover_resize(img, width, height)
                return img.filter(ImageFilter.GaussianBlur(8))
            except Exception as exc:  # pragma: no cover
                logger.warning("Image de fond illisible (%s) - degrade utilise.", exc)

        # Degrade de secours #0a0a0a -> #16213e
        img = Image.new("RGB", (width, height))
        draw = __import__("PIL.ImageDraw", fromlist=["ImageDraw"]).Draw(img)
        top, bottom = (10, 10, 10), (22, 33, 62)
        for y in range(height):
            ratio = y / max(1, height - 1)
            r = int(top[0] + (bottom[0] - top[0]) * ratio)
            g = int(top[1] + (bottom[1] - top[1]) * ratio)
            b = int(top[2] + (bottom[2] - top[2]) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        return img

    @staticmethod
    def _cover_resize(img, width: int, height: int):
        """Redimensionne en mode 'cover' puis recadre au centre."""
        scale = max(width / img.width, height / img.height)
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size)
        left = (img.width - width) // 2
        top = (img.height - height) // 2
        return img.crop((left, top, left + width, top + height))

    def _draw_title(self, draw: Any, titre: str, width: int, height: int) -> None:
        """Dessine le titre en gros avec ombre portee."""
        font = self._load_font(72)
        wrapped = self._wrap(draw, titre.upper(), font, int(width * 0.9))
        line_height = 86
        total = line_height * len(wrapped)
        y = (height - total) // 2
        for line in wrapped:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            x = (width - w) // 2
            # Ombre noire.
            draw.text((x + 4, y + 4), line, font=font, fill=(0, 0, 0))
            draw.text((x, y), line, font=font, fill=(255, 255, 255))
            y += line_height

    def _draw_badge(self, draw: Any, width: int, height: int) -> None:
        """Dessine un badge couleur vif en bas a gauche."""
        font = self._load_font(40)
        text = self.badge_text.upper()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad = 18
        x0, y0 = 40, height - th - 2 * pad - 40
        draw.rectangle(
            [x0, y0, x0 + tw + 2 * pad, y0 + th + 2 * pad], fill=(0, 212, 255)
        )
        draw.text((x0 + pad, y0 + pad - bbox[1]), text, font=font, fill=(10, 10, 10))

    def _draw_watermark(self, draw: Any, width: int, height: int) -> None:
        """Dessine un filigrane discret en bas a droite."""
        font = self._load_font(28)
        text = self.watermark
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(
            (width - tw - 40, height - 60), text, font=font, fill=(220, 220, 220)
        )

    @staticmethod
    def _load_font(size: int):
        """Charge une police bold, avec repli sur la police par defaut."""
        from PIL import ImageFont

        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "title.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
            "arialbd.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()

    @staticmethod
    def _wrap(draw: Any, text: str, font: Any, max_width: int) -> list[str]:
        """Decoupe le texte pour respecter une largeur maximale."""
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
