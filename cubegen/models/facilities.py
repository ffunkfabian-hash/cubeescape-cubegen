"""Station facilities: lab devices, galley / mess, washroom and the floor plan board.

Mostly static decoration (Art/Models/Library/Props); the centrifuge's rotor and
the floor plan's "you are here" light use the game's ``Rotator`` / ``SignalLight``.
"""

from __future__ import annotations

import math

from ..params import Param
from .common import ALONG_X, ALONG_Y, cube, cyl, deg, strut
from .lettering import add_text, check_text, text_width
from .registry import model

LIQUIDS = ("M_Liquid", "M_GlowOrange", "M_Warning", "M_GlowRed", "M_HazardOrange")


# --------------------------------------------------------------------------
# lab devices
# --------------------------------------------------------------------------

@model("lab_device", "LabDevice", "props", "Lab equipment for a table top (pivot on the table): microscope, test "
       "tube rack with coloured liquids or a centrifuge with a turning rotor (Rotor)", params=[
           Param("kind", "choice", "Gerät", choices=("microscope", "tube_rack", "centrifuge")),
           Param("size", "float", "Größe (m)", lo=0.2, hi=0.8, size=True),
           Param("speed", "float", "Rotor-Tempo (°/s, Zentrifuge)", lo=0, hi=3000, unity=True, default=720),
       ])
def lab_device(rng, a):
    p = a.p
    kind = p.choice("kind", ["microscope", "tube_rack", "centrifuge"])
    s = p.float("size", 0.3, 0.5)
    body = a.part("Body")
    shell = p.material(["M_RobotBody", "M_Platform", "M_Wall"])
    a.meta["kind"] = kind
    if kind == "microscope":
        cube(body, (s * 0.6, s * 0.7, s * 0.08), (0, 0, s * 0.04), shell, bevel=0.01)
        cube(body, (s * 0.12, s * 0.12, s * 0.7), (0, s * 0.25, s * 0.43), shell, bevel=0.01)  # arm
        cube(body, (s * 0.4, s * 0.35, s * 0.04), (0, -s * 0.05, s * 0.3), "M_RobotDark")  # stage
        head = (0.0, -s * 0.02, s * 0.72)
        cube(body, (s * 0.2, s * 0.4, s * 0.16), (0, s * 0.1, head[2]), shell, bevel=0.01)
        for k in range(3):  # objective turret
            ang = deg(-60 + 60 * k)
            cyl(body, s * 0.03, s * 0.12, (math.sin(ang) * s * 0.06, -s * 0.06, s * 0.56), "M_Metal", sides=6)
        cyl(body, s * 0.025, s * 0.04, (0, -s * 0.06, s * 0.48), "M_Glass", sides=6)
        for x in (-1, 1):  # eyepieces, tilted towards the viewer
            strut(body, (x * s * 0.04, s * 0.15, s * 0.78), (x * s * 0.05, s * 0.3, s * 0.92), s * 0.025, "M_RobotDark",
                  sides=6)
        cyl(body, s * 0.05, s * 0.03, (s * 0.33, s * 0.05, s * 0.3), "M_RobotDark", sides=8, rot=ALONG_X)  # focus
        cube(a.part("Lights"), (s * 0.1, s * 0.1, s * 0.01), (0, -s * 0.05, s * 0.085), "M_GlowCyan")
    elif kind == "tube_rack":
        n = rng.randint(4, 8)
        rows = 2 if n > 5 else 1
        per = math.ceil(n / rows)
        w = per * s * 0.16 + s * 0.1
        d = rows * s * 0.18 + s * 0.06
        cube(body, (w, d, s * 0.05), (0, 0, s * 0.025), shell)
        cube(body, (w, d, s * 0.03), (0, 0, s * 0.3), shell)
        for x in (-1, 1):
            cube(body, (s * 0.04, d, s * 0.3), (x * (w / 2 - s * 0.02), 0, s * 0.15), shell)
        liquids = a.part("Liquids")
        for k in range(n):
            col, row = k % per, k // per
            x = -w / 2 + s * 0.1 + col * s * 0.16
            y = (row - (rows - 1) / 2) * s * 0.18
            th = s * rng.uniform(0.4, 0.55)
            cyl(body, s * 0.04, th, (x, y, s * 0.05 + th / 2 + 0.002), "M_Glass", sides=6)
            fill = th * rng.uniform(0.3, 0.8)
            cyl(liquids, s * 0.032, fill, (x, y, s * 0.05 + fill / 2 + 0.004), rng.choice(LIQUIDS), sides=6)
            if rng.random() < 0.5:
                cyl(body, s * 0.045, s * 0.03, (x, y, s * 0.05 + th + 0.017), rng.choice(["M_GlowRed", "M_Wall",
                                                                                          "M_RobotDark"]), sides=6)
        a.meta["tubes"] = n
    else:
        r = s * 0.5
        cyl(body, r, s * 0.4, (0, 0, s * 0.2), shell, sides=12, bevel=0.01)
        cyl(body, r * 0.9, s * 0.02, (0, 0, s * 0.41), "M_RobotDark", sides=12)
        center = (0.0, 0.0, s * 0.44)
        rotor = a.part("Rotor", pivot=center)
        cyl(rotor, r * 0.15, s * 0.05, center, "M_Metal", sides=8)
        for k in range(6):
            ang = 2 * math.pi * k / 6
            cube(rotor, (r * 0.6, s * 0.06, s * 0.03), (math.cos(ang) * r * 0.35, math.sin(ang) * r * 0.35, s * 0.44),
                 "M_Metal", rot=(0, 0, ang))
        hinge = (0.0, r * 0.9, s * 0.55)
        cyl(body, r * 0.95, s * 0.04, (0, r * 0.95 * 0.0 + r * 0.55, s * 0.62), "M_Glass", sides=12,
            rot=(deg(-60), 0, 0))  # open glass lid
        cube(body, (s * 0.3, s * 0.06, s * 0.12), (0, -r * 0.95, s * 0.25), "M_RobotDark")
        cube(a.part("Screen"), (s * 0.22, s * 0.01, s * 0.07), (0, -r * 0.98 - 0.006, s * 0.26), "M_GlowCyan")
        a.behaviour("Rotator", {"target": "Rotor"}, {"axis": "up", "speed": p.option("speed")})
        a.meta["hinge"] = [round(c, 3) for c in hinge]


