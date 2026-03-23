# GyroDynamo

included file descriptions: 

Try4:

Resonant Gyroscopic Rings Visualizer

This script is an interactive Pythonista (iOS) visualization that simulates a system of concentric rings rotating on shifting axes, inspired by gyroscopes and the machine from Contact. It is designed as both a generative art experiment and a physics demo to explore emergent resonance, beat frequencies, and tumbling motion in multi-axis rotation.

Features
	?	Beat-Lock Mode
Ring spin speeds are offset by multiples of a target BPM. This creates visual ?pulses? where the rings align in rhythm with the chosen tempo.
	?	Ratio Mode
Ring speeds are set to small integer ratios of a base rotation, producing exact repeating patterns after a defined cycle length.
	?	Precession (Sliding Axis Wobble)
Each ring?s axis drifts over time, simulating tumbling or non-principal axis rotation. Precession speed can be tuned relative to the beat frequency for subtle or chaotic wobble.
	?	Interactive Controls (via Pythonista UI panel)
	?	Toggle between Beat-Lock and Ratio modes
	?	Adjust Base RPM
	?	Adjust Target BPM
	?	Adjust Precession ratio
	?	Choose number of rings
	?	Start/Stop the simulation
	?	Dynamic Rendering
Uses scene.ShapeNode to draw and animate ring paths smoothly on iOS devices.

Intended Goal

The goal of this script is to create a controllable environment where nested gyroscopic rotations produce emergent rhythmic patterns. By adjusting speed ratios and precession, users can explore:
	?	How phase alignment leads to beat frequencies (visual ?resonance? at musical tempos).
	?	How rational vs. irrational spin ratios change repetition and symmetry.
	?	How sliding axes introduce wobble, drift, and complex motion.

It bridges physics concepts (gyroscopic motion, precession, beats) with artistic output, making it useful as a teaching tool, a generative art piece, or simply an experimental visual toy.


phase3:

This script renders a field of 12 concentric rings, each tumbling around its own 3D axis, with a rotating gradient that alternates direction from ring to ring. The visual design is inspired by gyroscopic gimbals and orbital mechanics, but it adds an audio/visual rhythm engine without requiring sound:
	?	Visuals
	?	Each ring is drawn as many tiny line segments projected into 3D space.
	?	A rotating gradient gives the illusion of depth and motion, rather than flat fill colors.
	?	On every beat, rings briefly pulse: line thickness and brightness swell, then fade.
	?	Haptics
	?	A haptic feedback pulse fires every beat, synced to the chosen BPM.
	?	Tapping the screen toggles pause/resume and also produces a haptic tap.
	?	Controls
	?	A vertical slider on the left adjusts ring rotation speed in real time.
	?	A BPM input field lets you set the tempo numerically, defining how often the haptics and visual pulses trigger.

Intended goal:
This piece is an interactive visual?haptic metronome. Instead of showing time as numbers or playing audio clicks, it uses geometry, light, and touch feedback to embody rhythm. It?s part meditative toy, part visualizer, and part tool for exploring how different tempos feel when mapped into a spatial, tactile medium.


GoGoGyro:
A Pythonista script for iOS that renders concentric, differently colored rings rotating in 3D like nested gimbals (think Contact). Each ring spins and tilts on independent axes, but their angular velocities are locked to a musical tempo, producing clean polyrhythms that re?align (?resolve?) on every measure.

Desktop version: a pygame-powered port lives in `GoGoGyroDesktop.py`. Install pygame and run `python GoGoGyroDesktop.py` (use `--duration 5` for a short headless run). Controls: space toggles pause, up/down arrows adjust BPM.

GoGoSolar:
An interactive solar-system simulation that shares the same Pythonista gesture controls as GoGoGyro. `GoGoSolar.py` models the Sun and eight planets with an n-body gravitational solver in astronomical units (AU). Trails trace each orbit while the camera is pitched to give a sense of depth.

Controls mirror the ring visualizer:
        ?       Single-finger tap toggles pause.
        ?       Two-finger tap increases the global time warp (faster orbits).
        ?       Three-or-more finger tap decreases the time warp (slower orbits).

