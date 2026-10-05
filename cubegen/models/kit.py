"""Modular building kit: stairs, ladders, catwalks, floor tiles, ceiling panels, wall corners, window walls,
cable trays, lifts, conveyors and jump / teleporter pads.

Sizes follow the wall module (3 m high, 0.5 m thick, 2 / 4 m long) and the
1 m floor grid. Walkable pieces (``catwalk``, ``floor_tile``) have their top at
z = 0 like the platforms.
"""

from __future__ import annotations

import math

from ..geometry import prism
from ..params import Param
from .common import ALONG_X, ALONG_Y, cube, cyl, deg, fan, rail, stripes
from .registry import model

# turns a (y, z) polygon into a prism extruded along X (local x -> world y, local y -> world z, local z -> world x)
YZ_TO_X = ((0, 0, 1), (1, 0, 0), (0, 1, 0))
STATUS = {"off": "M_GlowRed", "on": "M_GlowCyan"}


def _wall_trims(m, length, along_x=True):
    """Base and top trims of the 3 m wall module (same sizes as ``wall``)."""
    for size, z in (((length, 0.56, 0.25), 0.125), ((length, 0.60, 0.15), 2.95)):
        cube(m, size if along_x else (size[1], size[0], size[2]), (0, 0, z), "M_RobotDark", bevel=0.01)


@model("stairs", "Stairs", "environment", "Stairs or ramp climbing towards the back (+Y), optional rails and glow edges",
       params=[
           Param("style", "choice", "Bauform", choices=("stairs", "ramp")),
           Param("width", "float", "Breite (m)", lo=0.6, hi=4.0, size=True),
           Param("rise", "float", "Höhe (m)", lo=0.4, hi=3.0, size=True),
           Param("rails", "choice", "Geländer", choices=("none", "left", "both")),
           Param("glow_edges", "bool", "Glow-Kanten"),
           Param("stripes", "bool", "Warnstreifen unten"),
       ])
def stairs(rng, a):
    p = a.p
    style = p.choice("style", ["stairs", "stairs", "ramp"])
    w = p.float("width", 1.0, 2.0)
    rise = p.float("rise", 1.0, 3.0)
    mat = p.material(["M_Metal", "M_Wall", "M_Platform"])
    glow = p.glow()
    body = a.part("Body")
    steps = max(2, int(round(rise / 0.2)))
    run = steps * 0.3 if style == "stairs" else rise * 2.2
    a.meta.update({"style": style, "run_m": round(run, 3), "steps": steps if style == "stairs" else 0})
    edges = p.bool("glow_edges", 0.4)
    lights = a.part("Glow") if edges else None
    if style == "stairs":
        sh, sd = rise / steps, run / steps
        for i in range(steps):
            h = sh * (i + 1)
            y = -run / 2 + sd * (i + 0.5)
            cube(body, (w, sd, h), (0, y, h / 2), "M_RobotDark" if i % 2 else mat)
            cube(body, (w + 0.02, sd * 0.25, 0.02), (0, y - sd * 0.375, h + 0.01), "M_Metal")  # nosing
            if edges:
                cube(lights, (w * 0.8, 0.02, 0.02), (0, y - sd / 2 - 0.01, h - 0.03), glow)
    else:
        body.add(prism([(-run / 2, 0.0), (run / 2, 0.0), (run / 2, rise)], w, mat), basis=YZ_TO_X)
        slope = math.atan2(rise, run)
        for i in range(int(run / 0.4)):  # anti-slip bars on the slope
            t = (i + 0.5) * 0.4 / run
            cube(body, (w * 0.9, 0.05, 0.03), (0, -run / 2 + run * t, rise * t + 0.01), "M_RobotDark",
                 rot=(slope, 0, 0))
        if edges:
            for s in (-1, 1):
                ln = math.hypot(run, rise)
                cube(lights, (0.03, ln * 0.9, 0.02), (s * (w / 2 - 0.05), 0, rise / 2 + 0.012), glow, rot=(slope, 0, 0))
    rails = p.choice("rails", ["none", "left", "both"])
    if rails != "none":
        slope = math.atan2(rise, run)
        ln = math.hypot(run, rise)
        for s in ((-1,) if rails == "left" else (-1, 1)):
            x = s * (w / 2 + 0.05)
            for t in (0.05, 0.5, 0.95):
                y, z = -run / 2 + run * t, rise * t
                cube(body, (0.05, 0.05, 1.0), (x, y, z + 0.5), "M_Metal")
            cube(body, (0.06, ln, 0.06), (x, 0, rise / 2 + 1.0), "M_Metal", rot=(slope, 0, 0))
            cube(body, (0.04, ln, 0.04), (x, 0, rise / 2 + 0.5), "M_Metal", rot=(slope, 0, 0))
    if p.bool("stripes", 0.3, warning=True):
        stripes(body, w * 0.9, (0, -run / 2 - 0.005, 0.06), count=max(3, int(w * 3)), width=0.01, height=0.1)


