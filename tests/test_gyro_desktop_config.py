import argparse
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from Dynam0.GyroDynamoVisPy import (
    PALETTES,
    build_ring_configs,
    clamp_ring_count,
    parse_args,
    parse_size,
    resolve_desktop_config,
    resolve_palette,
    write_bmp,
)


class GyroDesktopConfigTests(unittest.TestCase):
    def test_parse_size_accepts_text_and_rejects_small_windows(self):
        self.assertEqual(parse_size("1920x1080"), (1920, 1080))
        self.assertEqual(parse_size([1280, 720]), (1280, 720))
        with self.assertRaises(ValueError):
            parse_size("400x300")

    def test_palette_resolution_accepts_name_and_index(self):
        self.assertEqual(resolve_palette("Solar Forge"), 0)
        self.assertEqual(resolve_palette("ion-aurora"), 1)
        self.assertEqual(resolve_palette("2"), 2)
        with self.assertRaises(ValueError):
            resolve_palette(str(len(PALETTES)))

    def test_ring_count_clamps_to_supported_range(self):
        self.assertEqual(clamp_ring_count(1), 3)
        self.assertEqual(clamp_ring_count(7), 7)
        self.assertEqual(clamp_ring_count(99), 10)
        self.assertEqual(len(build_ring_configs(99)), 10)

    def test_config_file_loads_and_cli_overrides_take_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "gyro.json"
            cfg_path.write_text(
                json.dumps(
                    {
                        "size": "1280x720",
                        "bpm": 72,
                        "rings": 4,
                        "palette": "Copper Flux",
                        "fullscreen": False,
                        "camera_drift": True,
                        "hud": True,
                        "tempo_scale": 1.25,
                        "screenshot_dir": "shots",
                    }
                ),
                encoding="utf-8",
            )

            args = parse_args(
                [
                    "--config",
                    str(cfg_path),
                    "--bpm",
                    "96",
                    "--rings",
                    "9",
                    "--palette",
                    "Arctic Neon",
                    "--no-hud",
                    "--no-camera-drift",
                    "--fullscreen",
                    "--screenshot-dir",
                    str(Path(tmp) / "captures"),
                ]
            )
            resolved = resolve_desktop_config(args)

            self.assertEqual(resolved.size, (1280, 720))
            self.assertEqual(resolved.bpm, 96)
            self.assertEqual(resolved.rings, 9)
            self.assertEqual(PALETTES[resolved.palette_index].name, "Arctic Neon")
            self.assertTrue(resolved.fullscreen)
            self.assertFalse(resolved.hud)
            self.assertFalse(resolved.camera_drift)
            self.assertEqual(resolved.tempo_scale, 1.25)
            self.assertEqual(resolved.screenshot_dir, (Path(tmp) / "captures").resolve())

    def test_missing_default_config_uses_internal_defaults(self):
        args = argparse.Namespace(
            config=None,
            size=None,
            bpm=None,
            rings=None,
            palette=None,
            fullscreen=False,
            no_hud=False,
            no_camera_drift=False,
            screenshot_dir=None,
            backend=None,
        )
        resolved = resolve_desktop_config(args)
        self.assertEqual(resolved.size, (1600, 1000))
        self.assertEqual(resolved.rings, 7)

    def test_write_bmp_creates_dependency_free_screenshot_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shot.bmp"
            image = np.zeros((2, 2, 4), dtype=np.uint8)
            image[0, 0] = [255, 0, 0, 255]

            write_bmp(path, image)

            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 54)
            self.assertEqual(path.read_bytes()[:2], b"BM")


if __name__ == "__main__":
    unittest.main()
