"""Visual gameplay-asset prototypes based on IDEEN.md; no game logic is implied."""

from __future__ import annotations

import math

from ..geometry import (
    angle_profile,
    grate,
    i_beam,
    pipe_section,
    rounded_box,
    sphere,
    tee_profile,
    torus,
    u_channel,
    wedge,
)
from .common import ALONG_X, ALONG_Y, cube, cyl, strut
from ..params import Param
from .common import deg
from .lettering import add_text
from .alien import _wiggle
from .dressing import on_floor
from .nature import _boulder, _crystal, crystal_cut_param, crystal_cutter
from .nature import _jitter as _nature_jitter
from .registry import model

NOTE = "Experimental visual prototype only; interaction and Unity gameplay wiring are not implemented."


def _mark(asset, rng, idea: str):
    asset.scale(rng.uniform(0.92, 1.08))
    if asset.p.style.generation < 3:
        # Generations 1/2 (historic, kept bit for bit): one box over the whole model. It filled the free space
        # under the pipe runs, the U-channel and the inside of the loop; generation 3 leaves the prototypes without
        # an own shape, so every part gets an exact mesh collider (collision.complete_static_collision).
        lo, hi = asset.bbox()
        size = tuple(hi[i] - lo[i] for i in range(3))
        center = tuple((hi[i] + lo[i]) / 2 for i in range(3))
        asset.collider(size, center)
    asset.meta.update({"experimental": True, "idea": idea, "gameplay_note": NOTE})


@model("test_utility_trench", "TestUtilityTrench", "environment",
       "Experimental floor utility trench with U-channel, removable-looking cover and conduits")
def test_utility_trench(rng, a):
    body = a.part("Body")
    body.add(u_channel(2.4, 0.38, 0.34, 0.06, "M_RobotDark"),
             loc=(0, 0, 0.17), rot=(math.pi / 2, 0, 0))
    cube(body, (2.25, 0.32, 0.055), (0, 0, 0.37), "M_Platform", bevel=0.015)
    for x in (-0.72, 0, 0.72):
        body.add(pipe_section(0.08, 2.1, 0.018, 8, "M_Metal"),
                 loc=(x, 0, 0.22), rot=ALONG_X)
    for x in (-0.95, 0.95):
        cube(body, (0.06, 0.38, 0.08), (x, 0, 0.4), "M_HazardOrange")
    _mark(a, rng, "utility_trench / coolant routing")


@model("test_pipe_rack", "TestPipeRack", "industrial",
       "Experimental service pipe rack using I-beam uprights and hollow pipe runs")
def test_pipe_rack(rng, a):
    body = a.part("Body")
    for x in (-0.95, 0.95):
        body.add(i_beam(0.48, 1.8, 0.18, 0.07, 0.12, "M_RobotDark"),
                 loc=(x, 0, 0.9), rot=(math.pi / 2, 0, 0))
    for z, radius, material in ((0.52, 0.11, "M_Metal"), (1.03, 0.085, "M_GlowCyan"),
                                (1.54, 0.12, "M_HazardOrange")):
        body.add(pipe_section(radius, 2.15, min(0.025, radius * 0.3), 10, material),
                 loc=(0, 0, z), rot=ALONG_X)
        for x in (-0.82, 0.82):
            body.add(torus(radius * 1.12, 0.018, 10, 4, "M_RobotDark"),
                     loc=(x, 0, z), rot=ALONG_Y)
    for x in (-0.98, 0.98):
        cube(body, (0.32, 0.42, 0.1), (x, 0, 0.05), "M_Metal")
    _mark(a, rng, "pipe_rack")


@model("test_relay_box", "TestRelayBox", "puzzle",
       "Experimental relay and breaker box with rounded housing, grille, switches and cable exits")
