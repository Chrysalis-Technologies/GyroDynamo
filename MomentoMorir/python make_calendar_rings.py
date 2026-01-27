import math
from datetime import date, datetime
from pathlib import Path

# ============================================================
# LIFE CALENDAR — WEEK-BASED RADIAL RINGS
# Ring n = n years = 52*n chambers
# Extends exactly to AGE 105 (full 14 rings)
# Red divider every 52 chambers (year boundary)
# ClipPath annulus prevents stroke overshoot
# Auto-sized viewBox (no clipping ever)
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_FILE = SCRIPT_DIR / "life_calendar_age_105_colored.svg"

# -----------------------
# Calendar constants
# -----------------------
YEARS_TARGET = 105
WEEKS_PER_YEAR = 52

# -----------------------
# Geometry
# -----------------------
SCALE = 2.0
R0_INNER = 170 * SCALE
RING_THICKNESS = 30 * SCALE
RING_GAP = 0 * SCALE
STROKE_W = 2 * SCALE
BOUNDARY_STROKE_W = 4 * SCALE
VIEW_PADDING = 40 * SCALE

ANGLE_OFFSET_DEG = -90.0  # rotate left so 0° points up

# -----------------------
# LIFE COMPLETED (progress)
# -----------------------
BIRTH_DATE = date(1991, 6, 17)
INCLUDE_CURRENT_WEEK = False
WEEKS_FILLED_OVERRIDE = None  # set int to override auto-fill
COLOR_UNFILLED = "#222222"  # dark gray but visible on black

# -----------------------
# Colors
# -----------------------
COLOR_BG = "#000000"
COLOR_RED = "#ff0000"

COLOR_WHITE = "#ffffff"
COLOR_POWDER_BLUE = "#B0E0E6"
COLOR_ORANGE = "#ff9900"
COLOR_GREEN = "#00a650"
COLOR_PURPLE = "#6a0dad"
COLOR_MAROON = "#800000"
COLOR_ICE_BLUE = "#aeefff"
COLOR_DARK_GREY = "#1f1f1f"
COLOR_SILVER = "#c0c0c0"
COLOR_BLACK = "#000000"

# You had this as black; leave it as-is, but note it will be invisible on black bg.
# If you want visible ring boundaries, set it to COLOR_WHITE.
COLOR_BOUNDARY = "#000000"

COLOR_ROSE_PINK = "#ff66cc"
COLOR_DOWNPIPE = "#404040"
COLOR_GOLD = "#ffd700"
COLOR_DARK_BROWN = "#502e16ff"  # you set 8-digit hex
COLOR_LIGHT_GREY = "#d3d3d3"

# -----------------------
# Age clock (center text)
# -----------------------
BIRTH_HOUR = 0
BIRTH_MINUTE = 0
SHOW_AGE_TEXT = True
TEXT_COLOR = COLOR_WHITE
TEXT_SIZE = 16 * SCALE
TEXT_LINE_HEIGHT = 1.25
TEXT_FONT_FAMILY = "Arial, sans-serif"
TEXT_FONT_WEIGHT = "bold"

# -----------------------
# Helpers
# -----------------------
def normalize_hex_for_svg(color: str) -> str:
    """
    Inkscape/SVG support for #RRGGBBAA is inconsistent.
    If a color is 8-digit (#RRGGBBAA), strip the alpha to #RRGGBB.
    """
    c = color.strip()
    if c.startswith("#") and len(c) == 9:
        return c[:7]
    return c

def weeks_since_birth(birthdate: date, today=None, include_current_week: bool = False) -> int:
    if today is None:
        today = date.today()
    days = (today - birthdate).days
    if days < 0:
        return 0
    weeks = days // 7
    if include_current_week:
        weeks += 1
    return weeks

if WEEKS_FILLED_OVERRIDE is None:
    WEEKS_FILLED = min(
        weeks_since_birth(BIRTH_DATE, include_current_week=INCLUDE_CURRENT_WEEK),
        YEARS_TARGET * WEEKS_PER_YEAR,
    )
else:
    WEEKS_FILLED = min(WEEKS_FILLED_OVERRIDE, YEARS_TARGET * WEEKS_PER_YEAR)

def years_months_since(birth: date, today: date) -> tuple[int, int]:
    if today < birth:
        return 0, 0
    years = today.year - birth.year
    if (today.month, today.day) < (birth.month, birth.day):
        years -= 1
    months = (today.year - birth.year) * 12 + (today.month - birth.month)
    if today.day < birth.day:
        months -= 1
    if months < 0:
        months = 0
    return years, months

