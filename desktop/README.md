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
- Rig controls for adding/removing rings, accelerating/decelerating spin, scaling the object, and adding visual wobble/shake.
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
7. Use `Rig Controls` to add/subtract rings, accelerate/decelerate spin, adjust scale, and add wobble or shake.
8. Switch themes and trail lengths.
9. Enable `Debug` to inspect raw, calibrated, smoothed, display, and rig values.
10. Connect a gamepad and move the sticks if you want controller-driven input.

## Manual Checks

- Input does not start on page load.
- Desktop input starts only after tapping `Start Desktop Input`.
- Pointer movement drives yaw/pitch/roll.
- Arrow keys and `Q`/`E` influence the visualization.
- `R` resets desktop input bias.
- Gamepad input works when a browser exposes the Gamepad API.
- Demo Mode animates the same render pipeline.
- Rig controls update the visualization without requiring sensors or external devices.
- Ring add/remove buttons clamp cleanly from 1 to 12 rings.
- Accel/Decel buttons clamp cleanly from stopped to 3x spin.
- Wobble and shake are visual-only effects and do not change raw input values.
- Calibration recenters the visual and clears trails.
- Smoothing stabilizes input jitter.
- Dead zone suppresses tiny movement without blocking larger movement.
- Sensitivity scales display motion without changing raw HUD values.
- Themes update canvas, HUD, and controls.
- Trails fade and respect Off/Short/Medium/Long.
- HUD shows sensor state, FPS, orientation values, calibration, settings, theme, mode, and haptic status.
- Debug HUD shows source, interval, sample age, late indicator, and haptic adapter type.
