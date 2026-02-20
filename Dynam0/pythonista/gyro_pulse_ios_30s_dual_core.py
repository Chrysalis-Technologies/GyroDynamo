"""GyroPulse (Pythonista) - Dual Core 30s variant.

Adds a second full core + ring stack that mirrors the primary ring attributes.
"""

import math
import scene

from gyro_pulse_ios_30s import GyroPulseScene, Ring


class DualCoreGyroPulseScene(GyroPulseScene):
    def setup(self):
        super().setup()
        self.secondary_phase_offset = math.pi / 3.0
        self.secondary_center_shift = 0.34  # fraction of scene width
        self.secondary_rings = []
        self._build_secondary_cluster()

    def _clone_ring(self, src):
        ring = Ring(src.R, src.color, n_points=src.n,
                    spin_ratio=src.spin_ratio, tx_ratio=src.tx_ratio, ty_ratio=src.ty_ratio)
        ring.speed_scale = src.speed_scale
        ring.spin = src.spin
        ring.tilt_x = src.tilt_x
        ring.tilt_y = src.tilt_y
        ring.offset = src.offset
        ring.glyph_stride = src.glyph_stride
        ring.glyph_phase = src.glyph_phase
        ring.base_radius = src.base_radius
        return ring

    def _build_secondary_cluster(self):
        self.secondary_rings = [self._clone_ring(r) for r in self.rings]

    def _reindex(self):
        super()._reindex()
        self._build_secondary_cluster()

    def update(self):
        super().update()
        if self.paused:
            return
        for src, dst in zip(self.rings, self.secondary_rings):
            dst.spin = src.spin + self.secondary_phase_offset
            dst.tilt_x = src.tilt_x + self.secondary_phase_offset * 0.7
            dst.tilt_y = src.tilt_y - self.secondary_phase_offset * 0.45

    @staticmethod
    def _pulse_metrics(elapsed, reset_period, align_width):
        beats_total = elapsed * (96.0 / 60.0)
        mph = (beats_total / 8.0) % 1.0
        bph = beats_total % 1.0
        pulse_fn = lambda x, sharp=3.0: max(0.0, min(1.0, (0.5 * (1.0 + math.cos(2.0 * math.pi * x))) ** sharp))
        thickness_scale = 1.0 + 0.25 * pulse_fn(mph, 2.5)
        alpha_boost = 0.08 * pulse_fn(bph, 3.5) + 0.14 * pulse_fn(mph, 2.5)
        align_phase = (elapsed % reset_period) / reset_period
        align_dist = min(align_phase, 1.0 - align_phase)
        align_pulse = max(0.0, 1.0 - align_dist / align_width) ** 3.2
        thickness_scale += 1.1 * align_pulse
        alpha_boost += 0.9 * align_pulse
        glow_scale = 1.0 + 3.0 * align_pulse
        return thickness_scale, alpha_boost, glow_scale, align_pulse

    def _draw_ring_cluster(self, rings, x_shift, thickness_scale, alpha_boost, glow_scale):
        for ring in rings:
            pts3d = ring.points3d()
            pts2d = []
            for p in pts3d:
                x, y = self._project(p)
                pts2d.append((x + x_shift, y, p[2]))
            base_r, base_g, base_b = ring.color

            scene.stroke_weight(self.base_thickness * thickness_scale * 2.0)
            for i in range(len(pts2d)):
                x0, y0, z0 = pts2d[i]
                x1, y1, _ = pts2d[(i + 1) % len(pts2d)]
                depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, z0 / max(0.0001, ring.R)))
                shade = 0.68 + 0.32 * depth_mix
                scene.stroke(base_r * shade, base_g * shade, base_b * shade, min(1.0, 0.2 * glow_scale))
                scene.line(x0, y0, x1, y1)

            scene.stroke_weight(self.base_thickness * thickness_scale)
            for i in range(len(pts2d)):
                x0, y0, z0 = pts2d[i]
                x1, y1, _ = pts2d[(i + 1) % len(pts2d)]
                depth_mix = 0.5 + 0.5 * max(-1.0, min(1.0, z0 / max(0.0001, ring.R)))
                shade = 0.72 + 0.28 * depth_mix
                alpha = min(1.0, 0.5 + 0.45 * depth_mix + alpha_boost)
                scene.stroke(base_r * shade, base_g * shade, base_b * shade, alpha)
                scene.line(x0, y0, x1, y1)

    def draw(self):
        super().draw()
        w, h = self.size
        x_shift = w * self.secondary_center_shift
        cx, cy = w * 0.5 + x_shift, h * 0.5
        rad = min(w, h) * 0.06 * self.zoom

        thickness_scale, alpha_boost, glow_scale, align_pulse = self._pulse_metrics(
            self.elapsed, self.reset_period, self.align_width
        )

        # Secondary core glow
        scene.no_stroke()
        for i in range(5):
            t = i / 4.0
            glow_r = rad * (1.35 + t * 2.0 + 0.25 * align_pulse)
            alpha = 0.22 * (1.0 - t) ** 1.5
            scene.fill(self.core_glow_color[0], self.core_glow_color[1], self.core_glow_color[2], alpha)
            scene.ellipse(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2)

        # Secondary rings
        self._draw_ring_cluster(self.secondary_rings, x_shift, thickness_scale, alpha_boost, glow_scale)

        # Secondary core body
        scene.no_stroke()
        scene.fill(self.core_color[0], self.core_color[1], self.core_color[2], 0.98)
        scene.ellipse(cx - rad, cy - rad, rad * 2, rad * 2)
        highlight_r = rad * 0.38
        scene.fill(1.0, 1.0, 1.0, 0.45)
        scene.ellipse(cx - rad * 0.35 - highlight_r, cy - rad * 0.35 - highlight_r,
                      highlight_r * 2, highlight_r * 2)

        scene.fill(0.9, 0.95, 1.0)
        scene.text('dual core', 'Helvetica', 10, w - 52, 20, 5)


def main():
    scene.run(DualCoreGyroPulseScene(), show_fps=False)


if __name__ == '__main__':
    main()
