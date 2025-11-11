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
                 spin_ratio=1, tx_ratio=1, ty_ratio=1):
        self.R = radius
        self.color = color  # (r,g,b) 0..1
        self.n = n_points

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
        for i in range(self.n):
            t = two_pi * i / self.n
            p = (self.R * math.cos(t), self.R * math.sin(t), 0.0)
            p = rot_z(p, self.spin)
            p = rot_x(p, self.tilt_x)
            p = rot_y(p, self.tilt_y)
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
        self.rings = [
            GyroRing(1.06, (1.00, 0.30, 0.30), spin_ratio=5,  tx_ratio=2, ty_ratio=3),
            GyroRing(0.84, (0.35, 0.85, 1.00), spin_ratio=7,  tx_ratio=3, ty_ratio=5),
            GyroRing(0.62, (0.40, 1.00, 0.58), spin_ratio=9,  tx_ratio=4, ty_ratio=7),
            GyroRing(0.44, (1.00, 0.74, 0.35), spin_ratio=11, tx_ratio=5, ty_ratio=9),
        ]

        # Drawing params
        self.base_thickness = 2.6
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
        segs_back, segs_front = [], []
        n = ring.n
        for i in range(n):
            p0 = pts3d[i]
            p1 = pts3d[(i + 1) % n]
            z_avg = 0.5 * (p0[2] + p1[2])
            x0, y0 = self.project(p0)
            x1, y1 = self.project(p1)
            (segs_back if z_avg < 0 else segs_front).append((x0, y0, x1, y1))

        # Back (far) segments
        stroke_weight(self.base_thickness * thickness_scale)
        stroke(ring.color[0], ring.color[1], ring.color[2], max(0.0, min(1.0, self.back_alpha)))
        for x0, y0, x1, y1 in segs_back:
            line(x0, y0, x1, y1)

        # Front (near) segments with a slight alpha “pulse”
        stroke(ring.color[0], ring.color[1], ring.color[2],
               max(0.0, min(1.0, self.front_alpha + alpha_boost)))
        for x0, y0, x1, y1 in segs_front:
            line(x0, y0, x1, y1)

    def draw(self):
        # Background + subtle vignette
        background(0, 0, 0)
        no_stroke()
        fill(0.05, 0.05, 0.08, 0.18)
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

        # Draw rings outer → inner
        for r in self.rings:
            self.draw_ring(r, thickness_scale=thickness_scale, alpha_boost=alpha_boost)

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