def test_relay_box(rng, a):
    body = a.part("Body")
    body.add(rounded_box(1.05, 0.42, 1.25, "M_RobotDark", 0.08), loc=(0, 0, 1.1))
    for x in (-0.29, -0.1, 0.1, 0.29):
        cube(body, (0.06, 0.025, 0.47), (x, -0.223, 1.12), "M_Metal")
    for x, material in ((-0.3, "M_GlowCyan"), (0, "M_Warning"), (0.3, "M_GlowOrange")):
        body.add(rounded_box(0.13, 0.045, 0.18, material, 0.025), loc=(x, -0.245, 1.48))
        cube(body, (0.05, 0.05, 0.12), (x, -0.26, 0.76), "M_HazardOrange")
    for x in (-0.3, 0.3):
        body.add(pipe_section(0.055, 0.5, 0.015, 8, "M_Metal"), loc=(x, 0.24, 0.62))
    _mark(a, rng, "relay_box / breaker_switch")


@model("test_coolant_loop", "TestCoolantLoop", "industrial",
       "Experimental coolant loop with supply and return pipes, elbows and a service valve")
def test_coolant_loop(rng, a):
    body = a.part("Body")
    for x, z, material in ((-0.55, 0.72, "M_GlowCyan"), (0.55, 1.48, "M_GlowOrange")):
        body.add(pipe_section(0.12, 1.5, 0.025, 10, material), loc=(x, 0, z))
        body.add(pipe_section(0.12, 1.1, 0.025, 10, material), loc=(0, 0, z - 0.38),
                 rot=ALONG_X)
        for end_x in (-0.55, 0.55):
            body.add(torus(0.12, 0.025, 10, 4, "M_Metal"),
                     loc=(end_x, 0, z - 0.38), rot=ALONG_Y)
    cube(body, (0.42, 0.5, 0.32), (0, 0, 1.1), "M_RobotDark", bevel=0.04)
    cyl(body, 0.1, 0.18, (0, -0.31, 1.1), "M_HazardOrange", rot=ALONG_Y)
    for x in (-0.2, 0.2):
        strut(body, (x, -0.28, 0.85), (x, -0.28, 1.35), 0.025, "M_Metal")
    _mark(a, rng, "coolant_loop / thermal_switch")


@model("test_warning_beacon", "TestWarningBeacon", "tech",
       "Experimental warning beacon with a framed light head and support brackets")
def test_warning_beacon(rng, a):
    body = a.part("Body")
    body.add(rounded_box(0.85, 0.72, 0.18, "M_RobotDark", 0.05), loc=(0, 0, 0.09))
    cyl(body, 0.12, 1.0, (0, 0, 0.68), "M_Metal", sides=8)
    body.add(rounded_box(0.55, 0.55, 0.48, "M_HazardOrange", 0.1), loc=(0, 0, 1.42))
    body.add(sphere(0.24, 8, 4, "M_GlowOrange"), loc=(0, -0.02, 1.43))
    for x in (-0.28, 0.28):
        body.add(angle_profile(0.2, 0.45, 0.1, 0.045, "M_Metal"),
                 loc=(x, 0.02, 1.38), rot=(0, 0, math.pi / 2))
    cube(body, (0.42, 0.04, 0.08), (0, -0.29, 1.42), "M_GlowOrange")
    _mark(a, rng, "warning_lamp / safety beacon")


@model("test_lens_array", "TestLensArray", "puzzle",
       "Experimental lens array for a beam-alignment puzzle; no laser behavior is wired")
def test_lens_array(rng, a):
    body = a.part("Body")
    cube(body, (1.8, 0.65, 0.16), (0, 0, 0.08), "M_RobotDark", bevel=0.025)
    for x, radius, material in ((-0.58, 0.22, "M_GlowCyan"), (0, 0.28, "M_Optic"),
                                (0.58, 0.22, "M_GlowOrange")):
        cyl(body, radius * 1.25, 0.14, (x, 0, 0.23), "M_Metal", sides=10)
        body.add(torus(radius, 0.035, 12, 4, "M_RobotDark"), loc=(x, 0, 0.46), rot=ALONG_Y)
        body.add(sphere(radius * 0.78, 10, 5, material), loc=(x, -0.025, 0.46))
        strut(body, (x, 0.13, 0.22), (x, 0.13, 0.55), 0.035, "M_Metal")
    body.add(wedge(0.3, 0.2, 0.12, "M_HazardOrange"), loc=(0, -0.38, 0.32),
             rot=(math.pi / 2, 0, 0))
    _mark(a, rng, "lens_array / beam alignment")


