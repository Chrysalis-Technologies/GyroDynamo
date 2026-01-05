import math
from pathlib import Path

# ============================================================
# LIFE CALENDAR — WEEK-BASED RADIAL RINGS
# Ring n = n years = 52*n chambers
# Extends exactly to AGE 105 (full 14 rings)
# Red divider every 52 chambers (year boundary)
# ClipPath annulus prevents stroke overshoot
# Auto-sized viewBox (no clipping ever)
# ============================================================

OUT_FILE = Path("life_calendar_age_105_colored.svg")

# -----------------------
# Calendar constants
# -----------------------
YEARS_TARGET = 105
WEEKS_PER_YEAR = 52

# -----------------------
# Geometry
# -----------------------
R0_INNER = 170
RING_THICKNESS = 30
RING_GAP = 0
STROKE_W = 2
VIEW_PADDING = 40

ANGLE_OFFSET_DEG = -90.0  # rotate left so 0° points up

# -----------------------
# LIFE COMPLETED (progress)
# -----------------------
WEEKS_FILLED = 260          # fill first 5 years (5*52)
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
COLOR_GOLD = "#ffd700"
COLOR_DARK_BROWN = "#502e16ff"  # you set 8-digit hex
COLOR_LIGHT_GREY = "#d3d3d3"

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

def ring_radii(ring_index_1based: int) -> tuple[int, int]:
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
        return COLOR_DARK_GREY
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

        # Red year-boundary divider (every 52 weeks) stays red regardless of fill
        if global_week % WEEKS_PER_YEAR == 0:
            out.append(divider_use(line_id, angle, COLOR_RED))
            continue

        # Filled vs unfilled weeks
        if global_week < WEEKS_FILLED:
            out.append(divider_use(line_id, angle, year_stroke(global_year)))
        else:
            out.append(divider_use(line_id, angle, COLOR_UNFILLED))

    # End marker at the exact stop point (end of year range)
    if mark_end:
        out.append(divider_use(line_id, weeks_drawn * step, COLOR_RED))

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

    # Background (use your COLOR_BG so "filled" colors pop)
    svg.append(f'<rect x="{-VIEW}" y="{-VIEW}" width="{VIEW*2}" height="{VIEW*2}" fill="{normalize_hex_for_svg(COLOR_BG)}"/>')

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

    # ---------- boundary circles ----------
    svg.append(f'<g fill="none" stroke-linecap="butt" stroke-width="{STROKE_W}">')
    for idx, _, _, _ in ring_specs:
        r_in, r_out = ring_radii(idx)
        stroke = COLOR_POWDER_BLUE if idx == 1 else COLOR_BOUNDARY
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

    svg.append('</g></svg>')
    return "\n".join(svg)

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    OUT_FILE.write_text(build_svg(), encoding="utf-8")
    print(f"Wrote {OUT_FILE.resolve()}")
