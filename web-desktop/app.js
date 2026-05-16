const SENSOR_STATE = Object.freeze({
  NOT_STARTED: "notStarted",
  REQUESTING: "requestingPermission",
  ACTIVE: "active",
  PERMISSION_DENIED: "permissionDenied",
  UNAVAILABLE: "unavailable",
  DEMO: "demoMode",
});

const SENSOR_STATE_TITLE = Object.freeze({
  [SENSOR_STATE.NOT_STARTED]: "Not started",
  [SENSOR_STATE.REQUESTING]: "Requesting permission",
  [SENSOR_STATE.ACTIVE]: "Active",
  [SENSOR_STATE.PERMISSION_DENIED]: "Permission denied",
  [SENSOR_STATE.UNAVAILABLE]: "Unavailable",
  [SENSOR_STATE.DEMO]: "Demo mode",
});

const DEFAULT_SETTINGS = Object.freeze({
  sensitivity: 1.0,
  smoothing: 0.15,
  deadZoneDegrees: 0.5,
  theme: "neon",
  trailLength: "short",
  showHUD: true,
  debugHUD: false,
  hapticsEnabled: true,
  advancedMotionHapticsEnabled: false,
  hapticMotionThresholdDegrees: 30,
  hapticCooldownMs: 500,
  orientationMode: "free",
  ringCount: 5,
  spinSpeed: 1,
  gyroScale: 1,
  wobble: 0.35,
  visualShake: 0,
});

const TRAIL_LIMITS = Object.freeze({
  off: 0,
  short: 24,
  medium: 48,
  long: 96,
});

const THEMES = Object.freeze({
  neon: {
    title: "Neon",
    backgroundTop: "#01040d",
    backgroundBottom: "#060a22",
    ringPrimary: "#19ebff",
    ringSecondary: "#ff59e0",
    accent: "#7affc7",
    text: "#ecfbff",
    axis: "rgba(82,174,255,0.72)",
    glowIntensity: 1.45,
    trailOpacity: 0.44,
    lineWeight: 3.4,
  },
  astrolabe: {
    title: "Astrolabe",
    backgroundTop: "#0d0a0f",
    backgroundBottom: "#1a140f",
    ringPrimary: "#f2ba56",
    ringSecondary: "#70d1e6",
    accent: "#eb5c3d",
    text: "#fff5dc",
    axis: "rgba(199,158,102,0.72)",
    glowIntensity: 0.92,
    trailOpacity: 0.3,
    lineWeight: 3.1,
  },
  scientific: {
    title: "Scientific",
    backgroundTop: "#f7fafd",
    backgroundBottom: "#d1e0eb",
    ringPrimary: "#053f8f",
    ringSecondary: "#0a8c70",
    accent: "#eb3d26",
    text: "#0a1520",
    axis: "rgba(46,61,77,0.58)",
    glowIntensity: 0.38,
    trailOpacity: 0.24,
    lineWeight: 2.4,
  },
  minimal: {
    title: "Minimal",
    backgroundTop: "#0a0b0d",
    backgroundBottom: "#1f2121",
    ringPrimary: "#e0e6e0",
    ringSecondary: "#8f9ea6",
    accent: "#42d1b3",
    text: "#f5fafa",
    axis: "rgba(179,189,194,0.48)",
    glowIntensity: 0.24,
    trailOpacity: 0.18,
    lineWeight: 2.1,
  },
  darkGlass: {
    title: "Dark Glass",
    backgroundTop: "#000306",
    backgroundBottom: "#121a1f",
    ringPrimary: "#addbff",
    ringSecondary: "#c7b3ff",
    accent: "#faa352",
    text: "#effbff",
    axis: "rgba(102,148,179,0.62)",
    glowIntensity: 0.82,
    trailOpacity: 0.34,
    lineWeight: 2.9,
  },
});

const SELECT_OPTIONS = Object.freeze({
  theme: Object.keys(THEMES).map((value) => [value, THEMES[value].title]),
  trailLength: [
    ["off", "Off"],
    ["short", "Short"],
    ["medium", "Medium"],
    ["long", "Long"],
  ],
  orientationMode: [
    ["portrait", "Portrait"],
    ["landscape", "Landscape"],
    ["free", "Free"],
  ],
});

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, Number(value)));
}

function radians(degrees) {
  return (degrees * Math.PI) / 180;
}

function normalizeSignedDegrees(value) {
  let result = Number(value || 0) % 360;
  if (result > 180) result -= 360;
  if (result < -180) result += 360;
  return result;
}

function angleDelta(from, to) {
  return normalizeSignedDegrees(to - from);
}

function orientationMagnitude(orientation) {
  return Math.max(Math.abs(orientation.yaw), Math.abs(orientation.pitch), Math.abs(orientation.roll));
}

function formatOrientation(label, orientation) {
  return `${label} Y ${orientation.yaw.toFixed(1)} · P ${orientation.pitch.toFixed(1)} · R ${orientation.roll.toFixed(1)}`;
}

function colorToRgba(color, alpha = 1) {
  if (color.startsWith("#") && color.length === 7) {
    const r = parseInt(color.slice(1, 3), 16);
    const g = parseInt(color.slice(3, 5), 16);
    const b = parseInt(color.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
  if (color.startsWith("rgb(")) return color.replace("rgb(", "rgba(").replace(")", `, ${alpha})`);
  if (color.startsWith("rgba(")) return color.replace(/,\s*[\d.]+\)$/, `, ${alpha})`);
  return color;
}

class SettingsStore {
  constructor(key = "gyroVisualizer.desktopPwa.settings.v1") {
    this.key = key;
  }

  load() {
    try {
      const raw = localStorage.getItem(this.key);
      const decoded = raw ? JSON.parse(raw) : {};
      return this.clampSettings({ ...DEFAULT_SETTINGS, ...decoded });
    } catch {
      return { ...DEFAULT_SETTINGS };
    }
  }

  save(settings) {
    localStorage.setItem(this.key, JSON.stringify(this.clampSettings(settings)));
  }

  clampSettings(settings) {
    return {
      ...settings,
      sensitivity: clamp(settings.sensitivity, 0.1, 3),
      smoothing: clamp(settings.smoothing, 0.02, 1),
      deadZoneDegrees: clamp(settings.deadZoneDegrees, 0, 5),
      hapticMotionThresholdDegrees: clamp(settings.hapticMotionThresholdDegrees, 1, 180),
      hapticCooldownMs: clamp(settings.hapticCooldownMs, 100, 5000),
      ringCount: Math.round(clamp(settings.ringCount, 1, 12)),
      spinSpeed: clamp(settings.spinSpeed, 0, 3),
      gyroScale: clamp(settings.gyroScale, 0.55, 1.45),
      wobble: clamp(settings.wobble, 0, 2),
      visualShake: clamp(settings.visualShake, 0, 1),
    };
  }
}

class HapticManager {
  constructor(settings) {
    this.enabled = Boolean(settings.hapticsEnabled);
    this.isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent)
      || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    this.canVibrate = "vibrate" in navigator && !this.isIOS;
    this.adapterType = this.canVibrate ? "navigator.vibrate" : "noop";
    this.thresholdArmed = true;
    this.lastThresholdPulse = 0;
    if (!this.canVibrate) console.info("Desktop Gyro Visualizer haptics unavailable in this browser.");
  }

  setEnabled(enabled) {
    this.enabled = Boolean(enabled);
    if (this.enabled) this.selection();
  }

  isAvailable() {
    return this.enabled && this.canVibrate;
  }

  availabilityText() {
    if (!this.enabled) return "disabled";
    return this.canVibrate ? "available" : "unavailable";
  }

  selection() {
    this.pattern([8]);
  }

  lightImpact() {
    this.pattern([12]);
  }

  mediumImpact() {
    this.pattern([18]);
  }

  heavyImpact() {
    this.pattern([28]);
  }

  success() {
    this.pattern([10, 28, 18]);
  }

  warning() {
    this.pattern([22, 36, 22]);
  }

  error() {
    this.pattern([38, 42, 38]);
  }

  calibrationPulse() {
    this.success();
  }

  modeChanged() {
    this.selection();
  }

  thresholdPulse(intensity = 0.5) {
    this.pattern([Math.round(clamp(intensity, 0.1, 1) * 18)]);
  }

  resetThresholdState() {
    this.thresholdArmed = false;
    this.lastThresholdPulse = performance.now();
  }

  evaluateThreshold(angleDegrees, settings, sampleCount) {
    if (!this.enabled || !settings.advancedMotionHapticsEnabled || sampleCount < 15) {
      this.thresholdArmed = angleDegrees < settings.hapticMotionThresholdDegrees;
      return;
    }

    const threshold = settings.hapticMotionThresholdDegrees;
    if (angleDegrees < threshold * 0.72) {
      this.thresholdArmed = true;
      return;
    }

    const now = performance.now();
    if (!this.thresholdArmed || now - this.lastThresholdPulse < settings.hapticCooldownMs) return;
    this.thresholdArmed = false;
    this.lastThresholdPulse = now;
    this.thresholdPulse(angleDegrees / threshold);
  }

  pattern(pattern) {
    if (!this.isAvailable()) return;
    try {
      navigator.vibrate(pattern);
    } catch {
      this.canVibrate = false;
    }
  }
}

