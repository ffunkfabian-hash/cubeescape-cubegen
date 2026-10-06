"""Outside and space: escape pod, solar panel, asteroid and a window with a planet behind it.

The escape pod's hatch opens with the game's ``Rotatable``; the planet window's
star lights and the solar panel's status light pulse via ``SignalLight``.
"""

from __future__ import annotations

import math

from ..geometry import cylinder, lathe, sphere
from ..params import Param
from .common import ALONG_Y, add_vec, cube, cyl, deg, rotated
from .nature import _crystal, _jitter
from .registry import model


@model("escape_pod", "EscapePod", "environment", "Escape pod on a launch cradle: capsule with porthole, thrusters, "
       "glow strips and a side hatch that swings open (Panel, Rotatable)", params=[
           Param("length", "float", "Länge (m)", lo=1.8, hi=4.5, size=True),
           Param("pose", "choice", "Lage", choices=("lying", "standing")),
           Param("speed", "float", "Luken-Tempo (°/s)", lo=10, hi=360, unity=True, default=90),
       ])
def escape_pod(rng, a):
    p = a.p
    ln = p.float("length", 2.4, 3.4)
    pose = p.choice("pose", ["lying", "lying", "standing"])
    shell = p.material(["M_RobotBody", "M_Platform", "M_HazardOrange", "M_Wall"])
    glow = p.glow()
    r = ln * rng.uniform(0.26, 0.32)
    body, lights = a.part("Body"), a.part("Glow")
    profile = [(0.0, 0.0), (r * 0.55, ln * 0.04), (r, ln * 0.2), (r, ln * 0.7), (r * 0.7, ln * 0.92), (0.0, ln)]
    if pose == "lying":  # axis along Y, nose to the front, on a cradle
        zc = r + 0.35
        rot = (math.pi / 2, 0.0, 0.0)  # +Z -> -Y: the nose (end of the profile) points to the front
        body.add(lathe(profile, 10, shell), loc=(0, ln / 2, zc), rot=rot)
        for y in (-ln * 0.25, ln * 0.25):
            cube(body, (r * 1.6, 0.25, 0.35), (0, y, 0.175), "M_RobotDark", bevel=0.02)
            cube(body, (r * 1.2, 0.2, r * 0.6), (0, y, 0.35 + r * 0.2), "M_RobotDark")

        def at(along, ang, out=0.0):
            return (math.cos(ang) * (r + out), ln / 2 - along, zc + math.sin(ang) * (r + out))
        hatch_c = at(ln * 0.45, 0.0, 0.02)
        hinge = at(ln * 0.45 + 0.4, 0.0, 0.02)
        hw, hh = 0.75, min(1.1, r * 1.4)
        lid = a.part("Panel", pivot=(hinge[0], hinge[1], hinge[2]))
        cube(lid, (0.06, hw, hh), (hatch_c[0] + 0.01, hatch_c[1], hatch_c[2]), "M_Metal", bevel=0.01)
        cube(lid, (0.02, hw * 0.4, hh * 0.3), (hatch_c[0] + 0.045, hatch_c[1], hatch_c[2] + hh * 0.15), "M_Glass")
        axis, step = "up", -100
        port = at(ln * 0.25, math.pi / 2 - 0.2, -0.02)
        cyl(body, r * 0.22, 0.08, port, "M_RobotDark", sides=8, rot=(deg(-80), 0, 0))
        cyl(body, r * 0.17, 0.1, port, "M_Glass", sides=8, rot=(deg(-80), 0, 0))
        for ang in (deg(150), deg(210)):
            cube(lights, (0.03, ln * 0.5, 0.03), at(ln * 0.5, ang, 0.01), glow, rot=(0, -ang, 0))
        tail = ln / 2 + 0.05
        for dx in (-r * 0.4, r * 0.4):
            cyl(body, r * 0.18, 0.3, (dx, tail, zc), "M_RobotDark", sides=8, radius_top=r * 0.24, rot=(-math.pi / 2, 0, 0))
    else:  # standing in a launch frame, hatch at the front
        cyl(body, r * 1.2, 0.3, (0, 0, 0.15), "M_RobotDark", sides=10)
        body.add(lathe(profile, 10, shell), loc=(0, 0, 0.3))
        for k in range(4):
            ang = math.pi / 4 + math.pi / 2 * k
            cube(body, (0.12, 0.12, ln * 0.8), (math.cos(ang) * r * 1.25, math.sin(ang) * r * 1.25, 0.3 + ln * 0.4),
                 "M_Metal")
        hz = 0.3 + ln * 0.42
        hinge = (-0.4, -r - 0.03, hz)
        hw, hh = 0.75, min(1.4, ln * 0.45)
        lid = a.part("Panel", pivot=hinge)
        cube(lid, (hw, 0.06, hh), (0, -r - 0.02, hz), "M_Metal", bevel=0.01)
        cube(lid, (hw * 0.4, 0.02, hh * 0.3), (0, -r - 0.055, hz + hh * 0.2), "M_Glass")
        axis, step = "up", 100
        for z in (0.3 + ln * 0.15, 0.3 + ln * 0.7):
            cyl(lights, r * 1.005, 0.04, (0, 0, z), glow, sides=10)
    a.behaviour("Rotatable", {"target": "Panel", "glow": "Glow"},
                {"axis": axis, "step": step, "speed": p.option("speed"), "target": 1, "interactive": True},
                note="the hatch swings open on its hinge (one step = open)")
    a.meta.update({"pose": pose, "length_m": round(ln, 3)})


