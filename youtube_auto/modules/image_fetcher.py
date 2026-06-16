"""Recuperation d'images libres de droits (Pexels, Pixabay) + repli Pillow."""
from __future__ import annotations

import logging
import math
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

PEXELS_ENDPOINT = "https://api.pexels.com/v1/search"
PIXABAY_ENDPOINT = "https://pixabay.com/api/"


class ImageFetcher:
    """Telecharge des images d'illustration ou genere des slides de secours."""

    def __init__(
        self,
        pexels_key: str = "",
        pixabay_key: str = "",
        resolution: tuple[int, int] = (1920, 1080),
        images_per_segment_seconds: int = 4,
    ) -> None:
        """Initialise le recuperateur d'images.

        Args:
            pexels_key: Cle API Pexels (gratuite).
            pixabay_key: Cle API Pixabay (gratuite).
            resolution: Resolution cible des slides generees.
            images_per_segment_seconds: 1 image par tranche de N secondes.
        """
        self.pexels_key = pexels_key or ""
        self.pixabay_key = pixabay_key or ""
        self.resolution = tuple(resolution)
        self.images_per_segment_seconds = max(1, int(images_per_segment_seconds))

    def fetch_for_segment(
        self, query: str, segment_duration: float, output_dir: str
    ) -> list[str]:
        """Recupere les images couvrant la duree d'un segment.

        Cherche d'abord sur Pexels, puis Pixabay. Genere une slide texte si
        aucune image n'est trouvee.

        Args:
            query: Mot-cle de recherche (anglais de preference).
            segment_duration: Duree du segment en secondes.
            output_dir: Repertoire de telechargement.

        Returns:
            Liste de chemins d'images locales.
        """
        os.makedirs(output_dir, exist_ok=True)
        n_images = max(1, math.ceil(segment_duration / self.images_per_segment_seconds))

        urls: list[str] = []
        if self.pexels_key:
            urls = self._search_pexels(query, n_images)
        if len(urls) < n_images and self.pixabay_key:
            urls.extend(self._search_pixabay(query, n_images - len(urls)))

        paths: list[str] = []
        for i, url in enumerate(urls[:n_images]):
            dest = os.path.join(output_dir, f"img_{i:02d}.jpg")
            if self._download(url, dest):
                paths.append(dest)

        if not paths:
            logger.info("Aucune image pour '%s' - generation d'une slide texte.", query)
            slide = os.path.join(output_dir, "slide_00.jpg")
            self.create_text_slide(query, slide, self.resolution)
            paths.append(slide)

        logger.info("%d image(s) prete(s) pour le segment '%s'.", len(paths), query)
        return paths

    def _search_pexels(self, query: str, count: int) -> list[str]:
        """Recherche des photos sur Pexels."""
        try:
            resp = requests.get(
                PEXELS_ENDPOINT,
                headers={"Authorization": self.pexels_key},
                params={
                    "query": query,
                    "per_page": max(1, count),
                    "orientation": "landscape",
                },
                timeout=20,
            )
            resp.raise_for_status()
            photos = resp.json().get("photos", [])
            return [p["src"]["large2x"] for p in photos if p.get("src")]
        except Exception as exc:  # pragma: no cover - dependant du reseau
            logger.warning("Pexels indisponible pour '%s' (%s).", query, exc)
            return []

    def _search_pixabay(self, query: str, count: int) -> list[str]:
        """Recherche des images sur Pixabay."""
        try:
            resp = requests.get(
                PIXABAY_ENDPOINT,
                params={
                    "key": self.pixabay_key,
                    "q": query,
                    "image_type": "photo",
                    "orientation": "horizontal",
                    "per_page": max(3, count),
                    "safesearch": "true",
                },
                timeout=20,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
            return [h["largeImageURL"] for h in hits if h.get("largeImageURL")]
        except Exception as exc:  # pragma: no cover - dependant du reseau
            logger.warning("Pixabay indisponible pour '%s' (%s).", query, exc)
            return []

    @staticmethod
    def _download(url: str, dest: str) -> bool:
        """Telecharge un fichier image. Retourne True en cas de succes."""
        try:
            resp = requests.get(url, timeout=30, stream=True)
            resp.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    fh.write(chunk)
            return True
        except Exception as exc:  # pragma: no cover - dependant du reseau
            logger.warning("Echec du telechargement de %s (%s).", url, exc)
            return False

    def create_text_slide(
        self, text: str, output_path: str, resolution: tuple[int, int]
    ) -> str:
        """Genere une slide de secours avec Pillow.

        Style :
            - Fond degrade sombre (#0a0a0a -> #1a1a2e).
            - Texte blanc centre.
            - Ligne d'accent coloree en bas (#00d4ff).

        Args:
            text: Texte a afficher.
            output_path: Chemin de sortie (JPG/PNG).
            resolution: Dimensions (largeur, hauteur).

        Returns:
            Le chemin de l'image generee.
        """
        from PIL import Image, ImageDraw, ImageFont

        width, height = resolution
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)

        # Degrade vertical #0a0a0a -> #1a1a2e
        top = (10, 10, 10)
        bottom = (26, 26, 46)
        for y in range(height):
            ratio = y / max(1, height - 1)
            r = int(top[0] + (bottom[0] - top[0]) * ratio)
            g = int(top[1] + (bottom[1] - top[1]) * ratio)
            b = int(top[2] + (bottom[2] - top[2]) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        font = self._load_font(int(height * 0.07))
        wrapped = self._wrap(draw, text, font, int(width * 0.8))

        # Centrage vertical du bloc de texte.
        line_height = int(height * 0.09)
        total_height = line_height * len(wrapped)
        y = (height - total_height) // 2
        for line in wrapped:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            x = (width - w) // 2
            draw.text((x, y), line, font=font, fill=(255, 255, 255))
            y += line_height

        # Ligne d'accent #00d4ff
        accent_y = int(height * 0.88)
        draw.rectangle(
            [int(width * 0.1), accent_y, int(width * 0.9), accent_y + 8],
            fill=(0, 212, 255),
        )

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        img.save(output_path, quality=90)
        return output_path

    @staticmethod
    def _load_font(size: int) -> Any:
        """Charge une police TrueType, avec repli sur la police par defaut."""
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
        """Retourne les lignes de texte respectant une largeur maximale."""
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
