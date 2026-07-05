"""Detection des sujets tendance via Google Trends (pytrends, gratuit)."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TrendFinder:
    """Recherche et score les sujets tendance lies a une niche.

    Utilise ``pytrends`` (API Google Trends non officielle, gratuite). En cas
    d'echec reseau ou d'indisponibilite de l'API, des suggestions de repli
    basees sur la niche sont retournees afin que le pipeline ne soit jamais
    bloque.
    """

    def __init__(self, hl: str = "fr-FR", tz: int = 60, timeout: int = 20) -> None:
        """Initialise le client pytrends.

        Args:
            hl: Langue de l'interface Google Trends.
            tz: Decalage horaire en minutes (60 = UTC+1).
            timeout: Timeout reseau en secondes.
        """
        self.hl = hl
        self.tz = tz
        self.timeout = timeout
        self._pytrends: Any | None = None

    def _client(self) -> Any:
        """Instancie (paresseusement) le client pytrends."""
        if self._pytrends is None:
            from pytrends.request import TrendReq

            self._pytrends = TrendReq(
                hl=self.hl, tz=self.tz, timeout=(self.timeout, self.timeout)
            )
        return self._pytrends

    def get_trending_topics(self, niche: str, langue: str = "FR") -> list[dict]:
        """Recupere les sujets tendance lies a la niche configuree.

        Args:
            niche: Description de la niche (ex. "intelligence artificielle").
            langue: Code geographique a deux lettres (ex. "FR", "US").

        Returns:
            Liste triee par score d'interet decroissant. Chaque element :
            ``{"topic": str, "score": int, "related_queries": list[str]}``.
        """
        keywords = [k.strip() for k in niche.split() if len(k.strip()) > 2][:5] or [niche]
        results: list[dict] = []
        try:
            client = self._client()
            client.build_payload(keywords, cat=0, timeframe="now 7-d", geo=langue, gprop="")

            # Requetes liees (montantes) pour chaque mot-cle.
            related = client.related_queries()
            for kw in keywords:
                kw_data = related.get(kw) or {}
                rising = kw_data.get("rising")
                top = kw_data.get("top")
                queries: list[str] = []
                if rising is not None and not rising.empty:
                    queries.extend(rising["query"].head(5).tolist())
                if top is not None and not top.empty:
                    queries.extend(top["query"].head(5).tolist())

                for q in queries:
                    score = self.score_topic(q)["score"]
                    results.append(
                        {
                            "topic": q,
                            "score": score,
                            "related_queries": queries[:5],
                        }
                    )

            # Interet relatif des mots-cles principaux.
            interest = client.interest_over_time()
            if interest is not None and not interest.empty:
                for kw in keywords:
                    if kw in interest.columns:
                        mean_score = int(interest[kw].mean())
                        results.append(
                            {"topic": kw, "score": mean_score, "related_queries": []}
                        )
        except Exception as exc:  # pragma: no cover - dependant du reseau
            logger.warning("pytrends indisponible (%s) - repli sur des suggestions.", exc)
            results = self._fallback_topics(niche)

        if not results:
            results = self._fallback_topics(niche)

        # Deduplication par topic en conservant le meilleur score.
        unique: dict[str, dict] = {}
        for item in results:
            key = item["topic"].lower()
            if key not in unique or item["score"] > unique[key]["score"]:
                unique[key] = item

        ranked = sorted(unique.values(), key=lambda d: d["score"], reverse=True)
        logger.info("%d sujets tendance trouves pour la niche '%s'.", len(ranked), niche)
        return ranked

    def score_topic(self, topic: str) -> dict:
        """Score un sujet selon sa pertinence pour YouTube.

        Criteres :
            - Volume de recherche estime (pytrends, sur 0-100).
            - Bonus de fraicheur si le sujet est tendance (< 7 jours).
            - Longueur optimale (4-8 mots) pour un titre accrocheur.

        Args:
            topic: Le sujet a evaluer.

        Returns:
            ``{"topic", "score", "recommended_title"}``.
        """
        score = 0.0

        # Volume de recherche (sur 7 jours).
        try:
            client = self._client()
            client.build_payload([topic], cat=0, timeframe="now 7-d", geo="", gprop="")
            interest = client.interest_over_time()
            if interest is not None and not interest.empty and topic in interest.columns:
                volume = float(interest[topic].mean())
                score += volume  # 0-100
                # Bonus de fraicheur : tendance montante sur la fin de periode.
                half = len(interest) // 2 or 1
                recent = interest[topic].tail(half).mean()
                older = interest[topic].head(half).mean()
                if recent > older:
                    score += 20.0
        except Exception:  # pragma: no cover - dependant du reseau
            score += 50.0  # score neutre si indisponible

        # Bonus de longueur optimale.
        word_count = len(topic.split())
        if 4 <= word_count <= 8:
            score += 15.0
        elif word_count < 4:
            score += 5.0

        return {
            "topic": topic,
            "score": int(round(score)),
            "recommended_title": self._to_title(topic),
        }

    def get_best_topic_today(self, niche: str) -> str:
        """Retourne le meilleur sujet du jour pour la niche.

        Args:
            niche: Description de la niche.

        Returns:
            Le sujet ayant le score le plus eleve.
        """
        topics = self.get_trending_topics(niche)
        best = topics[0]["topic"] if topics else niche
        logger.info("Meilleur sujet du jour : %s", best)
        return best

    @staticmethod
    def _to_title(topic: str) -> str:
        """Transforme un sujet brut en titre accrocheur."""
        clean = topic.strip().capitalize()
        return clean

    @staticmethod
    def _fallback_topics(niche: str) -> list[dict]:
        """Suggestions de repli quand Google Trends est indisponible."""
        templates = [
            f"Tout comprendre sur {niche} en 2026",
            f"5 choses a savoir sur {niche}",
            f"Comment {niche} va changer notre quotidien",
            f"Les dangers caches de {niche}",
            f"{niche} expliquee simplement",
        ]
        return [
            {"topic": t, "score": 60 - i * 5, "related_queries": []}
            for i, t in enumerate(templates)
        ]
