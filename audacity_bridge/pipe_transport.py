"""Windows named-pipe transport for Audacity mod-script-pipe."""

from __future__ import annotations

import logging
import threading
import time
from queue import Empty, Queue
from typing import Callable, Optional, TextIO, Type

from .config import AudacityBridgeConfig
from .errors import (
    AudacityCommandError,
    AudacityConnectionError,
    AudacityResponseTimeoutError,
)


class NamedPipeTransport:
    """Transport layer that talks to Audacity through named pipes."""

    def __init__(self, config: AudacityBridgeConfig, *, logger: Optional[logging.Logger] = None) -> None:
        self._config = config
        self._logger = logger or logging.getLogger("audacity_bridge.transport")
        self._to_pipe: Optional[TextIO] = None
        self._from_pipe: Optional[TextIO] = None
        self._lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        return self._to_pipe is not None and self._from_pipe is not None

    def connect(self) -> None:
        with self._lock:
            self._connect_locked()

    def _connect_locked(self) -> None:
        if self.is_connected:
            return

        self._logger.debug("Connecting to Audacity pipes: to=%s from=%s", self._config.to_pipe_path, self._config.from_pipe_path)

        try:
            self._to_pipe = self._open_pipe_with_timeout(
                self._config.to_pipe_path,
                mode="w",
                timeout_s=self._config.connect_timeout_s,
                action_name="open write pipe",
                timeout_exc_cls=AudacityConnectionError,
            )
            self._from_pipe = self._open_pipe_with_timeout(
                self._config.from_pipe_path,
                mode="r",
                timeout_s=self._config.connect_timeout_s,
                action_name="open read pipe",
                timeout_exc_cls=AudacityConnectionError,
            )
        except Exception:
            self._disconnect_locked()
            raise

    def disconnect(self) -> None:
        with self._lock:
            self._disconnect_locked()

    def _disconnect_locked(self) -> None:
        if self._to_pipe is not None:
            try:
                self._to_pipe.close()
            except OSError:
                pass
        if self._from_pipe is not None:
            try:
                self._from_pipe.close()
            except OSError:
                pass
        self._to_pipe = None
        self._from_pipe = None

    def send_command(self, command: str, *, timeout_s: Optional[float] = None) -> str:
        cmd = (command or "").strip()
        if not cmd:
            raise ValueError("Command is required.")

        timeout = float(timeout_s) if timeout_s is not None else self._config.response_timeout_s
        retries = max(0, int(self._config.command_retries))
        last_exc: Optional[Exception] = None

        for attempt in range(retries + 1):
            try:
                with self._lock:
                    self._connect_locked()
                    assert self._to_pipe is not None
                    assert self._from_pipe is not None

                    self._to_pipe.write(cmd + self._config.eol)
                    self._to_pipe.flush()

                    response = self._read_response_locked(timeout)
                    return response
            except (AudacityConnectionError, AudacityResponseTimeoutError, OSError, ValueError) as exc:
                last_exc = exc
                self._logger.warning(
                    "Command attempt %s/%s failed for '%s': %s",
                    attempt + 1,
                    retries + 1,
                    cmd,
                    exc,
                )
                with self._lock:
                    self._disconnect_locked()
                if attempt < retries:
                    time.sleep(self._config.retry_delay_s)
                    continue

        raise AudacityCommandError(f"Unable to execute command '{cmd}' after {retries + 1} attempt(s).") from last_exc

    def _open_pipe_with_timeout(
        self,
        path: str,
        *,
        mode: str,
        timeout_s: float,
        action_name: str,
        timeout_exc_cls: Type[Exception],
    ) -> TextIO:
        def _open() -> TextIO:
            return open(path, mode, encoding="utf-8", newline="", errors="replace")

        return self._run_with_timeout(
            _open,
            timeout_s=timeout_s,
            action_name=action_name,
            timeout_exc_cls=timeout_exc_cls,
        )

    def _read_response_locked(self, timeout_s: float) -> str:
        assert self._from_pipe is not None

        def _read() -> str:
            assert self._from_pipe is not None
            lines: list[str] = []
            while True:
                line = self._from_pipe.readline()
                if line == "":
                    raise AudacityConnectionError("Audacity response pipe closed while reading.")
                lines.append(line)
                if line in ("\n", "\r\n"):
                    break
            return "".join(lines)

        return self._run_with_timeout(
            _read,
            timeout_s=timeout_s,
            action_name="read command response",
            timeout_exc_cls=AudacityResponseTimeoutError,
        )

    def _run_with_timeout(
        self,
        fn: Callable[[], object],
        *,
        timeout_s: float,
        action_name: str,
        timeout_exc_cls: Type[Exception],
    ):
        queue: Queue[tuple[bool, object]] = Queue(maxsize=1)

        def _worker() -> None:
            try:
                queue.put((True, fn()))
            except Exception as exc:
                queue.put((False, exc))

        thread = threading.Thread(target=_worker, name="audacity-bridge-blocking-op", daemon=True)
        thread.start()

        try:
            success, value = queue.get(timeout=max(0.01, timeout_s))
        except Empty as exc:
            raise timeout_exc_cls(f"Timed out while trying to {action_name} after {timeout_s:.2f}s.") from exc

        if success:
            return value

        if isinstance(value, Exception):
            raise value
        raise AudacityConnectionError(f"Unknown failure while trying to {action_name}.")
