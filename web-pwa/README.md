# Gyroscope Visualizer Web/PWA

Static browser/PWA version of the phone-orientation gyro visualizer.

## What Works

- Explicit `Start Sensors` button.
- iOS Safari `DeviceOrientationEvent.requestPermission()` / `DeviceMotionEvent.requestPermission()` flow.
- Demo Mode for desktop, denied permissions, simulator, and missing sensors.
- Calibration/zero orientation.
- Sensitivity, smoothing, and dead-zone controls.
- Portrait/landscape/free orientation normalization.
- Themes: Neon, Astrolabe, Scientific, Minimal, Dark Glass.
- Motion trails: Off, Short, Medium, Long.
- Compact HUD plus debug diagnostics.
- PWA manifest and service worker.
- Haptic adapter with no-crash fallback.

## Important iPhone Limits

iPhone Safari does not expose native Taptic Engine haptics to normal web pages.

- `Haptics: unavailable` is expected on iPhone web/PWA.
- The haptics toggle remains present because the same app can use `navigator.vibrate` on browsers/devices that support it.
- Real iPhone haptics require a native wrapper or the Swift app.

iPhone motion sensors also require a secure context:

- Use HTTPS for real `Start Sensors` testing on iPhone.
- Plain `http://<LAN-IP>` is useful for layout/demo testing, but sensor permission may not work.
- `Demo Mode` works without HTTPS or hardware sensors.

## Run Locally

From this folder:

```bash
python3 -m http.server 8765
```

Open on the desktop:

```text
http://127.0.0.1:8765/
```

For iPhone visual/demo testing on the same network, browse to the host machine's LAN URL:

```text
http://<computer-lan-ip>:8765/
```

For real iPhone sensor testing, deploy this folder to any HTTPS static host, for example GitHub Pages, Cloudflare Pages, Netlify, or an HTTPS tunnel.

## iPhone Test Flow

1. Open the HTTPS-hosted PWA in iPhone Safari.
2. Tap `Start Sensors`.
3. Accept motion permission.
4. Hold the phone naturally.
5. Tap `Calibrate`.
6. Adjust `Sensitivity`, `Smoothing`, and `Dead Zone`.
7. Switch themes and trail lengths.
8. Enable `Debug` to inspect raw, calibrated, smoothed, and display values.
9. Add to Home Screen if you want standalone PWA mode.

## Manual Checks

- Sensors do not start on page load.
- Permission request only appears after tapping `Start Sensors`.
- Permission denied/unavailable states remain visible and allow Demo Mode.
- Demo Mode animates the same render pipeline.
- Calibration recenters the visual and clears trails.
- Smoothing stabilizes held-still jitter.
- Dead zone suppresses tiny tremors without blocking larger movement.
- Sensitivity scales display motion without changing raw HUD values.
- Themes update canvas, HUD, and controls.
- Trails fade and respect Off/Short/Medium/Long.
- HUD shows sensor state, FPS, orientation values, calibration, settings, theme, mode, and haptic status.
- Debug HUD shows source, interval, sample age, late indicator, and haptic adapter type.
- Page remains responsive in portrait and landscape.
