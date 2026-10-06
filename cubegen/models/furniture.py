"""Station furniture and small props: lockers, shelves, workbenches, tool carts, cryo pods, chairs,
gas bottle racks, fire extinguishers, first aid kits, barriers, pallets, signs, beds, tables, bins and toolboxes.

Static decoration (no game scripts) - goes into Art/Models/Library/Props.
"""

from __future__ import annotations

import math

from ..geometry import prism
from ..params import Param
from .common import ALONG_X, ALONG_Y, cube, cyl, deg, stripes
from .registry import model

BOX_MATS = ["M_RobotDark", "M_Wall", "M_Metal", "M_HazardOrange", "M_Platform"]


def _small_box(rng, mesh, x, y, z, max_w, max_d, max_h):
    """A small crate or canister standing at (x, y, z); returns its height."""
    if rng.random() < 0.6:
        w, d, h = max_w * rng.uniform(0.5, 0.9), max_d * rng.uniform(0.5, 0.9), max_h * rng.uniform(0.4, 0.9)
        cube(mesh, (w, d, h), (x, y, z + h / 2), rng.choice(BOX_MATS), bevel=0.01, rot=(0, 0, deg(rng.uniform(-8, 8))))
    else:
        r, h = min(max_w, max_d) * rng.uniform(0.2, 0.4), max_h * rng.uniform(0.5, 0.9)
        cyl(mesh, r, h, (x, y, z + h / 2), rng.choice(["M_Wall", "M_Metal", "M_HazardOrange", "M_RobotBody"]), sides=8)
        cyl(mesh, r * 1.05, 0.03, (x, y, z + h * 0.8), "M_RobotDark", sides=8)
    return h


@model("locker", "Locker", "props", "Row of 1-4 lockers: vented doors, handles, number plates", params=[
    Param("count", "int", "Spinde", lo=1, hi=4),
    Param("height", "float", "Höhe (m)", lo=1.2, hi=2.4, size=True),
    Param("open", "bool", "Eine Tür offen"),
    Param("bench", "bool", "Bank davor"),
])
def locker(rng, a):
    p = a.p
    n = p.int("count", 1, 3)
    h = p.float("height", 1.8, 2.1)
    lw, d = rng.uniform(0.4, 0.5), rng.uniform(0.45, 0.55)
    w = n * lw
    mat = p.material(["M_Wall", "M_Metal", "M_RobotBody", "M_RobotDark"])
    body = a.part("Body")
    cube(body, (w, d, h), (0, 0, h / 2), "M_RobotDark", bevel=0.02)
    cube(body, (w + 0.04, d + 0.04, 0.06), (0, 0, h + 0.03), mat, bevel=0.01)
    opened = rng.randrange(n) if p.bool("open", 0.3) else -1
    for i in range(n):
        x = -w / 2 + lw * (i + 0.5)
        if i == opened:  # open door swung out to the left, dark inside
            cube(body, (lw - 0.04, 0.02, h - 0.1), (x, -d / 2 + 0.02, h / 2), "M_Ground")
            hx = x - lw / 2 + 0.02
            cube(body, (lw - 0.04, 0.03, h - 0.12), (hx - (lw - 0.04) / 2 * math.cos(deg(70)),
                                                     -d / 2 - (lw - 0.04) / 2 * math.sin(deg(70)), h / 2), mat,
                 rot=(0, 0, deg(70)))
            cube(body, (lw - 0.08, d - 0.08, 0.02), (x, 0, h * 0.75), "M_Metal")  # shelf
            continue
        cube(body, (lw - 0.04, 0.03, h - 0.1), (x, -d / 2 - 0.005, h / 2), mat, bevel=0.005)
        for k in range(4):  # vent slots at the top
            cube(body, (lw * 0.5, 0.035, 0.02), (x, -d / 2 - 0.01, h - 0.2 - k * 0.05), "M_RobotDark")
        cube(body, (0.03, 0.05, 0.14), (x + lw * 0.32, -d / 2 - 0.03, h * 0.55), "M_Metal")  # handle
        cube(body, (lw * 0.3, 0.035, 0.06), (x, -d / 2 - 0.01, h * 0.8), "M_Platform")  # number plate
    if p.bool("bench", 0.3):
        bw = max(0.8, w * 0.9)
        cube(body, (bw, 0.3, 0.05), (0, -d / 2 - 0.45, 0.45), p.material(["M_Metal", "M_Wall"]))
        for x in (-bw / 2 + 0.1, bw / 2 - 0.1):
            cube(body, (0.05, 0.25, 0.43), (x, -d / 2 - 0.45, 0.215), "M_RobotDark")
    a.meta.update({"lockers": n, "open": opened >= 0})


@model("shelf", "Shelf", "props", "Storage shelf with 2-5 levels, filled with small crates and canisters", params=[
    Param("width", "float", "Breite (m)", lo=0.6, hi=3.0, size=True),
    Param("height", "float", "Höhe (m)", lo=0.8, hi=3.0, size=True),
    Param("levels", "int", "Böden", lo=2, hi=5),
    Param("fill", "float", "Füllgrad", lo=0.0, hi=1.0),
])
def shelf(rng, a):
    p = a.p
    w = p.float("width", 1.2, 2.2)
    h = p.float("height", 1.6, 2.2)
    n = p.int("levels", 3, 4)
    fill = p.float("fill", 0.4, 0.9)
    d = rng.uniform(0.45, 0.6)
    mat = p.material(["M_Metal", "M_RobotDark", "M_HazardOrange"])
    body, load = a.part("Body"), a.part("Load")
    for x in (-w / 2, w / 2):
        for y in (-d / 2, d / 2):
            cube(body, (0.05, 0.05, h), (x, y, h / 2), mat)
    gap = (h - 0.1) / n
    for i in range(n + 1):
        z = 0.1 + i * gap if i < n else h - 0.02
        cube(body, (w, d, 0.03), (0, 0, z), "M_Metal" if mat != "M_Metal" else "M_Wall")
        if i == n:
            break
        x = -w / 2 + 0.05
        while x < w / 2 - 0.15:
            slot = rng.uniform(0.2, 0.4)
            if rng.random() < fill and x + slot < w / 2:
                _small_box(rng, load, x + slot / 2, 0, z + 0.015, slot, d * 0.9, gap - 0.08)
            x += slot + 0.03
    for s in (-1, 1):  # diagonal braces at the back
        cube(body, (0.02, 0.02, math.hypot(w, h) * 0.9), (0, d / 2, h / 2), "M_RobotDark",
             rot=(0, s * math.atan2(w, h), 0))
    a.meta["levels"] = n


