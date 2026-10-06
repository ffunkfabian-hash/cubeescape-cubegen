"""More building kit: floor hatches, roll-up shutters, crawl shafts, floor grates with a pit, bulkheads and wall
cladding.

Sizes follow the wall module (3 m high, 0.5 m thick) and the 1 m floor grid.
Walkable pieces (``hatch``, ``floor_grate``) have their top at z = 0 like the
platforms; ``wall_panel`` hangs in front of a wall (back side at y = +0.1).
"""

from __future__ import annotations

import math

from ..geometry import prism
from ..params import Param
from .common import ALONG_X, ALONG_Y, cube, cyl, deg, flat_wheel, stripes
from .registry import model

STATUS = {"off": "M_GlowRed", "on": "M_GlowCyan"}


def _status_param():
    return Param("status", "choice", "Glow-Startzustand", choices=("off", "on"), default="off",
                 description="Status-Glow beim Export: off = M_GlowRed, on = M_GlowCyan (Unity schaltet ihn um)")


# --------------------------------------------------------------------------
# floor hatch
# --------------------------------------------------------------------------

@model("hatch", "Hatch", "environment", "Floor hatch (top at z = 0): frame, shaft, lid hinged at the back (Panel), "
       "round lids with a wheel (Wheel)", pivot="top", params=[
           Param("shape", "choice", "Form", choices=("square", "round")),
           Param("size", "float", "Öffnung (m)", lo=0.6, hi=2.0, size=True),
           Param("ladder", "bool", "Leiter nach unten"),
           Param("lid_angle", "float", "Deckel-Winkel offen (°)", lo=30, hi=180, unity=True, default=110),
           _status_param(),
       ])
def hatch(rng, a):
    p = a.p
    shape = p.choice("shape", ["square", "square", "round"])
    s = p.float("size", 0.8, 1.2)
    rim, depth = 0.15, rng.uniform(0.5, 0.9)
    frame = p.material(["M_RobotDark", "M_Metal", "M_Wall"])
    status = STATUS[p.option("status")]
    body, glow = a.part("Body"), a.part("Glow")
    a.meta.update({"shape": shape, "opening_m": round(s, 3)})
    for k in range(4):  # frame flush with the floor + shaft walls below
        ang = math.pi / 2 * k
        dx, dy = round(math.cos(ang)), round(math.sin(ang))
        size = (rim, s + 2 * rim, 0.25) if dx else (s + 2 * rim, rim, 0.25)
        cube(body, size, (dx * (s + rim) / 2, dy * (s + rim) / 2, -0.125), frame, bevel=0.015)
        wall = (0.06, s, depth) if dx else (s, 0.06, depth)
        cube(body, wall, (dx * (s / 2 - 0.03), dy * (s / 2 - 0.03), -0.25 - depth / 2), "M_Ground")
        corner = (s / 2 + rim / 2) * math.sqrt(2)
        cube(glow, (0.05, 0.05, 0.02),
             (math.cos(ang + math.pi / 4) * corner, math.sin(ang + math.pi / 4) * corner, 0.0), status)
    cube(body, (s, s, 0.04), (0, 0, -0.27 - depth), "M_RobotDark")  # dark bottom of the shaft
    if p.bool("ladder", 0.6):
        for x in (-0.2, 0.2):
            cube(body, (0.04, 0.05, depth + 0.2), (x, s / 2 - 0.1, -0.15 - depth / 2), "M_Metal")
        for i in range(int((depth + 0.1) / 0.3)):
            cube(body, (0.4, 0.04, 0.03), (0, s / 2 - 0.1, -0.2 - i * 0.3), "M_Metal")
    hinge = (0.0, s / 2, -0.03)
    lid = a.part("Panel", pivot=hinge)
    lid_mat = p.material(["M_Metal", "M_Platform", "M_HazardOrange"])
    for x in (-s * 0.3, s * 0.3):  # hinge knuckles
        cyl(body, 0.035, 0.12, (x, s / 2 - 0.01, -0.03), "M_Metal", sides=6, rot=(0, math.pi / 2, 0))
    if shape == "round":
        r = s / 2 / math.cos(math.pi / 10)
        c = s * 0.32
        for sx in (-1, 1):  # corner plates: square frame, round opening
            for sy in (-1, 1):
                tri = [(sx * s / 2, sy * s / 2), (sx * (s / 2 - c), sy * s / 2), (sx * s / 2, sy * (s / 2 - c))]
                body.add(prism(tri, 0.06, frame), loc=(0, 0, -0.03))
        cyl(lid, r - 0.01, 0.06, (0, 0, -0.03), lid_mat, sides=10, bevel=0.01)
        cyl(lid, r * 0.8, 0.02, (0, 0, 0.005), "M_RobotDark", sides=10)
        center = (0.0, 0.0, 0.06)
        cyl(lid, 0.05, 0.06, (0, 0, 0.03), "M_RobotDark", sides=8)
        flat_wheel(a.part("Wheel", pivot=center, parent="Panel"), center, radius=s * 0.28)
        a.behaviour("Rotatable", {"target": "Wheel", "glow": "Glow"},
                    {"axis": "up", "step": 90, "speed": 180, "target": 2, "interactive": True},
                    note="unlock wheel on the lid (turns with the lid)")
    else:
        cube(lid, (s - 0.02, s - 0.02, 0.06), (0, 0, -0.03), lid_mat, bevel=0.01)
        cube(lid, (s * 0.35, 0.08, 0.03), (0, -s / 2 + 0.12, 0.015), "M_RobotDark")  # recessed pull handle
        if rng.random() < 0.5:
            stripes(lid, s * 0.8, (0, s * 0.1, 0.002), count=5, width=s * 0.25, height=0.004)
    a.behaviour("Rotatable", {"target": "Panel", "glow": "Glow"},
                {"axis": "right", "step": -p.option("lid_angle"), "speed": 90, "target": 1, "interactive": True},
                note="lid swings up around its hinge at the back (negative step around Unity right = upwards)")


