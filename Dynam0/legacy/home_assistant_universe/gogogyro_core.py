"""
GoGoGyro core primitives (desktop / pygame).

This file is intentionally extracted from the existing
`GoGoGyroDesktopAligned*.py` scripts so multiple "gyros" (planets) can be
rendered in one scene while preserving the original look (core glow, ring
shading, sweep/specular effects).
"""

from __future__ import annotations

import colorsys
import math
import random
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

import pygame

Vec3 = Tuple[float, float, float]


def rot_x(p: Vec3, a: float) -> Vec3:
    x, y, z = p
    ca, sa = math.cos(a), math.sin(a)
    return (x, y * ca - z * sa, y * sa + z * ca)


def rot_y(p: Vec3, a: float) -> Vec3:
    x, y, z = p
    ca, sa = math.cos(a), math.sin(a)
    return (x * ca + z * sa, y, -x * sa + z * ca)


def rot_z(p: Vec3, a: float) -> Vec3:
    x, y, z = p
    ca, sa = math.cos(a), math.sin(a)
    return (x * ca - y * sa, x * sa + y * ca, z)


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _normalize(vec: Vec3) -> Vec3:
    x, y, z = vec
    mag = math.sqrt(x * x + y * y + z * z)
    if mag < 1e-6:
        return (0.0, 0.0, 1.0)
    return (x / mag, y / mag, z / mag)


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


class Ring:
    """
    A single glowing ring made of N short line segments in 3D, projected to 2D.

    Note: This is compatible with the existing aligned scripts but adds optional
    deterministic RNG injection (`rng`) for stable per-planet variety.
    """

    def __init__(
        self,
        radius: float,
        color: Tuple[float, float, float],
        n_points: int,
        spin_ratio: float,
        tx_ratio: float,
        ty_ratio: float,
        *,
        band_count: int = 3,
        axis_angle: float = 0.0,
        thickness_scale: float = 1.0,
        rng: Optional[random.Random] = None,
    ) -> None:
        rng = rng if rng is not None else random

        self.R = float(radius)
        self.color = tuple(float(c) for c in color)
        self.n = int(n_points)
        self.spin_ratio = float(spin_ratio)
        self.tx_ratio = float(tx_ratio)
        self.ty_ratio = float(ty_ratio)
        self.axis_angle = float(axis_angle)
        self.thickness_scale = max(0.5, float(thickness_scale))

        self.spin = 0.0
        self.tilt_x = 0.0
        self.tilt_y = 0.0
        self.offset: Vec3 = (0.0, 0.0, 0.0)

        h, s, v = colorsys.rgb_to_hsv(*self.color)
        self.hue = float(h)
        self.saturation = float(s)
        self.value = float(v)

        self.band_count = max(2, int(band_count))
        self.band_phase = rng.randrange(max(1, self.n))
        self.band_colors: list[Tuple[float, float, float]] = []

        self.glyph_stride = rng.choice([9, 11, 13])
        self.glyph_phase = rng.randrange(max(1, self.glyph_stride))

        # Precompute circle points so we don't evaluate cos/sin per-vertex per-frame.
        two_pi = 2.0 * math.pi
        denom = max(1, self.n)
        self._unit_circle = [
            (math.cos(two_pi * i / denom), math.sin(two_pi * i / denom)) for i in range(self.n)
        ]

        self.refresh_band_colors()

    def refresh_band_colors(self) -> None:
        self.band_colors = []
        band_count = max(2, int(self.band_count))
        for band in range(band_count):
            band_pos = (band / (band_count - 1)) - 0.5
            hue = (self.hue + band_pos * 0.05) % 1.0
            sat = clamp01(self.saturation * (1.0 - abs(band_pos) * 0.12))
            val = clamp01(self.value * (1.0 + band_pos * 0.25))
            self.band_colors.append(colorsys.hsv_to_rgb(hue, sat, val))

    def segment_color(self, idx: int) -> Tuple[float, float, float]:
        if not self.band_colors:
            self.refresh_band_colors()
        n = max(1, self.n)
        offset_idx = (int(idx) + int(self.band_phase)) % n
        band = int((offset_idx / n) * self.band_count)
        if band >= self.band_count:
            band = self.band_count - 1
        return self.band_colors[band]

    def update(self, spin_phase: float, tumble_phase: float) -> None:
        self.spin = self.spin_ratio * float(spin_phase)
        self.tilt_x = self.tx_ratio * float(tumble_phase)
        self.tilt_y = self.ty_ratio * float(tumble_phase)

    def ring_points_3d(self) -> list[Vec3]:
        # Hot loop: avoid trig per-point by precomputing sin/cos per-ring.
        ox, oy, oz = self.offset

        cs, ss = math.cos(self.spin), math.sin(self.spin)
        ctx, stx = math.cos(self.tilt_x), math.sin(self.tilt_x)
        cty, sty = math.cos(self.tilt_y), math.sin(self.tilt_y)

        use_axis = abs(self.axis_angle) > 1e-6
        if use_axis:
            ca, sa = math.cos(self.axis_angle), math.sin(self.axis_angle)

        pts: list[Vec3] = []
        for ucx, ucy in self._unit_circle:
            x = self.R * ucx
            y = self.R * ucy
            z = 0.0

            # Rz(spin)
            x, y = (x * cs - y * ss), (x * ss + y * cs)

            # Optional axis pre-rotate
            if use_axis:
                x, y = (x * ca - y * sa), (x * sa + y * ca)

            # Rx(tilt_x)
            y, z = (y * ctx - z * stx), (y * stx + z * ctx)

            # Ry(tilt_y)
            x, z = (x * cty + z * sty), (-x * sty + z * cty)

            # Optional axis un-rotate (Rz(-axis))
            if use_axis:
                x, y = (x * ca + y * sa), (-x * sa + y * ca)

            pts.append((x + ox, y + oy, z + oz))

        return pts