@model("workbench", "Workbench", "props", "Workbench: table top, drawers, vise, tools, pegboard and lamp", params=[
    Param("width", "float", "Breite (m)", lo=1.0, hi=3.0, size=True),
    Param("pegboard", "bool", "Werkzeugwand"),
    Param("vise", "bool", "Schraubstock"),
    Param("lamp", "bool", "Lampe"),
])
def workbench(rng, a):
    p = a.p
    w = p.float("width", 1.4, 2.2)
    d, h = rng.uniform(0.7, 0.9), rng.uniform(0.85, 0.95)
    body, tools = a.part("Body"), a.part("Tools")
    top_mat = p.material(["M_Metal", "M_Wall", "M_Platform"])
    cube(body, (w, d, 0.06), (0, 0, h - 0.03), top_mat, bevel=0.01)
    for x in (-w / 2 + 0.05, w / 2 - 0.05):
        for y in (-d / 2 + 0.05, d / 2 - 0.05):
            cube(body, (0.06, 0.06, h - 0.06), (x, y, (h - 0.06) / 2), "M_RobotDark")
    cube(body, (w - 0.1, d - 0.1, 0.03), (0, 0, 0.15), "M_RobotDark")  # lower shelf
    dw = min(0.5, w * 0.3)
    cube(body, (dw, d - 0.1, h * 0.55), (w / 2 - 0.05 - dw / 2, 0, h - 0.06 - h * 0.275), "M_Wall", bevel=0.01)
    for k in range(3):  # drawers
        z = h - 0.12 - k * h * 0.17
        cube(body, (dw - 0.04, 0.02, h * 0.14), (w / 2 - 0.05 - dw / 2, -d / 2 + 0.04, z - 0.02), "M_Metal")
        cube(body, (dw * 0.4, 0.03, 0.02), (w / 2 - 0.05 - dw / 2, -d / 2 + 0.025, z), "M_RobotDark")
    if p.bool("vise", 0.6):
        x = -w / 2 + 0.2
        cube(tools, (0.18, 0.12, 0.08), (x, -d / 2 + 0.12, h + 0.04), "M_HazardOrange", bevel=0.01)
        cube(tools, (0.04, 0.12, 0.1), (x - 0.07, -d / 2 + 0.04, h + 0.1), "M_Metal")
        cube(tools, (0.04, 0.12, 0.1), (x + 0.07, -d / 2 + 0.04, h + 0.1), "M_Metal")
        cyl(tools, 0.012, 0.2, (x, -d / 2 - 0.05, h + 0.06), "M_Metal", sides=6, rot=ALONG_Y)
    for _ in range(rng.randint(2, 5)):  # tools lying on the top
        x, y = rng.uniform(-w * 0.2, w * 0.35), rng.uniform(-d * 0.3, d * 0.2)
        cube(tools, (rng.uniform(0.15, 0.3), 0.03, 0.02), (x, y, h + 0.01), rng.choice(["M_Metal", "M_RobotDark"]),
             rot=(0, 0, rng.uniform(0, math.pi)))
    if rng.random() < 0.6:  # a small box of parts
        _small_box(rng, tools, rng.uniform(-w * 0.1, w * 0.2), d * 0.25, h, 0.3, 0.25, 0.2)
    if p.bool("pegboard", 0.6):
        cube(body, (w, 0.04, 0.8), (0, d / 2 - 0.02, h + 0.45), "M_Wall")
        for _ in range(rng.randint(3, 7)):
            x, z = rng.uniform(-w / 2 + 0.15, w / 2 - 0.15), h + rng.uniform(0.25, 0.7)
            cube(tools, (0.03, 0.03, rng.uniform(0.15, 0.3)), (x, d / 2 - 0.06, z), rng.choice(["M_Metal", "M_HazardOrange"]))
    if p.bool("lamp", 0.5):
        glow = p.glow(weights=(0.8, 0.05, 0.15))
        x = w / 2 - 0.25
        cyl(body, 0.08, 0.03, (x, d / 2 - 0.15, h + 0.015), "M_RobotDark", sides=8)
        cube(body, (0.025, 0.025, 0.5), (x, d / 2 - 0.15, h + 0.25), "M_Metal", rot=(deg(-15), 0, 0))
        cube(body, (0.2, 0.12, 0.08), (x, d / 2 - 0.3, h + 0.5), "M_RobotDark", bevel=0.01)
        cube(a.part("Lights"), (0.16, 0.08, 0.02), (x, d / 2 - 0.3, h + 0.455), glow)


@model("tool_cart", "ToolCart", "props", "Rolling tool cart: drawers, handle, castor wheels", params=[
    Param("drawers", "int", "Schubladen", lo=1, hi=6),
    Param("width", "float", "Breite (m)", lo=0.4, hi=1.2, size=True),
    Param("top", "choice", "Oben", choices=("tools", "tray", "box")),
])
def tool_cart(rng, a):
    p = a.p
    w = p.float("width", 0.6, 0.9)
    d, h = rng.uniform(0.4, 0.5), rng.uniform(0.75, 0.95)
    n = p.int("drawers", 3, 5)
    mat = p.material(["M_HazardOrange", "M_Wall", "M_RobotBody", "M_Warning"])
    body = a.part("Body")
    z0 = 0.12
    cube(body, (w, d, h - z0), (0, 0, z0 + (h - z0) / 2), mat, bevel=0.02)
    dh = (h - z0 - 0.08) / n
    for i in range(n):
        z = z0 + 0.04 + dh * (i + 0.5)
        cube(body, (w - 0.06, 0.02, dh - 0.03), (0, -d / 2 - 0.005, z), "M_RobotDark" if i % 2 else mat)
        cube(body, (w * 0.5, 0.04, 0.02), (0, -d / 2 - 0.02, z + dh * 0.25), "M_Metal")
    for x in (-w / 2 + 0.06, w / 2 - 0.06):
        for y in (-d / 2 + 0.06, d / 2 - 0.06):
            cube(body, (0.04, 0.04, 0.05), (x, y, z0 - 0.025), "M_Metal")
            cyl(body, 0.045, 0.03, (x, y, 0.045), "M_RobotDark", sides=8, rot=ALONG_X)
    for y in (-d / 2 + 0.05, d / 2 - 0.05):  # handle on the right
        cube(body, (0.12, 0.03, 0.03), (w / 2 + 0.06, y, h - 0.1), "M_Metal")
    cyl(body, 0.02, d - 0.06, (w / 2 + 0.11, 0, h - 0.1), "M_Metal", sides=6, rot=ALONG_Y)
    top = p.choice("top", ["tools", "tray", "box"])
    tools = a.part("Tools")
    if top == "tools":
        for _ in range(rng.randint(2, 4)):
            cube(tools, (rng.uniform(0.12, 0.25), 0.03, 0.02), (rng.uniform(-w * 0.3, w * 0.3),
                                                               rng.uniform(-d * 0.3, d * 0.3), h + 0.01),
                 rng.choice(["M_Metal", "M_RobotDark"]), rot=(0, 0, rng.uniform(0, math.pi)))
    elif top == "tray":
        cube(tools, (w - 0.04, d - 0.04, 0.02), (0, 0, h + 0.01), "M_Metal")
        for s in (-1, 1):
            cube(tools, (w - 0.04, 0.02, 0.06), (0, s * (d / 2 - 0.03), h + 0.04), "M_Metal")
    else:
        _small_box(rng, tools, 0, 0, h, w * 0.8, d * 0.8, 0.3)
    a.meta["top"] = top


@model("cryo_pod", "CryoPod", "props", "Cryo pod, standing or lying: glass hood (Glass), glow ring, control panel",
       params=[
           Param("pose", "choice", "Lage", choices=("standing", "lying")),
           Param("length", "float", "Länge (m)", lo=1.6, hi=3.0, size=True),
           Param("occupied", "bool", "Belegt (Silhouette)"),
           Param("frost", "bool", "Vereist (Kristall-Akzente)"),
       ])
