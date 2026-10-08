"""Traps and hazards: crusher, saw blade, steam vent and shock plate.

Wired to the game's existing scripts (``Door`` moves the crusher head,
``Rotator`` spins the blade, ``SignalLight`` makes the warning lights blink).
Damage / timing is game logic: the parts and anchor points are here.

* ``Panel`` - crusher head (``Door`` "open" = slammed down)
* ``Rotor`` - saw blade
* ``Steam`` - empty where a steam particle system sits (emits along Unity up)
"""

from __future__ import annotations

import math

from ..params import Param
from .common import ALONG_X, ALONG_Y, cube, cyl, stripes, valve_wheel
from .registry import model


def _mode_param(default):
    return Param("mode", "choice", "SignalLight-Modus", choices=("Steady", "Blink", "Pulse"), unity=True,
                 default=default)


# --------------------------------------------------------------------------
# crusher
# --------------------------------------------------------------------------

@model("crusher", "Crusher", "puzzle", "Crusher / stamping press: two posts, top beam, heavy head (Panel) that the "
       "Door script slams down onto the floor plate", params=[
           Param("width", "float", "Breite (m)", lo=0.8, hi=3.0, size=True),
           Param("height", "float", "Durchgang Höhe (m)", lo=1.4, hi=3.5, size=True),
           Param("teeth", "bool", "Zähne unten am Kopf"),
           Param("speed", "float", "Tempo (m/s)", lo=0.2, hi=20.0, unity=True, default=6.0),
       ])
def crusher(rng, a):
    p = a.p
    w = p.float("width", 1.2, 2.2)
    h = p.float("height", 2.0, 2.8)
    post, depth = rng.uniform(0.25, 0.4), rng.uniform(0.6, 1.0)
    head_h = rng.uniform(0.35, 0.6)
    frame = p.material(["M_RobotDark", "M_HazardOrange", "M_Metal"])
    top_z = h + head_h  # underside of the top beam
    for side, x in (("Left", -(w + post) / 2), ("Right", (w + post) / 2)):
        f = a.part(f"Frame_{side}")
        cube(f, (post, depth, top_z), (x, 0, top_z / 2), frame, bevel=0.03)
        cube(f, (0.06, depth * 0.5, top_z - 0.3), (x - math.copysign(post / 2, x), 0, top_z / 2), "M_RobotDark")
        for k in range(3):  # warning bands on the front
            cube(f, (post + 0.02, 0.02, 0.12), (x, -depth / 2 - 0.01, 0.3 + k * 0.25), "M_Warning")
        a.collider((post, depth, top_z), (x, 0, top_z / 2), part=f"Frame_{side}")
    beam_h = rng.uniform(0.4, 0.6)
    top = a.part("Frame_Top")
    cube(top, (w + 2 * post, depth, beam_h), (0, 0, top_z + beam_h / 2), frame, bevel=0.03)
    cyl(top, depth * 0.3, 0.3, (0, 0, top_z + beam_h + 0.15), "M_Metal", sides=8)  # hydraulic cylinder
    a.collider((w + 2 * post, depth, beam_h), (0, 0, top_z + beam_h / 2), part="Frame_Top")
    if p.style.generation >= 3:  # the hydraulic cylinder on top
        a.collider((depth * 0.6, depth * 0.6, 0.3), (0, 0, top_z + beam_h + 0.15), part="Frame_Top")
    for side, y in (("Front", -depth / 2 - 0.01), ("Back", depth / 2 + 0.01)):
        cube(a.part(f"StatusLight_{side}"), (min(1.0, w * 0.5), 0.02, 0.08), (0, y, top_z + beam_h / 2), "M_GlowRed")
    base = a.part("Base")
    cube(base, (w, depth, 0.08), (0, 0, 0.04), "M_RobotDark", bevel=0.01)
    stripes(base, w * 0.9, (0, -depth / 2 + 0.06, 0.085), count=max(3, int(w * 3)), width=0.08, height=0.01)
    a.collider((w, depth, 0.08), (0, 0, 0.04), part="Base")
    center = (0.0, 0.0, h + head_h / 2)
    head = a.part("Panel", pivot=center)
    cube(head, (w - 0.04, depth * 0.85, head_h), center, p.material(["M_Metal", "M_RobotDark", "M_Wall"]), bevel=0.03)
    for x in (-w / 2 + 0.01, w / 2 - 0.01):  # guide shoes running in the posts
        cube(head, (0.06, depth * 0.4, head_h * 0.7), (x, 0, center[2]), "M_RobotDark")
    teeth = p.bool("teeth", 0.5)
    if teeth:
        n = max(3, int(w / 0.25))
        for i in range(n):
            x = -w / 2 + 0.1 + i * (w - 0.2) / (n - 1)
            cube(head, (0.08, depth * 0.7, 0.1), (x, 0, h - 0.04), "M_Metal", rot=(0, math.pi / 4, 0))
    a.collider((w - 0.04, depth * 0.85, head_h), center, part="Panel")
    travel = round(head.bbox()[0][2] - 0.08, 4)  # lowest point of the head (teeth) lands on the floor plate
    a.meta.update({"opening_m": [round(w, 3), round(h, 3)], "travel_m": travel})
    a.behaviour("Door", {"panels": ["Panel"], "statusLights": ["StatusLight_Front", "StatusLight_Back"],
                         "upperFrame": ["Frame_Top"], "colliders": ["Frame_Left", "Frame_Right", "Frame_Top"]},
                {"openOffset": [0.0, -travel, 0.0], "speed": p.option("speed")},
                note="crusher: 'open' = head slams down onto the floor plate, 'close' = back up; "
                     "the rhythm (and damage) comes from game logic")


