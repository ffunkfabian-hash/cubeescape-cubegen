"""More ruins: a crashed escape pod, a burnt-out console and a collapsed catwalk.

Static decoration (Art/Models/Library/Ruins). The collapsed catwalk keeps a
walkable deck collider (it can be used as a ramp); embers glow (``Lights``).
"""

from __future__ import annotations

import math

from ..geometry import lathe
from ..params import Param
from .common import add_vec, cube, deg, rotated, strut
from .registry import model
from .ruins import CHUNK_MATS, _cable, _jitter, _mound


@model("crashed_pod", "CrashedPod", "ruins", "Crashed escape pod: dented capsule nose-down in a crater of rubble, "
       "torn-off hatch, scorch plates, smouldering embers (Lights)", params=[
           Param("length", "float", "Länge (m)", lo=1.8, hi=4.5, size=True),
           Param("embers", "bool", "Glut"),
       ])
def crashed_pod(rng, a):
    p = a.p
    ln = p.float("length", 2.4, 3.4)
    shell = p.material(["M_RobotBody", "M_Platform", "M_HazardOrange", "M_Wall"])
    r = ln * rng.uniform(0.26, 0.32)
    body = a.part("Wreck")
    rubble = a.part("Rubble")
    _mound(rng, a, rubble, ln * 0.7, ln * 0.18)
    tilt = deg(rng.uniform(25, 45))
    yaw = rng.uniform(0, 2 * math.pi)
    rot = (math.pi / 2 - tilt, 0.0, yaw)
    profile = [(0.0, 0.0), (r * 0.55, ln * 0.04), (r, ln * 0.2), (r, ln * 0.7), (r * 0.7, ln * 0.92), (0.0, ln)]
    pod = body.add(lathe(profile, 9, shell), loc=(0, 0, 0), rot=rot)
    _jitter(body, pod, rng, r * 0.06)
    lo = min(body.verts[i][2] for i in pod.vertex_indices())
    for i in pod.vertex_indices():  # nose buried: lift so the lowest point sits a little under the mound top
        x, y, z = body.verts[i]
        body.verts[i] = (x, y, z - lo + 0.05)
    axis = rotated(rot, (0, 0, 1))
    for k in range(rng.randint(3, 5)):  # scorch plates on the hull
        t = rng.uniform(0.3, 0.8)
        ang = rng.uniform(0, 2 * math.pi)
        c = add_vec(rotated(rot, (math.cos(ang) * r * 1.02, math.sin(ang) * r * 1.02, ln * t)), (0, 0, 0.05 - lo))
        cube(body, (r * 0.5, r * 0.5, 0.03), c, "M_RobotDark", rot=(rng.uniform(0, 1), rng.uniform(0, 1), ang))
    hatch = (math.cos(yaw + 2) * ln * 0.7, math.sin(yaw + 2) * ln * 0.7, 0.04)
    cube(body, (0.75, 0.06, 1.0), hatch, "M_Metal", rot=(deg(85), deg(rng.uniform(-10, 10)), rng.uniform(0, 3)))
    for _ in range(rng.randint(5, 9)):
        ang = rng.uniform(0, 2 * math.pi)
        d = ln * rng.uniform(0.3, 0.8)
        s = ln * rng.uniform(0.04, 0.09)
        cube(rubble, (s, s * 0.8, s * 0.6), (math.cos(ang) * d, math.sin(ang) * d, s * 0.25), rng.choice(CHUNK_MATS),
             rot=(deg(rng.uniform(-30, 30)), deg(rng.uniform(-30, 30)), rng.uniform(0, math.pi)))
    if p.bool("embers", 0.6):
        lights = a.part("Lights")
        for _ in range(rng.randint(3, 6)):
            ang = rng.uniform(0, 2 * math.pi)
            d = ln * rng.uniform(0.2, 0.5)
            cube(lights, (0.06, 0.06, 0.04), (math.cos(ang) * d, math.sin(ang) * d, 0.05), "M_GlowOrange",
                 rot=(0, 0, rng.uniform(0, 1)))
    a.meta.update({"length_m": round(ln, 3), "tilt_deg": round(math.degrees(tilt), 1),
                   "nose": [round(c, 3) for c in axis]})


@model("burnt_console", "BurntConsole", "ruins", "Burnt-out console: blackened desk, smashed screens, melted keys, "
       "hanging cables, a few embers (Lights)", params=[
           Param("width", "float", "Breite (m)", lo=0.6, hi=3.0, size=True),
           Param("screens", "int", "Bildschirme", lo=1, hi=3),
       ])