def age_breakdown(birth_dt: datetime, now=None) -> tuple[int, int, int, int, int, int]:
    if now is None:
        now = datetime.now()
    if now < birth_dt:
        return 0, 0, 0, 0, 0, 0
    delta = now - birth_dt
    total_minutes = int(delta.total_seconds() // 60)
    total_hours = total_minutes // 60
    total_days = delta.days
    total_weeks = total_days // 7
    years, months = years_months_since(birth_dt.date(), now.date())
    return years, months, total_weeks, total_days, total_hours, total_minutes

def polar_to_xy(radius: float, angle_deg: float) -> tuple[float, float]:
    rad = math.radians(angle_deg)
    return radius * math.cos(rad), radius * math.sin(rad)

def annular_wedge_path(r_in: float, r_out: float, start_deg: float, end_deg: float) -> str:
    x0_in, y0_in = polar_to_xy(r_in, start_deg)
    x0_out, y0_out = polar_to_xy(r_out, start_deg)
    x1_out, y1_out = polar_to_xy(r_out, end_deg)
    x1_in, y1_in = polar_to_xy(r_in, end_deg)
    delta = (end_deg - start_deg) % 360.0
    large_arc = 1 if delta > 180.0 else 0
    return (
        f"M {x0_in:.6f},{y0_in:.6f} "
        f"L {x0_out:.6f},{y0_out:.6f} "
        f"A {r_out:.6f},{r_out:.6f} 0 {large_arc} 1 {x1_out:.6f},{y1_out:.6f} "
        f"L {x1_in:.6f},{y1_in:.6f} "
        f"A {r_in:.6f},{r_in:.6f} 0 {large_arc} 0 {x0_in:.6f},{y0_in:.6f} Z"
    )

def ring_radii(ring_index_1based: int) -> tuple[float, float]:
    inner = R0_INNER + (ring_index_1based - 1) * (RING_THICKNESS + RING_GAP)
    return inner, inner + RING_THICKNESS

def divider_use(line_id: str, angle: float, stroke: str) -> str:
    stroke = normalize_hex_for_svg(stroke)
    return f'<use href="#{line_id}" transform="rotate({(angle + ANGLE_OFFSET_DEG):.12f})" stroke="{stroke}"/>'

def year_stroke(year: int) -> str:
    if year == 1:
        return COLOR_POWDER_BLUE
    if 2 <= year <= 5:
        return COLOR_ORANGE
    if 6 <= year <= 11:
        return COLOR_GREEN
    if 12 <= year <= 18:
        return COLOR_PURPLE
    if year == 19:
        return COLOR_MAROON
    if 20 <= year <= 21:
        return COLOR_DARK_BROWN
    if 22 <= year <= 23:
        return COLOR_ICE_BLUE
    if 24 <= year <= 30:
        return COLOR_DOWNPIPE
    if 31 <= year <= 34:
        return COLOR_SILVER
    if 35 <= year <= 47:
        return COLOR_ROSE_PINK
    if 48 <= year <= 65:
        return COLOR_GOLD

    # Default for everything else
    return COLOR_LIGHT_GREY

def build_ring_dividers(
    ring_years: int,
    weeks_drawn: int,
    line_id: str,
    ring_start_week_index: int,
    mark_end: bool = False,
) -> str:
    step = 360.0 / (ring_years * WEEKS_PER_YEAR)
    out = ['<g>']

    for i in range(weeks_drawn):
        global_week = ring_start_week_index + i
        global_year = (global_week // WEEKS_PER_YEAR) + 1
        angle = i * step

        # Red year-boundary divider (every 52 weeks) stays red everywhere
        if global_week % WEEKS_PER_YEAR == 0:
            out.append(divider_use(line_id, angle, COLOR_RED))
            continue

        # Filled weeks: turn dividers black
        if global_week < WEEKS_FILLED:
            out.append(divider_use(line_id, angle, COLOR_BLACK))
            continue

        # Year-range color bands (unfilled region)
        out.append(divider_use(line_id, angle, year_stroke(global_year)))

    # End marker at the exact stop point (end of year range)
    if mark_end:
        out.append(divider_use(line_id, weeks_drawn * step, COLOR_RED))

    out.append("</g>")
    return "\n".join(out)

def build_ring_fills(
    ring_years: int,
    weeks_drawn: int,
    ring_start_week_index: int,
    r_in: float,
    r_out: float,
) -> str:
    step = 360.0 / (ring_years * WEEKS_PER_YEAR)
    out = ['<g>']

    for i in range(weeks_drawn):
        global_week = ring_start_week_index + i
        if global_week >= WEEKS_FILLED:
            break
        global_year = (global_week // WEEKS_PER_YEAR) + 1
        start_angle = (i * step) + ANGLE_OFFSET_DEG
        end_angle = start_angle + step
        fill = normalize_hex_for_svg(year_stroke(global_year))
        out.append(
            f'<path d="{annular_wedge_path(r_in, r_out, start_angle, end_angle)}" '
            f'fill="{fill}"/>'
        )

    out.append("</g>")
    return "\n".join(out)

# -----------------------
# Build SVG
# -----------------------
def build_svg() -> str:
    total_weeks = YEARS_TARGET * WEEKS_PER_YEAR

    # ring_specs: (ring_index, ring_years_capacity, weeks_drawn_in_ring, ring_start_week_index)
    ring_specs = []
    weeks_left = total_weeks
    ring_idx = 1
    start_week = 0

    while weeks_left > 0:
        capacity = ring_idx * WEEKS_PER_YEAR
        drawn = min(capacity, weeks_left)
        ring_specs.append((ring_idx, ring_idx, drawn, start_week))
        weeks_left -= drawn
        start_week += drawn
        ring_idx += 1

    # Auto size
    last_ring = ring_specs[-1][0]
    clip_inner = ring_radii(1)[0]
    clip_outer = ring_radii(last_ring)[1]
    VIEW = int(math.ceil(clip_outer + STROKE_W / 2 + VIEW_PADDING))

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-VIEW} {-VIEW} {VIEW*2} {VIEW*2}">')

    # ---------- defs ----------
    svg.append('<defs>')

    # ClipPath annulus (evenodd)
    svg.append('<clipPath id="annulusClip">')
    svg.append('<path fill-rule="evenodd" d="')
    svg.append(f'M 0,0 m -{clip_outer},0')
    svg.append(f'a {clip_outer},{clip_outer} 0 1,0 {clip_outer*2},0')
    svg.append(f'a {clip_outer},{clip_outer} 0 1,0 -{clip_outer*2},0')
    svg.append(f'M 0,0 m -{clip_inner},0')
    svg.append(f'a {clip_inner},{clip_inner} 0 1,0 {clip_inner*2},0')
    svg.append(f'a {clip_inner},{clip_inner} 0 1,0 -{clip_inner*2},0')
    svg.append('"/>')
    svg.append('</clipPath>')

    # Divider templates (one per ring)
    for idx, _, _, _ in ring_specs:
        r_in, r_out = ring_radii(idx)
        svg.append(f'<line id="div{idx}" x1="{r_in}" y1="0" x2="{r_out}" y2="0"/>')

    svg.append('</defs>')

    # ---------- filled weeks (wedges) ----------
    if WEEKS_FILLED > 0:
        svg.append(f'<g clip-path="url(#annulusClip)" stroke="none">')
        for idx, ring_years, weeks_drawn, ring_start_week in ring_specs:
            r_in, r_out = ring_radii(idx)
            svg.append(build_ring_fills(
                ring_years=ring_years,
                weeks_drawn=weeks_drawn,
                ring_start_week_index=ring_start_week,
                r_in=r_in,
                r_out=r_out,
            ))
        svg.append('</g>')

    # ---------- boundary circles ----------
    svg.append(f'<g fill="none" stroke-linecap="butt" stroke-width="{BOUNDARY_STROKE_W}">')
    for idx, _, _, _ in ring_specs:
        r_in, r_out = ring_radii(idx)
        stroke = COLOR_BOUNDARY
        stroke = normalize_hex_for_svg(stroke)
        svg.append(f'<circle cx="0" cy="0" r="{r_in}" stroke="{stroke}"/>')
        svg.append(f'<circle cx="0" cy="0" r="{r_out}" stroke="{stroke}"/>')
    svg.append('</g>')

    # ---------- dividers (clipped) ----------
    svg.append(f'<g clip-path="url(#annulusClip)" fill="none" stroke-linecap="butt" stroke-width="{STROKE_W}">')

    for idx, ring_years, weeks_drawn, ring_start_week in ring_specs:
        is_last = (idx == ring_specs[-1][0])
        svg.append(f'<!-- Ring {idx}: capacity {ring_years} years; drawn {weeks_drawn} weeks -->')
        svg.append(build_ring_dividers(
            ring_years=ring_years,
            weeks_drawn=weeks_drawn,
            line_id=f"div{idx}",
            ring_start_week_index=ring_start_week,
            mark_end=is_last
        ))

    svg.append('</g>')

    # ---------- age clock (center text) ----------
    if SHOW_AGE_TEXT:
        birth_dt = datetime(BIRTH_DATE.year, BIRTH_DATE.month, BIRTH_DATE.day, BIRTH_HOUR, BIRTH_MINUTE)
        years, months, weeks, days, hours, minutes = age_breakdown(birth_dt)
        line_h = TEXT_SIZE * TEXT_LINE_HEIGHT
        lines = [
            f"Years: {years:,}",
            f"Months: {months:,}",
            f"Weeks: {weeks:,}",
            f"Days: {days:,}",
            f"Hours: {hours:,}",
            f"Minutes: {minutes:,}",
        ]
        start_y = -line_h * (len(lines) - 1) / 2.0
        svg.append(
            f'<g text-anchor="middle" font-family="{TEXT_FONT_FAMILY}" '
            f'font-weight="{TEXT_FONT_WEIGHT}" '
            f'font-size="{TEXT_SIZE}" fill="{normalize_hex_for_svg(TEXT_COLOR)}">'
        )
        for idx, line in enumerate(lines):
            y = start_y + (idx * line_h)
            svg.append(f'<text x="0" y="{y:.2f}">{line}</text>')
        svg.append('</g>')

    svg.append('</svg>')
    return "\n".join(svg)

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    OUT_FILE.write_text(build_svg(), encoding="utf-8")
    print(f"Wrote {OUT_FILE.resolve()}")
