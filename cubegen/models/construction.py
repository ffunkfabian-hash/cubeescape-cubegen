"""Building kit additions: spiral stairs, railing segments and a cage with a door.

All of them carry explicit colliders (``Asset.collider``): spiral stairs as one
slab per step plus an outer fence, railings as a thin wall, the cage as bar
walls and a door that swings with its ``Panel``.
"""

from __future__ import annotations

import math

from ..params import Param
from .common import cube, cyl, strut
from .registry import model


# --------------------------------------------------------------------------
# spiral stairs
# --------------------------------------------------------------------------

@model("spiral_stairs", "SpiralStairs", "environment", "Spiral staircase around a central pole: wedge steps, "
       "outer handrail, landing at the top (turns counter-clockwise, starts at the front)", params=[
           Param("radius", "float", "Radius (m)", lo=0.7, hi=2.0, size=True),
           Param("rise", "float", "Höhe (m)", lo=1.5, hi=5.0, size=True),
           Param("turn", "choice", "Drehung (°)", choices=(270, 360, 450)),
           Param("rail", "bool", "Handlauf außen"),
           Param("glow", "bool", "Glow-Kanten"),
       ])
def spiral_stairs(rng, a):
    p = a.p
    r = p.float("radius", 0.9, 1.4)
    rise = p.float("rise", 2.5, 3.5)
    turn = math.radians(p.choice("turn", [270, 360, 360, 450]))
    mat = p.material(["M_Metal", "M_Platform", "M_RobotDark"])
    body = a.part("Body")
    steps = max(6, int(round(rise / 0.2)))
    sh, da = rise / steps, turn / steps
    start = -math.pi / 2  # first step points to the front (-Y)
    pole = 0.09
    cyl(body, pole, rise + 1.0, (0, 0, (rise + 1.0) / 2), "M_RobotDark", sides=8)
    cyl(body, pole * 2.2, 0.06, (0, 0, 0.03), "M_RobotDark", sides=8)
    a.collider((pole * 2, pole * 2, rise + 1.0), (0, 0, (rise + 1.0) / 2))
    glow = p.glow() if p.bool("glow", 0.4) else None
    lights = a.part("Glow") if glow else None
    length = r - pole * 0.5
    rc = pole * 0.5 + length / 2
    width = r * da * 1.08  # tangential width at the outer edge (slight overlap)
    t = 0.06
    posts = []
    for i in range(steps):
        ang = start + i * da
        top = sh * (i + 1)
        c, s = math.cos(ang), math.sin(ang)
        cube(body, (length, width, t), (c * rc, s * rc, top - t / 2), "M_RobotDark" if i % 2 else mat,
             rot=(0, 0, ang))
        cube(body, (length * 0.9, 0.02, 0.012), (c * rc - s * width * 0.45, s * rc + c * width * 0.45, top + 0.006),
             "M_Metal", rot=(0, 0, ang))  # nosing on the leading edge
        a.collider((length, width, t), (c * rc, s * rc, top - t / 2), rot=(0, 0, ang))
        if lights:
            cube(lights, (0.03, 0.03, 0.02), (c * (r - 0.05), s * (r - 0.05), top + 0.005), glow)
        posts.append((c * (r - 0.03), s * (r - 0.03), top))
    # landing: a wider slab after the last step
    ang = start + steps * da
    c, s = math.cos(ang), math.sin(ang)
    land = r * 0.9
    cube(body, (length, land, t), (c * rc - s * land * 0.4, s * rc + c * land * 0.4, rise - t / 2), mat,
         rot=(0, 0, ang))
    a.collider((length, land, t), (c * rc - s * land * 0.4, s * rc + c * land * 0.4, rise - t / 2), rot=(0, 0, ang))
    if p.bool("rail", 0.8):
        for i, (x, y, z) in enumerate(posts):
            cube(body, (0.04, 0.04, 1.0), (x, y, z + 0.5), "M_Metal")
            ang = start + i * da
            a.collider((0.06, width, 1.0), (x, y, z + 0.5), rot=(0, 0, ang))  # fence on the open side
            if i:
                px, py, pz = posts[i - 1]
                strut(body, (px, py, pz + 1.0), (x, y, z + 1.0), 0.025, "M_Metal", sides=6)
    a.meta.update({"steps": steps, "turn_deg": round(math.degrees(turn)), "radius_m": round(r, 3)})


