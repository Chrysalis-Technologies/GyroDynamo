# GyroDynamo

included file descriptions: 

Try4:

Resonant Gyroscopic Rings Visualizer

This script is an interactive Pythonista (iOS) visualization that simulates a system of concentric rings rotating on shifting axes, inspired by gyroscopes and the machine from Contact. It is designed as both a generative art experiment and a physics demo to explore emergent resonance, beat frequencies, and tumbling motion in multi-axis rotation.

Features
	•	Beat-Lock Mode
Ring spin speeds are offset by multiples of a target BPM. This creates visual “pulses” where the rings align in rhythm with the chosen tempo.
	•	Ratio Mode
Ring speeds are set to small integer ratios of a base rotation, producing exact repeating patterns after a defined cycle length.
	•	Precession (Sliding Axis Wobble)
Each ring’s axis drifts over time, simulating tumbling or non-principal axis rotation. Precession speed can be tuned relative to the beat frequency for subtle or chaotic wobble.
	•	Interactive Controls (via Pythonista UI panel)
	•	Toggle between Beat-Lock and Ratio modes
	•	Adjust Base RPM
	•	Adjust Target BPM
	•	Adjust Precession ratio
	•	Choose number of rings
	•	Start/Stop the simulation
	•	Dynamic Rendering
Uses scene.ShapeNode to draw and animate ring paths smoothly on iOS devices.

Intended Goal

The goal of this script is to create a controllable environment where nested gyroscopic rotations produce emergent rhythmic patterns. By adjusting speed ratios and precession, users can explore:
	•	How phase alignment leads to beat frequencies (visual “resonance” at musical tempos).
	•	How rational vs. irrational spin ratios change repetition and symmetry.
	•	How sliding axes introduce wobble, drift, and complex motion.

It bridges physics concepts (gyroscopic motion, precession, beats) with artistic output, making it useful as a teaching tool, a generative art piece, or simply an experimental visual toy.


phase3:

This script renders a field of 12 concentric rings, each tumbling around its own 3D axis, with a rotating gradient that alternates direction from ring to ring. The visual design is inspired by gyroscopic gimbals and orbital mechanics, but it adds an audio/visual rhythm engine without requiring sound:
	•	Visuals
	•	Each ring is drawn as many tiny line segments projected into 3D space.
	•	A rotating gradient gives the illusion of depth and motion, rather than flat fill colors.
	•	On every beat, rings briefly pulse: line thickness and brightness swell, then fade.
	•	Haptics
	•	A haptic feedback pulse fires every beat, synced to the chosen BPM.
	•	Tapping the screen toggles pause/resume and also produces a haptic tap.
	•	Controls
	•	A vertical slider on the left adjusts ring rotation speed in real time.
	•	A BPM input field lets you set the tempo numerically, defining how often the haptics and visual pulses trigger.

Intended goal:
This piece is an interactive visual–haptic metronome. Instead of showing time as numbers or playing audio clicks, it uses geometry, light, and touch feedback to embody rhythm. It’s part meditative toy, part visualizer, and part tool for exploring how different tempos feel when mapped into a spatial, tactile medium.


GoGoGyro:
A Pythonista script for iOS that renders concentric, differently colored rings rotating in 3D like nested gimbals (think Contact). Each ring spins and tilts on independent axes, but their angular velocities are locked to a musical tempo, producing clean polyrhythms that re‑align (“resolve”) on every measure.

Desktop version: a pygame-powered port lives in `GoGoGyroDesktop.py`. Install pygame and run `python GoGoGyroDesktop.py` (use `--duration 5` for a short headless run). Controls: space toggles pause, up/down arrows adjust BPM.

Intended goal
	•	Visualize gyroscopic/gimbal dynamics with an immediately readable rhythm.
	•	Serve as a silent, beat‑synchronized visual metronome/ambient display.
	•	Explore emergent patterns from simple integer ratios and periodic re‑alignment.
	•	Provide a compact reference for 3D rotation, perspective projection, and UI control in Pythonista.

Key features
	•	Configurable ring count (NUM_RINGS) to match companion “spinning” scripts.
	•	Tempo‑locked motion: all rotations are integer multiples of the bar frequency, so patterns recur every measure at a target BPM.
	•	On‑screen speed controls: play/pause, BPM slider, and ± step buttons (±1/±5/±10).
	•	Depth‑aware drawing: back/front segments rendered with different alpha for occlusion.
	•	Subtle beat/measure pulses (line thickness/alpha) to make the downbeat obvious.
	•	Runs full‑screen at phone‑friendly performance using Pythonista’s scene + ui.