# --------------------------------------------------------------------------
# saw blade
# --------------------------------------------------------------------------

@model("saw_blade", "SawBlade", "puzzle", "Spinning saw blade in a floor housing (Rotor, Rotator), warning glow",
       params=[
           Param("radius", "float", "Blatt-Radius (m)", lo=0.2, hi=1.0, size=True, snap_factor=2),
           Param("length", "float", "Gehäuse-Länge (m)", lo=0.6, hi=4.0, size=True),
           Param("teeth", "int", "Zähne", lo=6, hi=24),
           Param("speed", "float", "Tempo (°/s)", lo=0, hi=2000, unity=True, default=720),
           _mode_param("Blink"),
       ])
def saw_blade(rng, a):
    p = a.p
    r = p.float("radius", 0.3, 0.6)
    length = max(p.float("length", 1.0, 2.5), r * 2.4)
    hh = r * rng.uniform(0.45, 0.6)  # housing height: the lower part of the blade is hidden
    hw = rng.uniform(0.25, 0.4)
    body, lights = a.part("Body"), a.part("Glow")
    cube(body, (length, hw, hh), (0, 0, hh / 2), p.material(["M_RobotDark", "M_Metal", "M_Wall"]), bevel=0.02)
    cube(body, (length - 0.1, 0.06, 0.02), (0, 0, hh + 0.005), "M_Ground")  # slot
    stripes(body, length * 0.9, (0, -hw / 2 - 0.005, hh * 0.5), count=max(3, int(length * 3)), width=0.01,
            height=hh * 0.3)
    warn = p.glow(weights=(0.1, 0.7, 0.2))
    for s in (-1, 1):
        cube(lights, (length * 0.85, 0.02, 0.03), (0, s * (hw / 2 + 0.01), hh - 0.04), warn)
    center = (0.0, 0.0, hh + r * 0.35)
    blade = a.part("Rotor", pivot=center)
    cyl(blade, r, 0.02, center, "M_Metal", sides=16, rot=ALONG_Y)
    cyl(blade, r * 0.25, 0.05, center, "M_RobotDark", sides=8, rot=ALONG_Y)
    n = p.int("teeth", 10, 18)
    for i in range(n):  # teeth: small tilted wedges around the rim
        ang = 2 * math.pi * i / n
        pos = (math.cos(ang) * r, 0.0, center[2] + math.sin(ang) * r)
        cube(blade, (r * 0.18, 0.022, r * 0.08), pos, "M_Metal", rot=(0, -ang + math.pi / 4, 0))
    a.collider((length, hw, hh), (0, 0, hh / 2))
    a.collider((2 * r, 0.06, r * 1.35), (0, 0, hh + r * 0.35 - r * 0.325))  # the blade's visible sweep
    a.meta.update({"radius_m": round(r, 3), "teeth": n})
    a.behaviour("Rotator", {"target": "Rotor"}, {"axis": "forward", "speed": p.option("speed")})
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")})


# --------------------------------------------------------------------------
# steam vent
# --------------------------------------------------------------------------

@model("steam_vent", "SteamVent", "puzzle", "Steam vent: floor grate or burst pipe with a nozzle, valve and "
       "warning glow; empty Steam = particle emitter (Unity up)", params=[
           Param("style", "choice", "Bauform", choices=("grate", "pipe")),
           Param("size", "float", "Größe (m)", lo=0.3, hi=1.5, size=True),
           Param("valve", "bool", "Absperrventil"),
           _mode_param("Pulse"),
       ])
