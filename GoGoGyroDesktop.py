import math
import random
import argparse
import time
import colorsys
import pygame

# Helios / Orbital Sun Core palette
CORE_COLOR = (0.98, 0.99, 1.0)
CORE_GLOW = (0.62, 0.8, 1.0)
RING_GOLD = (0.93, 0.76, 0.30)
ACCENT_TEAL = (0.18, 0.74, 0.7)

GOLD_HUE, GOLD_SAT, GOLD_VAL = colorsys.rgb_to_hsv(*RING_GOLD)
GOLD_HUE_RANGE = 0.05
GOLD_SAT_RANGE = 0.18
GOLD_VAL_RANGE = 0.12


class Slider:
    """Simple horizontal slider that can be dragged with the mouse."""

    def __init__(self, rect, label, value=1.0, min_value=0.2, max_value=1.5, value_format=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.value = float(value)
        self.min_value = float(min_value)
        self.max_value = float(max_value)
        self.dragging = False
        self._pad = 14  # padding inside track
        self.value_format = value_format or "{label}: {value:.2f}x"

    def _value_from_pos(self, x):
        track_start = self.rect.left + self._pad
        track_end = self.rect.right - self._pad
        if track_end <= track_start:
            return self.value
        t = (x - track_start) / float(track_end - track_start)
        t = max(0.0, min(1.0, t))
        return self.min_value + t * (self.max_value - self.min_value)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self.value = self._value_from_pos(event.pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.value = self._value_from_pos(event.pos[0])
                self.dragging = False
                return True
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.value = self._value_from_pos(event.pos[0])
            return True
        return False

    def draw(self, surface, font):
        track_y = self.rect.centery
        track_start = self.rect.left + self._pad
        track_end = self.rect.right - self._pad

        pygame.draw.rect(surface, (40, 40, 40), self.rect, border_radius=6)
        pygame.draw.line(surface, (120, 120, 120), (track_start, track_y), (track_end, track_y), 4)

        knob_range = max(1, track_end - track_start)
        t = (self.value - self.min_value) / (self.max_value - self.min_value)
        knob_x = track_start + t * knob_range
        pygame.draw.circle(surface, (220, 220, 220), (int(knob_x), track_y), 10)
        pygame.draw.circle(surface, (30, 30, 30), (int(knob_x), track_y), 10, 2)

        label_text = self.value_format.format(label=self.label, value=self.value)
        text = font.render(label_text, True, (230, 230, 230))
        text_rect = text.get_rect()
        text_rect.midbottom = (self.rect.centerx, self.rect.top - 6)
        surface.blit(text, text_rect)

# ========================
# Tempo / Rhythm Settings
# ========================
TARGET_BPM = 96               # visual rhythm (beats per minute)
BEATS_PER_MEASURE = 8         # rings all realign every measure
BPM_SMOOTHING = 4.0           # how quickly current BPM eases to TARGET_BPM

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
        self.base_radius = radius
        self.color = color  # (r,g,b) 0..1
        self.n = n_points
        self.speed_scale = 1.0
        self.thickness_scale = 1.0
        self.base_color = color
        self.offset = offset if offset is not None else (0.0, 0.0, 0.0)
        h, s, v = colorsys.rgb_to_hsv(*color)
        self.hue = h
        self.saturation = s
        self.value = v
        self.glyph_stride = random.choice([9, 11, 13])
        self.glyph_phase = random.randrange(self.glyph_stride)

        # Orientation state
        self.tilt_x = random.uniform(-0.3, 0.3)
        self.tilt_y = random.uniform(-0.3, 0.3)
        self.spin = random.uniform(0, 2*math.pi)

        # Tempo-locked ratios (integers recommended for clean realignment)
        self.spin_ratio = spin_ratio
        self.tx_ratio = tx_ratio
        self.ty_ratio = ty_ratio

    def update(self, dt, omega_bar):
        # Lock angular velocities to multiples of the bar angular frequency.
        scaled = self.speed_scale * omega_bar
        self.spin += (self.spin_ratio * scaled) * dt
        self.tilt_x += (self.tx_ratio * scaled) * dt
        self.tilt_y += (self.ty_ratio * scaled) * dt

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

    def current_color(self):
        r, g, b = colorsys.hsv_to_rgb(self.hue % 1.0, self.saturation, self.value)
        return (r, g, b)

# ========================
# Desktop application using pygame
# ========================
class GoGoGyroDesktop:
    def __init__(self, width=800, height=800):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("GoGoGyro Desktop")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 22)
        self.font_small = pygame.font.SysFont(None, 18)

        self.paused = False
        self.elapsed = 0.0
        self.target_bpm = float(TARGET_BPM)
        self.cur_bpm = float(TARGET_BPM)
        self.beats_per_measure = BEATS_PER_MEASURE
        self.reset_period = 10.0

        # Camera/focal settings (unit-space)
        self.cam_dist = 3.5
        self.focal_len = 1.0
        self.cam_orbit_amp = 0.06   # fraction of draw width for a subtle parallax wobble
        self.cam_orbit_speed = 0.14
        self.light_dir = self._normalize((0.2, 0.35, 1.0))
        self.glow_alpha = 0.14
        self.align_width = 0.06     # portion of the measure used for alignment flash
        self.min_radius_gap = 0.015
        self.core_color = CORE_COLOR
        self.core_glow_color = CORE_GLOW
        self.accent_teal = ACCENT_TEAL
        self.aux_orbit_speed = 0.22

        # Rings: choose relatively prime-ish integer ratios so
        # rich polyrhythms emerge within the bar but realign each measure.
        ring_specs = [
            (1.06, 320, 5, 2, 3),
            (0.84, 280, 7, 3, 5),
            (0.62, 240, 9, 4, 7),
            (0.44, 200, 11, 5, 9),
        ]
        tones = [1.0, 0.95, 0.9, 0.84]
        self.rings = []
        for idx, (radius, n_points, spin_ratio, tx_ratio, ty_ratio) in enumerate(ring_specs):
            tone = tones[idx % len(tones)]
            color = tuple(min(1.0, c * tone) for c in RING_GOLD)
            offset = self._ring_offset(radius)
            self.rings.append(
                GyroRing(
                    radius,
                    color,
                    n_points=n_points,
                    spin_ratio=spin_ratio,
                    tx_ratio=tx_ratio,
                    ty_ratio=ty_ratio,
                    offset=offset,
                )
            )

        # Drawing params
        self.base_thickness = 3.2
        self.back_alpha = 0.35
        self.front_alpha = 0.98
        self.bg_top = (6, 8, 16)
        self.bg_bottom = (10, 14, 26)
        self.bg_surface = None

        self.ring_controls = []
        self.all_sliders = []
        self.buttons = []
        self.button_bottom = 120
        self.resize(width, height, rebuild=True)

    @staticmethod
    def _normalize(vec):
        x, y, z = vec
        mag = math.sqrt(x*x + y*y + z*z)
        if mag < 1e-6:
            return (0.0, 0.0, 1.0)
        return (x/mag, y/mag, z/mag)

    @staticmethod
    def _dot(a, b):
        return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

    @staticmethod
    def _clamp01(value):
        return max(0.0, min(1.0, value))

    @staticmethod
    def _ring_offset(radius):
        jitter = 0.06
        return (
            random.uniform(-jitter, jitter) * radius,
            random.uniform(-jitter * 0.6, jitter * 0.6) * radius,
            random.uniform(-jitter, jitter) * radius,
        )

    @staticmethod
    def _gold_color(tone=1.0):
        return tuple(min(1.0, c * tone) for c in RING_GOLD)

    def _capture_slider_state(self):
        if not self.ring_controls:
            return []
        return [
            {
                'size': controls['size'].value,
                'speed': controls['speed'].value,
                'thickness': controls['thickness'].value,
                'color': controls['color'].value,
            }
            for controls in self.ring_controls
        ]

    def resize(self, width, height, rebuild=False):
        slider_state = self._capture_slider_state()

        self.width = max(400, width)
        self.height = max(400, height)
        self.ui_panel_width = max(220, int(self.width * 0.28))
        self.draw_width = max(220, self.width - self.ui_panel_width)
        self.cx_base = self.draw_width * 0.5
        self.cy_base = self.height * 0.5
        self.cx = self.cx_base
        self.cy = self.cy_base
        self.scale_px = min(self.draw_width, self.height) * 0.48
        self._build_background()
        self._build_buttons()
        self._build_sliders(slider_state)

    def _build_sliders(self, slider_state=None):
        self.ring_controls = []
        self.all_sliders = []

        panel_x = self.draw_width + 22
        slider_width = max(140, self.ui_panel_width - 90)
        start_y = max(150, int(self.button_bottom + 22))
        available_height = max(100, self.height - start_y - 20)

        # Fit all ring control blocks within the panel by adapting their height
        # based on how many rings exist.
        slider_count = 4
        block_height = available_height / max(1, len(self.rings))
        block_height = min(240.0, block_height)  # keep roomy when few rings

        # Leave room for header + padding (~26 px budget)
        slider_height = max(10.0, min(42.0, (block_height - 26.0) / slider_count))
        slider_gap = max(2.0, (block_height - slider_count * slider_height - 16.0) / max(1, slider_count - 1))
        section_gap = block_height

        for idx, ring in enumerate(self.rings):
            section_y = int(start_y + idx * section_gap)

            slider_y = section_y + 22  # leave space for header

            size_rect = (panel_x, int(slider_y), slider_width, int(slider_height))
            speed_rect = (
                panel_x,
                int(slider_y + slider_height + slider_gap),
                slider_width,
                int(slider_height),
            )
            thickness_rect = (
                panel_x,
                int(slider_y + 2 * (slider_height + slider_gap)),
                slider_width,
                int(slider_height),
            )
            color_rect = (
                panel_x,
                int(slider_y + 3 * (slider_height + slider_gap)),
                slider_width,
                int(slider_height),
            )

            size_val = 1.0
            speed_val = 1.0
            thickness_val = 1.0
            hue_val = (ring.hue % 1.0) * 360.0
            if slider_state and idx < len(slider_state):
                state = slider_state[idx]
                size_val = state.get('size', size_val)
                speed_val = state.get('speed', speed_val)
                thickness_val = state.get('thickness', thickness_val)
                hue_val = state.get('color', hue_val)

            size_slider = Slider(size_rect, "Size", value=size_val, min_value=0.4, max_value=1.6,
                                 value_format="{label}: {value:.2f}x")
            speed_slider = Slider(speed_rect, "Speed", value=speed_val, min_value=0.2, max_value=3.0)
            thickness_slider = Slider(thickness_rect, "Thickness", value=thickness_val,
                                      min_value=0.3, max_value=3.0)
            color_slider = Slider(color_rect, "Hue", value=hue_val, min_value=0.0, max_value=360.0,
                                  value_format="{label}: {value:.0f}°")

            control_group = {
                'size': size_slider,
                'speed': speed_slider,
                'thickness': thickness_slider,
                'color': color_slider,
                'section_top': section_y,
                'block_height': block_height,
            }
            self.ring_controls.append(control_group)
            self.all_sliders.extend([size_slider, speed_slider, thickness_slider, color_slider])

    def _build_background(self):
        grad_col = pygame.Surface((1, self.height))
        for y in range(self.height):
            t = y / max(1, self.height - 1)
            r = int(self.bg_top[0] * (1 - t) + self.bg_bottom[0] * t)
            g = int(self.bg_top[1] * (1 - t) + self.bg_bottom[1] * t)
            b = int(self.bg_top[2] * (1 - t) + self.bg_bottom[2] * t)
            grad_col.set_at((0, y), (r, g, b))
        self.bg_surface = pygame.transform.smoothscale(grad_col, (self.draw_width, self.height))

    def _build_buttons(self):
        self.buttons = []
        panel_x = self.draw_width + 16
        gap = 8
        align_y = 120
        align_h = 32
        align_w = int((self.ui_panel_width - 32 - gap) / 2)
        align_w = max(60, align_w)

        self.buttons.append({
            'label': "Align -",
            'action': self.period_down,
            'rect': pygame.Rect(panel_x, align_y, align_w, align_h)
        })
        self.buttons.append({
            'label': "Align +",
            'action': self.period_up,
            'rect': pygame.Rect(panel_x + align_w + gap, align_y, align_w, align_h)
        })

        ring_y = align_y + align_h + gap
        ring_h = 32
        ring_gap = 8
        ring_w = int((self.ui_panel_width - 32 - 2 * ring_gap) / 3)
        ring_w = max(56, ring_w)
        ring_defs = [
            ("Inner +", self.add_ring),
            ("Outer +", self.add_outer_ring),
            ("Remove", self.remove_ring),
        ]
        for i, (label, action) in enumerate(ring_defs):
            x = panel_x + i * (ring_w + ring_gap)
            self.buttons.append({
                'label': label,
                'action': action,
                'rect': pygame.Rect(x, ring_y, ring_w, ring_h)
            })

        self.button_bottom = ring_y + ring_h

    def add_ring(self):
        slider_state = self._capture_slider_state()
        count = len(self.rings)

        if self.rings:
            last = self.rings[-1]
            radius = max(0.10, last.R * 0.78)
            spin_ratio = last.spin_ratio + 2
            tx_ratio = last.tx_ratio + 1
            ty_ratio = last.ty_ratio + 2
        else:
            radius = 1.0
            spin_ratio = 5
            tx_ratio = 2
            ty_ratio = 3

        tone = 0.92 + 0.06 * math.sin(count)
        color = self._gold_color(tone)
        new_points = max(180, int(360 * radius))
        new_ring = GyroRing(
            radius,
            color,
            n_points=new_points,
            spin_ratio=spin_ratio,
            tx_ratio=tx_ratio,
            ty_ratio=ty_ratio,
            offset=self._ring_offset(radius),
        )
        self.rings.append(new_ring)

        slider_state.append({
            'size': 1.0,
            'speed': 1.0,
            'thickness': 1.0,
            'color': (new_ring.hue % 1.0) * 360.0,
        })
        self._assign_ratios()
        self._build_sliders(slider_state)

    def add_outer_ring(self):
        slider_state = self._capture_slider_state()
        count = len(self.rings)
        if self.rings:
            outer = self.rings[0]
            radius = min(2.0, outer.R * 1.22)
        else:
            radius = 1.0
        tone = 0.96 - 0.04 * math.sin(count)
        color = self._gold_color(tone)
        new_points = max(180, int(360 * radius))
        new_ring = GyroRing(
            radius,
            color,
            n_points=new_points,
            spin_ratio=5,
            tx_ratio=2,
            ty_ratio=3,
            offset=self._ring_offset(radius),
        )
        self.rings.insert(0, new_ring)
        slider_state.insert(0, {
            'size': 1.0,
            'speed': 1.0,
            'thickness': 1.0,
            'color': (new_ring.hue % 1.0) * 360.0,
        })
        self._assign_ratios()
        self._build_sliders(slider_state)

    def remove_ring(self):
        if len(self.rings) <= 1:
            return
        slider_state = self._capture_slider_state()
        self.rings.pop()
        slider_state = slider_state[:-1]
        self._assign_ratios()
        self._build_sliders(slider_state)

    def _assign_ratios(self):
        """Keep integer spin/tilt ratios in a predictable pattern."""
        for idx, ring in enumerate(self.rings):
            ring.spin_ratio = 5 + 2 * idx
            ring.tx_ratio = 2 + idx
            ring.ty_ratio = 3 + 2 * idx

    # --------- Tempo helpers ---------
    def bar_omega(self):
        return 2.0 * math.pi / max(0.001, self.reset_period)

    def beat_phase(self):
        beat_len = self.reset_period / max(1.0, float(self.beats_per_measure))
        phase = (self.elapsed % beat_len) / beat_len
        return phase

    def measure_phase(self):
        return (self.elapsed % self.reset_period) / self.reset_period

    def pulse(self, x, sharpness=3.0):
        v = 0.5 * (1.0 + math.cos(2.0 * math.pi * x))
        return max(0.0, min(1.0, v ** sharpness))

    def period_up(self):
        self.reset_period = min(60.0, self.reset_period + 1.0)

    def period_down(self):
        self.reset_period = max(2.0, self.reset_period - 1.0)

    # --------- Engine ---------
    def update(self, dt):
        if self.paused:
            return
        self.elapsed += dt
        self.cur_bpm = (self.beats_per_measure * 60.0) / max(0.001, self.reset_period)
        self.target_bpm = self.cur_bpm
        omega_bar = self.bar_omega()
        # Apply slider values
        for ring, controls in zip(self.rings, self.ring_controls):
            ring.R = ring.base_radius * controls['size'].value
            ring.speed_scale = controls['speed'].value
            ring.thickness_scale = controls['thickness'].value
            tone = (controls['color'].value % 360.0) / 360.0
            ring.hue = GOLD_HUE + (tone - 0.5) * GOLD_HUE_RANGE
            ring.saturation = self._clamp01(GOLD_SAT - GOLD_SAT_RANGE * (tone - 0.5))
            ring.value = self._clamp01(GOLD_VAL + GOLD_VAL_RANGE * (tone - 0.5))

        # Enforce inner rings not exceeding size or speed vs. outer neighbor.
        for idx, (ring, controls) in enumerate(zip(self.rings, self.ring_controls)):
            if idx > 0:
                outer = self.rings[idx - 1]
                # Size constraint
                max_r = max(0.05, outer.R - self.min_radius_gap)
                if ring.R > max_r:
                    ring.R = max_r
                    size_val = ring.R / max(0.0001, ring.base_radius)
                    controls['size'].max_value = min(controls['size'].max_value, size_val)
                    controls['size'].value = size_val

                # Speed constraint (effective angular speed cannot exceed outer ring)
                outer_eff = outer.spin_ratio * max(0.0001, outer.speed_scale)
                max_speed = outer_eff / max(0.0001, ring.spin_ratio)
                if ring.speed_scale > max_speed:
                    ring.speed_scale = max_speed
                    controls['speed'].value = ring.speed_scale

            ring.update(dt, omega_bar)

    # --------- Projection & drawing ---------
    def project(self, p):
        x, y, z = p
        denom = (z + self.cam_dist)
        if denom < 0.1:
            denom = 0.1
        u = (self.focal_len * x) / denom
        v = (self.focal_len * y) / denom
        return (self.cx + u * self.scale_px, self.cy + v * self.scale_px)

    def draw_ring(self, surface, glow_surface, ring, thickness_scale=1.0,
                 alpha_boost=0.0, glow_scale=1.0):
        pts3d = ring.ring_points_3d()
        n = ring.n
        segments = []
        for i in range(n):
            p0 = pts3d[i]
            p1 = pts3d[(i + 1) % n]
            z_avg = 0.5 * (p0[2] + p1[2])
            mid = ((p0[0] + p1[0]) * 0.5, (p0[1] + p1[1]) * 0.5, z_avg)
            x0, y0 = self.project(p0)
            x1, y1 = self.project(p1)
            segments.append((z_avg, mid, i, x0, y0, x1, y1))

        # Draw from back to front for better occlusion.
        segments.sort(key=lambda s: s[0])

        base_color = ring.current_color()
        base_thickness = max(1.0, self.base_thickness * thickness_scale * ring.thickness_scale)
        thickness_px = max(1, int(base_thickness))
        glow_thickness_px = max(1, int(thickness_px * 2.2))

        clamp255 = lambda v: max(0, min(255, int(v)))

        for _, mid, _, x0, y0, x1, y1 in segments:
            depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, mid[2]))  # [-1,1] -> [0,1]
            light = max(0.0, self._dot(self._normalize(mid), self.light_dir))
            shade = 0.7 + 0.2 * depth_mix + 0.25 * light

            alpha = self.back_alpha + (self.front_alpha - self.back_alpha) * depth_mix + alpha_boost
            alpha = max(0.0, min(1.0, alpha))
            rgba = (
                clamp255(base_color[0] * shade * 255),
                clamp255(base_color[1] * shade * 255),
                clamp255(base_color[2] * shade * 255),
                int(alpha * 255),
            )

            glow_a = min(1.0, self.glow_alpha * (0.8 + 0.6 * depth_mix) * glow_scale)
            glow_color = (
                clamp255(base_color[0] * shade * 255),
                clamp255(base_color[1] * shade * 255),
                clamp255(base_color[2] * shade * 255),
                int(glow_a * 255),
            )

            pygame.draw.line(glow_surface, glow_color, (x0, y0), (x1, y1), glow_thickness_px)
            pygame.draw.line(surface, rgba, (x0, y0), (x1, y1), thickness_px)

        glyph_thickness = max(1, int(thickness_px * 0.7))
        for _, mid, idx, x0, y0, x1, y1 in segments:
            if (idx + ring.glyph_phase) % ring.glyph_stride != 0:
                continue
            depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, mid[2]))
            if depth_mix < 0.35:
                continue
            light = max(0.0, self._dot(self._normalize(mid), self.light_dir))
            shade = 0.9 + 0.2 * depth_mix + 0.2 * light
            alpha = min(1.0, self.front_alpha + alpha_boost + 0.2)
            glyph_color = (
                clamp255(base_color[0] * shade * 255 + 15),
                clamp255(base_color[1] * shade * 255 + 15),
                clamp255(base_color[2] * shade * 255 + 15),
                int(alpha * 255),
            )
            pygame.draw.line(surface, glyph_color, (x0, y0), (x1, y1), glyph_thickness)

    def _center_palette(self):
        """Core stays white-hot; avoid inheriting ring hues."""
        base = self.core_color
        palette = [self.core_color, (1.0, 1.0, 1.0)]
        return base, palette

    def draw_center_sphere(self, surface, glow_surface):
        _, palette = self._center_palette()
        radius_px = int(min(self.draw_width, self.height) * 0.07)
        if self.rings:
            inner = self.rings[-1]
            px, _ = self.project((inner.R, 0, 0))
            inner_px = abs(px - self.cx)
            radius_px = min(radius_px, max(12, int(inner_px * 0.55)))
        radius_px = max(10, min(radius_px, int(min(self.draw_width, self.height) * 0.18)))

        sphere = pygame.Surface((radius_px * 2, radius_px * 2), pygame.SRCALPHA)
        center = (radius_px, radius_px)

        layers = max(4, len(palette) + 2)
        for i in range(layers):
            t = i / float(layers - 1)
            col_idx = min(len(palette) - 1, int(t * len(palette)))
            tint = palette[col_idx]
            tint_rgb = tuple(int(max(0.0, min(1.0, c)) * 255) for c in tint)
            alpha = int(245 * (1.0 - t) ** 1.5)
            radius = max(1, int(radius_px * (1.0 - 0.09 * i)))
            pygame.draw.circle(sphere, tint_rgb + (alpha,), center, radius)

        highlight_col = (255, 255, 255, 150)
        pygame.draw.circle(
            sphere,
            highlight_col,
            (int(radius_px * 0.42), int(radius_px * 0.42)),
            int(radius_px * 0.32)
        )

        surface.blit(sphere, (self.cx - radius_px, self.cy - radius_px))
        glow_rgb = tuple(int(c * 255) for c in self.core_glow_color)
        for scale, alpha in ((1.6, 160), (2.2, 90), (2.9, 50)):
            pygame.draw.circle(
                glow_surface,
                glow_rgb + (alpha,),
                (int(self.cx), int(self.cy)),
                int(radius_px * scale),
            )

    def draw_aux_node(self, surface, glow_surface):
        if not self.rings:
            return
        t = self.elapsed * self.aux_orbit_speed
        orbit_r = self.rings[0].R * 0.9
        pos = (
            orbit_r * math.cos(t),
            orbit_r * 0.35 * math.sin(t * 0.7),
            orbit_r * 0.6 * math.sin(t),
        )
        x, y = self.project(pos)
        radius = int(min(self.draw_width, self.height) * 0.012)
        teal_rgb = tuple(int(c * 255) for c in self.accent_teal)
        pygame.draw.circle(glow_surface, teal_rgb + (50,), (int(x), int(y)), int(radius * 2.8))
        pygame.draw.circle(glow_surface, teal_rgb + (90,), (int(x), int(y)), int(radius * 1.6))
        pygame.draw.circle(surface, teal_rgb + (200,), (int(x), int(y)), max(2, radius))

    def draw(self):
        if self.bg_surface:
            self.screen.blit(self.bg_surface, (0, 0))
        else:
            self.screen.fill((0, 0, 0))

        layer = pygame.Surface((self.draw_width, self.height), pygame.SRCALPHA)
        glow_layer = pygame.Surface((self.draw_width, self.height), pygame.SRCALPHA)

        orbit_t = self.elapsed * self.cam_orbit_speed
        orbit_amp_px = self.cam_orbit_amp * self.scale_px
        self.cx = self.cx_base + math.sin(orbit_t) * orbit_amp_px
        self.cy = self.cy_base + math.cos(orbit_t * 0.8) * orbit_amp_px

        bph = self.beat_phase()
        mph = self.measure_phase()
        beat_pulse = self.pulse(bph, sharpness=3.5)
        measure_pulse = self.pulse(mph, sharpness=2.5)
        align_dist = min(mph, 1.0 - mph)
        align_pulse = max(0.0, 1.0 - align_dist / max(0.0001, self.align_width)) ** 3.2

        thickness_scale = 1.0 + 0.25 * measure_pulse + 1.05 * align_pulse
        alpha_boost = 0.06 * beat_pulse + 0.12 * measure_pulse + 0.85 * align_pulse
        glow_scale = 1.0 + 3.0 * align_pulse

        for r in self.rings:
            self.draw_ring(
                layer,
                glow_layer,
                r,
                thickness_scale=thickness_scale,
                alpha_boost=alpha_boost,
                glow_scale=glow_scale
            )

        self.draw_aux_node(layer, glow_layer)
        self.draw_center_sphere(layer, glow_layer)

        self.screen.blit(glow_layer, (0, 0))
        self.screen.blit(layer, (0, 0))
        self._draw_ui()
        pygame.display.flip()

    def _draw_ui(self):
        panel_rect = pygame.Rect(self.draw_width, 0, self.ui_panel_width, self.height)
        pygame.draw.rect(self.screen, (18, 18, 20), panel_rect)
        pygame.draw.rect(self.screen, (60, 60, 70), panel_rect, 2)

        title = self.font.render("Ring Controls", True, (230, 230, 240))
        self.screen.blit(title, (panel_rect.left + 18, 24))

        help_lines = [
            f"Align pulse every {self.reset_period:.1f}s.",
            "Buttons: Align -/+, inner +, outer +, remove.",
            "Space: pause • +/- inner • O outer • - remove",
        ]
        for i, line in enumerate(help_lines):
            text = self.font_small.render(line, True, (190, 190, 205))
            self.screen.blit(text, (panel_rect.left + 18, 60 + i * 18))

        self._draw_buttons()

        for idx, (ring, controls) in enumerate(zip(self.rings, self.ring_controls)):
            section_top = controls['section_top']
            block_height = controls.get('block_height', 160)
            top = section_top
            bottom = section_top + int(block_height)
            container_rect = pygame.Rect(
                panel_rect.left + 12,
                top,
                self.ui_panel_width - 24,
                bottom - top
            )
            pygame.draw.rect(self.screen, (24, 24, 28), container_rect, border_radius=10)
            pygame.draw.rect(self.screen, (70, 70, 82), container_rect, 2, border_radius=10)

            header = self.font.render(f"Ring {idx + 1}", True, (210, 210, 225))
            self.screen.blit(header, (container_rect.left + 10, top + 6))

            controls['size'].draw(self.screen, self.font_small)
            controls['speed'].draw(self.screen, self.font_small)
            controls['thickness'].draw(self.screen, self.font_small)
            controls['color'].draw(self.screen, self.font_small)

            # Draw a color swatch next to the hue slider for quick reference.
            swatch_rect = pygame.Rect(
                controls['color'].rect.right + 12,
                controls['color'].rect.centery - 12,
                24,
                24
            )
            swatch_color = tuple(int(c * 255) for c in ring.current_color())
            pygame.draw.rect(self.screen, swatch_color, swatch_rect)
            pygame.draw.rect(self.screen, (230, 230, 230), swatch_rect, 2)

    def _draw_buttons(self):
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.buttons:
            rect = btn['rect']
            hovered = rect.collidepoint(mouse_pos)
            base = (34, 36, 46)
            border = (90, 96, 112)
            if hovered:
                base = (44, 48, 62)
                border = (120, 132, 150)
            pygame.draw.rect(self.screen, base, rect, border_radius=6)
            pygame.draw.rect(self.screen, border, rect, 2, border_radius=6)
            label = self.font_small.render(btn['label'], True, (220, 222, 230))
            label_rect = label.get_rect(center=rect.center)
            self.screen.blit(label, label_rect)

    def _handle_button_click(self, pos):
        for btn in self.buttons:
            if btn['rect'].collidepoint(pos):
                btn['action']()
                return True
        return False

    # --------- Event handling ---------
    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            self.resize(event.w, event.h)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._handle_button_click(event.pos):
                return

        for slider in self.all_sliders:
            if slider.handle_event(event):
                return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
            elif event.key == pygame.K_UP:
                self.period_down()
            elif event.key == pygame.K_DOWN:
                self.period_up()
            elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS) or event.unicode == '+':
                self.add_ring()
            elif event.key in (pygame.K_o, pygame.K_O):
                self.add_outer_ring()
            elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS) or event.unicode == '-':
                self.remove_ring()

    def run(self, duration=None):
        running = True
        start_time = time.time()
        while running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_event(event)
            self.update(dt)
            self.draw()
            if duration and (time.time() - start_time) >= duration:
                running = False
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Desktop version of GoGoGyro using pygame")
    parser.add_argument('--width', type=int, default=800)
    parser.add_argument('--height', type=int, default=800)
    parser.add_argument('--duration', type=float, default=None,
                        help='Seconds to run before exiting (useful for headless testing).')
    args = parser.parse_args()

    app = GoGoGyroDesktop(args.width, args.height)
    app.run(duration=args.duration)


if __name__ == '__main__':
    main()
