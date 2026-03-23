"""
Universe config loader (JSON) + optional .env support.

Token security requirement:
- HA long-lived token must not be hardcoded in repo.
- We read it from an environment variable (config.ha.token_env), optionally
  populated from a local .env file that is NOT committed.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


def load_dotenv(dotenv_path: str) -> None:
    """
    Minimal .env loader.

    - Lines like KEY=VALUE
    - Ignores blanks and comments (# ...)
    - Does not override already-set environment variables.
    """

    if not dotenv_path:
        return
    if not os.path.exists(dotenv_path):
        return

    with open(dotenv_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            if not key:
                continue
            val = val.strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if key not in os.environ:
                os.environ[key] = val


def load_universe_config(config_path: str) -> Dict[str, Any]:
    config_path = os.path.abspath(config_path)
    config_dir = os.path.dirname(config_path)

    # Prefer a .env alongside the config for local secrets.
    load_dotenv(os.path.join(config_dir, ".env"))

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if not isinstance(cfg, dict):
        raise ValueError("Universe config must be a JSON object at the root.")

    cfg.setdefault("ha", {})
    cfg.setdefault("render", {})
    cfg.setdefault("galaxies", {})

    # Render defaults.
    render = cfg["render"]
    render.setdefault("window", {"width": 1400, "height": 900})
    render.setdefault("layout", "radial")  # radial | grid
    render.setdefault("max_rings_per_planet", 10)
    render.setdefault("outer_radius", 1.05)
    render.setdefault("inner_radius", 0.38)
    render.setdefault("max_fps", 60)
    render.setdefault("stream_fps", 10)
    render.setdefault("radial_padding", 1.28)
    render.setdefault("align_interval_bars", 4.0)
    render.setdefault("target_bpm", 84.0)
    render.setdefault("beats_per_measure", 8.0)

    # HA defaults.
    ha = cfg["ha"]
    ha.setdefault("url", "")
    ha.setdefault("token_env", "HA_TOKEN")
    ha.setdefault("context_entity", "input_select.gyrodynamo_galaxy")
    ha.setdefault("poll_interval_s", 1.5)
    ha.setdefault("timeout_s", 5.0)

    return cfg


def list_galaxies(cfg: Dict[str, Any]) -> List[str]:
    galaxies = cfg.get("galaxies") or {}
    if not isinstance(galaxies, dict):
        return []
    return list(galaxies.keys())


def get_galaxy_cfg(cfg: Dict[str, Any], galaxy_id: str) -> Optional[Dict[str, Any]]:
    galaxies = cfg.get("galaxies") or {}
    if not isinstance(galaxies, dict):
        return None
    if galaxy_id in galaxies:
        val = galaxies.get(galaxy_id)
        return val if isinstance(val, dict) else None
    # Case-insensitive fallback
    g_lower = (galaxy_id or "").strip().lower()
    for k, v in galaxies.items():
        if str(k).lower() == g_lower and isinstance(v, dict):
            return v
    return None

