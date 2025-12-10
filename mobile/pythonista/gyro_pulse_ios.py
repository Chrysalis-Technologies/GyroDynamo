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
import colorsys
import scene
import ui


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

    def points3d(self):
        pts = []
        two_pi = 2.0 * math.pi
        for i in range(self.n):
            t = two_pi * i / self.n
            p = (self.R * math.cos(t), self.R * math.sin(t), 0.0)
            p = rot_z(p, self.spin)
            p = rot_x(p, self.tilt_x)
            p = rot_y(p, self.tilt_y)
            pts.append(p)
        return pts


class GyroPulseScene(scene.Scene):
    def setup(self):
        self.reset_period = 10.0
        self.align_width = 0.05  # fraction of cycle for flash
        self.elapsed = 0.0
        self.paused = False
        self.zoom = 1.0
        self.base_thickness = 3.0
        self.bg_top = (0.03, 0.04, 0.10)
        self.bg_bottom = (0.04, 0.07, 0.14)
        self.buttons = []
        self._build_buttons()
        self.rings = []
        self._init_rings()

    # ---------- Ring setup ----------
    def _make_ring(self, idx, R):
        sign = 1 if idx % 2 == 0 else -1
        spin_ratio = sign * (idx + 1)
        tx_ratio = sign * (idx + 1)
        ty_ratio = sign * (idx + 2)
        hue = (0.16 * idx) % 1.0
        color = colorsys.hsv_to_rgb(hue, 0.8, 1.0)
        n_pts = max(120, int(280 * R))
        return Ring(R, color, n_points=n_pts, spin_ratio=spin_ratio, tx_ratio=tx_ratio, ty_ratio=ty_ratio)

    def _init_rings(self):
        for idx, r in enumerate([1.0, 0.8, 0.62, 0.46]):
            self.rings.append(self._make_ring(idx, r))

    def _reindex(self):
        self.rings.sort(key=lambda r: r.R, reverse=True)
        for idx, r in enumerate(self.rings):
            sign = 1 if idx % 2 == 0 else -1
            r.spin_ratio = sign * (idx + 1)
            r.tx_ratio = sign * (idx + 1)
            r.ty_ratio = sign * (idx + 2)
            r.base_radius = r.R

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
        actions = ['add_inner', 'add_outer', 'remove', 'period_down', 'period_up', 'zoom_out', 'zoom_in']
        x = 14
        for lbl, act in zip(labels, actions):
            self.buttons.append({'rect': ui.Rect(x, 12, 52, 30), 'label': lbl, 'action': act})
            x += 56

    def _hit_button(self, touch):
        for btn in self.buttons:
            if btn['rect'].contains_point(touch.location.x, self.size.h - touch.location.y):
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
        if not self.rings:
            return (1.0, 1.0, 1.0)
        cols = []
        wts = []
        for r in self.rings:
            cols.append(r.color)
            wts.append(1.0 / max(0.1, r.R))
        tot = sum(wts) or 1.0
        return (
            sum(c[0] * w for c, w in zip(cols, wts)) / tot,
            sum(c[1] * w for c, w in zip(cols, wts)) / tot,
            sum(c[2] * w for c, w in zip(cols, wts)) / tot,
        )

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

    def draw(self):
        w, h = self.size
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

        # Draw rings
        scene.stroke_weight(self.base_thickness * thickness_scale)
        for ring in self.rings:
            pts3d = ring.points3d()
            pts2d = [self._project(p) for p in pts3d]
            path = ui.Path()
            path.move_to(*pts2d[0])
            for p in pts2d[1:]:
                path.line_to(*p)
            path.close()

            r, g, b = ring.color
            a = min(1.0, max(0.1, 0.4 + alpha_boost))
            scene.stroke(r, g, b, a)
            scene.fill(0, 0, 0, 0)
            scene.draw_path(path)

            # Glow
            scene.stroke(r, g, b, min(1.0, a * 0.4 * glow_scale))
            scene.stroke_weight(self.base_thickness * thickness_scale * 2.0)
            scene.draw_path(path)
            scene.stroke_weight(self.base_thickness * thickness_scale)

        # Center sphere
        base_c = self._center_color()
        cx, cy = w * 0.5, h * 0.5
        rad = min(w, h) * 0.06 * self.zoom
        scene.fill(base_c[0], base_c[1], base_c[2], 0.8)
        scene.stroke(base_c[0] * 0.6, base_c[1] * 0.6, base_c[2] * 0.6, 0.9)
        scene.stroke_weight(2)
        scene.ellipse(cx - rad, cy - rad, rad * 2, rad * 2)

        # HUD buttons
        for btn in self.buttons:
            rect = btn['rect']
            scene.fill(0.1, 0.12, 0.16, 0.75)
            scene.stroke(0.45, 0.48, 0.55, 0.9)
            scene.stroke_weight(1)
            scene.rect(rect.x, h - rect.y - rect.h, rect.w, rect.h)
            scene.fill(0.9, 0.9, 0.95, 1.0)
            scene.text(btn['label'], 'Helvetica', 12, rect.x + rect.w * 0.5, h - rect.y - rect.h * 0.62, 5)

        # HUD text
        info = f"{len(self.rings)} rings • align {self.reset_period:.1f}s • zoom {self.zoom:.2f}"
        scene.fill(0.9, 0.9, 0.95)
        scene.text(info, 'Helvetica', 12, w * 0.5, 20, 5)


def main():
    scene.run(GyroPulseScene(), show_fps=False)


if __name__ == '__main__':
    main()
