"""Props: crates, canisters, inventory items and debris."""

from __future__ import annotations

import math

from ..params import Param
from .common import ALONG_X, cube, cyl, deg, item_pickup, pickup_params
from .registry import model


@model("crate", "Crate", "props", "Sci-fi crate: panels, rims or corner posts, warning paint, glow strips", params=[
    Param("width", "float", "Breite (m)", lo=0.3, hi=3.0, size=True),
    Param("height", "float", "Höhe (m)", lo=0.2, hi=3.0, size=True),
    Param("style", "choice", "Stil", choices=("panels", "rims", "posts")),
    Param("stripes", "bool", "Warnstreifen vorne"),
    Param("hatch", "bool", "Orange Deckelluke"),
    Param("glow_pattern", "choice", "Glow-Muster", choices=("strips", "line")),
    Param("depth", "float", "Tiefe (m)", lo=0.2, hi=3.0),
], set_faces=("x-", "x+", "y+", "z-"), set_pins=("style", "glow_pattern"))  # a row of crates: same box
def crate(rng, a):
    p = a.p
    w = p.float("width", 0.8, 1.4)
    d = p.value("depth", w * rng.choice([1.0, 1.0, rng.uniform(0.7, 1.0)]))
    h = p.value("height", w * rng.uniform(0.6, 1.0))
    body_mat = p.material(["M_RobotDark", "M_Wall", "M_Metal"])
    trim = "M_Metal" if body_mat == "M_RobotDark" else "M_RobotDark"
    panel = rng.choice([m for m in ("M_Platform", "M_Wall", "M_RobotBody", "M_Metal") if m != body_mat])
    style = p.choice("style", ["panels", "rims", "posts"])
    glow = p.glow()
    a.meta["style"] = style
    body, lights = a.part("Body"), a.part("Glow")

    cube(body, (w, d, h), (0, 0, h / 2), body_mat, bevel=0.04)
    inset = min(w, h) * 0.12
    out = 0.0  # how far the decoration sticks out of the body
    if style == "panels":
        t = 0.03
        for s in (-1, 1):
            cube(body, (w - 2 * inset, t, h - 2 * inset), (0, s * d / 2, h / 2), panel, bevel=0.01)
            cube(body, (t, d - 2 * inset, h - 2 * inset), (s * w / 2, 0, h / 2), panel, bevel=0.01)
        cube(body, (w - 2 * inset, d - 2 * inset, t), (0, 0, h), panel, bevel=0.01)
        out = t / 2
    elif style == "rims":
        rh = h * 0.12
        for z in (rh / 2, h - rh / 2 + 0.01):  # top rim 1 cm proud: no shared plane with the lid
            cube(body, (w + 0.04, d + 0.04, rh), (0, 0, z), trim, bevel=0.01)
        out = 0.02
    else:
        t = min(w, d) * 0.12
        for x in (-1, 1):
            for y in (-1, 1):
                cube(body, (t, t, h + 0.02), (x * (w / 2 - t / 2 + 0.01), y * (d / 2 - t / 2 + 0.01), h / 2 + 0.01),
                     trim, bevel=0.01)
        out = 0.01

    if p.bool("stripes", 0.45, warning=True):  # warning stripes on the front
        n = rng.randint(3, 6)
        span = w * 0.6
        for i in range(n):
            x = -span / 2 + span * (i + 0.5) / n
            cube(body, (span / n * 0.45, 0.02, h * 0.18), (x, -d / 2 - out - 0.01, h * 0.3), "M_Warning",
                 rot=(0, deg(30), 0))
        a.meta["stripes"] = n
    if p.bool("hatch", 0.35, warning=True):
        cube(body, (w * 0.4, d * 0.4, 0.04), (0, 0, h + out + 0.02), "M_HazardOrange", bevel=0.01)

    gy = d / 2 + out + 0.01
    if p.value("glow_pattern", "strips" if rng.random() < 0.5 else "line") == "strips":
        for s in (-1, 1):  # vertical strips front and back
            for x in (-w * 0.3, w * 0.3):
                cube(lights, (0.04, 0.02, h * 0.5), (x, s * gy, h / 2), glow)
    else:  # one line around the crate
        z = h * rng.uniform(0.55, 0.75)
        for s in (-1, 1):
            cube(lights, (w * 0.7, 0.02, 0.04), (0, s * gy, z), glow)
            cube(lights, (0.02, d * 0.7, 0.04), (s * (w / 2 + out + 0.01), 0, z), glow)