@model("ladder", "Ladder", "environment", "Ladder with wall brackets at the back (+Y), optional safety cage",
       params=[
           Param("height", "float", "Höhe (m)", lo=1.0, hi=6.0, size=True),
           Param("width", "float", "Breite (m)", lo=0.3, hi=1.0),
           Param("cage", "bool", "Rückenschutz"),
           Param("hoops", "bool", "Haltebügel oben"),
       ])
def ladder(rng, a):
    p = a.p
    h = p.float("height", 2.0, 4.0)
    w = p.float("width", 0.45, 0.6)
    mat = p.material(["M_Metal", "M_Metal", "M_HazardOrange", "M_Warning"])
    body = a.part("Body")
    for x in (-w / 2, w / 2):
        cube(body, (0.05, 0.06, h), (x, 0, h / 2), mat)
        cube(body, (0.12, 0.06, 0.04), (x, 0, 0.02), "M_RobotDark")  # foot
    n = max(2, int((h - 0.2) / 0.3))
    for i in range(n):
        cyl(body, 0.02, w, (0, 0, 0.3 + i * (h - 0.3) / n), "M_Metal", sides=6, rot=ALONG_X)
    for z in [0.5 + k * 1.5 for k in range(int((h - 0.3) / 1.5) + 1)]:  # wall brackets
        for x in (-w / 2, w / 2):
            cube(body, (0.04, 0.2, 0.04), (x, 0.13, min(z, h - 0.1)), "M_RobotDark")
    if p.bool("hoops", 0.5):  # grab bars sticking up over the top
        for x in (-w / 2, w / 2):
            cube(body, (0.05, 0.06, 0.9), (x, 0, h + 0.45), mat)
        cube(body, (w + 0.05, 0.06, 0.05), (0, 0, h + 0.9), mat)
    cage = p.bool("cage", 0.4, enabled=h > 2.4)
    if cage:
        r = w / 2 + 0.25
        for z in [2.2 + k * 0.9 for k in range(int((h - 2.2) / 0.9) + 1)]:
            for i in range(7):  # half hoop (front half), made of short segments
                ang = math.pi + math.pi * i / 6
                ang2 = math.pi + math.pi * (i + 1) / 6
                mx, my = (math.cos(ang) + math.cos(ang2)) / 2 * r, (math.sin(ang) + math.sin(ang2)) / 2 * r
                if i < 6:
                    cube(body, (math.pi * r / 6 * 1.05, 0.04, 0.04), (mx, my - 0.05, z), mat,
                         rot=(0, 0, (ang + ang2) / 2 + math.pi / 2))
        for i in range(5):  # vertical bars of the cage
            ang = math.pi + math.pi * (i + 1) / 6
            cube(body, (0.03, 0.03, h - 2.2), (math.cos(ang) * r, math.sin(ang) * r - 0.05, 2.2 + (h - 2.2) / 2), mat)
    a.meta.update({"rungs": n, "cage": cage})


@model("catwalk", "Catwalk", "environment", "Catwalk / bridge segment (walkable top at z = 0): grating, rails, "
       "glow edges, optional supports", pivot="top", params=[
           Param("length", "choice", "Länge (m)", choices=(2.0, 4.0)),
           Param("width", "choice", "Breite (m)", choices=(1.0, 2.0)),
           Param("rails", "choice", "Geländer", choices=("both", "one", "none")),
           Param("supports", "float", "Stützen-Länge (m, 0 = keine)", lo=0.0, hi=4.0),
           Param("glow", "bool", "Glow-Kanten"),
       ])
