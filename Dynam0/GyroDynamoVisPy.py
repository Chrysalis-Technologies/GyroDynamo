"""
GyroDynamo standalone desktop visualizer.

The top half of this module is intentionally display-free so config and CLI
behavior can be unit tested without opening a GL window.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

try:
    from vispy import app, scene
except Exception:  # pragma: no cover - exercised only when runtime deps are missing.
    app = None
    scene = None

TAU = 2.0 * math.pi
ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT_DIR / "gyro_desktop_config.json"


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def parse_size(text: str | list[int] | tuple[int, int]) -> tuple[int, int]:
    if isinstance(text, (list, tuple)):
        if len(text) != 2:
            raise ValueError("size must contain width and height")
        w = int(text[0])
        h = int(text[1])
    else:
        parts = str(text).lower().split("x", 1)
        if len(parts) != 2:
            raise ValueError("size must be WIDTHxHEIGHT, e.g. 1600x1000")
        w = int(parts[0].strip())
        h = int(parts[1].strip())

    if w < 640 or h < 480:
        raise ValueError("size must be at least 640x480")
    return (w, h)


def clamp_ring_count(value: int | str) -> int:
    return max(3, min(10, int(value)))


def rot_x(a: float) -> np.ndarray:
    c = math.cos(a)
    s = math.sin(a)
    return np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, c, -s],
            [0.0, s, c],
        ],
        dtype=np.float32,
    )


def rot_y(a: float) -> np.ndarray:
    c = math.cos(a)
    s = math.sin(a)
    return np.array(
        [
            [c, 0.0, s],
            [0.0, 1.0, 0.0],
            [-s, 0.0, c],
        ],
        dtype=np.float32,
    )


def rot_z(a: float) -> np.ndarray:
    c = math.cos(a)
    s = math.sin(a)
    return np.array(
        [
            [c, -s, 0.0],
            [s, c, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )


def hsv_to_rgb_np(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    # Vectorized HSV->RGB conversion (h,s,v are [0..1] arrays).
    h6 = h * 6.0
    i = np.floor(h6).astype(np.int32)
    f = h6 - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    i = np.mod(i, 6)

    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack((r, g, b), axis=1).astype(np.float32)


def write_bmp(path: str | Path, image: np.ndarray) -> None:
    arr = np.asarray(image)
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise ValueError("screenshot image must be HxWxRGB or HxWxRGBA")
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)

    rgb = arr[:, :, :3]
    height, width, _ = rgb.shape
    row_stride = (width * 3 + 3) & ~3
    pixel_bytes = row_stride * height
    file_size = 14 + 40 + pixel_bytes
    padding = b"\x00" * (row_stride - width * 3)

    with Path(path).open("wb") as f:
        f.write(struct.pack("<2sIHHI", b"BM", file_size, 0, 0, 54))
        f.write(struct.pack("<IIIHHIIIIII", 40, width, height, 1, 24, 0, pixel_bytes, 2835, 2835, 0, 0))
        for row in rgb[::-1]:
            f.write(row[:, ::-1].tobytes())
            f.write(padding)


@dataclass(frozen=True)
class Palette:
    name: str
    hue_start: float
    hue_span: float
    saturation: float
    value: float


@dataclass(frozen=True)
class RingConfig:
    radius: float
    segments: int
    spin_ratio: float
    tx_ratio: float
    ty_ratio: float
    axis_tilt: float
    phase: float
    width: float
    glow_width: float
    stripe_count: float


@dataclass(frozen=True)
class DesktopConfig:
    size: tuple[int, int]
    bpm: float
    rings: int
    palette_index: int
    fullscreen: bool
    camera_drift: bool
    hud: bool
    tempo_scale: float
    screenshot_dir: Path
    backend: str
    beats_per_measure: int
    align_bars: int


PALETTES = [
    Palette("Solar Forge", 0.08, 0.55, 0.78, 0.95),
    Palette("Ion Aurora", 0.42, 0.36, 0.72, 0.96),
    Palette("Copper Flux", 0.02, 0.20, 0.84, 0.98),
    Palette("Arctic Neon", 0.52, 0.15, 0.56, 1.00),
]

DEFAULT_CONFIG: dict[str, Any] = {
    "size": "1600x1000",
    "bpm": 84.0,
    "rings": 7,
    "palette": "Solar Forge",
    "fullscreen": False,
    "camera_drift": True,
    "hud": True,
    "tempo_scale": 1.0,
    "screenshot_dir": "captures",
    "backend": "glfw",
    "beats_per_measure": 8,
    "align_bars": 4,
}

CONTROL_RANGES = {
    "bpm": (30.0, 220.0),
    "tempo": (0.25, 3.0),
    "rings": (3.0, 10.0),
}


def _normalized_palette_key(value: str) -> str:
    return "".join(ch for ch in value.casefold() if ch.isalnum())


def resolve_palette(value: str | int | None) -> int:
    if value is None or value == "":
        return 0

    if isinstance(value, int) or str(value).strip().isdigit():
        index = int(value)
        if 0 <= index < len(PALETTES):
            return index
        raise ValueError(f"palette index must be between 0 and {len(PALETTES) - 1}")

    lookup = {_normalized_palette_key(p.name): i for i, p in enumerate(PALETTES)}
    key = _normalized_palette_key(str(value))
    if key in lookup:
        return lookup[key]

    valid = ", ".join(p.name for p in PALETTES)
    raise ValueError(f"unknown palette {value!r}; valid palettes: {valid}")


def build_ring_configs(ring_count: int) -> list[RingConfig]:
    rings: list[RingConfig] = []
    count = clamp_ring_count(ring_count)
    for i in range(count):
        t = i / max(1, count - 1)
        radius = 1.55 - 1.15 * t
        segments = int(820 - 420 * t)
        width = 2.8 - 1.0 * t
        glow_width = 11.0 - 4.8 * t

        spin = (4.0 + i * 1.8) * (-1.0 if i % 2 else 1.0)
        tx = (2.0 + (i % 4) * 0.9) * (-1.0 if i % 3 == 1 else 1.0)
        ty = (2.8 + (i % 5) * 0.8) * (-1.0 if i % 2 else 1.0)

        rings.append(
            RingConfig(
                radius=radius,
                segments=max(220, segments),
                spin_ratio=spin,
                tx_ratio=tx,
                ty_ratio=ty,
                axis_tilt=math.radians(-30.0 + i * 10.0),
                phase=i * 0.67,
                width=width,
                glow_width=glow_width,
                stripe_count=3.0 + 0.7 * i,
            )
        )
    return rings


def load_config_file(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        if config_path == DEFAULT_CONFIG_PATH:
            return {}
        raise FileNotFoundError(f"config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("desktop config must be a JSON object")
    return data


def resolve_desktop_config(args: argparse.Namespace) -> DesktopConfig:
    config_path = Path(args.config or DEFAULT_CONFIG_PATH)
    raw = {**DEFAULT_CONFIG, **load_config_file(config_path)}

    if args.size is not None:
        raw["size"] = args.size
    if args.bpm is not None:
        raw["bpm"] = args.bpm
    if args.rings is not None:
        raw["rings"] = args.rings
    if args.palette is not None:
        raw["palette"] = args.palette
    if args.fullscreen:
        raw["fullscreen"] = True
    if args.no_hud:
        raw["hud"] = False
    if args.no_camera_drift:
        raw["camera_drift"] = False
    if args.screenshot_dir is not None:
        raw["screenshot_dir"] = args.screenshot_dir
    if args.backend is not None:
        raw["backend"] = args.backend

    return DesktopConfig(
        size=parse_size(raw["size"]),
        bpm=clamp(float(raw["bpm"]), 30.0, 220.0),
        rings=clamp_ring_count(raw["rings"]),
        palette_index=resolve_palette(raw.get("palette")),
        fullscreen=bool(raw["fullscreen"]),
        camera_drift=bool(raw["camera_drift"]),
        hud=bool(raw["hud"]),
        tempo_scale=clamp(float(raw["tempo_scale"]), 0.25, 3.0),
        screenshot_dir=(config_path.parent / str(raw["screenshot_dir"])).resolve(),
        backend=str(raw["backend"] or "glfw"),
        beats_per_measure=max(1, int(raw["beats_per_measure"])),
        align_bars=max(1, int(raw["align_bars"])),
    )


class GyroDynamoVisPy(scene.SceneCanvas if scene is not None else object):
    def __init__(
        self,
        *,
        config: DesktopConfig,
    ) -> None:
        if app is None or scene is None:
            raise RuntimeError("VisPy is not installed. Install requirements-desktop.txt first.")

        if config.backend:
            try:
                app.use_app(config.backend)
            except Exception:
                pass

        super().__init__(
            keys="interactive",
            size=config.size,
            show=False,
            title="GyroDynamo Desktop",
            bgcolor="#05070f",
            vsync=True,
        )

        self.unfreeze()
        self.bpm = config.bpm
        self.beats_per_measure = config.beats_per_measure
        self.align_bars = config.align_bars
        self.time_scale = config.tempo_scale
        self.elapsed = 0.0
        self.paused = False
        self.auto_camera = config.camera_drift
        self.palette_index = config.palette_index
        self.hud_visible = config.hud
        self.screenshot_dir = config.screenshot_dir

        self._last_t = time.perf_counter()
        self._last_title_t = 0.0
        self._last_capture_path: Path | None = None
        self._control_regions: list[tuple[str, tuple[float, float, float, float]]] = []
        self._active_control: str | None = None

        self.view = self.central_widget.add_view()
        self.view.camera = scene.cameras.TurntableCamera(
            fov=48.0,
            azimuth=18.0,
            elevation=24.0,
            distance=6.2,
            up="+z",
        )

        self._base_cam_azimuth = float(self.view.camera.azimuth)
        self._base_cam_elevation = float(self.view.camera.elevation)
        self._base_cam_distance = float(self.view.camera.distance)

        self._build_starfield()
        self._build_rings(config.rings)
        self._build_core()
        self._build_hud()
        self._apply_palette(self.palette_index)
        self._refresh_window_title(force=True)

        self.timer = app.Timer("auto", connect=self.on_timer, start=True)
        self.freeze()

    def _build_starfield(self) -> None:
        rng = np.random.default_rng(1138)
        count = 500
        u = rng.uniform(-1.0, 1.0, count).astype(np.float32)
        phi = rng.uniform(0.0, TAU, count).astype(np.float32)
        radius = rng.uniform(9.0, 16.0, count).astype(np.float32)
        xy = np.sqrt(1.0 - u * u)

        pos = np.zeros((count, 3), dtype=np.float32)
        pos[:, 0] = radius * xy * np.cos(phi)
        pos[:, 1] = radius * xy * np.sin(phi)
        pos[:, 2] = radius * u

        alpha = rng.uniform(0.06, 0.25, count).astype(np.float32)
        rgb = rng.uniform(0.72, 1.0, (count, 3)).astype(np.float32)
        colors = np.concatenate((rgb, alpha[:, None]), axis=1)
        sizes = rng.uniform(1.0, 3.0, count).astype(np.float32)

        self.stars = scene.visuals.Markers(parent=self.view.scene)
        self.stars.set_data(pos=pos, size=sizes, face_color=colors, edge_width=0.0)
        self.stars.set_gl_state("translucent", depth_test=False, blend=True)

    def _build_rings(self, ring_count: int) -> None:
        self.rings = build_ring_configs(ring_count)
        self.ring_state: list[dict[str, np.ndarray | scene.visuals.Line]] = []

        for ring in self.rings:
            theta = np.linspace(0.0, TAU, ring.segments + 1, dtype=np.float32)
            base = np.zeros((ring.segments + 1, 3), dtype=np.float32)
            base[:, 0] = ring.radius * np.cos(theta)
            base[:, 1] = ring.radius * np.sin(theta)

            glow = scene.visuals.Line(
                pos=base,
                color=(0.9, 0.9, 1.0, 0.08),
                width=ring.glow_width,
                method="gl",
                antialias=True,
                parent=self.view.scene,
            )
            glow.set_gl_state(
                "translucent",
                depth_test=True,
                blend=True,
                blend_func=("src_alpha", "one"),
            )

            core = scene.visuals.Line(
                pos=base,
                color=(0.95, 0.98, 1.0, 0.85),
                width=ring.width,
                method="gl",
                antialias=True,
                parent=self.view.scene,
            )
            core.set_gl_state(
                "translucent",
                depth_test=True,
                blend=True,
                blend_func=("src_alpha", "one_minus_src_alpha"),
            )

            self.ring_state.append(
                {
                    "theta": theta,
                    "base": base,
                    "glow": glow,
                    "core": core,
                }
            )

    def _build_core(self) -> None:
        self.core_outer = scene.visuals.Sphere(
            radius=0.28,
            method="latitude",
            parent=self.view.scene,
            color=(0.55, 0.85, 1.0, 0.16),
            subdivisions=3,
        )
        self.core_outer.set_gl_state(
            "translucent",
            depth_test=True,
            blend=True,
            blend_func=("src_alpha", "one"),
        )

        self.core_inner = scene.visuals.Sphere(
            radius=0.16,
            method="latitude",
            parent=self.view.scene,
            color=(0.98, 0.99, 1.0, 1.0),
            subdivisions=3,
        )
        self.core_inner.set_gl_state("translucent", depth_test=True, blend=True)

    def _build_hud(self) -> None:
        self.control_panel = scene.visuals.Rectangle(
            center=(250, 155),
            width=448,
            height=214,
            radius=18,
            color=(0.015, 0.020, 0.035, 0.74),
            border_color=(0.72, 0.88, 1.0, 0.18),
            border_width=1,
            parent=self.scene,
        )

        self.hud = scene.visuals.Text(
            "",
            parent=self.scene,
            color=(0.92, 0.96, 1.0, 0.95),
            font_size=13,
            pos=(44, 62),
            anchor_x="left",
            anchor_y="top",
        )
        self.status = scene.visuals.Text(
            "",
            parent=self.scene,
            color=(0.66, 0.75, 0.86, 0.92),
            font_size=9,
            pos=(44, 84),
            anchor_x="left",
            anchor_y="top",
        )

        self.sliders: dict[str, dict[str, Any]] = {}
        for name, label, y in (
            ("bpm", "BPM", 116),
            ("tempo", "TEMPO", 150),
            ("rings", "RINGS", 184),
        ):
            self.sliders[name] = self._make_slider(label=label, y=float(y))

        self.palette_chips: list[dict[str, Any]] = []
        chip_labels = ["Solar", "Ion", "Copper", "Arctic"]
        chip_colors = [
            (0.93, 0.65, 0.24, 0.72),
            (0.18, 0.78, 0.76, 0.72),
            (0.95, 0.38, 0.20, 0.72),
            (0.48, 0.78, 1.0, 0.72),
        ]
        for i, (label, color) in enumerate(zip(chip_labels, chip_colors)):
            x = 44 + i * 88
            rect = scene.visuals.Rectangle(
                center=(x + 35, 219),
                width=70,
                height=23,
                radius=10,
                color=(0.08, 0.10, 0.14, 0.78),
                border_color=color,
                border_width=1,
                parent=self.scene,
            )
            text = scene.visuals.Text(
                label,
                parent=self.scene,
                color=(0.88, 0.94, 1.0, 0.94),
                font_size=8,
                pos=(x + 35, 220),
                anchor_x="center",
                anchor_y="center",
            )
            self.palette_chips.append({"rect": rect, "text": text, "color": color, "region": (x, 207, x + 70, 231)})

        self.controls = scene.visuals.Text(
            "Space pause   C camera   S capture   F full   H hide   Esc quit",
            parent=self.scene,
            color=(0.56, 0.64, 0.74, 0.84),
            font_size=8,
            pos=(44, 254),
            anchor_x="left",
            anchor_y="top",
        )
        self._layout_hud()
        self._set_hud_visibility()
        self._update_hud()

    def _make_slider(self, *, label: str, y: float) -> dict[str, Any]:
        label_text = scene.visuals.Text(
            label,
            parent=self.scene,
            color=(0.58, 0.68, 0.80, 0.88),
            font_size=8,
            pos=(44, y - 9),
            anchor_x="left",
            anchor_y="top",
        )
        value_text = scene.visuals.Text(
            "",
            parent=self.scene,
            color=(0.91, 0.96, 1.0, 0.96),
            font_size=9,
            pos=(392, y - 9),
            anchor_x="right",
            anchor_y="top",
        )
        track = scene.visuals.Line(
            pos=np.array([[112, y], [362, y]], dtype=np.float32),
            color=(0.22, 0.28, 0.38, 0.96),
            width=5,
            parent=self.scene,
        )
        fill = scene.visuals.Line(
            pos=np.array([[112, y], [112, y]], dtype=np.float32),
            color=(0.28, 0.82, 0.82, 0.96),
            width=5,
            parent=self.scene,
        )
        knob = scene.visuals.Rectangle(
            center=(112, y),
            width=17,
            height=17,
            radius=8,
            color=(0.86, 0.96, 1.0, 0.96),
            border_color=(0.18, 0.78, 0.76, 1.0),
            border_width=1,
            parent=self.scene,
        )
        return {
            "label": label_text,
            "value": value_text,
            "track": track,
            "fill": fill,
            "knob": knob,
            "y": y,
            "region": (104, y - 13, 370, y + 13),
        }

    def _layout_hud(self) -> None:
        left = 28.0
        top = 46.0
        width = 448.0
        height = 230.0
        self.control_panel.center = (left + width * 0.5, top + height * 0.5)
        self.control_panel.width = width
        self.control_panel.height = height

        self.hud.pos = (left + 16, top + 16)
        self.status.pos = (left + 16, top + 39)

        slider_specs = {
            "bpm": top + 76,
            "tempo": top + 110,
            "rings": top + 144,
        }
        for name, y in slider_specs.items():
            slider = self.sliders[name]
            slider["label"].pos = (left + 16, y - 9)
            slider["value"].pos = (left + width - 56, y - 9)
            slider["track_x0"] = left + 84
            slider["track_x1"] = left + width - 86
            slider["y"] = y
            slider["region"] = (slider["track_x0"] - 10, y - 14, slider["track_x1"] + 10, y + 14)
            slider["track"].set_data(
                pos=np.array([[slider["track_x0"], y], [slider["track_x1"], y]], dtype=np.float32),
                color=(0.22, 0.28, 0.38, 0.96),
                width=5,
            )

        self._control_regions = []
        for name, slider in self.sliders.items():
            self._control_regions.append((f"slider:{name}", slider["region"]))

        chip_y = top + 180
        for i, chip in enumerate(self.palette_chips):
            x = left + 16 + i * 88
            chip["rect"].center = (x + 35, chip_y)
            chip["text"].pos = (x + 35, chip_y + 1)
            chip["region"] = (x, chip_y - 12, x + 70, chip_y + 12)
            self._control_regions.append((f"palette:{i}", chip["region"]))

        self.controls.pos = (left + 16, top + height - 24)

    def _set_hud_visibility(self) -> None:
        visuals: list[Any] = [self.control_panel, self.hud, self.status, self.controls]
        for slider in getattr(self, "sliders", {}).values():
            visuals.extend([slider["label"], slider["value"], slider["track"], slider["fill"], slider["knob"]])
        for chip in getattr(self, "palette_chips", []):
            visuals.extend([chip["rect"], chip["text"]])

        for visual in visuals:
            visual.visible = self.hud_visible

    def _current_palette(self) -> Palette:
        return PALETTES[self.palette_index % len(PALETTES)]

    def _apply_palette(self, index: int) -> None:
        self.palette_index = index % len(PALETTES)
        self._update_hud()

    def _slider_fraction(self, name: str) -> float:
        lo, hi = CONTROL_RANGES[name]
        if name == "bpm":
            value = self.bpm
        elif name == "tempo":
            value = self.time_scale
        elif name == "rings":
            value = float(len(self.rings))
        else:
            value = lo
        return clamp((value - lo) / (hi - lo), 0.0, 1.0)

    def _format_slider_value(self, name: str) -> str:
        if name == "bpm":
            return f"{self.bpm:.0f}"
        if name == "tempo":
            return f"{self.time_scale:.2f}x"
        if name == "rings":
            return str(len(self.rings))
        return ""

    def _set_ring_count(self, count: int) -> None:
        count = clamp_ring_count(count)
        if count == len(self.rings):
            return

        for state in self.ring_state:
            for key in ("glow", "core"):
                state[key].parent = None  # type: ignore[index]
        self._build_rings(count)

    def _set_slider_from_x(self, name: str, x: float) -> None:
        slider = self.sliders[name]
        x0 = float(slider["track_x0"])
        x1 = float(slider["track_x1"])
        t = clamp((float(x) - x0) / (x1 - x0), 0.0, 1.0)
        lo, hi = CONTROL_RANGES[name]
        value = lo + t * (hi - lo)

        if name == "bpm":
            self.bpm = round(value)
        elif name == "tempo":
            self.time_scale = round(value / 0.05) * 0.05
        elif name == "rings":
            self._set_ring_count(round(value))

        self._update_hud()
        self._refresh_window_title(force=True)

    def _hit_control(self, pos: tuple[float, float]) -> str | None:
        x, y = pos
        for name, (x0, y0, x1, y1) in self._control_regions:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return name
        return None

    def _handle_control_pointer(self, pos: tuple[float, float]) -> None:
        control = self._active_control or self._hit_control(pos)
        if not control:
            return

        kind, value = control.split(":", 1)
        if kind == "slider":
            self._set_slider_from_x(value, pos[0])
        elif kind == "palette":
            self._apply_palette(int(value))
            self._refresh_window_title(force=True)

    def _update_hud(self) -> None:
        if not hasattr(self, "hud"):
            return

        pal = self._current_palette()
        pause_state = "PAUSED" if self.paused else "LIVE"
        cam_state = "auto" if self.auto_camera else "manual"
        capture = f"  |  saved {self._last_capture_path.name}" if self._last_capture_path else ""
        self.hud.text = "GyroDynamo"
        self.status.text = f"{pause_state}  |  {pal.name}  |  camera {cam_state}{capture}"

        for name, slider in self.sliders.items():
            t = self._slider_fraction(name)
            x0 = float(slider["track_x0"])
            x1 = float(slider["track_x1"])
            y = float(slider["y"])
            knob_x = x0 + t * (x1 - x0)
            slider["value"].text = self._format_slider_value(name)
            slider["fill"].set_data(
                pos=np.array([[x0, y], [knob_x, y]], dtype=np.float32),
                color=(0.28, 0.82, 0.82, 0.96),
                width=5,
            )
            slider["knob"].center = (knob_x, y)

        for i, chip in enumerate(self.palette_chips):
            selected = i == self.palette_index
            chip["rect"].color = (chip["color"][0], chip["color"][1], chip["color"][2], 0.34 if selected else 0.12)
            chip["rect"].border_color = chip["color"] if selected else (0.38, 0.46, 0.58, 0.62)

        self._set_hud_visibility()

    def _refresh_window_title(self, force: bool = False) -> None:
        now = self.elapsed
        if not force and now - self._last_title_t < 0.33:
            return
        self._last_title_t = now
        pause_state = "Paused" if self.paused else "Running"
        pal = self._current_palette().name
        self.title = f"GyroDynamo Desktop | {pause_state} | {self.bpm:.1f} BPM | {pal}"

    def _bar_omega(self) -> float:
        bar_rate = (self.bpm / 60.0) / self.beats_per_measure
        return TAU * bar_rate

    def _align_omega(self) -> float:
        return self._bar_omega() / float(self.align_bars)

    def _update_camera(self) -> None:
        if not self.auto_camera:
            return
        self.view.camera.azimuth = self._base_cam_azimuth + 18.0 * math.sin(self.elapsed * 0.11)
        self.view.camera.elevation = self._base_cam_elevation + 7.0 * math.sin(self.elapsed * 0.09)
        self.view.camera.distance = self._base_cam_distance + 0.35 * math.sin(self.elapsed * 0.07)

    def _animate_core(self, beat_pulse: float, measure_pulse: float) -> None:
        inner_scale = 1.0 + 0.10 * beat_pulse + 0.14 * measure_pulse
        outer_scale = 1.0 + 0.17 * beat_pulse + 0.20 * measure_pulse

        self.core_inner.transform = scene.transforms.MatrixTransform()
        self.core_inner.transform.scale((inner_scale, inner_scale, inner_scale))
        self.core_inner.transform.rotate(self.elapsed * 18.0, (0, 0, 1))

        self.core_outer.transform = scene.transforms.MatrixTransform()
        self.core_outer.transform.scale((outer_scale, outer_scale, outer_scale))
        self.core_outer.transform.rotate(-self.elapsed * 12.0, (0, 0, 1))

    def _ring_colors(
        self,
        theta: np.ndarray,
        z: np.ndarray,
        ring_index: int,
        beat_pulse: float,
        measure_pulse: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        pal = self._current_palette()
        count = len(self.rings)
        t_ring = ring_index / max(1, count - 1)
        hue_base = (pal.hue_start + pal.hue_span * t_ring) % 1.0

        hue = (
            hue_base
            + 0.025 * np.sin(theta * (2.0 + t_ring * 2.4) + self.elapsed * 0.22)
            + 0.008 * np.sin(self.elapsed * 0.9 + ring_index * 0.7)
        ) % 1.0

        stripe = 0.5 + 0.5 * np.sin(theta * (2.5 + t_ring * 4.0) + self.elapsed * (0.35 + t_ring * 0.15))
        depth = clamp(0.5 + 0.5 * float(np.mean(z) / (1.5 + t_ring)), 0.0, 1.0)

        sat = np.clip(pal.saturation + 0.12 * (stripe - 0.5), 0.45, 1.0).astype(np.float32)
        val = pal.value * (0.56 + 0.44 * stripe)
        val = val * (0.85 + 0.25 * depth)
        val = val * (1.0 + 0.25 * beat_pulse + 0.40 * measure_pulse)
        val = np.clip(val, 0.0, 1.0).astype(np.float32)

        rgb = hsv_to_rgb_np(hue.astype(np.float32), sat.astype(np.float32), val)

        core_alpha = np.full((theta.shape[0], 1), 0.80 + 0.16 * beat_pulse, dtype=np.float32)
        glow_alpha = np.full((theta.shape[0], 1), 0.10 + 0.12 * beat_pulse + 0.16 * measure_pulse, dtype=np.float32)

        core = np.concatenate((rgb, core_alpha), axis=1)
        glow = np.concatenate((np.clip(rgb * 1.15, 0.0, 1.0), glow_alpha), axis=1)
        return (core, glow)

    def _update_rings(self) -> None:
        spin_phase = self._bar_omega() * self.elapsed
        tumble_phase = self._align_omega() * self.elapsed

        beat_phase = (self.elapsed * self.bpm / 60.0) % 1.0
        measure_phase = (self.elapsed * self.bpm / (60.0 * self.beats_per_measure)) % 1.0
        beat_pulse = math.exp(-16.0 * beat_phase)
        measure_pulse = math.exp(-24.0 * measure_phase)

        for i, ring in enumerate(self.rings):
            state = self.ring_state[i]
            theta = state["theta"]  # type: ignore[assignment]
            base = state["base"]  # type: ignore[assignment]
            core = state["core"]  # type: ignore[assignment]
            glow = state["glow"]  # type: ignore[assignment]

            spin = ring.spin_ratio * spin_phase + ring.phase
            tx = ring.tx_ratio * tumble_phase * 0.27
            ty = ring.ty_ratio * tumble_phase * 0.27

            breathe = 1.0 + 0.028 * math.sin(self.elapsed * 0.7 + ring.phase * 1.9)
            axis_wobble = ring.axis_tilt + 0.08 * math.sin(self.elapsed * 0.19 + i)
            rot = rot_z(axis_wobble) @ rot_y(ty) @ rot_x(tx) @ rot_z(spin)
            pos = (base @ rot.T) * breathe

            core_color, glow_color = self._ring_colors(
                theta,
                pos[:, 2],
                i,
                beat_pulse=beat_pulse,
                measure_pulse=measure_pulse,
            )

            core_obj: scene.visuals.Line = core  # type: ignore[assignment]
            glow_obj: scene.visuals.Line = glow  # type: ignore[assignment]
            core_obj.set_data(pos=pos, color=core_color, width=ring.width + 0.5 * beat_pulse)
            glow_obj.set_data(pos=pos, color=glow_color, width=ring.glow_width + 1.4 * beat_pulse + 1.8 * measure_pulse)

        self._animate_core(beat_pulse=beat_pulse, measure_pulse=measure_pulse)

    def capture_screenshot(self) -> Path:
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        path = self.screenshot_dir / f"gyrodynamo_{datetime.now().strftime('%Y%m%d-%H%M%S')}.bmp"
        write_bmp(path, self.render())
        self._last_capture_path = path
        self._update_hud()
        return path

    def advance_smoke_frames(self, frames: int) -> None:
        for _ in range(max(1, frames)):
            self.elapsed += 1.0 / 60.0
            self._update_camera()
            self._update_rings()
            self._update_hud()
            self._refresh_window_title(force=True)
            self.update()

    def on_key_press(self, event) -> None:
        key = str(event.key).lower()
        if key == "space":
            self.paused = not self.paused
        elif key == "up":
            self.bpm = clamp(self.bpm + 2.0, 30.0, 220.0)
        elif key == "down":
            self.bpm = clamp(self.bpm - 2.0, 30.0, 220.0)
        elif key == "left":
            self.time_scale = clamp(self.time_scale - 0.05, 0.25, 3.0)
        elif key == "right":
            self.time_scale = clamp(self.time_scale + 0.05, 0.25, 3.0)
        elif key == "c":
            self.auto_camera = not self.auto_camera
        elif key == "r":
            self._apply_palette(self.palette_index + 1)
        elif key == "h":
            self.hud_visible = not self.hud_visible
            self._set_hud_visibility()
        elif key in {"+", "="}:
            self._set_ring_count(len(self.rings) + 1)
        elif key in {"-", "_"}:
            self._set_ring_count(len(self.rings) - 1)
        elif key == "s":
            self.capture_screenshot()
        elif key == "f":
            self.fullscreen = not bool(self.fullscreen)
        elif key in {"escape", "q"}:
            self.close()
            return
        self._update_hud()
        self._refresh_window_title(force=True)

    def on_mouse_press(self, event) -> None:
        if not self.hud_visible:
            return
        control = self._hit_control(tuple(event.pos))
        if control:
            self._active_control = control
            self._handle_control_pointer(tuple(event.pos))

    def on_mouse_move(self, event) -> None:
        if not self.hud_visible or not self._active_control:
            return
        self._handle_control_pointer(tuple(event.pos))

    def on_mouse_release(self, _event) -> None:
        self._active_control = None

    def on_resize(self, event) -> None:
        super().on_resize(event)
        if hasattr(self, "hud"):
            self._layout_hud()
            self._update_hud()

    def on_timer(self, _event) -> None:
        now = time.perf_counter()
        dt = now - self._last_t
        self._last_t = now
        dt = clamp(dt, 0.0005, 0.05)

        if not self.paused:
            self.elapsed += dt * self.time_scale

        self._update_camera()
        self._update_rings()
        self._update_hud()
        self._refresh_window_title()
        self.update()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="GyroDynamo standalone desktop renderer")
    p.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to desktop JSON config.")
    p.add_argument("--size", default=None, help="Window size as WIDTHxHEIGHT.")
    p.add_argument("--bpm", type=float, default=None, help="Target BPM.")
    p.add_argument("--rings", type=int, default=None, help="Ring count between 3 and 10.")
    p.add_argument("--palette", default=None, help="Palette name or zero-based palette index.")
    p.add_argument("--fullscreen", action="store_true", help="Start in fullscreen mode.")
    p.add_argument("--no-hud", action="store_true", help="Hide the on-canvas HUD at startup.")
    p.add_argument("--no-camera-drift", action="store_true", help="Disable automatic camera drift at startup.")
    p.add_argument("--screenshot-dir", default=None, help="Directory for screenshots captured with S.")
    p.add_argument("--backend", default=None, help="VisPy backend name, e.g. glfw.")
    p.add_argument("--smoke-test", action="store_true", help="Initialize, advance frames, and exit.")
    p.add_argument("--smoke-frames", type=int, default=3, help="Frame count for --smoke-test.")
    p.add_argument("--smoke-screenshot", action="store_true", help="Write one screenshot during --smoke-test.")
    return p.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = resolve_desktop_config(args)

    canvas = GyroDynamoVisPy(config=config)
    if config.fullscreen:
        canvas.fullscreen = True

    if args.smoke_test:
        canvas.advance_smoke_frames(args.smoke_frames)
        if args.smoke_screenshot:
            path = canvas.capture_screenshot()
            print(f"[GyroDynamo] Smoke screenshot: {path}")
        canvas.close()
        return 0

    canvas.show()
    app.run()
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