# --------------------------------------------------------------------------
# roll-up shutter
# --------------------------------------------------------------------------

@model("shutter", "Shutter", "environment", "Roll-up shutter or security grille: guide rails, roll housing, "
       "slatted Panel (Door moves it up)", params=[
           Param("style", "choice", "Art", choices=("roller", "grille")),
           Param("width", "float", "Öffnung Breite (m)", lo=1.0, hi=6.0, size=True),
           Param("height", "float", "Öffnung Höhe (m)", lo=1.6, hi=4.0, size=True),
           Param("speed", "float", "Tempo (m/s)", lo=0.1, hi=10.0, unity=True, default=1.0),
       ])
def shutter(rng, a):
    p = a.p
    style = p.choice("style", ["roller", "roller", "grille"])
    width = round(p.float("width", 1.6, 3.6) * 5) / 5
    height = round(p.float("height", 2.4, 3.0) * 5) / 5
    rail, depth = 0.2, rng.uniform(0.35, 0.5)
    frame = p.material(["M_RobotDark", "M_Metal", "M_Wall"])
    box_h = rng.uniform(0.4, 0.55)
    a.meta.update({"style": style, "opening_m": [width, height]})
    for side, x in (("Left", -(width + rail) / 2), ("Right", (width + rail) / 2)):
        m = a.part(f"Frame_{side}")
        cube(m, (rail, depth, height + box_h), (x, 0, (height + box_h) / 2), frame, bevel=0.02)
        cube(m, (0.05, depth * 0.3, height), (x - math.copysign(rail / 2, x), 0, height / 2), "M_Ground")  # guide
        cube(m, (rail + 0.02, depth + 0.02, 0.4), (x, 0, 0.2), "M_Warning")
    top = a.part("Frame_Top")
    cube(top, (width + 0.1, depth + 0.1, box_h), (0, 0, height + box_h / 2), frame, bevel=0.04)
    cyl(top, box_h * 0.42, width + 0.06, (0, 0, height + box_h / 2), "M_RobotDark", sides=10, rot=(0, math.pi / 2, 0))
    for side, y in (("Front", -(depth / 2 + 0.06)), ("Back", depth / 2 + 0.06)):
        cube(a.part(f"StatusLight_{side}"), (0.5, 0.02, 0.08), (0, y, height + box_h * 0.6), "M_GlowRed")
    center = (0.0, 0.0, height / 2)
    panel = a.part("Panel", pivot=center)
    mat = p.material(["M_Metal", "M_Wall", "M_Platform"])
    if style == "roller":
        n = max(6, int(height / 0.14))
        sh = height / n
        for i in range(n):
            cube(panel, (width + 0.1, 0.06, sh * 0.92), (0, 0, sh * (i + 0.5)), mat, bevel=0.012)
        cube(panel, (width + 0.1, 0.1, 0.08), (0, 0, 0.04), "M_RobotDark")  # bottom bar
        if rng.random() < 0.5:
            stripes(panel, width * 0.9, (0, -0.04, 0.3), count=int(width * 2), width=0.02, height=0.25)
    else:
        for i in range(max(4, int(width / 0.18))):  # vertical bars + crossings
            x = -width / 2 + 0.05 + i * (width - 0.1) / (max(4, int(width / 0.18)) - 1)
            cube(panel, (0.03, 0.03, height - 0.05), (x, 0, height / 2), "M_Metal")
        for z in [0.1 + k * (height - 0.2) / 4 for k in range(5)]:
            cube(panel, (width + 0.1, 0.05, 0.05), (0, 0, z), "M_RobotDark")
    a.behaviour("Door", {"panels": ["Panel"], "statusLights": ["StatusLight_Front", "StatusLight_Back"],
                         "upperFrame": ["Frame_Top"], "colliders": ["Frame_Left", "Frame_Right", "Frame_Top"]},
                {"openOffset": [0.0, round(height + 0.05, 4), 0.0], "speed": p.option("speed")},
                note="'open' = the curtain slides up into the wall above (like Door_Blast); hide it there")