def catwalk(rng, a):
    p = a.p
    length = p.choice("length", [2.0, 4.0, 4.0])
    width = p.choice("width", [1.0, 1.0, 2.0])
    deck = a.part("Deck")
    frame = p.material(["M_RobotDark", "M_Metal", "M_HazardOrange"])
    a.meta.update({"length_m": length, "width_m": width})
    for s in (-1, 1):  # side beams
        cube(deck, (length, 0.08, 0.2), (0, s * (width / 2 - 0.04), -0.1), frame, bevel=0.01)
    for x in (-length / 2 + 0.04, length / 2 - 0.04):
        cube(deck, (0.08, width - 0.16, 0.16), (x, 0, -0.08), frame)
    n = int(length / 0.12)
    for i in range(n):  # grating bars across
        cube(deck, (0.04, width - 0.16, 0.04), (-length / 2 + 0.1 + i * (length - 0.2) / (n - 1), 0, -0.03),
             "M_Metal")
    for y in (-width / 4, width / 4):
        cube(deck, (length - 0.16, 0.03, 0.08), (0, y, -0.1), "M_Metal")
    if p.bool("glow", 0.5):
        glow = p.glow()
        lights = a.part("Glow")
        for s in (-1, 1):
            cube(lights, (length * 0.9, 0.02, 0.04), (0, s * (width / 2 + 0.01), -0.08), glow)
    rails = p.choice("rails", ["both", "both", "one", "none"])
    if rails != "none":
        r = a.part("Rail")
        for s in ((-1, 1) if rails == "both" else (1,)):
            rail(r, length - 0.1, True, s * (width / 2 - 0.04))
    sup = p.value("supports", rng.choice([0.0, 0.0, rng.uniform(1.0, 3.0)]))
    if sup > 0.05:
        for x in (-length / 2 + 0.3, length / 2 - 0.3):
            for s in (-1, 1):
                cube(deck, (0.1, 0.1, sup), (x, s * (width / 2 - 0.1), -0.2 - sup / 2), "M_RobotDark")
            cube(deck, (0.08, width - 0.2, 0.08), (x, 0, -0.2 - sup * 0.6), "M_RobotDark")
        a.meta["supports_m"] = round(sup, 3)


@model("floor_tile", "FloorTile", "environment", "Floor tile on the 1 m grid (top at z = 0): grating, plate, "
       "hatch or vent, optional glow", pivot="top", params=[
           Param("size", "choice", "Größe (m)", choices=(1.0, 2.0, 4.0)),
           Param("style", "choice", "Art", choices=("grate", "plate", "hatch", "vent")),
           Param("glow", "bool", "Glow-Linien"),
           Param("stripes", "bool", "Warnstreifen"),
       ])
def floor_tile(rng, a):
    p = a.p
    size = p.choice("size", [1.0, 2.0, 2.0, 4.0])
    style = p.choice("style", ["grate", "plate", "hatch", "vent"])
    m = a.part("Deck")
    mat = p.material(["M_Platform", "M_Metal", "M_Ground"])
    a.meta.update({"size_m": size, "style": style})
    depth = 0.1 + rng.uniform(0.0, 0.1)
    if style == "grate":
        for s in (-1, 1):
            cube(m, (size, 0.06, depth), (0, s * (size / 2 - 0.03), -depth / 2), "M_RobotDark")
            cube(m, (0.06, size - 0.12, depth), (s * (size / 2 - 0.03), 0, -depth / 2), "M_RobotDark")
        n = int(size / 0.1)
        for i in range(n - 1):
            cube(m, (0.03, size - 0.12, depth * 0.8), (-size / 2 + (i + 1) * size / n, 0, -depth * 0.4), "M_Metal")
        cube(m, (size - 0.12, size - 0.12, 0.02), (0, 0, -depth + 0.01), "M_Ground")  # dark pit below
    else:
        cube(m, (size, size, depth), (0, 0, -depth / 2), mat, bevel=0.02)
        for i in range(int(size)):  # panel seams every metre
            for j in range(int(size)):
                cx, cy = -size / 2 + 0.5 + i, -size / 2 + 0.5 + j
                if style == "plate":
                    cube(m, (0.9, 0.9, 0.01), (cx, cy, 0.0), "M_Wall" if mat != "M_Wall" else "M_Metal")
                elif style == "hatch" and i == 0 and j == 0:
                    cube(m, (0.8, 0.8, 0.02), (cx, cy, 0.0), "M_HazardOrange", bevel=0.005)
                    cube(m, (0.3, 0.06, 0.04), (cx, cy - 0.25, 0.02), "M_RobotDark")
                elif style == "vent":
                    for k in range(5):
                        cube(m, (0.7, 0.05, 0.02), (cx, cy - 0.3 + k * 0.15, 0.0), "M_RobotDark")
    if p.bool("glow", 0.35):
        glow = p.glow()
        lights = a.part("Glow")
        for s in (-1, 1):
            cube(lights, (size * 0.9, 0.03, 0.02), (0, s * (size / 2 - 0.02), 0.0), glow)
    if p.bool("stripes", 0.25, warning=True):
        stripes(m, size * 0.9, (0, -size / 2 + 0.1, 0.006), count=int(size * 3), width=0.1)


