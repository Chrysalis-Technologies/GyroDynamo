# Pythonista (iOS) — Tempo‐locked Gyroscopic Rings
# Larger rendering + motion synchronized to a target BPM (visual “resonance” on each measure).
# Edit TARGET_BPM and BEATS_PER_MEASURE below. Tap screen to pause/resume.

"""Pythonista scene that mirrors the desktop GoGoGyro experience on phones.

The desktop build (``GoGoGyroDesktop.py``) recently gained rhythm-driven
touches—measure-synced alpha pops, beat pulses, and smooth BPM easing.  This
module recreates the same behaviour using the ``scene`` module so the animation
looks and feels identical on iPhone/iPad.

Gestures
========
* Single tap: toggle pause / resume.
* Two-finger tap: bump the target BPM up by 5.
* Three-finger tap: bump the target BPM down by 5.

Touch handling keeps track of active touches so that quick multitouch gestures
reliably map to the BPM nudges without accidentally toggling pause.
"""

from scene import *
import math
import random

# ------------------------
# Orbital sun core palette
# ------------------------
# Helios / Orbital Sun Core palette
CORE_COLOR = (0.98, 0.99, 1.0)
CORE_GLOW = (0.62, 0.8, 1.0)
RING_GOLD = (0.93, 0.76, 0.30)
ACCENT_TEAL = (0.18, 0.74, 0.7)
BG_DEEP = (0.02, 0.03, 0.05)
BG_HALO = (0.06, 0.08, 0.14)

# ========================
# Tempo / Rhythm Settings
# ========================
TARGET_BPM = 96              # visual rhythm (beats per minute)
BEATS_PER_MEASURE = 8        # rings all realign every measure
BPM_SMOOTHING = 4.0          # how quickly current BPM eases to TARGET_BPM
SHOW_HUD = True              # display BPM/beat info at the bottom of the screen

# ========================
# 3D rotation helpers
# ========================
def rot_x(p, a):
    x, y, z = p
    ca, sa = math.cos(a), math.sin(a)
    return (x, y*ca - z*sa, y*sa + z*ca)

def rot_y(p, a):
    x, y, z = p
    ca, sa = math.cos(a), math.sin(a)
    return (x*ca + z*sa, y, -x*sa + z*ca)

def rot_z(p, a):
    x, y, z = p
    ca, sa = math.cos(a), math.sin(a)
    return (x*ca - y*sa, x*sa + y*ca, z)

# ========================
# Ring model (tempo-locked)
# ========================
class GyroRing:
    def __init__(self, radius, color, n_points=240,
                 spin_ratio=1, tx_ratio=1, ty_ratio=1, offset=None):
        self.R = radius
        self.color = color  # (r,g,b) 0..1
        self.n = n_points
        self.offset = offset if offset is not None else (0.0, 0.0, 0.0)
        self.glyph_stride = random.choice([9, 11, 13])
        self.glyph_phase = random.randrange(self.glyph_stride)

        # Orientation state
        self.tilt_x = random.uniform(-0.3, 0.3)
        self.tilt_y = random.uniform(-0.3, 0.3)
        self.spin   = random.uniform(0, 2*math.pi)

        # Tempo-locked ratios (integers recommended for clean realignment)
        self.spin_ratio = spin_ratio
        self.tx_ratio   = tx_ratio
        self.ty_ratio   = ty_ratio

    def update(self, dt, omega_bar):
        # Lock angular velocities to multiples of the bar angular frequency.
        self.spin   += (self.spin_ratio * omega_bar) * dt
        self.tilt_x += (self.tx_ratio   * omega_bar) * dt
        self.tilt_y += (self.ty_ratio   * omega_bar) * dt

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

