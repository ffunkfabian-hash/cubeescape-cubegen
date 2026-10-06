"""More inventory items: tools, clues and spare parts (pivot in the centre, ``ItemPickup``).

Items lie in the XZ plane facing the front (-Y) like the existing ``item`` /
``keycard`` types; ``ItemPickup`` lets them float and turn in the level. The
``kind`` is written to ``meta`` so a puzzle can ask for the right piece.
"""

from __future__ import annotations

import math

from ..geometry import prism
from ..params import Param
from .common import ALONG_X, ALONG_Y, cube, cyl, deg, gear, rotated, strut, valve_wheel
from .registry import model


def _pickup(a):
    parts = [o.name for o in a.meshes()]
    a.behaviour("ItemPickup", {"model": parts}, {"spin": a.p.option("spin")},
                note="ItemPickup turns the whole model around world Y and lets it float")


def _spin_param():
    return Param("spin", "float", "Drehtempo im Level (°/s)", lo=0, hi=360, unity=True, default=45)


@model("tool", "Tool", "props", "Inventory item: wrench, crowbar, pliers or screwdriver (pivot in the centre)",
       pivot="center", params=[
           Param("kind", "choice", "Art", choices=("wrench", "crowbar", "pliers", "screwdriver")),
           Param("length", "float", "Länge (m)", lo=0.15, hi=0.9, size=True),
           _spin_param(),
       ])
def tool(rng, a):
    p = a.p
    kind = p.choice("kind", ["wrench", "crowbar", "pliers", "screwdriver"])
    length = p.float("length", *{"wrench": (0.28, 0.42), "crowbar": (0.45, 0.7), "pliers": (0.22, 0.32),
                                 "screwdriver": (0.22, 0.32)}[kind])
    glow = p.glow(weights=(0.7, 0.1, 0.2))
    grip = rng.choice(["M_HazardOrange", "M_RobotDark", "M_Warning"])
    body, lights = a.part("Body"), a.part("Glow")
    a.meta["kind"] = kind
    if kind == "wrench":
        w = length * 0.12
        cube(body, (length * 0.75, 0.025, w), (0, 0, 0), "M_Metal", bevel=0.005)
        head = (-length / 2 + w, 0, 0)  # open jaw: two prongs
        cube(body, (w * 1.2, 0.03, w * 2.4), head, "M_Metal", bevel=0.006)
        for sz in (-1, 1):
            cube(body, (w * 1.1, 0.03, w * 0.6), (head[0] - w * 1.0, 0, sz * w * 0.9), "M_Metal")
        ring = (length / 2 - w * 1.1, 0, 0)  # ring end
        cyl(body, w * 1.3, 0.03, ring, "M_Metal", sides=8, rot=ALONG_Y)
        cyl(body, w * 0.7, 0.034, ring, "M_RobotDark", sides=6, rot=ALONG_Y)
        cube(body, (length * 0.35, 0.03, w * 1.05), (length * 0.05, 0, 0), grip)
        cube(lights, (length * 0.2, 0.034, w * 0.3), (length * 0.05, 0, 0), glow)
    elif kind == "crowbar":
        r = length * 0.03
        bend = (length / 2 - length * 0.12, 0, length * 0.02)
        strut(body, (-length / 2, 0, -length * 0.05), bend, r, "M_HazardOrange", sides=6)
        hook = (length / 2, 0, length * 0.14)
        strut(body, bend, hook, r, "M_HazardOrange", sides=6)
        strut(body, hook, (length / 2 - length * 0.06, 0, length * 0.2), r * 0.9, "M_Metal", sides=6)
        for sz in (-1, 1):  # split claw at the straight end
            cube(body, (length * 0.08, r * 1.6, r * 0.8), (-length / 2 - length * 0.03, 0, -length * 0.05 + sz * r),
                 "M_Metal")
        cube(lights, (length * 0.15, r * 2.4, r * 2.4), (-length * 0.05, 0, -length * 0.02), glow,
             rot=(0, deg(-8), 0))
    elif kind == "pliers":
        pivot_x = length * 0.12
        for s in (-1, 1):  # two crossing halves
            ang = deg(8) * s
            cube(body, (length * 0.62, 0.025, length * 0.07), (pivot_x - length * 0.33, 0, s * length * 0.05), grip,
                 bevel=0.005, rot=(0, ang, 0))
            cube(body, (length * 0.32, 0.025, length * 0.05), (pivot_x + length * 0.17, 0, s * length * 0.018),
                 "M_Metal", rot=(0, -ang * 0.5, 0))
        cyl(body, length * 0.05, 0.04, (pivot_x, 0, 0), "M_Metal", sides=8, rot=ALONG_Y)
        cyl(lights, length * 0.025, 0.044, (pivot_x, 0, 0), glow, sides=8, rot=ALONG_Y)
    else:  # screwdriver
        r = length * 0.07
        hl = length * 0.42
        cyl(body, r, hl, (-length / 2 + hl / 2, 0, 0), grip, sides=6, bevel=0.006, rot=ALONG_X)
        cyl(lights, r * 1.05, hl * 0.12, (-length / 2 + hl * 0.75, 0, 0), glow, sides=6, rot=ALONG_X)
        cyl(body, r * 0.25, length - hl, (-length / 2 + hl + (length - hl) / 2, 0, 0), "M_Metal", sides=6,
            rot=ALONG_X)
        cube(body, (length * 0.05, r * 0.2, r * 0.6), (length / 2 - length * 0.02, 0, 0), "M_Metal")
    _pickup(a)