How it works (concise)
	•	Each ring is a parametric circle transformed by Rz(spin) → Rx(tilt_x) → Ry(tilt_y), then perspective‑projected.
	•	Angular rates are tied to the bar angular frequency:
ω_bar = 2π * (BPM/60) / BEATS_PER_MEASURE.
Per‑ring rates are small integer multiples of ω_bar, creating rich intra‑measure phase relationships with guaranteed measure‑level re‑alignment.
	•	Beat/measure phase drives gentle visual pulses; no audio is generated.

Controls & config
	•	Slider/±/⏯: live BPM adjustment and play/pause.
	•	Tap scene: toggle pause.
	•	Config vars: NUM_RINGS, TARGET_BPM, BEATS_PER_MEASURE, BPM_MIN, BPM_MAX, BPM_SMOOTHING.

Requirements
	•	Pythonista 3 on iOS (uses built‑in scene and ui; no external deps).

Usage
Open the script in Pythonista and run. Adjust BPM via the slider or step buttons. Set NUM_RINGS to keep parity with other ring‑spinning scripts in this repo.

SpinningRings:
A self‑contained Pythonista script (tumbling_gyro_rings_bpm.py) that renders many concentric rings which rotate in 3D on different axes (“tumbling”). The rings are drawn as donuts (outer circle minus inner circle) and projected to 2D with a lightweight perspective camera. The motion can be phase‑locked to a musical tempo so the whole scene repeats on a strict beat, and a subtle flash marks each downbeat.

Intended goal.
Create a compact, dependency‑free playground for:
	•	exploring rhythmic, repeatable motion in a generative visual,
	•	demonstrating minimal 3D rotation + perspective math in Pythonista,
	•	providing an interactive instrument for tempo, acceleration, and camera changes,
	•	serving as a base for audio‑reactive or performance visuals.

Features
	•	3D tumble per ring: each ring rotates about its own normalized axis (Rodrigues rotation), producing interlocking motion in different planes.
	•	BPM‑locked rhythm (optional): set BASE_BPM. Each ring’s angular speed is an integer multiple of the base frequency, so the composition is periodic and returns to the same state every beat. A short beat flash helps you perceive the groove.
	•	Touch controls (iPhone/iPad):
	•	1‑finger drag →/←: change global speed multiplier (tempo scaling)
	•	1‑finger drag ↑/↓: add/remove acceleration (tempo ramps)
	•	Pinch: adjust camera distance (perspective)
	•	Single tap: pause/resume
	•	Double tap: reset tempo scale, acceleration, and camera
(Tap detection is implemented manually—Pythonista’s Touch here doesn’t expose tap_count.)
	•	No external dependencies: uses only Pythonista’s scene and ui modules.

How it works
	•	Geometry: for each ring of radius r and thickness t, the script builds two circles (outer and inner), rotates their points around the ring’s axis by angle θ (Rodrigues formula), then perspective‑projects to screen coordinates and constructs an even‑odd ui.Path to produce a donut outline.
	•	Dynamics: the base beat frequency is f0 = BASE_BPM / 60. The global angular velocity unit is ω₀ = 2π f0 * speed_scale. Ring i advances by θ̇ᵢ = sᵢ kᵢ ω₀, where sᵢ ∈ {+1, −1} sets direction and kᵢ ∈ ℕ is an integer multiplier. Because all kᵢ are integers, the system is periodic; the scene repeats every 60 / (BASE_BPM * |speed_scale|) seconds. A phase accumulator triggers the beat flash.
	•	Rendering: paths are recomputed each frame for smooth motion. Background uses an (r, g, b) tuple; ring colors are RGBA tuples.

Configuration (top‑of‑file constants)
	•	BASE_BPM — tempo of the visual beat.
	•	MULTIPLIERS — per‑ring integer speed multipliers (e.g., [1,2,3,4,6,8,12]).
	•	RING_COUNT, THICKNESS, SEGMENTS — quantity, visual weight, smoothness/perf.
	•	CAMERA_D_INIT — perspective distance; larger values look flatter.
	•	Touch sensitivity: DX_TO_SPEED, DY_TO_ALPHA; clamps: SPEED_CLAMP, ALPHA_CLAMP.
	•	Layout: BASE_RADIUS_FACTOR, SPACING_TARGET (auto‑fits to the screen).

Requirements
	•	Pythonista 3 on iOS/iPadOS.
	•	No additional packages. Open the script in Pythonista and run.

Notes & limits
	•	Z‑ordering is by ring index; there’s no depth test or shading, by design (simple and fast).
	•	Higher SEGMENTS improves smoothness but costs CPU; tune for your device.
	•	To add an audible click each beat, call sound.play_effect('ui:click3') where the beat pulse is triggered.
