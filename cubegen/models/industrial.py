"""Industrial station parts: tanks, pipes, machines, generators and vents.

Moving parts are separate objects with their pivot on the axis: ``Rotor``
(turns), ``Wheel`` (valve wheel, turns around Y / Unity Z). ``Glow`` shows the
state and is recoloured by Unity.
"""

from __future__ import annotations

import math

from .common import ALONG_X, ALONG_Y, cube, cyl, deg, fan, glow_material, stripes, valve_wheel
from .registry import model


@model("tank", "Tank", "industrial", "Storage tank: rings, legs or plinth, optional ladder and top pipe")
def tank(rng, a):
    r = rng.uniform(0.5, 1.3)
    h = rng.uniform(1.4, 3.2)
    sides = rng.choice([10, 12])
    mat = rng.choice(["M_Wall", "M_Metal", "M_Wall"])
    glow = glow_material(rng)
    body, lights = a.part("Body"), a.part("Glow")
    legs = r < 0.8 and rng.random() < 0.6
    z0 = 0.4 if legs else 0.2
    a.meta["legs"] = legs

    if legs:
        for x in (-1, 1):
            for y in (-1, 1):
                cube(body, (0.08, 0.08, z0 + 0.1), (x * r * 0.65, y * r * 0.65, (z0 + 0.1) / 2), "M_RobotDark")
    else:
        cyl(body, r * 1.08, z0, (0, 0, z0 / 2), "M_RobotDark", sides=sides, bevel=0.02)
    cyl(body, r, h, (0, 0, z0 + h / 2), mat, sides=sides, bevel=0.04)
    cyl(body, r * 0.8, h * 0.08, (0, 0, z0 + h + h * 0.04), "M_RobotDark", sides=sides, radius_top=r * 0.55)
    for i in range(rng.randint(1, 3)):
        cyl(body, r * 1.03, 0.1, (0, 0, z0 + h * (0.2 + 0.3 * i)), "M_RobotDark", sides=sides)
    if rng.random() < 0.5:
        cube(body, (r * 0.9, 0.04, 0.15), (0, -r * 0.99, z0 + h * 0.62), "M_Warning")
    if h > 2.2 and rng.random() < 0.7:  # ladder at the front
        y = -r - 0.08
        for x in (-0.22, 0.22):
            cube(body, (0.05, 0.05, h), (x, y, z0 + h / 2), "M_Metal")
        for i in range(int(h / 0.3)):
            cube(body, (0.44, 0.04, 0.04), (0, y, z0 + 0.25 + i * 0.3), "M_Metal")
        a.meta["ladder"] = True
    if rng.random() < 0.5:  # outlet pipe on top
        cyl(body, 0.1, r * 1.4, (r * 0.5, 0, z0 + h + h * 0.06), "M_Metal", rot=ALONG_X)
    if rng.random() < 0.5:
        cube(lights, (0.1, 0.02, h * 0.45), (r * 0.5, -r * 0.88, z0 + h * 0.5), glow)
    else:
        cyl(lights, r * 1.04, 0.05, (0, 0, z0 + h * 0.9), glow, sides=sides)