@model("test_magnetic_lock", "TestMagneticLock", "puzzle",
       "Experimental magnetic rail lock with channel frame, coil and sliding wedge bolt")
def test_magnetic_lock(rng, a):
    body = a.part("Body")
    body.add(u_channel(1.4, 1.0, 0.16, 0.09, "M_RobotDark"),
             loc=(0, 0, 0.88), rot=(math.pi / 2, 0, 0))
    for x in (-0.42, 0.42):
        cyl(body, 0.23, 0.18, (x, -0.14, 0.88), "M_Metal", rot=ALONG_Y)
        for k in range(3):
            body.add(torus(0.18 + k * 0.025, 0.018, 10, 4, "M_GlowCyan"),
                     loc=(x, -0.25, 0.88), rot=ALONG_Y)
    body.add(wedge(0.48, 0.38, 0.22, "M_HazardOrange"), loc=(0, -0.35, 0.82),
             rot=(math.pi / 2, 0, 0))
    cube(body, (1.6, 0.22, 0.14), (0, 0.25, 0.1), "M_Metal")
    _mark(a, rng, "magnetic_lock / sliding rail")


@model("test_scanner_pad", "TestScannerPad", "puzzle",
       "Experimental floor scanner pad with grate surface, guide rails and a status wedge")
def test_scanner_pad(rng, a):
    body = a.part("Body")
    body.add(rounded_box(1.8, 1.5, 0.2, "M_RobotDark", 0.09), loc=(0, 0, -0.1))
    body.add(grate(1.35, 1.05, 0.045, 0.055, 0.07, "M_Metal"), loc=(0, 0, -0.015))
    for x in (-0.78, 0.78):
        body.add(u_channel(0.12, 0.22, 1.18, 0.035, "M_GlowCyan"),
                 loc=(x, 0, 0.055), rot=(math.pi / 2, 0, 0))
    body.add(wedge(0.28, 0.16, 0.08, "M_GlowOrange"), loc=(0, -0.82, 0.04),
             rot=(math.pi / 2, 0, 0))
    _mark(a, rng, "scanner_pad / identity scan")


@model("test_power_routing", "TestPowerRouting", "puzzle",
       "Experimental power-routing board with visible channels and three connection nodes")
def test_power_routing(rng, a):
    body = a.part("Body")
    body.add(rounded_box(1.8, 0.38, 1.15, "M_RobotDark", 0.07), loc=(0, 0, 1.0))
    for x, material in ((-0.56, "M_GlowCyan"), (0, "M_HazardOrange"), (0.56, "M_GlowOrange")):
        body.add(rounded_box(0.22, 0.06, 0.24, material, 0.035), loc=(x, -0.225, 1.36))
        cyl(body, 0.09, 0.06, (x, -0.25, 0.81), "M_Metal", rot=ALONG_Y)
        cyl(body, 0.045, 0.075, (x, -0.29, 0.81), material, rot=ALONG_Y)
    for x in (-0.56, 0, 0.56):
        body.add(pipe_section(0.025, 0.46, 0.007, 6, "M_HazardOrange"),
                 loc=(x, 0.24, 0.82), rot=ALONG_X)
    body.add(tee_profile(0.8, 0.1, 0.04, 0.035, "M_Metal"), loc=(0, -0.25, 1.03))
    _mark(a, rng, "power_routing / relay sequence")


@model("test_thermal_switch", "TestThermalSwitch", "puzzle",
       "Experimental thermal switch with cooling fins, pipe stubs and a temperature selector")
