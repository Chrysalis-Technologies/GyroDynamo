"""
GyroDynamo desktop visualizer (VisPy edition).

A polished, desktop-focused renderer with glowing gyroscopic rings, beat-linked
motion, and smooth camera drift.
"""

from __future__ import annotations

import argparse
import math
import time
from dataclasses import dataclass

import numpy as np
from vispy import app, scene

TAU = 2.0 * math.pi


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def parse_size(text: str) -> tuple[int, int]:
    parts = text.lower().split("x", 1)
    if len(parts) != 2:
        raise ValueError("size must be WIDTHxHEIGHT, e.g. 1600x1000")
    w = int(parts[0].strip())
    h = int(parts[1].strip())
    if w < 640 or h < 480:
        raise ValueError("size must be at least 640x480")
    return (w, h)


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


@dataclass
class Palette:
    name: str
    hue_start: float
    hue_span: float
    saturation: float
    value: float


@dataclass
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


PALETTES = [
    Palette("Solar Forge", 0.08, 0.55, 0.78, 0.95),
    Palette("Ion Aurora", 0.42, 0.36, 0.72, 0.96),
    Palette("Copper Flux", 0.02, 0.20, 0.84, 0.98),
    Palette("Arctic Neon", 0.52, 0.15, 0.56, 1.00),
]


def build_ring_configs(ring_count: int) -> list[RingConfig]:
    rings: list[RingConfig] = []
    count = max(3, min(10, ring_count))
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


class GyroDynamoVisPy(scene.SceneCanvas):
    def __init__(
        self,
        *,
        size: tuple[int, int],
        bpm: float = 84.0,
        ring_count: int = 7,
        beats_per_measure: int = 8,
        align_bars: int = 4,
        backend: str | None = None,
    ) -> None:
        if backend:
            try:
                app.use_app(backend)
            except Exception:
                pass

        super().__init__(
            keys="interactive",
            size=size,
            show=False,
            title="Gyro Dynamo VisPy",
            bgcolor="#05070f",
            vsync=True,
        )

        self.unfreeze()
        self.bpm = clamp(bpm, 30.0, 220.0)
        self.beats_per_measure = max(1, int(beats_per_measure))
        self.align_bars = max(1, int(align_bars))
        self.time_scale = 1.0
        self.elapsed = 0.0
        self.paused = False
        self.auto_camera = True
        self.palette_index = 0

        self._last_t = time.perf_counter()
        self._last_title_t = 0.0

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
        self._build_rings(ring_count)
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
        self.hud = scene.visuals.Text(
            "",
            parent=self.scene,
            color=(0.82, 0.88, 1.0, 0.92),
            font_size=11,
            pos=(16, 16),
            anchor_x="left",
            anchor_y="top",
        )
        self.controls = scene.visuals.Text(
            "SPACE pause  UP/DOWN BPM  LEFT/RIGHT tempo  C camera  R palette  F fullscreen  ESC quit",
            parent=self.scene,
            color=(0.60, 0.68, 0.80, 0.85),
            font_size=10,
            pos=(16, 34),
            anchor_x="left",
            anchor_y="top",
        )
        self._update_hud()

    def _current_palette(self) -> Palette:
        return PALETTES[self.palette_index % len(PALETTES)]

    def _apply_palette(self, index: int) -> None:
        self.palette_index = index % len(PALETTES)
        self._update_hud()

    def _update_hud(self) -> None:
        pal = self._current_palette()
        pause_state = "PAUSED" if self.paused else "LIVE"
        cam_state = "auto" if self.auto_camera else "manual"
        self.hud.text = (
            f"{pause_state}  |  {self.bpm:.1f} BPM  |  x{self.time_scale:.2f} tempo"
            f"  |  palette: {pal.name}  |  camera: {cam_state}"
        )

    def _refresh_window_title(self, force: bool = False) -> None:
        now = self.elapsed
        if not force and now - self._last_title_t < 0.33:
            return
        self._last_title_t = now
        pause_state = "Paused" if self.paused else "Running"
        self.title = f"Gyro Dynamo VisPy | {pause_state} | BPM {self.bpm:.1f}"

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
        elif key == "f":
            self.fullscreen = not bool(self.fullscreen)
        elif key == "escape":
            self.close()
            return
        self._update_hud()
        self._refresh_window_title(force=True)

    def on_resize(self, event) -> None:
        super().on_resize(event)
        if hasattr(self, "hud"):
            self.hud.pos = (16, 16)
        if hasattr(self, "controls"):
            self.controls.pos = (16, 34)

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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gyro Dynamo desktop renderer (VisPy)")
    p.add_argument("--bpm", type=float, default=84.0, help="Target BPM (default: 84)")
    p.add_argument("--rings", type=int, default=7, help="Ring count between 3 and 10")
    p.add_argument("--size", default="1600x1000", help="Window size as WIDTHxHEIGHT")
    p.add_argument("--backend", default="glfw", help="VisPy backend name (default: glfw)")
    p.add_argument("--fullscreen", action="store_true", help="Start in fullscreen mode")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    width, height = parse_size(args.size)

    canvas = GyroDynamoVisPy(
        size=(width, height),
        bpm=args.bpm,
        ring_count=args.rings,
        backend=args.backend,
    )
    if args.fullscreen:
        canvas.fullscreen = True
    canvas.show()
    app.run()


if __name__ == "__main__":
    main()