# --------------------------------------------------------------------------
# railing
# --------------------------------------------------------------------------

@model("railing", "Railing", "environment", "Railing segment along X (1, 2 or 4 m): bars, mesh panel or glass, "
       "kick plate, optional glow line", params=[
           Param("length", "choice", "Länge (m)", choices=(1.0, 2.0, 4.0)),
           Param("height", "float", "Höhe (m)", lo=0.8, hi=1.4),
           Param("style", "choice", "Füllung", choices=("bars", "rails", "glass")),
           Param("kick", "bool", "Fußleiste"),
           Param("glow", "bool", "Glow-Linie oben"),
       ])
def railing(rng, a):
    p = a.p
    length = p.choice("length", [1.0, 2.0, 2.0, 4.0])
    h = p.float("height", 1.0, 1.15)
    style = p.choice("style", ["bars", "rails", "glass"])
    mat = p.material(["M_Metal", "M_HazardOrange", "M_RobotDark", "M_Warning"])
    body = a.part("Body")
    a.meta.update({"length_m": length, "style": style})
    posts = max(2, int(round(length)) + 1)
    for i in range(posts):
        x = -length / 2 + 0.03 + (length - 0.06) * i / (posts - 1)
        cube(body, (0.06, 0.06, h), (x, 0, h / 2), mat, bevel=0.008)
        cube(body, (0.12, 0.12, 0.02), (x, 0, 0.01), "M_RobotDark")  # foot plate
    cube(body, (length, 0.07, 0.05), (0, 0, h), mat, bevel=0.01)
    if style == "bars":
        n = int(length / 0.12)
        for i in range(1, n):
            cube(body, (0.02, 0.02, h - 0.15), (-length / 2 + i * length / n, 0, (h - 0.15) / 2 + 0.12), "M_Metal")
    elif style == "rails":
        for z in (h * 0.35, h * 0.65):
            cube(body, (length - 0.06, 0.04, 0.04), (0, 0, z), mat)
    else:
        cube(a.part("Glass"), (length - 0.1, 0.02, h - 0.25), (0, 0, (h - 0.25) / 2 + 0.15), "M_Glass")
        cube(body, (length - 0.06, 0.04, 0.03), (0, 0, 0.14), "M_RobotDark")
    if p.bool("kick", 0.5):
        cube(body, (length - 0.06, 0.03, 0.12), (0, 0, 0.06), "M_RobotDark")
    if p.bool("glow", 0.3):
        cube(a.part("Glow"), (length * 0.95, 0.02, 0.02), (0, -0.036, h - 0.01), p.glow())
    a.collider((length, 0.1, h + 0.03), (0, 0, (h + 0.03) / 2))


# --------------------------------------------------------------------------
# cage
# --------------------------------------------------------------------------

@model("cage", "Cage", "environment", "Bar cage on a floor plate: three barred walls, roof bars and a door (Panel, "
       "Rotatable) with a lock light", params=[
           Param("width", "float", "Breite (m)", lo=0.8, hi=3.0, size=True),
           Param("depth", "float", "Tiefe (m)", lo=0.8, hi=3.0, size=True),
           Param("height", "float", "Höhe (m)", lo=1.2, hi=3.0, size=True),
           Param("door_angle", "float", "Tür-Winkel offen (°)", lo=30, hi=170, unity=True, default=100),
           Param("status", "choice", "Glow-Startzustand", choices=("off", "on"), default="off",
                 description="Schloss-Licht beim Export: off = M_GlowRed, on = M_GlowCyan"),
       ])