@model("solar_panel", "SolarPanel", "tech", "Solar panel array on a mast or a ground frame: tilted cell grid "
       "(Array), cables, status light (Glow)", params=[
           Param("mount", "choice", "Unterbau", choices=("mast", "frame")),
           Param("size", "float", "Breite (m)", lo=1.0, hi=4.0, size=True),
           Param("tilt", "float", "Neigung (°)", lo=10, hi=60),
       ])
def solar_panel(rng, a):
    p = a.p
    mount = p.choice("mount", ["mast", "frame"])
    w = p.float("size", 1.6, 3.0)
    tilt = deg(p.float("tilt", 20, 40))
    d = w * rng.uniform(0.5, 0.65)
    body = a.part("Body")
    h = rng.uniform(1.2, 2.0) if mount == "mast" else d * math.sin(tilt) / 2 + 0.35
    if mount == "mast":
        cube(body, (0.5, 0.5, 0.15), (0, 0, 0.075), "M_RobotDark", bevel=0.02)
        cyl(body, 0.07, h - 0.15, (0, 0, 0.15 + (h - 0.15) / 2), "M_Metal", sides=8)
        cube(body, (0.3, 0.12, 0.12), (0, 0, h), "M_RobotDark")
        cube(body, (0.2, 0.15, 0.25), (0, 0.06, h * 0.5), "M_Wall")  # inverter box
    else:
        for x in (-1, 1):
            for y in (-1, 1):  # up to the underside of the array, which climbs towards +Y
                top = h + 0.08 + y * d * 0.4 * math.sin(tilt) - 0.025 / math.cos(tilt)
                cube(body, (0.06, 0.06, top), (x * w * 0.4, y * d * math.cos(tilt) * 0.4, top / 2), "M_Metal")
    rot = (tilt, 0.0, 0.0)
    array = a.part("Array")
    center = (0.0, 0.0, h + 0.08)
    cube(array, (w, d, 0.05), center, "M_Metal", rot=rot)
    cols, rows = max(2, int(w / 0.5)), max(2, int(d / 0.5))
    for i in range(cols):
        for j in range(rows):
            off = ((i + 0.5) / cols - 0.5) * w, ((j + 0.5) / rows - 0.5) * d
            cube(array, (w / cols * 0.92, d / rows * 0.92, 0.012), add_vec(center, rotated(rot, (off[0], off[1], 0.03))),
                 "M_RobotDark" if (i + j) % 2 else "M_Glass", rot=rot)
    light = (0.08, -0.08, h * 0.5) if mount == "mast" else (w * 0.4, -d * math.cos(tilt) * 0.4 - 0.04, 0.25)
    cube(a.part("Glow"), (0.04, 0.02, 0.04), light, "M_GlowCyan")  # on the mast / on the front right leg
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": "Pulse"}, note="charging indicator")
    a.meta.update({"mount": mount, "cells": cols * rows})