@dataclass
class GyroRenderTuning:
    # Thickness tuning for performance scaling.
    base_thickness_mult: float = 1.0
    glow_thickness_mult: float = 1.0


class GyroRenderer:
    """
    Draw helper that preserves the "Aligned" renderer look, but can render many rings/cores.

    The caller owns the animation clock; pass `elapsed_s` into draw calls.
    """

    def __init__(self, width: int, height: int) -> None:
        self.width = int(width)
        self.height = int(height)
        self.cx = self.width * 0.5
        self.cy = self.height * 0.5

        self.cam_dist = 3.8
        self.focal_len = 1.0
        self.light_dir = _normalize((0.2, 0.35, 1.0))

        self.base_thickness = 8.0
        self.back_alpha = 0.35
        self.front_alpha = 0.98
        self.glow_alpha = 0.22
        self.core_spin_rate = 0.9
        self.sweep_speed = 0.09
        self.sweep_strength = 0.45
        self.sweep_tint = (0.3, 0.9, 1.0)
        self.specular_strength = 0.4
        self.specular_width = 0.05

        self.bg_top = (6, 8, 16)
        self.bg_bottom = (10, 14, 26)
        self.core_color = (0.98, 0.99, 1.0)
        self.core_glow_color = (0.62, 0.8, 1.0)

        self.scale_px = 1.0
        self.bg_surface: Optional[pygame.Surface] = None
        self._core_sphere_cache: dict[int, pygame.Surface] = {}
        self.tuning = GyroRenderTuning()
        self.rebuild_background()

    def set_scale_for_ring_radius_px(self, *, outer_radius_world: float, ring_radius_px: float) -> None:
        outer_radius_world = max(1e-6, float(outer_radius_world))
        ring_radius_px = max(1.0, float(ring_radius_px))
        self.scale_px = ring_radius_px * self.cam_dist / outer_radius_world

    def rebuild_background(self) -> None:
        grad_col = pygame.Surface((1, self.height))
        for y in range(self.height):
            t = y / max(1, self.height - 1)
            r = int(self.bg_top[0] * (1 - t) + self.bg_bottom[0] * t)
            g = int(self.bg_top[1] * (1 - t) + self.bg_bottom[1] * t)
            b = int(self.bg_top[2] * (1 - t) + self.bg_bottom[2] * t)
            grad_col.set_at((0, y), (r, g, b))
        self.bg_surface = pygame.transform.smoothscale(grad_col, (self.width, self.height))

    def resize(self, width: int, height: int) -> None:
        self.width = max(320, int(width))
        self.height = max(320, int(height))
        self.cx = self.width * 0.5
        self.cy = self.height * 0.5
        self.rebuild_background()

    def project(self, p: Vec3) -> Tuple[float, float]:
        x, y, z = p
        denom = float(z) + self.cam_dist
        if denom < 0.1:
            denom = 0.1
        u = (self.focal_len * float(x)) / denom
        v = (self.focal_len * float(y)) / denom
        return (self.cx + u * self.scale_px, self.cy + v * self.scale_px)

    @staticmethod
    def _offset_line(x0: float, y0: float, x1: float, y1: float, offset: float):
        dx = x1 - x0
        dy = y1 - y0
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return None
        nx = -dy / length
        ny = dx / length
        return (x0 + nx * offset, y0 + ny * offset, x1 + nx * offset, y1 + ny * offset)

    def draw_ring(
        self,
        surface: pygame.Surface,
        glow_surface: pygame.Surface,
        ring: Ring,
        *,
        elapsed_s: float,
        thickness_scale: float = 1.0,
        alpha_boost: float = 0.0,
        glow_scale: float = 1.0,
    ) -> None:
        pts3d = ring.ring_points_3d()
        segments = []
        for i in range(ring.n):
            p0 = pts3d[i]
            p1 = pts3d[(i + 1) % ring.n]
            z_avg = 0.5 * (p0[2] + p1[2])
            mid = ((p0[0] + p1[0]) * 0.5, (p0[1] + p1[1]) * 0.5, z_avg)
            x0, y0 = self.project(p0)
            x1, y1 = self.project(p1)
            segments.append((z_avg, mid, i, x0, y0, x1, y1))
        segments.sort(key=lambda s: s[0])

        ring_thickness = float(thickness_scale) * ring.thickness_scale * self.tuning.base_thickness_mult
        base_thickness = max(1.0, self.base_thickness * ring_thickness)
        thickness_px = max(1, int(base_thickness))
        glow_thickness_px = max(1, int(thickness_px * 3.0 * self.tuning.glow_thickness_mult))

        clamp255 = lambda v: max(0, min(255, int(v)))
        n = max(1, ring.n)
        two_pi = 2.0 * math.pi
        sweep_time = float(elapsed_s) * self.sweep_speed
        phase_offset = ring.band_phase / n
        specular_center = (ring.spin / two_pi + phase_offset) % 1.0

        ox, oy, oz = ring.offset
        for _, mid, idx, x0, y0, x1, y1 in segments:
            depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, mid[2]))

            # Important for multi-planet: light should be local to the ring, not biased by world translation.
            local_mid = (mid[0] - ox, mid[1] - oy, mid[2] - oz)
            light = max(0.0, _dot(_normalize(local_mid), self.light_dir))

            shade = 0.7 + 0.2 * depth_mix + 0.25 * light
            alpha = self.back_alpha + (self.front_alpha - self.back_alpha) * depth_mix + float(alpha_boost)
            alpha = max(0.0, min(1.0, alpha))

            seg_color = ring.segment_color(idx)
            pos = idx / n
            sweep_phase = (pos + sweep_time + phase_offset) % 1.0
            sweep = 0.5 + 0.5 * math.sin(two_pi * sweep_phase)
            sweep = sweep**1.6
            sweep_mix = self.sweep_strength * sweep
            if sweep_mix > 0.0:
                seg_color = (
                    seg_color[0] * (1.0 - sweep_mix) + self.sweep_tint[0] * sweep_mix,
                    seg_color[1] * (1.0 - sweep_mix) + self.sweep_tint[1] * sweep_mix,
                    seg_color[2] * (1.0 - sweep_mix) + self.sweep_tint[2] * sweep_mix,
                )

            specular_dist = abs(pos - specular_center)
            if specular_dist > 0.5:
                specular_dist = 1.0 - specular_dist
            specular = max(0.0, 1.0 - specular_dist / max(1e-6, self.specular_width))
            specular = (specular**4.0) * self.specular_strength * (0.65 + 0.35 * light)
            if specular > 0.0:
                highlight_mix = min(1.0, specular * 0.45)
                seg_color = (
                    seg_color[0] * (1.0 - highlight_mix) + highlight_mix,
                    seg_color[1] * (1.0 - highlight_mix) + highlight_mix,
                    seg_color[2] * (1.0 - highlight_mix) + highlight_mix,
                )
            shade = min(1.5, shade + specular * 0.7)
            alpha = min(1.0, alpha + specular * 0.2)

            rgba = (
                clamp255(seg_color[0] * shade * 255),
                clamp255(seg_color[1] * shade * 255),
                clamp255(seg_color[2] * shade * 255),
                int(alpha * 255),
            )
            glow_a = min(
                1.0, self.glow_alpha * (0.8 + 0.6 * depth_mix) * float(glow_scale) + specular * 0.12
            )
            glow_color = (
                clamp255(seg_color[0] * shade * 255),
                clamp255(seg_color[1] * shade * 255),
                clamp255(seg_color[2] * shade * 255),
                int(glow_a * 255),
            )

            pygame.draw.line(glow_surface, glow_color, (x0, y0), (x1, y1), glow_thickness_px)
            pygame.draw.line(surface, rgba, (x0, y0), (x1, y1), thickness_px)

            tube_offset = max(0.6, thickness_px * 0.45)
            edge_line = self._offset_line(x0, y0, x1, y1, -tube_offset)
            highlight_line = self._offset_line(x0, y0, x1, y1, tube_offset)
            edge_shade = shade * 0.65
            edge_alpha = alpha * 0.7
            edge_color = (
                clamp255(seg_color[0] * edge_shade * 255),
                clamp255(seg_color[1] * edge_shade * 255),
                clamp255(seg_color[2] * edge_shade * 255),
                int(edge_alpha * 255),
            )
            highlight_mix = 0.35 + 0.45 * light
            highlight_shade = shade * 0.85
            highlight_color = (
                clamp255((seg_color[0] * (1.0 - highlight_mix) + highlight_mix) * highlight_shade * 255),
                clamp255((seg_color[1] * (1.0 - highlight_mix) + highlight_mix) * highlight_shade * 255),
                clamp255((seg_color[2] * (1.0 - highlight_mix) + highlight_mix) * highlight_shade * 255),
                int(min(1.0, alpha * (0.6 + 0.4 * light) + 0.05) * 255),
            )
            if edge_line:
                pygame.draw.line(
                    surface,
                    edge_color,
                    (edge_line[0], edge_line[1]),
                    (edge_line[2], edge_line[3]),
                    max(1, int(thickness_px * 0.55)),
                )
            if highlight_line:
                pygame.draw.line(
                    surface,
                    highlight_color,
                    (highlight_line[0], highlight_line[1]),
                    (highlight_line[2], highlight_line[3]),
                    max(1, int(thickness_px * 0.5)),
                )

        glyph_thickness = max(1, int(thickness_px * 0.7))
        for _, mid, idx, x0, y0, x1, y1 in segments:
            if (idx + ring.glyph_phase) % ring.glyph_stride != 0:
                continue
            depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, mid[2]))
            if depth_mix < 0.35:
                continue

            local_mid = (mid[0] - ox, mid[1] - oy, mid[2] - oz)
            light = max(0.0, _dot(_normalize(local_mid), self.light_dir))

            shade = 0.9 + 0.2 * depth_mix + 0.2 * light
            alpha = min(1.0, self.front_alpha + float(alpha_boost) + 0.2)
            seg_color = ring.segment_color(idx)
            glyph_color = (
                clamp255(seg_color[0] * shade * 255 + 15),
                clamp255(seg_color[1] * shade * 255 + 15),
                clamp255(seg_color[2] * shade * 255 + 15),
                int(alpha * 255),
            )
            pygame.draw.line(surface, glyph_color, (x0, y0), (x1, y1), glyph_thickness)

    def _core_sphere_surface(self, radius_px: int, *, core_color_rgb: Tuple[float, float, float]) -> pygame.Surface:
        radius_px = int(radius_px)
        cached = self._core_sphere_cache.get(radius_px)
        if cached is not None:
            return cached

        sphere = pygame.Surface((radius_px * 2, radius_px * 2), pygame.SRCALPHA)
        center = (radius_px, radius_px)
        layers = 5
        tint_rgb = tuple(int(clamp01(c) * 255) for c in core_color_rgb)
        for i in range(layers):
            t = i / float(layers - 1)
            alpha = int(245 * (1.0 - t) ** 1.5)
            radius = max(1, int(radius_px * (1.0 - 0.09 * i)))
            pygame.draw.circle(sphere, tint_rgb + (alpha,), center, radius)

        self._core_sphere_cache[radius_px] = sphere
        return sphere

    def draw_core(
        self,
        surface: pygame.Surface,
        glow_surface: pygame.Surface,
        *,
        center_world: Vec3,
        rings: Sequence[Ring],
        elapsed_s: float,
        core_color: Optional[Tuple[float, float, float]] = None,
        glow_color: Optional[Tuple[float, float, float]] = None,
    ) -> int:
        min_dim = min(self.width, self.height)
        radius_px = int(min_dim * 0.07)

        sx, sy = self.project(center_world)
        if rings:
            inner = rings[-1]
            px, _ = self.project((center_world[0] + inner.R, center_world[1], center_world[2]))
            inner_px = abs(px - sx)
            radius_px = min(radius_px, max(12, int(inner_px * 0.55)))

        radius_px = max(10, min(radius_px, int(min_dim * 0.18)))

        core_color_rgb = core_color if core_color is not None else self.core_color
        sphere = self._core_sphere_surface(radius_px, core_color_rgb=core_color_rgb)
        surface.blit(sphere, (sx - radius_px, sy - radius_px))

        spin_angle = float(elapsed_s) * self.core_spin_rate
        highlight_col = (255, 255, 255, 150)
        highlight_radius = int(radius_px * 0.32)
        orbit_gap = max(2.0, radius_px * 0.02)
        orbit_radius = radius_px + highlight_radius + orbit_gap
        pygame.draw.circle(
            surface,
            highlight_col,
            (
                int(sx + math.cos(spin_angle) * orbit_radius),
                int(sy + math.sin(spin_angle) * orbit_radius),
            ),
            highlight_radius,
        )

        glow_rgb = tuple(
            int(clamp01(c) * 255) for c in (glow_color if glow_color is not None else self.core_glow_color)
        )
        for scale, alpha in ((1.6, 160), (2.2, 90), (2.9, 50)):
            pygame.draw.circle(glow_surface, glow_rgb + (alpha,), (int(sx), int(sy)), int(radius_px * scale))

        return radius_px


# Backwards compat for earlier internal name.
_clamp01 = clamp01
