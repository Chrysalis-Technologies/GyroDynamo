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

TARGET_BPM = 84
BEATS_PER_MEASURE = 8
ALIGN_INTERVAL_BARS = 4


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


class Ring:
    def __init__(self, radius, color, n_points,
                 spin_ratio, tx_ratio, ty_ratio,
                 band_count=3, axis_angle=0.0):
        self.R = radius
        self.color = color
        self.n = n_points
        self.spin_ratio = spin_ratio
        self.tx_ratio = tx_ratio
        self.ty_ratio = ty_ratio
        self.axis_angle = axis_angle
        self.spin = 0.0
        self.tilt_x = 0.0
        self.tilt_y = 0.0
        self.offset = (0.0, 0.0, 0.0)
        h, s, v = colorsys.rgb_to_hsv(*color)
        self.hue = h
        self.saturation = s
        self.value = v
        self.band_count = max(2, int(band_count))
        self.band_phase = random.randrange(self.n)
        self.band_colors = []
        self.glyph_stride = random.choice([9, 11, 13])
        self.glyph_phase = random.randrange(self.glyph_stride)
        self.refresh_band_colors()

    def refresh_band_colors(self):
        self.band_colors = []
        band_count = max(2, int(self.band_count))
        for band in range(band_count):
            band_pos = (band / (band_count - 1)) - 0.5
            hue = (self.hue + band_pos * 0.05) % 1.0
            sat = max(0.0, min(1.0, self.saturation * (1.0 - abs(band_pos) * 0.12)))
            val = max(0.0, min(1.0, self.value * (1.0 + band_pos * 0.25)))
            self.band_colors.append(colorsys.hsv_to_rgb(hue, sat, val))

    def segment_color(self, idx):
        if not self.band_colors:
            self.refresh_band_colors()
        n = max(1, self.n)
        offset_idx = (idx + self.band_phase) % n
        band = int((offset_idx / n) * self.band_count)
        if band >= self.band_count:
            band = self.band_count - 1
        return self.band_colors[band]

    def update(self, spin_phase, tumble_phase):
        self.spin = self.spin_ratio * spin_phase
        self.tilt_x = self.tx_ratio * tumble_phase
        self.tilt_y = self.ty_ratio * tumble_phase

    def ring_points_3d(self):
        pts = []
        two_pi = 2.0 * math.pi
        ox, oy, oz = self.offset
        for i in range(self.n):
            t = two_pi * i / self.n
            p = (self.R * math.cos(t), self.R * math.sin(t), 0.0)
            p = rot_z(p, self.spin)
            if abs(self.axis_angle) > 1e-6:
                p = rot_z(p, self.axis_angle)
            p = rot_x(p, self.tilt_x)
            p = rot_y(p, self.tilt_y)
            if abs(self.axis_angle) > 1e-6:
                p = rot_z(p, -self.axis_angle)
            p = (p[0] + ox, p[1] + oy, p[2] + oz)
            pts.append(p)
        return pts


