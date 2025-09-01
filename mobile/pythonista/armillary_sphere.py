import math
import random
import sys
import time

try:
    import scene as _scene
    # The Pythonista `scene` module exposes a `Path` class used for drawing. In
    # some environments (e.g. running the script outside Pythonista) a different
    # module named `scene` might be importable but without the expected API. We
    # explicitly check for the `Path` attribute and fall back to a harmless stub
    # if it's missing so that the math helpers can still be imported and tested.
    if not hasattr(_scene, "Path"):
        raise ImportError
    scene = _scene
except Exception:  # allow import outside Pythonista or with incompatible module
    from types import SimpleNamespace

    class _DummyPath:
        """Minimal stand-in for `scene.Path` used when not running in Pythonista.

        The methods implement no behaviour but allow code that builds paths to
        execute without raising attribute errors.
        """

        @staticmethod
        def oval(*args, **kwargs):
            return _DummyPath()

        def move_to(self, *args, **kwargs):
            return self

        def line_to(self, *args, **kwargs):
            return self

        def close(self):
            return self

        def fill(self):
            return self

    def _no_op(*args, **kwargs):
        pass

    scene = SimpleNamespace(
        Scene=object, Path=_DummyPath, run=_no_op, background=_no_op
    )
    # Expose the stub as a module so `from scene import run` works below.
    sys.modules.setdefault("scene", scene)

try:
    import ui  # noqa: F401
except Exception:
    ui = None

IS_PYTHONISTA = 'Pythonista' in sys.executable or sys.platform == 'ios'

# --- Math helpers ---------------------------------------------------------

def vec3(x, y, z):
    return (x, y, z)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(v):
    return math.sqrt(dot(v, v))


def normalize(v):
    n = norm(v)
    if n == 0:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def quat_from_axis_angle(axis, radians):
    ax = normalize(axis)
    s = math.sin(radians / 2.0)
    return (ax[0] * s, ax[1] * s, ax[2] * s, math.cos(radians / 2.0))


def quat_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def quat_rotate(q, v):
    x, y, z, w = q
    # Quaternion-vector multiplication optimized
    uv = cross((x, y, z), v)
    uuv = cross((x, y, z), uv)
    uv = (uv[0] * (2.0 * w), uv[1] * (2.0 * w), uv[2] * (2.0 * w))
    uuv = (uuv[0] * 2.0, uuv[1] * 2.0, uuv[2] * 2.0)
    return (
        v[0] + uv[0] + uuv[0],
        v[1] + uv[1] + uuv[1],
        v[2] + uv[2] + uuv[2],
    )


def look_at(eye, target, up):
    z = normalize((eye[0] - target[0], eye[1] - target[1], eye[2] - target[2]))
    x = normalize(cross(up, z))
    y = cross(z, x)
    return [
        [x[0], x[1], x[2], -dot(x, eye)],
        [y[0], y[1], y[2], -dot(y, eye)],
        [z[0], z[1], z[2], -dot(z, eye)],
        [0.0, 0.0, 0.0, 1.0],
    ]


def perspective(fov_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fov_deg) / 2.0)
    return [
        [f / aspect, 0.0, 0.0, 0.0],
        [0.0, f, 0.0, 0.0],
        [0.0, 0.0, (far + near) / (near - far), (2 * far * near) / (near - far)],
        [0.0, 0.0, -1.0, 0.0],
    ]


def transform_point(m, v):
    x, y, z = v
    return (
        m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3],
        m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3],
        m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3],
        m[3][0] * x + m[3][1] * y + m[3][2] * z + m[3][3],
    )


def project_point(v, view, proj, w, h):
    vx, vy, vz, vw = transform_point(view, v)
    px, py, pz, pw = transform_point(proj, (vx, vy, vz))
    px, py, pz = px / pw, py / pw, pz / pw
    sx = (px * 0.5 + 0.5) * w
    sy = (1.0 - (py * 0.5 + 0.5)) * h
    return sx, sy, pz

# --- Geometry -------------------------------------------------------------

def build_ring(num_segments, radius, band_thickness):
    centers = []
    normals = []
    for i in range(num_segments):
        a = 2 * math.pi * i / num_segments
        c, s = math.cos(a), math.sin(a)
        centers.append((c * radius, s * radius, 0.0))
        normals.append((c, s, 0.0))
    return centers, normals

# --- Data classes ---------------------------------------------------------

class Ring:
    def __init__(self, radius, tilt_deg, speed, num_segments, band_half_width):
        self.radius = radius
        self.speed = speed
        self.angle = 0.0
        self.tilt = quat_from_axis_angle((1, 0, 0), math.radians(tilt_deg))
        centers, normals = build_ring(num_segments, radius, band_half_width)
        self.inner = []
        self.outer = []
        for c, n in zip(centers, normals):
            self.outer.append((c[0] + n[0] * band_half_width, c[1] + n[1] * band_half_width, 0.0))
            self.inner.append((c[0] - n[0] * band_half_width, c[1] - n[1] * band_half_width, 0.0))
        self.normals = normals
        self.num_segments = num_segments

# --- Scene ----------------------------------------------------------------

RINGS = 5
RING_RADII = [1.1, 1.6, 2.1, 2.6, 3.1]
RING_TILTS_DEG = [0, 23, 47, 74, 102]
RING_SPEEDS = [0.06, -0.03, 0.04, -0.02, 0.03]
BAND_HALF_WIDTH = 0.12
NUM_SEGMENTS = 220
LIGHT_DIR = normalize((0.6, 0.4, 0.7))
FOV_DEG = 60
NEAR, FAR = 0.1, 100.0
CAMERA_RADIUS_START = 7.5
CAMERA_TARGET = (0.0, 0.0, 0.0)
STAR_SEED = 1337
STARS = 800