class CalibrationManager {
  constructor() {
    this.baselineOrientation = null;
    this.calibratedAt = null;
  }

  calibrate(orientation) {
    this.baselineOrientation = { ...orientation };
    this.calibratedAt = new Date();
  }

  get isCalibrated() {
    return Boolean(this.baselineOrientation);
  }

  relativeOrientation(orientation) {
    if (!this.baselineOrientation) return { ...orientation };
    return {
      yaw: angleDelta(this.baselineOrientation.yaw, orientation.yaw),
      pitch: angleDelta(this.baselineOrientation.pitch, orientation.pitch),
      roll: angleDelta(this.baselineOrientation.roll, orientation.roll),
    };
  }
}

class MotionFilter {
  constructor() {
    this.smoothed = null;
    this.stable = null;
  }

  reset() {
    this.smoothed = null;
    this.stable = null;
  }

  process(relativeOrientation, smoothing, deadZoneDegrees) {
    const smoothed = this.applySmoothing(relativeOrientation, smoothing);
    return this.applyDeadZone(smoothed, deadZoneDegrees);
  }

  applySmoothing(orientation, smoothing) {
    const response = clamp(smoothing, 0.02, 1);
    if (response >= 1 || !this.smoothed) {
      this.smoothed = { ...orientation };
      return { ...orientation };
    }

    const next = {
      yaw: normalizeSignedDegrees(this.smoothed.yaw + angleDelta(this.smoothed.yaw, orientation.yaw) * response),
      pitch: normalizeSignedDegrees(this.smoothed.pitch + angleDelta(this.smoothed.pitch, orientation.pitch) * response),
      roll: normalizeSignedDegrees(this.smoothed.roll + angleDelta(this.smoothed.roll, orientation.roll) * response),
    };
    this.smoothed = next;
    return next;
  }

  applyDeadZone(orientation, deadZoneDegrees) {
    const threshold = Math.max(0, deadZoneDegrees);
    if (threshold === 0 || !this.stable) {
      this.stable = { ...orientation };
      return { ...orientation };
    }

    const delta = {
      yaw: angleDelta(this.stable.yaw, orientation.yaw),
      pitch: angleDelta(this.stable.pitch, orientation.pitch),
      roll: angleDelta(this.stable.roll, orientation.roll),
    };

    if (
      Math.abs(delta.yaw) < threshold
      && Math.abs(delta.pitch) < threshold
      && Math.abs(delta.roll) < threshold
    ) {
      return { ...this.stable };
    }

    this.stable = { ...orientation };
    return { ...orientation };
  }
}

class OrientationNormalizer {
  constructor() {
    this.activeMode = "portrait";
  }

  normalize(orientation, requestedMode) {
    const effectiveMode = requestedMode === "free" ? this.detectScreenMode() : requestedMode;
    this.activeMode = effectiveMode;

    if (effectiveMode !== "landscape") return { ...orientation };

    // Landscape remaps pitch/roll into screen coordinates so wide desktop windows
    // and rotated displays keep tilt controls in the expected display direction.
    return {
      yaw: orientation.yaw,
      pitch: orientation.roll,
      roll: -orientation.pitch,
    };
  }

  detectScreenMode() {
    const angle = screen.orientation?.angle ?? window.orientation ?? 0;
    return Math.abs(Number(angle)) % 180 === 90 ? "landscape" : "portrait";
  }
}

class DesktopInputSensorManager {
  constructor() {
    this.source = "desktop";
    this.updateIntervalMs = 16.7;
    this.onSample = null;
    this.onStatus = null;
    this.isListening = false;
    this.desiredStart = false;
    this.timer = null;
    this.pointer = { x: 0, y: 0, active: false };
    this.keyboard = { yaw: 0, pitch: 0, roll: 0 };
    this.keys = new Set();
    this.lastOrientation = { yaw: 0, pitch: 0, roll: 0 };
    this.lastTimestamp = performance.now();
    this.handlePointerMove = this.handlePointerMove.bind(this);
    this.handleKeyDown = this.handleKeyDown.bind(this);
    this.handleKeyUp = this.handleKeyUp.bind(this);
  }

  start(onSample, onStatus) {
    this.onSample = onSample;
    this.onStatus = onStatus;
    this.desiredStart = true;
    this.publish(SENSOR_STATE.REQUESTING, "Starting desktop input listeners.");
    this.attach();
    this.publish(SENSOR_STATE.ACTIVE, "Desktop input active: pointer, keyboard, and optional gamepad.");
    this.emitSample();
  }

  stop() {
    this.desiredStart = false;
    this.detach();
    this.publish(SENSOR_STATE.NOT_STARTED, "Rig controls work now. Start Desktop Input when you want pointer, keyboard, or gamepad control.");
  }

  pause() {
    this.detach();
  }

  resume() {
    if (this.desiredStart) this.attach();
  }

  attach() {
    this.detach();
    window.addEventListener("pointermove", this.handlePointerMove, { passive: true });
    window.addEventListener("keydown", this.handleKeyDown);
    window.addEventListener("keyup", this.handleKeyUp);
    this.timer = window.setInterval(() => this.emitSample(), this.updateIntervalMs);
    this.isListening = true;
  }

