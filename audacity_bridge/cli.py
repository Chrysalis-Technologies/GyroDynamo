"""CLI entry point for local Audacity bridge commands."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import replace
from typing import Optional

from .commands import AudacityBridge
from .config import load_config_from_env
from .errors import AudacityBridgeError
from .workflows.horn_cascade import run_horn_cascade_workflow
from .workflows.sample_workflow import run_sample_workflow


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _build_bridge(env_file: Optional[str], log_level: Optional[str]) -> AudacityBridge:
    config = load_config_from_env(env_file=env_file)
    if log_level:
        config = replace(config, log_level=log_level.upper())
    _setup_logging(config.log_level)
    return AudacityBridge(config=config)


def _print_data(value: object) -> None:
    if isinstance(value, (dict, list)):
        print(json.dumps(value, indent=2, sort_keys=True))
    else:
        print(str(value))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="audacity-bridge", description="Local Audacity mod-script-pipe bridge")
    parser.add_argument("--env-file", help="Optional env file for bridge config.")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Override log level.")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ping", help="Health check the Audacity pipe connection.")

    p_raw = sub.add_parser("raw", help="Send a raw Audacity command string.")
    p_raw.add_argument("raw_command", help='Example: "Help:" or "GetInfo: Type=Tracks Format=JSON"')
    p_raw.add_argument("--allow-fail", action="store_true", help="Return output even if Audacity reports failed status.")

    p_help = sub.add_parser("help", help="Run Audacity Help command.")
    p_help.add_argument("--command-name", help="Optional command to inspect.")
    p_help.add_argument("--format", default="JSON", choices=["JSON", "Brief", "LISP"], help="Help output format.")

    p_info = sub.add_parser("info", help="Run Audacity GetInfo command.")
    p_info.add_argument("--type", dest="info_type", default="Tracks", help="Info type: Tracks, Clips, Commands, etc.")
    p_info.add_argument("--format", default="JSON", choices=["JSON", "Brief", "LISP"], help="Output format.")

    p_open = sub.add_parser("open-project", help="Open an existing Audacity .aup3 project.")
    p_open.add_argument("path", help="Path to .aup3 project file.")
    p_open.add_argument("--add-to-history", action="store_true", help="Set AddToHistory=1 on OpenProject2.")

    p_import = sub.add_parser("import", help="Import an audio file into the active project.")
    p_import.add_argument("path", help="Path to input audio file.")

    p_select = sub.add_parser("select", help="Select time region.")
    p_select.add_argument("--start", type=float, required=True)
    p_select.add_argument("--end", type=float, required=True)
    p_select.add_argument("--relative-to", default="ProjectStart", help="ProjectStart, ProjectEnd, SelectionStart, SelectionEnd")

    p_silence = sub.add_parser("add-silence", help="Append silence to the current project audio.")
    p_silence.add_argument("--duration", type=float, required=True)

    p_tempo = sub.add_parser("change-tempo", help="Apply ChangeTempo effect to current selection.")
    p_tempo.add_argument("--percent", type=float, required=True, help="Tempo change percent (e.g. -5, 10).")

    p_effect = sub.add_parser("effect", help="Apply a raw effect/macro command.")
    p_effect.add_argument("effect_command", help='Example: "Echo:" or "Reverb:"')

    p_export = sub.add_parser("export", help="Export audio with Export2.")
    p_export.add_argument("path", help="Output file path.")
    p_export.add_argument("--format", dest="format_name", help="Optional extension/format hint (wav, mp3, flac).")
    p_export.add_argument("--channels", type=int, default=2)

    p_save = sub.add_parser("save-project", help="Save project as .aup3.")
    p_save.add_argument("path", help="Project path or stem.")

    p_workflow = sub.add_parser("workflow", help="Run built-in workflow scripts.")
    workflow_sub = p_workflow.add_subparsers(dest="workflow_name", required=True)

    p_sample = workflow_sub.add_parser("sample", help="Sample import/edit/export workflow.")
    p_sample.add_argument("--input", required=True, help="Input audio file.")
    p_sample.add_argument("--output", required=True, help="Output audio file.")
    p_sample.add_argument("--silence", type=float, default=1.5, help="Seconds of tail silence to add.")
    p_sample.add_argument("--tempo", type=float, default=-5.0, help="Tempo change percent.")
    p_sample.add_argument("--effect", help="Optional raw effect command; if set, tempo step is skipped.")
    p_sample.add_argument("--format", dest="format_name", help="Optional export format extension.")

    p_horn = workflow_sub.add_parser("horn-cascade", help="Open layered horn project, extend tail, process, export.")
    p_horn.add_argument("--project", required=True, help="Path to input .aup3 project.")
    p_horn.add_argument("--output", required=True, help="Output audio file.")
    p_horn.add_argument("--tail-silence", type=float, default=2.0, help="Seconds of trailing silence to add.")
    p_horn.add_argument("--tempo", type=float, help="Optional tempo change percent.")
    p_horn.add_argument("--effect", default="Reverb:", help='Raw effect command to apply (default: "Reverb:").')
    p_horn.add_argument("--save-project-copy", help="Optional output .aup3 copy path.")
    p_horn.add_argument("--format", dest="format_name", help="Optional export format extension.")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    bridge = _build_bridge(args.env_file, args.log_level)

    try:
        if args.command == "ping":
            bridge.connect()
            ok = bridge.ping()
            print("OK" if ok else "NOT_OK")
            return 0 if ok else 1

        if args.command == "raw":
            response = bridge.raw_command(args.raw_command, expect_ok=not args.allow_fail)
            print(response.raw.strip())
            return 0

        if args.command == "help":
            data = bridge.help(command=args.command_name, fmt=args.format)
            _print_data(data)
            return 0

        if args.command == "info":
            data = bridge.get_info(info_type=args.info_type, fmt=args.format)
            _print_data(data)
            return 0

        if args.command == "open-project":
            bridge.open_project(args.path, add_to_history=args.add_to_history)
            print("ProjectOpened")
            return 0

        if args.command == "import":
            bridge.import_audio(args.path)
            print("Imported")
            return 0

        if args.command == "select":
            bridge.select_time(args.start, args.end, relative_to=args.relative_to)
            print("Selected")
            return 0

        if args.command == "add-silence":
            bridge.add_silence(args.duration)
            print("SilenceAdded")
            return 0

        if args.command == "change-tempo":
            bridge.change_tempo(args.percent)
            print("TempoChanged")
            return 0

        if args.command == "effect":
            bridge.apply_macro_or_effect(args.effect_command)
            print("EffectApplied")
            return 0

        if args.command == "export":
            bridge.export_audio(args.path, format=args.format_name, num_channels=args.channels)
            print("Exported")
            return 0

        if args.command == "save-project":
            bridge.save_project(args.path)
            print("ProjectSaved")
            return 0

        if args.command == "workflow" and args.workflow_name == "sample":
            output = run_sample_workflow(
                bridge,
                input_path=args.input,
                output_path=args.output,
                silence_duration_s=args.silence,
                tempo_percent=None if args.effect else args.tempo,
                effect_command=args.effect,
                export_format=args.format_name,
            )
            print(f"WorkflowComplete: {output}")
            return 0

        if args.command == "workflow" and args.workflow_name == "horn-cascade":
            output = run_horn_cascade_workflow(
                bridge,
                project_path=args.project,
                output_path=args.output,
                tail_silence_s=args.tail_silence,
                tempo_percent=args.tempo,
                effect_command=args.effect,
                save_project_copy_path=args.save_project_copy,
                export_format=args.format_name,
            )
            print(f"WorkflowComplete: {output}")
            return 0

        parser.error("Unknown command")
        return 2
    except (AudacityBridgeError, OSError, ValueError) as exc:
        logging.getLogger("audacity_bridge.cli").error("%s", exc)
        return 1
    finally:
        bridge.disconnect()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