# --------------------------------------------------------------------------
# crawl / ventilation shaft
# --------------------------------------------------------------------------

SHAFT_OPEN = {  # open sides of a piece: -X, +X, -Y (front), +Y (back)
    "straight": ("-x", "+x"),
    "corner": ("-x", "-y"),
    "tee": ("-x", "+x", "-y"),
    "cross": ("-x", "+x", "-y", "+y"),
    "end": ("-x",),
}


@model("vent_shaft", "VentShaft", "environment", "Crawlable vent shaft piece: straight, corner, tee, cross or end "
       "(walkable inside), optional grille (Grille)", params=[
           Param("kind", "choice", "Stück", choices=tuple(SHAFT_OPEN)),
           Param("inner", "float", "Innenmaß (m)", lo=0.6, hi=2.0, size=True),
           Param("length", "choice", "Länge gerade (m)", choices=(1.0, 2.0)),
           Param("glow", "bool", "Glow-Streifen innen"),
           Param("grille", "bool", "Gitter vor der Öffnung -X"),
       ])
def vent_shaft(rng, a):
    p = a.p
    kind = p.choice("kind", ["straight", "straight", "corner", "tee", "end", "cross"])
    inner = p.float("inner", 0.9, 1.2)
    t = 0.08
    outer = inner + 2 * t
    lx = p.choice("length", [1.0, 2.0]) if kind == "straight" else outer
    ly = outer
    opened = SHAFT_OPEN[kind]
    mat = p.material(["M_Metal", "M_Wall", "M_RobotDark"])
    m = a.part("Shaft")
    a.meta.update({"kind": kind, "inner_m": round(inner, 3), "length_m": round(lx, 3)})
    cube(m, (lx, ly, t), (0, 0, t / 2), mat)                       # floor
    cube(m, (lx, ly, t), (0, 0, outer - t / 2), mat)               # roof
    for side in ("-x", "+x", "-y", "+y"):
        sx = -1 if side[0] == "-" else 1
        along_x = side[1] == "y"
        if side in opened:  # rib frame around the opening
            for zz, hh in ((t / 2, t), (outer - t / 2, t)):
                size = (lx, 0.08, hh + 0.04) if along_x else (0.08, ly, hh + 0.04)
                pos = (0, sx * (ly / 2 - 0.04), zz) if along_x else (sx * (lx / 2 - 0.04), 0, zz)
                cube(m, size, pos, "M_RobotDark")
            for s2 in (-1, 1):
                pos = (s2 * (lx / 2 - t / 2), sx * (ly / 2 - 0.04), outer / 2) if along_x else \
                    (sx * (lx / 2 - 0.04), s2 * (ly / 2 - t / 2), outer / 2)
                cube(m, (t + 0.04, 0.08, outer) if along_x else (0.08, t + 0.04, outer), pos, "M_RobotDark")
        else:
            size = (lx, t, outer) if along_x else (t, ly, outer)
            pos = (0, sx * (ly / 2 - t / 2), outer / 2) if along_x else (sx * (lx / 2 - t / 2), 0, outer / 2)
            cube(m, size, pos, mat)
            span = lx if along_x else ly
            for k in range(max(1, int(span / 0.5)) + 1):  # outside stiffener ribs
                f = -span / 2 + 0.06 + k * (span - 0.12) / max(1, int(span / 0.5))
                rpos = (f, sx * (ly / 2 + 0.015), outer / 2) if along_x else (sx * (lx / 2 + 0.015), f, outer / 2)
                cube(m, (0.04, 0.03, outer - 0.04) if along_x else (0.03, 0.04, outer - 0.04), rpos, "M_RobotDark")
    for k in range(max(1, int(lx / 0.5))):  # floor plates inside (grip)
        cube(m, (0.04, inner * 0.8, 0.012), (-lx / 2 + (k + 0.5) * lx / max(1, int(lx / 0.5)), 0, t + 0.006),
             "M_RobotDark")
    if p.bool("glow", 0.5):
        cube(a.part("Glow"), (lx * 0.85 if kind == "straight" else inner * 0.5, 0.04, 0.02), (0, 0, outer - t - 0.01),
             p.glow())
    if p.bool("grille", 0.35, enabled="-x" in opened):  # kick-out grille in front of the -X opening
        center = (-lx / 2 - 0.03, 0.0, outer / 2)
        g = a.part("Grille", pivot=center)
        cube(g, (0.04, inner + 0.06, 0.05), (center[0], 0, outer / 2 + inner / 2), "M_RobotDark")
        cube(g, (0.04, inner + 0.06, 0.05), (center[0], 0, outer / 2 - inner / 2), "M_RobotDark")
        for k in range(7):
            cube(g, (0.03, inner, 0.035), (center[0], 0, outer / 2 - inner * 0.42 + k * inner * 0.14), "M_Metal",
                 rot=(deg(30), 0, 0))
        a.meta["grille"] = True