  detach() {
    window.removeEventListener("pointermove", this.handlePointerMove);
    window.removeEventListener("keydown", this.handleKeyDown);
    window.removeEventListener("keyup", this.handleKeyUp);
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    this.isListening = false;
  }

  handlePointerMove(event) {
    const width = Math.max(1, window.innerWidth);
    const height = Math.max(1, window.innerHeight);
    this.pointer = {
      x: clamp(((event.clientX / width) * 2) - 1, -1, 1),
      y: clamp(((event.clientY / height) * 2) - 1, -1, 1),
      active: true,
    };
  }

  handleKeyDown(event) {
    if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "KeyQ", "KeyE", "KeyR"].includes(event.code)) {
      event.preventDefault();
    }
    if (event.code === "KeyR") {
      this.keyboard = { yaw: 0, pitch: 0, roll: 0 };
      this.pointer = { x: 0, y: 0, active: false };
      return;
    }
    this.keys.add(event.code);
  }

  handleKeyUp(event) {
    this.keys.delete(event.code);
  }

  emitSample() {
    const now = performance.now();
    const dt = Math.min(0.05, Math.max(0, (now - this.lastTimestamp) / 1000));
    this.lastTimestamp = now;
    this.integrateKeyboard(dt);

    const gamepad = this.readGamepad();
    const pointerWeight = gamepad ? 0.45 : 1.0;
    const gamepadWeight = gamepad ? 1.0 : 0.0;
    const pointerOrientation = {
      yaw: this.pointer.x * 28,
      pitch: this.pointer.y * 34,
      roll: this.pointer.x * 46,
    };
    const gamepadOrientation = gamepad ?? { yaw: 0, pitch: 0, roll: 0 };
    const orientation = {
      yaw: normalizeSignedDegrees((pointerOrientation.yaw * pointerWeight) + (gamepadOrientation.yaw * gamepadWeight) + this.keyboard.yaw),
      pitch: normalizeSignedDegrees((pointerOrientation.pitch * pointerWeight) + (gamepadOrientation.pitch * gamepadWeight) + this.keyboard.pitch),
      roll: normalizeSignedDegrees((pointerOrientation.roll * pointerWeight) + (gamepadOrientation.roll * gamepadWeight) + this.keyboard.roll),
    };
    const rotationRate = {
      alpha: angleDelta(this.lastOrientation.yaw, orientation.yaw) / Math.max(dt, 0.001),
      beta: angleDelta(this.lastOrientation.pitch, orientation.pitch) / Math.max(dt, 0.001),
      gamma: angleDelta(this.lastOrientation.roll, orientation.roll) / Math.max(dt, 0.001),
    };
    this.lastOrientation = orientation;

    this.onSample?.({
      timestamp: now,
      orientation,
      rotationRate,
      acceleration: null,
      source: "desktop",
      isValid: true,
      statusMessage: gamepad ? "Desktop pointer/keyboard/gamepad input" : "Desktop pointer/keyboard input",
    });
  }

  integrateKeyboard(dt) {
    const rate = 58 * dt;
    if (this.keys.has("ArrowLeft")) this.keyboard.roll -= rate;
    if (this.keys.has("ArrowRight")) this.keyboard.roll += rate;
    if (this.keys.has("ArrowUp")) this.keyboard.pitch -= rate;
    if (this.keys.has("ArrowDown")) this.keyboard.pitch += rate;
    if (this.keys.has("KeyQ")) this.keyboard.yaw -= rate;
    if (this.keys.has("KeyE")) this.keyboard.yaw += rate;

    this.keyboard.yaw = normalizeSignedDegrees(this.keyboard.yaw * 0.998);
    this.keyboard.pitch = normalizeSignedDegrees(this.keyboard.pitch * 0.996);
    this.keyboard.roll = normalizeSignedDegrees(this.keyboard.roll * 0.996);
  }

  readGamepad() {
    const pads = navigator.getGamepads?.() ?? [];
    const pad = Array.from(pads).find((candidate) => candidate && candidate.connected);
    if (!pad) return null;
    const axis = (index) => {
      const value = pad.axes[index] ?? 0;
      return Math.abs(value) < 0.08 ? 0 : value;
    };
    return {
      yaw: axis(2) * 58,
      pitch: axis(1) * 46,
      roll: axis(0) * 58,
    };
  }

  publish(state, message) {
    this.onStatus?.({
      state,
      source: "desktop",
      message,
      updateIntervalMs: this.updateIntervalMs,
    });
  }
}

class DemoSensorManager {
  constructor() {
    this.source = "demo";
    this.updateIntervalMs = 16.7;
    this.onSample = null;
    this.onStatus = null;
    this.timer = null;
    this.startedAt = performance.now();
  }

  start(onSample, onStatus) {
    this.onSample = onSample;
    this.onStatus = onStatus;
    this.startedAt = performance.now();
    this.publish(SENSOR_STATE.DEMO, "Demo mode is generating simulated orientation data.");
    this.timer = window.setInterval(() => this.emitSample(), this.updateIntervalMs);
    this.emitSample();
  }

  stop() {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }

  pause() {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }

  resume() {
    if (!this.timer && this.onSample) {
      this.timer = window.setInterval(() => this.emitSample(), this.updateIntervalMs);
    }
  }

  emitSample() {
    const now = performance.now();
    const t = (now - this.startedAt) / 1000;
    this.onSample?.({
      timestamp: now,
      orientation: {
        yaw: normalizeSignedDegrees(Math.sin(t * 0.43) * 44),
        pitch: normalizeSignedDegrees(Math.sin(t * 0.71) * 28),
        roll: normalizeSignedDegrees(Math.cos(t * 0.59) * 36),
      },
      rotationRate: {
        alpha: Math.cos(t * 0.43) * 18,
        beta: Math.cos(t * 0.71) * 14,
        gamma: -Math.sin(t * 0.59) * 16,
      },
      acceleration: {
        x: Math.sin(t * 0.9) * 0.04,
        y: Math.cos(t * 0.7) * 0.04,
        z: 0,
      },
      source: "demo",
      isValid: true,
      statusMessage: "Synthetic sine/cosine orientation",
    });
  }

  publish(state, message) {
    this.onStatus?.({
      state,
      source: "demo",
      message,
      updateIntervalMs: this.updateIntervalMs,
    });
  }
}

class GyroRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d", { alpha: false });
    this.width = 1;
    this.height = 1;
    this.dpr = 1;
    this.elapsed = 0;
    this.lastTimestamp = performance.now();
    window.addEventListener("resize", () => this.resize());
    this.resize();
  }

  resize() {
    this.dpr = Math.min(2, window.devicePixelRatio || 1);
    this.width = Math.max(1, Math.floor(this.canvas.clientWidth));
    this.height = Math.max(1, Math.floor(this.canvas.clientHeight));
    this.canvas.width = Math.floor(this.width * this.dpr);
    this.canvas.height = Math.floor(this.height * this.dpr);
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
  }

  render(renderState, trailSamples) {
    const now = performance.now();
    const dt = Math.min(0.05, Math.max(0, (now - this.lastTimestamp) / 1000));
    this.lastTimestamp = now;
    this.elapsed += dt;

    const theme = THEMES[renderState.settings.theme] ?? THEMES.neon;
    this.drawBackground(theme);

    const settings = renderState.settings;
    const minDimension = Math.min(this.width, this.height);
    const shake = settings.visualShake ?? 0;
    const center = {
      x: (this.width * 0.5) + (Math.sin(this.elapsed * 39.5) * minDimension * 0.004 * shake),
      y: (this.height * 0.46) + (Math.cos(this.elapsed * 33.25) * minDimension * 0.004 * shake),
    };
    const projectionScale = minDimension * 0.42 * settings.gyroScale;
    const orientation = renderState.displayOrientation;
    const basePhase = ((Math.PI * 2 * this.elapsed) / 30) * settings.spinSpeed;

    this.renderAxisMarkers(center, projectionScale, orientation, theme);
    this.renderTrails(center, projectionScale, trailSamples, theme);
    this.renderGyroRings(center, projectionScale, orientation, basePhase, theme, settings);
    this.renderMotionIndicator(center, projectionScale, orientation, theme, settings);
    this.renderHub(center, minDimension, theme, settings);
  }

  drawBackground(theme) {
    const gradient = this.ctx.createLinearGradient(0, 0, 0, this.height);
    gradient.addColorStop(0, theme.backgroundTop);
    gradient.addColorStop(1, theme.backgroundBottom);
    this.ctx.fillStyle = gradient;
    this.ctx.fillRect(0, 0, this.width, this.height);
  }

  renderGyroRings(center, projectionScale, orientation, basePhase, theme, settings) {
    const ringCount = Math.round(clamp(settings.ringCount, 1, 12));
    const wobble = settings.wobble ?? 0;
    const shake = settings.visualShake ?? 0;
    const radii = buildRingRadii(ringCount);

    radii.forEach((radius, index) => {
      const sign = index % 2 === 0 ? 1 : -1;
      const wobblePhase = this.elapsed * (0.82 + index * 0.09) + index * 0.74;
      const wobbleTilt = radians(8 * wobble);
      const pulse = 1 + (Math.sin(this.elapsed * 8.4 + index) * 0.018 * shake);
      const spin = (sign * basePhase * (index + 1) * (0.82 + index * 0.045))
        + (Math.sin(wobblePhase) * 0.14 * wobble);
      const tiltX = (sign * basePhase * (index + 1) * 0.72)
        + (Math.sin(wobblePhase + 0.4) * wobbleTilt);
      const tiltY = (sign * basePhase * (index + 2) * 0.52)
        + (Math.cos(wobblePhase + 0.9) * wobbleTilt);
      const color = index % 2 === 0 ? theme.ringPrimary : theme.ringSecondary;
      this.renderDepthRing({
        center,
        radius: radius * pulse,
        projectionScale,
        spin,
        tiltX,
        tiltY,
        orientation,
        color,
        theme,
        lineWeightMultiplier: 1 + wobble * 0.04 + shake * 0.16,
        segmentCount: Math.max(96, Math.floor(radius * 180)),
        glyphStride: [9, 11, 13][index % 3],
        glyphPhase: index * 4,
      });
    });
  }

  renderDepthRing(config) {
    const points = [];
    for (let index = 0; index <= config.segmentCount; index += 1) {
      const t = (Math.PI * 2 * index) / config.segmentCount;
      let point = { x: config.radius * Math.cos(t), y: config.radius * Math.sin(t), z: 0 };
      point = rotateZ(point, config.spin);
      point = rotateX(point, config.tiltX);
      point = rotateY(point, config.tiltY);
      point = applyOrientation(point, config.orientation);
      const projected = project(point, config.center, config.projectionScale, config.radius);
      points.push(projected);
    }

    const drawPass = (frontPass) => {
      for (let index = 0; index < points.length - 1; index += 1) {
        const start = points[index];
        const end = points[index + 1];
        const depth = (start.depth + end.depth) * 0.5;
        if (frontPass !== depth >= 0.52) continue;

        const alpha = frontPass ? 0.38 + depth * 0.56 : 0.08 + depth * 0.18;
        const lineWidth = config.theme.lineWeight
          * config.lineWeightMultiplier
          * (frontPass ? 0.8 + depth * 0.88 : 0.38 + depth * 0.36);
        this.strokeSegment(start, end, config.color, alpha, lineWidth);

        if (frontPass && (index + config.glyphPhase) % config.glyphStride === 0) {
          this.strokeSegment(start, end, "#ffffff", 0.36 + depth * 0.34, lineWidth * 1.55);
        }
      }
    };

    this.ctx.save();
    this.ctx.shadowColor = config.color;
    this.ctx.shadowBlur = 13 * config.theme.glowIntensity;
    drawPass(false);
    drawPass(true);
    this.ctx.restore();
  }

  renderAxisMarkers(center, projectionScale, orientation, theme) {
    const axisLength = 1.18;
    const axes = [
      ["X", { x: axisLength, y: 0, z: 0 }, theme.accent],
      ["Y", { x: 0, y: -axisLength, z: 0 }, theme.axis],
      ["Z", { x: 0, y: 0, z: axisLength }, theme.ringSecondary],
    ];

    axes.forEach(([label, vector, color]) => {
      const end3d = applyOrientation(vector, orientation);
      const start = project({ x: 0, y: 0, z: 0 }, center, projectionScale, axisLength);
      const end = project(end3d, center, projectionScale, axisLength);
      this.strokeSegment(start, end, color, 0.18 + end.depth * 0.44, 1.4 + end.depth * 1.4);
      this.ctx.save();
      this.ctx.fillStyle = color;
      this.ctx.globalAlpha = 0.45 + end.depth * 0.42;
      this.ctx.font = "700 12px system-ui, sans-serif";
      this.ctx.fillText(label, end.x + 6, end.y - 4);
      this.ctx.restore();
    });
  }

  renderTrails(center, projectionScale, trailSamples, theme) {
    const count = trailSamples.length;
    if (!count) return;

    trailSamples.forEach((sample, index) => {
      const t = (index + 1) / count;
      const point = orientationIndicatorPoint(sample.orientation, 0.86);
      const projected = project(point, center, projectionScale, 1);
      this.ctx.save();
      this.ctx.globalAlpha = theme.trailOpacity * t * (0.25 + projected.depth * 0.75);
      this.ctx.fillStyle = theme.accent;
      this.ctx.beginPath();
      this.ctx.arc(projected.x, projected.y, 2 + t * 5, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.restore();
    });
  }

  renderMotionIndicator(center, projectionScale, orientation, theme, settings) {
    const point = orientationIndicatorPoint(orientation, 0.86);
    const projected = project(point, center, projectionScale, 1);
    const pulse = 1 + Math.sin(this.elapsed * 11.5) * 0.18 * (settings.visualShake ?? 0);
    this.ctx.save();
    this.ctx.shadowColor = theme.accent;
    this.ctx.shadowBlur = 18;
    this.ctx.fillStyle = colorToRgba(theme.accent, 0.25);
    this.ctx.beginPath();
    this.ctx.arc(projected.x, projected.y, 14 * pulse, 0, Math.PI * 2);
    this.ctx.fill();
    this.ctx.fillStyle = colorToRgba(theme.accent, 0.92);
    this.ctx.beginPath();
    this.ctx.arc(projected.x, projected.y, 5.5 * pulse, 0, Math.PI * 2);
    this.ctx.fill();
    this.ctx.restore();
  }

  renderHub(center, minDimension, theme, settings) {
    const pulse = 1 + Math.sin(this.elapsed * 9.2) * 0.07 * (settings.visualShake ?? 0);
    const radius = Math.max(14, minDimension * 0.026) * pulse;
    this.ctx.save();
    this.ctx.shadowColor = theme.accent;
    this.ctx.shadowBlur = 18 * theme.glowIntensity;
    this.ctx.fillStyle = colorToRgba(theme.text, 0.92);
    this.ctx.beginPath();
    this.ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
    this.ctx.fill();
    this.ctx.fillStyle = "rgba(255,255,255,0.52)";
    this.ctx.beginPath();
    this.ctx.arc(center.x - radius * 0.32, center.y - radius * 0.34, radius * 0.28, 0, Math.PI * 2);
    this.ctx.fill();
    this.ctx.restore();
  }

  strokeSegment(start, end, color, alpha, width) {
    this.ctx.save();
    this.ctx.globalAlpha = clamp(alpha, 0, 1);
    this.ctx.lineWidth = Math.max(0.6, width);
    this.ctx.lineCap = "round";
    this.ctx.strokeStyle = color;
    this.ctx.beginPath();
    this.ctx.moveTo(start.x, start.y);
    this.ctx.lineTo(end.x, end.y);
    this.ctx.stroke();
    this.ctx.restore();
  }
}