@model("ceiling_panel", "CeilingPanel", "environment", "Ceiling panel (hangs at mount height): light panel, "
       "fan (Rotor) or plain plate", pivot="wall", view="below", params=[
           Param("size", "choice", "Größe (m)", choices=(1.0, 2.0, 4.0)),
           Param("style", "choice", "Art", choices=("light", "fan", "plain")),
           Param("mount_height", "float", "Deckenhöhe (m)", lo=2.0, hi=6.0, default=3.0),
           Param("fan_speed", "float", "Lüfter-Tempo (°/s)", lo=0, hi=2000, unity=True, default=200,
                 description="Nur mit Lüfter"),
       ])
def ceiling_panel(rng, a):
    p = a.p
    size = p.choice("size", [1.0, 2.0, 2.0, 4.0])
    style = p.choice("style", ["light", "light", "fan", "plain"])
    z = p.value("mount_height", 3.0)
    t = rng.uniform(0.08, 0.14)
    body = a.part("Body")
    a.meta.update({"size_m": size, "style": style})
    cube(body, (size, size, t), (0, 0, z - t / 2), p.styled("M_Wall", ["M_Wall", "M_Metal", "M_Platform"]), bevel=0.02)
    if style == "light":
        glow = p.glow(weights=(0.8, 0.05, 0.15))
        lights = a.part("Glow")
        n = 1 if size < 2 else int(size)
        for i in range(n):
            x = -size / 2 + size * (i + 0.5) / n
            cube(body, (size / n * 0.7, size * 0.7, 0.04), (x, 0, z - t - 0.02), "M_RobotDark")
            cube(lights, (size / n * 0.6, size * 0.6, 0.02), (x, 0, z - t - 0.05), glow)
        a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": "Steady"})
    elif style == "fan":
        r = size * 0.38
        cyl(body, r * 1.1, 0.08, (0, 0, z - t - 0.04), "M_RobotDark", sides=12)
        for i in range(4):
            cube(body, (r * 2.2, 0.03, 0.03), (0, 0, z - t - 0.1), "M_Metal", rot=(0, 0, math.pi / 4 * i))
        center = (0.0, 0.0, z - t - 0.16)
        fan(a.part("Rotor", pivot=center), center, r, rng.choice([3, 4, 5]), "M_Metal")
        a.behaviour("Rotator", {"target": "Rotor"}, {"axis": "up", "speed": p.option("fan_speed")})
    else:
        for i in range(int(size)):
            for j in range(int(size)):
                cube(body, (0.85, 0.85, 0.02), (-size / 2 + 0.5 + i, -size / 2 + 0.5 + j, z - t - 0.01), "M_Ground")


@model("wall_corner", "WallCorner", "environment", "Corner, end or T piece for the 3 m wall module (0.5 m thick)",
       params=[
           Param("style", "choice", "Art", choices=("corner", "end", "tee")),
           Param("pipe", "bool", "Rohr an der Ecke"),
           Param("guard", "bool", "Kantenschutz (Warnfarbe)"),
           Param("glow", "bool", "Glow-Linie"),
       ])