def steam_vent(rng, a):
    p = a.p
    style = p.choice("style", ["grate", "pipe"])
    s = p.float("size", 0.5, 1.0)
    body, lights = a.part("Body"), a.part("Glow")
    glow = p.glow(weights=(0.2, 0.3, 0.5))
    a.meta["style"] = style
    if style == "grate":
        cube(body, (s + 0.16, s + 0.16, 0.08), (0, 0, 0.04), "M_RobotDark", bevel=0.02)
        n = max(3, int(s / 0.08))
        for i in range(n):
            cube(body, (0.03, s, 0.03), (-s / 2 + (i + 0.5) * s / n, 0, 0.085), "M_Metal")
        cube(body, (s, s, 0.02), (0, 0, 0.06), "M_Ground")
        for k in range(4):  # glow corners
            ang = math.pi / 4 + k * math.pi / 2
            d = (s / 2 + 0.04) * math.sqrt(2)
            cube(lights, (0.05, 0.05, 0.02), (math.cos(ang) * d, math.sin(ang) * d, 0.085), glow)
        nozzle = (0.0, 0.0, 0.1)
        valve_at = (s / 2 + 0.25, 0.0)
    else:
        r = s * 0.2
        z = r + 0.15
        cyl(body, r, s * 2, (0, 0, z), p.material(["M_Metal", "M_Wall"]), sides=8, rot=ALONG_X)
        for x in (-s, s):
            cyl(body, r * 1.25, 0.1, (x - math.copysign(0.05, x), 0, z), "M_RobotDark", sides=8, rot=ALONG_X)
            cube(body, (0.12, r * 2.2, z - r * 0.5), (x * 0.7, 0, (z - r * 0.5) / 2), "M_RobotDark")
        cyl(body, r * 0.5, r * 1.2, (0, 0, z + r * 1.1), "M_Metal", sides=6)  # burst nozzle on top
        cyl(lights, r * 1.08, 0.06, (s * 0.4, 0, z), glow, sides=8, rot=ALONG_X)
        nozzle = (0.0, 0.0, z + r * 1.7)
        valve_at = (-s * 0.5, -r - 0.15)
    a.empty("Steam", nozzle)
    if p.bool("valve", 0.5):
        vx, vy = valve_at
        cyl(body, 0.035, 0.6, (vx, vy, 0.3), "M_Metal", sides=6)
        center = (vx, vy, 0.62)
        valve_wheel(a.part("Wheel", pivot=center), center, radius=0.14)
        a.behaviour("Rotatable", {"target": "Wheel", "glow": "Glow"},
                    {"axis": "up", "step": 90, "speed": 180, "target": 2, "interactive": True},
                    note="closing the valve stops the steam")
        if p.style.generation >= 3:
            a.mesh_collider("Wheel", convex=True)
    if p.style.generation >= 3:
        a.mesh_collider("Body", convex=True)
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")},
                note="Steam: particle emitter along Unity up; damage zone = game logic")


# --------------------------------------------------------------------------
# shock plate
# --------------------------------------------------------------------------

@model("shock_plate", "ShockPlate", "puzzle", "Electrified floor plate: metal plate with glow grid and corner "
       "coils (SignalLight)", params=[
           Param("size", "float", "Größe (m)", lo=0.6, hi=4.0, size=True),
           Param("coils", "bool", "Spulen an den Ecken"),
           Param("stripes", "bool", "Warnrahmen"),
           _mode_param("Pulse"),
       ])
def shock_plate(rng, a):
    p = a.p
    s = p.float("size", 1.0, 2.0)
    body, lights = a.part("Body"), a.part("Glow")
    glow = p.glow(weights=(0.6, 0.1, 0.3))
    cube(body, (s, s, 0.05), (0, 0, 0.025), p.material(["M_Metal", "M_Platform", "M_RobotDark"]), bevel=0.01)
    n = max(2, int(s / 0.35))
    for i in range(1, n):  # glow grid in the plate
        t = -s / 2 + i * s / n
        cube(lights, (0.02, s * 0.92, 0.01), (t, 0, 0.052), glow)
        cube(lights, (s * 0.92, 0.02, 0.01), (0, t, 0.052), glow)
    a.collider((s, s, 0.05), (0, 0, 0.025))
    if p.bool("coils", 0.6):
        for sx in (-1, 1):
            for sy in (-1, 1):
                pos = (sx * (s / 2 + 0.08), sy * (s / 2 + 0.08))
                cyl(body, 0.06, 0.3, (pos[0], pos[1], 0.15), "M_RobotDark", sides=6)
                for k in range(3):
                    cyl(body, 0.075, 0.03, (pos[0], pos[1], 0.08 + k * 0.08), "M_HazardOrange", sides=6)
                cyl(lights, 0.04, 0.05, (pos[0], pos[1], 0.325), glow, sides=6)
                a.collider((0.15, 0.15, 0.35), (pos[0], pos[1], 0.175))
    if p.bool("stripes", 0.5, warning=True):
        for sy in (-1, 1):
            stripes(body, s, (0, sy * (s / 2 + 0.04), 0.005), count=max(3, int(s * 3)), width=0.06, height=0.01)
    a.meta["size_m"] = round(s, 3)
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")},
                note="trigger volume above Body; shock / damage = game logic")
