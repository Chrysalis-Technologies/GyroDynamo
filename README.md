# GyroDynamo

GyroDynamo is now centered on a standalone Windows desktop visualizer:

- Entry point: `Dynam0/GyroDynamoVisPy.py`
- Config: `Dynam0/gyro_desktop_config.json`
- Dev runner: `Dynam0/run_gyro_dynamo_vispy.bat`
- Packaged app builder: `Dynam0/build_gyro_dynamo_desktop.bat`

The active desktop app does not connect to Home Assistant, does not serve MJPEG,
and does not depend on the old Universe/dashboard pipeline.

## Desktop Setup

Create the runtime venv from the repo root:

```bat
py -3 -m venv .venv-win
.venv-win\Scripts\python.exe -m pip install -r requirements-desktop.txt
```

Run the app:

```bat
Dynam0\run_gyro_dynamo_vispy.bat
```

Run with overrides:

```bat
Dynam0\run_gyro_dynamo_vispy.bat --size 1920x1080 --bpm 92 --rings 8 --palette "Ion Aurora" --fullscreen
```

## Configuration

Default settings live in `Dynam0/gyro_desktop_config.json`:

```json
{
  "size": "1600x1000",
  "bpm": 84.0,
  "rings": 7,
  "palette": "Solar Forge",
  "fullscreen": false,
  "camera_drift": true,
  "hud": true,
  "tempo_scale": 1.0,
  "screenshot_dir": "captures",
  "backend": "glfw",
  "beats_per_measure": 8,
  "align_bars": 4
}
```

CLI flags override config values:

```text
--config PATH
--size WIDTHxHEIGHT
--bpm FLOAT
--rings INT
--palette NAME_OR_INDEX
--fullscreen
--no-hud
--no-camera-drift
--screenshot-dir PATH
```

Available palettes:

- `Solar Forge`
- `Ion Aurora`
- `Copper Flux`
- `Arctic Neon`

## Controls

| Key | Action |
| --- | --- |
| `Space` | Pause or resume |
| `Up` / `Down` | Increase or decrease BPM |
| `Left` / `Right` | Adjust tempo scale |
| `C` | Toggle automatic camera drift |
| `R` | Cycle color palette |
| `+` / `-` | Add or remove rings |
| `H` | Toggle HUD |
| `S` | Save screenshot |
| `F` | Toggle fullscreen |
| `Esc` / `Q` | Quit |

You can also drag the BPM, tempo, and ring-count sliders or click a palette
chip in the on-canvas control panel.

Screenshots are written as `.bmp` files to the configured `screenshot_dir`.

## Packaged Windows App

Build an onedir packaged app with PyInstaller:

```bat
Dynam0\build_gyro_dynamo_desktop.bat
```

The build script creates `.venv-win-build`, installs:

- `requirements-desktop.txt`
- `requirements-build.txt`

Output:

```text
dist\GyroDynamoDesktop\GyroDynamoDesktop.exe
```

Build outputs are ignored by git.

## Tests

Run the focused desktop tests:

```bat
.venv-win\Scripts\python.exe -m unittest tests.test_gyro_desktop_config
```

Run the smoke-test startup path:

```bat
.venv-win\Scripts\python.exe Dynam0\GyroDynamoVisPy.py --smoke-test
```

Optional smoke screenshot:

```bat
.venv-win\Scripts\python.exe Dynam0\GyroDynamoVisPy.py --smoke-test --smoke-screenshot --screenshot-dir Dynam0\captures
```

## Legacy Prototypes

The Swift/iOS Metal app remains a separate track under `GyroDynamo/` and
`GyroDynamo.xcodeproj`.

Older Pythonista and pygame experiments remain in `archive/`, `Dynam0/pythonista/`,
and the aligned desktop scripts. The former Home Assistant / Universe renderer
has been archived under:

```text
Dynam0\legacy\home_assistant_universe
```

That archive is preserved for reference only and is not part of the active
standalone desktop app.