def test_thermal_switch(rng, a):
    body = a.part("Body")
    body.add(rounded_box(1.1, 0.38, 0.95, "M_RobotDark", 0.07), loc=(0, 0, 1.08))
    for x in (-0.37, -0.22, -0.07, 0.08, 0.23, 0.38):
        cube(body, (0.055, 0.06, 0.58), (x, -0.235, 1.08), "M_Metal")
    body.add(torus(0.22, 0.045, 12, 5, "M_GlowCyan"), loc=(0, -0.26, 1.42), rot=ALONG_Y)
    cyl(body, 0.14, 0.08, (0, -0.3, 1.42), "M_HazardOrange", rot=ALONG_Y)
    for x in (-0.32, 0.32):
        body.add(pipe_section(0.07, 0.55, 0.018, 8, "M_Metal"), loc=(x, 0.24, 0.86))
        cyl(body, 0.09, 0.045, (x, -0.23, 0.78), "M_GlowOrange", rot=ALONG_Y)
    _mark(a, rng, "thermal_switch / coolant control")


@model("test_wall_modules", "TestWallModules", "environment",
       "Experimental wall set piece of stacked modules (concepts 'Industrial' / 'Crystal'): 2 x 3 x 0.5 m, plinth, cap "
       "and hazard stripes continue into the neighbour; the inside varies per variant (columns, blocks, accent plates, "
       "vents, pipe, cable duct, ID sign, optional energy crystals)",
       params=[Param("crystals", "choice", "Kristalle", choices=("none", "some", "many"), default="none"),
               Param("dressing", "choice", "Ausstattung", choices=("none", "ruin", "organic"), default="none",
                     description="ruin: freiliegende Rohre, lose Platte, Schutt; organic: Steinplatten, Ranken, "
                                 "Steine und Büsche am Fuß (Geometrie zu den Anstrichen Ruin / Organic)"),
               crystal_cut_param("faceted")])