function rotateX(point, angle) {
  const c = Math.cos(angle);
  const s = Math.sin(angle);
  return { x: point.x, y: point.y * c - point.z * s, z: point.y * s + point.z * c };
}

function rotateY(point, angle) {
  const c = Math.cos(angle);
  const s = Math.sin(angle);
  return { x: point.x * c + point.z * s, y: point.y, z: -point.x * s + point.z * c };
}

function rotateZ(point, angle) {
  const c = Math.cos(angle);
  const s = Math.sin(angle);
  return { x: point.x * c - point.y * s, y: point.x * s + point.y * c, z: point.z };
}

function applyOrientation(point, orientation) {
  let result = rotateX(point, radians(orientation.pitch));
  result = rotateY(result, radians(orientation.roll));
  result = rotateZ(result, radians(orientation.yaw));
  return result;
}

function project(point, center, projectionScale, depthRadius) {
  const camDistance = 3.5;
  const denominator = Math.max(0.12, point.z + camDistance);
  const depthRaw = Math.max(-1, Math.min(1, point.z / Math.max(0.0001, depthRadius)));
  return {
    x: center.x + (point.x / denominator) * projectionScale,
    y: center.y + (point.y / denominator) * projectionScale,
    depth: 0.5 + depthRaw * 0.5,
  };
}

function buildRingRadii(count) {
  if (count <= 1) return [1];
  return Array.from({ length: count }, (_, index) => {
    const t = index / Math.max(1, count - 1);
    return 1 - t * 0.68;
  });
}

function orientationIndicatorPoint(orientation, radius) {
  let point = { x: 0, y: -radius, z: 0 };
  point = rotateX(point, radians(orientation.pitch));
  point = rotateY(point, radians(orientation.roll));
  point = rotateZ(point, radians(orientation.yaw));
  return point;
}

class GyroApp {
  constructor() {
    this.store = new SettingsStore();
    this.settings = this.store.load();
    this.haptics = new HapticManager(this.settings);
    this.calibration = new CalibrationManager();
    this.filter = new MotionFilter();
    this.normalizer = new OrientationNormalizer();
    this.sensorManager = null;
    this.sensorStatus = {
      state: SENSOR_STATE.NOT_STARTED,
      source: "unavailable",
      message: "Rig controls work now. Start Desktop Input when you want pointer, keyboard, or gamepad control.",
      updateIntervalMs: 16.7,
    };
    this.lastSample = null;
    this.lastNormalized = null;
    this.sampleCount = 0;
    this.trails = [];
    this.lastTrailSampleAt = 0;
    this.lastLoggedState = null;
    this.lastFrameAt = performance.now();
    this.fps = 0;
    this.renderState = {
      rawOrientation: { yaw: 0, pitch: 0, roll: 0 },
      calibratedOrientation: { yaw: 0, pitch: 0, roll: 0 },
      smoothedOrientation: { yaw: 0, pitch: 0, roll: 0 },
      displayOrientation: { yaw: 0, pitch: 0, roll: 0 },
      settings: this.settings,
    };

    this.elements = this.collectElements();
    this.renderer = new GyroRenderer(this.elements.canvas);
    this.bindControls();
    this.applySettingsToControls();
    this.applyTheme();
    this.updateUI();
    this.registerServiceWorker();
    this.installVisibilityHandlers();
    requestAnimationFrame((timestamp) => this.animationLoop(timestamp));
  }

  collectElements() {
    return {
      canvas: document.getElementById("gyroCanvas"),
      startupPanel: document.getElementById("startupPanel"),
      startupStatus: document.getElementById("startupStatus"),
      startupMessage: document.getElementById("startupMessage"),
      startSensorsButton: document.getElementById("startSensorsButton"),
      demoModeButton: document.getElementById("demoModeButton"),
      hud: document.getElementById("hud"),
      collapseHudButton: document.getElementById("collapseHudButton"),
      hudSensorState: document.getElementById("hudSensorState"),
      hudFps: document.getElementById("hudFps"),
      hudDisplayOrientation: document.getElementById("hudDisplayOrientation"),
      hudCalibration: document.getElementById("hudCalibration"),
      hudSensitivity: document.getElementById("hudSensitivity"),
      hudSmoothing: document.getElementById("hudSmoothing"),
      hudDeadZone: document.getElementById("hudDeadZone"),
      hudTheme: document.getElementById("hudTheme"),
      hudTrail: document.getElementById("hudTrail"),
      hudOrientationMode: document.getElementById("hudOrientationMode"),
      hudRig: document.getElementById("hudRig"),
      hudHaptics: document.getElementById("hudHaptics"),
      hudDebug: document.getElementById("hudDebug"),
      hudRaw: document.getElementById("hudRaw"),
      hudCalibrated: document.getElementById("hudCalibrated"),
      hudSmoothed: document.getElementById("hudSmoothed"),
      hudDiagnostics: document.getElementById("hudDiagnostics"),
      drawer: document.querySelector(".control-drawer"),
      drawerStatus: document.getElementById("drawerStatus"),
      drawerBody: document.getElementById("drawerBody"),
      toggleDrawerButton: document.getElementById("toggleDrawerButton"),
      drawerStartStopButton: document.getElementById("drawerStartStopButton"),
      calibrateButton: document.getElementById("calibrateButton"),
      drawerDemoButton: document.getElementById("drawerDemoButton"),
      themeSelect: document.getElementById("themeSelect"),
      trailSelect: document.getElementById("trailSelect"),
      orientationModeSelect: document.getElementById("orientationModeSelect"),
      sensitivitySlider: document.getElementById("sensitivitySlider"),
      smoothingSlider: document.getElementById("smoothingSlider"),
      deadZoneSlider: document.getElementById("deadZoneSlider"),
      sensitivityOutput: document.getElementById("sensitivityOutput"),
      smoothingOutput: document.getElementById("smoothingOutput"),
      deadZoneOutput: document.getElementById("deadZoneOutput"),
      showHudToggle: document.getElementById("showHudToggle"),
      debugHudToggle: document.getElementById("debugHudToggle"),
      hapticsToggle: document.getElementById("hapticsToggle"),
      motionHapticsToggle: document.getElementById("motionHapticsToggle"),
      rigSummary: document.getElementById("rigSummary"),
      removeRingButton: document.getElementById("removeRingButton"),
      addRingButton: document.getElementById("addRingButton"),
      decelerateButton: document.getElementById("decelerateButton"),
      accelerateButton: document.getElementById("accelerateButton"),
      resetRigButton: document.getElementById("resetRigButton"),
      ringCountSlider: document.getElementById("ringCountSlider"),
      spinSpeedSlider: document.getElementById("spinSpeedSlider"),
      gyroScaleSlider: document.getElementById("gyroScaleSlider"),
      wobbleSlider: document.getElementById("wobbleSlider"),
      visualShakeSlider: document.getElementById("visualShakeSlider"),
      ringCountOutput: document.getElementById("ringCountOutput"),
      spinSpeedOutput: document.getElementById("spinSpeedOutput"),
      gyroScaleOutput: document.getElementById("gyroScaleOutput"),
      wobbleOutput: document.getElementById("wobbleOutput"),
      visualShakeOutput: document.getElementById("visualShakeOutput"),
      hapticThresholdSlider: document.getElementById("hapticThresholdSlider"),
      hapticCooldownSlider: document.getElementById("hapticCooldownSlider"),
      hapticThresholdOutput: document.getElementById("hapticThresholdOutput"),
      hapticCooldownOutput: document.getElementById("hapticCooldownOutput"),
    };
  }