def cryo_pod(rng, a):
    p = a.p
    pose = p.choice("pose", ["standing", "standing", "lying"])
    length = p.float("length", 2.0, 2.4)
    r = rng.uniform(0.4, 0.5)
    glow = p.glow(weights=(0.85, 0.0, 0.15))
    body, glass, lights = a.part("Body"), a.part("Glass"), a.part("Glow")
    shell = p.material(["M_RobotBody", "M_Platform", "M_Wall"])
    sides = 8
    a.meta["pose"] = pose
    occupied = p.bool("occupied", 0.5)
    frost = p.bool("frost", 0.3)
    if pose == "standing":
        cyl(body, r * 1.25, 0.2, (0, 0, 0.1), "M_RobotDark", sides=sides, bevel=0.02)
        cyl(lights, r * 1.27, 0.04, (0, 0, 0.17), glow, sides=sides)
        h = length
        cube(body, (r * 2.0, r * 0.8, h), (0, r * 0.5, 0.2 + h / 2), shell, bevel=0.04)  # back shell
        cyl(glass, r, h - 0.1, (0, -0.05, 0.2 + h / 2), "M_Glass", sides=sides)
        cyl(body, r * 1.15, 0.25, (0, 0, 0.2 + h + 0.12), shell, sides=sides, radius_top=r * 0.8, bevel=0.02)
        for z in (0.35, 0.2 + h - 0.1):
            cyl(body, r * 1.06, 0.06, (0, -0.05, z), "M_RobotDark", sides=sides)
        cube(body, (0.3, 0.05, 0.4), (r * 0.9, -r * 0.4, 1.2), "M_RobotDark", rot=(0, 0, deg(-30)))
        cube(a.part("Screen"), (0.24, 0.02, 0.3), (r * 0.9 + 0.01, -r * 0.4 - 0.03, 1.2), glow, rot=(0, 0, deg(-30)))
        if occupied:  # dark silhouette behind the glass
            sil = a.part("Occupant")
            cube(sil, (r * 0.8, r * 0.5, h * 0.55), (0, 0, 0.2 + h * 0.35), "M_RobotDark", bevel=0.05)
            cyl(sil, r * 0.25, r * 0.5, (0, 0, 0.2 + h * 0.72), "M_RobotDark", sides=8)
        if frost:
            for _ in range(rng.randint(3, 6)):
                ang = rng.uniform(math.pi * 1.1, math.pi * 1.9)
                cyl(a.part("Crystals"), 0.04, rng.uniform(0.1, 0.25),
                    (math.cos(ang) * r * 1.2, math.sin(ang) * r * 1.2, 0.25), "M_Crystal", sides=5, radius_top=0.0)
    else:
        h = r * 1.1
        cube(body, (length + 0.2, r * 2.4, 0.5), (0, 0, 0.25), "M_RobotDark", bevel=0.03)
        cube(lights, (length + 0.22, 0.04, 0.04), (0, -r * 1.2 - 0.01, 0.4), glow)
        cube(body, (length, r * 2.0, 0.25), (0, 0, 0.5 + 0.125), shell, bevel=0.03)
        hood = 0.75 + h * 0.4
        cyl(glass, r * 0.95, length - 0.3, (0, 0, hood), "M_Glass", sides=sides, rot=ALONG_X)
        for x in (-length / 2 + 0.1, length / 2 - 0.1):
            cyl(body, r * 1.05, 0.18, (x, 0, hood), shell, sides=sides, rot=ALONG_X)
        cube(body, (0.4, 0.05, 0.3), (-length / 2 - 0.05, -r * 1.3, 0.7), "M_RobotDark", rot=(deg(-20), 0, 0))
        cube(a.part("Screen"), (0.32, 0.02, 0.22), (-length / 2 - 0.05, -r * 1.33, 0.705), glow, rot=(deg(-20), 0, 0))
        if occupied:
            sil = a.part("Occupant")
            cube(sil, (length * 0.55, r * 0.7, r * 0.4), (length * 0.05, 0, hood - r * 0.3), "M_RobotDark", bevel=0.05)
            cyl(sil, r * 0.25, r * 0.4, (-length * 0.3, 0, hood - r * 0.25), "M_RobotDark", sides=8, rot=ALONG_X)
        if frost:
            for _ in range(rng.randint(3, 6)):
                x = rng.uniform(-length / 2, length / 2)
                cyl(a.part("Crystals"), 0.04, rng.uniform(0.1, 0.2), (x, -r * 1.2, 0.55), "M_Crystal", sides=5,
                    radius_top=0.0, rot=(deg(40), 0, 0))
    a.meta.update({"occupied": occupied, "frost": frost})


@model("chair", "Chair", "props", "Control room swivel chair: star base, column, seat, back, optional armrests",
       params=[
           Param("armrests", "bool", "Armlehnen"),
           Param("back", "choice", "Lehne", choices=("high", "low")),
           Param("turn", "float", "Drehung (°)", lo=-180, hi=180),
       ])
def chair(rng, a):
    p = a.p
    seat_h = rng.uniform(0.45, 0.55)
    sw = rng.uniform(0.45, 0.55)
    turn = deg(p.float("turn", -30, 30))
    mat = p.material(["M_RobotDark", "M_Wall", "M_HazardOrange", "M_RobotBody"])
    body = a.part("Body")
    for i in range(5):  # star base with castors
        ang = 2 * math.pi * i / 5
        cube(body, (0.3, 0.05, 0.04), (math.cos(ang) * 0.15, math.sin(ang) * 0.15, 0.08), "M_Metal",
             rot=(0, 0, ang))
        cyl(body, 0.035, 0.04, (math.cos(ang) * 0.29, math.sin(ang) * 0.29, 0.035), "M_RobotDark", sides=6,
            rot=(0, math.pi / 2, ang + math.pi / 2))
    cyl(body, 0.035, seat_h - 0.1, (0, 0, 0.1 + (seat_h - 0.1) / 2), "M_Metal", sides=8)

    def turned(x, y):
        return (x * math.cos(turn) - y * math.sin(turn), x * math.sin(turn) + y * math.cos(turn))

    cube(body, (sw, sw, 0.08), (0, 0, seat_h), mat, bevel=0.03, rot=(0, 0, turn))
    back = p.choice("back", ["high", "low"])
    bh = 0.7 if back == "high" else 0.4
    bx, by = turned(0, sw / 2)
    cube(body, (sw * 0.95, 0.07, bh), (bx, by, seat_h + 0.12 + bh / 2), mat, bevel=0.03,
         rot=(deg(-8), 0, turn))
    cx, cy = turned(0, sw / 2 - 0.03)
    cube(body, (0.06, 0.04, 0.2), (cx, cy, seat_h + 0.08), "M_Metal", rot=(0, 0, turn))
    if p.bool("armrests", 0.6):
        for s in (-1, 1):
            ax, ay = turned(s * (sw / 2 + 0.02), 0)
            cube(body, (0.04, 0.04, 0.2), (ax, ay, seat_h + 0.1), "M_Metal", rot=(0, 0, turn))
            ax, ay = turned(s * (sw / 2 + 0.02), -0.02)
            cube(body, (0.06, sw * 0.7, 0.04), (ax, ay, seat_h + 0.21), "M_RobotDark", rot=(0, 0, turn))
    a.meta["back"] = back


