"""
Home Assistant client + poller for GyroDynamo.

We keep this dependency-light (standard library only). Rendering should not
block on network I/O, so polling runs in a background thread and caches the
latest-known entity states.
"""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple


def parse_intish(state: Optional[str]) -> Optional[int]:
    if state is None:
        return None
    s = str(state).strip()
    if not s:
        return None
    sl = s.lower()
    if sl in ("unknown", "unavailable", "none", "null"):
        return None
    try:
        return int(float(sl))
    except ValueError:
        m = re.search(r"-?\d+", sl)
        if m:
            try:
                return int(m.group(0))
            except ValueError:
                return None
        return None


@dataclass(frozen=True)
class CachedState:
    state: Optional[str]
    attributes: Dict[str, Any]
    updated_s: float


class HomeAssistantREST:
    def __init__(self, base_url: str, token: str, *, timeout_s: float = 5.0) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.token = token or ""
        self.timeout_s = float(timeout_s)

    def _request_json(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
            raw = resp.read()
        return json.loads(raw.decode("utf-8"))

    def get_state(self, entity_id: str) -> Tuple[Optional[str], Dict[str, Any]]:
        entity_id = (entity_id or "").strip()
        if not entity_id:
            return (None, {})

        # Entity IDs are already URL-safe, but keep this robust.
        quoted = urllib.parse.quote(entity_id, safe="._-")
        try:
            obj = self._request_json(f"/api/states/{quoted}")
            state = obj.get("state")
            attrs = obj.get("attributes") or {}
            if not isinstance(attrs, dict):
                attrs = {}
            return (state, attrs)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Missing entity -> treat as unknown but not a connectivity failure.
                return (None, {})
            raise


class HomeAssistantPoller:
    """
    Polls entity states and caches results.

    - Keeps last-known values when HA is unreachable.
    - Tracks online/offline + last error for UI overlay.
    """

    def __init__(self, rest: Optional[HomeAssistantREST], *, poll_interval_s: float = 1.5) -> None:
        self._rest = rest
        self._poll_interval_s = max(0.5, float(poll_interval_s))

        self._lock = threading.Lock()
        self._context_entity_id: Optional[str] = None
        self._entity_ids: list[str] = []
        self._cache: Dict[str, CachedState] = {}

        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="ha-poller", daemon=True)

        self._online = False
        self._last_ok_s: Optional[float] = None
        self._last_error: Optional[str] = None

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self, *, timeout_s: float = 2.0) -> None:
        self._stop.set()
        self._thread.join(timeout=timeout_s)

    def set_targets(self, *, context_entity_id: Optional[str], entity_ids: Iterable[str]) -> None:
        context_entity_id = (context_entity_id or "").strip() or None
        ids: list[str] = []
        seen: set[str] = set()
        for eid in entity_ids:
            eid = (eid or "").strip()
            if not eid or eid in seen:
                continue
            seen.add(eid)
            ids.append(eid)
        with self._lock:
            self._context_entity_id = context_entity_id
            self._entity_ids = ids

    def get_cached(self, entity_id: str) -> Optional[CachedState]:
        with self._lock:
            return self._cache.get(entity_id)

    def get_context(self) -> Optional[str]:
        with self._lock:
            eid = self._context_entity_id
            if not eid:
                return None
            st = self._cache.get(eid)
            if st is None:
                return None
            if st.state is None:
                return None
            s = str(st.state).strip()
            if not s or s.lower() in ("unknown", "unavailable", "none"):
                return None
            return s

    @property
    def online(self) -> bool:
        return bool(self._online)

    @property
    def last_ok_s(self) -> Optional[float]:
        return self._last_ok_s

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def _run(self) -> None:
        backoff_s = self._poll_interval_s
        backoff_max_s = 15.0

        while not self._stop.is_set():
            rest = self._rest
            if rest is None or not rest.base_url or not rest.token:
                self._online = False
                if rest is None or not rest.base_url:
                    self._last_error = "No HA URL configured"
                elif not rest.token:
                    self._last_error = "No HA token configured"
                self._stop.wait(self._poll_interval_s)
                continue

            with self._lock:
                context_eid = self._context_entity_id
                entity_ids = list(self._entity_ids)

            # Poll context first (if configured), then the rest.
            targets: list[str] = []
            if context_eid:
                targets.append(context_eid)
            targets.extend([eid for eid in entity_ids if eid != context_eid])

            any_ok = False
            now_s = time.time()
            try:
                for eid in targets:
                    state, attrs = rest.get_state(eid)
                    any_ok = True
                    with self._lock:
                        self._cache[eid] = CachedState(state=state, attributes=attrs, updated_s=now_s)

                if any_ok:
                    self._online = True
                    self._last_ok_s = now_s
                    self._last_error = None
                    backoff_s = self._poll_interval_s
                else:
                    self._online = False
                    self._last_error = "No targets"
            except Exception as e:
                self._online = False
                self._last_error = f"{type(e).__name__}: {e}"
                backoff_s = min(backoff_max_s, max(self._poll_interval_s, backoff_s * 1.6))
                self._stop.wait(backoff_s)
                continue

            self._stop.wait(self._poll_interval_s)