  bindControls() {
    this.populateSelect(this.elements.themeSelect, SELECT_OPTIONS.theme);
    this.populateSelect(this.elements.trailSelect, SELECT_OPTIONS.trailLength);
    this.populateSelect(this.elements.orientationModeSelect, SELECT_OPTIONS.orientationMode);

    this.elements.startSensorsButton.addEventListener("click", () => this.startSensors());
    this.elements.drawerStartStopButton.addEventListener("click", () => {
      if ([SENSOR_STATE.ACTIVE, SENSOR_STATE.DEMO].includes(this.sensorStatus.state)) this.stopSensors();
      else this.startSensors();
    });
    this.elements.demoModeButton.addEventListener("click", () => this.enableDemoMode());
    this.elements.drawerDemoButton.addEventListener("click", () => this.enableDemoMode());
    this.elements.calibrateButton.addEventListener("click", () => this.calibrate());

    this.elements.themeSelect.addEventListener("change", (event) => {
      this.updateSetting("theme", event.target.value);
      this.applyTheme();
      this.haptics.modeChanged();
    });
    this.elements.trailSelect.addEventListener("change", (event) => {
      this.updateSetting("trailLength", event.target.value);
      this.trimTrails();
      this.haptics.selection();
    });
    this.elements.orientationModeSelect.addEventListener("change", (event) => {
      this.updateSetting("orientationMode", event.target.value);
      this.filter.reset();
      this.trails = [];
      this.haptics.modeChanged();
    });

    this.bindSlider("sensitivity", this.elements.sensitivitySlider, this.elements.sensitivityOutput, (value) => value.toFixed(1));
    this.bindSlider("smoothing", this.elements.smoothingSlider, this.elements.smoothingOutput, (value) => value.toFixed(2));
    this.bindSlider("deadZoneDegrees", this.elements.deadZoneSlider, this.elements.deadZoneOutput, (value) => `${value.toFixed(1)}°`);
    this.bindSlider("ringCount", this.elements.ringCountSlider, this.elements.ringCountOutput, (value) => `${Math.round(value)}`);
    this.bindSlider("spinSpeed", this.elements.spinSpeedSlider, this.elements.spinSpeedOutput, (value) => `${value.toFixed(1)}x`);
    this.bindSlider("gyroScale", this.elements.gyroScaleSlider, this.elements.gyroScaleOutput, (value) => value.toFixed(2));
    this.bindSlider("wobble", this.elements.wobbleSlider, this.elements.wobbleOutput, (value) => value.toFixed(2));
    this.bindSlider("visualShake", this.elements.visualShakeSlider, this.elements.visualShakeOutput, (value) => value.toFixed(2));
    this.bindSlider("hapticMotionThresholdDegrees", this.elements.hapticThresholdSlider, this.elements.hapticThresholdOutput, (value) => `${value.toFixed(0)}°`);
    this.bindSlider("hapticCooldownMs", this.elements.hapticCooldownSlider, this.elements.hapticCooldownOutput, (value) => `${value.toFixed(0)} ms`);

    this.elements.removeRingButton.addEventListener("click", () => this.adjustRigSetting("ringCount", -1));
    this.elements.addRingButton.addEventListener("click", () => this.adjustRigSetting("ringCount", 1));
    this.elements.decelerateButton.addEventListener("click", () => this.adjustRigSetting("spinSpeed", -0.1));
    this.elements.accelerateButton.addEventListener("click", () => this.adjustRigSetting("spinSpeed", 0.1));
    this.elements.resetRigButton.addEventListener("click", () => this.resetRigControls());

    this.elements.showHudToggle.addEventListener("change", (event) => {
      this.updateSetting("showHUD", event.target.checked);
      this.haptics.selection();
      this.updateUI();
    });
    this.elements.debugHudToggle.addEventListener("change", (event) => {
      this.updateSetting("debugHUD", event.target.checked);
      this.haptics.selection();
      this.updateUI();
    });
    this.elements.hapticsToggle.addEventListener("change", (event) => {
      this.updateSetting("hapticsEnabled", event.target.checked);
      this.haptics.setEnabled(event.target.checked);
      this.updateUI();
    });
    this.elements.motionHapticsToggle.addEventListener("change", (event) => {
      this.updateSetting("advancedMotionHapticsEnabled", event.target.checked);
      this.haptics.resetThresholdState();
      this.haptics.selection();
    });
    this.elements.collapseHudButton.addEventListener("click", () => {
      this.elements.hud.classList.toggle("is-collapsed");
      this.elements.collapseHudButton.textContent = this.elements.hud.classList.contains("is-collapsed") ? "+" : "−";
    });
    this.elements.toggleDrawerButton.addEventListener("click", () => {
      this.elements.drawer.classList.toggle("is-collapsed");
      this.elements.toggleDrawerButton.textContent = this.elements.drawer.classList.contains("is-collapsed") ? "⌃" : "⌄";
    });
  }

  populateSelect(select, options) {
    options.forEach(([value, label]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      select.appendChild(option);
    });
  }

  bindSlider(key, slider, output, formatter) {
    slider.addEventListener("input", (event) => {
      const value = Number(event.target.value);
      this.updateSetting(key, value);
      output.textContent = formatter(this.settings[key]);
      if (["ringCount", "spinSpeed", "gyroScale", "wobble", "visualShake"].includes(key)) {
        this.syncRigControls();
      }
    });
  }