@model("pipe", "Pipe", "industrial", "Straight pipe along X (2 or 4 m) on supports, flanges, glow rings, optional valve")
def pipe(rng, a):
    length = rng.choice([2.0, 4.0])
    r = rng.choice([0.09, 0.18, 0.18, 0.35])
    z = r + rng.uniform(0.25, 0.6)
    sides = 8 if r < 0.3 else 10
    mat = rng.choice(["M_Wall", "M_Metal"])
    glow = glow_material(rng)
    body, lights = a.part("Pipe"), a.part("Glow")
    a.meta.update({"length": length, "radius": r})

    cyl(body, r, length - 0.02, (0, 0, z), mat, sides=sides, rot=ALONG_X)  # end flanges cover the ends
    for x in (-length / 2 + 0.06, length / 2 - 0.06):
        cyl(body, r * 1.25, 0.12, (x, 0, z), "M_RobotDark", sides=sides, rot=ALONG_X)
    n_sup = 2 if length > 2 else 1
    sup_x = [-length * 0.3, length * 0.3] if n_sup == 2 else [0.0]
    valve = rng.random() < 0.4 and r < 0.3
    if valve:
        sup_x = [-length * 0.35, length * 0.35]
    for x in sup_x:
        cube(body, (max(0.12, r * 1.2), r * 2.4, z - r * 0.5), (x, 0, (z - r * 0.5) / 2), "M_RobotDark", bevel=0.02)
        cyl(body, r * 1.18, 0.1, (x, 0, z), "M_RobotDark", sides=sides, rot=ALONG_X)
    rings = rng.choice([[-0.25, 0.25], [0.0], [-0.4, 0.0, 0.4]])
    for f in rings:
        if valve and abs(f) < 0.2:
            continue
        cyl(lights, r * 1.06, 0.08, (f * length, 0, z), glow, sides=sides, rot=ALONG_X)
    if valve:
        cube(body, (r * 3, r * 2.6, r * 3), (0, 0, z), "M_RobotDark", bevel=0.03)
        cyl(body, 0.04, 0.2, (0, -r * 1.3 - 0.1, z), "M_Metal", sides=6, rot=ALONG_Y)
        center = (0, -r * 1.3 - 0.22, z)
        valve_wheel(a.part("Wheel", pivot=center), center, radius=max(0.18, r * 1.5))
        a.meta["valve"] = True


@model("machine", "Machine", "industrial", "Machine block: front screen, vents, pistons or stack, optional flywheel (Rotor)")
def machine(rng, a):
    w = rng.uniform(1.0, 2.4)
    d = rng.uniform(0.8, 1.6)
    h = rng.uniform(0.9, 1.6)
    mat = rng.choice(["M_Wall", "M_Metal", "M_Wall"])
    glow = glow_material(rng, weights=(0.5, 0.3, 0.2))
    body, lights = a.part("Body"), a.part("Glow")

    cube(body, (w + 0.1, d + 0.1, 0.15), (0, 0, 0.075), "M_RobotDark", bevel=0.02)
    cube(body, (w, d, h), (0, 0, 0.15 + h / 2), mat, bevel=0.04)
    pw = w * rng.uniform(0.4, 0.7)
    cube(body, (pw, 0.04, h * 0.45), (-w * 0.1, -d / 2 - 0.01, 0.15 + h * 0.55), "M_RobotDark")
    cube(lights, (pw * 0.8, 0.02, h * 0.2), (-w * 0.1, -d / 2 - 0.035, 0.15 + h * 0.62), glow)
    for i in range(rng.randint(1, 4)):
        cube(lights, (0.07, 0.02, 0.07), (w * 0.32 - i * 0.1, -d / 2 - 0.02, 0.15 + h * 0.3), glow)
    for i in range(rng.randint(3, 6)):  # side vents
        cube(body, (0.03, d * 0.5, 0.04), (-w / 2 - 0.01, 0, 0.15 + h * 0.3 + i * 0.08), "M_RobotDark")
    if rng.random() < 0.5:
        cube(body, (w + 0.02, 0.06, 0.12), (0, -d / 2 + 0.02, 0.15 + h * 0.9), "M_Warning")

    top = 0.15 + h
    if rng.random() < 0.5:  # pistons
        n = rng.randint(1, 2)
        for i in range(n):
            x = (i - (n - 1) / 2) * w * 0.45
            ph = rng.uniform(0.3, 0.7)
            cyl(body, 0.16, ph, (x, 0, top + ph / 2), "M_Metal", sides=8)
            cube(body, (0.45, 0.45, 0.1), (x, 0, top + ph), "M_RobotDark", bevel=0.02)
            cyl(lights, 0.17, 0.05, (x, 0, top + ph * 0.4), glow, sides=8)
        a.meta["top"] = "pistons"
    else:  # exhaust stack
        sh = rng.uniform(0.4, 0.9)
        cyl(body, 0.14, sh, (w * 0.3, d * 0.2, top + sh / 2), "M_Metal", sides=8)
        cyl(body, 0.18, 0.08, (w * 0.3, d * 0.2, top + sh), "M_RobotDark", sides=8)
        a.meta["top"] = "stack"
    if rng.random() < 0.6:  # flywheel on the right side
        fr = min(h, d) * rng.uniform(0.3, 0.45)
        center = (w / 2 + 0.08, 0, 0.15 + h * 0.5)
        rotor = a.part("Rotor", pivot=center)
        cyl(rotor, fr, 0.08, center, "M_RobotDark", sides=10, rot=ALONG_X)
        spokes = rng.choice([2, 3, 4])
        for i in range(spokes):
            cube(rotor, (0.06, 0.05, fr * 1.8), (center[0] + 0.05, 0, center[2]), "M_HazardOrange",
                 rot=(math.pi * i / spokes, 0, 0))
        a.meta["rotor"] = True