@model("gas_rack", "GasRack", "props", "Rack with 2-6 gas bottles: caps, chains, warning colours", params=[
    Param("bottles", "int", "Flaschen", lo=1, hi=6),
    Param("height", "float", "Flaschenhöhe (m)", lo=0.6, hi=1.8, size=True),
    Param("cage", "bool", "Gitter vorne"),
])
def gas_rack(rng, a):
    p = a.p
    n = p.int("bottles", 2, 5)
    bh = p.float("height", 1.2, 1.6)
    r = rng.uniform(0.1, 0.14)
    w = n * (2 * r + 0.06) + 0.1
    d = 2 * r + 0.12
    body, bottles = a.part("Body"), a.part("Bottles")
    frame = p.material(["M_RobotDark", "M_Metal", "M_Warning"])
    cube(body, (w, d, 0.06), (0, 0, 0.03), frame)
    for x in (-w / 2 + 0.03, w / 2 - 0.03):
        for y in (-d / 2 + 0.03, d / 2 - 0.03):
            cube(body, (0.05, 0.05, bh * 0.9), (x, y, 0.06 + bh * 0.45), frame)
    for z in (bh * 0.35, bh * 0.75):
        cube(body, (w, 0.04, 0.04), (0, d / 2 - 0.03, z), frame)
        cube(body, (w, 0.03, 0.03), (0, -d / 2 + 0.03, z), "M_Metal")  # chain bar in front
    colours = ["M_HazardOrange", "M_Warning", "M_Wall", "M_Metal", "M_RobotBody", "M_Platform"]
    mat = None
    for i in range(n):
        x = -w / 2 + 0.05 + (2 * r + 0.06) * (i + 0.5)
        h = bh * rng.uniform(0.85, 1.0)
        if mat is None or rng.random() < 0.3:  # mostly one colour, sometimes a different gas
            mat = p.material(colours)
        cyl(bottles, r, h - r * 0.7, (x, 0, 0.06 + (h - r * 0.7) / 2), mat, sides=10, bevel=0.02)
        cyl(bottles, r, r * 0.7, (x, 0, 0.06 + h - r * 0.35), mat, sides=10, radius_top=r * 0.35)
        cyl(bottles, r * 0.25, 0.08, (x, 0, 0.06 + h + 0.04), "M_Metal", sides=6)
        cyl(bottles, r * 0.4, 0.06, (x, 0, 0.06 + h + 0.1), "M_RobotDark", sides=6)
        cyl(bottles, r * 1.02, 0.05, (x, 0, 0.06 + h * 0.75), "M_RobotDark" if mat != "M_RobotDark" else "M_Warning",
            sides=10)
    if p.bool("cage", 0.3):
        for k in range(int(w / 0.15)):
            cube(body, (0.02, 0.02, bh * 0.8), (-w / 2 + 0.07 + k * 0.15, -d / 2 + 0.01, 0.06 + bh * 0.4), "M_Metal")
    a.meta["bottles"] = n


@model("extinguisher", "Extinguisher", "props", "Fire extinguisher: bottle, valve head, hose, optional stand or "
       "cabinet", params=[
           Param("height", "float", "Höhe (m)", lo=0.3, hi=1.0, size=True),
           Param("holder", "choice", "Halter", choices=("none", "stand", "cabinet")),
       ])
def extinguisher(rng, a):
    p = a.p
    h = p.float("height", 0.5, 0.7)
    r = h * rng.uniform(0.15, 0.2)
    holder = p.choice("holder", ["none", "stand", "cabinet"])
    body, unit = a.part("Body"), a.part("Unit")
    mat = p.material(["M_HazardOrange", "M_HazardOrange", "M_Warning"])
    z0 = 0.0
    if holder == "stand":
        cube(body, (r * 4, r * 3, 0.04), (0, 0, 0.02), "M_RobotDark")
        cube(body, (0.04, 0.04, h * 1.2), (0, r * 1.3, h * 0.6), "M_Metal")
        cube(body, (r * 3, 0.04, 0.12), (0, r * 1.3, h * 1.25), "M_Platform")
        z0 = 0.04
    elif holder == "cabinet":  # open-front cabinet with a sign on top
        cw, cd, ch = r * 3.4, r * 2.8, h * 1.35
        cube(body, (cw, 0.04, ch), (0, cd / 2, ch / 2 + 0.02), "M_Wall")
        for s in (-1, 1):
            cube(body, (0.04, cd, ch), (s * cw / 2, 0, ch / 2 + 0.02), "M_Wall")
        cube(body, (cw + 0.04, cd, 0.04), (0, 0, 0.02), "M_Wall")
        cube(body, (cw + 0.04, cd, 0.04), (0, 0, ch + 0.04), "M_Wall")
        cube(body, (cw * 0.8, 0.02, ch * 0.12), (0, -cd / 2 - 0.01, ch - 0.04), "M_HazardOrange")
        z0 = 0.04
    cyl(unit, r, h * 0.8, (0, 0, z0 + h * 0.4), mat, sides=10, bevel=0.02)
    cyl(unit, r * 0.9, h * 0.08, (0, 0, z0 + h * 0.84), mat, sides=10, radius_top=r * 0.4)
    cyl(unit, r * 0.35, h * 0.08, (0, 0, z0 + h * 0.92), "M_RobotDark", sides=8)
    cube(unit, (r * 1.6, r * 0.4, h * 0.04), (r * 0.4, 0, z0 + h * 0.98), "M_Metal")  # handle lever
    cube(unit, (r * 1.2, r * 0.3, h * 0.03), (r * 0.3, 0, z0 + h * 0.94), "M_Metal")
    cube(unit, (r * 1.6, 0.01, h * 0.25), (0, -r - 0.004, z0 + h * 0.45), "M_Platform")  # label
    hose = h * 0.5
    cyl(unit, r * 0.15, hose, (-r * 1.05, 0, z0 + h * 0.92 - hose / 2), "M_RobotDark", sides=6)
    cyl(unit, r * 0.25, h * 0.08, (-r * 1.05, 0, z0 + h * 0.92 - hose - h * 0.04), "M_RobotDark", sides=6,
        radius_top=r * 0.15)
    a.meta["holder"] = holder


@model("medkit", "Medkit", "props", "Wall first aid box or cabinet with a cross (Lights)", pivot="wall", params=[
    Param("style", "choice", "Art", choices=("box", "cabinet")),
    Param("mount_height", "float", "Mitte über Boden (m)", lo=0.5, hi=2.5),
    Param("cross", "choice", "Kreuz", choices=("red", "cyan", "white")),
])
def medkit(rng, a):
    p = a.p
    style = p.choice("style", ["box", "box", "cabinet"])
    w, h = (rng.uniform(0.35, 0.45), rng.uniform(0.3, 0.38)) if style == "box" else \
        (rng.uniform(0.5, 0.7), rng.uniform(0.7, 0.9))
    d = 0.12 if style == "box" else 0.22
    z = p.value("mount_height", rng.uniform(1.2, 1.5))
    z = max(z, h / 2 + 0.05)
    body = a.part("Body")
    mat = p.material(["M_Platform", "M_RobotBody", "M_Wall"])
    yf = 0.1 - d
    cube(body, (w, d, h), (0, 0.1 - d / 2, z), mat, bevel=0.02)
    cube(body, (w * 0.9, 0.015, h * 0.9), (0, yf - 0.005, z), "M_RobotBody" if mat != "M_RobotBody" else "M_Platform")
    cross_mat = {"red": "M_GlowRed", "cyan": "M_GlowCyan", "white": "M_Platform"}[p.choice("cross", ["red", "red", "cyan", "white"])]
    lights = a.part("Lights")
    s = min(w, h) * 0.5
    cube(lights, (s, 0.02, s * 0.32), (0, yf - 0.015, z + (h * 0.1 if style == "cabinet" else 0)), cross_mat)
    cube(lights, (s * 0.32, 0.021, s), (0, yf - 0.015, z + (h * 0.1 if style == "cabinet" else 0)), cross_mat)
    if style == "box":
        cube(body, (w * 0.3, 0.04, 0.03), (0, yf - 0.03, z + h / 2 - 0.04), "M_RobotDark")  # latch
    else:
        cube(body, (0.03, 0.04, 0.14), (w * 0.38, yf - 0.03, z - h * 0.2), "M_Metal")  # handle
        cube(body, (w * 0.9, 0.015, 0.02), (0, yf - 0.015, z - h * 0.3), "M_RobotDark")
    a.meta["style"] = style


