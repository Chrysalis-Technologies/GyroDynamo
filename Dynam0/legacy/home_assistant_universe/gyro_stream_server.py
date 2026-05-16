"""
MJPEG streaming server for GyroDynamo (for embedding in Home Assistant).

Endpoints:
- /stream.mjpeg  multipart MJPEG stream
- /snapshot.jpg  latest single JPEG
- /stream/<galaxy_id>.mjpeg  per-galaxy MJPEG stream
- /snapshot/<galaxy_id>.jpg  per-galaxy single JPEG
- /layout/<galaxy_id>.json   optional per-galaxy layout metadata
- /              simple HTML page with <img src="/stream.mjpeg">

JPEG encoding uses Pillow (PIL). We keep it optional so window-only mode
requires only pygame.
"""

from __future__ import annotations

import io
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore


class LatestJpegFrame:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jpeg: Optional[bytes] = None
        self._updated_s: float = 0.0

    def update_from_rgb(
        self,
        *,
        rgb_bytes: bytes,
        size: Tuple[int, int],
        quality: int = 85,
        subsampling: str = "4:2:0",
        galaxy_id: Optional[str] = None,
    ) -> None:
        if Image is None:
            raise RuntimeError("Pillow is required for MJPEG mode. Install with: pip install pillow")

        img = Image.frombytes("RGB", size, rgb_bytes)  # type: ignore[attr-defined]
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=int(quality), optimize=True, subsampling=subsampling)
        jpeg = buf.getvalue()
        now_s = time.time()
        with self._lock:
            self._jpeg = jpeg
            self._updated_s = now_s

    def update_from_surface(self, surface, *, quality: int = 85, galaxy_id: Optional[str] = None) -> None:
        # Import locally so window-only mode doesn't require surfarray/numpy.
        import pygame

        rgb = pygame.image.tostring(surface, "RGB")
        self.update_from_rgb(rgb_bytes=rgb, size=surface.get_size(), quality=quality, galaxy_id=galaxy_id)

    def get(self, galaxy_id: Optional[str] = None) -> Tuple[Optional[bytes], float]:
        with self._lock:
            return self._jpeg, self._updated_s


class _MjpegServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address,
        RequestHandlerClass,
        frame: Any,
        *,
        layout_store: Optional["LatestLayoutStore"] = None,
        galaxy_ids: Optional[List[str]] = None,
    ):
        super().__init__(server_address, RequestHandlerClass)
        # Back-compat: old code refers to "frame". New handler uses "frames".
        self.frame = frame
        self.frames = frame
        self.layout_store = layout_store
        self.galaxy_ids = list(galaxy_ids or [])
        self.stop_event = threading.Event()


class LatestJpegFrames:
    """Thread-safe multi-key frame store for per-galaxy streaming."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frames: Dict[str, Tuple[Optional[bytes], float]] = {}
        self._default_galaxy_id: Optional[str] = None

    def set_default(self, galaxy_id: Optional[str]) -> None:
        g = (galaxy_id or "").strip().lower() or None
        with self._lock:
            self._default_galaxy_id = g

    def get_default(self) -> Optional[str]:
        with self._lock:
            return self._default_galaxy_id

    def update_from_rgb(
        self,
        *,
        rgb_bytes: bytes,
        size: Tuple[int, int],
        galaxy_id: str,
        quality: int = 85,
        subsampling: str = "4:2:0",
    ) -> None:
        if Image is None:
            raise RuntimeError("Pillow is required for MJPEG mode. Install with: pip install pillow")

        g = (galaxy_id or "").strip().lower()
        if not g:
            raise ValueError("galaxy_id is required")

        img = Image.frombytes("RGB", size, rgb_bytes)  # type: ignore[attr-defined]
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=int(quality), optimize=True, subsampling=subsampling)
        jpeg = buf.getvalue()
        now_s = time.time()
        with self._lock:
            self._frames[g] = (jpeg, now_s)
            self._default_galaxy_id = self._default_galaxy_id or g

    def update_from_surface(self, surface, *, galaxy_id: str, quality: int = 85) -> None:
        import pygame

        rgb = pygame.image.tostring(surface, "RGB")
        self.update_from_rgb(rgb_bytes=rgb, size=surface.get_size(), galaxy_id=galaxy_id, quality=quality)

    def touch(self, galaxy_id: str) -> None:
        """Bump updated time without re-encoding (useful for static placeholders)."""
        g = (galaxy_id or "").strip().lower()
        if not g:
            return
        now_s = time.time()
        with self._lock:
            jpeg, _ = self._frames.get(g, (None, 0.0))
            if jpeg is not None:
                self._frames[g] = (jpeg, now_s)

    def get(self, galaxy_id: Optional[str] = None) -> Tuple[Optional[bytes], float]:
        g = (galaxy_id or "").strip().lower() if galaxy_id else None
        with self._lock:
            if g is None:
                g = self._default_galaxy_id
            if not g:
                return (None, 0.0)
            return self._frames.get(g, (None, 0.0))


class LatestLayoutStore:
    """Thread-safe store for per-galaxy layout metadata (e.g., star positions)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._layouts: Dict[str, Dict[str, Any]] = {}

    def update(self, galaxy_id: str, layout: Dict[str, Any]) -> None:
        g = (galaxy_id or "").strip().lower()
        if not g:
            return
        if not isinstance(layout, dict):
            return
        with self._lock:
            self._layouts[g] = layout

    def get(self, galaxy_id: str) -> Optional[Dict[str, Any]]:
        g = (galaxy_id or "").strip().lower()
        if not g:
            return None
        with self._lock:
            val = self._layouts.get(g)
            return dict(val) if isinstance(val, dict) else None