  adjustRigSetting(key, delta) {
    this.updateSetting(key, Number(this.settings[key]) + delta);
    this.syncRigControls();
    this.haptics.selection();
  }

  resetRigControls() {
    this.settings = this.store.clampSettings({
      ...this.settings,
      ringCount: DEFAULT_SETTINGS.ringCount,
      spinSpeed: DEFAULT_SETTINGS.spinSpeed,
      gyroScale: DEFAULT_SETTINGS.gyroScale,
      wobble: DEFAULT_SETTINGS.wobble,
      visualShake: DEFAULT_SETTINGS.visualShake,
    });
    this.renderState.settings = this.settings;
    this.store.save(this.settings);
    this.syncRigControls();
    this.haptics.modeChanged();
    this.updateUI();
  }

  applySettingsToControls() {
    this.elements.themeSelect.value = this.settings.theme;
    this.elements.trailSelect.value = this.settings.trailLength;
    this.elements.orientationModeSelect.value = this.settings.orientationMode;
    this.elements.sensitivitySlider.value = this.settings.sensitivity;
    this.elements.smoothingSlider.value = this.settings.smoothing;
    this.elements.deadZoneSlider.value = this.settings.deadZoneDegrees;
    this.elements.ringCountSlider.value = this.settings.ringCount;
    this.elements.spinSpeedSlider.value = this.settings.spinSpeed;
    this.elements.gyroScaleSlider.value = this.settings.gyroScale;
    this.elements.wobbleSlider.value = this.settings.wobble;
    this.elements.visualShakeSlider.value = this.settings.visualShake;
    this.elements.hapticThresholdSlider.value = this.settings.hapticMotionThresholdDegrees;
    this.elements.hapticCooldownSlider.value = this.settings.hapticCooldownMs;
    this.elements.showHudToggle.checked = this.settings.showHUD;
    this.elements.debugHudToggle.checked = this.settings.debugHUD;
    this.elements.hapticsToggle.checked = this.settings.hapticsEnabled;
    this.elements.motionHapticsToggle.checked = this.settings.advancedMotionHapticsEnabled;
    this.elements.sensitivityOutput.textContent = this.settings.sensitivity.toFixed(1);
    this.elements.smoothingOutput.textContent = this.settings.smoothing.toFixed(2);
    this.elements.deadZoneOutput.textContent = `${this.settings.deadZoneDegrees.toFixed(1)}°`;
    this.syncRigControls();
    this.elements.hapticThresholdOutput.textContent = `${this.settings.hapticMotionThresholdDegrees.toFixed(0)}°`;
    this.elements.hapticCooldownOutput.textContent = `${this.settings.hapticCooldownMs.toFixed(0)} ms`;
  }

  syncRigControls() {
    this.elements.ringCountSlider.value = this.settings.ringCount;
    this.elements.spinSpeedSlider.value = this.settings.spinSpeed;
    this.elements.gyroScaleSlider.value = this.settings.gyroScale;
    this.elements.wobbleSlider.value = this.settings.wobble;
    this.elements.visualShakeSlider.value = this.settings.visualShake;
    this.elements.ringCountOutput.textContent = `${this.settings.ringCount}`;
    this.elements.spinSpeedOutput.textContent = `${this.settings.spinSpeed.toFixed(1)}x`;
    this.elements.gyroScaleOutput.textContent = this.settings.gyroScale.toFixed(2);
    this.elements.wobbleOutput.textContent = this.settings.wobble.toFixed(2);
    this.elements.visualShakeOutput.textContent = this.settings.visualShake.toFixed(2);
    this.elements.rigSummary.textContent = `${this.settings.ringCount} rings · spin ${this.settings.spinSpeed.toFixed(1)}x`;
  }

  updateSetting(key, value) {
    this.settings = this.store.clampSettings({ ...this.settings, [key]: value });
    this.renderState.settings = this.settings;
    this.store.save(this.settings);
    this.updateUI();
  }

  applyTheme() {
    const theme = THEMES[this.settings.theme] ?? THEMES.neon;
    const root = document.documentElement.style;
    root.setProperty("--bg-top", theme.backgroundTop);
    root.setProperty("--bg-bottom", theme.backgroundBottom);
    root.setProperty("--ring-primary", theme.ringPrimary);
    root.setProperty("--ring-secondary", theme.ringSecondary);
    root.setProperty("--accent", theme.accent);
    root.setProperty("--text", theme.text);
    root.setProperty("--axis", theme.axis);
  }

  async startSensors() {
    this.sensorManager?.stop();
    this.resetMotionPipeline(false);
    this.sensorManager = new DesktopInputSensorManager();
    this.haptics.lightImpact();
    console.info("Desktop Gyro Visualizer input start requested.");
    await this.sensorManager.start(
      (sample) => this.processSample(sample),
      (status) => this.handleStatus(status),
    );
  }

  enableDemoMode() {
    this.sensorManager?.stop();
    this.resetMotionPipeline(false);
    this.sensorManager = new DemoSensorManager();
    this.haptics.modeChanged();
    console.info("Desktop Gyro Visualizer demo mode enabled.");
    this.sensorManager.start(
      (sample) => this.processSample(sample),
      (status) => this.handleStatus(status),
    );
  }

  stopSensors() {
    this.sensorManager?.stop();
    this.sensorManager = null;
    this.haptics.lightImpact();
    this.handleStatus({
      state: SENSOR_STATE.NOT_STARTED,
      source: "unavailable",
      message: "Rig controls work now. Start Desktop Input when you want pointer, keyboard, or gamepad control.",
      updateIntervalMs: 16.7,
    });
    console.info("Desktop Gyro Visualizer input stop requested.");
  }

  calibrate() {
    if (!this.lastNormalized) {
      this.handleStatus({
        ...this.sensorStatus,
        message: "No current input sample. Start Desktop Input or Demo Mode before calibrating.",
      });
      this.haptics.warning();
      return;
    }
    this.calibration.calibrate(this.lastNormalized);
    this.filter.reset();
    this.trails = [];
    this.haptics.calibrationPulse();
    this.haptics.resetThresholdState();
    console.info("Desktop Gyro Visualizer calibration set.");
    if (this.lastSample) this.processSample(this.lastSample);
    this.updateUI();
  }

  processSample(sample) {
    this.sampleCount += 1;
    this.lastSample = sample;
    const previousMode = this.normalizer.activeMode;
    const normalized = this.normalizer.normalize(sample.orientation, this.settings.orientationMode);
    if (this.settings.orientationMode === "free" && previousMode !== this.normalizer.activeMode) {
      this.filter.reset();
      this.trails = [];
      this.haptics.resetThresholdState();
    }

    this.lastNormalized = normalized;
    const calibrated = this.calibration.relativeOrientation(normalized);
    const smoothed = this.filter.process(calibrated, this.settings.smoothing, this.settings.deadZoneDegrees);
    const display = {
      yaw: smoothed.yaw * this.settings.sensitivity,
      pitch: smoothed.pitch * this.settings.sensitivity,
      roll: smoothed.roll * this.settings.sensitivity,
    };

    this.renderState = {
      rawOrientation: sample.orientation,
      calibratedOrientation: calibrated,
      smoothedOrientation: smoothed,
      displayOrientation: display,
      settings: this.settings,
    };
    this.appendTrail(display, sample.timestamp);
    this.haptics.evaluateThreshold(orientationMagnitude(calibrated), this.settings, this.sampleCount);
    this.updateUI();
  }

