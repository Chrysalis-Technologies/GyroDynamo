"""Parsers for Audacity mod-script-pipe responses."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

_STATUS_RE = re.compile(r"^BatchCommand finished:\s*(?P<status>.+?)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class AudacityResponse:
    command: str
    raw: str
    payload: str
    status: Optional[str]
    ok: bool
    json_payload: Optional[Any]


def parse_response(command: str, raw_response: str) -> AudacityResponse:
    """
    Parse a command response into status, payload, and optional JSON payload.

    Audacity typically terminates responses with:
    - an empty line
    - a status line like: "BatchCommand finished: OK"
    """

    raw = (raw_response or "").replace("\0", "")
    lines = [line.strip() for line in raw.splitlines()]
    lines = [line for line in lines if line]

    status: Optional[str] = None
    payload_lines = list(lines)
    if lines:
        match = _STATUS_RE.match(lines[-1])
        if match:
            status = match.group("status").strip()
            payload_lines = lines[:-1]

    payload = "\n".join(payload_lines).strip()
    json_payload: Optional[Any] = None

    if payload.startswith("{") or payload.startswith("["):
        try:
            json_payload = json.loads(payload)
        except json.JSONDecodeError:
            json_payload = None

    ok = True
    if status is not None:
        low = status.lower()
        if "failed" in low or "error" in low:
            ok = False
    elif payload.lower().startswith("error"):
        ok = False

    return AudacityResponse(
        command=command,
        raw=raw,
        payload=payload,
        status=status,
        ok=ok,
        json_payload=json_payload,
    )