# --------------------------------------------------------------------------
# galley / mess
# --------------------------------------------------------------------------

@model("galley", "Galley", "props", "Galley and mess: kitchen counter (stove, sink, cabinets, hood), mess table with "
       "benches and trays, or a fridge / food dispenser", params=[
           Param("style", "choice", "Art", choices=("counter", "mess_table", "fridge")),
           Param("length", "float", "Länge (m)", lo=1.0, hi=4.0, size=True),
       ])
def galley(rng, a):
    p = a.p
    style = p.choice("style", ["counter", "mess_table", "fridge"])
    ln = p.float("length", 1.6, 3.0)
    body = a.part("Body")
    mat = p.material(["M_Platform", "M_Wall", "M_Metal", "M_RobotBody"])
    a.meta["style"] = style
    if style == "counter":
        d, h = 0.65, 0.9
        cube(body, (ln, d, h - 0.05), (0, 0, (h - 0.05) / 2), mat)
        cube(body, (ln + 0.04, d + 0.04, 0.05), (0, 0, h - 0.025), "M_Metal")
        doors = max(2, int(ln / 0.6))
        for i in range(doors):  # cabinet doors with handles
            x = -ln / 2 + ln * (i + 0.5) / doors
            cube(body, (ln / doors - 0.04, 0.02, h - 0.2), (x, -d / 2 - 0.01, (h - 0.05) / 2 + 0.03), "M_RobotDark"
                 if i % 2 else mat)
            cube(body, (0.12, 0.03, 0.02), (x, -d / 2 - 0.03, h - 0.18), "M_Metal")
        stove = -ln / 2 + 0.4
        for dx in (-0.12, 0.12):
            for dy in (-0.12, 0.12):
                cyl(body, 0.08, 0.012, (stove + dx, dy, h + 0.006), "M_RobotDark", sides=8)
        lights = a.part("Lights")
        cyl(lights, 0.06, 0.006, (stove - 0.12, -0.12, h + 0.015), "M_GlowOrange", sides=8)
        sink = ln / 2 - 0.45
        cube(body, (0.5, 0.4, 0.02), (sink, 0, h + 0.01), "M_Metal")
        cube(body, (0.42, 0.32, 0.01), (sink, 0, h + 0.025), "M_Ground")
        strut(body, (sink, d / 2 - 0.08, h), (sink, d / 2 - 0.08, h + 0.3), 0.015, "M_Metal")
        strut(body, (sink, d / 2 - 0.08, h + 0.3), (sink, d / 2 - 0.25, h + 0.3), 0.012, "M_Metal")
        if rng.random() < 0.6:  # extractor hood
            cube(body, (0.7, 0.5, 0.1), (stove, 0.05, h + 1.0), "M_Metal", bevel=0.01)
            cube(body, (0.25, 0.25, 0.6), (stove, 0.1, h + 1.35), "M_Metal")
        for _ in range(rng.randint(1, 3)):  # pots and cans
            x = rng.uniform(-ln / 2 + 0.2, ln / 2 - 0.9)
            r = rng.uniform(0.06, 0.12)
            cyl(body, r, r * 1.2, (x, rng.uniform(-0.15, 0.15), h + r * 0.6), rng.choice(["M_Metal", "M_HazardOrange",
                                                                                          "M_Wall"]), sides=8)
    elif style == "mess_table":
        w, h = 0.8, 0.75
        cube(body, (ln, w, 0.05), (0, 0, h - 0.025), mat, bevel=0.01)
        for x in (-1, 1):
            cube(body, (0.08, w * 0.7, h - 0.05), (x * (ln / 2 - 0.25), 0, (h - 0.05) / 2), "M_RobotDark")
            cube(body, (0.1, w * 0.9, 0.05), (x * (ln / 2 - 0.25), 0, 0.025), "M_RobotDark")
        for s in (-1, 1):  # benches
            cube(body, (ln, 0.32, 0.05), (0, s * (w / 2 + 0.3), 0.45), mat)
            for x in (-1, 1):
                cube(body, (0.06, 0.2, 0.42), (x * (ln / 2 - 0.25), s * (w / 2 + 0.3), 0.21), "M_RobotDark")
        trays = rng.randint(1, max(1, int(ln / 0.6)))
        for i in range(trays):
            x = -ln / 2 + ln * (i + 0.5) / trays
            y = rng.choice([-1, 1]) * w * 0.25
            cube(body, (0.35, 0.25, 0.02), (x, y, h + 0.01), "M_Wall")
            cyl(body, 0.06, 0.03, (x - 0.08, y, h + 0.035), rng.choice(["M_HazardOrange", "M_Warning", "M_Liquid"]),
                sides=8)
            cyl(body, 0.035, 0.1, (x + 0.1, y + 0.05, h + 0.07), "M_Metal", sides=6)
        a.meta["trays"] = trays
    else:
        w, d, h = min(ln, 1.4), 0.7, rng.uniform(1.8, 2.1)
        cube(body, (w, d, h), (0, 0, h / 2), mat, bevel=0.02)
        split = h * rng.uniform(0.3, 0.4)
        cube(body, (w - 0.04, 0.02, 0.02), (0, -d / 2 - 0.005, split), "M_RobotDark")
        for zz in (split / 2, split + (h - split) / 2):
            cube(body, (0.04, 0.05, 0.4), (w / 2 - 0.1, -d / 2 - 0.03, zz), "M_Metal")
        if rng.random() < 0.6:  # food dispenser: screen and a hatch
            cube(a.part("Screen"), (w * 0.35, 0.01, 0.22), (-w * 0.2, -d / 2 - 0.006, h * 0.72), "M_GlowCyan")
            cube(body, (w * 0.4, 0.04, 0.25), (-w * 0.2, -d / 2 - 0.01, split + 0.3), "M_RobotDark")
            a.meta["dispenser"] = True