@model("asteroid", "Asteroid", "nature", "Floating asteroid (pivot in the centre): lumpy rock with craters, optional "
       "crystal veins and small moonlets", pivot="center", params=[
           Param("size", "float", "Größe (m)", lo=0.4, hi=5.0, size=True),
           Param("crystals", "int", "Kristalle", lo=0, hi=6),
           Param("moonlets", "int", "Brocken", lo=0, hi=4),
       ])
def asteroid(rng, a):
    p = a.p
    s = p.float("size", 1.0, 2.5)
    rock = a.part("Rock")
    mat = p.material(["M_Ground", "M_RobotDark", "M_Wall"])
    main = rock.add(sphere(1.0, 9, 6, mat), scale=(s / 2, s / 2 * rng.uniform(0.7, 0.95), s / 2 * rng.uniform(0.6, 0.9)),
                    rot=(rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0, 3)))
    _jitter(rock, main, rng, s * 0.06)
    for _ in range(rng.randint(2, 5)):  # craters: dark discs pressed onto the surface
        theta, phi = rng.uniform(0, 2 * math.pi), rng.uniform(-1.0, 1.0)
        n = (math.cos(theta) * math.cos(phi), math.sin(theta) * math.cos(phi), math.sin(phi))
        cr = s * rng.uniform(0.08, 0.16)
        c = (n[0] * s * 0.36, n[1] * s * 0.3, n[2] * s * 0.28)
        rx = math.atan2(math.hypot(n[0], n[1]), n[2])
        rz = math.atan2(n[1], n[0]) + math.pi / 2
        rock.add(cylinder(cr, s * 0.05, 8, "M_RobotDark"), loc=c, rot=(rx, 0.0, rz))
    for _ in range(p.int("moonlets", 0, 2)):
        ang = rng.uniform(0, 2 * math.pi)
        d = s * rng.uniform(0.7, 0.9)
        m = s * rng.uniform(0.1, 0.2)
        part = rock.add(sphere(m, 6, 4, mat), loc=(math.cos(ang) * d, math.sin(ang) * d, rng.uniform(-0.2, 0.2) * s))
        _jitter(rock, part, rng, m * 0.15)
    n_cr = p.int("crystals", 0, 3)
    if n_cr:
        cr = a.part("Crystals")
        for _ in range(n_cr):
            ang = rng.uniform(0, 2 * math.pi)
            tilt = (deg(-math.sin(ang) * 50), deg(math.cos(ang) * 50), 0.0)
            _crystal(cr, (math.cos(ang) * s * 0.25, math.sin(ang) * s * 0.2, s * 0.15), s * rng.uniform(0.25, 0.45),
                     s * rng.uniform(0.04, 0.07), tilt)
    a.meta["size_m"] = round(s, 3)


PLANETS = (("M_HazardOrange", "M_Warning"), ("M_Crystal", "M_Platform"), ("M_Wall", "M_Metal"),
           ("M_GlowOrange", "M_HazardOrange"))


@model("planet_window", "PlanetWindow", "environment", "Window to space on the wall (back at y = +0.1): round or "
       "wide frame, glass (Glass), a planet with optional rings and stars (Lights) behind it", pivot="wall", params=[
           Param("shape", "choice", "Form", choices=("round", "wide")),
           Param("size", "float", "Größe (m)", lo=0.6, hi=3.0, size=True),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=1.0, hi=3.0),
           Param("rings", "bool", "Planetenringe"),
       ])