class GoGoGyroAligned:
    def __init__(self, width=900, height=900):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("GoGoGyro Aligned")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont(None, 18)

        self.paused = False
        self.elapsed = 0.0

        self.cam_dist = 3.8
        self.focal_len = 1.0
        self.light_dir = self._normalize((0.2, 0.35, 1.0))
        self.base_thickness = 3.0
        self.back_alpha = 0.35
        self.front_alpha = 0.98
        self.glow_alpha = 0.14
        self.align_width = 0.07

        self.bg_top = (6, 8, 16)
        self.bg_bottom = (10, 14, 26)
        self.core_color = CORE_COLOR
        self.core_glow_color = CORE_GLOW

        self.width = width
        self.height = height
        self.cx = width * 0.5
        self.cy = height * 0.5
        self.scale_px = min(width, height) * 0.48
        self.bg_surface = None
        self._build_background()

        ring_specs = [
            (1.05, 320, 5, 3, 0, 3, 0),
            (0.82, 280, 7, 4, 0, 3, 24),
            (0.60, 240, 9, 5, 0, 4, -28),
            (0.38, 210, 11, 6, 0, 4, 36),
        ]
        tones = [1.0, 0.95, 0.9, 0.85]
        self.rings = []
        for idx, (radius, n_points, spin_ratio, tx_ratio, ty_ratio,
                  band_count, axis_angle_deg) in enumerate(ring_specs):
            dir_sign = -1 if (idx % 2) else 1
            spin_ratio *= dir_sign
            tx_ratio *= dir_sign
            ty_ratio *= dir_sign
            tone = tones[idx % len(tones)]
            color = tuple(min(1.0, c * tone) for c in RING_GOLD)
            self.rings.append(
                Ring(
                    radius,
                    color,
                    n_points=n_points,
                    spin_ratio=spin_ratio,
                    tx_ratio=tx_ratio,
                    ty_ratio=ty_ratio,
                    band_count=band_count,
                    axis_angle=math.radians(axis_angle_deg),
                )
            )

    @staticmethod
    def _normalize(vec):
        x, y, z = vec
        mag = math.sqrt(x * x + y * y + z * z)
        if mag < 1e-6:
            return (0.0, 0.0, 1.0)
        return (x / mag, y / mag, z / mag)

    @staticmethod
    def _dot(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    @staticmethod
    def _offset_line(x0, y0, x1, y1, offset):
        dx = x1 - x0
        dy = y1 - y0
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return None
        nx = -dy / length
        ny = dx / length
        return (x0 + nx * offset, y0 + ny * offset,
                x1 + nx * offset, y1 + ny * offset)

    def _build_background(self):
        grad_col = pygame.Surface((1, self.height))
        for y in range(self.height):
            t = y / max(1, self.height - 1)
            r = int(self.bg_top[0] * (1 - t) + self.bg_bottom[0] * t)
            g = int(self.bg_top[1] * (1 - t) + self.bg_bottom[1] * t)
            b = int(self.bg_top[2] * (1 - t) + self.bg_bottom[2] * t)
            grad_col.set_at((0, y), (r, g, b))
        self.bg_surface = pygame.transform.smoothscale(grad_col, (self.width, self.height))

    def bar_omega(self):
        bar_rate = (TARGET_BPM / 60.0) / BEATS_PER_MEASURE
        return 2.0 * math.pi * bar_rate

    def align_omega(self):
        return self.bar_omega() / max(1, ALIGN_INTERVAL_BARS)

    def measure_phase(self):
        phase = (self.bar_omega() * self.elapsed) / (2.0 * math.pi)
        return phase - math.floor(phase)

    def align_phase(self):
        phase = (self.align_omega() * self.elapsed) / (2.0 * math.pi)
        return phase - math.floor(phase)

    def pulse(self, x, sharpness=3.0):
        v = 0.5 * (1.0 + math.cos(2.0 * math.pi * x))
        return max(0.0, min(1.0, v ** sharpness))

    def update(self, dt):
        if self.paused:
            return
        self.elapsed += dt
        spin_phase = self.bar_omega() * self.elapsed
        tumble_phase = self.align_omega() * self.elapsed
        for ring in self.rings:
            ring.update(spin_phase, tumble_phase)

    def project(self, p):
        x, y, z = p
        denom = z + self.cam_dist
        if denom < 0.1:
            denom = 0.1
        u = (self.focal_len * x) / denom
        v = (self.focal_len * y) / denom
        return (self.cx + u * self.scale_px, self.cy + v * self.scale_px)

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

        base_thickness = max(1.0, self.base_thickness * thickness_scale)
        thickness_px = max(1, int(base_thickness))
        glow_thickness_px = max(1, int(thickness_px * 2.2))

        clamp255 = lambda v: max(0, min(255, int(v)))
        for _, mid, idx, x0, y0, x1, y1 in segments:
            depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, mid[2]))
            light = max(0.0, self._dot(self._normalize(mid), self.light_dir))
            shade = 0.7 + 0.2 * depth_mix + 0.25 * light
            alpha = self.back_alpha + (self.front_alpha - self.back_alpha) * depth_mix + alpha_boost
            alpha = max(0.0, min(1.0, alpha))
            seg_color = ring.segment_color(idx)
            rgba = (
                clamp255(seg_color[0] * shade * 255),
                clamp255(seg_color[1] * shade * 255),
                clamp255(seg_color[2] * shade * 255),
                int(alpha * 255),
            )
            glow_a = min(1.0, self.glow_alpha * (0.8 + 0.6 * depth_mix) * glow_scale)
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
                pygame.draw.line(surface, edge_color, (edge_line[0], edge_line[1]),
                                 (edge_line[2], edge_line[3]), max(1, int(thickness_px * 0.55)))
            if highlight_line:
                pygame.draw.line(surface, highlight_color, (highlight_line[0], highlight_line[1]),
                                 (highlight_line[2], highlight_line[3]), max(1, int(thickness_px * 0.5)))

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
            seg_color = ring.segment_color(idx)
            glyph_color = (
                clamp255(seg_color[0] * shade * 255 + 15),
                clamp255(seg_color[1] * shade * 255 + 15),
                clamp255(seg_color[2] * shade * 255 + 15),
                int(alpha * 255),
            )
            pygame.draw.line(surface, glyph_color, (x0, y0), (x1, y1), glyph_thickness)

    def draw_center_sphere(self, surface, glow_surface):
        radius_px = int(min(self.width, self.height) * 0.07)
        if self.rings:
            inner = self.rings[-1]
            px, _ = self.project((inner.R, 0, 0))
            inner_px = abs(px - self.cx)
            radius_px = min(radius_px, max(12, int(inner_px * 0.55)))
        radius_px = max(10, min(radius_px, int(min(self.width, self.height) * 0.18)))

        sphere = pygame.Surface((radius_px * 2, radius_px * 2), pygame.SRCALPHA)
        center = (radius_px, radius_px)
        layers = 5
        for i in range(layers):
            t = i / float(layers - 1)
            tint = self.core_color
            tint_rgb = tuple(int(max(0.0, min(1.0, c)) * 255) for c in tint)
            alpha = int(245 * (1.0 - t) ** 1.5)
            radius = max(1, int(radius_px * (1.0 - 0.09 * i)))
            pygame.draw.circle(sphere, tint_rgb + (alpha,), center, radius)

        highlight_col = (255, 255, 255, 150)
        pygame.draw.circle(
            sphere,
            highlight_col,
            (int(radius_px * 0.42), int(radius_px * 0.42)),
            int(radius_px * 0.32),
        )

        surface.blit(sphere, (self.cx - radius_px, self.cy - radius_px))
        glow_rgb = tuple(int(c * 255) for c in self.core_glow_color)
        for scale, alpha in ((1.6, 160), (2.2, 90), (2.9, 50)):
            pygame.draw.circle(
                glow_surface,
                glow_rgb + (alpha,),
                (int(self.cx), int(self.cy)),
                int(radius_px * scale),
            )

    def draw(self):
        if self.bg_surface:
            self.screen.blit(self.bg_surface, (0, 0))
        else:
            self.screen.fill((0, 0, 0))

        layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        glow_layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        mph = self.measure_phase()
        aph = self.align_phase()
        measure_pulse = self.pulse(mph, sharpness=2.5)
        align_dist = min(aph, 1.0 - aph)
        align_pulse = max(0.0, 1.0 - align_dist / max(0.0001, self.align_width)) ** 3.2
        thickness_scale = 1.0 + 0.25 * measure_pulse + 0.9 * align_pulse
        alpha_boost = 0.08 * measure_pulse + 0.7 * align_pulse
        glow_scale = 1.0 + 2.8 * align_pulse

        for ring in self.rings:
            self.draw_ring(
                layer,
                glow_layer,
                ring,
                thickness_scale=thickness_scale,
                alpha_boost=alpha_boost,
                glow_scale=glow_scale,
            )

        self.draw_center_sphere(layer, glow_layer)

        self.screen.blit(glow_layer, (0, 0))
        self.screen.blit(layer, (0, 0))
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
    parser = argparse.ArgumentParser(description="Aligned ring variant (no UI controls)")
    parser.add_argument('--width', type=int, default=900)
    parser.add_argument('--height', type=int, default=900)
    parser.add_argument('--duration', type=float, default=None,
                        help='Seconds to run before exiting (useful for headless testing).')
    args = parser.parse_args()

    app = GoGoGyroAligned(args.width, args.height)
    app.run(duration=args.duration)


if __name__ == '__main__':
    main()