@model("barrier", "Barrier", "props", "Barrier: striped gate bar on posts, jersey barrier block or traffic cones",
       params=[
           Param("style", "choice", "Art", choices=("gate", "jersey", "cones")),
           Param("width", "float", "Breite (m)", lo=0.8, hi=4.0, size=True),
           Param("lights", "bool", "Warnlichter"),
       ])
def barrier(rng, a):
    p = a.p
    style = p.choice("style", ["gate", "jersey", "cones"])
    w = p.float("width", 1.5, 2.5)
    body = a.part("Body")
    a.meta["style"] = style
    lamp_pos = []
    if style == "gate":
        for x in (-w / 2, w / 2):
            cube(body, (0.35, 0.25, 0.06), (x, 0, 0.03), "M_RobotDark")
            cube(body, (0.06, 0.06, 1.0), (x, 0, 0.53), "M_Metal")
        for z in (0.95, 0.55):
            cube(body, (w + 0.1, 0.05, 0.16), (0, -0.06, z), "M_Platform")
            stripes(body, w, (0, -0.09, z), count=max(3, int(w * 2.5)), width=0.01, height=0.15,
                    material="M_HazardOrange")
        lamp_pos = [(-w / 2, -0.06, 1.1), (w / 2, -0.06, 1.1)]
    elif style == "jersey":
        prof = [(-0.3, 0.0), (0.3, 0.0), (0.3, 0.08), (0.12, 0.3), (0.08, 0.8), (-0.08, 0.8), (-0.12, 0.3),
                (-0.3, 0.08)]
        body.add(prism(prof, w, p.material(["M_Wall", "M_Platform", "M_HazardOrange"])),
                 basis=((0, 0, 1), (1, 0, 0), (0, 1, 0)))
        for x in (-w * 0.25, w * 0.25):
            cube(body, (w * 0.18, 0.01, 0.12), (x, -0.105, 0.55), "M_Warning", rot=(deg(-4.6), deg(30), 0))
        lamp_pos = [(0.0, 0.0, 0.85)]
    else:  # cones
        n = max(2, int(w / 0.7) + 1)
        for i in range(n):
            x = -w / 2 + w * i / (n - 1) + rng.uniform(-0.1, 0.1)
            y = rng.uniform(-0.15, 0.15)
            ch = rng.uniform(0.45, 0.7)
            cube(body, (0.38, 0.38, 0.04), (x, y, 0.02), "M_RobotDark")
            cyl(body, 0.15, ch, (x, y, 0.04 + ch / 2), "M_HazardOrange", sides=8, radius_top=0.03)
            for f in (0.35, 0.6):
                rr = 0.15 + (0.03 - 0.15) * f + 0.006
                cyl(body, rr, 0.06, (x, y, 0.04 + ch * f), "M_Platform", sides=8, radius_top=rr - 0.012)
            if i < n - 1 and rng.random() < 0.7:  # chain / tape between cones
                lamp_pos.append((x, y, 0.04 + ch + 0.03))
        lamp_pos = lamp_pos[:2]
    if p.bool("lights", 0.5) and lamp_pos:
        lights = a.part("Lights")
        for x, y, z in lamp_pos:
            cyl(lights, 0.05, 0.08, (x, y, z), p.glow_from(["M_GlowOrange", "M_GlowRed"]), sides=8)


@model("pallet", "Pallet", "props", "Pallet, empty or loaded with crates, sacks or canisters", params=[
    Param("size", "choice", "Größe", choices=("euro", "square")),
    Param("load", "choice", "Ladung", choices=("none", "crates", "sacks", "canisters")),
    Param("straps", "bool", "Spanngurte"),
])
def pallet(rng, a):
    p = a.p
    w, d = (1.2, 0.8) if p.choice("size", ["euro", "euro", "square"]) == "euro" else (1.0, 1.0)
    wood = p.material(["M_Wall", "M_Metal", "M_RobotDark"])
    body = a.part("Body")
    for y in (-d / 2 + 0.05, 0, d / 2 - 0.05):  # bottom boards
        cube(body, (w, 0.1, 0.02), (0, y, 0.01), wood)
    for x in (-w / 2 + 0.05, 0, w / 2 - 0.05):  # blocks
        for y in (-d / 2 + 0.05, 0, d / 2 - 0.05):
            cube(body, (0.1, 0.1, 0.08), (x, y, 0.06), "M_RobotDark")
    n = 5 if w > 1.1 else 4
    for i in range(n):  # top boards
        cube(body, (w, d / n * 0.7, 0.025), (0, -d / 2 + d * (i + 0.5) / n, 0.1125), wood)
    top = 0.125
    load = p.choice("load", ["none", "crates", "crates", "sacks", "canisters"])
    a.meta["load"] = load
    if load == "none":
        return
    cargo = a.part("Load")
    height = 0.0
    if load == "crates":
        for layer in range(rng.randint(1, 2)):
            for x in (-w / 4, w / 4):
                for y in (-d / 4, d / 4):
                    if rng.random() < 0.85 or layer == 0:
                        s = rng.uniform(0.32, 0.4)
                        z = top + layer * 0.42
                        cube(cargo, (w / 2 - 0.04, d / 2 - 0.04, s), (x, y, z + s / 2), rng.choice(BOX_MATS),
                             bevel=0.015)
                        height = max(height, layer * 0.42 + s)
    elif load == "sacks":
        for layer in range(rng.randint(1, 3)):
            for k in range(2):
                yy = (-d / 4 if k == 0 else d / 4)
                cube(cargo, (w * 0.9, d / 2 - 0.04, 0.16), (0, yy, top + 0.08 + layer * 0.15),
                     rng.choice(["M_Platform", "M_Wall", "M_Warning"]), bevel=0.05,
                     rot=(0, 0, deg(rng.uniform(-6, 6))))
                height = max(height, 0.16 + layer * 0.15)
    else:
        for x in (-w * 0.3, 0, w * 0.3):
            for y in (-d * 0.25, d * 0.25):
                ch = rng.uniform(0.5, 0.6)
                cyl(cargo, 0.15, ch, (x, y, top + ch / 2), rng.choice(["M_HazardOrange", "M_Wall", "M_Metal"]),
                    sides=10, bevel=0.01)
                cyl(cargo, 0.155, 0.03, (x, y, top + ch * 0.8), "M_RobotDark", sides=10)
                height = max(height, ch)
    if p.bool("straps", 0.6):
        for x in (-w * 0.3, w * 0.3):
            cube(cargo, (0.05, d + 0.02, 0.02), (x, 0, top + height + 0.01), "M_HazardOrange")
            for s in (-1, 1):
                cube(cargo, (0.05, 0.02, height), (x, s * (d / 2 + 0.01), top + height / 2), "M_HazardOrange")


# a polygon drawn in (x, z) facing the front: local x -> x, local y -> z, extrusion -> -y
UPRIGHT = ((1, 0, 0), (0, 0, -1), (0, 1, 0))
SIGN_SYMBOLS = ("warning", "arrow", "exit", "electric", "number")