def test_wall_modules(rng, a):
    """Style test 0.17.0. A *set*: every variant has the same outline and joins its neighbours seamlessly (no random
    scale, stripe period divides the length); what changes is the inside, so a row of them never repeats."""
    m, lights = a.part("Wall"), a.part("Glow")
    length, height, front = 2.0, 3.0, -0.15          # module faces start at y = front (the core's front face)
    cube(m, (length, 0.40, height), (0, 0.05, height / 2), "M_Wall")                         # core slab (joins)
    cube(m, (length, 0.56, 0.22), (0, 0, 0.11), "M_RobotDark")                              # plinth (joins)
    cube(m, (length, 0.58, 0.16), (0, 0, height - 0.08), "M_RobotDark")                     # cap (joins)
    for k in range(10):                                   # stripes: period 0.2 m divides 2 m -> continuous in a row
        x = -length / 2 + 0.1 + k * 0.2
        cube(m, (0.09, 0.02, 0.16), (x, -0.29, 0.11), "M_Warning" if k % 2 else "M_RobotDark", rot=(0, 0.6, 0))
    z0, z1 = 0.26, height - 0.2
    dressing = a.p.option("dressing")  # not rolled: the default keeps every variant exactly as before
    # column layout of this piece: an accent column in the middle, left, right - or none (plain stacks)
    layout = rng.choice(("mid", "mid", "left", "right", "none", "split"))
    gap = 0.06
    if layout == "none":
        columns = [("stack", 0.94), ("stack", 0.94)]
    elif layout == "split":
        columns = [("stack", 0.6), ("stack", 0.6), ("stack", 0.62)]
    else:
        accent = rng.choice((0.3, 0.36, 0.42))
        side = (length - accent - 2 * gap) / 2
        columns = {"mid": [("stack", side), ("accent", accent), ("stack", side)],
                   "left": [("accent", accent), ("stack", 2 * side + gap)],
                   "right": [("stack", 2 * side + gap), ("accent", accent)]}[layout]
    total = sum(w for _, w in columns) + gap * (len(columns) - 1)
    x = -total / 2
    centers = []
    for kind, width in columns:
        centers.append((kind, x + width / 2, width))
        x += width + gap
    accent_share = rng.uniform(0.15, 0.4)                 # how many blocks get an orange (accent) plate
    for kind, cx, width in centers:
        if kind == "accent":                              # accent column with a glowing slot
            cube(m, (width, 0.2, z1 - z0), (cx, front - 0.1, (z0 + z1) / 2), "M_HazardOrange", bevel=0.03)
            slot = rng.uniform(0.45, 0.75) * (z1 - z0)
            cz = rng.uniform(z0 + slot / 2 + 0.15, z1 - slot / 2 - 0.15)
            cube(m, (0.08, 0.04, slot + 0.1), (cx, front - 0.21, cz), "M_RobotDark", bevel=0.01)
            cube(lights, (0.04, 0.02, slot), (cx, front - 0.235, cz), a.p.glow_or("M_GlowOrange"))  # paint: theme
            continue
        blocks = rng.choice((2, 3, 3, 4))
        cuts = sorted(rng.uniform(0.2, 0.8) for _ in range(blocks - 1))
        edges = [z0] + [z0 + c * (z1 - z0) for c in cuts] + [z1]
        for k in range(blocks):
            bz0, bz1 = edges[k] + (0.025 if k else 0), edges[k + 1] - (0.025 if k < blocks - 1 else 0)
            h = bz1 - bz0
            if h < 0.25:
                continue
            depth = rng.choice((0.12, 0.18, 0.24))
            cz = (bz0 + bz1) / 2
            cube(m, (width, depth, h), (cx, front - depth / 2, cz), "M_RobotDark", bevel=0.03)        # block
            face_part = cube(m, (width - 0.06, 0.04, h - 0.06), (cx, front - depth - 0.02, cz), "M_Metal", bevel=0.02)
            if dressing == "organic":  # weathered stone instead of a machined front: irregular, a little proud
                _nature_jitter(m, face_part, rng, 0.018)
            face = front - depth - 0.04
            roll = rng.random()
            if roll < accent_share:                       # accent plate (concept: orange inserts) - the accent
                # material, so paint schemes colour it like the accent column (M_Ground is a floor/base surface)
                cube(m, (width - 0.12, 0.02, h - 0.14), (cx, face - 0.01, cz), "M_HazardOrange", bevel=0.01)
            elif roll < accent_share + 0.25 and h > 0.5:  # vent slats
                for j in range(5):
                    cube(m, (width - 0.16, 0.03, 0.03), (cx, face - 0.015, cz - h / 2 + 0.12 + j * (h - 0.24) / 4),
                         "M_RobotDark")
            for bx in (-1, 1):                            # bolts in the corners
                for bz in (-1, 1):
                    cyl(m, 0.022, 0.03, (cx + bx * (width / 2 - 0.05), face - 0.015, cz + bz * (h / 2 - 0.05)),
                        "M_RobotDark", sides=6, rot=ALONG_Y)
    stacks = [c for c in centers if c[0] == "stack"]
    if rng.random() < 0.45:                               # ID sign
        _, cx, width = rng.choice(stacks)
        sign_z = rng.uniform(z0 + 0.3, 1.6)
        text = f"{rng.choice('ABCDKR')}-{rng.randint(1, 29):02d}"
        cube(m, (0.34, 0.02, 0.16), (cx, front - 0.3, sign_z), "M_Warning", bevel=0.005)
        add_text(m, text, (cx, front - 0.31, sign_z), 0.09, 0.008, "M_RobotDark")
    if rng.random() < 0.5:                                # vertical pipe with brackets
        _, cx, width = rng.choice(stacks)
        px = cx + rng.choice((-1, 1)) * (width / 2 - 0.1)
        cyl(m, 0.05, z1 - z0 - 0.1, (px, front - 0.34, (z0 + z1) / 2), "M_Metal", sides=10)
        for bz in (z0 + 0.4, (z0 + z1) / 2, z1 - 0.4):
            cube(m, (0.14, 0.12, 0.05), (px, front - 0.3, bz), "M_RobotDark", bevel=0.01)
    if rng.random() < 0.5:                                # cable duct along the bottom (ends at the joints)
        cyl(m, 0.035, length - 0.04, (0, front - 0.32, z0 + 0.06), "M_HazardOrange", sides=8, rot=ALONG_X)
    crystals_option = a.p.option("crystals")
    count = {"none": 0, "some": rng.choice((0, 0, 1)), "many": rng.choice((1, 1, 2))}[crystals_option]
    if count:
        crystals, cut = a.part("Crystals"), crystal_cutter(a)
        for c in range(count):
            _, cx, width = stacks[c % len(stacks)] if c == 0 else rng.choice(stacks)
            sx = cx + rng.uniform(-0.2, 0.2) * width
            cube(m, (0.6, 0.45, 0.3), (sx, front - 0.42, 0.15), "M_RobotDark", bevel=0.04)          # socket
            cube(m, (0.5, 0.35, 0.06), (sx, front - 0.42, 0.33), "M_Metal", bevel=0.02)
            _crystal(crystals, (sx, front - 0.42, 0.33), rng.uniform(1.0, 2.0), rng.uniform(0.12, 0.17),
                     (0.0, deg(rng.uniform(-8, 8)), 0.0), cut=cut)
            for k in range(rng.randint(2, 5)):
                foot = (sx + rng.uniform(-0.2, 0.2), front - 0.42 + rng.uniform(-0.1, 0.1), 0.33)
                tilt = (deg(rng.uniform(-30, 10)), deg(rng.uniform(-35, 35)), 0.0)
                _crystal(crystals, foot, rng.uniform(0.3, 0.8), rng.uniform(0.05, 0.09), tilt, sides=rng.choice((5, 6)),
                         cut=cut)
        if crystals_option == "many":                     # crystals breaking out of a stack
            _, cx, width = rng.choice(stacks)
            for k in range(rng.randint(1, 3)):
                foot = (cx + rng.uniform(-0.3, 0.3) * width, front - 0.25, rng.uniform(1.0, 2.4))
                _crystal(crystals, foot, rng.uniform(0.3, 0.6), rng.uniform(0.05, 0.09),
                         (deg(rng.uniform(55, 80)), deg(rng.uniform(-25, 25)), 0.0), sides=6, cut=cut)
    if dressing == "ruin":
        _ruin_dressing(rng, m, length, front, z0, z1)
    elif dressing == "organic":
        _organic_dressing(rng, m, length, front, height)
    # no random scale (unlike the other prototypes): set pieces must keep their 2 m length to join
    a.meta.update({"experimental": True, "idea": "wall_modules set (style test 0.17.0)", "gameplay_note": NOTE,
                   "layout": layout, "set_length_m": length})


