# Pythonista (iOS) — Resonant Gyroscopic Rings (Stepper-free)
# - Beat-lock mode: visual pulses align to a target BPM via |ω_i - ω_j| = 2π·BPM/60
# - Ratios mode: ω_i = (p_i/q_i)·ω0 for exact repeating patterns
# - Precession wobble simulates a sliding axis: Ω_prec = r_prec · 2π·BPM/60 (± alternating)
# Controls (left): mode toggle, Base RPM, Target BPM, Precession ratio, Ring count (slider), Start/Stop.

import math, random
import scene
import ui

TAU = 2*math.pi
MAX_RINGS = 16

DEFAULT_NUM_RINGS = 6
DEFAULT_BASE_RPM  = 12.0
DEFAULT_BPM       = 120.0
DEFAULT_PREC_RATIO= 0.5

# Helios / Orbital Sun Core palette
CORE_COLOR = (0.98, 0.99, 1.0)
CORE_GLOW = (0.62, 0.8, 1.0)
RING_GOLD = (0.93, 0.76, 0.30)
ACCENT_TEAL = (0.18, 0.74, 0.7)
BG_DEEP = (0.02, 0.03, 0.05)

RATIO_LIST = [
    (1,1),(3,2),(2,1),(5,2),(5,3),(7,4),(8,5),(13,8)
]

# Near-rational approximations of irrational numbers for quasi mode
QUASI_LIST = [
    (34, 21),   # φ ≈ 1.6190
    (99, 70),   # √2 ≈ 1.4143
    (97, 56),   # √3 ≈ 1.7321
    (193, 71),  # e  ≈ 2.7183
    (355, 226)  # π/2 ≈ 1.5708
]

def norm(v):
    x,y,z = v
    m = (x*x+y*y+z*z)**0.5
    return (x/m, y/m, z/m) if m>1e-9 else (0,0,1)

def rot3(v, axis, theta):
    # Rodrigues' formula
    ax, ay, az = norm(axis)
    x, y, z = v
    ct, st = math.cos(theta), math.sin(theta)
    dot = x*ax + y*ay + z*az
    cross = (ay*z - az*y, az*x - ax*z, ax*y - ay*x)
    rx = x*ct + cross[0]*st + ax*dot*(1-ct)
    ry = y*ct + cross[1]*st + ay*dot*(1-ct)
    rz = z*ct + cross[2]*st + az*dot*(1-ct)
    return (rx, ry, rz)

class Ring:
    def __init__(self, idx, base_radius, thickness):
        self.idx = idx
        self.radius = base_radius * (1.0 - 0.1*idx)
        self.thickness = thickness
        # Start all rings with a common axis so they remain concentric
        self.axis = norm((0.0, 0.0, 1.0))
        self.spin = 0.0
        self.theta = 0.0
        self.prec_axis = norm((0.0, 1.0, 0.0))
        self.prec_phase = 0.0
        self.prec_rate = 0.0
        jitter = 0.06
        self.offset = (
            random.uniform(-jitter, jitter) * self.radius,
            random.uniform(-jitter * 0.6, jitter * 0.6) * self.radius,
            random.uniform(-jitter, jitter) * self.radius,
        )
        self.glyph_stride = random.choice([9, 11, 13])
        self.glyph_phase = random.randrange(self.glyph_stride)

    def set_spin(self, omega): self.spin = float(omega)
    def set_precession(self, omega_prec): self.prec_rate = float(omega_prec)

    def update(self, dt):
        self.prec_phase += self.prec_rate * dt
        self.axis = rot3(self.axis, self.prec_axis, self.prec_rate * dt)
        self.theta = (self.theta + self.spin*dt) % TAU

def project(v, w, h, scale=1.0, cam=(0,0,600.0)):
    x,y,z = v
    cz = max(1.0, cam[2]-z)
    s = scale*(cam[2]/cz)
    return (w*0.5 + x*s, h*0.5 + y*s)

def ring_points(axis, phase, radius, offset=(0.0, 0.0, 0.0), npts=160):
    pts = []
    ax = norm(axis)
    tmp = (0,1,0) if abs(ax[1])<0.9 else (1,0,0)
    u = norm((ax[1]*tmp[2]-ax[2]*tmp[1],
              ax[2]*tmp[0]-ax[0]*tmp[2],
              ax[0]*tmp[1]-ax[1]*tmp[0]))
    v = norm((ax[1]*u[2]-ax[2]*u[1],
              ax[2]*u[0]-ax[0]*u[2],
              ax[0]*u[1]-ax[1]*u[0]))
    ox, oy, oz = offset
    for i in range(npts):
        a = phase + TAU*i/npts
        px, py = radius*math.cos(a), radius*math.sin(a)
        pts.append((px*u[0] + py*v[0],
                    px*u[1] + py*v[1],
                    px*u[2] + py*v[2] + oz))
        pts[-1] = (pts[-1][0] + ox, pts[-1][1] + oy, pts[-1][2])
    return pts

