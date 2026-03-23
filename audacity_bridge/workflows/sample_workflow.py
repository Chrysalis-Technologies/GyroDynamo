"""Sample local workflow for repetitive Audacity edits."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..commands import AudacityBridge


def run_sample_workflow(
    bridge: AudacityBridge,
    *,
    input_path: str,
    output_path: str,
    silence_duration_s: float = 1.5,
    tempo_percent: Optional[float] = -5.0,
    effect_command: Optional[str] = None,
    export_format: Optional[str] = None,
) -> Path:
    """
    Workflow steps:
    1) connect
    2) import audio
    3) add trailing silence
    4) apply tempo change or effect command
    5) export
    """

    logger = logging.getLogger("audacity_bridge.workflow.sample")
    in_path = Path(input_path).resolve()
    out_path = Path(output_path).resolve()

    if not in_path.exists():
        raise FileNotFoundError(f"Input audio file not found: {in_path}")

    logger.info("Connecting to Audacity mod-script-pipe")
    bridge.connect()

    logger.info("Importing audio: %s", in_path)
    bridge.import_audio(str(in_path))

    logger.info("Adding trailing silence: %.3fs", silence_duration_s)
    bridge.add_silence(float(silence_duration_s))

    logger.info("Selecting all audio before effect step")
    bridge.select_all()

    if effect_command:
        logger.info("Applying effect/macro command: %s", effect_command)
        bridge.apply_macro_or_effect(effect_command)
    elif tempo_percent is not None:
        logger.info("Changing tempo: %.2f%%", float(tempo_percent))
        bridge.change_tempo(float(tempo_percent))
    else:
        logger.info("Skipping effect step (no tempo/effect requested)")

    logger.info("Exporting processed output: %s", out_path)
    bridge.export_audio(str(out_path), format=export_format)

    logger.info("Workflow finished successfully")
    return out_path