def wall_corner(rng, a):
    p = a.p
    style = p.choice("style", ["corner", "end", "tee"])
    m = a.part("Wall")
    cube(m, (0.5, 0.5, 3.0), (0, 0, 1.5), p.styled("M_Wall", ["M_Wall", "M_Metal"]), bevel=0.03)
    cube(m, (0.56, 0.56, 0.25), (0, 0, 0.125), "M_RobotDark", bevel=0.01)
    cube(m, (0.6, 0.6, 0.15), (0, 0, 2.95), "M_RobotDark", bevel=0.01)
    # exposed faces: corner -> front (-Y) and left (-X); end -> front, back, left; tee -> front
    faces = {"corner": ("front", "left"), "end": ("front", "back", "left"), "tee": ("front",)}[style]
    a.meta["style"] = style
    if p.bool("glow", 0.7):
        glow = p.glow()
        lights = a.part("Glow")
        for f in faces:
            if f in ("front", "back"):
                cube(lights, (0.5, 0.02, 0.05), (0, (-1 if f == "front" else 1) * 0.285, 2.45), glow)
            else:
                cube(lights, (0.02, 0.5, 0.05), (-0.285, 0, 2.45), glow)
    if p.bool("guard", 0.4, warning=True) and style != "tee":
        cube(m, (0.08, 0.08, 2.6), (-0.25, -0.25, 1.55), "M_Warning", rot=(0, 0, math.pi / 4))
    if p.bool("pipe", 0.4):
        x = -0.36 if style != "tee" else 0.0
        cyl(m, 0.06, 2.75, (x, -0.36, 1.5), "M_Metal", sides=8)
        for z in (0.6, 2.4):
            cube(m, (0.1, 0.14, 0.06), (x, -0.3, z), "M_RobotDark")
        a.meta["pipe"] = True


@model("window_wall", "WindowWall", "environment", "Wall module 2 or 4 m with windows (Glass): single, split or band",
       params=[
           Param("length", "choice", "Länge (m)", choices=(2.0, 4.0)),
           Param("windows", "choice", "Fenster", choices=("single", "split", "band")),
           Param("sill", "float", "Brüstung (m)", lo=0.2, hi=1.5),
           Param("glow", "bool", "Glow-Linie"),
       ])
