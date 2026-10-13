"""More inventory items: tools, clues, spare parts, flashlights, keys and cable reels.

Pivot in the centre, ``ItemPickup``.

Items lie in the XZ plane facing the front (-Y) like the existing ``item`` /
``keycard`` types; ``ItemPickup`` lets them float and turn in the level. The
``kind`` is written to ``meta`` so a puzzle can ask for the right piece.
"""

from __future__ import annotations

import math

from ..geometry import prism, torus
from ..params import Param
from .common import ALONG_X, ALONG_Y, cube, cyl, deg, gear, item_pickup, pickup_params, rotated, strut, valve_wheel
from .details import tool_grip
from .registry import model


def _pickup(a):
    item_pickup(a, [o.name for o in a.meshes()])


@model("tool", "Tool", "props", "Inventory item: wrench, crowbar, pliers or screwdriver (pivot in the centre)",
       pivot="center", params=[
           Param("kind", "choice", "Art", choices=("wrench", "crowbar", "pliers", "screwdriver")),
           Param("length", "float", "Länge (m)", lo=0.15, hi=0.9, size=True),
           *pickup_params(),
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
    tool_grip(a, body, kind, length)  # variety details (own stream): grip bands, a pliers spring
    _pickup(a)


@model("clue", "Clue", "props", "Inventory item with a hint: tablet, paper note, datapad or audio log "
       "(pivot in the centre)", pivot="center", params=[
           Param("kind", "choice", "Art", choices=("tablet", "note", "datapad", "audio_log")),
           *pickup_params(),
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
           *pickup_params(),
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


@model("flashlight", "Flashlight", "props", "Inventory item: torch or lantern with a glowing lens (pivot in the "
       "centre)", pivot="center", params=[
           Param("kind", "choice", "Art", choices=("torch", "lantern")),
           Param("length", "float", "Länge (m)", lo=0.12, hi=0.45, size=True),
           *pickup_params(),
       ])
def flashlight(rng, a):
    p = a.p
    kind = p.choice("kind", ["torch", "torch", "lantern"])
    length = p.float("length", 0.18, 0.3)
    body, lights = a.part("Body"), a.part("Glow")
    case = p.material(["M_RobotDark", "M_HazardOrange", "M_Metal", "M_Warning"])
    glow = p.glow(weights=(0.5, 0.0, 0.5))
    a.meta["kind"] = kind
    if kind == "torch":  # lies along X, lens to the right
        r = length * 0.12
        cyl(body, r, length * 0.7, (-length * 0.15, 0, 0), case, sides=8, bevel=0.004, rot=ALONG_X)
        cyl(body, r * 1.5, length * 0.25, (length * 0.32, 0, 0), "M_Metal", sides=8, radius_top=r * 1.1,
            rot=(0, -math.pi / 2, 0))
        cyl(lights, r * 1.3, 0.01, (length * 0.45 + 0.004, 0, 0), glow, sides=8, rot=ALONG_X)
        for k in range(3):  # grip rings
            cyl(body, r * 1.06, 0.012, (-length * 0.4 + k * length * 0.08, 0, 0), "M_Metal", sides=8, rot=ALONG_X)
        cube(body, (length * 0.08, r * 0.6, r * 0.5), (length * 0.05, 0, r + r * 0.15), "M_GlowRed")  # switch
    else:  # lantern: standing housing, glowing window, handle on top
        w = length * 0.45
        cube(body, (w, w, length * 0.15), (0, 0, -length * 0.4), case, bevel=0.006)
        cube(body, (w, w, length * 0.1), (0, 0, length * 0.2), case, bevel=0.006)
        cyl(lights, w * 0.38, length * 0.45, (0, 0, -length * 0.1), glow, sides=8)
        for sx in (-1, 1):
            for sy in (-1, 1):
                cube(body, (0.012, 0.012, length * 0.45), (sx * w * 0.42, sy * w * 0.42, -length * 0.1), "M_Metal")
        strut(body, (-w * 0.35, 0, length * 0.25), (0, 0, length * 0.5), 0.008, "M_Metal", sides=4)
        strut(body, (0, 0, length * 0.5), (w * 0.35, 0, length * 0.25), 0.008, "M_Metal", sides=4)
    _pickup(a)


@model("key", "Key", "props", "Inventory item: mechanical key with bow, shaft and bit, optional tag (pivot in the "
       "centre)", pivot="center", params=[
           Param("style", "choice", "Art", choices=("bit", "modern", "tubular")),
           Param("length", "float", "Länge (m)", lo=0.06, hi=0.3, size=True),
           Param("tag", "bool", "Anhänger"),
           *pickup_params(),
       ])
def key(rng, a):
    p = a.p
    style = p.choice("style", ["bit", "modern", "tubular"])
    length = p.float("length", 0.09, 0.16)
    body, lights = a.part("Body"), a.part("Glow")
    metal = p.material(["M_Metal", "M_Warning", "M_HazardOrange"])
    a.meta["style"] = style
    t = 0.012
    bow = (-length / 2 + length * 0.15, 0, 0)
    if style == "modern":
        cube(body, (length * 0.32, t * 1.4, length * 0.32), bow, "M_RobotDark", bevel=0.004)
        cyl(lights, length * 0.06, t * 1.6, bow, p.glow(), sides=6, rot=ALONG_Y)
    else:
        cyl(body, length * 0.16, t, bow, metal, sides=10, rot=ALONG_Y)
        cyl(lights, length * 0.07, t * 1.1, bow, p.glow(), sides=6, rot=ALONG_Y)  # glowing gem in the bow
    shaft_x0, shaft_x1 = bow[0] + length * 0.15, length / 2
    mid = (shaft_x0 + shaft_x1) / 2
    if style == "tubular":
        cyl(body, length * 0.06, shaft_x1 - shaft_x0, (mid, 0, 0), metal, sides=8, rot=ALONG_X)
        cyl(body, length * 0.03, 0.004, (shaft_x1 + 0.002, 0, 0), "M_RobotDark", sides=6, rot=ALONG_X)
    else:
        cube(body, (shaft_x1 - shaft_x0, t, length * 0.07), (mid, 0, 0), metal)
        n = rng.randint(2, 4)
        for i in range(n):  # bit / teeth below the shaft
            depth = length * rng.uniform(0.05, 0.12)
            x = shaft_x1 - length * 0.06 - i * length * 0.08
            cube(body, (length * 0.06, t, depth), (x, 0, -length * 0.035 - depth / 2), metal)
    if p.bool("tag", 0.4):
        ring = (bow[0] - length * 0.2, 0, 0)
        strut(body, (bow[0] - length * 0.14, 0, 0), ring, 0.004, "M_Metal", sides=4)
        cube(body, (length * 0.25, 0.006, length * 0.18), (ring[0] - length * 0.12, 0, -length * 0.08),
             rng.choice(["M_HazardOrange", "M_Warning", "M_Platform"]), rot=(0, math.radians(25), 0))
    _pickup(a)


@model("cable_reel", "CableReel", "props", "Inventory item: coil of cable with a plug end, optionally on a spool "
       "(pivot in the centre)", pivot="center", params=[
           Param("radius", "float", "Radius (m)", lo=0.06, hi=0.25, size=True, snap_factor=4),
           Param("spool", "bool", "Auf Spule"),
           *pickup_params(),
       ])
def cable_reel(rng, a):
    p = a.p
    r = p.float("radius", 0.08, 0.15)
    body, lights = a.part("Body"), a.part("Glow")
    cable = rng.choice(["M_HazardOrange", "M_RobotDark", "M_Warning", "M_GlowCyan"])
    spool = p.bool("spool", 0.4)
    turns = rng.randint(3, 5)
    thick = r * 0.12
    for k in range(turns):  # stacked windings, lying in the XZ plane (facing the front)
        y = (k - (turns - 1) / 2) * thick * 1.6
        body.add(torus(r - thick * (k % 2) * 0.4, thick, 10, 4, cable), loc=(0, y, 0), rot=ALONG_Y)
    if spool:
        for s in (-1, 1):
            cyl(body, r * 1.35, 0.01, (0, s * (turns * thick * 0.8 + 0.008), 0), "M_RobotDark", sides=10, rot=ALONG_Y)
        cyl(body, r * 0.6, turns * thick * 1.6 + 0.02, (0, 0, 0), "M_Metal", sides=8, rot=ALONG_Y)
    end = (r * 0.7, 0, -r - thick)  # loose end with a plug
    strut(body, (r * 0.2, 0, -r + thick * 0.5), end, thick * 0.8, cable, sides=4)
    plug = (end[0] + 0.03, 0, end[2])
    cube(body, (0.05, 0.03, 0.03), plug, "M_RobotDark", bevel=0.004)
    cube(lights, (0.006, 0.02, 0.02), (plug[0] + 0.028, 0, plug[2]), p.glow())
    a.meta.update({"spool": spool, "cable": cable})
    _pickup(a)