def burnt_console(rng, a):
    p = a.p
    w = p.float("width", 1.2, 2.0)
    n = p.int("screens", 1, 3)
    d, h = rng.uniform(0.7, 0.9), rng.uniform(0.8, 0.9)
    body = a.part("Wreck")
    cube(body, (w, d, h - 0.04), (0, 0.05, (h - 0.04) / 2), "M_RobotDark", bevel=0.03)
    top = cube(body, (w, d + 0.1, 0.08), (0, 0, h), "M_Ground")
    _jitter(body, top, rng, 0.015)
    for i in range(n):
        x = -w * 0.46 + (i + 0.5) * (w * 0.92) / n
        sw = (w * 0.92) / n - 0.06
        cube(body, (0.08, 0.12, 0.3), (x, 0.28, h + 0.15), "M_Wall")
        tilt = deg(rng.uniform(10, 40))
        frame = (x, 0.25, h + 0.55)
        cube(body, (sw, 0.06, 0.45), frame, "M_RobotDark", rot=(-tilt, deg(rng.uniform(-8, 8)), 0))
        for k in range(rng.randint(2, 4)):  # broken glass shards stuck in the frame
            off = (rng.uniform(-sw * 0.3, sw * 0.3), -0.035, rng.uniform(-0.15, 0.15))
            cube(body, (sw * rng.uniform(0.1, 0.3), 0.01, rng.uniform(0.05, 0.15)),
                 add_vec(frame, rotated((-tilt, 0, 0), off)), "M_Ground", rot=(-tilt, rng.uniform(0, 1), 0))
    for i in range(rng.randint(4, 8)):  # melted keys
        cube(body, (0.07, 0.06, rng.uniform(0.01, 0.03)), (rng.uniform(-w * 0.4, w * 0.3), -0.25 + rng.uniform(-0.05,
                                                                                                         0.05),
                                                          h + 0.05), rng.choice(["M_RobotDark", "M_Ground", "M_Wall"]),
             rot=(deg(rng.uniform(-15, 15)), 0, rng.uniform(0, 1)))
    for _ in range(rng.randint(1, 3)):  # cables hanging down the front
        x = rng.uniform(-w * 0.4, w * 0.4)
        strut(body, (x, -d / 2 + 0.02, h - 0.1), (x + rng.uniform(-0.2, 0.2), -d / 2 - 0.15, 0.03), 0.015,
              rng.choice(["M_HazardOrange", "M_RobotDark"]), sides=4)
    _cable(rng, body, (w * 0.3, d / 2 + 0.2), rng.randint(3, 5), 0.25)
    lights = a.part("Lights")
    for _ in range(rng.randint(2, 4)):
        cube(lights, (0.04, 0.04, 0.02), (rng.uniform(-w * 0.4, w * 0.4), rng.uniform(-0.3, 0.1), h + 0.05),
             "M_GlowOrange")
    a.meta.update({"screens": n})


@model("collapsed_catwalk", "CollapsedCatwalk", "ruins", "Collapsed catwalk: deck torn off one support, its end on "
       "the floor, bent rails, broken post, debris; the deck stays walkable (collider)", params=[
           Param("length", "float", "Länge (m)", lo=2.0, hi=6.0, size=True),
           Param("width", "float", "Breite (m)", lo=0.8, hi=3.0, size=True),
           Param("height", "float", "Höhe der Stütze (m)", lo=1.0, hi=3.5, size=True),
       ])
def collapsed_catwalk(rng, a):
    p = a.p
    ln = p.float("length", 3.0, 4.5)
    w = p.float("width", 1.0, 2.0)
    hs = p.float("height", 1.5, 2.6)
    body = a.part("Wreck")
    mat = p.material(["M_Metal", "M_Wall", "M_Platform"])
    run = math.sqrt(max(0.5, ln * ln - hs * hs))
    slope = math.atan2(hs, run)
    deck_c = (0.0, 0.0, hs / 2 + 0.06)
    rot = (slope, deg(rng.uniform(-6, 6)), 0.0)
    cube(body, (w, ln, 0.08), deck_c, mat, rot=rot)
    a.collider((w, ln * 0.98, 0.08), deck_c, rot=rot)
    for k in range(int(ln / 0.5)):  # grating bars on the deck
        t = (k + 0.5) / int(ln / 0.5) - 0.5
        cube(body, (w * 0.95, 0.04, 0.03), add_vec(deck_c, rotated(rot, (0, t * ln, 0.05))), "M_RobotDark", rot=rot)
    top_end = add_vec(deck_c, rotated(rot, (0, ln / 2, 0)))
    for x in (-w * 0.4, w * 0.4):  # the support that still stands
        cube(body, (0.12, 0.12, top_end[2] - 0.04), (x, top_end[1] + 0.05, (top_end[2] - 0.04) / 2), "M_RobotDark")
    for s in (-1, 1):  # bent rails
        bend = rng.uniform(0.2, 0.5)
        p0 = add_vec(deck_c, rotated(rot, (s * w / 2, -ln * 0.45, 0.9)))
        p1 = add_vec(deck_c, rotated(rot, (s * (w / 2 + bend), 0, 0.9 - bend)))
        p2 = add_vec(deck_c, rotated(rot, (s * w / 2, ln * 0.45, 0.9)))
        strut(body, p0, p1, 0.03, "M_Metal", sides=5)
        strut(body, p1, p2, 0.03, "M_Metal", sides=5)
        for t in (-0.45, 0.45):
            strut(body, add_vec(deck_c, rotated(rot, (s * w / 2, ln * t, 0.0))),
                  add_vec(deck_c, rotated(rot, (s * w / 2, ln * t, 0.9))), 0.025, "M_Metal", sides=5)
    broken = (rng.choice([-1, 1]) * w * 0.4, -run / 2 + 0.3, 0.0)  # the snapped post, lying on the floor
    cube(body, (0.12, 0.12, hs * 0.7), (broken[0] * 1.6, broken[1] - 0.4, 0.06), "M_RobotDark",
         rot=(deg(90), 0, rng.uniform(-0.5, 0.5)))
    rubble = a.part("Rubble")
    for _ in range(rng.randint(4, 8)):
        x, y = rng.uniform(-w, w), rng.uniform(-run / 2 - 0.3, -run / 4)
        s = rng.uniform(0.08, 0.2)
        cube(rubble, (s, s * 0.8, s * 0.5), (x, y, s * 0.2), rng.choice(CHUNK_MATS),
             rot=(deg(rng.uniform(-30, 30)), deg(rng.uniform(-30, 30)), rng.uniform(0, math.pi)))
    a.meta.update({"length_m": round(ln, 3), "drop_m": round(hs, 3), "slope_deg": round(math.degrees(slope), 1)})