@model("sign", "Sign", "props", "Wall sign: warning triangle, arrow, exit, high voltage or a sector number",
       pivot="wall", params=[
           Param("symbol", "choice", "Symbol", choices=SIGN_SYMBOLS),
           Param("size", "float", "Größe (m)", lo=0.2, hi=1.5, size=True),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.5, hi=3.5),
           Param("lit", "bool", "Beleuchtet (Glow)"),
       ])
def sign(rng, a):
    p = a.p
    symbol = p.choice("symbol", list(SIGN_SYMBOLS))
    s = p.float("size", 0.4, 0.7)
    z = p.value("mount_height", rng.uniform(1.6, 2.2))
    z = max(z, s / 2 + 0.05)
    lit = p.bool("lit", 0.4)
    body = a.part("Body")
    sym = a.part("Glow") if lit else body
    glow = p.glow() if lit else None
    plate_mat = {"warning": "M_Warning", "electric": "M_Warning", "arrow": "M_RobotDark", "exit": "M_RobotDark",
                 "number": p.material(["M_Platform", "M_RobotDark", "M_HazardOrange"])}[symbol]
    ink = glow or ("M_RobotDark" if plate_mat in ("M_Warning", "M_Platform", "M_HazardOrange") else "M_Platform")
    w = s * (1.6 if symbol in ("arrow", "exit") else 1.0)
    cube(body, (w + 0.04, 0.04, s + 0.04), (0, 0.08, z), "M_RobotDark", bevel=0.01)
    cube(body, (w, 0.02, s), (0, 0.05, z), plate_mat)
    y = 0.03
    a.meta["symbol"] = symbol
    if symbol == "warning":
        tri = [(-s * 0.4, -s * 0.33), (s * 0.4, -s * 0.33), (0.0, s * 0.37)]
        sym.add(prism(tri, 0.012, ink), loc=(0, y, z), basis=UPRIGHT)
        cube(body, (s * 0.07, 0.016, s * 0.28), (0, y - 0.004, z + s * 0.0), plate_mat)  # exclamation mark
        cube(body, (s * 0.07, 0.016, s * 0.07), (0, y - 0.004, z - s * 0.22), plate_mat)
    elif symbol == "electric":
        bolt = [(s * 0.05, s * 0.4), (-s * 0.2, -s * 0.02), (-s * 0.02, -s * 0.02), (-s * 0.1, -s * 0.4),
                (s * 0.2, s * 0.08), (s * 0.02, s * 0.08)]
        sym.add(prism(bolt, 0.012, ink), loc=(0, y, z), basis=UPRIGHT)
    elif symbol in ("arrow", "exit"):
        direction = rng.choice([-1, 1])
        arrow = [(-w * 0.35, -s * 0.08), (w * 0.05, -s * 0.08), (w * 0.05, -s * 0.25), (w * 0.38, 0.0),
                 (w * 0.05, s * 0.25), (w * 0.05, s * 0.08), (-w * 0.35, s * 0.08)]
        arrow = [(x * direction, zz) for x, zz in arrow]
        sym.add(prism(arrow, 0.012, ink), loc=(0, y, z - (s * 0.15 if symbol == "exit" else 0)),
                basis=UPRIGHT)
        if symbol == "exit":  # a running figure as two blocks above the arrow
            cube(sym, (s * 0.12, 0.012, s * 0.22), (-direction * w * 0.28, y, z + s * 0.2), ink,
                 rot=(0, deg(20 * direction), 0))
            cube(sym, (s * 0.1, 0.012, s * 0.1), (-direction * w * 0.24, y, z + s * 0.38), ink)
        a.meta["direction"] = "right" if direction > 0 else "left"
    else:  # sector number: seven-segment digit
        digit = rng.randint(0, 9)
        segs = {0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc", 5: "afgcd", 6: "afgedc", 7: "abc",
                8: "abcdefg", 9: "abcdfg"}[digit]
        dw, dh, t = s * 0.35, s * 0.6, s * 0.08
        pos = {"a": (0, dh / 2, True), "g": (0, 0, True), "d": (0, -dh / 2, True), "f": (-dw / 2, dh / 4, False),
               "b": (dw / 2, dh / 4, False), "e": (-dw / 2, -dh / 4, False), "c": (dw / 2, -dh / 4, False)}
        for k in segs:
            x, zz, horizontal = pos[k]
            cube(sym, (dw, 0.012, t) if horizontal else (t, 0.012, dh / 2), (x, y, z + zz), ink)
        a.meta["digit"] = digit


@model("bed", "Bed", "props", "Crew bed: cot, bunk bed with ladder or medical bed with raised back and monitor",
       params=[
           Param("style", "choice", "Art", choices=("cot", "bunk", "medical")),
           Param("length", "float", "Länge (m)", lo=1.6, hi=2.4, size=True),
           Param("blanket", "bool", "Decke"),
           Param("lamp", "bool", "Leselampe"),
       ])
def bed(rng, a):
    p = a.p
    style = p.choice("style", ["cot", "bunk", "medical"])
    length = p.float("length", 1.9, 2.1)
    width = rng.uniform(0.8, 1.0)
    frame = p.material(["M_Metal", "M_RobotDark", "M_Wall", "M_Platform"])
    body = a.part("Body")
    blanket_mat = rng.choice(["M_HazardOrange", "M_Wall", "M_RobotDark", "M_RobotBody"])
    has_blanket = p.bool("blanket", 0.7)
    a.meta["style"] = style

    def mattress(z, back=0.0):
        cube(body, (length - 0.1, width - 0.08, 0.04), (0, 0, z), frame)  # slatted base
        if back > 0:  # raised back part (head end at +X)
            cube(body, (length * 0.6, width - 0.1, 0.14), (-length * 0.18, 0, z + 0.09), "M_PortalPanel", bevel=0.03)
            hinge_x = length * 0.12
            seg = length * 0.32
            cube(body, (seg, width - 0.1, 0.14),
                 (hinge_x + math.cos(back) * seg / 2, 0, z + 0.09 + math.sin(back) * seg / 2), "M_PortalPanel",
                 bevel=0.03, rot=(0, -back, 0))
            pz = z + 0.2 + math.sin(back) * seg * 0.75
            cube(body, (0.12, width * 0.5, 0.1), (hinge_x + math.cos(back) * seg * 0.7, 0, pz), "M_Platform",
                 bevel=0.03, rot=(0, -back, 0))
            return
        cube(body, (length - 0.12, width - 0.1, 0.14), (0, 0, z + 0.09), "M_PortalPanel", bevel=0.03)
        cube(body, (0.3, width * 0.55, 0.1), (length / 2 - 0.25, 0, z + 0.2), "M_Platform", bevel=0.03)  # pillow
        if has_blanket:
            bl = length * rng.uniform(0.45, 0.65)
            cube(body, (bl, width - 0.04, 0.03), (-length / 2 + bl / 2 + 0.04, 0, z + 0.17), blanket_mat, bevel=0.01)
            cube(body, (bl, 0.03, 0.2), (-length / 2 + bl / 2 + 0.04, -width / 2 + 0.03, z + 0.08), blanket_mat)

    levels = [0.45] if style != "bunk" else [0.4, 1.45]
    top = levels[-1] + 0.4
    for sx in (-1, 1):  # posts
        for sy in (-1, 1):
            cube(body, (0.06, 0.06, top), (sx * (length / 2 - 0.03), sy * (width / 2 - 0.03), top / 2), frame)
    for z in levels:
        for sy in (-1, 1):
            cube(body, (length, 0.05, 0.1), (0, sy * (width / 2 - 0.025), z - 0.02), frame)
        mattress(z, deg(rng.uniform(25, 45)) if style == "medical" else 0.0)
    for sx in (-1, 1):  # head and foot boards
        cube(body, (0.04, width - 0.06, 0.35), (sx * (length / 2 - 0.03), 0, top - 0.2), frame)
    if style == "bunk":
        lx = -length / 2 + 0.35
        for x in (lx - 0.18, lx + 0.18):
            cube(body, (0.04, 0.04, top - 0.1), (x, -width / 2 - 0.06, (top - 0.1) / 2), "M_Metal")
        for k in range(4):
            cube(body, (0.4, 0.04, 0.03), (lx, -width / 2 - 0.06, 0.35 + k * 0.3), "M_Metal")
        cube(body, (length, 0.04, 0.2), (0, -width / 2 + 0.02, levels[1] + 0.25), frame)  # fall guard
    if style == "medical":
        for sx in (-1, 1):  # castors
            for sy in (-1, 1):
                cyl(body, 0.05, 0.04, (sx * (length / 2 - 0.03), sy * (width / 2 - 0.03), 0.05), "M_RobotDark",
                    sides=8, rot=ALONG_Y)
        mx = length / 2 + 0.25
        cyl(body, 0.03, 1.3, (mx, width * 0.3, 0.65), "M_Metal", sides=6)
        cube(body, (0.06, 0.32, 0.24), (mx, width * 0.3, 1.35), "M_RobotDark", bevel=0.01, rot=(0, 0, deg(-20)))
        cube(a.part("Screen"), (0.01, 0.26, 0.18), (mx - 0.035, width * 0.3, 1.35), "M_GlowCyan",
             rot=(0, 0, deg(-20)))
    if p.bool("lamp", 0.4):
        lz = levels[0] + 0.75 if style == "bunk" else top + 0.25
        cyl(body, 0.015, 0.25 if style != "bunk" else 0.04, (length / 2 - 0.03, 0, lz - 0.12), "M_Metal", sides=6)
        cube(body, (0.16, 0.12, 0.06), (length / 2 - 0.1, 0, lz), "M_RobotDark")
        cube(a.part("Lights"), (0.12, 0.08, 0.01), (length / 2 - 0.1, 0, lz - 0.035), "M_GlowOrange")


