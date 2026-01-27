# tumbling_gyro_rings_gradients_bpm_haptics_pulse.py
# Tumbling gradient rings with alternating shading,
# haptic + visual pulse synced to BPM.

import math, time, ui, random
from scene import (
    Scene,
    stroke,
    stroke_weight,
    line,
    background,
    fill,
    ellipse,
    no_stroke,
    get_screen_size,
    Vector2,
    SceneView,
)
from objc_util import ObjCClass

# ---------------- Haptics ----------------
UIImpactFeedbackGenerator = ObjCClass('UIImpactFeedbackGenerator')
impact_medium = UIImpactFeedbackGenerator.alloc().initWithStyle_(1)  # 1 = medium
impact_medium.prepare()

def haptic_pulse():
    impact_medium.impactOccurred()
    impact_medium.prepare()

# ---------------- Config ----------------
BG = (0.02, 0.03, 0.05)
DEFAULT_RING_COUNT = 7
BASE_RADIUS_FACTOR = 0.07
SPACING_TARGET = 46.0
SEGMENTS = 160
CAMERA_D = 900.0

LINE_THICKNESS = 2.0
BACK_ALPHA = 0.25
FRONT_ALPHA = 1.0

# Helios / Orbital Sun Core palette
RING_GOLD = (0.93, 0.76, 0.30)
CORE_COLOR = (0.98, 0.99, 1.0)
CORE_GLOW = (0.62, 0.8, 1.0)
ACCENT_TEAL = (0.18, 0.74, 0.7)
PALETTE = [
    (0.94, 0.79, 0.34),
    (0.9, 0.75, 0.3),
    (0.86, 0.71, 0.28),
    (0.82, 0.67, 0.26),
]

# ---------------- Pulse curve ----------------
def pulse_curve(t, length=0.3):
    """Strength 0..1 for time since last pulse, decays over 'length' seconds."""
    if t < 0 or t > length:
        return 0.0
    # cosine fade-out
    return math.cos((t / length) * math.pi * 0.5) ** 2

# --------------- Math helpers ---------------
def norm(v):
    x, y, z = v
    m = math.sqrt(x*x + y*y + z*z) or 1.0
    return (x/m, y/m, z/m)

def rot_axis(v, k, a):
    vx, vy, vz = v
    kx, ky, kz = k
    c = math.cos(a); s = math.sin(a); one_c = 1.0 - c
    cx = ky*vz - kz*vy
    cy = kz*vx - kx*vz
    cz = kx*vy - ky*vx
    dot = kx*vx + ky*vy + kz*vz
    rx = vx*c + cx*s + kx*dot*one_c
    ry = vy*c + cy*s + ky*dot*one_c
    rz = vz*c + cz*s + kz*dot*one_c
    return (rx, ry, rz)

def proj(x, y, z, d=CAMERA_D):
    f = d / (d + z)
    return (x * f, y * f, z)

def circle_points(radius, seg=SEGMENTS):
    for i in range(seg):
        t = (i / float(seg)) * (2.0 * math.pi)
        yield (radius * math.cos(t), radius * math.sin(t), 0.0), t

