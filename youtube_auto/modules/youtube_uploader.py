"""Upload et programmation de videos via la YouTube Data API v3."""
from __future__ import annotations

import logging
import os
import pickle
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.pickle"


class YouTubeUploader:
    """Authentifie l'utilisateur et publie les videos sur YouTube."""

    def __init__(
        self,
        client_secrets: str = "client_secrets.json",
        category_id: str = "28",
        default_privacy: str = "private",
        made_for_kids: bool = False,
    ) -> None:
        """Initialise l'uploader.

        Args:
            client_secrets: Chemin du fichier OAuth client_secrets.json.
            category_id: ID de categorie YouTube (28 = Science & Tech).
            default_privacy: Statut par defaut sans programmation.
            made_for_kids: Indique si le contenu vise les enfants.
        """
        self.client_secrets = client_secrets
        self.category_id = str(category_id)
        self.default_privacy = default_privacy
        self.made_for_kids = made_for_kids
        self._service: Any | None = None

    def authenticate(self) -> Any:
        """Authentifie via OAuth2 et met en cache le token.

        Returns:
            Le service YouTube authentifie (``googleapiclient`` resource).
        """
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as fh:
                creds = pickle.load(fh)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.client_secrets):
                    raise FileNotFoundError(
                        f"Fichier OAuth introuvable : {self.client_secrets}. "
                        "Telechargez-le depuis Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "wb") as fh:
                pickle.dump(creds, fh)

        self._service = build("youtube", "v3", credentials=creds)
        logger.info("Authentification YouTube reussie.")
        return self._service

    def upload(
        self,
        video_path: str,
        thumbnail_path: str | None,
        metadata: dict[str, Any],
        schedule_time: str | None = None,
    ) -> str:
        """Televerse une video et, optionnellement, programme sa publication.

        Args:
            video_path: Chemin du fichier video MP4.
            thumbnail_path: Chemin de la miniature (ou None).
            metadata: ``{"title", "description", "tags"}``.
            schedule_time: Date/heure ISO 8601 de publication (privee jusque-la).

        Returns:
            L'URL de la video publiee.
        """
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload

        service = self._service or self.authenticate()

        privacy = self.default_privacy if schedule_time else "public"
        status: dict[str, Any] = {
            "privacyStatus": "private" if schedule_time else privacy,
            "selfDeclaredMadeForKids": self.made_for_kids,
        }
        if schedule_time:
            status["privacyStatus"] = "private"
            status["publishAt"] = self._to_iso8601(schedule_time)

        body = {
            "snippet": {
                "title": metadata.get("title", "")[:100],
                "description": metadata.get("description", "")[:5000],
                "tags": metadata.get("tags", [])[:50],
                "categoryId": self.category_id,
            },
            "status": status,
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = service.videos().insert(
            part="snippet,status", body=body, media_body=media
        )

        response = None
        try:
            while response is None:
                progress, response = request.next_chunk()
                if progress:
                    logger.info("Upload : %d%%", int(progress.progress() * 100))
        except HttpError as exc:
            logger.error("Erreur d'upload YouTube : %s", exc)
            raise

        video_id = response["id"]
        logger.info("Video uploadee, id=%s", video_id)

        if thumbnail_path and os.path.exists(thumbnail_path):
            self._set_thumbnail(service, video_id, thumbnail_path)

        return f"https://www.youtube.com/watch?v={video_id}"

    def _set_thumbnail(self, service: Any, video_id: str, thumbnail_path: str) -> None:
        """Definit la miniature personnalisee de la video."""
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload

        try:
            service.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path),
            ).execute()
            logger.info("Miniature definie pour la video %s.", video_id)
        except HttpError as exc:  # pragma: no cover - depend du compte
            logger.warning("Impossible de definir la miniature (%s).", exc)

    @staticmethod
    def _to_iso8601(schedule_time: str) -> str:
        """Normalise une date de programmation en ISO 8601 UTC.

        Accepte deja un ISO 8601 ou ``YYYY-MM-DD HH:MM``.
        """
        try:
            dt = datetime.fromisoformat(schedule_time)
        except ValueError:
            dt = datetime.strptime(schedule_time, "%Y-%m-%d %H:%M")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