@model("table", "Table", "props", "Table: four-leg table, desk with drawers and monitor (Screen), round pedestal "
       "table or lab table with a shelf; optional clutter", params=[
           Param("style", "choice", "Art", choices=("table", "desk", "round", "lab")),
           Param("width", "float", "Breite (m)", lo=0.6, hi=3.0, size=True),
           Param("clutter", "bool", "Kleinkram oben"),
       ])
def table(rng, a):
    p = a.p
    style = p.choice("style", ["table", "desk", "round", "lab"])
    w = p.float("width", 1.0, 1.8)
    d = w * rng.uniform(0.45, 0.6) if style != "round" else w
    h = rng.uniform(0.74, 0.8) if style != "lab" else rng.uniform(0.88, 0.95)
    mat = p.material(["M_Wall", "M_Metal", "M_Platform", "M_RobotDark"])
    body = a.part("Body")
    a.meta["style"] = style
    if style == "round":
        r = w / 2
        cyl(body, r, 0.05, (0, 0, h - 0.025), mat, sides=12, bevel=0.01)
        cyl(body, 0.07, h - 0.08, (0, 0, (h - 0.05) / 2), "M_Metal", sides=8)
        cyl(body, r * 0.45, 0.05, (0, 0, 0.025), "M_RobotDark", sides=8)
        if rng.random() < 0.5:
            cyl(a.part("Lights"), r * 1.01, 0.015, (0, 0, h - 0.035), p.glow(), sides=12)
    else:
        cube(body, (w, d, 0.05), (0, 0, h - 0.025), mat, bevel=0.01)
        for sx in (-1, 1):
            for sy in (-1, 1):
                if style == "desk" and sx > 0:
                    continue
                cube(body, (0.05, 0.05, h - 0.05), (sx * (w / 2 - 0.05), sy * (d / 2 - 0.05), (h - 0.05) / 2),
                     "M_RobotDark" if style != "lab" else "M_Metal")
        if style == "desk":  # drawer block on the right, monitor and keyboard
            bw = min(0.45, w * 0.35)
            cube(body, (bw, d - 0.06, h - 0.05), (w / 2 - bw / 2 - 0.02, 0, (h - 0.05) / 2), mat, bevel=0.01)
            for k in range(3):
                zz = 0.15 + k * (h - 0.2) / 3
                cube(body, (bw - 0.06, 0.02, (h - 0.2) / 3 - 0.04), (w / 2 - bw / 2 - 0.02, -d / 2 + 0.02, zz + 0.1),
                     "M_RobotDark")
                cube(body, (0.1, 0.03, 0.02), (w / 2 - bw / 2 - 0.02, -d / 2, zz + 0.15), "M_Metal")
            mw = min(0.6, w * 0.4)
            cube(body, (0.15, 0.12, 0.02), (-w * 0.1, d * 0.2, h + 0.01), "M_RobotDark")
            cube(body, (0.04, 0.04, 0.2), (-w * 0.1, d * 0.2, h + 0.1), "M_RobotDark")
            cube(body, (mw, 0.04, mw * 0.6), (-w * 0.1, d * 0.2 - 0.02, h + 0.2 + mw * 0.3), "M_RobotDark", bevel=0.01)
            cube(a.part("Screen"), (mw * 0.9, 0.01, mw * 0.5), (-w * 0.1, d * 0.2 - 0.045, h + 0.2 + mw * 0.3),
                 p.glow(weights=(0.8, 0.05, 0.15)))
            cube(body, (0.45, 0.15, 0.02), (-w * 0.1, -d * 0.2, h + 0.01), "M_Wall")
        elif style == "lab":  # lower shelf, stripes
            cube(body, (w - 0.1, d - 0.1, 0.03), (0, 0, 0.2), mat)
            cube(body, (w, 0.02, 0.04), (0, -d / 2 - 0.005, h - 0.03), "M_Warning")
        else:
            for sy in (-1, 1):
                cube(body, (w - 0.1, 0.03, 0.08), (0, sy * (d / 2 - 0.05), h - 0.09), "M_RobotDark")
    if p.bool("clutter", 0.6):
        for _ in range(rng.randint(2, 5)):
            x, y = rng.uniform(-w * 0.35, w * 0.35), rng.uniform(-d * 0.3, d * 0.3)
            if style == "round" and math.hypot(x, y) > w * 0.4:
                continue
            kind = rng.random()
            if kind < 0.35:  # cup
                cyl(body, 0.04, 0.1, (x, y, h + 0.05), rng.choice(["M_Platform", "M_HazardOrange", "M_Metal"]),
                    sides=8)
            elif kind < 0.7:  # papers
                cube(body, (0.21, 0.29, 0.01), (x, y, h + 0.005), "M_PortalPanel", rot=(0, 0, rng.uniform(-0.5, 0.5)))
            else:  # small box / device
                cube(body, (0.15, 0.1, 0.06), (x, y, h + 0.03), rng.choice(BOX_MATS), bevel=0.01,
                     rot=(0, 0, rng.uniform(-0.5, 0.5)))


