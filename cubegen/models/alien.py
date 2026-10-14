"""Alien growth: vines on walls, cocoons, roots breaking through walls, fungus carpets and puddles.

Static decoration (Art/Models/Library/Nature) - only the cocoon's glowing core
pulses (``SignalLight``). Like the plants, alien leaves use the game's colours:
``M_Leaf`` (``M_Crystal`` before 0.24), ``M_HazardOrange`` or ``M_Warning`` (``meta.leaves``).
"""

from __future__ import annotations

import math

from ..geometry import cylinder, lathe, prism, sphere
from ..params import Param
from .common import add_vec, cube, cyl, deg, strut
from .nature import _jitter
from .registry import model

LEAVES = ("M_Leaf", "M_HazardOrange", "M_Warning")
UPRIGHT = ((1, 0, 0), (0, 0, -1), (0, 1, 0))  # (x, z) polygon facing the front, extruded towards -y


def _wiggle(rng, start, step, count, spread, floor=0.05):
    """Points of a hanging / creeping tendril: ``count`` steps of ``step`` with sideways wiggle."""
    pts = [start]
    for _ in range(count):
        x, y, z = pts[-1]
        pts.append((x + rng.uniform(-spread, spread), y, max(floor, z + step + rng.uniform(-0.05, 0.05))))
    return pts


@model("vines", "Vines", "nature", "Alien vines creeping down a wall (back at y = +0.1): tendrils from a top "
       "bracket or a crack, leaves and glowing bulbs (Lights)", pivot="wall", params=[
           Param("width", "float", "Breite (m)", lo=0.5, hi=4.0, size=True),
           Param("length", "float", "Länge (m)", lo=0.5, hi=3.0, size=True),
           Param("tendrils", "int", "Ranken", lo=2, hi=10),
           Param("bulbs", "bool", "Leuchtknollen"),
       ])
def vines(rng, a):
    p = a.p
    w = p.float("width", 1.0, 2.5)
    ln = p.float("length", 1.2, 2.4)
    n = p.int("tendrils", 3, 7)
    top = rng.uniform(2.6, 3.0)
    leaf = p.material(list(LEAVES))
    stem = p.material(["M_RobotDark", "M_Ground"])
    plant = a.part("Vines")
    bulbs = p.bool("bulbs", 0.6)
    lights = a.part("Lights") if bulbs else None
    cube(plant, (w, 0.06, 0.12), (0, 0.06, top), stem)  # the growth's root mass along the top
    count = 0
    for i in range(n):
        x0 = -w / 2 + w * (i + 0.5) / n + rng.uniform(-0.1, 0.1)
        steps = max(2, int(ln * rng.uniform(0.6, 1.0) / 0.3))
        pts = _wiggle(rng, (x0, 0.04, top - 0.05), -0.3, steps, 0.12, floor=0.15)
        for k, (p1, p2) in enumerate(zip(pts, pts[1:])):
            strut(plant, p1, p2, 0.025 * (1 - k / (steps + 1)) + 0.008, stem, sides=5)
            if rng.random() < 0.7:  # a leaf at every joint
                ang = rng.uniform(-60, 60)
                cube(plant, (0.12, 0.012, 0.06), add_vec(p2, (0.05 * (1 if ang > 0 else -1), -0.01, 0)), leaf,
                     rot=(0, deg(ang), 0))
                count += 1
        if bulbs and rng.random() < 0.6:
            end = pts[-1]
            lights.add(sphere(0.045, 6, 3, "M_Biolume"), loc=(end[0], end[1] - 0.02, end[2] - 0.04))
    a.meta.update({"leaves": leaf, "tendrils": n, "leaf_count": count})


@model("cocoon", "Cocoon", "nature", "Alien cocoons: 1-4 egg-shaped shells on a resin base with strands and a "
       "pulsing core (Glow, SignalLight)", params=[
           Param("count", "int", "Kokons", lo=1, hi=4),
           Param("size", "float", "Größe (m)", lo=0.4, hi=2.2, size=True),
           Param("open", "bool", "Einer aufgebrochen"),
       ])
