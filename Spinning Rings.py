# filename: tumbling_gyro_rings.py
# Pythonista (iOS) — multiple concentric rings, each rotating about a different 3D axis.
# Uses ui.Path + ShapeNode with tuple colors (no Color objects), perspective projection.

import math, time, random
from scene import Scene, ShapeNode, Vector2, run, PORTRAIT, LANDSCAPE
from ui import Path, get_screen_size

# ---------------- Config ----------------
BG = (0.05, 0.07, 0.10)        # background color (tuple)
RING_COUNT = 7                  # number of rings
BASE_RADIUS_FACTOR = 0.07       # inner ring radius as fraction of min(width,height)
SPACING_TARGET = 46.0           # desired pixel spacing between rings (auto-fits)
THICKNESS = 6.0                 # ring thickness in pixels
SEGMENTS = 160                  # polygon segments per circle (smoothness)
CAMERA_D = 900.0                # perspective distance (larger = flatter)
OMEGA_BASE = 0.9                # base angular speed (rad/s)

# palette (RGBA tuples)
PALETTE = [
    (0.98, 0.46, 0.30, 1.0),  # orange
    (0.20, 0.78, 0.68, 1.0),  # teal
    (0.60, 0.50, 0.90, 1.0),  # purple
    (0.95, 0.78, 0.25, 1.0),  # gold
    (0.35, 0.72, 0.95, 1.0),  # sky
    (0.90, 0.42, 0.65, 1.0),  # rose
    (0.55, 0.88, 0.45, 1.0),  # green
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

def ring_path_3d(radius, thickness, axis, angle):
    """Build a donut path by projecting outer and inner circles after 3D rotation."""
    outer_pts = []
    inner_pts = []
    r_in = max(1.0, radius - thickness)

    for (x, y, z) in circle_points(radius):
        X, Y, Z = rot_axis((x, y, z), axis, angle)
        px, py = proj(X, Y, Z)
        outer_pts.append((px, py))

    for (x, y, z) in circle_points(r_in):
        X, Y, Z = rot_axis((x, y, z), axis, angle)
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
    return p

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
            path = ring_path_3d(r, THICKNESS, axis, angle)
            node = ShapeNode(path, fill_color=color, stroke_color=(0, 0, 0, 0))
            node.position = self.center
            node.z_position = i  # stable order
            self.add_child(node)

            self.rings.append({
                'radius': r,
                'axis': axis,
                'angle': angle,
                'omega': omega,
                'node': node
            })

        self._last = time.time()

    def update(self):
        now = time.time()
        dt = now - self._last
        self._last = now
        if dt <= 0:
            return

        for ring in self.rings:
            ring['angle'] = (ring['angle'] + ring['omega'] * dt) % math.tau
            path = ring_path_3d(ring['radius'], THICKNESS, ring['axis'], ring['angle'])
            ring['node'].path = path  # update geometry each frame

# --------------- Main ---------------
if __name__ == '__main__':
    w, h = get_screen_size()
    run(TumblingGyro(), PORTRAIT if h >= w else LANDSCAPE, show_fps=False)
