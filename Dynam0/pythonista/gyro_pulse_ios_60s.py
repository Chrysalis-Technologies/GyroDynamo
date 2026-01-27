# GyroPulse (Pythonista)
# Lightweight iOS-friendly version of the desktop GyroPulse.
# Features:
# - Rings spin with integer ratios so they realign every reset_period seconds.
# - Alignment flash (thicker/brighter stroke) on each realignment.
# - Add/remove rings, adjust alignment period, and zoom via on-screen buttons.
# - Pause/resume with a tap.
#
# Controls (tap buttons at top):
#   [+] add inner ring    [O+] add outer ring    [-] remove ring
#   [T-] period -1s       [T+] period +1s
#   [Z-] zoom out         [Z+] zoom in
# Tap anywhere else to pause/resume.

import math
import random
import colorsys
import scene
import ui

# Helios / Orbital Sun Core palette
CORE_COLOR = (0.98, 0.99, 1.0)
CORE_GLOW = (0.62, 0.8, 1.0)
RING_GOLD = (0.93, 0.76, 0.30)
ACCENT_TEAL = (0.18, 0.74, 0.7)


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
    def __init__(self, R, color, n_points=180, spin_ratio=1, tx_ratio=1, ty_ratio=2):
        self.R = R
        self.base_radius = R
        self.color = color
        self.n = n_points
        self.spin_ratio = spin_ratio
        self.tx_ratio = tx_ratio
        self.ty_ratio = ty_ratio
        self.speed_scale = 1.0
        self.spin = 0.0
        self.tilt_x = 0.0
        self.tilt_y = 0.0
        self.offset = (0.0, 0.0, 0.0)
        self.glyph_stride = 11
        self.glyph_phase = 0

    def points3d(self):
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