# --------------- Scene ---------------
class TumblingGyroGradient(Scene):
    def __init__(self):
        super().__init__()
        self.bpm = 120.0
        self._last_pulse_time = 0.0
        self._aligned_prev = False
        self._outer_aligned_prev = False
        self.speed_factor = 1.0
        self.paused = False
        self.ring_count = DEFAULT_RING_COUNT
        self.aux_phase = 0.0

    def setup(self):
        self.background_color = BG
        self.center = Vector2(self.size.w / 2, self.size.h / 2)
        self.min_dim = min(self.size.w, self.size.h)
        self.build_rings()

    def build_rings(self):
        base_r = self.min_dim * BASE_RADIUS_FACTOR
        max_outer = (self.min_dim * 0.5) - 20.0
        spacing = SPACING_TARGET
        if self.ring_count > 1:
            spacing = min(SPACING_TARGET, max(0.0, (max_outer - base_r)) / (self.ring_count - 1))

        axes = [
            norm((1.0, 0.2, 0.0)),
            norm((0.0, 1.0, 0.25)),
            norm((0.35, 0.25, 1.0)),
            norm((1.0, 1.0, 0.0)),
            norm((0.0, 1.0, 1.0)),
            norm((1.0, 0.0, 1.0)),
            norm((0.5, 0.8, 0.25)),
        ]

        self.rings = []
        for i in range(self.ring_count):
            r = base_r + i * spacing
            axis = axes[i % len(axes)]
            color = PALETTE[i % len(PALETTE)]
            omega = (0.6 + 0.25 * i) * (1 if i % 2 == 0 else -1)
            offset = (
                random.uniform(-0.06, 0.06) * r,
                random.uniform(-0.04, 0.04) * r,
                random.uniform(-0.06, 0.06) * r,
            )
            glyph_stride = random.choice([9, 11, 13])
            glyph_phase = random.randrange(glyph_stride)
            self.rings.append({
                'radius': r,
                'axis': axis,
                'angle': 0.0,
                'omega': omega,
                'color': color,
                'shade_dir': 1 if i % 2 == 0 else -1,
                'offset': offset,
                'glyph_stride': glyph_stride,
                'glyph_phase': glyph_phase,
            })
        self._last = time.time()

    def set_ring_count(self, count):
        self.ring_count = max(1, int(count))
        self.build_rings()

    def update(self):
        if self.paused: return
        now = time.time()
        dt = now - self._last
        self._last = now
        if dt <= 0: return
        aligned = True
        outer_aligned = False
        eps = 0.01
        for idx, ring in enumerate(self.rings):
            ring['angle'] = (ring['angle'] + ring['omega'] * dt * self.speed_factor) % math.tau
            a = ring['angle']
            if idx == len(self.rings) - 1:
                if a < eps or a > math.tau - eps:
                    outer_aligned = True
            if not (a < eps or a > math.tau - eps):
                aligned = False

        self.aux_phase = (self.aux_phase + dt * 0.35 * self.speed_factor) % math.tau

        if outer_aligned and not self._outer_aligned_prev:
            haptic_pulse()
            self._last_pulse_time = now
        elif aligned and not self._aligned_prev:
            haptic_pulse()
            self._last_pulse_time = now
        self._outer_aligned_prev = outer_aligned
        self._aligned_prev = aligned

    def draw_ring(self, ring, pulse_strength):
        pts3d = []
        for (x, y, z), t in circle_points(ring['radius']):
            X, Y, Z = rot_axis((x, y, z), ring['axis'], ring['angle'])
            X += ring['offset'][0]
            Y += ring['offset'][1]
            Z += ring['offset'][2]
            px, py, pz = proj(X, Y, Z)
            pts3d.append((px + self.center.x, py + self.center.y, pz, t))

        n = len(pts3d)
        stroke_weight(LINE_THICKNESS * (1.0 + 0.6 * pulse_strength))
        for i in range(n):
            p0 = pts3d[i]
            p1 = pts3d[(i+1) % n]
            phase = (p0[3] / (2.0 * math.pi))
            if ring['shade_dir'] == -1:
                phase = 1.0 - phase
            depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, p0[2] / max(1.0, ring['radius'])))
            alpha = (BACK_ALPHA + (FRONT_ALPHA - BACK_ALPHA) * depth_mix) * (1.0 + 0.4 * pulse_strength)
            shade = 0.6 + 0.25 * phase + 0.25 * depth_mix
            stroke(
                min(1.0, ring['color'][0] * shade),
                min(1.0, ring['color'][1] * shade),
                min(1.0, ring['color'][2] * shade),
                min(1.0, alpha),
            )
            line(p0[0], p0[1], p1[0], p1[1])

        stroke_weight(max(1.0, LINE_THICKNESS * 0.7))
        for i in range(n):
            if (i + ring['glyph_phase']) % ring['glyph_stride'] != 0:
                continue
            p0 = pts3d[i]
            p1 = pts3d[(i+1) % n]
            depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, p0[2] / max(1.0, ring['radius'])))
            if depth_mix < 0.35:
                continue
            shade = 0.9 + 0.2 * depth_mix
            stroke(
                min(1.0, ring['color'][0] * shade + 0.1),
                min(1.0, ring['color'][1] * shade + 0.1),
                min(1.0, ring['color'][2] * shade + 0.1),
                min(1.0, 0.85 + 0.2 * pulse_strength),
            )
            line(p0[0], p0[1], p1[0], p1[1])

    def draw_core(self, pulse_strength):
        r = self.min_dim * 0.06
        no_stroke()
        for i in range(5):
            t = i / 4.0
            glow_r = r * (1.35 + t * 2.0 + 0.25 * pulse_strength)
            alpha = 0.26 * (1.0 - t) ** 1.5
            fill(CORE_GLOW[0], CORE_GLOW[1], CORE_GLOW[2], alpha)
            ellipse(self.center.x - glow_r, self.center.y - glow_r, glow_r * 2, glow_r * 2)
        fill(CORE_COLOR[0], CORE_COLOR[1], CORE_COLOR[2], 1.0)
        ellipse(self.center.x - r, self.center.y - r, r * 2, r * 2)
        highlight_r = r * 0.38
        fill(1.0, 1.0, 1.0, 0.5)
        ellipse(
            self.center.x - r * 0.35 - highlight_r,
            self.center.y - r * 0.35 - highlight_r,
            highlight_r * 2,
            highlight_r * 2,
        )

    def draw_aux_node(self):
        if not self.rings:
            return
        orbit_r = self.rings[-1]['radius'] * 0.85
        px, py, _ = proj(
            orbit_r * math.cos(self.aux_phase),
            orbit_r * 0.35 * math.sin(self.aux_phase * 0.7),
            orbit_r * 0.6 * math.sin(self.aux_phase),
        )
        x = self.center.x + px
        y = self.center.y + py
        r = max(4.0, self.min_dim * 0.013)
        no_stroke()
        fill(ACCENT_TEAL[0], ACCENT_TEAL[1], ACCENT_TEAL[2], 0.16)
        ellipse(x - r * 2.4, y - r * 2.4, r * 4.8, r * 4.8)
        fill(ACCENT_TEAL[0], ACCENT_TEAL[1], ACCENT_TEAL[2], 0.6)
        ellipse(x - r, y - r, r * 2, r * 2)
        fill(0.95, 1.0, 1.0, 0.45)
        ellipse(x - r * 0.32, y - r * 0.32, r * 0.64, r * 0.64)

    def draw(self):
        background(*BG)
        now = time.time()
        pulse_strength = pulse_curve(now - self._last_pulse_time, length=0.3)
        for ring in self.rings:
            self.draw_ring(ring, pulse_strength)
        self.draw_aux_node()
        self.draw_core(pulse_strength)

    def touch_began(self, touch):
        self.paused = not self.paused
        haptic_pulse()
        self._last_pulse_time = time.time()

