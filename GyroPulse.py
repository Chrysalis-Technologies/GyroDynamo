import math
import random
import argparse
import time
import colorsys
import pygame

# Helios / Orbital Sun Core palette
CORE_COLOR = (0.98, 0.99, 1.0)
CORE_GLOW = (0.62, 0.8, 1.0)
RING_GOLD = (0.93, 0.76, 0.30)
ACCENT_TEAL = (0.18, 0.74, 0.7)
GOLD_HUE, GOLD_SAT, GOLD_VAL = colorsys.rgb_to_hsv(*RING_GOLD)


# 3D rotation helpers
def rot_x(p, a):
    x, y, z = p
    ca, sa = math.cos(a), math.sin(a)
    return (x, y * ca - z * sa, y * sa + z * ca)


def rot_y(p, a):
    x, y, z = p
    ca, sa = math.cos(a), math.sin(a)
    return (x * ca + z * sa, y, -x * sa + z * ca)


def rot_z(p, a):
    x, y, z = p
    ca, sa = math.cos(a), math.sin(a)
    return (x * ca - y * sa, x * sa + y * ca, z)


class GyroRing:
    def __init__(self, radius, color, n_points=240,
                 spin_ratio=1, tx_ratio=1, ty_ratio=1, offset=None):
        self.base_radius = radius
        self.R = radius
        self.color = color  # (r,g,b) 0..1
        self.n = n_points
        self.speed_scale = 1.0
        self.thickness_scale = 1.0
        self.offset = offset if offset is not None else (0.0, 0.0, 0.0)
        h, s, v = colorsys.rgb_to_hsv(*color)
        self.hue = h
        self.saturation = s
        self.value = v
        self.glyph_stride = random.choice([9, 11, 13])
        self.glyph_phase = random.randrange(self.glyph_stride)

        # Orientation state
        self.tilt_x = 0.0
        self.tilt_y = 0.0
        self.spin = 0.0

        # Tempo-locked ratios (integers recommended for clean realignment)
        self.spin_ratio = spin_ratio
        self.tx_ratio = tx_ratio
        self.ty_ratio = ty_ratio

    def ring_points_3d(self):
        pts = []
        two_pi = 2.0 * math.pi
        ox, oy, oz = self.offset
        for i in range(self.n):
            t = two_pi * i / self.n
            p = (self.R * math.cos(t), self.R * math.sin(t), 0.0)
            p = rot_z(p, self.spin)
            p = rot_x(p, self.tilt_x)
            p = rot_y(p, self.tilt_y)
            p = (p[0] + ox, p[1] + oy, p[2] + oz)
            pts.append(p)
        return pts

    def current_color(self):
        r, g, b = colorsys.hsv_to_rgb(self.hue % 1.0, self.saturation, self.value)
        return (r, g, b)