# --------------------------------------------------------------------------
# washroom
# --------------------------------------------------------------------------

@model("washroom", "Washroom", "props", "Washroom fixtures (back against the wall at +Y): wash basin with mirror, "
       "toilet or shower cabin with glass door", params=[
           Param("style", "choice", "Art", choices=("sink", "toilet", "shower")),
           Param("mirror", "bool", "Spiegel / Ablage"),
       ])
def washroom(rng, a):
    p = a.p
    style = p.choice("style", ["sink", "toilet", "shower"])
    body = a.part("Body")
    ceramic = p.material(["M_Platform", "M_RobotBody"])
    a.meta["style"] = style
    if style == "sink":
        w = rng.uniform(0.5, 0.9)
        if p.style.generation < 3:
            cube(body, (w, 0.45, 0.15), (0, 0, 0.8), ceramic, bevel=0.02)
            cube(body, (w * 0.7, 0.3, 0.02), (0, -0.03, 0.885), "M_Ground")
        else:
            # A real recess: ceramic floor and four rim walls, no plate closing the basin.
            cube(body, (w, 0.45, 0.03), (0, 0, 0.74), ceramic)
            for x in (-1, 1):
                cube(body, (0.055, 0.45, 0.14), (x * (w / 2 - 0.0275), 0, 0.815), ceramic)
            for y in (-1, 1):
                cube(body, (w - 0.11, 0.055, 0.14), (0, y * (0.225 - 0.0275), 0.815), ceramic)
            cyl(body, 0.025, 0.003, (0, -0.03, 0.757), "M_Metal", sides=8)
        cube(body, (0.16, 0.2, 0.65), (0, 0.1, 0.4), ceramic)  # pedestal
        strut(body, (0, 0.18, 0.875), (0, 0.18, 1.0), 0.015, "M_Metal")
        strut(body, (0, 0.18, 1.0), (0, 0.06, 1.0), 0.012, "M_Metal")
        if p.bool("mirror", 0.7):
            mh = rng.uniform(0.5, 0.8)
            cube(body, (w, 0.03, mh), (0, 0.215, 1.15 + mh / 2), "M_RobotDark")
            cube(a.part("Glass"), (w - 0.06, 0.01, mh - 0.06), (0, 0.195, 1.15 + mh / 2), "M_Glass")
    elif style == "toilet":
        cube(body, (0.38, 0.18, 0.4), (0, 0.13, 0.62), ceramic, bevel=0.02)  # cistern
        cyl(body, 0.18, 0.4, (0, -0.1, 0.2), ceramic, sides=10, radius_top=0.2)
        cyl(body, 0.2, 0.03, (0, -0.1, 0.415), "M_Wall", sides=10)  # seat
        cube(body, (0.08, 0.03, 0.02), (0, 0.04, 0.83), "M_Metal")  # flush button
        if p.bool("mirror", 0.4):  # paper holder instead
            cyl(body, 0.06, 0.1, (0.3, 0.15, 0.7), "M_Platform", sides=8, rot=ALONG_X)
    else:
        w = rng.uniform(0.85, 1.1)
        h = 2.1
        cube(body, (w, w, 0.12), (0, 0, 0.06), ceramic)
        cube(body, (w * 0.8, w * 0.8, 0.01), (0, 0, 0.125), "M_Ground")
        for x in (-1, 1):
            cube(body, (0.04, w, h), (x * (w / 2 - 0.02), 0, 0.12 + h / 2), "M_Wall")
        cube(body, (w, 0.04, h), (0, w / 2 - 0.02, 0.12 + h / 2), "M_Wall")
        cube(body, (w, w, 0.04), (0, 0, 0.12 + h), "M_RobotDark")
        glass = a.part("Glass")
        cube(glass, (w * 0.6, 0.02, h * 0.9), (w * 0.18, -w / 2 + 0.03, 0.12 + h * 0.47), "M_Glass")
        cube(body, (0.03, 0.04, h), (-w * 0.12, -w / 2 + 0.03, 0.12 + h / 2), "M_Metal")
        cyl(body, 0.08, 0.02, (0, w * 0.25, 0.12 + h - 0.25), "M_Metal", sides=8)  # shower head
        strut(body, (0, w / 2 - 0.04, 0.12 + h - 0.15), (0, w * 0.25, 0.12 + h - 0.24), 0.012, "M_Metal")
        cube(a.part("Lights"), (0.05, 0.02, 0.05), (-w / 2 + 0.1, w / 2 - 0.05, 1.3), "M_GlowCyan")