@model("clue", "Clue", "props", "Inventory item with a hint: tablet, paper note, datapad or audio log "
       "(pivot in the centre)", pivot="center", params=[
           Param("kind", "choice", "Art", choices=("tablet", "note", "datapad", "audio_log")),
           _spin_param(),
       ])
def clue(rng, a):
    p = a.p
    kind = p.choice("kind", ["tablet", "note", "datapad", "audio_log"])
    glow = p.glow(weights=(0.8, 0.05, 0.15))
    body = a.part("Body")
    a.meta["kind"] = kind
    if kind == "tablet":
        w, h = rng.uniform(0.26, 0.36), rng.uniform(0.18, 0.24)
        cube(body, (w, 0.02, h), (0, 0, 0), p.material(["M_RobotDark", "M_Wall"]), bevel=0.008)
        cube(a.part("Screen"), (w * 0.86, 0.006, h * 0.8), (0, -0.011, 0), glow)
        for i in range(rng.randint(2, 4)):  # text lines on the screen
            cube(body, (w * rng.uniform(0.3, 0.7), 0.006, 0.01), (-w * 0.1, -0.016, h * 0.25 - i * 0.035),
                 "M_RobotDark")
    elif kind == "note":
        w, h = rng.uniform(0.18, 0.24), rng.uniform(0.24, 0.32)
        fold = deg(rng.uniform(8, 20))
        for s in (-1, 1):  # sheet folded once in the middle
            cube(body, (w / 2, 0.004, h), (s * w / 4 * math.cos(fold), s * w / 4 * math.sin(fold) * 0.5, 0),
                 "M_PortalPanel", rot=(0, 0, -s * fold))
        for i in range(rng.randint(4, 7)):
            lw = w * rng.uniform(0.15, 0.38)
            pos = (-w / 4 * math.cos(fold), -w / 4 * math.sin(fold) * 0.5 - 0.004, h * 0.38 - i * h * 0.1)
            cube(body, (lw, 0.006, 0.008), pos, "M_RobotDark", rot=(0, 0, fold))
        cube(body, (0.03, 0.012, 0.05), (0, 0, h / 2 - 0.02), rng.choice(["M_HazardOrange", "M_Metal"]))  # clip
        cube(a.part("Glow"), (0.02, 0.008, 0.02), (w / 4 * math.cos(fold), w / 4 * math.sin(fold) * 0.5 - 0.004,
                                                   -h * 0.38), glow, rot=(0, 0, -fold))  # glowing code mark
    elif kind == "datapad":
        w, h = rng.uniform(0.12, 0.16), rng.uniform(0.2, 0.26)
        cube(body, (w, 0.04, h), (0, 0, 0), p.material(["M_Wall", "M_RobotBody", "M_HazardOrange"]), bevel=0.012)
        cube(a.part("Screen"), (w * 0.8, 0.006, h * 0.4), (0, -0.021, h * 0.18), glow)
        for row in range(2):
            for col in range(3):
                cube(body, (w * 0.2, 0.01, h * 0.08), (-w * 0.27 + col * w * 0.27, -0.022, -h * 0.15 - row * h * 0.13),
                     "M_RobotDark")
        cyl(body, 0.008, h * 0.4, (w * 0.35, 0, h / 2 + h * 0.2), "M_Metal", sides=6)  # antenna
    else:  # audio log: small cylinder recorder with a speaker grille
        r, h = rng.uniform(0.05, 0.07), rng.uniform(0.14, 0.2)
        cyl(body, r, h, (0, 0, 0), p.material(["M_RobotDark", "M_Wall", "M_Metal"]), sides=8, bevel=0.008)
        for i in range(3):
            cube(body, (r * 1.1, 0.01, 0.008), (0, -r * 0.95, h * 0.2 - i * 0.02), "M_Ground")
        cyl(a.part("Glow"), r * 1.04, 0.02, (0, 0, -h * 0.25), glow, sides=8)
        cube(body, (r * 0.5, 0.02, 0.02), (0, -r * 0.95, -h * 0.05), "M_HazardOrange")  # play button
    _pickup(a)