class GyroPulse:
    """Rings realign to upright every reset_period seconds while staying tempo-locked."""

    def __init__(self, width=900, height=900, reset_period=10.0):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("GyroPulse")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont(None, 18)

        self.paused = False
        self.elapsed = 0.0
        self.reset_period = float(reset_period)
        self.target_bpm = 96.0
        self.cur_bpm = self.target_bpm
        self.beats_per_measure = 8
        self.align_width_frac = 0.05  # portion of cycle to use for flash
        self.zoom_scale = 1.0

        # Camera/focal settings
        self.cam_dist = 3.5
        self.focal_len = 1.0
        self.cam_orbit_amp = 0.06
        self.cam_orbit_speed = 0.14
        self.light_dir = self._normalize((0.2, 0.35, 1.0))

        # Visual settings
        self.base_thickness = 3.2
        self.back_alpha = 0.35
        self.front_alpha = 0.98
        self.glow_alpha = 0.14
        self.bg_top = (6, 8, 16)
        self.bg_bottom = (10, 14, 26)
        self.core_color = CORE_COLOR
        self.core_glow_color = CORE_GLOW
        self.accent_teal = ACCENT_TEAL
        self.aux_orbit_speed = 0.22

        # Rings (alternate directions for variety)
        self.rings = []
        self._init_rings()

        self.width = width
        self.height = height
        self.cx = width * 0.5
        self.cy = height * 0.5
        self.scale_px = min(width, height) * 0.48
        self.bg_surface = None
        self._build_background()

    # Utility helpers
    @staticmethod
    def _normalize(vec):
        x, y, z = vec
        mag = math.sqrt(x*x + y*y + z*z)
        if mag < 1e-6:
            return (0.0, 0.0, 1.0)
        return (x/mag, y/mag, z/mag)

    @staticmethod
    def _dot(a, b):
        return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

    @staticmethod
    def _clamp01(value):
        return max(0.0, min(1.0, value))

    @staticmethod
    def _ring_offset(radius):
        jitter = 0.06
        return (
            random.uniform(-jitter, jitter) * radius,
            random.uniform(-jitter * 0.6, jitter * 0.6) * radius,
            random.uniform(-jitter, jitter) * radius,
        )

    def _build_background(self):
        grad_col = pygame.Surface((1, self.height))
        for y in range(self.height):
            t = y / max(1, self.height - 1)
            r = int(self.bg_top[0] * (1 - t) + self.bg_bottom[0] * t)
            g = int(self.bg_top[1] * (1 - t) + self.bg_bottom[1] * t)
            b = int(self.bg_top[2] * (1 - t) + self.bg_bottom[2] * t)
            grad_col.set_at((0, y), (r, g, b))
        self.bg_surface = pygame.transform.smoothscale(grad_col, (self.width, self.height))

    # Ring management
    def _make_ring(self, index, radius):
        sign = 1 if index % 2 == 0 else -1
        spin_ratio = sign * (index + 1)
        tx_ratio = sign * (index + 1)
        ty_ratio = sign * (index + 2)
        tone = 0.98 - 0.04 * (index % 4)
        color = tuple(min(1.0, c * tone) for c in RING_GOLD)
        n_points = max(160, int(360 * radius))
        ring = GyroRing(radius, color, n_points=n_points,
                        spin_ratio=spin_ratio, tx_ratio=tx_ratio, ty_ratio=ty_ratio,
                        offset=self._ring_offset(radius))
        ring.speed_scale = 1.0
        return ring

    def _init_rings(self):
        base_radii = [1.06, 0.84, 0.62, 0.44]
        for idx, r in enumerate(base_radii):
            self.rings.append(self._make_ring(idx, r))

    def _reindex_rings(self):
        # Ensure order from outermost to innermost based on current radii.
        self.rings.sort(key=lambda r: r.R, reverse=True)
        for idx, ring in enumerate(self.rings):
            sign = 1 if idx % 2 == 0 else -1
            ring.spin_ratio = sign * (idx + 1)
            ring.tx_ratio = sign * (idx + 1)
            ring.ty_ratio = sign * (idx + 2)
            tone = 0.98 - 0.04 * (idx % 4)
            ring.color = tuple(min(1.0, c * tone) for c in RING_GOLD)
            h, s, v = colorsys.rgb_to_hsv(*ring.color)
            ring.hue, ring.saturation, ring.value = h, s, v
            ring.base_radius = ring.R
            ring.speed_scale = 1.0

    def add_ring(self):
        max_rings = 12
        if len(self.rings) >= max_rings:
            return
        last_r = self.rings[-1].R if self.rings else 1.0
        new_radius = max(0.08, last_r * 0.78)
        idx = len(self.rings)
        self.rings.append(self._make_ring(idx, new_radius))
        self._reindex_rings()

    def add_outer_ring(self):
        max_rings = 12
        if len(self.rings) >= max_rings:
            return
        outer_r = self.rings[0].R if self.rings else 1.0
        new_radius = min(2.0, outer_r * 1.22)
        idx = len(self.rings)
        self.rings.append(self._make_ring(idx, new_radius))
        self._reindex_rings()

    def add_inner_ring(self):
        self.add_ring()

    def remove_ring(self):
        if len(self.rings) > 1:
            self.rings.pop()
            self._reindex_rings()

    # Center sphere
    def _center_palette(self):
        """Return core palette (white-hot) independent of rings."""
        base = self.core_color
        palette = [self.core_color, (1.0, 1.0, 1.0)]
        return base, palette

    def draw_center_sphere(self, surface, glow_surface):
        _, palette = self._center_palette()
        radius_px = int(min(self.width, self.height) * 0.07 * self.zoom_scale)
        if self.rings:
            inner = self.rings[-1]
            px, _ = self.project((inner.R, 0, 0))
            inner_px = abs(px - self.cx)
            radius_px = min(radius_px, max(12, inner_px * 0.55))
        radius_px = max(10, min(radius_px, int(min(self.width, self.height) * 0.18)))

        sphere = pygame.Surface((radius_px * 2, radius_px * 2), pygame.SRCALPHA)
        center = (radius_px, radius_px)

        # Layered body using palette colors to mimic reflective pickup of ring hues.
        layers = max(4, len(palette) + 2)
        for i in range(layers):
            t = i / float(layers - 1)
            col_idx = min(len(palette) - 1, int(t * len(palette)))
            tint = palette[col_idx]
            tint_rgb = tuple(int(max(0.0, min(1.0, c)) * 255) for c in tint)
            alpha = int(245 * (1.0 - t) ** 1.5)
            radius = int(radius_px * (1.0 - 0.09 * i))
            pygame.draw.circle(sphere, tint_rgb + (alpha,), center, radius)

        # Specular highlight
        highlight_col = (255, 255, 255, 150)
        pygame.draw.circle(sphere, highlight_col,
                           (int(radius_px * 0.42), int(radius_px * 0.42)),
                           int(radius_px * 0.32))

        surface.blit(sphere, (self.cx - radius_px, self.cy - radius_px))

        # Glow also tinted with palette average
        glow_rgb = tuple(int(c * 255) for c in self.core_glow_color)
        for scale, alpha in ((1.6, 160), (2.2, 90), (2.9, 50)):
            pygame.draw.circle(
                glow_surface,
                glow_rgb + (alpha,),
                (int(self.cx), int(self.cy)),
                int(radius_px * scale),
            )

    def draw_aux_node(self, surface, glow_surface):
        if not self.rings:
            return
        t = self.elapsed * self.aux_orbit_speed
        orbit_r = self.rings[0].R * 0.9
        pos = (
            orbit_r * math.cos(t),
            orbit_r * 0.35 * math.sin(t * 0.7),
            orbit_r * 0.6 * math.sin(t),
        )
        x, y = self.project(pos)
        radius = int(min(self.width, self.height) * 0.012 * self.zoom_scale)
        teal_rgb = tuple(int(c * 255) for c in self.accent_teal)
        pygame.draw.circle(glow_surface, teal_rgb + (50,), (int(x), int(y)), int(radius * 2.8))
        pygame.draw.circle(glow_surface, teal_rgb + (90,), (int(x), int(y)), int(radius * 1.6))
        pygame.draw.circle(surface, teal_rgb + (200,), (int(x), int(y)), max(2, radius))

    # Tempo helpers
    def bar_omega(self):
        bar_rate = (self.cur_bpm / 60.0) / self.beats_per_measure  # measures per second
        return 2.0 * math.pi * bar_rate

    # Projection
    def project(self, p):
        x, y, z = p
        denom = (z + self.cam_dist)
        if denom < 0.1:
            denom = 0.1
        u = (self.focal_len * x) / denom
        v = (self.focal_len * y) / denom
        return (self.cx + u * self.scale_px * self.zoom_scale,
                self.cy + v * self.scale_px * self.zoom_scale)

    def update(self, dt):
        if self.paused:
            return
        self.elapsed += dt
        self.cur_bpm += (self.target_bpm - self.cur_bpm) * min(1.0, 4.0 * dt)

        base_omega = 2.0 * math.pi / self.reset_period

        # Continuous spin/tilt that realigns every reset_period (integer turns per period).
        for ring in self.rings:
            phase = base_omega * self.elapsed
            ring.spin = ring.spin_ratio * ring.speed_scale * phase
            ring.tilt_x = ring.tx_ratio * ring.speed_scale * phase
            ring.tilt_y = ring.ty_ratio * ring.speed_scale * phase

        # Camera parallax drift
        orbit_t = self.elapsed * self.cam_orbit_speed
        orbit_amp_px = self.cam_orbit_amp * self.scale_px
        self.cx = (self.width * 0.5) + math.sin(orbit_t) * orbit_amp_px
        self.cy = (self.height * 0.5) + math.cos(orbit_t * 0.8) * orbit_amp_px

    def draw_ring(self, surface, glow_surface, ring, thickness_scale=1.0,
                 alpha_boost=0.0, glow_scale=1.0):
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

        base_color = ring.current_color()
        base_thickness = max(1.0, self.base_thickness * thickness_scale * ring.thickness_scale)
        thickness_px = max(1, int(base_thickness))
        glow_thickness_px = max(1, int(thickness_px * 2.2))

        clamp255 = lambda v: max(0, min(255, int(v)))
        for _, mid, _, x0, y0, x1, y1 in segments:
            depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, mid[2]))  # [-1,1] -> [0,1]
            light = max(0.0, self._dot(self._normalize(mid), self.light_dir))
            shade = 0.7 + 0.2 * depth_mix + 0.25 * light
            alpha = self.back_alpha + (self.front_alpha - self.back_alpha) * depth_mix + alpha_boost
            alpha = max(0.0, min(1.0, alpha))
            rgba = (
                clamp255(base_color[0] * shade * 255),
                clamp255(base_color[1] * shade * 255),
                clamp255(base_color[2] * shade * 255),
                int(alpha * 255),
            )

            glow_a = min(1.0, self.glow_alpha * (0.8 + 0.6 * depth_mix) * glow_scale)
            glow_color = (
                clamp255(base_color[0] * shade * 255),
                clamp255(base_color[1] * shade * 255),
                clamp255(base_color[2] * shade * 255),
                int(glow_a * 255),
            )

            pygame.draw.line(glow_surface, glow_color, (x0, y0), (x1, y1), glow_thickness_px)
            pygame.draw.line(surface, rgba, (x0, y0), (x1, y1), thickness_px)

        glyph_thickness = max(1, int(thickness_px * 0.7))
        for _, mid, idx, x0, y0, x1, y1 in segments:
            if (idx + ring.glyph_phase) % ring.glyph_stride != 0:
                continue
            depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, mid[2]))
            if depth_mix < 0.35:
                continue
            light = max(0.0, self._dot(self._normalize(mid), self.light_dir))
            shade = 0.9 + 0.2 * depth_mix + 0.2 * light
            alpha = min(1.0, self.front_alpha + alpha_boost + 0.2)
            glyph_color = (
                clamp255(base_color[0] * shade * 255 + 15),
                clamp255(base_color[1] * shade * 255 + 15),
                clamp255(base_color[2] * shade * 255 + 15),
                int(alpha * 255),
            )
            pygame.draw.line(surface, glyph_color, (x0, y0), (x1, y1), glyph_thickness)

    def draw(self):
        if self.bg_surface:
            self.screen.blit(self.bg_surface, (0, 0))
        else:
            self.screen.fill((0, 0, 0))

        layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        glow_layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        # Beat/measure pulses retained for subtle dynamics
        beats_total = self.elapsed * (self.cur_bpm / 60.0)
        mph = (beats_total / self.beats_per_measure) % 1.0
        bph = beats_total % 1.0
        pulse = lambda x, sharp=3.0: max(0.0, min(1.0, (0.5 * (1.0 + math.cos(2.0 * math.pi * x))) ** sharp))
        thickness_scale = 1.0 + 0.25 * pulse(mph, 2.5)
        alpha_boost = 0.06 * pulse(bph, 3.5) + 0.12 * pulse(mph, 2.5)

        # Alignment pulse: flash when cycle resets (every reset_period seconds).
        align_phase = (self.elapsed % self.reset_period) / self.reset_period
        align_dist = min(align_phase, 1.0 - align_phase)
        align_pulse = max(0.0, 1.0 - align_dist / self.align_width_frac) ** 3.2
        thickness_scale += 1.1 * align_pulse
        alpha_boost += 0.9 * align_pulse
        glow_scale = 1.0 + 3.2 * align_pulse

        for r in self.rings:
            self.draw_ring(layer, glow_layer, r,
                           thickness_scale=thickness_scale,
                           alpha_boost=alpha_boost,
                           glow_scale=glow_scale)

        self.draw_aux_node(layer, glow_layer)
        self.draw_center_sphere(layer, glow_layer)
        self.screen.blit(glow_layer, (0, 0))
        self.screen.blit(layer, (0, 0))

        # HUD
        info = (
            f"Align every {self.reset_period:.1f}s ([ / ] to change) • "
            f"Rings: {len(self.rings)} (+ inner / o outer / - remove) • "
            f"Zoom: , / . • BPM {self.cur_bpm:5.1f} • Space: pause • Esc/Q: quit"
        )
        text = self.font_small.render(info, True, (210, 210, 220))
        self.screen.blit(text, (16, 16))

        pygame.display.flip()

    def resize(self, width, height):
        self.width = max(400, width)
        self.height = max(400, height)
        self.cx = self.width * 0.5
        self.cy = self.height * 0.5
        self.scale_px = min(self.width, self.height) * 0.48
        self._build_background()

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            self.resize(event.w, event.h)
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
            elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            elif event.key == pygame.K_LEFTBRACKET:
                self.reset_period = max(2.0, self.reset_period - 1.0)
            elif event.key == pygame.K_RIGHTBRACKET:
                self.reset_period = min(60.0, self.reset_period + 1.0)
            elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS) or event.unicode == '+':
                self.add_inner_ring()
            elif event.key == pygame.K_o:
                self.add_outer_ring()
            elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS) or event.unicode == '-':
                self.remove_ring()
            elif event.key == pygame.K_COMMA:
                self.zoom_scale = max(0.25, self.zoom_scale * 0.9)
                self.scale_px = min(self.width, self.height) * 0.48
            elif event.key == pygame.K_PERIOD:
                self.zoom_scale = min(3.0, self.zoom_scale * 1.1)
                self.scale_px = min(self.width, self.height) * 0.48

    def run(self, duration=None):
        running = True
        start_time = time.time()
        while running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_event(event)
            self.update(dt)
            self.draw()
            if duration and (time.time() - start_time) >= duration:
                running = False
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="GyroPulse: rings realign upright on a fixed period")
    parser.add_argument('--width', type=int, default=900)
    parser.add_argument('--height', type=int, default=900)
    parser.add_argument('--duration', type=float, default=None, help='Seconds to run before exiting')
    parser.add_argument('--period', type=float, default=10.0, help='Seconds between full upright resets')
    args = parser.parse_args()

    app = GyroPulse(args.width, args.height, reset_period=args.period)
    app.run(duration=args.duration)


if __name__ == '__main__':
    main()
