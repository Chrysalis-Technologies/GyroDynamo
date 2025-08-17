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

RATIO_LIST = [
    (1,1),(3,2),(2,1),(5,2),(5,3),(7,4),(8,5),(13,8)
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

def ring_points(axis, phase, radius, npts=160):
    pts = []
    ax = norm(axis)
    tmp = (0,1,0) if abs(ax[1])<0.9 else (1,0,0)
    u = norm((ax[1]*tmp[2]-ax[2]*tmp[1],
              ax[2]*tmp[0]-ax[0]*tmp[2],
              ax[0]*tmp[1]-ax[1]*tmp[0]))
    v = norm((ax[1]*u[2]-ax[2]*u[1],
              ax[2]*u[0]-ax[0]*u[2],
              ax[0]*u[1]-ax[1]*u[0]))
    for i in range(npts):
        a = phase + TAU*i/npts
        px, py = radius*math.cos(a), radius*math.sin(a)
        pts.append((px*u[0] + py*v[0],
                    px*u[1] + py*v[1],
                    px*u[2] + py*v[2]))
    return pts

class ResonanceController:
    def __init__(self):
        self.mode = 'beat'  # 'beat' or 'ratio'
        self.base_rpm = DEFAULT_BASE_RPM
        self.bpm = DEFAULT_BPM
        self.prec_ratio = DEFAULT_PREC_RATIO
        self.num_rings = DEFAULT_NUM_RINGS
        self.n_offsets = [0,1,-1,2,-2,3,-3,4,-4,5,-5,6,-6,7,-7,8]
        self.ratios = [RATIO_LIST[i % len(RATIO_LIST)] for i in range(MAX_RINGS)]

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
        else:
            for k in range(n):
                p,q = self.ratios[k]
                rings[k].set_spin((p/float(q))*self.base_omega)
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

        def add_switch(text, init, action):
            nonlocal y
            sw = ui.Switch(frame=(10,y,51,31))
            sw.value = init
            self.add_subview(sw)
            lb = ui.Label(frame=(65,y,120,31), text=text, text_color='#ddd', alignment=ui.ALIGN_LEFT)
            self.add_subview(lb)
            sw.action = action
            y += 40
            return sw

        add_label('Mode:')
        self.mode_switch = add_switch('Beat-Lock / Ratios', True, self.toggle_mode)

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
        self.controller.mode = 'beat' if sender.value else 'ratio'
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
        self.bg_color = '#0c0f14'
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
            random.seed(i*73+11)
            c = (0.35+0.65*random.random(), 0.55+0.45*random.random(), 0.75+0.25*random.random())
            self.palette.append(c)

        self.align_epsilon = 0.025
        self.last_pulse_time = -999

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
            self.bpm_badge.bg_color = (0.1,0.9,0.7,0.15)
        else:
            self.bpm_badge.text = 'RATIO MODE'
            self.bpm_badge.bg_color = (0.7,0.9,1.0,0.15)

    def draw(self):
        w_total, h = self.size.w, self.size.h
        w = w_total - self.panel_width
        n = self.controller.num_rings

        # clear frame
        scene.background(0.05, 0.07, 0.10)

        for i in range(n):
            r = self.rings[i]
            pts3 = ring_points(r.axis, r.theta, r.radius, npts=220)
            pts2 = []
            for p in pts3:
                x, y = project(p, w, h, scale=1.0)
                pts2.append((x + self.panel_width, y))

            scene.stroke(*self.palette[i])
            scene.stroke_weight(2.0)
            for j in range(len(pts2)):
                x0, y0 = pts2[j]
                x1, y1 = pts2[(j + 1) % len(pts2)]
                scene.line(x0, y0, x1, y1)

if __name__ == '__main__':
    scene.run(GyroScene(), multi_touch=False, show_fps=False)
