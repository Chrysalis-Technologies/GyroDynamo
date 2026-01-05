# filename: tumbling_gyro_rings.py
# Pythonista (iOS) — multiple concentric rings, each rotating about a different 3D axis.
# Uses ui.Path + ShapeNode with tuple colors (no Color objects), perspective projection.

import math, time, random
from scene import Scene, ShapeNode, Vector2, run, PORTRAIT, LANDSCAPE
from ui import Path, get_screen_size

# ---------------- Config ----------------
BG = (0.02, 0.03, 0.05)        # background color (tuple)
RING_COUNT = 7                  # number of rings
BASE_RADIUS_FACTOR = 0.07       # inner ring radius as fraction of min(width,height)
SPACING_TARGET = 46.0           # desired pixel spacing between rings (auto-fits)
THICKNESS = 4.0                 # ring thickness in pixels
SEGMENTS = 160                  # polygon segments per circle (smoothness)
CAMERA_D = 900.0                # perspective distance (larger = flatter)
OMEGA_BASE = 0.75               # base angular speed (rad/s)

# palette (RGBA tuples)
# Helios / Orbital Sun Core palette (RGBA)
RING_GOLD = (0.93, 0.76, 0.30, 1.0)
RING_EDGE = (1.0, 0.88, 0.6, 0.6)
CORE_COLOR = (0.98, 0.99, 1.0, 1.0)
CORE_GLOW = (0.62, 0.8, 1.0, 0.26)
ACCENT_TEAL = (0.18, 0.74, 0.7, 1.0)
PALETTE = [
    (0.94, 0.79, 0.34, 1.0),
    (0.9, 0.75, 0.3, 1.0),
    (0.86, 0.71, 0.28, 1.0),
    (0.82, 0.67, 0.26, 1.0),
]

# --------------- Math helpers ---------------
def norm(v):
    x, y, z = v
    m = math.sqrt(x*x + y*y + z*z) or 1.0
    return (x/m, y/m, z/m)

def rot_axis(v, k, a):
    """Rotate vector v around axis k (unit) by angle a (Rodrigues)."""
    vx, vy, vz = v
    kx, ky, kz = k
    c = math.cos(a); s = math.sin(a); one_c = 1.0 - c
    # cross k × v
    cx = ky*vz - kz*vy
    cy = kz*vx - kx*vz
    cz = kx*vy - ky*vx
    dot = kx*vx + ky*vy + kz*vz
    rx = vx*c + cx*s + kx*dot*one_c
    ry = vy*c + cy*s + ky*dot*one_c
    rz = vz*c + cz*s + kz*dot*one_c
    return (rx, ry, rz)

def proj(x, y, z, d=CAMERA_D):
    """Simple pinhole projection onto screen plane centered at (0,0)."""
    f = d / (d + z)
    return (x * f, y * f)

def circle_points(radius, seg=SEGMENTS):
    for i in range(seg):
        t = (i / float(seg)) * (2.0 * math.pi)
        yield (radius * math.cos(t), radius * math.sin(t), 0.0)

def ring_path_3d(radius, thickness, axis, angle, offset=(0.0, 0.0, 0.0),
                 glyph_stride=11, glyph_phase=0):
    """Build a donut path by projecting outer and inner circles after 3D rotation."""
    outer_pts = []
    inner_pts = []
    r_in = max(1.0, radius - thickness)
    ox, oy, oz = offset

    for (x, y, z) in circle_points(radius):
        X, Y, Z = rot_axis((x, y, z), axis, angle)
        X += ox
        Y += oy
        Z += oz
        px, py = proj(X, Y, Z)
        outer_pts.append((px, py))

    for (x, y, z) in circle_points(r_in):
        X, Y, Z = rot_axis((x, y, z), axis, angle)
        X += ox
        Y += oy
        Z += oz
        px, py = proj(X, Y, Z)
        inner_pts.append((px, py))

    # Build even-odd donut: outer CCW, inner CW (reverse)
    p = Path()
    ox, oy = outer_pts[0]
    p.move_to(ox, oy)
    for (x, y) in outer_pts[1:]:
        p.line_to(x, y)
    p.close()

    inner_pts.reverse()
    ix, iy = inner_pts[0]
    p.move_to(ix, iy)
    for (x, y) in inner_pts[1:]:
        p.line_to(x, y)
    p.close()

    # Cut the hole using even-odd rule
    p.eo_fill_rule = True

    # Etched glyph ticks
    glyph = Path()
    count = len(outer_pts)
    stride = max(6, int(glyph_stride))
    for i in range(glyph_phase % count, count, stride):
        oxp, oyp = outer_pts[i]
        ixp, iyp = inner_pts[i]
        glyph.move_to(oxp, oyp)
        glyph.line_to(ixp, iyp)
    return p, glyph