class ResonanceController:
    def __init__(self):
        self.mode = 'beat'  # 'beat', 'ratio', or 'quasi'
        self.base_rpm = DEFAULT_BASE_RPM
        self.bpm = DEFAULT_BPM
        self.prec_ratio = DEFAULT_PREC_RATIO
        self.num_rings = DEFAULT_NUM_RINGS
        self.n_offsets = [0,1,-1,2,-2,3,-3,4,-4,5,-5,6,-6,7,-7,8]
        self.ratios = [RATIO_LIST[i % len(RATIO_LIST)] for i in range(MAX_RINGS)]
        self.quasi_ratios = [QUASI_LIST[i % len(QUASI_LIST)] for i in range(MAX_RINGS)]

    @property
    def base_omega(self): return TAU * (self.base_rpm/60.0)
    @property
    def beat_omega(self): return TAU * (self.bpm/60.0)

    def configure(self, rings):
        n = min(self.num_rings, len(rings))
        if self.mode == 'beat':
            for k in range(n):
                nk = self.n_offsets[k]
                rings[k].set_spin(self.base_omega + nk*self.beat_omega)
        elif self.mode == 'ratio':
            for k in range(n):
                p, q = self.ratios[k]
                rings[k].set_spin((p/float(q)) * self.base_omega)
        elif self.mode == 'quasi':
            for k in range(n):
                p, q = self.quasi_ratios[k]
                rings[k].set_spin((p/float(q)) * self.base_omega)
        omega_prec = self.prec_ratio * self.beat_omega
        for k in range(n):
            rings[k].set_precession(omega_prec)

