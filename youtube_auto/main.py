"""Orchestrateur principal du pipeline YouTube automatise.

Modes d'utilisation :
    python main.py --topic "Les 5 metiers qui vont disparaitre avec l'IA"
    python main.py --schedule --time 09:00
    python main.py --batch 5
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from modules.config_loader import load_config
from modules.image_fetcher import ImageFetcher
from modules.script_generator import ScriptGenerator
from modules.subtitle_engine import SubtitleEngine
from modules.thumbnail_maker import ThumbnailMaker
from modules.trend_finder import TrendFinder
from modules.tts_engine import TTSEngine
from modules.video_builder import VideoBuilder
from modules.youtube_uploader import YouTubeUploader

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"


def setup_logging() -> logging.Logger:
    """Configure le logging vers la console et un fichier journalier."""
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"{datetime.now():%Y-%m-%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("pipeline")


logger = logging.getLogger("pipeline")


def _safe(step_name: str, func, *args, **kwargs):
    """Execute une etape en capturant les erreurs non bloquantes.

    Args:
        step_name: Nom de l'etape (pour le log).
        func: Fonction a executer.

    Returns:
        Le resultat de la fonction, ou None en cas d'erreur.
    """
    try:
        return func(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Etape '%s' en echec : %s", step_name, exc)
        return None


def run_pipeline(topic: str | None = None, config_path: str | None = None) -> str | None:
    """Execute le pipeline complet de generation et publication.

    Etapes :
        1. Detection du sujet (si non fourni).
        2. Generation du script.
        3. Synthese vocale.
        4. Recuperation des images.
        5. Assemblage de la video.
        6. Sous-titres (generation + incrustation).
        7. Miniature.
        8. Upload YouTube (avec programmation).
        9. Nettoyage des fichiers temporaires.

    Args:
        topic: Sujet impose, ou None pour detection automatique.
        config_path: Chemin du config.yaml (par defaut a la racine du projet).

    Returns:
        L'URL de la video publiee, ou le chemin local si l'upload echoue/saute.
    """
    config_path = config_path or str(BASE_DIR / "config.yaml")
    config = load_config(config_path)
    channel = config.get("channel", {})
    production = config.get("production", {})
    api = config.get("api", {})
    yt_cfg = config.get("youtube", {})

    niche = channel.get("niche", "technologie")
    langue = channel.get("langue", "fr")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = OUTPUT_DIR / run_id
    tmp_dir = work_dir / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    logger.info("=== Demarrage du pipeline (run %s) ===", run_id)

    # --- 1. Sujet ---
    if not topic:
        finder = TrendFinder(hl=f"{langue}-{langue.upper()}")
        topic = _safe("trend_finder", finder.get_best_topic_today, niche) or niche
    logger.info("Sujet retenu : %s", topic)

    # --- 2. Script ---
    generator = ScriptGenerator(config)
    script = _safe("script_generator", generator.generate, topic, config)
    if script is None:
        logger.error("Impossible de generer le script - arret du pipeline.")
        return None

    # Tags permanents fusionnes.
    script.tags = list(dict.fromkeys(script.tags + channel.get("tags_permanents", [])))

    # --- 3. Synthese vocale ---
    tts = TTSEngine(langue=langue)
    voice = production.get("voix_tts", "fr-FR-DeniseNeural")
    speed = float(production.get("vitesse_voix", 1.0))
    audio_dir = str(tmp_dir / "audio")
    _safe("tts_engine", tts.synthesize_segments, script.segments, audio_dir, voice, speed)
    audio_files = [seg.audio_path for seg in script.segments if seg.audio_path]

    # --- 4. Images ---
    fetcher = ImageFetcher(
        pexels_key=api.get("pexels_key", ""),
        pixabay_key=api.get("pixabay_key", ""),
        resolution=tuple(production.get("resolution", [1920, 1080])),
        images_per_segment_seconds=int(production.get("images_per_segment_seconds", 4)),
    )
    image_files: dict[int, list[str]] = {}
    for idx, seg in enumerate(script.segments):
        duration = seg.duree_reelle or seg.duree or 5.0
        seg_dir = str(tmp_dir / "images" / f"seg_{idx:03d}")
        imgs = _safe(
            f"image_fetcher[{idx}]",
            fetcher.fetch_for_segment,
            seg.image_query,
            duration,
            seg_dir,
        )
        image_files[idx] = imgs or []

    # --- 5. Video ---
    builder = VideoBuilder(config)
    raw_video = str(work_dir / "video_raw.mp4")
    built = _safe(
        "video_builder",
        builder.build,
        script.segments,
        audio_files,
        image_files,
        config,
        raw_video,
    )
    if built is None:
        logger.error("Echec de l'assemblage video - arret du pipeline.")
        return None

    final_video = built

    # --- 6. Sous-titres ---
    if production.get("burn_subtitles", True):
        sub = SubtitleEngine(
            model_size=production.get("whisper_model", "small"), language=langue
        )
        srt_path = str(work_dir / "subtitles.srt")
        generated = _safe("subtitle_generate", sub.generate_srt, built, srt_path)
        if generated:
            subbed = str(work_dir / "video_final.mp4")
            burned = _safe("subtitle_burn", sub.burn_subtitles, built, generated, subbed)
            if burned:
                final_video = burned

    # --- 7. Miniature ---
    thumb_maker = ThumbnailMaker(
        badge_text=(channel.get("tags_permanents") or ["TECH"])[0],
        watermark=niche.split()[0] if niche else "",
    )
    first_image = None
    if image_files.get(0):
        first_image = image_files[0][0]
    thumb_path = str(work_dir / "thumbnail.png")
    _safe("thumbnail_maker", thumb_maker.create, script.titre_miniature, first_image, thumb_path)

    # --- 8. Upload ---
    schedule_iso = _compute_schedule(channel.get("upload_schedule"))
    uploader = YouTubeUploader(
        client_secrets=api.get("youtube_credentials", "client_secrets.json"),
        category_id=yt_cfg.get("category_id", "28"),
        default_privacy=yt_cfg.get("default_privacy", "private"),
        made_for_kids=bool(yt_cfg.get("made_for_kids", False)),
    )
    url = _safe(
        "youtube_uploader",
        uploader.upload,
        final_video,
        thumb_path if os.path.exists(thumb_path) else None,
        script.as_metadata(),
        schedule_iso,
    )

    # --- 9. Nettoyage ---
    _safe("cleanup", shutil.rmtree, str(tmp_dir), ignore_errors=True)

    result = url or final_video
    logger.info("=== Pipeline termine : %s ===", result)
    return result


def _compute_schedule(upload_schedule: str | None) -> str | None:
    """Calcule la prochaine date de publication ISO a partir d'une heure HH:MM.

    Args:
        upload_schedule: Heure cible "HH:MM" ou None.

    Returns:
        Date ISO 8601 de la prochaine occurrence, ou None.
    """
    if not upload_schedule:
        return None
    try:
        hour, minute = (int(x) for x in upload_schedule.split(":"))
    except ValueError:
        logger.warning("Heure de publication invalide : %s", upload_schedule)
        return None
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target.isoformat()


def run_scheduler(time_str: str, config_path: str | None = None) -> None:
    """Lance le pipeline tous les jours a une heure donnee.

    Args:
        time_str: Heure quotidienne "HH:MM".
        config_path: Chemin du config.yaml.
    """
    import schedule

    logger.info("Scheduler arme : execution quotidienne a %s.", time_str)
    schedule.every().day.at(time_str).do(run_pipeline, None, config_path)
    while True:
        schedule.run_pending()
        time.sleep(30)


def run_batch(count: int, config_path: str | None = None) -> list[str]:
    """Genere plusieurs videos d'affilee a partir des meilleurs sujets.

    Args:
        count: Nombre de videos a produire.
        config_path: Chemin du config.yaml.

    Returns:
        Liste des URLs/chemins produits.
    """
    config = load_config(config_path or str(BASE_DIR / "config.yaml"))
    niche = config.get("channel", {}).get("niche", "technologie")
    langue = config.get("channel", {}).get("langue", "fr")
    finder = TrendFinder(hl=f"{langue}-{langue.upper()}")
    topics = _safe("trend_finder_batch", finder.get_trending_topics, niche) or []
    results: list[str] = []
    for i in range(count):
        topic = topics[i]["topic"] if i < len(topics) else None
        logger.info("--- Batch %d/%d ---", i + 1, count)
        res = run_pipeline(topic, config_path)
        if res:
            results.append(res)
    return results


def main() -> None:
    """Point d'entree CLI."""
    parser = argparse.ArgumentParser(
        description="Pipeline YouTube faceless 100%% gratuit et open-source."
    )
    parser.add_argument("--topic", type=str, help="Sujet impose pour la video.")
    parser.add_argument(
        "--schedule", action="store_true", help="Active le scheduler quotidien."
    )
    parser.add_argument(
        "--time", type=str, default=None, help="Heure du scheduler (HH:MM)."
    )
    parser.add_argument(
        "--batch", type=int, default=0, help="Genere N videos d'affilee."
    )
    parser.add_argument(
        "--config", type=str, default=None, help="Chemin du config.yaml."
    )
    args = parser.parse_args()

    setup_logging()

    if args.schedule:
        config = load_config(args.config or str(BASE_DIR / "config.yaml"))
        time_str = args.time or config.get("channel", {}).get("upload_schedule", "09:00")
        run_scheduler(time_str, args.config)
    elif args.batch and args.batch > 0:
        run_batch(args.batch, args.config)
    else:
        run_pipeline(args.topic, args.config)


if __name__ == "__main__":
    main()