Physics model
        ?       Normalized gravity constant (4??) so that 1 AU orbits complete in roughly one simulation year.
        ?       Semi-implicit integration with a small softening term for stability.
        ?       Per-planet mass, eccentricity, and inclination approximations generate distinct orbital paths.

Intended goal
	?	Visualize gyroscopic/gimbal dynamics with an immediately readable rhythm.
	?	Serve as a silent, beat?synchronized visual metronome/ambient display.
	?	Explore emergent patterns from simple integer ratios and periodic re?alignment.
	?	Provide a compact reference for 3D rotation, perspective projection, and UI control in Pythonista.

Key features
	?	Adjustable ring count via an on-screen slider.
	?	Tempo?locked motion: all rotations are integer multiples of the bar frequency, so patterns recur every measure at a target BPM.
	?	On-screen controls: sliders for BPM and ring count; tap to pause/resume.
	?	Depth?aware drawing: back/front segments rendered with different alpha for occlusion.
	?	Subtle beat/measure pulses (line thickness/alpha) to make the downbeat obvious.
	?	Runs full?screen at phone?friendly performance using Pythonista?s scene + ui.

How it works (concise)
	?	Each ring is a parametric circle transformed by Rz(spin) ? Rx(tilt_x) ? Ry(tilt_y), then perspective?projected.
	?	Angular rates are tied to the bar angular frequency:
?_bar = 2? * (BPM/60) / BEATS_PER_MEASURE.
Per?ring rates are small integer multiples of ?_bar, creating rich intra?measure phase relationships with guaranteed measure?level re?alignment.
	?	Beat/measure phase drives gentle visual pulses; no audio is generated.

Controls & config
	?	Sliders: adjust BPM and ring quantity.
	?	Tap scene: toggle pause.
	?	Config vars: TARGET_BPM, BEATS_PER_MEASURE, BPM_SMOOTHING, MIN_BPM, MAX_BPM, MIN_RING_COUNT, MAX_RING_COUNT, DEFAULT_RING_COUNT.

Requirements
	?	Pythonista 3 on iOS (uses built?in scene and ui; no external deps).

Usage
Open the script in Pythonista and run. Use the sliders to adjust BPM and ring count. Set DEFAULT_RING_COUNT if you want a different starting value to match other ring-spinning scripts in this repo.

SpinningRings:
A self?contained Pythonista script (tumbling_gyro_rings_bpm.py) that renders many concentric rings which rotate in 3D on different axes (?tumbling?). The rings are drawn as donuts (outer circle minus inner circle) and projected to 2D with a lightweight perspective camera. The motion can be phase?locked to a musical tempo so the whole scene repeats on a strict beat, and a subtle flash marks each downbeat.

Intended goal.
Create a compact, dependency?free playground for:
	?	exploring rhythmic, repeatable motion in a generative visual,
	?	demonstrating minimal 3D rotation + perspective math in Pythonista,
	?	providing an interactive instrument for tempo, acceleration, and camera changes,
	?	serving as a base for audio?reactive or performance visuals.

Features
	?	3D tumble per ring: each ring rotates about its own normalized axis (Rodrigues rotation), producing interlocking motion in different planes.
	?	BPM?locked rhythm (optional): set BASE_BPM. Each ring?s angular speed is an integer multiple of the base frequency, so the composition is periodic and returns to the same state every beat. A short beat flash helps you perceive the groove.
	?	Touch controls (iPhone/iPad):
	?	1?finger drag ?/?: change global speed multiplier (tempo scaling)
	?	1?finger drag ?/?: add/remove acceleration (tempo ramps)
	?	Pinch: adjust camera distance (perspective)
	?	Single tap: pause/resume
	?	Double tap: reset tempo scale, acceleration, and camera
(Tap detection is implemented manually?Pythonista?s Touch here doesn?t expose tap_count.)
	?	No external dependencies: uses only Pythonista?s scene and ui modules.

