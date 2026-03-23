"""Configuration for local Audacity mod-script-pipe transport."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

DEFAULT_TO_PIPE = r"\\.\pipe\ToSrvPipe"
DEFAULT_FROM_PIPE = r"\\.\pipe\FromSrvPipe"


@dataclass(frozen=True)
class AudacityBridgeConfig:
    to_pipe_path: str = DEFAULT_TO_PIPE
    from_pipe_path: str = DEFAULT_FROM_PIPE
    eol: str = "\r\n\0"
    connect_timeout_s: float = 6.0
    response_timeout_s: float = 30.0
    command_retries: int = 1
    retry_delay_s: float = 0.25
    log_level: str = "INFO"


def load_env_file(path: str) -> None:
    """Load key=value pairs from an env file without overriding existing env vars."""

    if not path:
        return
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                continue
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            if key not in os.environ:
                os.environ[key] = value


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def load_config_from_env(*, env_file: Optional[str] = None) -> AudacityBridgeConfig:
    if env_file:
        load_env_file(env_file)

    return AudacityBridgeConfig(
        to_pipe_path=os.getenv("AUDACITY_PIPE_TO", DEFAULT_TO_PIPE),
        from_pipe_path=os.getenv("AUDACITY_PIPE_FROM", DEFAULT_FROM_PIPE),
        eol=os.getenv("AUDACITY_PIPE_EOL", "\r\n\0"),
        connect_timeout_s=_env_float("AUDACITY_PIPE_CONNECT_TIMEOUT_S", 6.0),
        response_timeout_s=_env_float("AUDACITY_PIPE_RESPONSE_TIMEOUT_S", 30.0),
        command_retries=max(0, _env_int("AUDACITY_PIPE_COMMAND_RETRIES", 1)),
        retry_delay_s=max(0.0, _env_float("AUDACITY_PIPE_RETRY_DELAY_S", 0.25)),
        log_level=os.getenv("AUDACITY_BRIDGE_LOG_LEVEL", "INFO").upper(),
    )