# --------------- UI Wrapper ---------------
class MainView(ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = 'Tumbling Rings with BPM Pulses'
        self.bg_color = 'black'

        self.scene_view = SceneView(frame=(0, 0, self.width, self.height-100), flex='WH')
        self.scene = TumblingGyroGradient()
        self.scene_view.scene = self.scene
        self.add_subview(self.scene_view)

        # Speed slider
        self.slider = ui.Slider(frame=(10, self.height-90, self.width-20, 30), flex='WT')
        self.slider.action = self.slider_changed
        self.slider.value = 0.5
        self.add_subview(self.slider)

        # BPM text field
        self.bpm_field = ui.TextField(frame=(10, self.height-50, 100, 30), flex='WT')
        self.bpm_field.text = str(int(self.scene.bpm))
        self.bpm_field.action = self.bpm_changed
        self.bpm_field.keyboard_type = ui.KEYBOARD_NUMBER_PAD
        self.add_subview(self.bpm_field)

        self.add_subview(ui.Label(frame=(120, self.height-50, 80, 30),
                                  text='BPM', text_color='white', alignment=ui.ALIGN_LEFT))

        # Ring count stepper
        self.ring_label = ui.Label(frame=(200, self.height-50, 60, 30),
                                   text='Rings', text_color='white', alignment=ui.ALIGN_LEFT)
        self.add_subview(self.ring_label)
        self.ring_stepper = ui.Stepper(frame=(260, self.height-50, 94, 30), flex='WT')
        self.ring_stepper.action = self.ring_count_changed
        self.ring_stepper.value = self.scene.ring_count
        self.ring_stepper.step = 1
        self.ring_stepper.minimum_value = 1
        self.ring_stepper.maximum_value = 12
        self.add_subview(self.ring_stepper)
        self.ring_value = ui.Label(frame=(360, self.height-50, 40, 30),
                                   text=str(self.scene.ring_count), text_color='white', alignment=ui.ALIGN_LEFT)
        self.add_subview(self.ring_value)

    def slider_changed(self, sender):
        self.scene.speed_factor = 0.1 + sender.value * 2.9

    def bpm_changed(self, sender):
        try:
            bpm_val = float(sender.text)
            if bpm_val > 0:
                self.scene.bpm = bpm_val
                self.scene._next_pulse = time.time() + (60.0 / self.scene.bpm)
        except ValueError:
            pass

    def ring_count_changed(self, sender):
        count = int(sender.value)
        self.scene.set_ring_count(count)
        self.ring_value.text = str(count)

# --------------- Main ---------------
if __name__ == '__main__':
    v = MainView(frame=(0, 0, *get_screen_size()))
    v.present('fullscreen')
