import argparse
import math
import os
import random
import time
import zlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pygame

from gogogyro_core import GyroRenderer, Ring, Vec3, clamp01
from gyro_stream_server import LatestJpegFrames, LatestLayoutStore, MjpegHttpServer
from ha_client import HomeAssistantPoller, HomeAssistantREST, parse_intish
from universe_config import get_galaxy_cfg, list_galaxies, load_universe_config


def stable_u32(text: str) -> int:
    return zlib.crc32(text.encode("utf-8")) & 0xFFFFFFFF


def stable_phase(text: str) -> float:
    return (stable_u32(text) / 0xFFFFFFFF) * (2.0 * math.pi)


def mix_rgb(a: Tuple[float, float, float], b: Tuple[float, float, float], t: float) -> Tuple[float, float, float]:
    t = clamp01(t)
    return (a[0] * (1 - t) + b[0] * t, a[1] * (1 - t) + b[1] * t, a[2] * (1 - t) + b[2] * t)


def hsv_variant(
    base_rgb: Tuple[float, float, float],
    *,
    ring_idx: int,
    ring_count: int,
    rng: random.Random,
) -> Tuple[float, float, float]:
    import colorsys

    h, s, v = colorsys.rgb_to_hsv(*base_rgb)
    center = 0.0 if ring_count <= 1 else (ring_idx / (ring_count - 1)) - 0.5
    h = (h + center * 0.03 + rng.uniform(-0.012, 0.012)) % 1.0
    s = clamp01(s * (1.0 - abs(center) * 0.10) * (0.98 + rng.uniform(-0.03, 0.03)))
    v = clamp01(v * (1.0 - (ring_idx * 0.06)) * (0.99 + rng.uniform(-0.03, 0.03)))
    return colorsys.hsv_to_rgb(h, s, v)


def build_planet_rings(
    *,
    planet_id: str,
    loop_count: int,
    base_color: Tuple[float, float, float],
    world_pos: Vec3,
    max_rings: int,
    outer_radius: float,
    inner_radius: float,
    quality_scale: float,
) -> Tuple[List[Ring], int]:
    loop_count = max(0, int(loop_count))
    max_rings = max(0, int(max_rings))
    ring_count = min(loop_count, max_rings)
    overflow = max(0, loop_count - max_rings)

    if ring_count <= 0:
        return ([], overflow)

    if ring_count == 1:
        radii = [outer_radius]
    else:
        step = (outer_radius - inner_radius) / float(ring_count - 1)
        radii = [outer_radius - step * i for i in range(ring_count)]

    rings: List[Ring] = []
    for i, r in enumerate(radii):
        seed = stable_u32(f"{planet_id}:{i}")
        rng = random.Random(seed)

        # Preserve the aligned feel: integer-ish ratios, alternating direction.
        dir_sign = -1 if (i % 2) else 1
        spin_ratio = (5 + i * 2) * dir_sign
        tx_ratio = (3 + i) * dir_sign
        ty_ratio = 0.0

        axis_angle_deg = rng.uniform(-42.0, 42.0)
        band_count = 3 if i < 2 else 4

        # Ring thickness: slight taper inward, overflow boosts the outer ring.
        thickness_scale = max(0.7, 1.40 - 0.08 * i)
        if i == 0 and overflow > 0:
            thickness_scale *= 1.0 + min(1.4, math.log10(overflow + 1.0) * 0.70)

        # Points per ring: scale for perf; cap to keep dozens-of-loops usable.
        base_n = 235 - 12 * i
        n_points = int(base_n * float(quality_scale))
        n_points = max(120, min(240, n_points))

        color = hsv_variant(base_color, ring_idx=i, ring_count=ring_count, rng=rng)

        ring = Ring(
            r,
            color,
            n_points=n_points,
            spin_ratio=spin_ratio,
            tx_ratio=tx_ratio,
            ty_ratio=ty_ratio,
            band_count=band_count,
            axis_angle=math.radians(axis_angle_deg),
            thickness_scale=thickness_scale,
            rng=rng,
        )
        ring.offset = world_pos
        rings.append(ring)

    return (rings, overflow)