_on_floor = on_floor  # the shared dressing helper (models/dressing.py); the wall's dressing keeps its own rolls


def _ruin_dressing(rng, m, length, front, z0, z1):
    """Concept 'Ruin': an exposed pipe run with couplings, a torn plate leaning against the wall, rubble at the foot.
    Everything stays within the piece's 2 m (x) - only the front changes, so set pieces still join."""
    pz = rng.uniform(z0 + 0.9, z1 - 0.4)
    run = length - 0.3
    cyl(m, 0.07, run, (0, front - 0.42, pz), "M_Metal", sides=10, rot=ALONG_X)            # horizontal pipe
    for x in (-run / 2 + 0.25, rng.uniform(-0.2, 0.2), run / 2 - 0.25):                    # couplings + brackets
        cyl(m, 0.09, 0.08, (x, front - 0.42, pz), "M_RobotDark", sides=10, rot=ALONG_X)
        cube(m, (0.06, 0.3, 0.06), (x, front - 0.27, pz), "M_RobotDark")
    down_x = rng.choice((-1, 1)) * (run / 2 - 0.12)                                         # elbow down to the floor
    cyl(m, 0.07, pz - 0.05, (down_x, front - 0.42, (pz - 0.05) / 2), "M_Metal", sides=10)
    cube(m, (0.18, 0.18, 0.18), (down_x, front - 0.42, pz), "M_RobotDark", bevel=0.02)
    cube(m, (0.62, 0.04, 0.9), (rng.uniform(-0.45, 0.45), front - 0.55, 0.47), "M_Metal", bevel=0.01,
         rot=(math.radians(rng.uniform(14, 24)), 0.0, math.radians(rng.uniform(-8, 8))))  # torn plate, leaning
    _on_floor(m, m.parts[-1])
    for _ in range(rng.randint(7, 12)):                                                    # rubble at the foot
        s = rng.uniform(0.08, 0.2)
        chunk = cube(m, (s * rng.uniform(0.8, 1.5), s * rng.uniform(0.7, 1.2), s * rng.uniform(0.5, 0.9)),
                     (rng.uniform(-length / 2 + 0.15, length / 2 - 0.15), front - rng.uniform(0.35, 0.8), s * 0.3),
                     rng.choice(("M_Wall", "M_RobotDark", "M_Metal")),
                     rot=(math.radians(rng.uniform(-30, 30)), math.radians(rng.uniform(-30, 30)),
                          rng.uniform(0, math.pi)))
        _on_floor(m, chunk)