class MjpegHandler(BaseHTTPRequestHandler):
    server: _MjpegServer  # help type checkers

    def log_message(self, fmt: str, *args) -> None:
        # Keep console noise low; the renderer already has its own overlay.
        return

    def do_GET(self) -> None:  # noqa: N802
        path = (self.path or "/").split("?", 1)[0]

        if path in ("/", "/index.html"):
            galaxy_links = ""
            try:
                galaxy_ids = self.server.galaxy_ids or []
                if galaxy_ids:
                    items = []
                    for g in galaxy_ids:
                        g2 = (g or "").strip().lower()
                        if not g2:
                            continue
                        items.append(f"<li><a href='/stream/{g2}.mjpeg'>{g2}</a></li>")
                    if items:
                        galaxy_links = "<ul style='margin:16px 0;padding-left:20px;'>" + "".join(items) + "</ul>"
            except Exception:
                galaxy_links = ""

            body = (
                "<!doctype html><html><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                "<title>GyroDynamo Stream</title></head>"
                "<body style='margin:0;background:#000;color:#cfe8ff;font-family:system-ui,Segoe UI,Arial;'>"
                "<div style='padding:12px 14px;'>"
                "<div style='font-weight:700;letter-spacing:0.08em;opacity:0.9;'>GYRODYNAMO</div>"
                "<div style='opacity:0.75;margin:6px 0 12px 0;'>MJPEG streams</div>"
                "<div style='display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start;'>"
                "<div style='flex:1;min-width:320px;max-width:1000px;'>"
                "<img src='/stream.mjpeg' style='width:100%;height:auto;border-radius:10px;border:1px solid rgba(255,255,255,0.14);'/>"
                "</div>"
                "<div style='width:260px;opacity:0.85;'>"
                "<div style='font-weight:700;margin-bottom:8px;'>Per-galaxy</div>"
                + galaxy_links
                + "</div>"
                "</div>"
                "</div>"
                "</body></html>"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path in ("/healthz", "/health"):
            body = b"ok\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/snapshot.jpg":
            jpeg, _ = self.server.frames.get(None)
            if not jpeg:
                self.send_error(503, "No frame yet")
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(jpeg)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(jpeg)
            return

        if path.startswith("/snapshot/") and path.endswith(".jpg"):
            galaxy_id = path[len("/snapshot/") : -len(".jpg")]
            jpeg, _ = self.server.frames.get(galaxy_id)
            if not jpeg:
                self.send_error(503, "No frame yet")
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(jpeg)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(jpeg)
            return

        if path == "/stream.mjpeg":
            galaxy_id = None
        elif path.startswith("/stream/") and path.endswith(".mjpeg"):
            galaxy_id = path[len("/stream/") : -len(".mjpeg")]
        else:
            galaxy_id = "___not_stream___"

        if galaxy_id != "___not_stream___":
            boundary = "frame"
            self.send_response(200)
            self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={boundary}")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

            last_sent_s = 0.0
            try:
                while not self.server.stop_event.is_set():
                    jpeg, updated_s = self.server.frames.get(galaxy_id)
                    if not jpeg or updated_s <= last_sent_s:
                        time.sleep(0.05)
                        continue
                    last_sent_s = updated_s

                    header = (
                        f"--{boundary}\r\n"
                        "Content-Type: image/jpeg\r\n"
                        f"Content-Length: {len(jpeg)}\r\n"
                        "\r\n"
                    ).encode("ascii")
                    self.wfile.write(header)
                    self.wfile.write(jpeg)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
            except Exception:
                # Client disconnected (broken pipe) or server shutting down.
                return

            return

        if path.startswith("/layout/") and path.endswith(".json"):
            galaxy_id = path[len("/layout/") : -len(".json")]
            store = self.server.layout_store
            if store is None:
                self.send_error(404)
                return
            layout = store.get(galaxy_id)
            if not layout:
                self.send_error(404)
                return
            body = json.dumps(layout, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_error(404)


class MjpegHttpServer:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        frame: Any,
        layout_store: Optional[LatestLayoutStore] = None,
        galaxy_ids: Optional[List[str]] = None,
    ) -> None:
        self._httpd = _MjpegServer(
            (host, int(port)),
            MjpegHandler,
            frame=frame,
            layout_store=layout_store,
            galaxy_ids=galaxy_ids,
        )
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="mjpeg-server", daemon=True)

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._httpd.stop_event.set()
        self._httpd.shutdown()
        self._httpd.server_close()