G_GLYPH_FREQ = 40.0

class ArmillaryScene(scene.Scene):
    def setup(self):
        self.start_time = time.time()
        self.paused = False
        self.rings = [
            Ring(r, t, s, NUM_SEGMENTS, BAND_HALF_WIDTH)
            for r, t, s in zip(RING_RADII, RING_TILTS_DEG, RING_SPEEDS)
        ]
        rnd = random.Random(STAR_SEED)
        self.stars = []
        for _ in range(STARS):
            v = normalize((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
            dist = rnd.uniform(20.0, 40.0)
            self.stars.append((v[0] * dist, v[1] * dist, v[2] * dist))

        self.cam_az = 0.2
        self.cam_el = 0.2
        self.cam_rad = CAMERA_RADIUS_START
        self.target_az = self.cam_az
        self.target_el = self.cam_el
        self.target_rad = self.cam_rad
        self.touches = {}

    # Touch controls --------------------------------------------------
    def touch_began(self, touch):
        if getattr(touch, 'tap_count', 0) == 2:
            self.paused = not self.paused
            return
        self.touches[touch.touch_id] = touch.location
        if len(self.touches) == 1:
            self.last_single = touch.location
        elif len(self.touches) == 2:
            pts = list(self.touches.values())
            self.pinch_start = _dist(pts[0], pts[1])
            self.pinch_rad = self.target_rad

    def touch_moved(self, touch):
        if touch.touch_id not in self.touches:
            return
        self.touches[touch.touch_id] = touch.location
        if len(self.touches) == 1:
            dx = touch.location.x - self.last_single.x
            dy = touch.location.y - self.last_single.y
            self.target_az -= dx * 0.01
            self.target_el -= dy * 0.01
            self.target_el = max(-1.2, min(1.2, self.target_el))
            self.last_single = touch.location
        elif len(self.touches) == 2:
            pts = list(self.touches.values())
            d = _dist(pts[0], pts[1])
            if d != 0:
                scale = self.pinch_start / d
                self.target_rad = max(3.0, min(15.0, self.pinch_rad * scale))

    def touch_ended(self, touch):
        self.touches.pop(touch.touch_id, None)
        if len(self.touches) == 1:
            self.last_single = next(iter(self.touches.values()))

    # Update & draw ----------------------------------------------------
    def update(self):
        dt = self.dt
        if self.paused:
            dt = 0.0
        for ring in self.rings:
            ring.angle += ring.speed * dt
        self.cam_az += (self.target_az - self.cam_az) * 0.15
        self.cam_el += (self.target_el - self.cam_el) * 0.15
        self.cam_rad += (self.target_rad - self.cam_rad) * 0.15

    def draw(self):
        w, h = self.size.w, self.size.h
        scene.background(0, 0, 0)
        # Camera matrices
        eye = _spherical(self.cam_rad, self.cam_az, self.cam_el)
        view = look_at(eye, CAMERA_TARGET, (0, 1, 0))
        proj = perspective(FOV_DEG, w / h, NEAR, FAR)

        # Draw stars
        for s in self.stars:
            sx, sy, sz = project_point(s, view, proj, w, h)
            if -1 <= sz <= 1:
                path = scene.Path.oval(sx, sy, 2, 2)
                scene.fill(1, 1, 1)
                path.fill()

        quads = []
        for ring in self.rings:
            rot = quat_from_axis_angle((0, 0, 1), ring.angle)
            orient = quat_mul(ring.tilt, rot)
            for i in range(ring.num_segments):
                j = (i + 1) % ring.num_segments
                p0 = quat_rotate(orient, ring.outer[i])
                p1 = quat_rotate(orient, ring.outer[j])
                p2 = quat_rotate(orient, ring.inner[j])
                p3 = quat_rotate(orient, ring.inner[i])
                v0 = transform_point(view, p0)
                v1 = transform_point(view, p1)
                v2 = transform_point(view, p2)
                v3 = transform_point(view, p3)
                depth = (v0[2] + v1[2] + v2[2] + v3[2]) / 4.0
                # normal in view space
                n = normalize(cross((v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2]),
                                     (v3[0]-v0[0], v3[1]-v0[1], v3[2]-v0[2])))
                lambert = max(0.0, dot(n, LIGHT_DIR))
                rim = max(0.0, -n[2]) ** 2
                t = i / ring.num_segments
                glyph = 0.7 + 0.3 * (1 if math.sin(t * G_GLYPH_FREQ + i * 0.15) > 0 else 0)
                shade = min(1.0, lambert + rim * 0.5) * glyph
                p0s = project_point(p0, view, proj, w, h)
                p1s = project_point(p1, view, proj, w, h)
                p2s = project_point(p2, view, proj, w, h)
                p3s = project_point(p3, view, proj, w, h)
                quads.append((depth, (p0s, p1s, p2s, p3s), shade))

        quads.sort(key=lambda q: q[0])
        for _, pts, shade in quads:
            path = scene.Path()
            path.move_to(pts[0][0], pts[0][1])
            path.line_to(pts[1][0], pts[1][1])
            path.line_to(pts[2][0], pts[2][1])
            path.line_to(pts[3][0], pts[3][1])
            path.close()
            scene.fill(shade * 0.8, shade * 0.78, shade * 0.75)
            path.fill()

# --- Utility --------------------------------------------------------------

def _spherical(r, az, el):
    return (
        r * math.cos(el) * math.sin(az),
        r * math.sin(el),
        r * math.cos(el) * math.cos(az),
    )


def _dist(a, b):
    dx = a.x - b.x
    dy = a.y - b.y
    return math.hypot(dx, dy)

if __name__ == '__main__':
    from scene import run
    run(ArmillaryScene(), show_fps=True, multi_touch=True)