@model("bin", "Bin", "props", "Waste bin: round, square, a recycling row with coloured lids or a hazard bin; "
       "optional open lid and trash", params=[
           Param("style", "choice", "Art", choices=("round", "square", "recycling", "hazard")),
           Param("height", "float", "Höhe (m)", lo=0.3, hi=1.4, size=True),
           Param("open", "bool", "Deckel offen"),
           Param("trash", "bool", "Müll daneben"),
       ])
def waste_bin(rng, a):
    p = a.p
    style = p.choice("style", ["round", "square", "recycling", "hazard"])
    h = p.float("height", 0.6, 1.0)
    body = a.part("Body")
    is_open = p.bool("open", 0.3)
    a.meta["style"] = style
    if style == "recycling":
        n = rng.randint(2, 3)
        w = h * 0.55
        lids = rng.sample(["M_HazardOrange", "M_Warning", "M_GlowCyan", "M_Platform", "M_GlowRed"], n)
        for i, lid in enumerate(lids):
            x = (i - (n - 1) / 2) * (w + 0.04)
            cube(body, (w, w, h), (x, 0, h / 2), p.styled("M_RobotDark", ["M_RobotDark", "M_Wall", "M_Metal"]),
                 bevel=0.02)
            cube(a.part("Lights") if lid.startswith("M_Glow") else body, (w + 0.02, w + 0.02, 0.05),
                 (x, 0, h + 0.025), lid, bevel=0.01)
            cube(body, (w * 0.5, 0.02, 0.06), (x, -w / 2 - 0.005, h * 0.75), "M_Platform")  # label
        return
    mat = "M_Warning" if style == "hazard" else p.material(["M_Metal", "M_Wall", "M_RobotDark", "M_HazardOrange"])
    r = h * rng.uniform(0.28, 0.36)
    if style == "round":
        cyl(body, r * 0.9, h, (0, 0, h / 2), mat, sides=10, radius_top=r, bevel=0.01)
        cyl(body, r * 1.04, 0.05, (0, 0, h - 0.025), "M_RobotDark", sides=10)
    else:
        cube(body, (2 * r, 2 * r, h), (0, 0, h / 2), mat, bevel=0.02)
        cube(body, (2 * r + 0.03, 2 * r + 0.03, 0.05), (0, 0, h - 0.025), "M_RobotDark")
    if style == "hazard":  # black band and a symbol
        cube(body, (2 * r + 0.01, 2 * r + 0.01, h * 0.12), (0, 0, h * 0.35), "M_RobotDark")
        cube(body, (r * 0.7, 0.01, r * 0.7), (0, -r - 0.006, h * 0.65), "M_RobotDark", rot=(0, deg(45), 0))
    lid_mat = "M_RobotDark" if style != "hazard" else "M_Warning"
    if is_open:  # lid hinged at the back, standing up
        cube(body, (2 * r, 0.04, 2 * r), (0, r + 0.02, h + r), lid_mat, bevel=0.01, rot=(deg(-15), 0, 0))
        for _ in range(rng.randint(2, 4)):  # trash sticking out
            pos = (rng.uniform(-r, r) * 0.5, rng.uniform(-r, r) * 0.5, h)
            mat = rng.choice(["M_PortalPanel", "M_Ground", "M_HazardOrange"])
            cube(body, (r * 0.4, r * 0.3, r * 0.3), pos, mat, rot=(rng.uniform(0, 1), rng.uniform(0, 1), 0))
    else:
        if style == "round":
            cyl(body, r * 1.02, 0.06, (0, 0, h + 0.03), lid_mat, sides=10, radius_top=r * 0.6)
        else:
            cube(body, (2 * r, 2 * r, 0.05), (0, 0, h + 0.025), lid_mat, bevel=0.01)
    if p.bool("trash", 0.35):
        for _ in range(rng.randint(2, 4)):
            ang = rng.uniform(0, 2 * math.pi)
            dist = r * rng.uniform(1.3, 1.9)
            s = r * rng.uniform(0.25, 0.45)
            cube(body, (s, s * 0.8, s * 0.6), (math.cos(ang) * dist, math.sin(ang) * dist, s * 0.3),
                 rng.choice(["M_PortalPanel", "M_Ground", "M_Wall", "M_HazardOrange"]),
                 rot=(deg(rng.uniform(-20, 20)), deg(rng.uniform(-20, 20)), rng.uniform(0, math.pi)))


@model("toolbox", "Toolbox", "props", "Toolbox: carry case, roller chest with drawers or an open box with tools",
       params=[
           Param("style", "choice", "Art", choices=("case", "chest", "open")),
           Param("width", "float", "Breite (m)", lo=0.3, hi=1.2, size=True),
       ])
def toolbox(rng, a):
    p = a.p
    style = p.choice("style", ["case", "chest", "open"])
    w = p.float("width", 0.45, 0.8)
    mat = p.material(["M_HazardOrange", "M_Warning", "M_RobotDark", "M_Wall"])
    body = a.part("Body")
    a.meta["style"] = style
    if style == "chest":
        d, h = w * 0.5, w * rng.uniform(0.9, 1.3)
        cube(body, (w, d, h), (0, 0, 0.08 + h / 2), mat, bevel=0.02)
        n = rng.randint(3, 6)
        for k in range(n):
            z = 0.08 + h * 0.08 + k * h * 0.84 / n
            cube(body, (w - 0.06, 0.02, h * 0.84 / n - 0.03), (0, -d / 2 - 0.005, z + h * 0.42 / n), "M_RobotDark")
            cube(body, (w * 0.5, 0.03, 0.02), (0, -d / 2 - 0.02, z + h * 0.42 / n + 0.02), "M_Metal")
        for sx in (-1, 1):
            for sy in (-1, 1):
                cyl(body, 0.04, 0.03, (sx * (w / 2 - 0.06), sy * (d / 2 - 0.06), 0.04), "M_RobotDark", sides=8,
                    rot=ALONG_Y)
        cube(body, (w + 0.02, d + 0.02, 0.04), (0, 0, 0.1 + h), "M_RobotDark", bevel=0.01)
        return
    d, h = w * 0.42, w * 0.38
    cube(body, (w, d, h), (0, 0, h / 2), mat, bevel=0.015)
    cube(body, (w + 0.01, d + 0.01, 0.03), (0, 0, h * 0.75), "M_RobotDark")
    for sx in (-1, 1):  # latches
        cube(body, (0.05, 0.02, 0.06), (sx * w * 0.3, -d / 2 - 0.01, h * 0.75), "M_Metal")
    if style == "case":
        for sx in (-1, 1):
            cube(body, (0.03, 0.03, 0.08), (sx * w * 0.2, 0, h + 0.04), "M_RobotDark")
        cube(body, (w * 0.45, 0.04, 0.03), (0, 0, h + 0.08), "M_RobotDark")
    else:  # open: lid folded back, tray with tools
        cube(body, (w, 0.03, d), (0, d / 2 + 0.02, h + d / 2 - 0.02), mat, bevel=0.01, rot=(deg(-10), 0, 0))
        cube(body, (w - 0.04, d - 0.04, 0.02), (0, 0, h - 0.02), "M_RobotDark")
        for k in range(rng.randint(2, 4)):  # tool handles sticking out
            x = -w * 0.35 + k * w * 0.22
            y = rng.uniform(-d, d) * 0.2
            mat = rng.choice(["M_HazardOrange", "M_Metal", "M_Warning"])
            cube(body, (0.04, 0.03, 0.12), (x, y, h + 0.03), mat,
                 rot=(deg(rng.uniform(-30, 30)), deg(rng.uniform(-20, 20)), 0))