def cocoon(rng, a):
    p = a.p
    n = p.int("count", 1, 3)
    s = p.float("size", 0.8, 1.5)
    shell = p.material(["M_Ground", "M_RobotDark", "M_HazardOrange"])
    glow = p.glow_from(["M_GlowOrange", "M_GlowCyan", "M_GlowRed"])
    body, core = a.part("Shell"), a.part("Glow")
    burst = p.bool("open", 0.35)
    base = s * (0.6 + 0.3 * n)
    resin = body.add(cylinder(base / 2, 0.08, 10, shell), loc=(0, 0, 0.04))
    _jitter(body, resin, rng, 0.02, keep=lambda v: v[2] < 1e-6)
    spots = [(0.0, 0.0)] + [(math.cos(2 * math.pi * k / (n - 1)) * base * 0.28,
                             math.sin(2 * math.pi * k / (n - 1)) * base * 0.28) for k in range(n - 1)]
    for i, (x, y) in enumerate(spots[:n]):
        h = s * rng.uniform(0.7, 1.0) * (1.0 if i == 0 else 0.7)
        r = h * 0.38
        profile = [(0.0, 0.0), (r * 0.7, h * 0.08), (r, h * 0.4), (r * 0.8, h * 0.8), (r * 0.3, h * 0.97), (0.0, h)]
        egg = body.add(lathe(profile, 8, shell), loc=(x, y, 0.06), rot=(deg(rng.uniform(-8, 8)), 0, 0))
        _jitter(body, egg, rng, r * 0.06)
        if burst and i == 0:  # torn open at the front: the glowing core shows
            core.add(sphere(r * 0.75, 7, 4, glow), loc=(x, y - r * 0.35, 0.06 + h * 0.45))
            for k in range(4):  # flaps of the shell
                ang = deg(-60 + 40 * k)
                cube(body, (r * 0.4, 0.03, h * 0.3), (x + math.cos(ang) * r, y - r * 0.9, 0.06 + h * 0.75),
                     shell, rot=(deg(-30), 0, ang))
        else:
            for k in range(3):  # glowing veins on the front
                vz = 0.06 + h * (0.25 + 0.2 * k)
                cube(core, (r * 0.9, 0.02, 0.025), (x, y - r * 0.92, vz), glow, rot=(0, deg(rng.uniform(-30, 30)), 0))
        for k in range(rng.randint(1, 3)):  # strands to the floor
            ang = rng.uniform(0, 2 * math.pi)
            strut(body, (x + math.cos(ang) * r * 0.6, y + math.sin(ang) * r * 0.6, 0.06 + h * 0.5),
                  (x + math.cos(ang) * r * 1.6, y + math.sin(ang) * r * 1.6, 0.02), 0.012, shell, sides=4)
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": "Pulse"}, note="the core pulses slowly")
    a.meta.update({"count": n, "open": burst})


@model("wall_roots", "WallRoots", "nature", "Roots breaking through a wall (back at y = +0.1): cracked plate, "
       "thick roots branching out and down to the floor, broken wall chunks", pivot="wall", params=[
           Param("size", "float", "Größe (m)", lo=0.8, hi=3.0, size=True),
           Param("roots", "int", "Wurzeln", lo=2, hi=8),
           Param("glow", "bool", "Leuchtadern"),
       ])
def wall_roots(rng, a):
    p = a.p
    s = p.float("size", 1.2, 2.2)
    n = p.int("roots", 3, 6)
    root_mat = p.material(["M_Ground", "M_RobotDark", "M_HazardOrange"])
    body = a.part("Roots")
    cz = s * 0.5 + 0.4
    hole = [(math.cos(2 * math.pi * k / 9) * s * rng.uniform(0.25, 0.4), math.sin(2 * math.pi * k / 9) * s *
             rng.uniform(0.25, 0.4)) for k in range(9)]
    body.add(prism(hole, 0.05, "M_RobotDark"), loc=(0, 0.075, cz), basis=UPRIGHT)  # the dark breach
    for k in range(rng.randint(3, 6)):  # cracked wall chunks around it
        ang = rng.uniform(0, 2 * math.pi)
        d = s * rng.uniform(0.4, 0.55)
        cube(body, (s * 0.12, 0.08, s * 0.08), (math.cos(ang) * d, 0.04, cz + math.sin(ang) * d), "M_Wall",
             rot=(0, rng.uniform(0, math.pi), 0))
    veins = p.bool("glow", 0.4)
    lights = a.part("Lights") if veins else None
    for i in range(n):
        ang = math.pi * (1.1 + 0.8 * i / max(1, n - 1)) + rng.uniform(-0.15, 0.15)  # fan out sideways and down
        start = (math.cos(ang) * s * 0.1, -0.02, cz + math.sin(ang) * s * 0.1)
        mid = (math.cos(ang) * s * 0.45, -0.15 - rng.uniform(0, 0.2), max(0.3, cz + math.sin(ang) * s * 0.45))
        r0 = s * rng.uniform(0.04, 0.07)
        end = (mid[0] + math.cos(ang) * s * 0.3, mid[1] - 0.15,
               0.04 + r0 * 0.3 if rng.random() < 0.6 else max(0.2, mid[2] - 0.4))
        strut(body, start, mid, r0, root_mat, sides=6, radius_end=r0 * 0.7)
        strut(body, mid, end, r0 * 0.7, root_mat, sides=6, radius_end=r0 * 0.25)
        if rng.random() < 0.5:  # side branch
            tip = (mid[0] + rng.uniform(-0.3, 0.3), mid[1] - 0.05, mid[2] + rng.uniform(0.1, 0.4))
            strut(body, mid, tip, r0 * 0.4, root_mat, sides=5, radius_end=r0 * 0.1)
        if veins:
            cube(lights, (r0 * 0.5, 0.01, 0.12), ((start[0] + mid[0]) / 2, (start[1] + mid[1]) / 2 - r0 * 0.9,
                                                  (start[2] + mid[2]) / 2), "M_Biolume",
                 rot=(0, -math.atan2(mid[2] - start[2], mid[0] - start[0]) + math.pi / 2, 0))
    a.meta.update({"roots": n, "breach_m": round(s, 3)})