def _organic_dressing(rng, m, length, front, height):
    """Concept 'Organic': vines hanging from the cap with leaves, stones and bushes at the foot. The vines and leaves
    use the ground material, so a paint scheme colours them (Organic: moss green)."""
    for _ in range(rng.randint(3, 6)):
        x0 = rng.uniform(-length / 2 + 0.15, length / 2 - 0.15)
        steps = rng.randint(4, 9)
        lim = length / 2 - 0.16  # vines and their leaves stay inside the piece: the joint stays clean
        pts = [(max(-lim, min(lim, x)), y, z)
               for x, y, z in _wiggle(rng, (x0, front - 0.33, height - 0.12), -0.28, steps, 0.1, floor=0.3)]
        for k, (p1, p2) in enumerate(zip(pts, pts[1:])):
            strut(m, p1, p2, 0.022 * (1 - k / (steps + 1)) + 0.008, "M_Ground", sides=5)
            if rng.random() < 0.75:
                ang = rng.uniform(-60, 60)
                cube(m, (0.13, 0.012, 0.07), (p2[0] + 0.05 * (1 if ang > 0 else -1), p2[1] - 0.01, p2[2]), "M_Ground",
                     rot=(0.0, math.radians(ang), 0.0))
    first = len(m.parts)
    for _ in range(rng.randint(4, 7)):                                                     # stones at the foot
        s = rng.uniform(0.15, 0.32)
        _boulder(rng, m, (rng.uniform(-length / 2 + 0.2, length / 2 - 0.2), front - rng.uniform(0.35, 0.7), 0.0),
                 (s * 1.3, s, s * 0.7), "M_Wall")
    for _ in range(rng.randint(2, 4)):                                                     # bushes
        bx, by = rng.uniform(-length / 2 + 0.25, length / 2 - 0.25), front - rng.uniform(0.35, 0.6)
        for k in range(rng.randint(5, 8)):
            yaw = rng.uniform(0, 2 * math.pi)
            cube(m, (0.07, 0.012, 0.28), (bx + math.cos(yaw) * 0.08, by + math.sin(yaw) * 0.08, 0.14), "M_Ground",
                 rot=(math.radians(rng.uniform(-35, 35)), math.radians(rng.uniform(-35, 35)), yaw))
    for part in m.parts[first:]:  # tilted stones and blades must not reach below the floor (the asset would re-pivot)
        _on_floor(m, part)