# --------------------------------------------------------------------------
# floor grate with a pit
# --------------------------------------------------------------------------

@model("floor_grate", "FloorGrate", "environment", "Floor grate (top at z = 0) over a pit with pipes, cables and "
       "lights; the grate (Panel) lifts out", pivot="top", params=[
           Param("size", "choice", "Größe (m)", choices=(1.0, 2.0)),
           Param("depth", "float", "Schachttiefe (m)", lo=0.2, hi=1.5),
           Param("content", "choice", "Inhalt", choices=("pipes", "cables", "both")),
           Param("lights", "bool", "Lichter im Schacht"),
       ])
def floor_grate(rng, a):
    p = a.p
    size = p.choice("size", [1.0, 1.0, 2.0])
    depth = p.float("depth", 0.4, 0.8)
    content = p.choice("content", ["pipes", "cables", "both"])
    body = a.part("Body")
    rim = 0.06
    inner = size - 2 * rim
    a.meta.update({"size_m": size, "content": content})
    for k in range(4):
        ang = math.pi / 2 * k
        dx, dy = round(math.cos(ang)), round(math.sin(ang))
        cube(body, (rim, size, 0.1) if dx else (size, rim, 0.1), (dx * (size - rim) / 2, dy * (size - rim) / 2, -0.05),
             "M_RobotDark")
        cube(body, (0.04, inner, depth) if dx else (inner, 0.04, depth),
             (dx * (inner / 2 - 0.02), dy * (inner / 2 - 0.02), -0.1 - depth / 2), "M_Ground")
    cube(body, (inner, inner, 0.04), (0, 0, -0.12 - depth), "M_RobotDark")
    zb = -0.1 - depth
    if content in ("pipes", "both"):
        for i in range(rng.randint(1, 3 if size > 1 else 2)):
            r = rng.uniform(0.05, min(0.12, depth * 0.3))
            y = -inner / 2 + 0.15 + i * (inner - 0.3) / 2
            cyl(body, r, inner, (0, y, zb + r + 0.02), rng.choice(["M_Metal", "M_HazardOrange", "M_Wall"]),
                rot=ALONG_X)
    if content in ("cables", "both"):
        for i in range(rng.randint(3, 6)):
            cyl(body, 0.02, inner, (0, inner * 0.3 + rng.uniform(-0.08, 0.08), zb + 0.03 + i * 0.025),
                rng.choice(["M_RobotDark", "M_HazardOrange", "M_Warning"]), sides=6, rot=ALONG_X)
    if p.bool("lights", 0.6):
        glow = p.glow()
        for x in (-inner / 3, inner / 3):
            cube(a.part("Lights"), (0.12, 0.02, 0.04), (x, -inner / 2 + 0.04, zb + depth * 0.5), glow)
    center = (0.0, 0.0, -0.02)
    grate = a.part("Panel", pivot=center)
    for s in (-1, 1):
        cube(grate, (inner - 0.01, 0.04, 0.04), (0, s * (inner / 2 - 0.02), -0.02), "M_Metal")
    n = int(inner / 0.08)
    for i in range(n):
        cube(grate, (0.025, inner - 0.08, 0.035), (-inner / 2 + 0.04 + i * (inner - 0.08) / (n - 1), 0, -0.02),
             "M_Metal")