@dataclass
class PlanetNode:
    id: str
    name: str
    loops_entity: str
    base_color: Tuple[float, float, float]
    world_pos: Vec3
    phase_offset: float
    screen_xy01: Tuple[float, float] = (0.5, 0.5)
    loop_count: int = 0
    overflow: int = 0
    unknown: bool = False
    rings: List[Ring] = field(default_factory=list)


@dataclass
class GalaxyState:
    id: str
    title: str
    planets: List[PlanetNode]
    scale_px: float
    layout: Dict[str, Any]
    last_encoded_s: float = 0.0
    last_touch_s: float = 0.0


class TextCache:
    def __init__(self, font: pygame.font.Font) -> None:
        self._font = font
        self._cache: Dict[Tuple[str, Tuple[int, int, int], int], pygame.Surface] = {}

    def render(self, text: str, *, color: Tuple[int, int, int], alpha: int = 255) -> pygame.Surface:
        key = (text, color, int(alpha))
        surf = self._cache.get(key)
        if surf is not None:
            return surf
        s = self._font.render(text, True, color)
        if alpha != 255:
            s.set_alpha(int(alpha))
        self._cache[key] = s
        return s


class GyroUniverseApp:
    def __init__(self, cfg: Dict[str, Any], args: argparse.Namespace) -> None:
        self.cfg = cfg
        self.args = args

        pygame.init()
        w = int(cfg["render"]["window"].get("width", 1400))
        h = int(cfg["render"]["window"].get("height", 900))
        self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        pygame.display.set_caption("GoGoGyro Universe")
        self.clock = pygame.time.Clock()

        self.font_small = pygame.font.SysFont(None, 18)
        self.font_label = pygame.font.SysFont(None, 22)
        self.font_title = pygame.font.SysFont(None, 26)
        self.text_small = TextCache(self.font_small)
        self.text_label = TextCache(self.font_label)
        self.text_title = TextCache(self.font_title)

        self.renderer = GyroRenderer(w, h)
        self.layer = pygame.Surface((w, h), pygame.SRCALPHA)
        self.glow_layer = pygame.Surface((w, h), pygame.SRCALPHA)
        self.composite = pygame.Surface((w, h))

        self.paused = False
        self.elapsed_s = 0.0

        self._quality_tier = 0
        self._quality_scale = 1.0

        self._galaxy_ids = list_galaxies(cfg)
        self._active_galaxy_id: Optional[str] = None
        self._local_galaxy_override: Optional[str] = args.galaxy
        self._planets: List[PlanetNode] = []
        self._galaxies: Dict[str, GalaxyState] = {}

        self._ha_poller: Optional[HomeAssistantPoller] = None
        self._configure_ha()

        self._stream_frames: Optional[LatestJpegFrames] = None
        self._layout_store: Optional[LatestLayoutStore] = None
        self._stream_server: Optional[MjpegHttpServer] = None
        self._stream_rr_idx = 0
        self._configure_stream()

        # Initial build.
        self._rebuild_all_galaxies()
        self._ensure_active_galaxy(force=True)
        if self._stream_frames:
            self._prime_stream_frames()

    def _configure_ha(self) -> None:
        ha = self.cfg.get("ha") or {}
        url = str(ha.get("url") or "").strip()
        token_env = str(ha.get("token_env") or "HA_TOKEN").strip() or "HA_TOKEN"
        token = os.getenv(token_env, "").strip()
        timeout_s = float(ha.get("timeout_s") or 5.0)
        poll_interval_s = float(ha.get("poll_interval_s") or 1.5)

        rest = None
        if url and token:
            rest = HomeAssistantREST(url, token, timeout_s=timeout_s)

        poller = HomeAssistantPoller(rest, poll_interval_s=poll_interval_s)
        self._ha_poller = poller

        # Targets get set after we build galaxies.
        poller.set_targets(context_entity_id=str(ha.get("context_entity") or "").strip() or None, entity_ids=[])
        poller.start()

    def _set_poller_targets_union(self) -> None:
        poller = self._ha_poller
        if not poller:
            return

        ha = self.cfg.get("ha") or {}
        context_entity = str(ha.get("context_entity") or "").strip() or None

        entity_ids: List[str] = []
        for gs in self._galaxies.values():
            for p in gs.planets:
                if p.loops_entity:
                    entity_ids.append(p.loops_entity)

        # De-dupe while preserving order.
        seen = set()
        uniq: List[str] = []
        for eid in entity_ids:
            if eid in seen:
                continue
            seen.add(eid)
            uniq.append(eid)

        poller.set_targets(context_entity_id=context_entity, entity_ids=uniq)

    def _configure_stream(self) -> None:
        if not self.args.serve_mjpeg:
            return

        # Fail early with a clear message if Pillow isn't installed.
        try:
            import PIL.Image  # noqa: F401
        except Exception:
            raise SystemExit(
                "[GoGoGyroUniverse] MJPEG mode requires Pillow. Install in your venv:\n"
                "  .venv-win\\Scripts\\python.exe -m pip install pillow\n"
            )

        self._stream_frames = LatestJpegFrames()
        self._layout_store = LatestLayoutStore()
        self._stream_server = MjpegHttpServer(
            host=str(self.args.host),
            port=int(self.args.port),
            frame=self._stream_frames,
            layout_store=self._layout_store,
            galaxy_ids=self._galaxy_ids,
        )
        self._stream_server.start()

    def _bar_omega(self) -> float:
        bpm = float(self.cfg["render"].get("target_bpm", 84.0))
        beats = float(self.cfg["render"].get("beats_per_measure", 8.0))
        bar_rate = (bpm / 60.0) / max(1e-6, beats)
        return 2.0 * math.pi * bar_rate

    def _align_omega(self) -> float:
        align_bars = float(self.cfg["render"].get("align_interval_bars", 4.0))
        return self._bar_omega() / max(1e-6, align_bars)

    def _phase01(self, omega: float) -> float:
        phase = (omega * self.elapsed_s) / (2.0 * math.pi)
        return phase - math.floor(phase)

    @staticmethod
    def _pulse(x01: float, *, sharpness: float = 3.0) -> float:
        v = 0.5 * (1.0 + math.cos(2.0 * math.pi * x01))
        return max(0.0, min(1.0, v**sharpness))

    def _current_galaxy_id(self) -> Optional[str]:
        poller = self._ha_poller
        ha_galaxy = poller.get_context() if poller else None

        if poller and poller.online:
            if ha_galaxy:
                return ha_galaxy
            return self._local_galaxy_override

        # Offline: allow local cycling override, else stick to last-known HA context.
        if self._local_galaxy_override:
            return self._local_galaxy_override
        if ha_galaxy:
            return ha_galaxy
        return None

    def _set_quality_tier(self, tier: int) -> None:
        tier = int(max(0, min(2, tier)))
        if tier == self._quality_tier:
            return
        self._quality_tier = tier
        if tier == 0:
            self._quality_scale = 1.0
            self.renderer.tuning.base_thickness_mult = 1.0
            self.renderer.tuning.glow_thickness_mult = 1.0
        elif tier == 1:
            self._quality_scale = 0.75
            self.renderer.tuning.base_thickness_mult = 0.93
            self.renderer.tuning.glow_thickness_mult = 0.90
        else:
            self._quality_scale = 0.60
            self.renderer.tuning.base_thickness_mult = 0.88
            self.renderer.tuning.glow_thickness_mult = 0.78

        # Rebuild rings for the new point budget.
        for gs in self._galaxies.values():
            for p in gs.planets:
                self._rebuild_planet_rings(p)

    def _layout_world_positions(
        self, count: int, *, outer_radius: float
    ) -> Tuple[List[Vec3], List[Tuple[float, float]]]:
        w, h = self.renderer.width, self.renderer.height
        layout = str(self.cfg["render"].get("layout") or "radial").strip().lower()
        pad = float(self.cfg["render"].get("radial_padding") or 1.28)

        # Even with 0 planets, set a reasonable scale so projection is stable.
        if count <= 0:
            ring_radius_px = max(40.0, min(w, h) * 0.18)
            self.renderer.set_scale_for_ring_radius_px(
                outer_radius_world=outer_radius, ring_radius_px=ring_radius_px
            )
            return ([], [])

        ring_radius_px = max(40.0, min(w, h) * 0.18)

        if layout == "grid":
            # Special-case 3 nodes for Lovelace hotspot alignment.
            if count == 3:
                self.renderer.set_scale_for_ring_radius_px(
                    outer_radius_world=outer_radius, ring_radius_px=ring_radius_px
                )
                xs01 = [0.25, 0.50, 0.75]
                y01 = 0.50
                out_fixed: List[Vec3] = []
                xy01_fixed: List[Tuple[float, float]] = []
                for x01 in xs01:
                    sx = w * x01
                    sy = h * y01
                    dx = sx - (w * 0.5)
                    dy = sy - (h * 0.5)
                    world_x = dx * self.renderer.cam_dist / self.renderer.scale_px
                    world_y = dy * self.renderer.cam_dist / self.renderer.scale_px
                    out_fixed.append((world_x, world_y, 0.0))
                    xy01_fixed.append((x01, y01))
                return (out_fixed, xy01_fixed)

            cols = max(1, int(math.ceil(math.sqrt(count))))
            rows = max(1, int(math.ceil(count / cols)))
            cell_w = w / (cols + 1)
            cell_h = h / (rows + 1)
            ring_radius_px = max(40.0, min(cell_w, cell_h) * 0.33)
            self.renderer.set_scale_for_ring_radius_px(outer_radius_world=outer_radius, ring_radius_px=ring_radius_px)

            out: List[Vec3] = []
            xy01: List[Tuple[float, float]] = []
            for idx in range(count):
                r = idx // cols
                c = idx % cols
                sx = (c + 1) * cell_w
                sy = (r + 1) * cell_h
                dx = sx - (w * 0.5)
                dy = sy - (h * 0.5)
                world_x = dx * self.renderer.cam_dist / self.renderer.scale_px
                world_y = dy * self.renderer.cam_dist / self.renderer.scale_px
                out.append((world_x, world_y, 0.0))
                xy01.append((sx / max(1.0, w), sy / max(1.0, h)))
            return (out, xy01)

        # Radial: choose a circle radius that both avoids overlap and stays within window bounds.
        if count <= 1:
            k = 0.0
        else:
            k = pad / max(1e-6, math.sin(math.pi / count))

        # Fit constraint: circle_radius + ring_radius <= 0.48 * min_dim.
        min_dim = min(w, h)
        ring_radius_px = max(40.0, (0.48 * min_dim) / max(1e-6, (k + 1.0)))
        circle_radius_px = k * ring_radius_px

        self.renderer.set_scale_for_ring_radius_px(outer_radius_world=outer_radius, ring_radius_px=ring_radius_px)
        circle_radius_world = circle_radius_px * self.renderer.cam_dist / self.renderer.scale_px

        out = []
        for i in range(count):
            a = (2.0 * math.pi * i / max(1, count)) - (math.pi * 0.5)
            out.append((math.cos(a) * circle_radius_world, math.sin(a) * circle_radius_world, 0.0))
        xy01_out: List[Tuple[float, float]] = []
        for wp in out:
            sx, sy = self.renderer.project(wp)
            xy01_out.append((sx / max(1.0, w), sy / max(1.0, h)))
        return (out, xy01_out)

    def _build_galaxy_state(self, galaxy_id: str) -> GalaxyState:
        galaxy_cfg = get_galaxy_cfg(self.cfg, galaxy_id) or {}
        title = str(galaxy_cfg.get("title") or galaxy_id or "Galaxy").strip() or galaxy_id

        systems_cfg = galaxy_cfg.get("systems")
        if systems_cfg is None:
            systems_cfg = galaxy_cfg.get("planets")
        if not isinstance(systems_cfg, list):
            systems_cfg = []

        outer_radius = float(self.cfg["render"].get("outer_radius", 1.05))
        positions, xy01 = self._layout_world_positions(len(systems_cfg), outer_radius=outer_radius)
        scale_px = float(self.renderer.scale_px)

        planets: List[PlanetNode] = []
        for idx, pcfg in enumerate(systems_cfg):
            if not isinstance(pcfg, dict):
                continue
            pid = str(pcfg.get("id") or f"system_{idx}").strip() or f"system_{idx}"
            name = str(pcfg.get("name") or pid).strip() or pid
            loops_entity = str(pcfg.get("loops_entity") or "").strip()
            base_color_raw = pcfg.get("base_color") or [0.93, 0.76, 0.30]
            try:
                base_color = (float(base_color_raw[0]), float(base_color_raw[1]), float(base_color_raw[2]))
            except Exception:
                base_color = (0.93, 0.76, 0.30)
            base_color = (clamp01(base_color[0]), clamp01(base_color[1]), clamp01(base_color[2]))

            world_pos = positions[idx] if idx < len(positions) else (0.0, 0.0, 0.0)
            pos01 = xy01[idx] if idx < len(xy01) else (0.5, 0.5)
            phase_offset = stable_phase(f"phase:{pid}")
            planets.append(
                PlanetNode(
                    id=pid,
                    name=name,
                    loops_entity=loops_entity,
                    base_color=base_color,
                    world_pos=world_pos,
                    phase_offset=phase_offset,
                    screen_xy01=pos01,
                )
            )

        for p in planets:
            self._rebuild_planet_rings(p)

        layout_obj: Dict[str, Any] = {
            "galaxy": galaxy_id,
            "systems": [{"id": p.id, "x": float(p.screen_xy01[0]), "y": float(p.screen_xy01[1])} for p in planets],
        }

        return GalaxyState(
            id=galaxy_id,
            title=title,
            planets=planets,
            scale_px=scale_px,
            layout=layout_obj,
        )

    def _rebuild_all_galaxies(self) -> None:
        galaxies: Dict[str, GalaxyState] = {}
        for gid in self._galaxy_ids:
            galaxies[gid] = self._build_galaxy_state(gid)
        self._galaxies = galaxies

        self._set_poller_targets_union()

        if self._layout_store:
            for gid, gs in self._galaxies.items():
                self._layout_store.update(gid, gs.layout)

    def _set_current_galaxy(self, galaxy_id: str) -> None:
        gs = self._galaxies.get(galaxy_id)
        if not gs:
            return
        self._active_galaxy_id = galaxy_id
        self._planets = gs.planets
        self.renderer.scale_px = float(gs.scale_px)

    def _rebuild_planet_rings(self, planet: PlanetNode) -> None:
        render = self.cfg.get("render") or {}
        max_rings = int(render.get("max_rings_per_planet") or 10)
        outer_radius = float(render.get("outer_radius") or 1.05)
        inner_radius = float(render.get("inner_radius") or 0.38)

        rings, overflow = build_planet_rings(
            planet_id=planet.id,
            loop_count=planet.loop_count,
            base_color=planet.base_color,
            world_pos=planet.world_pos,
            max_rings=max_rings,
            outer_radius=outer_radius,
            inner_radius=inner_radius,
            quality_scale=self._quality_scale,
        )
        planet.rings = rings
        planet.overflow = overflow

    def _ensure_active_galaxy(self, *, force: bool = False) -> None:
        galaxy_id = self._current_galaxy_id() or self.args.galaxy
        if not galaxy_id:
            galaxy_id = self._galaxy_ids[0] if self._galaxy_ids else None
        if not galaxy_id:
            return

        # Match existing configured galaxies (case-insensitive fallback).
        if galaxy_id not in self._galaxies:
            g_lower = str(galaxy_id).strip().lower()
            for k in self._galaxies.keys():
                if str(k).lower() == g_lower:
                    galaxy_id = k
                    break

        if galaxy_id not in self._galaxies:
            galaxy_id = self._galaxy_ids[0] if self._galaxy_ids else galaxy_id

        if not force and galaxy_id == self._active_galaxy_id:
            return

        self._set_current_galaxy(galaxy_id)

    def _update_planet_counts(self) -> None:
        poller = self._ha_poller
        for gs in self._galaxies.values():
            for p in gs.planets:
                if not p.loops_entity or not poller:
                    if p.loop_count != 0 or p.unknown:
                        p.loop_count = 0
                        p.unknown = False
                        self._rebuild_planet_rings(p)
                    continue

                st = poller.get_cached(p.loops_entity)
                parsed = parse_intish(st.state if st else None)
                unknown = parsed is None
                loops = int(parsed or 0)
                if loops != p.loop_count or unknown != p.unknown:
                    p.loop_count = loops
                    p.unknown = unknown
                    self._rebuild_planet_rings(p)

        total_rings = 0
        for gs in self._galaxies.values():
            for p in gs.planets:
                total_rings += len(p.rings)
        if total_rings > 100:
            self._set_quality_tier(2)
        elif total_rings > 60:
            self._set_quality_tier(1)
        else:
            self._set_quality_tier(0)

    def _update_animation(self, dt: float) -> None:
        if self.paused:
            return
        self.elapsed_s += float(dt)
        spin_phase_base = self._bar_omega() * self.elapsed_s
        tumble_phase_base = self._align_omega() * self.elapsed_s

        for gs in self._galaxies.values():
            for p in gs.planets:
                spin_phase = spin_phase_base + p.phase_offset
                tumble_phase = tumble_phase_base + p.phase_offset * 0.37
                for r in p.rings:
                    r.offset = p.world_pos
                    r.update(spin_phase, tumble_phase)

    def _draw_overlay(self) -> None:
        galaxy_id = self._active_galaxy_id or ""
        gs = self._galaxies.get(galaxy_id)
        title = (gs.title if gs else "").strip() or str(galaxy_id or "Universe")

        title_surf = self.text_title.render(title, color=(220, 235, 255), alpha=235)
        self.composite.blit(title_surf, (12, 10))

        poller = self._ha_poller
        if poller and not poller.online:
            status = "OFFLINE"
            s = self.text_small.render(status, color=(255, 120, 120), alpha=235)
            self.composite.blit(s, (12, 40))
            if poller.last_error:
                err = poller.last_error
                if len(err) > 80:
                    err = err[:77] + "..."
                e = self.text_small.render(err, color=(255, 160, 160), alpha=200)
                self.composite.blit(e, (12, 58))

        if self._stream_server and galaxy_id:
            line = f"/stream/{galaxy_id}.mjpeg"
            u = self.text_small.render(line, color=(170, 205, 255), alpha=170)
            self.composite.blit(u, (12, self.renderer.height - u.get_height() - 10))

    def _render_to_composite(self) -> None:
        if self.renderer.bg_surface:
            self.composite.blit(self.renderer.bg_surface, (0, 0))
        else:
            self.composite.fill((0, 0, 0))

        self.layer.fill((0, 0, 0, 0))
        self.glow_layer.fill((0, 0, 0, 0))

        mph = self._phase01(self._bar_omega())
        aph = self._phase01(self._align_omega())
        measure_pulse = self._pulse(mph, sharpness=2.5)
        align_width = 0.07
        align_dist = min(aph, 1.0 - aph)
        align_pulse = max(0.0, 1.0 - align_dist / max(0.0001, align_width)) ** 3.2
        breath_rate = 0.08
        breath_depth = 0.22
        breath = math.sin(2.0 * math.pi * breath_rate * self.elapsed_s)

        thickness_scale = 1.0 + 0.25 * measure_pulse + 0.9 * align_pulse + breath_depth * breath
        alpha_boost = 0.08 * measure_pulse + 0.7 * align_pulse
        glow_scale = 1.0 + 2.8 * align_pulse

        for p in self._planets:
            for ring in p.rings:
                self.renderer.draw_ring(
                    self.layer,
                    self.glow_layer,
                    ring,
                    elapsed_s=self.elapsed_s,
                    thickness_scale=thickness_scale,
                    alpha_boost=alpha_boost,
                    glow_scale=glow_scale,
                )

            # Core glow tinted slightly toward planet color; core stays helios-white.
            core_glow = mix_rgb(self.renderer.core_glow_color, p.base_color, 0.35)
            core_radius_px = self.renderer.draw_core(
                self.layer,
                self.glow_layer,
                center_world=p.world_pos,
                rings=p.rings,
                elapsed_s=self.elapsed_s,
                glow_color=core_glow,
            )

            sx, sy = self.renderer.project(p.world_pos)
            label_y = int(sy + core_radius_px + 10)
            label = p.name + (" ?" if p.unknown else "")
            label_alpha = 170 if p.unknown else 235
            label_surf = self.text_label.render(label, color=(230, 235, 245), alpha=label_alpha)
            self.layer.blit(label_surf, (int(sx - label_surf.get_width() * 0.5), label_y))

            if p.overflow > 0:
                badge = f"+{p.overflow} loops"
                badge_surf = self.text_small.render(badge, color=(255, 210, 160), alpha=210)
                self.layer.blit(
                    badge_surf,
                    (int(sx - badge_surf.get_width() * 0.5), label_y + label_surf.get_height() + 2),
                )

        self.composite.blit(self.glow_layer, (0, 0))
        self.composite.blit(self.layer, (0, 0))
        self._draw_overlay()

    def _encode_stream(self, galaxy_id: str, *, force: bool = False) -> None:
        frames = self._stream_frames
        if not frames:
            return
        gs = self._galaxies.get(galaxy_id)
        if not gs:
            return

        stream_fps = max(1.0, float(self.cfg["render"].get("stream_fps") or 10))
        now_s = time.time()
        if not force and (now_s - gs.last_encoded_s) < (1.0 / stream_fps):
            return

        gs.last_encoded_s = now_s
        try:
            frames.update_from_surface(self.composite, galaxy_id=galaxy_id, quality=85)
        except Exception:
            # Keep rendering even if encoding fails.
            return

    def _prime_stream_frames(self) -> None:
        frames = self._stream_frames
        if not frames:
            return

        saved_active = self._active_galaxy_id
        saved_planets = self._planets
        saved_scale_px = float(self.renderer.scale_px)
        try:
            for gid in self._galaxy_ids:
                if gid not in self._galaxies:
                    continue
                self._set_current_galaxy(gid)
                self._render_to_composite()
                self._encode_stream(gid, force=True)
        finally:
            if saved_active and saved_active in self._galaxies:
                self._set_current_galaxy(saved_active)
            else:
                self._active_galaxy_id = saved_active
                self._planets = saved_planets
                self.renderer.scale_px = saved_scale_px

    def _stream_background_tick(self) -> None:
        frames = self._stream_frames
        if not frames:
            return

        now_s = time.time()
        active = self._active_galaxy_id or ""

        other_ids = [g for g in self._galaxy_ids if g != active]
        if not other_ids:
            return

        gid = other_ids[self._stream_rr_idx % len(other_ids)]
        self._stream_rr_idx = (self._stream_rr_idx + 1) % 10_000_000

        gs = self._galaxies.get(gid)
        if not gs:
            return

        # Static placeholder: touch occasionally so MJPEG clients don't stall forever.
        if not gs.planets:
            if now_s - gs.last_touch_s >= 2.0:
                frames.touch(gid)
                gs.last_touch_s = now_s
            return

        stream_fps = max(1.0, float(self.cfg["render"].get("stream_fps") or 10))
        if (now_s - gs.last_encoded_s) < (1.0 / stream_fps):
            return

        saved_active = self._active_galaxy_id
        saved_planets = self._planets
        saved_scale_px = float(self.renderer.scale_px)
        try:
            self._set_current_galaxy(gid)
            self._render_to_composite()
            self._encode_stream(gid, force=True)
        finally:
            if saved_active and saved_active in self._galaxies:
                self._set_current_galaxy(saved_active)
            else:
                self._active_galaxy_id = saved_active
                self._planets = saved_planets
                self.renderer.scale_px = saved_scale_px

    def _draw(self) -> None:
        self._render_to_composite()

        self.screen.blit(self.composite, (0, 0))
        pygame.display.flip()

        # MJPEG encode (active galaxy).
        if self._stream_frames and self._active_galaxy_id:
            self._stream_frames.set_default(self._active_galaxy_id)
            self._encode_stream(self._active_galaxy_id, force=False)

    def _resize(self, width: int, height: int) -> None:
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.renderer.resize(width, height)
        self.layer = pygame.Surface((self.renderer.width, self.renderer.height), pygame.SRCALPHA)
        self.glow_layer = pygame.Surface((self.renderer.width, self.renderer.height), pygame.SRCALPHA)
        self.composite = pygame.Surface((self.renderer.width, self.renderer.height))
        self._rebuild_all_galaxies()
        self._ensure_active_galaxy(force=True)
        if self._stream_frames:
            self._prime_stream_frames()

    def _reload_config(self) -> None:
        self.cfg = load_universe_config(self.args.config)
        self._galaxy_ids = list_galaxies(self.cfg)

        # Restart HA poller with new settings.
        if self._ha_poller:
            self._ha_poller.stop()
            self._ha_poller = None
        self._configure_ha()

        self._rebuild_all_galaxies()
        self._ensure_active_galaxy(force=True)
        if self._stream_frames:
            self._prime_stream_frames()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.VIDEORESIZE:
            self._resize(max(400, event.w), max(400, event.h))
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
            elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            elif event.key == pygame.K_r:
                self._reload_config()
            elif event.key == pygame.K_g:
                poller = self._ha_poller
                if poller and poller.online:
                    return
                if not self._galaxy_ids:
                    return
                cur = self._active_galaxy_id or self._galaxy_ids[0]
                try:
                    idx = self._galaxy_ids.index(cur)
                except ValueError:
                    idx = 0
                self._local_galaxy_override = self._galaxy_ids[(idx + 1) % len(self._galaxy_ids)]
                self._ensure_active_galaxy(force=True)

    def run(self) -> None:
        running = True
        start_s = time.time()
        max_fps = int(self.cfg["render"].get("max_fps") or 60)
        duration = float(self.args.duration) if self.args.duration is not None else None

        try:
            while running:
                dt = self.clock.tick(max(1, max_fps)) / 1000.0
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    else:
                        self.handle_event(event)

                self._ensure_active_galaxy(force=False)
                self._update_planet_counts()
                self._update_animation(dt)
                self._draw()
                self._stream_background_tick()

                if duration is not None and (time.time() - start_s) >= duration:
                    running = False
        finally:
            if self._stream_server:
                self._stream_server.stop()
            if self._ha_poller:
                self._ha_poller.stop()
            pygame.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description="GoGoGyro Universe (multi-planet) + Home Assistant adapter")
    parser.add_argument("--config", default="universe.json", help="Path to universe JSON config.")
    parser.add_argument("--galaxy", default=None, help="Fallback galaxy id if HA context is missing/offline.")
    parser.add_argument("--duration", type=float, default=None, help="Seconds to run before exiting (testing).")

    parser.add_argument("--serve-mjpeg", action="store_true", help="Serve MJPEG for Home Assistant embedding.")
    parser.add_argument("--host", default="0.0.0.0", help="Host bind for MJPEG server (default 0.0.0.0).")
    parser.add_argument("--port", type=int, default=8765, help="Port for MJPEG server.")

    args = parser.parse_args()

    cfg = load_universe_config(args.config)
    app = GyroUniverseApp(cfg, args)
    app.run()


if __name__ == "__main__":
    main()