How it works
	?	Geometry: for each ring of radius r and thickness t, the script builds two circles (outer and inner), rotates their points around the ring?s axis by angle ? (Rodrigues formula), then perspective?projects to screen coordinates and constructs an even?odd ui.Path to produce a donut outline.
	?	Dynamics: the base beat frequency is f0 = BASE_BPM / 60. The global angular velocity unit is ?? = 2? f0 * speed_scale. Ring i advances by ??? = s? k? ??, where s? ? {+1, ?1} sets direction and k? ? ? is an integer multiplier. Because all k? are integers, the system is periodic; the scene repeats every 60 / (BASE_BPM * |speed_scale|) seconds. A phase accumulator triggers the beat flash.
	?	Rendering: paths are recomputed each frame for smooth motion. Background uses an (r, g, b) tuple; ring colors are RGBA tuples.

Configuration (top?of?file constants)
	?	BASE_BPM ? tempo of the visual beat.
	?	MULTIPLIERS ? per?ring integer speed multipliers (e.g., [1,2,3,4,6,8,12]).
	?	RING_COUNT, THICKNESS, SEGMENTS ? quantity, visual weight, smoothness/perf.
	?	CAMERA_D_INIT ? perspective distance; larger values look flatter.
	?	Touch sensitivity: DX_TO_SPEED, DY_TO_ALPHA; clamps: SPEED_CLAMP, ALPHA_CLAMP.
	?	Layout: BASE_RADIUS_FACTOR, SPACING_TARGET (auto?fits to the screen).

Requirements
	?	Pythonista 3 on iOS/iPadOS.
	?	No additional packages. Open the script in Pythonista and run.

Notes & limits
<<<<<<< HEAD
	?	Z?ordering is by ring index; there?s no depth test or shading, by design (simple and fast).
	?	Higher SEGMENTS improves smoothness but costs CPU; tune for your device.
	?	To add an audible click each beat, call sound.play_effect('ui:click3') where the beat pulse is triggered.


## GoGoGyro Universe (Home Assistant "Universe Map")

This is a desktop pygame renderer that draws multiple GoGoGyros ("planets") in one window and drives the ring count per planet from Home Assistant entities.

Files (desktop/HA integration):
- `Dynam0/GoGoGyroUniverse.py` (entrypoint)
- `Dynam0/gogogyro_core.py` (shared renderer primitives extracted from the aligned scripts)
- `Dynam0/ha_client.py` (REST polling + cache, with offline resilience)
- `Dynam0/universe_config.py` (JSON + `.env` loader)
- `Dynam0/gyro_stream_server.py` (optional MJPEG server)
- `Dynam0/universe.json` (config template)
- `Dynam0/run_gyro_universe.bat` (Windows runner)

### Windows Setup (venv)

1. Create venv:
```bat
py -3 -m venv .venv-win
```

2. Install deps:
```bat
.venv-win\Scripts\python.exe -m pip install pygame
```

MJPEG streaming (optional) needs Pillow:
```bat
.venv-win\Scripts\python.exe -m pip install pillow
```

### Home Assistant Token (Never Commit)

Create a long-lived access token in Home Assistant:
- Profile -> Long-Lived Access Tokens -> Create Token

Set it via environment variable (default name is `HA_TOKEN`):
- Option A (recommended): set a Windows env var
```bat
setx HA_TOKEN "paste_your_token_here"
```
- Option B: local `.env` file next to `universe.json`
  - Create `Dynam0\.env`:
```env
HA_TOKEN=paste_your_token_here
```

### Configure `universe.json`

Edit `Dynam0/universe.json`:
- `ha.url`: your HA base URL (example `http://homeassistant.local:8123`)
- `ha.context_entity`: the input_select that holds the active galaxy id
- `galaxies.<id>.planets[].loops_entity`: entity id whose `state` parses to an integer loop count
- `render.max_rings_per_planet`: cap per planet; overflow becomes a badge and a thicker outer ring
- `render.layout`: `radial` or `grid`

Ring mapping strategy:
- If `loop_count <= max_rings_per_planet`: draw that many rings.
- If `loop_count > max_rings_per_planet`: draw `max_rings_per_planet`, show `+N loops`, and thicken/brighten the outer ring based on `log10(N)`.

### Run (Window Mode)