def planet_window(rng, a):
    p = a.p
    shape = p.choice("shape", ["round", "wide"])
    s = p.float("size", 1.0, 1.8)
    z = p.value("mount_height", rng.uniform(1.5, 1.8))
    w, h = (s, s) if shape == "round" else (s * 1.8, s * 0.8)
    z = max(z, h / 2 + 0.2)
    depth = 0.45
    body, glass, stars = a.part("Body"), a.part("Glass"), a.part("Lights")
    frame = p.material(["M_RobotDark", "M_Metal", "M_Wall"])
    yb = 0.1  # back plate against the wall
    cube(body, (w + 0.3, 0.04, h + 0.3), (0, yb - 0.02, z), "M_RobotDark")  # space backdrop
    for s_ in (-1, 1):  # box sides
        cube(body, (0.06, depth, h + 0.3), (s_ * (w / 2 + 0.12), yb - depth / 2, z), frame)
        cube(body, (w + 0.3, depth, 0.06), (0, yb - depth / 2, z + s_ * (h / 2 + 0.12)), frame)
    yf = yb - depth
    if shape == "round":
        sides = 12
        for k in range(sides):  # porthole ring in front
            ang = 2 * math.pi * k / sides
            cube(body, (2 * math.pi * (s / 2 + 0.06) / sides * 1.1, 0.08, 0.12),
                 (math.cos(ang) * (s / 2 + 0.06), yf - 0.04, z + math.sin(ang) * (s / 2 + 0.06)), frame,
                 rot=(0, math.pi / 2 - ang, 0))
        cyl(glass, s / 2, 0.02, (0, yf + 0.02, z), "M_Glass", sides=sides, rot=ALONG_Y)
        for cx in (-1, 1):  # corner fillers between ring and box
            for cz in (-1, 1):
                cube(body, (0.18, 0.04, 0.18), (cx * (w / 2 - 0.02), yf + 0.02, z + cz * (h / 2 - 0.02)), frame)
    else:
        for zz in (-1, 1):
            cube(body, (w + 0.24, 0.1, 0.1), (0, yf - 0.03, z + zz * (h / 2 + 0.05)), frame)
        for xx in (-1, 0, 1):
            cube(body, (0.1 if xx else 0.05, 0.1, h + 0.2), (xx * (w / 2 + 0.05), yf - 0.03, z), frame)
        cube(glass, (w, 0.02, h), (0, yf + 0.02, z), "M_Glass")
    surface, band = rng.choice(PLANETS)
    pr = min(w, h) * rng.uniform(0.3, 0.42)
    pc = (rng.uniform(-w * 0.2, w * 0.2), yb - 0.1, z + rng.uniform(-h * 0.15, h * 0.1))
    planet = a.part("Planet")
    planet.add(sphere(1.0, 10, 6, surface), loc=pc, scale=(pr, 0.05, pr))
    cube(planet, (pr * 1.6, 0.02, pr * 0.15), (pc[0], pc[1] - 0.05, pc[2] + pr * 0.25), band)
    if p.bool("rings", 0.5):
        tilt = (0.0, deg(rng.uniform(-25, 25)), 0.0)
        for k in range(16):
            ang = 2 * math.pi * k / 16
            pos = add_vec(pc, rotated(tilt, (math.cos(ang) * pr * 1.5, -0.07, math.sin(ang) * pr * 0.35)))
            cube(planet, (pr * 0.3, 0.015, 0.04), pos, "M_Platform", rot=(0, tilt[1] - math.atan2(math.sin(ang) * 0.35,
                                                                                                     math.cos(ang)), 0))
    for _ in range(rng.randint(8, 16)):
        x, zz = rng.uniform(-w / 2, w / 2), rng.uniform(-h / 2, h / 2)
        if math.hypot(x - pc[0], zz - (pc[2] - z)) < pr * 1.1:
            continue
        cube(stars, (0.015, 0.01, 0.015), (x, yb - 0.045, z + zz), "M_Crystal")
    if not stars.faces:
        cube(stars, (0.015, 0.01, 0.015), (w * 0.45, yb - 0.045, z + h * 0.45), "M_Crystal")
    a.meta.update({"shape": shape, "planet": surface})