class GyroPulseScene(scene.Scene):
    def setup(self):
        self.reset_period = 60.0
        self.align_width = 0.05  # fraction of cycle for flash
        self.elapsed = 0.0
        self.paused = False
        self.zoom = 1.0
        self.base_thickness = 2.4
        self.bg_top = (0.02, 0.03, 0.05)
        self.bg_bottom = (0.04, 0.05, 0.09)
        self.core_color = CORE_COLOR
        self.core_glow_color = CORE_GLOW
        self.accent_teal = ACCENT_TEAL
        self.aux_orbit_speed = 0.22
        self.aux_phase = 0.0
        self.buttons = []
        self._build_buttons()
        self.rings = []
        self._init_rings()

    # ---------- Ring setup ----------
    @staticmethod
    def _ring_offset(radius):
        jitter = 0.06
        return (
            random.uniform(-jitter, jitter) * radius,
            random.uniform(-jitter * 0.6, jitter * 0.6) * radius,
            random.uniform(-jitter, jitter) * radius,
        )

    def _make_ring(self, idx, R):
        sign = 1 if idx % 2 == 0 else -1
        spin_ratio = sign * (idx + 1)
        tx_ratio = sign * (idx + 1)
        ty_ratio = sign * (idx + 2)
        tone = 0.98 - 0.04 * (idx % 4)
        color = tuple(min(1.0, c * tone) for c in RING_GOLD)
        n_pts = max(120, int(280 * R))
        ring = Ring(R, color, n_points=n_pts, spin_ratio=spin_ratio, tx_ratio=tx_ratio, ty_ratio=ty_ratio)
        ring.offset = self._ring_offset(R)
        ring.glyph_stride = random.choice([9, 11, 13])
        ring.glyph_phase = random.randrange(ring.glyph_stride)
        return ring

    def _init_rings(self):
        for idx, r in enumerate([1.0, 0.8, 0.62, 0.46]):
            self.rings.append(self._make_ring(idx, r))
        self._layout_buttons()

    def _reindex(self):
        self.rings.sort(key=lambda r: r.R, reverse=True)
        for idx, r in enumerate(self.rings):
            sign = 1 if idx % 2 == 0 else -1
            r.spin_ratio = sign * (idx + 1)
            r.tx_ratio = sign * (idx + 1)
            r.ty_ratio = sign * (idx + 2)
            r.base_radius = r.R
            tone = 0.98 - 0.04 * (idx % 4)
            r.color = tuple(min(1.0, c * tone) for c in RING_GOLD)

    def add_inner(self):
        if len(self.rings) >= 12:
            return
        new_r = max(0.08, self.rings[-1].R * 0.78)
        self.rings.append(self._make_ring(len(self.rings), new_r))
        self._reindex()

    def add_outer(self):
        if len(self.rings) >= 12:
            return
        new_r = min(2.0, self.rings[0].R * 1.22)
        self.rings.append(self._make_ring(len(self.rings), new_r))
        self._reindex()

    def remove_ring(self):
        if len(self.rings) > 1:
            self.rings.pop()
            self._reindex()

    # ---------- UI ----------
    def _build_buttons(self):
        labels = ['+', 'O+', '-', 'T-', 'T+', 'Z-', 'Z+']
        actions = ['add_inner', 'add_outer', 'remove_ring', 'period_down', 'period_up', 'zoom_out', 'zoom_in']
        x = 14
        for lbl, act in zip(labels, actions):
            self.buttons.append({'rect': ui.Rect(x, 12, 52, 30), 'label': lbl, 'action': act})
            x += 56

    def _layout_buttons(self):
        # Place the button bar near the bottom (assumes scene origin top-left in Pythonista).
        bar_h = 30
        margin = 10
        y = max(margin, self.size.h - bar_h - margin)
        for btn in self.buttons:
            r = btn['rect']
            btn['rect'] = ui.Rect(r.x, y, r.width, r.height)

    def _hit_button(self, touch):
        pt = (touch.location.x, touch.location.y)
        for btn in self.buttons:
            r = btn['rect']
            rx, ry, rw, rh = r.x, r.y, r.width, r.height
            if (rx <= pt[0] <= rx + rw) and (ry <= pt[1] <= ry + rh):
                return btn['action']
        return None

    # ---------- Interaction ----------
    def touch_began(self, touch):
        action = self._hit_button(touch)
        if action:
            getattr(self, action)()
        else:
            self.paused = not self.paused

    def period_up(self):
        self.reset_period = min(60.0, self.reset_period + 1.0)

    def period_down(self):
        self.reset_period = max(2.0, self.reset_period - 1.0)

    def zoom_in(self):
        self.zoom = min(3.0, self.zoom * 1.1)

    def zoom_out(self):
        self.zoom = max(0.3, self.zoom * 0.9)

    # ---------- Rendering helpers ----------
    def _project(self, p):
        w, h = self.size
        cx, cy = w * 0.5, h * 0.5
        cam_dist = 3.5
        focal = 1.0
        x, y, z = p
        denom = z + cam_dist
        if denom < 0.1:
            denom = 0.1
        u = (focal * x) / denom
        v = (focal * y) / denom
        scale_px = min(w, h) * 0.46 * self.zoom
        return (cx + u * scale_px, cy + v * scale_px)

    def _center_color(self):
        return self.core_color

    # ---------- Scene loop ----------
    def update(self):
        if self.paused:
            return
        dt = min(1 / 30.0, self.dt)
        self.elapsed += dt
        base_omega = 2.0 * math.pi / self.reset_period
        phase = base_omega * self.elapsed

        # Update ring angles
        for r in self.rings:
            r.spin = r.spin_ratio * r.speed_scale * phase
            r.tilt_x = r.tx_ratio * r.speed_scale * phase
            r.tilt_y = r.ty_ratio * r.speed_scale * phase

        self.aux_phase = (self.aux_phase + dt * self.aux_orbit_speed) % (2.0 * math.pi)

    def draw(self):
        w, h = self.size
        self._layout_buttons()
        # Gradient background
        for i in range(int(h)):
            t = i / max(1, h - 1)
            c = tuple(self.bg_top[j] * (1 - t) + self.bg_bottom[j] * t for j in range(3))
            scene.fill(*c)
            scene.stroke(0, 0, 0, 0)
            scene.rect(0, h - i - 1, w, 1)

        # Pulses
        beats_total = self.elapsed * (96.0 / 60.0)
        mph = (beats_total / 8.0) % 1.0
        bph = beats_total % 1.0
        pulse_fn = lambda x, sharp=3.0: max(0.0, min(1.0, (0.5 * (1.0 + math.cos(2.0 * math.pi * x))) ** sharp))
        thickness_scale = 1.0 + 0.25 * pulse_fn(mph, 2.5)
        alpha_boost = 0.08 * pulse_fn(bph, 3.5) + 0.14 * pulse_fn(mph, 2.5)
        align_phase = (self.elapsed % self.reset_period) / self.reset_period
        align_dist = min(align_phase, 1.0 - align_phase)
        align_pulse = max(0.0, 1.0 - align_dist / self.align_width) ** 3.2
        thickness_scale += 1.1 * align_pulse
        alpha_boost += 0.9 * align_pulse
        glow_scale = 1.0 + 3.0 * align_pulse

        # Core glow (behind rings)
        cx, cy = w * 0.5, h * 0.5
        rad = min(w, h) * 0.06 * self.zoom
        scene.no_stroke()
        for i in range(5):
            t = i / 4.0
            glow_r = rad * (1.35 + t * 2.0 + 0.25 * align_pulse)
            alpha = 0.26 * (1.0 - t) ** 1.5
            scene.fill(self.core_glow_color[0], self.core_glow_color[1], self.core_glow_color[2], alpha)
            scene.ellipse(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2)

        # Draw rings
        for ring in self.rings:
            pts3d = ring.points3d()
            pts2d = []
            for p in pts3d:
                x, y = self._project(p)
                pts2d.append((x, y, p[2]))
            base_r, base_g, base_b = ring.color

            scene.stroke_weight(self.base_thickness * thickness_scale * 2.0)
            for i in range(len(pts2d)):
                x0, y0, z0 = pts2d[i]
                x1, y1, z1 = pts2d[(i + 1) % len(pts2d)]
                depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, z0 / max(0.0001, ring.R)))
                shade = 0.68 + 0.32 * depth_mix
                scene.stroke(base_r * shade, base_g * shade, base_b * shade, min(1.0, 0.2 * glow_scale))
                scene.line(x0, y0, x1, y1)

            scene.stroke_weight(self.base_thickness * thickness_scale)
            for i in range(len(pts2d)):
                x0, y0, z0 = pts2d[i]
                x1, y1, z1 = pts2d[(i + 1) % len(pts2d)]
                depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, z0 / max(0.0001, ring.R)))
                shade = 0.72 + 0.28 * depth_mix
                alpha = min(1.0, 0.5 + 0.45 * depth_mix + alpha_boost)
                scene.stroke(base_r * shade, base_g * shade, base_b * shade, alpha)
                scene.line(x0, y0, x1, y1)

            scene.stroke_weight(self.base_thickness * thickness_scale * 0.7)
            for i in range(len(pts2d)):
                if (i + ring.glyph_phase) % ring.glyph_stride != 0:
                    continue
                x0, y0, z0 = pts2d[i]
                x1, y1, z1 = pts2d[(i + 1) % len(pts2d)]
                depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, z0 / max(0.0001, ring.R)))
                if depth_mix < 0.35:
                    continue
                shade = 0.92 + 0.2 * depth_mix
                scene.stroke(
                    min(1.0, base_r * shade + 0.1),
                    min(1.0, base_g * shade + 0.1),
                    min(1.0, base_b * shade + 0.1),
                    min(1.0, 0.9 + alpha_boost),
                )
                scene.line(x0, y0, x1, y1)

        # Auxiliary node
        if self.rings:
            orbit_r = self.rings[0].R * 0.9
            pos = (
                orbit_r * math.cos(self.aux_phase),
                orbit_r * 0.35 * math.sin(self.aux_phase * 0.7),
                orbit_r * 0.6 * math.sin(self.aux_phase),
            )
            ax, ay = self._project(pos)
            node_r = max(4.0, rad * 0.3)
            scene.no_stroke()
            scene.fill(self.accent_teal[0], self.accent_teal[1], self.accent_teal[2], 0.16)
            scene.ellipse(ax - node_r * 2.4, ay - node_r * 2.4, node_r * 4.8, node_r * 4.8)
            scene.fill(self.accent_teal[0], self.accent_teal[1], self.accent_teal[2], 0.6)
            scene.ellipse(ax - node_r, ay - node_r, node_r * 2, node_r * 2)
            scene.fill(0.95, 1.0, 1.0, 0.45)
            scene.ellipse(ax - node_r * 0.32, ay - node_r * 0.32, node_r * 0.64, node_r * 0.64)

        # Core body
        scene.no_stroke()
        scene.fill(self.core_color[0], self.core_color[1], self.core_color[2], 1.0)
        scene.ellipse(cx - rad, cy - rad, rad * 2, rad * 2)
        highlight_r = rad * 0.38
        scene.fill(1.0, 1.0, 1.0, 0.5)
        scene.ellipse(cx - rad * 0.35 - highlight_r, cy - rad * 0.35 - highlight_r,
                      highlight_r * 2, highlight_r * 2)

        # HUD buttons
        for btn in self.buttons:
            rect = btn['rect']
            scene.fill(0.1, 0.12, 0.16, 0.75)
            scene.stroke(0.45, 0.48, 0.55, 0.9)
            scene.stroke_weight(1)
            scene.rect(rect.x, rect.y, rect.w, rect.h)
            scene.fill(0.9, 0.9, 0.95, 1.0)
            scene.text(btn['label'], 'Helvetica', 12, rect.x + rect.w * 0.5, rect.y + rect.h * 0.38, 5)

        # HUD text
        info = f"{len(self.rings)} rings • align {self.reset_period:.1f}s • zoom {self.zoom:.2f}"
        scene.fill(0.9, 0.9, 0.95)
        scene.text(info, 'Helvetica', 12, w * 0.5, 20, 5)


def main():
    scene.run(GyroPulseScene(), show_fps=False)


if __name__ == '__main__':
    main()