class ControlPanel(ui.View):
    def __init__(self, controller, on_change, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = (0,0,0,0.2)
        self.controller = controller
        self.on_change = on_change
        y = 10

        def add_label(t):
            nonlocal y
            l = ui.Label(frame=(10,y,160,22), text=t, text_color='#ddd', alignment=ui.ALIGN_LEFT)
            self.add_subview(l)
            y += 22
            return l

        def add_slider(minv,maxv,val, action):
            nonlocal y
            s = ui.Slider(frame=(10,y,160,22))
            s.min_value = 0.0
            s.max_value = 1.0
            # store mapping on control to compute absolute value in handler
            s._map = (minv, maxv, val)
            s.value = 0.0 if maxv==minv else (val-minv)/(maxv-minv)
            s.action = action
            self.add_subview(s)
            y += 28
            return s

        def add_segment(items, action, index=0):
            nonlocal y
            seg = ui.SegmentedControl(frame=(10, y, 160, 32))
            seg.segments = items
            seg.selected_index = index
            seg.action = action
            self.add_subview(seg)
            y += 40
            return seg

        add_label('Mode:')
        self.mode_seg = add_segment(['Beat', 'Ratio', 'Quasi'], self.toggle_mode, 0)

        add_label('Base RPM')
        self.base_label = ui.Label(frame=(120, y-22, 60, 22), text=f'{DEFAULT_BASE_RPM:.2f}', text_color='#aaa', alignment=ui.ALIGN_RIGHT)
        self.add_subview(self.base_label)
        self.base_slider = add_slider(2.0, 60.0, DEFAULT_BASE_RPM, self.on_base)

        add_label('Target BPM')
        self.bpm_label = ui.Label(frame=(120, y-22, 60, 22), text=f'{DEFAULT_BPM:.0f}', text_color='#aaa', alignment=ui.ALIGN_RIGHT)
        self.add_subview(self.bpm_label)
        self.bpm_slider = add_slider(30.0, 240.0, DEFAULT_BPM, self.on_bpm)

        add_label('Precession ratio')
        self.prec_label = ui.Label(frame=(120, y-22, 60, 22), text=f'{DEFAULT_PREC_RATIO:.2f}', text_color='#aaa', alignment=ui.ALIGN_RIGHT)
        self.add_subview(self.prec_label)
        self.prec_slider = add_slider(0.0, 2.0, DEFAULT_PREC_RATIO, self.on_prec)

        add_label('Rings')
        # slider replaces missing ui.Stepper
        self.rings_label = ui.Label(frame=(120, y-22, 60, 22), text=str(DEFAULT_NUM_RINGS), text_color='#aaa', alignment=ui.ALIGN_RIGHT)
        self.add_subview(self.rings_label)
        self.rings_slider = add_slider(1.0, float(MAX_RINGS), float(DEFAULT_NUM_RINGS), self.on_rings)

        self.start_btn = ui.Button(title='Start/Stop', frame=(10,y,160,34), bg_color='#333', tint_color='#eee')
        self.start_btn.action = self.toggle_run
        self.add_subview(self.start_btn)

    # Handlers
    def _map_val(self, s):
        minv,maxv,_ = s._map
        return minv + s.value*(maxv-minv)

    def toggle_mode(self, sender):
        idx = sender.selected_index
        self.controller.mode = ['beat', 'ratio', 'quasi'][idx]
        self.on_change()

    def on_base(self, s):
        val = round(self._map_val(s), 2)
        self.controller.base_rpm = val
        self.base_label.text = f'{val:.2f}'
        self.on_change()

    def on_bpm(self, s):
        val = round(self._map_val(s))
        self.controller.bpm = float(val)
        self.bpm_label.text = f'{val:.0f}'
        self.on_change()

    def on_prec(self, s):
        val = round(self._map_val(s), 2)
        self.controller.prec_ratio = val
        self.prec_label.text = f'{val:.2f}'
        self.on_change()

    def on_rings(self, s):
        val = int(round(self._map_val(s)))
        val = max(1, min(MAX_RINGS, val))
        self.controller.num_rings = val
        self.rings_label.text = str(val)
        self.on_change()

    def toggle_run(self, s):
        self.on_change(toggle=True)

class GyroScene(scene.Scene):
    def setup(self):
        self.bg_color = BG_DEEP
        self.controller = ResonanceController()
        self.running = True

        # Width reserved for the control panel on the left
        self.panel_width = 180

        # Create rings sized to the remaining display area
        avail_w = self.size.w - self.panel_width
        base_radius = min(avail_w, self.size.h) * 0.42
        self.rings = []
        for i in range(MAX_RINGS):
            self.rings.append(Ring(i, base_radius, thickness=2.0))

        self.controller.configure(self.rings)

        # Add control panel after rings so its width is known
        self.panel = ControlPanel(self.controller, self.on_controls_changed,
                                   frame=(0,0,self.panel_width,self.size.h))
        self.panel.flex = 'H'
        self.view.add_subview(self.panel)

        self.last_t = self.t

        self.palette = []
        for i in range(MAX_RINGS):
            tone = 0.98 - 0.04 * (i % 4)
            self.palette.append(tuple(min(1.0, c * tone) for c in RING_GOLD))

        self.align_epsilon = 0.025
        self.last_pulse_time = -999
        self.aux_phase = 0.0

        # persistent BPM badge to avoid subview churn
        self.bpm_badge = ui.Label(frame=(self.size.w-120,10,110,40))
        self.bpm_badge.text_color = '#aaffee'
        self.bpm_badge.alignment = ui.ALIGN_CENTER
        self.bpm_badge.font = ('<System>', 12)
        self.view.add_subview(self.bpm_badge)

    def on_controls_changed(self, toggle=False):
        if toggle:
            self.running = not self.running
            return
        self.controller.configure(self.rings)

    def update(self):
        now = self.t
        dt = max(0.0, now - getattr(self, 'last_t', now))
        self.last_t = now
        if not self.running:
            return
        for k in range(self.controller.num_rings):
            self.rings[k].update(dt)

        self.aux_phase = (self.aux_phase + dt * 0.35) % TAU

        # Simple alignment pulse detector (optional hook point)
        if self.controller.num_rings >= 2:
            cs = [math.cos(r.theta) for r in self.rings[:self.controller.num_rings]]
            sn = [math.sin(r.theta) for r in self.rings[:self.controller.num_rings]]
            if (max(cs)-min(cs) < 0.10) and (max(sn)-min(sn) < 0.10):
                if now - self.last_pulse_time > 0.25:
                    self.last_pulse_time = now
                    # add visuals/haptics here if desired

        # update BPM badge
        if self.controller.mode == 'beat':
            self.bpm_badge.text = f'{int(self.controller.bpm)} BPM'
            self.bpm_badge.bg_color = (ACCENT_TEAL[0], ACCENT_TEAL[1], ACCENT_TEAL[2], 0.18)
        elif self.controller.mode == 'ratio':
            self.bpm_badge.text = 'RATIO MODE'
            self.bpm_badge.bg_color = (RING_GOLD[0], RING_GOLD[1], RING_GOLD[2], 0.18)
        else:
            self.bpm_badge.text = 'QUASI MODE'
            self.bpm_badge.bg_color = (0.95, 0.7, 0.3, 0.18)

    def draw(self):
        w_total, h = self.size.w, self.size.h
        w = w_total - self.panel_width
        n = self.controller.num_rings

        # clear frame
        scene.background(*BG_DEEP)
        cx = self.panel_width + w * 0.5
        cy = h * 0.5

        # core glow + body
        core_r = min(w, h) * 0.06
        scene.no_stroke()
        for i in range(5):
            t = i / 4.0
            glow_r = core_r * (1.35 + t * 2.0)
            alpha = 0.26 * (1.0 - t) ** 1.5
            scene.fill(CORE_GLOW[0], CORE_GLOW[1], CORE_GLOW[2], alpha)
            scene.ellipse(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2)
        scene.fill(CORE_COLOR[0], CORE_COLOR[1], CORE_COLOR[2], 1.0)
        scene.ellipse(cx - core_r, cy - core_r, core_r * 2, core_r * 2)
        highlight_r = core_r * 0.38
        scene.fill(1.0, 1.0, 1.0, 0.5)
        scene.ellipse(cx - core_r * 0.35 - highlight_r, cy - core_r * 0.35 - highlight_r,
                      highlight_r * 2, highlight_r * 2)

        # auxiliary node
        if self.rings:
            orbit_r = self.rings[0].radius * 0.9
            px, py = project(
                (orbit_r * math.cos(self.aux_phase),
                 orbit_r * 0.35 * math.sin(self.aux_phase * 0.7),
                 orbit_r * 0.6 * math.sin(self.aux_phase)),
                w,
                h,
                scale=1.0,
            )
            ax = px + self.panel_width
            ay = py
            node_r = max(4.0, core_r * 0.3)
            scene.no_stroke()
            scene.fill(ACCENT_TEAL[0], ACCENT_TEAL[1], ACCENT_TEAL[2], 0.16)
            scene.ellipse(ax - node_r * 2.4, ay - node_r * 2.4, node_r * 4.8, node_r * 4.8)
            scene.fill(ACCENT_TEAL[0], ACCENT_TEAL[1], ACCENT_TEAL[2], 0.6)
            scene.ellipse(ax - node_r, ay - node_r, node_r * 2, node_r * 2)
            scene.fill(0.95, 1.0, 1.0, 0.45)
            scene.ellipse(ax - node_r * 0.32, ay - node_r * 0.32, node_r * 0.64, node_r * 0.64)

        for i in range(n):
            r = self.rings[i]
            pts3 = ring_points(r.axis, r.theta, r.radius, offset=r.offset, npts=220)
            pts2 = []
            for p in pts3:
                x, y = project(p, w, h, scale=1.0)
                pts2.append((x + self.panel_width, y, p[2]))

            base = self.palette[i]
            glow_w = 4.2
            base_w = 2.0
            scene.stroke_weight(glow_w)
            for j in range(len(pts2)):
                x0, y0, z0 = pts2[j]
                x1, y1, z1 = pts2[(j + 1) % len(pts2)]
                depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, z0 / max(1.0, r.radius)))
                shade = 0.68 + 0.32 * depth_mix
                scene.stroke(base[0] * shade, base[1] * shade, base[2] * shade, 0.22)
                scene.line(x0, y0, x1, y1)

            scene.stroke_weight(base_w)
            for j in range(len(pts2)):
                x0, y0, z0 = pts2[j]
                x1, y1, z1 = pts2[(j + 1) % len(pts2)]
                depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, z0 / max(1.0, r.radius)))
                shade = 0.72 + 0.28 * depth_mix
                alpha = 0.6 + 0.35 * depth_mix
                scene.stroke(base[0] * shade, base[1] * shade, base[2] * shade, alpha)
                scene.line(x0, y0, x1, y1)

            scene.stroke_weight(max(1.0, base_w * 0.7))
            for j in range(len(pts2)):
                if (j + r.glyph_phase) % r.glyph_stride != 0:
                    continue
                x0, y0, z0 = pts2[j]
                x1, y1, z1 = pts2[(j + 1) % len(pts2)]
                depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, z0 / max(1.0, r.radius)))
                if depth_mix < 0.35:
                    continue
                shade = 0.92 + 0.2 * depth_mix
                scene.stroke(
                    min(1.0, base[0] * shade + 0.1),
                    min(1.0, base[1] * shade + 0.1),
                    min(1.0, base[2] * shade + 0.1),
                    0.9,
                )
                scene.line(x0, y0, x1, y1)

if __name__ == '__main__':
    scene.run(GyroScene(), multi_touch=False, show_fps=False)