From `Dynam0`:
```bat
run_gyro_universe.bat
```

Optional: if the HA context entity is missing/offline, you can force a galaxy:
```bat
run_gyro_universe.bat --galaxy farm
```

Controls:
- `Space`: pause
- `r`: reload config
- `g`: cycle galaxies (only when HA is offline)
- `Esc` / `q`: quit

### Run (MJPEG Streaming Mode For Home Assistant)

Start server (also shows a window):
```bat
run_gyro_universe.bat --serve-mjpeg --host 0.0.0.0 --port 8765
```

Endpoints:
- `http://<pc>:8765/stream.mjpeg`
- `http://<pc>:8765/snapshot.jpg`
- `http://<pc>:8765/` (simple page that shows the stream)

Home Assistant UI:
- Settings -> Devices & services -> Add integration -> `MJPEG IP Camera`
- URL: `http://<pc>:8765/stream.mjpeg`
- Add a `Picture Entity` card using the new camera.

Notes:
- If HA is served over HTTPS and the stream is HTTP, browsers may block it as mixed content. Prefer matching schemes or put the stream behind a reverse proxy.

### Home Assistant YAML Snippets (Quick Testing)

Context entity:
```yaml
input_select:
  gyrodynamo_galaxy:
    name: Gyrodynamo Galaxy
    options:
      - farm
      - work
      - home
    initial: farm
```

Loop count entities (easy test stubs):
```yaml
input_number:
  loops_farm_chickens:
    name: Loops (Farm - Chickens)
    min: 0
    max: 99
    step: 1
  loops_farm_sheep:
    name: Loops (Farm - Sheep)
    min: 0
    max: 99
    step: 1
  loops_farm_cows:
    name: Loops (Farm - Cows)
    min: 0
    max: 99
    step: 1
```

Buttons/scripts to switch galaxy:
```yaml
script:
  set_galaxy_farm:
    sequence:
      - service: input_select.select_option
        target:
          entity_id: input_select.gyrodynamo_galaxy
        data:
          option: farm
```

Optional: launching on-demand (limitations)
- `shell_command` in HA has a hard timeout and is not designed to launch long-running processes.
- On HAOS it runs inside the homeassistant container, not on the host Windows machine.
- Recommended: run the MJPEG server on your Windows box as a startup task/service.

### Troubleshooting

- `401 Unauthorized` / `OFFLINE`:
  - token invalid/expired, or `ha.token_env` doesn't match your env var name
- Entity not found (`404`) or `unknown/unavailable`:
  - loop count is treated as `0` and the planet label shows `?`
- Performance:
  - lower `render.max_rings_per_planet`
  - use `render.layout: grid` for many planets
  - lower window size and/or `render.max_fps`



## GyroDynamo VisPy (Polished Desktop Build)

A new desktop-first renderer built on VisPy lives at:
- `Dynam0/GyroDynamoVisPy.py`
- `Dynam0/run_gyro_dynamo_vispy.bat`

### Install deps
```bat
.venv-win\Scripts\python.exe -m pip install -r requirements-desktop.txt
```

### Run
```bat
Dynam0\run_gyro_dynamo_vispy.bat
```

### Controls
- `Space`: pause/resume
- `Up/Down`: BPM
- `Left/Right`: tempo scale
- `C`: toggle camera drift
- `R`: cycle color palettes
- `F`: fullscreen
- `Esc`: quit

### Optional CLI flags
```bat
.venv-win\Scripts\python.exe Dynam0\GyroDynamoVisPy.py --size 1920x1080 --bpm 92 --rings 8 --fullscreen
```

## Audacity Automation Bridge (Local Python, mod-script-pipe)

This repo now includes a local-only Python bridge for Audacity automation at:

- `audacity_bridge/`
- `docs/audacity_bridge_mcp_design.md`

### What it supports

- Open existing .aup3 projects`r`n- Import audio files`r`n- Select time regions
- Add trailing silence (with version-tolerant fallback strategy)
- Apply effects/macros (raw command passthrough)
- Change tempo
- Export processed output
- Query info/help (`GetInfo`, `Help`)

