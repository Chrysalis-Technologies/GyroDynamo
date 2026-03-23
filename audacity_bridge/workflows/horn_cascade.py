"""Workflow for layered horn projects that cascade from war-horn to siren textures."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..commands import AudacityBridge


def run_horn_cascade_workflow(
    bridge: AudacityBridge,
    *,
    project_path: str,
    output_path: str,
    tail_silence_s: float = 2.0,
    tempo_percent: Optional[float] = None,
    effect_command: Optional[str] = "Reverb:",
    save_project_copy_path: Optional[str] = None,
    export_format: Optional[str] = None,
) -> Path:
    """
    Workflow steps:
    1) connect + open existing .aup3 project
    2) select all tracks/clips
    3) add trailing silence to lengthen cascade tail
    4) optionally apply tempo change and/or effect command
    5) export mixdown
    6) optionally save a project copy
    """

    logger = logging.getLogger("audacity_bridge.workflow.horn_cascade")
    in_project = Path(project_path).resolve()
    out_file = Path(output_path).resolve()

    if not in_project.exists():
        raise FileNotFoundError(f"Audacity project not found: {in_project}")

    logger.info("Connecting to Audacity mod-script-pipe")
    bridge.connect()

    logger.info("Opening project: %s", in_project)
    bridge.open_project(str(in_project))

    logger.info("Selecting all tracks")
    bridge.select_all()

    logger.info("Adding trailing silence: %.3fs", tail_silence_s)
    bridge.add_silence(float(tail_silence_s))

    logger.info("Selecting all tracks before transform/effects")
    bridge.select_all()

    if tempo_percent is not None:
        logger.info("Applying tempo change: %.2f%%", float(tempo_percent))
        bridge.change_tempo(float(tempo_percent))

    if effect_command:
        logger.info("Applying effect/macro command: %s", effect_command)
        bridge.apply_macro_or_effect(effect_command)

    logger.info("Exporting mixed output: %s", out_file)
    bridge.export_audio(str(out_file), format=export_format)

    if save_project_copy_path:
        save_copy = Path(save_project_copy_path).resolve()
        logger.info("Saving project copy: %s", save_copy)
        bridge.save_project(str(save_copy))

    logger.info("Horn cascade workflow finished")
    return out_file
