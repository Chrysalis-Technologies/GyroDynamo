"""High-level Audacity command wrapper with raw command passthrough."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Iterable, Optional

from .config import AudacityBridgeConfig, load_config_from_env
from .errors import AudacityCommandError
from .pipe_transport import NamedPipeTransport
from .response_parser import AudacityResponse, parse_response


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.8f}".rstrip("0").rstrip(".")

    raw = str(value)
    escaped = raw.replace('"', '\\"')
    return f'"{escaped}"'


def build_command(command_name: str, **params: Any) -> str:
    name = (command_name or "").strip()
    if not name:
        raise ValueError("command_name is required")
    if name.endswith(":"):
        name = name[:-1]

    parts = [f"{name}:"]
    for key, value in params.items():
        if value is None:
            continue
        parts.append(f"{key}={_format_value(value)}")
    return " ".join(parts)


class AudacityBridge:
    """Convenience wrapper over Audacity mod-script-pipe commands."""

    def __init__(
        self,
        *,
        config: Optional[AudacityBridgeConfig] = None,
        transport: Optional[NamedPipeTransport] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.config = config or load_config_from_env()
        self.logger = logger or logging.getLogger("audacity_bridge")
        self.transport = transport or NamedPipeTransport(self.config, logger=self.logger)

    def connect(self) -> None:
        self.transport.connect()

    def disconnect(self) -> None:
        self.transport.disconnect()

    def ping(self) -> bool:
        response = self.raw_command("Help:")
        return response.ok

    def raw_command(
        self,
        command: str,
        *,
        timeout_s: Optional[float] = None,
        expect_ok: bool = True,
    ) -> AudacityResponse:
        raw = self.transport.send_command(command, timeout_s=timeout_s)
        parsed = parse_response(command, raw)
        if expect_ok and not parsed.ok:
            raise AudacityCommandError(
                f"Audacity reported a failed command status for '{command}': {parsed.status or parsed.payload}"
            )
        return parsed

    def help(self, *, command: Optional[str] = None, fmt: str = "Brief") -> Any:
        args = {"Format": fmt}
        if command:
            args["Command"] = command
        response = self.raw_command(build_command("Help", **args))
        return response.json_payload if response.json_payload is not None else response.payload

    def get_info(self, *, info_type: str = "Tracks", fmt: str = "JSON") -> Any:
        response = self.raw_command(build_command("GetInfo", Type=info_type, Format=fmt))
        return response.json_payload if response.json_payload is not None else response.payload

    def import_audio(self, path: str) -> AudacityResponse:
        source = str(Path(path).resolve())
        return self.raw_command(build_command("Import2", Filename=source))

    def open_project(self, path: str, *, add_to_history: bool = False) -> AudacityResponse:
        project_path = Path(path).resolve()
        if project_path.suffix.lower() != ".aup3":
            project_path = project_path.with_suffix(".aup3")
        if not project_path.exists():
            raise FileNotFoundError(f"Audacity project not found: {project_path}")
        return self.raw_command(
            build_command(
                "OpenProject2",
                Filename=str(project_path),
                AddToHistory=bool(add_to_history),
            )
        )

    def select_all(self) -> AudacityResponse:
        return self.raw_command("SelectAll:")

    def select_time(self, start: float, end: float, *, relative_to: str = "ProjectStart") -> AudacityResponse:
        if end < start:
            start, end = end, start
        return self.raw_command(
            build_command(
                "SelectTime",
                Start=float(start),
                End=float(end),
                RelativeTo=relative_to,
            )
        )

    def add_silence(self, duration: float) -> AudacityResponse:
        duration = float(duration)
        if duration <= 0:
            raise ValueError("duration must be > 0")

        available = self.list_commands()
        if self._supports(available, "InsertSilence"):
            return self.raw_command(build_command("InsertSilence", Duration=duration))

        if self._supports(available, "Silence"):
            # Some Audacity versions expose Silence with a Duration parameter.
            try:
                return self.raw_command(build_command("Silence", Duration=duration))
            except AudacityCommandError:
                pass

        # Fallback strategy: duplicate a small tail section and then silence it.
        # This avoids version differences in direct "insert silence" command names.
        chunk = min(duration, 0.1)
        chunk = max(0.01, chunk)
        repeats = max(1, int(math.ceil(duration / chunk)))
        appended_duration = repeats * chunk

        self.select_time(-chunk, 0.0, relative_to="ProjectEnd")
        self.raw_command(build_command("Repeat", Count=repeats))
        self.select_time(-appended_duration, 0.0, relative_to="ProjectEnd")
        result = self.raw_command("Silence:")

        overshoot = appended_duration - duration
        if overshoot > 1e-6:
            self.select_time(-overshoot, 0.0, relative_to="ProjectEnd")
            self.raw_command("Delete:")

        return result

    def change_tempo(self, percent: float) -> AudacityResponse:
        return self.raw_command(build_command("ChangeTempo", Percentage=float(percent)))

    def apply_macro_or_effect(self, command_string: str) -> AudacityResponse:
        return self.raw_command(command_string)

    def export_audio(self, path: str, *, format: Optional[str] = None, num_channels: int = 2) -> AudacityResponse:
        output = Path(path).resolve()
        if format:
            ext = "." + str(format).strip().lower().lstrip(".")
            if output.suffix.lower() != ext:
                output = output.with_suffix(ext)

        output.parent.mkdir(parents=True, exist_ok=True)
        return self.raw_command(build_command("Export2", Filename=str(output), NumChannels=int(num_channels)))

    def save_project(self, path: str) -> AudacityResponse:
        project_path = Path(path).resolve()
        project_path.parent.mkdir(parents=True, exist_ok=True)
        if project_path.suffix.lower() != ".aup3":
            project_path = project_path.with_suffix(".aup3")
        return self.raw_command(build_command("SaveProject2", Filename=str(project_path)))

    def list_commands(self) -> set[str]:
        info = self.get_info(info_type="Commands", fmt="JSON")
        return _extract_command_names(info)

    @staticmethod
    def _supports(catalog: Iterable[str], name: str) -> bool:
        target = name.strip().rstrip(":").lower()
        return any(str(item).strip().rstrip(":").lower() == target for item in catalog)


def _extract_command_names(payload: Any) -> set[str]:
    out: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                lk = str(key).strip().lower()
                if lk in {"id", "name", "command", "scriptingid", "scripting_id"} and isinstance(value, str):
                    candidate = value.strip().rstrip(":")
                    if candidate:
                        out.add(candidate)
                walk(value)
            return
        if isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return out
