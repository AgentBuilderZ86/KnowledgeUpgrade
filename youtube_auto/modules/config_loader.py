"""Chargement de la configuration YAML avec resolution des variables d'environnement.

Permet d'ecrire ``${MA_VARIABLE}`` dans ``config.yaml`` ; la valeur est alors
remplacee par la variable d'environnement correspondante (chargee depuis ``.env``).
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_ENV_PATTERN = re.compile(r"\$\{([^}^{]+)\}")


def _resolve_env(value: Any) -> Any:
    """Remplace recursivement les motifs ``${VAR}`` par les variables d'environnement."""
    if isinstance(value, str):
        def _replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, "")

        return _ENV_PATTERN.sub(_replace, value)
    if isinstance(value, dict):
        return {k: _resolve_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env(v) for v in value]
    return value


def load_config(config_path: str | os.PathLike[str] = "config.yaml") -> dict[str, Any]:
    """Charge ``config.yaml`` et resout les variables d'environnement.

    Args:
        config_path: Chemin vers le fichier YAML de configuration.

    Returns:
        Dictionnaire de configuration avec variables d'environnement resolues.
    """
    # Charge .env situe a la racine du projet (a cote de config.yaml)
    config_path = Path(config_path)
    env_path = config_path.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()  # cherche un .env dans le cwd ou les parents

    if not config_path.exists():
        raise FileNotFoundError(f"Fichier de configuration introuvable : {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    resolved = _resolve_env(raw)
    logger.debug("Configuration chargee depuis %s", config_path)
    return resolved