  appendTrail(orientation, timestamp) {
    const limit = TRAIL_LIMITS[this.settings.trailLength] ?? 0;
    if (limit === 0) {
      this.trails = [];
      return;
    }
    if (timestamp - this.lastTrailSampleAt < 42) return;
    this.lastTrailSampleAt = timestamp;
    this.trails.push({ timestamp, orientation: { ...orientation } });
    this.trimTrails();
  }

  trimTrails() {
    const limit = TRAIL_LIMITS[this.settings.trailLength] ?? 0;
    if (limit === 0) {
      this.trails = [];
      return;
    }
    if (this.trails.length > limit) this.trails.splice(0, this.trails.length - limit);
  }

  handleStatus(status) {
    this.sensorStatus = status;
    if (status.state !== this.lastLoggedState) {
      this.lastLoggedState = status.state;
      console.info(`Desktop Gyro Visualizer status: ${SENSOR_STATE_TITLE[status.state]} - ${status.message}`);
    }
    if (status.state === SENSOR_STATE.PERMISSION_DENIED) this.haptics.error();
    if (status.state === SENSOR_STATE.UNAVAILABLE) this.haptics.warning();
    this.updateUI();
  }

  resetMotionPipeline(clearCalibration) {
    this.sampleCount = 0;
    this.lastSample = null;
    this.lastNormalized = null;
    this.trails = [];
    this.filter.reset();
    this.haptics.resetThresholdState();
    if (clearCalibration) this.calibration = new CalibrationManager();
  }

  updateUI() {
    const title = SENSOR_STATE_TITLE[this.sensorStatus.state];
    const theme = THEMES[this.settings.theme] ?? THEMES.neon;
    const showStartup = [
      SENSOR_STATE.NOT_STARTED,
      SENSOR_STATE.REQUESTING,
      SENSOR_STATE.PERMISSION_DENIED,
      SENSOR_STATE.UNAVAILABLE,
    ].includes(this.sensorStatus.state);

    this.elements.startupPanel.classList.toggle("is-hidden", !showStartup);
    this.elements.startupStatus.textContent = title;
    this.elements.startupMessage.textContent = this.sensorStatus.message;

    this.elements.hud.classList.toggle("is-hidden", !this.settings.showHUD);
    this.elements.hudDebug.hidden = !this.settings.debugHUD;
    this.elements.hudSensorState.textContent = title;
    this.elements.hudFps.textContent = `${Math.round(this.fps)} FPS`;
    this.elements.hudDisplayOrientation.textContent = formatOrientation("Display", this.renderState.displayOrientation);
    this.elements.hudCalibration.textContent = `Cal: ${this.calibration.isCalibrated ? this.calibrationAgeText() : "No"}`;
    this.elements.hudSensitivity.textContent = `Sens: ${this.settings.sensitivity.toFixed(1)}`;
    this.elements.hudSmoothing.textContent = `Smooth: ${this.settings.smoothing.toFixed(2)}`;
    this.elements.hudDeadZone.textContent = `Dead: ${this.settings.deadZoneDegrees.toFixed(1)}°`;
    this.elements.hudTheme.textContent = `Theme: ${theme.title}`;
    this.elements.hudTrail.textContent = `Trail: ${this.titleFor("trailLength", this.settings.trailLength)}`;
    this.elements.hudOrientationMode.textContent = `Orient: ${this.titleFor("orientationMode", this.normalizer.activeMode)}`;
    this.elements.hudRig.textContent = `Rig: ${this.settings.ringCount} rings · ${this.settings.spinSpeed.toFixed(1)}x`;
    this.elements.hudHaptics.textContent = `Haptics: ${this.haptics.availabilityText()}`;
    this.elements.hudRaw.textContent = formatOrientation("Raw", this.renderState.rawOrientation);
    this.elements.hudCalibrated.textContent = formatOrientation("Cal", this.renderState.calibratedOrientation);
    this.elements.hudSmoothed.textContent = formatOrientation("Smooth", this.renderState.smoothedOrientation);
    this.elements.hudDiagnostics.textContent = this.diagnosticsLine();

    this.elements.rigSummary.textContent = `${this.settings.ringCount} rings · spin ${this.settings.spinSpeed.toFixed(1)}x`;
    this.elements.drawerStatus.textContent = `${title} · ${theme.title} · ${this.titleFor("trailLength", this.settings.trailLength)} trails · ${this.settings.ringCount} rings`;
    this.elements.drawerStartStopButton.textContent = [SENSOR_STATE.ACTIVE, SENSOR_STATE.DEMO].includes(this.sensorStatus.state)
      ? "Stop Input"
      : "Start Input";
  }

  titleFor(kind, value) {
    const option = SELECT_OPTIONS[kind]?.find(([candidate]) => candidate === value);
    return option?.[1] ?? value;
  }

  calibrationAgeText() {
    if (!this.calibration.calibratedAt) return "Yes";
    const seconds = Math.max(0, (Date.now() - this.calibration.calibratedAt.getTime()) / 1000);
    if (seconds < 4) return "just now";
    if (seconds < 60) return `${Math.round(seconds)}s`;
    return `${Math.round(seconds / 60)}m`;
  }

  diagnosticsLine() {
    const age = this.lastSample ? `${Math.round(performance.now() - this.lastSample.timestamp)} ms` : "n/a";
    const late = this.lastSample && performance.now() - this.lastSample.timestamp > this.sensorStatus.updateIntervalMs * 4 ? "late" : "ok";
    return `src ${this.sensorStatus.source} · interval ${this.sensorStatus.updateIntervalMs.toFixed(1)} ms · age ${age} · ${late} · rig ${this.settings.ringCount}/${this.settings.spinSpeed.toFixed(1)}x · haptics ${this.haptics.adapterType}`;
  }

  installVisibilityHandlers() {
    document.addEventListener("visibilitychange", () => {
      if (!this.sensorManager) return;
      if (document.hidden) {
        this.sensorManager.pause();
      } else {
        this.sensorManager.resume();
      }
    });
    window.addEventListener("orientationchange", () => {
      if (this.settings.orientationMode === "free") {
        this.filter.reset();
        this.trails = [];
      }
    });
  }

  async registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    try {
      await navigator.serviceWorker.register("./sw.js");
    } catch (error) {
      console.info(`Desktop Gyro Visualizer service worker unavailable: ${error.message || error}`);
    }
  }

  animationLoop(timestamp) {
    const dt = Math.max(1, timestamp - this.lastFrameAt);
    this.lastFrameAt = timestamp;
    const instantFps = 1000 / dt;
    this.fps = this.fps ? this.fps * 0.88 + instantFps * 0.12 : instantFps;
    this.renderer.render(this.renderState, this.trails);
    if (Math.floor(timestamp / 250) !== Math.floor((timestamp - dt) / 250)) this.updateUI();
    requestAnimationFrame((nextTimestamp) => this.animationLoop(nextTimestamp));
  }
}

window.addEventListener("DOMContentLoaded", () => {
  window.gyroVisualizer = new GyroApp();
});