@model("generator", "Generator", "industrial", "Generator drum with glow rings, side boxes, floor pipes and a fan (Rotor)")
def generator(rng, a):
    r = rng.uniform(0.5, 1.2)
    h = rng.uniform(1.0, 2.2)
    sides = rng.choice([8, 10, 12])
    glow = glow_material(rng, weights=(0.5, 0.4, 0.1))
    body, lights = a.part("Body"), a.part("Glow")

    cyl(body, r * 1.35, 0.2, (0, 0, 0.1), "M_RobotDark", sides=8, bevel=0.03)
    cyl(body, r, h, (0, 0, 0.2 + h / 2), "M_Wall", sides=sides, bevel=0.03)
    cyl(body, r * 1.08, 0.12, (0, 0, 0.2 + h), "M_RobotDark", sides=sides)
    rings = rng.randint(1, 3)
    for i in range(rings):
        cyl(lights, r * 1.02, 0.07, (0, 0, 0.2 + h * (i + 1) / (rings + 1)), glow, sides=sides)
    cube(body, (r * 0.9, 0.35, h * 0.4), (0, -r - 0.1, 0.2 + h * 0.25), "M_RobotDark", bevel=0.03)
    cube(lights, (r * 0.6, 0.02, h * 0.1), (0, -r - 0.28, 0.2 + h * 0.3), glow)
    if rng.random() < 0.6:
        for i in range(4):
            ang = math.pi / 2 * i + math.pi / 4
            x, y = math.cos(ang) * r * 1.2, math.sin(ang) * r * 1.2
            cube(body, (0.3, 0.3, h * 0.6), (x, y, h * 0.3), "M_Metal", bevel=0.03, rot=(0, 0, ang))
        a.meta["floor_pipes"] = True
    center = (0, 0, 0.2 + h + 0.12)
    fan(a.part("Rotor", pivot=center), center, r * 0.8, rng.choice([4, 5, 6]), "M_Platform")


@model("vent", "Vent", "industrial", "Wall vent (back side on the wall at y = +0.1) with slats and an optional fan (Rotor)",
       pivot="wall")
def vent(rng, a):
    w = rng.uniform(0.6, 2.0)
    h = rng.uniform(0.6, 1.6)
    z = rng.uniform(max(h / 2 + 0.1, 0.5), 1.4)
    body = a.part("Body")
    cube(body, (w, 0.2, h), (0, 0, z), "M_RobotDark", bevel=0.02)
    has_fan = h > 0.9 and rng.random() < 0.6
    if has_fan:
        cube(body, (w - 0.12, 0.04, h - 0.12), (0, -0.1, z), "M_Wall")
        center = (0, -0.13, z)
        fan(a.part("Rotor", pivot=center), center, min(w, h) * 0.4, 5, "M_Metal", axis="y")
    else:
        n = max(2, int(h / 0.12))
        for i in range(n):
            zz = z - h / 2 + 0.1 + i * (h - 0.2) / max(1, n - 1)
            cube(body, (w - 0.12, 0.05, 0.03), (0, -0.1, zz), "M_Metal", rot=(deg(30), 0, 0))
    if rng.random() < 0.4:
        stripes(body, w * 0.8, (0, -0.1, z - h / 2 - 0.01), count=4, width=0.04, height=0.02)
    a.meta["fan"] = has_fan
