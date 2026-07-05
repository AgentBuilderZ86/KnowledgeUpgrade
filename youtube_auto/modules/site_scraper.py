"""Récupération des images réelles d'un site web (pour B-roll authentique)."""
from __future__ import annotations

import logging
import os
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_IMG_EXT_RE = re.compile(r"\.(?:jpg|jpeg|png|webp)(?:\?|$)", re.IGNORECASE)


class _ImgParser(HTMLParser):
    """Extrait les URLs d'images d'une page HTML (img/src, srcset, og:image)."""

    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        d = dict(attrs)
        if tag == "img":
            for key in ("src", "data-src", "data-lazy-src"):
                if d.get(key):
                    self.urls.append(d[key])
            if d.get("srcset"):
                # srcset = "url1 320w, url2 640w, ..." → on prend chaque url
                for part in d["srcset"].split(","):
                    url = part.strip().split(" ")[0]
                    if url:
                        self.urls.append(url)
        elif tag == "meta" and d.get("property") in ("og:image", "og:image:url"):
            if d.get("content"):
                self.urls.append(d["content"])
        elif tag == "source" and d.get("srcset"):
            for part in d["srcset"].split(","):
                url = part.strip().split(" ")[0]
                if url:
                    self.urls.append(url)


class SiteScraper:
    """Télécharge les images d'un site web dans un dossier local."""

    def __init__(self, min_bytes: int = 15000, timeout: int = 25) -> None:
        """Initialise le scraper.

        Args:
            min_bytes: Taille minimale d'une image conservée (filtre logos/icônes).
            timeout: Timeout réseau par requête (secondes).
        """
        self.min_bytes = min_bytes
        self.timeout = timeout

    def scrape_images(
        self, url: str, output_dir: str, max_images: int = 40
    ) -> list[str]:
        """Récupère et télécharge les images d'une page web.

        Args:
            url: URL de la page à analyser (ex. https://www.z0guesthouse.com).
            output_dir: Dossier de destination des images.
            max_images: Nombre maximum d'images à télécharger.

        Returns:
            Liste des chemins locaux des images téléchargées (>= min_bytes).
        """
        os.makedirs(output_dir, exist_ok=True)
        try:
            resp = requests.get(
                url, headers={"User-Agent": _USER_AGENT}, timeout=self.timeout
            )
            resp.raise_for_status()
            html = resp.text
        except Exception as exc:
            logger.warning("Impossible de charger %s (%s).", url, exc)
            return []

        # Parse le HTML + capture aussi les URLs brutes (Wix/Squarespace inline).
        parser = _ImgParser()
        try:
            parser.feed(html)
        except Exception:
            pass
        raw = re.findall(r"https?://[^\"'()\s]+", html)

        candidates: list[str] = []
        for u in parser.urls + raw:
            absolute = urljoin(url, u)
            if _IMG_EXT_RE.search(absolute):
                candidates.append(self._normalize(absolute))

        # Déduplication en préservant l'ordre.
        seen: set[str] = set()
        unique = [u for u in candidates if not (u in seen or seen.add(u))]
        logger.info("%d URLs d'images candidates trouvées sur %s.", len(unique), url)

        paths: list[str] = []
        for i, img_url in enumerate(unique):
            if len(paths) >= max_images:
                break
            dest = os.path.join(output_dir, f"site_{len(paths):03d}.jpg")
            if self._download(img_url, dest):
                paths.append(dest)

        logger.info("%d image(s) du site téléchargée(s) dans %s.", len(paths), output_dir)
        return paths

    @staticmethod
    def _normalize(url: str) -> str:
        """Améliore la résolution des CDN connus (Wix, Squarespace)."""
        # Wix : retire les transformations pour obtenir l'original haute résolution.
        if "wixstatic.com" in url:
            url = re.sub(r"/v1/(?:fill|fit|crop)/[^/]+/", "/v1/fill/w_1920,h_1080/", url)
        return url

    def _download(self, url: str, dest: str) -> bool:
        """Télécharge une image si elle dépasse la taille minimale."""
        try:
            resp = requests.get(
                url, headers={"User-Agent": _USER_AGENT}, timeout=self.timeout, stream=True
            )
            resp.raise_for_status()
            content = resp.content
            if len(content) < self.min_bytes:
                return False  # trop petite : logo, icône, pixel de tracking
            with open(dest, "wb") as fh:
                fh.write(content)
            return True
        except Exception as exc:
            logger.debug("Echec téléchargement %s (%s).", url, exc)
            return False
