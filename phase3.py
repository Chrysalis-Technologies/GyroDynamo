# tumbling_gyro_rings_gradients_bpm_haptics_pulse.py
# Tumbling gradient rings with alternating shading,
# haptic + visual pulse synced to BPM.

import math, time, ui
from scene import Scene, stroke, stroke_weight, line, background, get_screen_size, Vector2, SceneView
from objc_util import ObjCClass

# ---------------- Haptics ----------------
UIImpactFeedbackGenerator = ObjCClass('UIImpactFeedbackGenerator')
impact_medium = UIImpactFeedbackGenerator.alloc().initWithStyle_(1)  # 1 = medium
impact_medium.prepare()

def haptic_pulse():
    impact_medium.impactOccurred()
    impact_medium.prepare()

# ---------------- Config ----------------
BG = (0.05, 0.07, 0.10)
RING_COUNT = 7
BASE_RADIUS_FACTOR = 0.07
SPACING_TARGET = 46.0
SEGMENTS = 160
CAMERA_D = 900.0

LINE_THICKNESS = 3.0
BACK_ALPHA = 0.25
FRONT_ALPHA = 1.0

PALETTE = [
    (0.98, 0.46, 0.30),
    (0.20, 0.78, 0.68),
    (0.60, 0.50, 0.90),
    (0.95, 0.78, 0.25),
    (0.35, 0.72, 0.95),
    (0.90, 0.42, 0.65),
    (0.55, 0.88, 0.45),
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
        self.speed_factor = 1.0
        self.paused = False

    def setup(self):
        self.background_color = BG
        self.center = Vector2(self.size.w / 2, self.size.h / 2)
        self.min_dim = min(self.size.w, self.size.h)

        base_r = self.min_dim * BASE_RADIUS_FACTOR
        max_outer = (self.min_dim * 0.5) - 20.0
        spacing = SPACING_TARGET
        if RING_COUNT > 1:
            spacing = min(SPACING_TARGET, max(0.0, (max_outer - base_r)) / (RING_COUNT - 1))

        self.rings = []
        for i in range(RING_COUNT):
            r = base_r + i * spacing
            color = PALETTE[i % len(PALETTE)]
            omega = (0.6 + 0.25 * i) * (1 if i % 2 == 0 else -1)
            self.rings.append({
                'radius': r,
                'axis': (0.0, 0.0, 1.0),
                'angle': 0.0,
                'omega': omega,
                'color': color,
                'shade_dir': 1 if i % 2 == 0 else -1
            })

        self._last = time.time()

    def update(self):
        if self.paused: return
        now = time.time()
        dt = now - self._last
        self._last = now
        if dt <= 0: return

        aligned = True
        eps = 0.01
        for ring in self.rings:
            ring['angle'] = (ring['angle'] + ring['omega'] * dt * self.speed_factor) % math.tau
            a = ring['angle']
            if not (a < eps or a > math.tau - eps):
                aligned = False

        if aligned and not self._aligned_prev:
            haptic_pulse()
            self._last_pulse_time = now
        self._aligned_prev = aligned

    def draw_ring(self, ring, pulse_strength):
        pts3d = []
        for (x, y, z), t in circle_points(ring['radius']):
            X, Y, Z = rot_axis((x, y, z), ring['axis'], ring['angle'])
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
            alpha = (BACK_ALPHA + (FRONT_ALPHA - BACK_ALPHA) * phase) * (1.0 + 0.4 * pulse_strength)
            stroke(ring['color'][0], ring['color'][1], ring['color'][2], min(1.0, alpha))
            line(p0[0], p0[1], p1[0], p1[1])

    def draw(self):
        background(*BG)
        now = time.time()
        pulse_strength = pulse_curve(now - self._last_pulse_time, length=0.3)
        for ring in self.rings:
            self.draw_ring(ring, pulse_strength)

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

# --------------- Main ---------------
if __name__ == '__main__':
    v = MainView(frame=(0, 0, *get_screen_size()))
    v.present('fullscreen')