# --------------------------------------------------------------------------
# bulkhead
# --------------------------------------------------------------------------

@model("bulkhead", "Bulkhead", "environment", "Corridor bulkhead frame (passage along Y): posts, beam, chamfered "
       "or ring corners, glow edge, pipes", params=[
           Param("style", "choice", "Form", choices=("frame", "chamfer", "ring")),
           Param("width", "float", "Durchgang Breite (m)", lo=1.2, hi=6.0, size=True),
           Param("height", "float", "Durchgang Höhe (m)", lo=2.0, hi=4.5, size=True),
           Param("pipes", "bool", "Rohre durch die Ecken"),
           Param("stripes", "bool", "Warnstreifen"),
       ])
def bulkhead(rng, a):
    p = a.p
    style = p.choice("style", ["frame", "chamfer", "chamfer", "ring"])
    w = p.float("width", 2.0, 3.6)
    h = p.float("height", 2.6, 3.2)
    post, depth = rng.uniform(0.3, 0.5), rng.uniform(0.4, 0.8)
    mat = p.material(["M_Wall", "M_Metal", "M_RobotDark"])
    body = a.part("Body")
    glow = p.glow()
    a.meta.update({"style": style, "opening_m": [round(w, 3), round(h, 3)]})
    for sx in (-1, 1):
        cube(body, (post, depth, h + post), (sx * (w + post) / 2, 0, (h + post) / 2), mat, bevel=0.03)
        cube(body, (post + 0.06, depth + 0.06, 0.25), (sx * (w + post) / 2, 0, 0.125), "M_RobotDark", bevel=0.01)
    cube(body, (w + 2 * post, depth, post), (0, 0, h + post / 2), mat, bevel=0.03)
    c = min(w, h) * rng.uniform(0.18, 0.28)
    if style in ("chamfer", "ring"):  # diagonal braces in the upper corners
        for sx in (-1, 1):
            cube(body, (c * 1.414 + 0.1, depth * 0.9, post * 0.7), (sx * (w / 2 - c / 2 + 0.03), 0, h - c / 2 + 0.03),
                 "M_RobotDark", bevel=0.02, rot=(0, sx * deg(45), 0))
    if style == "ring":  # sill and lower braces: an octagonal passage
        cube(body, (w, depth, 0.12), (0, 0, 0.06), "M_RobotDark")
        for sx in (-1, 1):
            cube(body, (c * 1.0 + 0.1, depth * 0.9, post * 0.6), (sx * (w / 2 - c * 0.35), 0, c * 0.35 + 0.05),
                 "M_RobotDark", bevel=0.02, rot=(0, -sx * deg(45), 0))
    lights = a.part("Glow")
    for y in (-depth / 2 - 0.01, depth / 2 + 0.01):
        cube(lights, (w * 0.6 if style != "frame" else w, 0.02, 0.05), (0, y, h + post * 0.3), glow)
        for sx in (-1, 1):
            cube(lights, (0.05, 0.02, h * 0.6), (sx * (w / 2 + post * 0.3), y, h * 0.45), glow)
    if p.bool("pipes", 0.4):
        for sx in (-1, 1):
            r = rng.uniform(0.06, 0.1)
            cyl(body, r, depth + 1.0, (sx * (w / 2 - r - 0.05), 0, h - r - 0.05), "M_Metal", rot=ALONG_Y)
            for y in (-depth / 2 - 0.05, depth / 2 + 0.05):
                cyl(body, r * 1.3, 0.06, (sx * (w / 2 - r - 0.05), y, h - r - 0.05), "M_RobotDark", rot=ALONG_Y)
    if p.bool("stripes", 0.35, warning=True):
        for sx in (-1, 1):
            for y in (-depth / 2 - 0.006, depth / 2 + 0.006):
                for k in range(4):
                    cube(body, (post * 0.9, 0.012, 0.1), (sx * (w + post) / 2, y, 0.4 + k * 0.25), "M_Warning",
                         rot=(0, deg(30) * sx, 0))