# ========================
# Scene
# ========================
class GimbalRings(Scene):
    def setup(self):
        self.paused = False
        self.elapsed = 0.0
        self.target_bpm = float(TARGET_BPM)
        self.cur_bpm = float(TARGET_BPM)
        self.beats_per_measure = BEATS_PER_MEASURE

        # Track active touches so we can tell single taps from multitouch BPM nudges.
        self._active_touches = {}
        self._pending_single_tap = None

        w, h = self.size
        self.cx, self.cy = w * 0.5, h * 0.5

        # Slightly larger overall scale (compared to previous script)
        self.scale_px = min(w, h) * 0.55

        # Camera/focal settings (unit-space)
        self.cam_dist = 3.5
        self.focal_len = 1.0

        # Rings: choose relatively prime-ish integer ratios so
        # rich polyrhythms emerge *within* the bar but realign each measure.
        ring_specs = [
            (1.06, 5, 2, 3),
            (0.84, 7, 3, 5),
            (0.62, 9, 4, 7),
            (0.44, 11, 5, 9),
        ]
        tones = [1.0, 0.94, 0.88, 0.82]
        self.rings = []
        for idx, (radius, spin_ratio, tx_ratio, ty_ratio) in enumerate(ring_specs):
            tone = tones[idx % len(tones)]
            color = tuple(min(1.0, c * tone) for c in RING_GOLD)
            jitter = 0.06
            offset = (
                random.uniform(-jitter, jitter) * radius,
                random.uniform(-jitter * 0.6, jitter * 0.6) * radius,
                random.uniform(-jitter, jitter) * radius,
            )
            self.rings.append(
                GyroRing(
                    radius,
                    color,
                    spin_ratio=spin_ratio,
                    tx_ratio=tx_ratio,
                    ty_ratio=ty_ratio,
                    offset=offset,
                )
            )

        # Drawing params
        self.base_thickness = 2.2
        self.back_alpha = 0.35
        self.front_alpha = 0.98

        if SHOW_HUD:
            self.hud = LabelNode(
                "",
                position=(self.size.w * 0.5, 22),
                anchor_point=(0.5, 0.5),
                color=(1.0, 1.0, 1.0, 0.8),
                font=('Menlo', 12),
                parent=self,
            )
        else:
            self.hud = None

    # --------- Tempo helpers ---------
    def bar_omega(self):
        # Angular frequency of a full measure (bar): 2π per measure.
        bar_rate = (self.cur_bpm / 60.0) / self.beats_per_measure  # measures per second
        return 2.0 * math.pi * bar_rate

    def beat_phase(self):
        # 0..1 within current beat
        beats_total = self.elapsed * (self.cur_bpm / 60.0)
        return beats_total - math.floor(beats_total)

    def measure_phase(self):
        # 0..1 within current measure
        beats_total = self.elapsed * (self.cur_bpm / 60.0)
        measures_total = beats_total / self.beats_per_measure
        return measures_total - math.floor(measures_total)

    def pulse(self, x, sharpness=3.0):
        # Symmetric pulse peaking at phase 0 (and 1), falling to 0 at phase 0.5
        # sharpness controls how “snappy” the pulse feels.
        # cos-based, then shaped:
        v = 0.5 * (1.0 + math.cos(2.0 * math.pi * x))
        return max(0.0, min(1.0, v ** sharpness))

    # --------- Engine ---------
    def update(self):
        if self.paused:
            return
        dt = self.dt if self.dt else 1/60.0
        self.elapsed += dt

        # Ease current BPM toward target BPM for smooth transitions
        self.cur_bpm += (self.target_bpm - self.cur_bpm) * min(1.0, BPM_SMOOTHING * dt)

        omega_bar = self.bar_omega()
        for r in self.rings:
            r.update(dt, omega_bar)

    # --------- Projection & drawing ---------
    def project(self, p):
        x, y, z = p
        denom = (z + self.cam_dist)
        if denom < 0.1:
            denom = 0.1
        u = (self.focal_len * x) / denom
        v = (self.focal_len * y) / denom
        return (self.cx + u * self.scale_px, self.cy + v * self.scale_px)

    def draw_ring(self, ring: GyroRing, thickness_scale=1.0, alpha_boost=0.0):
        pts3d = ring.ring_points_3d()
        segments = []
        n = ring.n
        for i in range(n):
            p0 = pts3d[i]
            p1 = pts3d[(i + 1) % n]
            z_avg = 0.5 * (p0[2] + p1[2])
            depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, z_avg))
            x0, y0 = self.project(p0)
            x1, y1 = self.project(p1)
            segments.append((z_avg, depth_mix, i, x0, y0, x1, y1))

        # Draw back-to-front for cleaner occlusion.
        segments.sort(key=lambda s: s[0])

        # Glow pass
        stroke_weight(self.base_thickness * thickness_scale * 2.1)
        for _, depth_mix, _, x0, y0, x1, y1 in segments:
            shade = 0.68 + 0.3 * depth_mix
            r = min(1.0, ring.color[0] * shade)
            g = min(1.0, ring.color[1] * shade)
            b = min(1.0, ring.color[2] * shade)
            a = (self.back_alpha + (self.front_alpha - self.back_alpha) * depth_mix) * 0.25
            stroke(r, g, b, max(0.0, min(1.0, a)))
            line(x0, y0, x1, y1)

        # Base pass
        stroke_weight(self.base_thickness * thickness_scale)
        for _, depth_mix, _, x0, y0, x1, y1 in segments:
            shade = 0.72 + 0.35 * depth_mix
            r = min(1.0, ring.color[0] * shade)
            g = min(1.0, ring.color[1] * shade)
            b = min(1.0, ring.color[2] * shade)
            alpha = self.back_alpha + (self.front_alpha - self.back_alpha) * depth_mix + alpha_boost
            stroke(r, g, b, max(0.0, min(1.0, alpha)))
            line(x0, y0, x1, y1)

        # Glyph pass (etched ticks)
        stroke_weight(self.base_thickness * thickness_scale * 0.65)
        for _, depth_mix, idx, x0, y0, x1, y1 in segments:
            if (idx + ring.glyph_phase) % ring.glyph_stride != 0 or depth_mix < 0.35:
                continue
            shade = 0.95 + 0.25 * depth_mix
            r = min(1.0, ring.color[0] * shade + 0.12)
            g = min(1.0, ring.color[1] * shade + 0.12)
            b = min(1.0, ring.color[2] * shade + 0.12)
            alpha = min(1.0, self.front_alpha + alpha_boost + 0.2)
            stroke(r, g, b, alpha)
            line(x0, y0, x1, y1)

    def _core_radius_px(self):
        if self.rings:
            inner = self.rings[-1]
            px, _ = self.project((inner.R, 0, 0))
            return max(10, int(abs(px - self.cx) * 0.45))
        return int(min(self.size) * 0.08)

    def draw_core_glow(self, pulse=0.0):
        r = self._core_radius_px()
        no_stroke()
        for i in range(5):
            t = i / 4.0
            glow_r = r * (1.3 + t * 2.0 + 0.25 * pulse)
            alpha = 0.26 * (1.0 - t) ** 1.5
            fill(CORE_GLOW[0], CORE_GLOW[1], CORE_GLOW[2], alpha)
            ellipse(self.cx - glow_r, self.cy - glow_r, glow_r * 2, glow_r * 2)

    def draw_core_body(self):
        r = self._core_radius_px()
        no_stroke()
        fill(CORE_COLOR[0], CORE_COLOR[1], CORE_COLOR[2], 1.0)
        ellipse(self.cx - r, self.cy - r, r * 2, r * 2)
        highlight_r = r * 0.38
        fill(1.0, 1.0, 1.0, 0.5)
        ellipse(
            self.cx - r * 0.35 - highlight_r,
            self.cy - r * 0.35 - highlight_r,
            highlight_r * 2,
            highlight_r * 2,
        )

    def draw_aux_node(self):
        if not self.rings:
            return
        t = self.elapsed * 0.35
        orbit_r = self.rings[0].R * 0.9
        pos = (
            orbit_r * math.cos(t),
            orbit_r * 0.35 * math.sin(t * 0.7),
            orbit_r * 0.6 * math.sin(t),
        )
        x, y = self.project(pos)
        r = max(4, int(self._core_radius_px() * 0.3))
        no_stroke()
        fill(ACCENT_TEAL[0], ACCENT_TEAL[1], ACCENT_TEAL[2], 0.16)
        ellipse(x - r * 2.4, y - r * 2.4, r * 4.8, r * 4.8)
        fill(ACCENT_TEAL[0], ACCENT_TEAL[1], ACCENT_TEAL[2], 0.6)
        ellipse(x - r, y - r, r * 2, r * 2)
        fill(0.95, 1.0, 1.0, 0.45)
        ellipse(x - r * 0.32, y - r * 0.32, r * 0.64, r * 0.64)
        no_fill()
        stroke(ACCENT_TEAL[0], ACCENT_TEAL[1], ACCENT_TEAL[2], 0.25)
        stroke_weight(1.0)
        ellipse(x - r * 1.4, y - r * 1.4, r * 2.8, r * 2.8)

    def draw(self):
        # Background + subtle vignette
        background(BG_DEEP[0], BG_DEEP[1], BG_DEEP[2])
        no_stroke()
        fill(BG_HALO[0], BG_HALO[1], BG_HALO[2], 0.22)
        d = min(self.size) * 1.02
        ellipse(self.cx - d/2, self.cy - d/2, d, d)

        # Beat/measure pulses: emphasize rhythm and “culmination” on each measure
        bph = self.beat_phase()
        mph = self.measure_phase()
        beat_pulse    = self.pulse(bph, sharpness=3.5)     # quick tick each beat
        measure_pulse = self.pulse(mph, sharpness=2.5)     # bigger glow on the downbeat

        # Slight breathing of thickness with measure, alpha pop with beat
        thickness_scale = 1.0 + 0.25 * measure_pulse
        alpha_boost = 0.06 * beat_pulse + 0.12 * measure_pulse

        self.draw_core_glow(pulse=measure_pulse)

        # Draw rings outer → inner
        for r in self.rings:
            self.draw_ring(r, thickness_scale=thickness_scale, alpha_boost=alpha_boost)

        self.draw_aux_node()
        self.draw_core_body()

        if self.hud is not None:
            beat_idx = int(bph * self.beats_per_measure) % self.beats_per_measure + 1
            self.hud.text = (
                f"{self.cur_bpm:5.1f} BPM  |  M:{self.beats_per_measure}  |  beat:{beat_idx}"
            )

    # --------- Interaction ---------
    def touch_began(self, touch):
        # Register the new touch and decide which gesture to trigger.  We delay
        # pausing until the touch ends so that multi-finger taps don't cause a
        # spurious toggle.
        self._active_touches[touch.touch_id] = touch

        if touch.tap_count >= 2:
            self.paused = not self.paused
            self._pending_single_tap = None
            return

        active = len(self._active_touches)
        if active == 1:
            # Remember this touch; if no other fingers join before it ends we
            # treat it as a single tap.
            self._pending_single_tap = touch.touch_id
        elif active == 2:
            self._pending_single_tap = None
            self.target_bpm = min(300.0, self.target_bpm + 5.0)
        elif active >= 3:
            self._pending_single_tap = None
            self.target_bpm = max(20.0, self.target_bpm - 5.0)

    def touch_moved(self, touch):
        if touch.touch_id in self._active_touches:
            self._active_touches[touch.touch_id] = touch

    def touch_ended(self, touch):
        self._active_touches.pop(touch.touch_id, None)
        if self._pending_single_tap == touch.touch_id:
            self.paused = not self.paused
        if not self._active_touches:
            self._pending_single_tap = None

    # Some iOS devices may deliver cancelled touches (e.g. incoming phone call).
    touch_cancelled = touch_ended


if __name__ == '__main__':
    run(GimbalRings(), show_fps=True, multi_touch=True)