def window_wall(rng, a):
    p = a.p
    length = p.choice("length", [2.0, 4.0, 4.0])
    kind = p.choice("windows", ["single", "split", "band"])
    sill = p.float("sill", 0.7, 1.1)
    top = rng.uniform(2.2, 2.5)
    m, glass = a.part("Wall"), a.part("Glass")
    mat = p.styled("M_Wall", ["M_Wall", "M_Metal"])
    a.meta.update({"length_m": length, "windows": kind})
    cube(m, (length, 0.5, sill), (0, 0, sill / 2), mat, bevel=0.03)
    cube(m, (length, 0.5, 3.0 - top), (0, 0, top + (3.0 - top) / 2), mat, bevel=0.03)
    _wall_trims(m, length)
    if kind == "band":
        openings = [(-length / 2 + 0.2, length / 2 - 0.2)]
    else:
        openings = [(-length / 2 + i * 2 + 0.3, -length / 2 + i * 2 + 1.7) for i in range(int(length // 2))]
    edges = [-length / 2] + [e for o in openings for e in o] + [length / 2]
    for x0, x1 in zip(edges[0::2], edges[1::2]):  # solid posts between the openings
        if x1 - x0 > 1e-6:
            cube(m, (x1 - x0, 0.5, top - sill), ((x0 + x1) / 2, 0, (sill + top) / 2), mat)
    oh = top - sill
    for x0, x1 in openings:
        cx, ow = (x0 + x1) / 2, x1 - x0
        for s in (-1, 1):  # dark frame around the opening, front and back
            cube(m, (ow + 0.1, 0.06, 0.06), (cx, s * 0.25, sill), "M_RobotDark")
            cube(m, (ow + 0.1, 0.06, 0.06), (cx, s * 0.25, top), "M_RobotDark")
            for x in (x0, x1):
                cube(m, (0.06, 0.06, oh), (x, s * 0.25, (sill + top) / 2), "M_RobotDark")
        cube(m, (ow + 0.1, 0.34, 0.06), (cx, -0.08, sill + 0.03), "M_Metal")  # sill
        cube(glass, (ow, 0.04, oh), (cx, 0, (sill + top) / 2), "M_Glass")
        mullions = 1 if kind == "split" else (int(ow / 1.0) if kind == "band" else 0)
        for k in range(mullions):
            x = x0 + ow * (k + 1) / (mullions + 1)
            cube(m, (0.06, 0.1, oh), (x, 0, (sill + top) / 2), "M_RobotDark")
    if p.bool("glow", 0.5):
        glow = p.glow()
        lights = a.part("Glow")
        for y in (-0.285, 0.285):
            cube(lights, (length - 0.4, 0.02, 0.05), (0, y, top + 0.2), glow)


@model("cable_tray", "CableTray", "environment", "Wall cable tray / conduit (2 or 4 m along X) with cable bundle",
       pivot="wall", params=[
           Param("length", "choice", "Länge (m)", choices=(2.0, 4.0)),
           Param("mount_height", "float", "Höhe über Boden (m)", lo=0.3, hi=3.0),
           Param("style", "choice", "Art", choices=("tray", "conduit")),
           Param("cables", "int", "Kabel", lo=1, hi=10),
       ])
def cable_tray(rng, a):
    p = a.p
    length = p.choice("length", [2.0, 4.0])
    z = p.value("mount_height", rng.uniform(1.8, 2.7))
    style = p.choice("style", ["tray", "tray", "conduit"])
    n = p.int("cables", 3, 6)
    m = a.part("Body")
    w = rng.uniform(0.2, 0.35)
    z = max(z, 0.15)
    yc = 0.1 - 0.05 - w / 2
    a.meta.update({"length_m": length, "style": style})
    for x in [-length / 2 + 0.25 + i * 1.0 for i in range(int(length))]:  # wall brackets
        cube(m, (0.04, w + 0.08, 0.04), (x, 0.06 - (w + 0.08) / 2, z - 0.06), "M_RobotDark")
        cube(m, (0.04, 0.03, 0.18), (x, 0.085, z - 0.0), "M_RobotDark")
    if style == "tray":  # open U channel
        cube(m, (length, w, 0.02), (0, yc, z - 0.03), "M_Metal")
        for s in (-1, 1):
            cube(m, (length, 0.02, 0.1), (0, yc + s * w / 2, z + 0.01), "M_Metal")
        mats = ["M_RobotDark", "M_RobotDark", "M_HazardOrange", "M_Warning", "M_Wall"]
        for i in range(n):  # cables lying in the tray
            r = rng.uniform(0.015, 0.03)
            col, row = i % 4, i // 4
            cyl(m, r, length, (0, yc - w / 2 + 0.04 + col * (w - 0.08) / 3, z - 0.02 + r + row * 0.05),
                rng.choice(mats), sides=6, rot=ALONG_X)
    else:  # closed conduits
        for i in range(min(n, 4)):
            r = rng.uniform(0.03, 0.05)
            y = 0.1 - r - 0.02 - i * (w / 4)
            cyl(m, r, length, (0, y, z), "M_Metal" if i % 2 == 0 else "M_Wall", sides=8, rot=ALONG_X)
            for x in (-length / 2 + 0.1, length / 2 - 0.1):
                cyl(m, r * 1.3, 0.06, (x, y, z), "M_RobotDark", sides=8, rot=ALONG_X)


@model("lift", "Lift", "environment", "Lift platform: moving Deck between two columns "
       "(Door script moves it up)", params=[
           Param("size", "float", "Plattform (m)", lo=1.0, hi=3.0, size=True),
           Param("travel", "float", "Hub (m)", lo=0.5, hi=4.0, unity=True),
           Param("speed", "float", "Tempo (m/s)", lo=0.1, hi=5.0, unity=True, default=1.0),
           Param("rail", "bool", "Geländer auf der Plattform"),
       ])
def lift(rng, a):
    p = a.p
    s = p.float("size", 1.4, 2.4)
    travel = p.value("travel", round(rng.uniform(1.5, 3.0) * 2) / 2)
    frame_mat = p.material(["M_RobotDark", "M_Metal", "M_HazardOrange"])
    col_h = travel + 0.6
    cube(a.part("Base"), (s + 0.2, s + 0.2, 0.12), (0, 0, 0.06), "M_RobotDark", bevel=0.02)
    for side, x in (("Left", -(s / 2 + 0.15)), ("Right", s / 2 + 0.15)):
        f = a.part(f"Frame_{side}")
        cube(f, (0.25, 0.3, col_h), (x, s * 0.3, col_h / 2), frame_mat, bevel=0.02)
        cube(f, (0.06, 0.32, col_h - 0.4), (x - math.copysign(0.12, x), s * 0.3, col_h / 2), "M_Warning")
    top = a.part("Frame_Top")
    cube(top, (s + 0.55, 0.3, 0.2), (0, s * 0.3, col_h + 0.1), frame_mat, bevel=0.02)
    for side, y in (("Front", s * 0.3 - 0.16), ("Back", s * 0.3 + 0.16)):
        cube(a.part(f"StatusLight_{side}"), (0.4, 0.02, 0.08), (0, y, col_h + 0.1), "M_GlowRed")
    center = (0.0, 0.0, 0.2)
    deck = a.part("Deck", pivot=center)
    cube(deck, (s, s, 0.14), (0, 0, 0.19), p.material(["M_Platform", "M_Metal"]), bevel=0.02)
    stripes(deck, s * 0.9, (0, -s / 2 + 0.08, 0.265), count=6, width=0.1)
    for x in (-s / 2 - 0.02, s / 2 + 0.02):  # guide shoes running in the columns
        cube(deck, (0.08, 0.2, 0.1), (x, s * 0.3, 0.19), "M_RobotDark")
    if p.bool("rail", 0.5):
        for x in (-s / 2 + 0.04, s / 2 - 0.04):
            for y in (-s / 2 + 0.04, s / 2 - 0.3):
                cube(deck, (0.05, 0.05, 0.9), (x, y, 0.26 + 0.45), "M_Metal")
            cube(deck, (0.05, s - 0.3, 0.05), (x, -0.13, 0.26 + 0.9), "M_Metal")
    a.meta["travel_m"] = travel
    a.behaviour("Door", {"panels": ["Deck"], "statusLights": ["StatusLight_Front", "StatusLight_Back"],
                         "upperFrame": ["Frame_Top"], "colliders": ["Frame_Left", "Frame_Right", "Base"]},
                {"openOffset": [0.0, round(travel, 4), 0.0], "speed": p.option("speed")},
                note="lift: 'open' = Deck up by travel (Unity Y); same mover as a vertical door")


@model("conveyor", "Conveyor", "industrial", "Conveyor along X: roller track or belt with end drums "
       "(Roller_<n>, Rotator)", params=[
           Param("style", "choice", "Art", choices=("rollers", "belt")),
           Param("length", "float", "Länge (m)", lo=0.8, hi=4.0, size=True),
           Param("width", "float", "Breite (m)", lo=0.4, hi=1.5, size=True),
           Param("height", "float", "Höhe (m)", lo=0.3, hi=1.2),
           Param("speed", "float", "Rollen-Tempo (°/s)", lo=0, hi=1000, unity=True, default=180),
       ])
def conveyor(rng, a):
    p = a.p
    style = p.choice("style", ["rollers", "belt"])
    length = p.float("length", 1.5, 3.0)
    w = p.float("width", 0.6, 1.0)
    h = p.float("height", 0.6, 0.9)
    frame = p.material(["M_RobotDark", "M_Metal", "M_Wall"])
    body = a.part("Body")
    a.meta["style"] = style
    for s in (-1, 1):
        cube(body, (length, 0.06, 0.16), (0, s * (w / 2 + 0.03), h - 0.02), frame, bevel=0.01)
    for x in (-length / 2 + 0.1, length / 2 - 0.1) + ((0.0,) if length > 2.5 else ()):
        for s in (-1, 1):
            cube(body, (0.06, 0.06, h - 0.1), (x, s * (w / 2 + 0.03), (h - 0.1) / 2), "M_RobotDark")
        cube(body, (0.05, w, 0.05), (x, 0, h * 0.3), "M_RobotDark")
    stripes(body, length * 0.9, (0, -w / 2 - 0.065, h - 0.02), count=int(length * 3), width=0.01, height=0.08)
    r = 0.045 if style == "rollers" else 0.08
    if style == "rollers":
        n = max(3, int(length / 0.18))
        xs = [-length / 2 + 0.1 + i * (length - 0.2) / (n - 1) for i in range(n)]
    else:
        xs = [-length / 2 + r + 0.02, length / 2 - r - 0.02]
        belt = a.part("Belt")
        cube(belt, (length - 0.04, w - 0.04, 0.02), (0, 0, h + 0.01), "M_Ground")
        cube(belt, (length - 2 * r - 0.04, w - 0.04, 0.02), (0, 0, h - 2 * r + 0.01), "M_Ground")
    for i, x in enumerate(xs):
        center = (x, 0.0, h - r + 0.01) if style == "belt" else (x, 0.0, h - 0.01)
        roller = a.part(f"Roller_{i + 1}", pivot=center)
        cyl(roller, r, w - 0.02 if style == "rollers" else w - 0.06, center, "M_Metal", sides=8, rot=ALONG_Y)
        cube(roller, (r * 0.5, w * 0.6, r * 2.05), center, "M_RobotDark")  # makes the turning visible
        a.behaviour("Rotator", {"target": f"Roller_{i + 1}"}, {"axis": "forward", "speed": p.option("speed")})
    a.meta["rollers"] = len(xs)


@model("pad", "Pad", "environment", "Jump pad (arrows, glow) or teleporter pad (floating ring, Rotor)", params=[
    Param("kind", "choice", "Art", choices=("jump", "teleport")),
    Param("radius", "float", "Radius (m)", lo=0.4, hi=2.0, size=True, snap_factor=2),
    Param("mode", "choice", "SignalLight-Modus", choices=("Steady", "Pulse", "Blink"), unity=True, default="Pulse"),
    Param("speed", "float", "Ring-Tempo (°/s)", lo=0, hi=720, unity=True, default=90,
          description="Nur Teleporter"),
])
def pad(rng, a):
    p = a.p
    kind = p.choice("kind", ["jump", "teleport"])
    r = p.float("radius", 0.6, 1.2)
    glow = p.glow(weights=(0.7, 0.05, 0.25))
    body, lights = a.part("Body"), a.part("Glow")
    sides = 10
    a.meta["kind"] = kind
    cyl(body, r * 1.15, 0.12, (0, 0, 0.06), "M_RobotDark", sides=sides, bevel=0.02)
    cyl(body, r, 0.06, (0, 0, 0.15), p.material(["M_Platform", "M_Metal", "M_Wall"]), sides=sides, bevel=0.01)
    cyl(lights, r * 1.05, 0.04, (0, 0, 0.12), glow, sides=sides)
    if kind == "jump":
        cyl(lights, r * 0.35, 0.03, (0, 0, 0.19), glow, sides=sides)
        for i in range(4):  # chevrons pointing outwards
            ang = math.pi / 2 * i
            for k in (0.55, 0.75):
                for s in (-1, 1):
                    cube(body, (r * 0.18, 0.04, 0.02), (math.cos(ang) * r * k - math.sin(ang) * s * r * 0.06,
                                                        math.sin(ang) * r * k + math.cos(ang) * s * r * 0.06, 0.185),
                         "M_Warning", rot=(0, 0, ang - s * deg(40)))  # V pointing outwards
        a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")})
    else:
        for i in range(3):  # pylons that carry the ring
            ang = 2 * math.pi * i / 3 + math.pi / 2
            cube(body, (0.12, 0.12, 1.4), (math.cos(ang) * r * 1.05, math.sin(ang) * r * 1.05, 0.7 + 0.1),
                 "M_RobotDark", bevel=0.02)
        center = (0.0, 0.0, 1.6)
        ring = a.part("Rotor", pivot=center)
        n = 12
        for i in range(n):
            ang = 2 * math.pi * i / n
            mat = "M_Crystal" if i % 3 == 0 else "M_Metal"
            cube(ring, (2 * math.pi * r * 0.95 / n * 1.05, 0.08, 0.08),
                 (math.cos(ang) * r * 0.95, math.sin(ang) * r * 0.95, 1.6), mat, rot=(0, 0, ang + math.pi / 2))
        a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")})
        a.behaviour("Rotator", {"target": "Rotor"}, {"axis": "up", "speed": p.option("speed")})
