# Desktop Gyro Visualizer Web/PWA

Static desktop browser/PWA version of the gyro visualizer.

## What Works

- Explicit `Start Desktop Input` button.
- Pointer-driven gyro orientation.
- Keyboard-driven tilt/yaw:
  - Arrow keys: pitch/roll.
  - `Q` / `E`: yaw.
  - `R`: reset desktop input bias.
- Optional Gamepad API axes when a controller is connected.
- Demo Mode for hands-free display.
- Calibration/zero orientation.
- Sensitivity, smoothing, and dead-zone controls.
- Portrait/landscape/free display normalization.
- Themes: Neon, Astrolabe, Scientific, Minimal, Dark Glass.
- Motion trails: Off, Short, Medium, Long.
- Compact HUD plus debug diagnostics.
- PWA manifest and service worker.
- Haptic adapter with no-crash fallback using `navigator.vibrate` only where browsers/devices support it.

## Run Locally

From this folder:

```bash
python3 -m http.server 8766
```

Open:

```text
http://127.0.0.1:8766/
```

## Hosted Shape

This folder is intended to be deployed adjacent to the phone PWA:

```text
/phone/
/desktop/
```

## Desktop Test Flow

1. Open the hosted desktop URL in a desktop browser.
2. Tap `Start Desktop Input`.
3. Move the pointer across the viewport.
4. Use arrow keys and `Q`/`E` to add keyboard-driven motion.
5. Tap `Calibrate` to make the current pose neutral.
6. Adjust `Sensitivity`, `Smoothing`, and `Dead Zone`.
7. Switch themes and trail lengths.
8. Enable `Debug` to inspect raw, calibrated, smoothed, and display values.
9. Connect a gamepad and move the sticks if you want controller-driven input.

## Manual Checks

- Input does not start on page load.
- Desktop input starts only after tapping `Start Desktop Input`.
- Pointer movement drives yaw/pitch/roll.
- Arrow keys and `Q`/`E` influence the visualization.
- `R` resets desktop input bias.
- Gamepad input works when a browser exposes the Gamepad API.
- Demo Mode animates the same render pipeline.
- Calibration recenters the visual and clears trails.
- Smoothing stabilizes input jitter.
- Dead zone suppresses tiny movement without blocking larger movement.
- Sensitivity scales display motion without changing raw HUD values.
- Themes update canvas, HUD, and controls.
- Trails fade and respect Off/Short/Medium/Long.
- HUD shows sensor state, FPS, orientation values, calibration, settings, theme, mode, and haptic status.
- Debug HUD shows source, interval, sample age, late indicator, and haptic adapter type.