@model("fungus_carpet", "FungusCarpet", "nature", "Fungus carpet on the floor: flat irregular patches, small caps "
       "and glowing spore dots (Lights)", params=[
           Param("size", "float", "Größe (m)", lo=0.5, hi=4.0, size=True),
           Param("caps", "int", "Hüte", lo=0, hi=20),
           Param("glow", "bool", "Leuchtpunkte"),
       ])
def fungus_carpet(rng, a):
    p = a.p
    s = p.float("size", 1.0, 2.5)
    caps = p.int("caps", 4, 12)
    mat = p.material(["M_HazardOrange", "M_Leaf", "M_Warning", "M_Ground"])
    body = a.part("Fungus")
    for k in range(rng.randint(3, 6)):  # overlapping flat patches
        ang = rng.uniform(0, 2 * math.pi)
        d = s * rng.uniform(0.0, 0.3)
        r = s * rng.uniform(0.2, 0.35)
        pts = [(math.cos(2 * math.pi * j / 9) * r * rng.uniform(0.7, 1.1),
                math.sin(2 * math.pi * j / 9) * r * rng.uniform(0.7, 1.1)) for j in range(9)]
        height = 0.02 + 0.004 * k
        body.add(prism(pts, height, mat if k % 2 == 0 else "M_Ground"), loc=(math.cos(ang) * d, math.sin(ang) * d,
                                                                              height / 2))
    for _ in range(caps):
        ang, d = rng.uniform(0, 2 * math.pi), s * rng.uniform(0.05, 0.4)
        x, y = math.cos(ang) * d, math.sin(ang) * d
        h = rng.uniform(0.04, 0.15)
        cyl(body, 0.012, h, (x, y, h / 2), "M_Platform", sides=5)
        cyl(body, h * 0.5, h * 0.25, (x, y, h), mat, sides=6, radius_top=h * 0.1)
    if p.bool("glow", 0.6):
        lights = a.part("Lights")
        for _ in range(rng.randint(5, 12)):
            ang, d = rng.uniform(0, 2 * math.pi), s * rng.uniform(0.05, 0.4)
            cube(lights, (0.025, 0.025, 0.02), (math.cos(ang) * d, math.sin(ang) * d, 0.05), "M_Biolume")
    a.meta.update({"caps": caps, "colour": mat})


PUDDLES = {"water": "M_Glass", "slime": "M_Liquid", "oil": "M_RobotDark", "toxic": "M_GlowOrange"}


@model("puddle", "Puddle", "nature", "Puddle on the floor: water, glowing slime, oil or toxic sludge - a flat "
       "irregular pool with a few drops around it", params=[
           Param("kind", "choice", "Flüssigkeit", choices=tuple(PUDDLES)),
           Param("size", "float", "Größe (m)", lo=0.3, hi=4.0, size=True),
           Param("drops", "int", "Tropfen", lo=0, hi=8),
       ])
def puddle(rng, a):
    p = a.p
    kind = p.choice("kind", list(PUDDLES))
    s = p.float("size", 0.8, 2.0)
    drops = p.int("drops", 1, 5)
    pool = a.part("Fluid")
    mat = PUDDLES[kind]
    n = 14
    pts = []
    for j in range(n):
        ang = 2 * math.pi * j / n
        r = s / 2 * (0.75 + 0.25 * math.sin(ang * 2 + rng.uniform(0, 6)) * rng.uniform(0.6, 1.0))
        pts.append((math.cos(ang) * r, math.sin(ang) * r * rng.uniform(0.6, 0.9)))
    pool.add(prism(pts, 0.012, mat), loc=(0, 0, 0.006))
    for _ in range(drops):
        ang = rng.uniform(0, 2 * math.pi)
        d = s * rng.uniform(0.55, 0.8)
        r = s * rng.uniform(0.04, 0.1)
        cyl(pool, r, 0.01, (math.cos(ang) * d, math.sin(ang) * d * 0.8, 0.005), mat, sides=6)
    a.meta.update({"kind": kind, "size_m": round(s, 3)})