# --------------------------------------------------------------------------
# wall cladding
# --------------------------------------------------------------------------

@model("wall_panel", "WallPanel", "environment", "Wall cladding in front of a wall (back at y = +0.1): consoles, "
       "pipes, cabinets or glow panels, 2 or 4 m", pivot="wall", params=[
           Param("length", "choice", "Länge (m)", choices=(2.0, 4.0)),
           Param("style", "choice", "Art", choices=("consoles", "pipes", "cabinets", "panels")),
           Param("stripes", "bool", "Warnstreifen unten"),
       ])
def wall_panel(rng, a):
    p = a.p
    length = p.choice("length", [2.0, 2.0, 4.0])
    style = p.choice("style", ["consoles", "pipes", "cabinets", "panels"])
    z0, z1 = 0.3, 2.75
    hh = z1 - z0
    body = a.part("Body")
    glow = p.glow()
    plate = p.styled("M_Wall", ["M_Wall", "M_Metal", "M_RobotDark"])
    cube(body, (length, 0.06, hh), (0, 0.07, z0 + hh / 2), plate, bevel=0.015)
    a.meta.update({"length_m": length, "style": style})
    modules = int(length)
    mw = length / modules
    if style == "consoles":
        screen = a.part("Screen")
        for i in range(modules):
            x = -length / 2 + mw * (i + 0.5)
            cube(body, (mw * 0.85, 0.16, 0.9), (x, -0.04, 1.35), "M_RobotDark", bevel=0.02)
            cube(screen, (mw * 0.6, 0.02, 0.35), (x, -0.13, 1.5), glow)
            for r in range(2):
                for c in range(4):
                    cube(a.part("Lights"), (0.06, 0.02, 0.04), (x - mw * 0.3 + c * mw * 0.2, -0.13, 1.08 + r * 0.08),
                         rng.choice(["M_GlowCyan", "M_GlowOrange", "M_GlowRed", "M_Platform"]))
            cyl(body, 0.08, 0.05, (x + mw * 0.25, 0.01, 2.2), "M_Metal", sides=10, rot=ALONG_Y)  # gauge
            cube(body, (0.02, 0.02, 0.07), (x + mw * 0.25, -0.025, 2.22), "M_HazardOrange", rot=(0, deg(30), 0))
    elif style == "pipes":
        n = rng.randint(2, 4)
        for i in range(n):
            x = -length / 2 + 0.25 + i * (length - 0.5) / max(1, n - 1)
            r = rng.uniform(0.04, 0.09)
            cyl(body, r, hh, (x, -0.02, z0 + hh / 2), rng.choice(["M_Metal", "M_HazardOrange", "M_Wall"]))
            for z in (z0 + 0.3, z1 - 0.3):
                cube(body, (r * 2.6, 0.08, 0.05), (x, 0.0, z), "M_RobotDark")
        hz = rng.uniform(0.9, 2.2)
        cyl(body, 0.06, length, (0, -0.12, hz), "M_Metal", rot=ALONG_X)
        cube(a.part("Lights"), (length * 0.6, 0.02, 0.03), (0, 0.03, z1 - 0.1), glow)
    elif style == "cabinets":
        for i in range(modules * 2):
            x = -length / 2 + mw / 2 * (i + 0.5)
            cube(body, (mw / 2 - 0.04, 0.2, 1.7), (x, -0.06, z0 + 0.85),
                 p.material(["M_Wall", "M_Metal", "M_RobotDark"]), bevel=0.02)
            cube(body, (0.03, 0.04, 0.2), (x + mw / 4 - 0.08, -0.17, z0 + 0.95), "M_Metal")
            for k in range(3):
                cube(body, (mw / 2 - 0.2, 0.02, 0.025), (x, -0.165, z0 + 1.45 + k * 0.05), "M_RobotDark")
        cube(a.part("Lights"), (length * 0.9, 0.02, 0.04), (0, -0.17, z0 + 1.76), glow)
    else:  # raised panels with glow seams and rivets
        lights = a.part("Lights")
        for i in range(modules):
            x = -length / 2 + mw * (i + 0.5)
            for zc, ph in ((z0 + 0.7, 1.0), (z0 + 1.85, 0.9)):
                cube(body, (mw - 0.12, 0.05, ph), (x, 0.02, zc), "M_RobotDark" if plate != "M_RobotDark" else "M_Metal",
                     bevel=0.02)
                for sx in (-1, 1):
                    for sz in (-1, 1):
                        cyl(body, 0.015, 0.02, (x + sx * (mw / 2 - 0.12), -0.01, zc + sz * (ph / 2 - 0.06)), "M_Metal",
                            sides=6, rot=ALONG_Y)
            cube(lights, (0.03, 0.02, hh * 0.85), (x + mw / 2 - 0.03, 0.03, z0 + hh / 2), glow)
    if p.bool("stripes", 0.3, warning=True):
        stripes(body, length * 0.9, (0, 0.03, z0 + 0.06), count=int(length * 3), width=0.02, height=0.1)