@model("spare_part", "SparePart", "props", "Inventory spare part: gear, lens, crystal shard, valve wheel or coil "
       "(pivot in the centre)", pivot="center", params=[
           Param("kind", "choice", "Art", choices=("gear", "lens", "crystal", "valve_wheel", "coil")),
           Param("size", "float", "Größe (m)", lo=0.08, hi=0.4, size=True),
           _spin_param(),
       ])
def spare_part(rng, a):
    p = a.p
    kind = p.choice("kind", ["gear", "lens", "crystal", "valve_wheel", "coil"])
    s = p.float("size", 0.12, 0.22)
    body = a.part("Body")
    a.meta.update({"kind": kind, "radius": round(s, 3)})
    if kind == "gear":  # fits the Slot of gear_puzzle (radius in meta)
        teeth = gear(body, (0, 0, 0), s, 0.05, rng.choice(["M_Metal", "M_HazardOrange", "M_Warning"]))
        cyl(a.part("Glow"), s * 0.12, 0.09, (0, 0, 0), p.glow(), sides=8, rot=ALONG_Y)
        a.meta["teeth"] = teeth
    elif kind == "lens":
        cyl(body, s, 0.05, (0, 0, 0), "M_RobotDark", sides=12, rot=ALONG_Y)
        cyl(a.part("Glow"), s * 0.8, 0.06, (0, 0, 0), rng.choice(["M_Crystal", "M_Glass"]), sides=12, rot=ALONG_Y)
        cube(body, (s * 0.3, 0.04, s * 0.25), (0, 0, s + s * 0.1), "M_Metal")  # mounting tab
    elif kind == "crystal":
        crystals = a.part("Glow")
        for k in range(rng.randint(1, 3)):
            tilt = (deg(rng.uniform(-25, 25)), deg(rng.uniform(-25, 25)), rng.uniform(0, math.pi))
            r = s * rng.uniform(0.25, 0.35) * (1.0 if k == 0 else 0.7)
            hexagon = [(math.cos(i * math.pi / 3) * r, math.sin(i * math.pi / 3) * r) for i in range(6)]
            length = s * (1.4 if k == 0 else 0.9)
            foot = ((k - 1) * s * 0.3 if k else 0.0, 0.0, -s * 0.2 * k)
            crystals.add(prism(hexagon, length, "M_Crystal"), loc=foot, rot=tilt)
            tip = rotated(tilt, (0.0, 0.0, length / 2 + s * 0.2))
            cyl(crystals, r, s * 0.4, (foot[0] + tip[0], foot[1] + tip[1], foot[2] + tip[2]), "M_Crystal", sides=6,
                radius_top=0.0, rot=tilt)
        cyl(body, s * 0.35, s * 0.25, (0, 0, -s * 0.7), "M_RobotDark", sides=6, radius_top=s * 0.25)  # holder
    elif kind == "valve_wheel":  # fits a valve stub without a wheel
        valve_wheel(body, (0.0, 0.0, 0.0), radius=s, rim=rng.choice(["M_HazardOrange", "M_Warning", "M_Metal"]))
        cyl(a.part("Glow"), 0.03, 0.14, (0, 0, 0), p.glow(), sides=6, rot=ALONG_Y)
    else:  # coil: core with windings and glowing ends
        h = s * 2
        cyl(body, s * 0.3, h, (0, 0, 0), "M_RobotDark", sides=8)
        for i in range(5):
            cyl(body, s * 0.5, h * 0.1, (0, 0, -h * 0.36 + i * h * 0.18), "M_HazardOrange", sides=8)
        glow = p.glow()
        for z in (-h / 2, h / 2):
            cyl(a.part("Glow"), s * 0.36, 0.03, (0, 0, z), glow, sides=8)
    _pickup(a)