@model("canister", "Canister", "props", "Canister / barrel: bands, cap, handle, warning band, glow window", params=[
    Param("radius", "float", "Radius (m)", lo=0.1, hi=1.0, size=True, snap_factor=2),
    Param("height", "float", "Höhe (m)", lo=0.3, hi=3.0, size=True),
    Param("sides", "choice", "Seiten", choices=(8, 10, 12)),
    Param("warning_band", "bool", "Warnband"),
    Param("handle", "bool", "Tragegriff"),
    Param("glow_style", "choice", "Glow", choices=("window", "ring")),
])
def canister(rng, a):
    p = a.p
    r = p.float("radius", 0.2, 0.35)
    h = p.float("height", 0.6, 1.1)
    sides = p.choice("sides", [8, 10, 12])
    mat = p.material(["M_Wall", "M_Metal", "M_RobotBody", "M_HazardOrange"])
    glow = p.glow()
    body, lights = a.part("Body"), a.part("Glow")
    apothem = r * math.cos(math.pi / sides)

    cyl(body, r, h, (0, 0, h / 2), mat, sides=sides, bevel=0.02)
    bands = rng.choice([(0.15, 0.85), (0.12, 0.5, 0.88), (0.1, 0.9)])
    for f in bands:
        cyl(body, r * 1.07, 0.06, (0, 0, h * f), "M_RobotDark", sides=sides)
    cyl(body, r * 0.7, 0.05, (0, 0, h + 0.025), "M_RobotDark", sides=sides)
    if p.bool("warning_band", 0.4, warning=True):
        cyl(body, r * 1.02, h * 0.12, (0, 0, h * 0.3), "M_Warning", sides=sides)
    if p.bool("handle", 0.5):  # carry handle
        for x in (-r * 0.45, r * 0.45):
            cube(body, (0.03, 0.03, 0.12), (x, 0, h + 0.1), "M_Metal")
        cube(body, (r * 0.9 + 0.03, 0.04, 0.03), (0, 0, h + 0.16), "M_Metal")
        a.meta["handle"] = True
    if p.value("glow_style", "window" if rng.random() < 0.5 else "ring") == "window":
        cube(lights, (0.05, 0.02, h * 0.45), (0, -apothem * 1.02 - 0.01, h / 2), glow)
    else:
        cyl(lights, r * 1.03, 0.05, (0, 0, h * rng.uniform(0.6, 0.7)), glow, sides=sides)


@model("item", "Item", "props", "Inventory item: energy cell, battery, data chip or fuse (pivot in the centre)",
       pivot="center", params=[
           Param("kind", "choice", "Art", choices=("energy_cell", "battery", "data_chip", "fuse")),
           *pickup_params(),
       ])