# --------------- Scene ---------------
class TumblingGyro(Scene):
    def setup(self):
        self.background_color = BG
        self.center = Vector2(self.size.w / 2, self.size.h / 2)
        self.min_dim = min(self.size.w, self.size.h)

        base_r = self.min_dim * BASE_RADIUS_FACTOR
        max_outer = (self.min_dim * 0.5) - 10.0 - THICKNESS
        spacing = SPACING_TARGET
        if RING_COUNT > 1:
            spacing = min(SPACING_TARGET, max(0.0, (max_outer - base_r)) / (RING_COUNT - 1))

        # Define distinct axes and speeds
        axes = [
            norm((1.0, 0.2, 0.0)),   # mostly pitch
            norm((0.0, 1.0, 0.25)),  # mostly yaw
            norm((0.35, 0.25, 1.0)), # diagonal
            norm((1.0, 1.0, 0.0)),   # 45° in plane
            norm((0.0, 1.0, 1.0)),   # another diagonal
            norm((1.0, 0.0, 1.0)),
            norm((0.5, 0.8, 0.25)),
        ]

        self.rings = []
        for i in range(RING_COUNT):
            r = base_r + i * spacing
            axis = axes[i % len(axes)]
            color = PALETTE[i % len(PALETTE)]
            omega = OMEGA_BASE * (0.6 + 0.25 * i) * (1 if i % 2 == 0 else -1)

            # Build initial path and node centered at (0,0); position the node at screen center
            angle = random.random() * math.tau
            offset = (
                random.uniform(-0.06, 0.06) * r,
                random.uniform(-0.04, 0.04) * r,
                random.uniform(-0.06, 0.06) * r,
            )
            glyph_stride = random.choice([9, 11, 13])
            glyph_phase = random.randrange(glyph_stride)
            path, glyph_path = ring_path_3d(
                r,
                THICKNESS,
                axis,
                angle,
                offset=offset,
                glyph_stride=glyph_stride,
                glyph_phase=glyph_phase,
            )
            node = ShapeNode(path, fill_color=color, stroke_color=RING_EDGE)
            node.line_width = 1.2
            node.position = self.center
            node.z_position = i  # stable order
            self.add_child(node)

            glyph_node = ShapeNode(glyph_path, fill_color=(0, 0, 0, 0), stroke_color=(1.0, 0.92, 0.65, 0.55))
            glyph_node.line_width = 1.0
            glyph_node.position = self.center
            glyph_node.z_position = i + 0.2
            self.add_child(glyph_node)

            self.rings.append({
                'radius': r,
                'axis': axis,
                'angle': angle,
                'omega': omega,
                'node': node,
                'glyph_node': glyph_node,
                'offset': offset,
                'glyph_stride': glyph_stride,
                'glyph_phase': glyph_phase,
            })

        self._last = time.time()
        self._build_core()

    def _build_core(self):
        self.core_nodes = []
        core_r = self.min_dim * 0.055
        glow_layers = [(3.0, 0.08), (2.3, 0.14), (1.6, 0.22), (1.1, 0.32)]
        for scale, alpha in glow_layers:
            r = core_r * scale
            path = Path.oval(-r, -r, r * 2, r * 2)
            node = ShapeNode(path, fill_color=(CORE_GLOW[0], CORE_GLOW[1], CORE_GLOW[2], alpha),
                             stroke_color=(0, 0, 0, 0))
            node.position = self.center
            node.z_position = -5
            self.add_child(node)
            self.core_nodes.append(node)

        body_path = Path.oval(-core_r, -core_r, core_r * 2, core_r * 2)
        self.core_body = ShapeNode(body_path, fill_color=CORE_COLOR, stroke_color=(0, 0, 0, 0))
        self.core_body.position = self.center
        self.core_body.z_position = 10
        self.add_child(self.core_body)

        highlight_r = core_r * 0.45
        highlight_path = Path.oval(-highlight_r, -highlight_r, highlight_r * 2, highlight_r * 2)
        self.core_highlight = ShapeNode(highlight_path, fill_color=(1.0, 1.0, 1.0, 0.5),
                                        stroke_color=(0, 0, 0, 0))
        self.core_highlight.position = Vector2(self.center.x - core_r * 0.35, self.center.y - core_r * 0.35)
        self.core_highlight.z_position = 11
        self.add_child(self.core_highlight)

        aux_r = max(6.0, core_r * 0.35)
        aux_path = Path.oval(-aux_r, -aux_r, aux_r * 2, aux_r * 2)
        self.aux_node = ShapeNode(
            aux_path,
            fill_color=(ACCENT_TEAL[0], ACCENT_TEAL[1], ACCENT_TEAL[2], 0.65),
            stroke_color=(0, 0, 0, 0),
        )
        self.aux_node.z_position = 9
        self.add_child(self.aux_node)

        glow_r = aux_r * 2.6
        glow_path = Path.oval(-glow_r, -glow_r, glow_r * 2, glow_r * 2)
        self.aux_glow = ShapeNode(glow_path, fill_color=(ACCENT_TEAL[0], ACCENT_TEAL[1], ACCENT_TEAL[2], 0.16),
                                  stroke_color=(0, 0, 0, 0))
        self.aux_glow.z_position = 8
        self.add_child(self.aux_glow)

        self.aux_phase = 0.0
        self.aux_orbit_r = self.rings[-1]['radius'] * 0.85 if self.rings else core_r * 3.0

    def update(self):
        now = time.time()
        dt = now - self._last
        self._last = now
        if dt <= 0:
            return

        for ring in self.rings:
            ring['angle'] = (ring['angle'] + ring['omega'] * dt) % math.tau
            path, glyph_path = ring_path_3d(
                ring['radius'],
                THICKNESS,
                ring['axis'],
                ring['angle'],
                offset=ring['offset'],
                glyph_stride=ring['glyph_stride'],
                glyph_phase=ring['glyph_phase'],
            )
            ring['node'].path = path  # update geometry each frame
            ring['glyph_node'].path = glyph_path

        self.aux_phase = (self.aux_phase + dt * 0.35) % math.tau
        orbit_r = self.aux_orbit_r
        px, py = proj(
            orbit_r * math.cos(self.aux_phase),
            orbit_r * 0.35 * math.sin(self.aux_phase * 0.7),
            orbit_r * 0.6 * math.sin(self.aux_phase),
        )
        pos = Vector2(self.center.x + px, self.center.y + py)
        self.aux_node.position = pos
        self.aux_glow.position = pos

# --------------- Main ---------------
if __name__ == '__main__':
    w, h = get_screen_size()
    run(TumblingGyro(), PORTRAIT if h >= w else LANDSCAPE, show_fps=False)
