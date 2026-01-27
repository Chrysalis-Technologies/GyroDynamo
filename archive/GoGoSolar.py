from scene import Scene, run, LabelNode
import math
from collections import deque

# Gravitational constant in AU^3 / (solar mass * year^2)
G = 4.0 * math.pi ** 2
SOFTENING = 1e-4  # softens close encounters to keep the system stable


def vec_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vec_scale(v, s):
    return (v[0] * s, v[1] * s, v[2] * s)


def vec_length_sq(v):
    return v[0] * v[0] + v[1] * v[1] + v[2] * v[2]


class CelestialBody:
    def __init__(self, name, mass, radius_px, color, position, velocity, trail_len=220):
        self.name = name
        self.mass = mass
        self.radius_px = radius_px
        self.color = color
        self.position = position
        self.velocity = velocity
        self.acc = (0.0, 0.0, 0.0)
        self.trail = deque(maxlen=trail_len)

    def push_trail(self):
        self.trail.append(self.position)


class SolarSystemScene(Scene):
    """Interactive solar system playground using the same gesture controls as the gyroscopic rings."""

    def setup(self):
        self.background_color = (0, 0, 0)
        self.center = (self.size.w * 0.5, self.size.h * 0.5)
        self.scale_au = min(self.size.w, self.size.h) * 0.32  # convert AU -> pixels
        self.cam_dist = 6.0
        self.focal_len = 1.2
        self.view_tilt = math.radians(60.0)

        self.seconds_per_year = 8.0
        self.time_scale = 1.0
        self.min_time_scale = 0.1
        self.max_time_scale = 48.0
        self.sim_years = 0.0

        # Central star (fixed initial position)
        self.bodies = []
        sun = CelestialBody(
            name="Sun",
            mass=1.0,
            radius_px=18.0,
            color=(1.0, 0.85, 0.55, 1.0),
            position=(0.0, 0.0, 0.0),
            velocity=(0.0, 0.0, 0.0),
            trail_len=80,
        )
        self.bodies.append(sun)
        sun.push_trail()

        # Planet data (semi-major axis in AU, mass in solar masses, inclination degrees)
        self._init_planets(sun)

        self.paused = False
        self.hud = LabelNode(
            '',
            position=(self.size.w * 0.5, self.size.h - 24),
            color='#e0e0ff',
            parent=self,
        )

    def _init_planets(self, sun):
        planets = [
            ("Mercury", 0.0553 / 332946.0, 0.39, 0.205, 7.0, 5.0, (0.83, 0.82, 0.72, 1.0)),
            ("Venus", 0.815 / 332946.0, 0.72, 0.007, 3.4, 7.0, (0.97, 0.86, 0.62, 1.0)),
            ("Earth", 1.0 / 332946.0, 1.0, 0.017, 0.0, 8.5, (0.54, 0.78, 1.0, 1.0)),
            ("Mars", 0.107 / 332946.0, 1.52, 0.093, 1.85, 7.5, (1.0, 0.62, 0.44, 1.0)),
            ("Jupiter", 317.8 / 332946.0, 5.20, 0.049, 1.3, 12.0, (0.94, 0.79, 0.58, 1.0)),
            ("Saturn", 95.2 / 332946.0, 9.58, 0.056, 2.5, 10.0, (0.94, 0.87, 0.73, 1.0)),
            ("Uranus", 14.5 / 332946.0, 19.2, 0.047, 0.8, 8.0, (0.74, 0.87, 0.94, 1.0)),
            ("Neptune", 17.1 / 332946.0, 30.1, 0.009, 1.8, 8.0, (0.54, 0.70, 0.94, 1.0)),
        ]

        for name, mass, a, eccentricity, inclination_deg, radius_px, color in planets:
            # Initial position at periapsis (x = a * (1 - e))
            r_peri = a * (1.0 - eccentricity)
            pos = (r_peri, 0.0, 0.0)

            # Circular orbit speed adjusted for eccentricity to approximate elliptical orbit
            mu = G * (sun.mass + mass)
            speed = math.sqrt(mu * (1.0 + eccentricity) / (a * (1.0 - eccentricity)))
            vel = (0.0, speed, 0.0)

            # Apply orbital inclination about the x-axis
            inc = math.radians(inclination_deg)
            pos = self._rotate_x(pos, inc)
            vel = self._rotate_x(vel, inc)

            body = CelestialBody(
                name=name,
                mass=mass,
                radius_px=radius_px,
                color=color,
                position=pos,
                velocity=vel,
                trail_len=400,
            )
            self.bodies.append(body)
            body.push_trail()

    @staticmethod
    def _rotate_x(v, angle):
        x, y, z = v
        ca = math.cos(angle)
        sa = math.sin(angle)
        return (x, y * ca - z * sa, y * sa + z * ca)

    def adjust_time_scale(self, factor):
        self.time_scale = max(self.min_time_scale, min(self.max_time_scale, self.time_scale * factor))

    def project(self, pos):
        # Rotate scene for an angled camera view
        x, y, z = pos
        ca = math.cos(self.view_tilt)
        sa = math.sin(self.view_tilt)
        y2 = y * ca - z * sa
        z2 = y * sa + z * ca

        denom = z2 + self.cam_dist
        if denom < 0.2:
            denom = 0.2
        scale = self.focal_len / denom
        sx = self.center[0] + x * self.scale_au * scale
        sy = self.center[1] + y2 * self.scale_au * scale
        return sx, sy

    def compute_accelerations(self):
        for body in self.bodies:
            acc = (0.0, 0.0, 0.0)
            for other in self.bodies:
                if body is other:
                    continue
                delta = vec_sub(other.position, body.position)
                dist_sq = vec_length_sq(delta) + SOFTENING
                inv_dist = dist_sq ** -0.5
                inv_dist3 = inv_dist * inv_dist * inv_dist
                acc = vec_add(acc, vec_scale(delta, G * other.mass * inv_dist3))
            body.acc = acc

    def step_dynamics(self, dt_years):
        self.compute_accelerations()
        for body in self.bodies:
            body.velocity = vec_add(body.velocity, vec_scale(body.acc, dt_years))
            body.position = vec_add(body.position, vec_scale(body.velocity, dt_years))
            body.push_trail()

    def update(self):
        if self.paused:
            return
        dt = self.dt or 1 / 60.0
        dt_years = (dt * self.time_scale) / self.seconds_per_year
        self.step_dynamics(dt_years)
        self.sim_years += dt_years
        self.hud.text = f'Time warp: {self.time_scale:.2f}x   |   Sim time: {self.sim_years:.2f} yr'

    def draw(self):
        # Draw background gradient
        background(0.02, 0.02, 0.05)
        no_fill()
        stroke(1, 1, 1, 0.05)

        # Planet trails
        for body in self.bodies:
            if len(body.trail) < 2:
                continue
            stroke(*body.color)
            stroke_weight(1.1 if body.radius_px > 9 else 0.8)
            pts = [self.project(p) for p in body.trail]
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                line(x0, y0, x1, y1)

        # Bodies themselves
        for body in self.bodies:
            sx, sy = self.project(body.position)
            r = body.radius_px
            fill(*body.color)
            no_stroke()
            ellipse(sx - r, sy - r, r * 2.0, r * 2.0)

    def touch_began(self, touch):
        touches = list(self.touches.values())
        if len(touches) == 1:
            self.paused = not self.paused
        elif len(touches) == 2:
            self.adjust_time_scale(1.5)
        elif len(touches) >= 3:
            self.adjust_time_scale(1.0 / 1.5)


if __name__ == '__main__':
    run(SolarSystemScene(), show_fps=True, multi_touch=True)