def item(rng, a):
    p = a.p
    kind = p.choice("kind", ["energy_cell", "battery", "data_chip", "fuse"])
    glow = p.glow(weights=(0.75, 0.05, 0.2))
    body, lights = a.part("Body"), a.part("Glow")
    a.meta["kind"] = kind
    if kind == "energy_cell":
        r = rng.uniform(0.08, 0.13)
        h = rng.uniform(0.28, 0.42)
        sides = rng.choice([6, 8])
        cyl(lights, r, h, (0, 0, 0), glow, sides=sides)
        for z in (-h / 2 - 0.02, h / 2 + 0.02):
            cyl(body, r * 1.35, 0.08, (0, 0, z), "M_RobotDark", sides=sides, bevel=0.015)
        n = rng.choice([3, 4, 6])
        for i in range(n):
            ang = 2 * math.pi * i / n + math.pi / n
            cube(body, (0.035, 0.035, h), (math.cos(ang) * r * 1.12, math.sin(ang) * r * 1.12, 0), "M_Wall")
        cyl(body, r * 0.45, 0.05, (0, 0, h / 2 + 0.085), "M_Platform", sides=6)
    elif kind == "battery":
        w, d, h = rng.uniform(0.28, 0.4), rng.uniform(0.16, 0.22), rng.uniform(0.2, 0.28)
        cube(body, (w, d, h), (0, 0, 0), p.material(["M_Wall", "M_RobotBody"]), bevel=0.02)
        for x in (-w / 2, w / 2):
            cube(body, (0.04, d + 0.02, h + 0.02), (x, 0, 0), "M_HazardOrange", bevel=0.01)
        cube(lights, (w * 0.6, 0.02, h * 0.2), (0, -d / 2 - 0.005, h * 0.12), glow)
        for x in (-w * 0.2, w * 0.2):
            cyl(body, 0.025, 0.05, (x, 0, h / 2 + 0.02), "M_Platform", sides=6)
        cube(body, (w * 0.45, 0.04, 0.03), (0, 0, h / 2 + 0.04), "M_RobotDark", bevel=0.01)
    elif kind == "data_chip":
        w, h = rng.uniform(0.3, 0.45), rng.uniform(0.2, 0.3)
        cube(body, (w, 0.03, h), (0, 0, 0), "M_Platform", bevel=0.012)
        cube(body, (w, 0.034, h * 0.2), (0, 0, h * 0.3), rng.choice(["M_HazardOrange", "M_Warning", "M_RobotDark"]))
        cube(lights, (w * 0.22, 0.036, h * 0.28), (-w * 0.25, 0, -h * 0.12), glow)
        for i in range(rng.randint(2, 4)):
            cube(body, (w * 0.35, 0.036, 0.018), (w * 0.18, 0, -h * 0.05 - i * 0.04), "M_RobotDark")
    else:
        r = rng.uniform(0.05, 0.08)
        length = rng.uniform(0.25, 0.4)
        cyl(lights, r * 0.8, length * 0.6, (0, 0, 0), glow, sides=8, rot=ALONG_X)
        for x in (-length / 2 + 0.03, length / 2 - 0.03):
            cyl(body, r, 0.06, (x, 0, 0), "M_Metal", sides=8, bevel=0.01, rot=ALONG_X)
        cube(body, (length * 0.3, r * 0.6, 0.02), (0, 0, r * 0.85), "M_RobotDark")
    # floats and turns around world up while lying in the level (pivot in the centre)
    item_pickup(a, ["Body", "Glow"])


@model("debris", "Debris", "props", "Pile of broken wall chunks, plates and a torn cable", params=[
    Param("radius", "float", "Radius (m)", lo=0.2, hi=3.0, size=True, snap_factor=2),
    Param("chunks", "int", "Brocken", lo=1, hi=20),
    Param("plate", "bool", "Lose Platte"),
    Param("cable", "bool", "Abgerissenes Kabel"),
])
def debris(rng, a):
    p = a.p
    m = a.part("Debris")
    radius = p.float("radius", 0.5, 1.4)
    for _ in range(p.int("chunks", 4, 9)):
        s = rng.uniform(0.15, 0.55) * radius
        ang = rng.uniform(0, 2 * math.pi)
        dist = rng.uniform(0, radius * 0.7)
        sx, sy, sz = s * rng.uniform(0.7, 1.4), s * rng.uniform(0.6, 1.2), s * rng.uniform(0.4, 0.9)
        cube(m, (sx, sy, sz), (math.cos(ang) * dist, math.sin(ang) * dist, sz * 0.3),
             p.material(["M_Wall", "M_Ground", "M_RobotDark", "M_Wall"]),
             rot=(deg(rng.uniform(-20, 20)), deg(rng.uniform(-20, 20)), rng.uniform(0, 2 * math.pi)))
    if p.bool("plate", 0.6):  # a loose plate leaning on the pile
        cube(m, (radius * 0.7, radius * 0.5, 0.04), (radius * 0.2, -radius * 0.2, radius * 0.15), "M_Platform",
             rot=(0, deg(-20), rng.uniform(0, 2 * math.pi)))
    if p.bool("cable", 0.5):  # a torn cable
        cube(m, (0.05, 0.05, radius), (-radius * 0.3, 0.1, radius * 0.4), "M_HazardOrange",
             rot=(deg(rng.uniform(20, 50)), deg(rng.uniform(-30, 30)), 0))