def cage(rng, a):
    p = a.p
    w = p.float("width", 1.2, 2.0)
    d = p.float("depth", 1.2, 2.0)
    h = p.float("height", 2.0, 2.6)
    mat = p.material(["M_Metal", "M_RobotDark", "M_HazardOrange"])
    body = a.part("Body")
    gap = rng.uniform(0.12, 0.18)
    bar = 0.025
    cube(body, (w + 0.1, d + 0.1, 0.06), (0, 0, 0.03), "M_RobotDark", bevel=0.01)
    for sx in (-1, 1):  # corner posts
        for sy in (-1, 1):
            cube(body, (0.06, 0.06, h), (sx * w / 2, sy * d / 2, h / 2), mat, bevel=0.01)
    for sy in (-1, 1):  # top frame
        cube(body, (w, 0.05, 0.05), (0, sy * d / 2, h), mat)
    for sx in (-1, 1):
        cube(body, (0.05, d, 0.05), (sx * w / 2, 0, h), mat)

    def bars(along_x, offset, span):
        n = max(2, int(span / gap))
        for i in range(1, n):
            f = -span / 2 + i * span / n
            pos = (f, offset, h / 2) if along_x else (offset, f, h / 2)
            cube(body, (bar, bar, h - 0.06), pos, mat)
        size = (span, bar, 0.04) if along_x else (bar, span, 0.04)
        cube(body, size, (0, offset, h * 0.5) if along_x else (offset, 0, h * 0.5), mat)  # cross brace

    bars(True, d / 2, w)            # back
    for sx in (-1, 1):
        bars(False, sx * w / 2, d)  # sides
    for i in range(1, max(2, int(w / gap))):  # roof bars
        cube(body, (bar, d, bar), (-w / 2 + i * w / max(2, int(w / gap)), 0, h), mat)
    a.collider((w + 0.1, d + 0.1, 0.06), (0, 0, 0.03))
    a.collider((w, 0.06, h), (0, d / 2, h / 2))
    for sx in (-1, 1):
        a.collider((0.06, d, h), (sx * w / 2, 0, h / 2))
    a.collider((w, d, 0.06), (0, 0, h))
    # door in the front wall, hinged at its left edge
    dw = min(w - 0.12, rng.uniform(0.7, 0.95))
    dh = min(h - 0.1, 2.0)
    x0 = -w / 2 + 0.03
    fill = w - 0.06 - dw  # front wall next to the door
    if fill > 0.05:
        n = max(1, int(fill / gap))
        for i in range(n):
            cube(body, (bar, bar, h - 0.06), (x0 + dw + (i + 0.5) * fill / n, -d / 2, h / 2), mat)
        a.collider((fill, 0.06, h), (x0 + dw + fill / 2, -d / 2, h / 2))
    if h - dh > 0.08:
        cube(body, (dw, 0.05, 0.05), (x0 + dw / 2, -d / 2, dh + 0.03), mat)
        a.collider((dw, 0.06, h - dh), (x0 + dw / 2, -d / 2, (h + dh) / 2))
    hinge = (x0, -d / 2, 0.06)
    door = a.part("Panel", pivot=hinge)
    for z in (0.12, dh - 0.03):
        cube(door, (dw, 0.04, 0.04), (x0 + dw / 2, -d / 2, z), mat)
    cube(door, (0.04, 0.04, dh - 0.1), (x0 + dw - 0.02, -d / 2, (dh + 0.1) / 2 + 0.01), mat)
    n = max(2, int(dw / gap))
    for i in range(1, n):
        cube(door, (bar, bar, dh - 0.15), (x0 + i * dw / n, -d / 2, (dh + 0.1) / 2 + 0.01), mat)
    cube(door, (0.08, 0.06, 0.12), (x0 + dw - 0.06, -d / 2 - 0.02, 1.0), "M_RobotDark", bevel=0.01)  # lock box
    led = (x0 + dw - 0.06, -d / 2 - 0.055, 1.03)
    cube(a.part("Glow", pivot=led, parent="Panel"), (0.03, 0.02, 0.03), led,
         {"off": "M_GlowRed", "on": "M_GlowCyan"}[p.option("status")])
    a.collider((dw, 0.06, dh - 0.06), (x0 + dw / 2, -d / 2, (dh + 0.06) / 2), part="Panel")
    a.meta.update({"door_m": [round(dw, 3), round(dh, 3)]})
    a.behaviour("Rotatable", {"target": "Panel", "glow": "Glow"},
                {"axis": "up", "step": -p.option("door_angle"), "speed": 90, "target": 1, "interactive": False},
                note="door swings outwards around its hinge (left post); opened by the game when unlocked "
                     "(e.g. by a keypad / item socket signal)")