### Prerequisites

1. Windows with Audacity installed.
2. Python 3.10+.
3. Audacity running with `mod-script-pipe` enabled.

### Enable mod-script-pipe in Audacity (Windows)

1. Open Audacity.
2. Go to `Edit -> Preferences -> Modules`.
3. Set `mod-script-pipe` to `Enabled`.
4. Restart Audacity.

Default Windows pipe names used by this bridge:

- `\\.\pipe\ToSrvPipe`
- `\\.\pipe\FromSrvPipe`

### Install (local editable)

```bat
py -3 -m venv .venv-win
.venv-win\Scripts\python.exe -m pip install -e .
```


If you prefer no install step, run from repo root:

```bat
.\audacity-bridge.bat ping
```

### Optional local config

Copy `.env.audacity.example` to a local env file and customize if needed:

```bat
copy .env.audacity.example .env.audacity
```

Then pass it to CLI commands with `--env-file .env.audacity`.

### Health check

```bat
audacity-bridge ping
```

### CLI usage examples

Raw command:

```bat
audacity-bridge raw "Help:"
```

Open existing project (.aup3):

```bat
audacity-bridge open-project "C:\path\project.aup3"
```

Import audio:

```bat
audacity-bridge import "C:\path\input.wav"
```

Get track info:

```bat
audacity-bridge info --type Tracks --format JSON
```

Export:

```bat
audacity-bridge export "C:\path\output.wav" --format wav
```

### Sample workflow

Runs: connect -> import -> add silence -> change tempo (or effect) -> export.

```bat
audacity-bridge workflow sample --input "C:\path\input.wav" --output "C:\path\out.wav"
```

Use a specific effect/macro command instead of tempo:

```bat
audacity-bridge workflow sample --input "C:\path\input.wav" --output "C:\path\out.wav" --effect "Echo:"
```

Horn cascade workflow (existing layered project):

```bat
audacity-bridge workflow horn-cascade --project "C:\Users\PaulMarzocchi\Documents\Audacity\HORN ALARM.aup3" --output "C:\Users\PaulMarzocchi\Documents\Audacity\HORN ALARM mix.wav" --tail-silence 2.5 --effect "Reverb:"
```

Optional: apply tempo + save a processed project copy:

```bat
audacity-bridge workflow horn-cascade --project "C:\Users\PaulMarzocchi\Documents\Audacity\HORN ALARM.aup3" --output "C:\Users\PaulMarzocchi\Documents\Audacity\HORN ALARM surge.wav" --tempo 6 --effect "Echo:" --save-project-copy "C:\Users\PaulMarzocchi\Documents\Audacity\HORN ALARM processed.aup3"
```\r\n\r\n### Known limitations

- Audacity scripting is single-session and brittle; only one command should run at a time.
- Some command names/parameters vary across Audacity versions and effect/plugin availability.
- Command output format can be inconsistent; parser handles common formats and preserves raw response.
- Some operations may behave differently depending on selection state and UI focus.

### Security note

This bridge is local-only by default and does not start any web server.

Do not expose command execution over an unauthenticated remote service.




=======
	•	Z‑ordering is by ring index; there’s no depth test or shading, by design (simple and fast).
	•	Higher SEGMENTS improves smoothness but costs CPU; tune for your device.
	•	To add an audible click each beat, call sound.play_effect('ui:click3') where the beat pulse is triggered.

## Swift SceneKit desktop prototype

A standalone macOS SceneKit prototype for one nested gyro ring stack is available at:

- `SwiftPrototype/GyroRingStackPrototype.swift`

Build/run on macOS:

```bash
cd SwiftPrototype
swiftc GyroRingStackPrototype.swift -framework Cocoa -framework SceneKit -framework QuartzCore -o GyroRingStackPrototype
./GyroRingStackPrototype
```

Notes:
- Uses nested `SCNTorus` geometry for ring stack visuals.
- Adds independent ring spin animations and a slow global precession.
- Enables mouse camera orbit (`allowsCameraControl = true`) for quick visual inspection.
>>>>>>> eec47662a5d3cb67d020948c9d2dbeb9b85402c9