# --------------------------------------------------------------------------
# floor plan board
# --------------------------------------------------------------------------

@model("floor_plan", "FloorPlan", "props", "Floor plan board on the wall (Lageplan): rooms and corridors in relief, "
       "blinking 'you are here' light (Glow, SignalLight), optional title", pivot="wall", params=[
           Param("width", "float", "Breite (m)", lo=0.5, hi=2.5, size=True),
           Param("rooms", "int", "Räume", lo=3, hi=12),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=1.0, hi=2.5),
           Param("title", "text", "Titel", quiet=True,
                 description="Zeile über dem Plan, z. B. DECK 3 (bis 16 Zeichen)"),
       ])
def floor_plan(rng, a):
    p = a.p
    w = p.float("width", 0.8, 1.6)
    n = p.int("rooms", 4, 8)
    z = p.value("mount_height", rng.uniform(1.4, 1.7))
    h = w * rng.uniform(0.55, 0.75)
    title = p.option("title")
    th = h * 0.1
    if title:
        title = check_text(title, max_len=16)
        w = max(w, text_width(title, th) + 0.2)
    total = h + (th * 2 if title else 0.0)
    z = max(z, total / 2 + 0.1)
    body = a.part("Body")
    board = p.material(["M_RobotDark", "M_Wall"])
    cube(body, (w + 0.08, 0.06, total + 0.08), (0, 0.07, z), "M_Metal", bevel=0.01)
    cube(body, (w, 0.02, total), (0, 0.035, z), board)
    zp = z - (th if title else 0.0)  # plan centre
    if title:
        add_text(body, title, (0, 0.025, z + total / 2 - th), th, 0.01, "M_Platform")
    # rooms: split the plan area recursively (seeded floor plan)
    areas = [(-w / 2 + 0.05, zp - h / 2 + 0.05, w / 2 - 0.05, zp + h / 2 - 0.05)]
    while len(areas) < n:
        areas.sort(key=lambda r: -(r[2] - r[0]) * (r[3] - r[1]))
        x0, z0, x1, z1 = areas.pop(0)
        if (x1 - x0) >= (z1 - z0):
            c = rng.uniform(x0 + (x1 - x0) * 0.35, x1 - (x1 - x0) * 0.35)
            areas += [(x0, z0, c, z1), (c, z0, x1, z1)]
        else:
            c = rng.uniform(z0 + (z1 - z0) * 0.35, z1 - (z1 - z0) * 0.35)
            areas += [(x0, z0, x1, c), (x0, c, x1, z1)]
    colours = ["M_Platform", "M_Wall", "M_Warning", "M_HazardOrange", "M_Metal", "M_RobotBody"]
    rooms = []
    for k, (x0, z0, x1, z1) in enumerate(sorted(areas)):
        gap = 0.012
        cube(body, (x1 - x0 - gap * 2, 0.012, z1 - z0 - gap * 2), ((x0 + x1) / 2, 0.019, (z0 + z1) / 2),
             colours[k % len(colours)] if rng.random() < 0.7 else "M_Ground")
        rooms.append([round((x0 + x1) / 2, 3), round((z0 + z1) / 2 - zp, 3)])
    here = rng.choice(rooms)
    cyl(a.part("Glow"), min(w, h) * 0.035, 0.012, (here[0], 0.005, zp + here[1]), "M_GlowRed", sides=8, rot=ALONG_Y)
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": "Blink"}, note="'you are here' marker")
    a.meta.update({"rooms": len(rooms), "here": here, **({"title": title} if title else {})})
