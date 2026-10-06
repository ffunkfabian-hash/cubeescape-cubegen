"""More pieces for the modular building kit: ramps, ceiling and roof modules, archways, wall caps and baseboards.

They follow the family measures like the wall module (``families.DIMS``): module
length, wall height and thickness, door opening (archway), walkway width (ramp).
All are static decoration with explicit colliders where people walk or pass.
"""

from __future__ import annotations

import math

from ..geometry import prism
from ..params import Param
from .common import cube, cyl, frustum, stripes
from .kit import YZ_TO_X, slope_colliders
from .registry import model

# a polygon drawn in (x, z) facing the front: local x -> x, local y -> z, extrusion -> -y
UPRIGHT = ((1, 0, 0), (0, 0, -1), (0, 1, 0))


def _module(p, rng, name="length"):
    """Module length: 2 or 4 m from the seed (a family sets its own)."""
    return p.value(name, rng.choice([2.0, 4.0, 4.0]))


# --------------------------------------------------------------------------
# ramp
# --------------------------------------------------------------------------

@model("ramp", "Ramp", "environment", "Short ramp on the module grid, climbs towards +Y by 0.1-1.5 m (platform "
       "edges, loading docks): wedge, curbs, rails, anti-slip surface", params=[
           Param("width", "float", "Breite (m)", lo=0.6, hi=4.0, size=True),
           Param("length", "float", "Länge (m)", lo=1.0, hi=8.0, size=True),
           Param("rise", "float", "Höhe (m)", lo=0.1, hi=1.5, size=True),
           Param("surface", "choice", "Belag", choices=("bars", "plates", "chevrons")),
           Param("curbs", "bool", "Randleisten"),
           Param("rails", "choice", "Geländer", choices=("none", "left", "both")),
           Param("glow_edges", "bool", "Glow-Kanten"),
           Param("stripes", "bool", "Warnstreifen unten"),
       ])
def ramp(rng, a):
    p = a.p
    w = p.float("width", 1.0, 2.0)
    run = _module(p, rng)
    rise = p.float("rise", 0.25, 1.0)
    surface = p.choice("surface", ["bars", "plates", "chevrons"])
    mat = p.material(["M_Metal", "M_Wall", "M_Platform"])
    glow = p.glow()
    body = a.part("Body")
    a.meta.update({"run_m": run, "rise_m": round(rise, 4), "surface": surface})
    lip = min(0.4, run * 0.15)  # flat landing at the top: the next deck joins on the level
    slope_run = run - lip
    body.add(prism([(-run / 2, 0.0), (run / 2, 0.0), (run / 2, rise), (run / 2 - lip, rise)], w, mat), basis=YZ_TO_X)
    slope_colliders(a, w, slope_run, rise, center_y=-lip / 2)
    a.collider((w, lip, rise), (0, run / 2 - lip / 2, rise / 2))
    run_full, run = run, slope_run  # the details below follow the slope

    slope, ln = math.atan2(rise, run), math.hypot(run, rise)
    y0 = -run_full / 2

    def on_slope(t, size, material, x=0.0, rz=0.0):
        cube(body, size, (x, y0 + run * t, rise * t + size[2] / 2 + 0.002), material, rot=(slope, 0, rz))

    count = max(2, int(ln / 0.45))
    for i in range(count):
        t = (i + 0.5) / count
        if surface == "bars":
            on_slope(t, (w * 0.9, 0.05, 0.025), "M_RobotDark")
        elif surface == "plates":
            on_slope(t, (w * 0.42, ln / count * 0.8, 0.015), "M_Ground", x=-w * 0.23)
            on_slope(t, (w * 0.42, ln / count * 0.8, 0.015), "M_Ground", x=w * 0.23)
        else:
            for s in (-1, 1):
                on_slope(t, (w * 0.4, 0.06, 0.02), "M_Warning", x=s * w * 0.18, rz=s * math.radians(25))
    if p.bool("curbs", 0.5):
        for s in (-1, 1):
            curb = prism([(y0, 0.0), (-y0, 0.0), (-y0, rise + 0.1), (y0 + run, rise + 0.1), (y0, 0.1)], 0.08,
                         "M_RobotDark")
            body.add(curb, loc=(s * (w / 2 + 0.04), 0, 0), basis=YZ_TO_X)
        a.meta["curbs"] = True
    rails = p.choice("rails", ["none", "none", "left", "both"])
    if rails != "none" and rise >= 0.3:
        for s in ((-1,) if rails == "left" else (-1, 1)):
            x = s * (w / 2 + 0.1)
            for t in (0.05, 0.5, 0.95):
                cube(body, (0.05, 0.05, 1.0), (x, y0 + run * t, rise * t + 0.5), "M_Metal")
            cube(body, (0.06, ln, 0.06), (x, y0 + run / 2, rise / 2 + 1.0), "M_Metal", rot=(slope, 0, 0))
            fence = max(0.2, (run - math.sin(slope)) / math.cos(slope))
            a.collider((0.08, fence, 1.0), (x, y0 + run / 2, rise / 2 + 0.5), rot=(slope, 0, 0))
    if p.bool("glow_edges", 0.35):
        lights = a.part("Glow")
        for s in (-1, 1):
            cube(lights, (0.03, ln * 0.9, 0.02), (s * (w / 2 - 0.06), y0 + run / 2, rise / 2 + 0.012), glow,
                 rot=(slope, 0, 0))
        cube(lights, (w * 0.8, 0.02, 0.03), (0, y0 + 0.05, 0.03), glow)
    if p.bool("stripes", 0.3, warning=True):
        stripes(body, w * 0.9, (0, y0 + 0.1, 0.02), count=max(3, int(w * 3)), width=0.1)


# --------------------------------------------------------------------------
# ceiling and roof module
# --------------------------------------------------------------------------

@model("ceiling_module", "CeilingModule", "environment", "Ceiling / roof slab on the module grid, resting on the "
       "walls (underside at wall height): beams, coffers with lights, skylight (Glass), vent or a pitched roof",
       pivot="wall", view="below", params=[
           Param("size", "float", "Größe (m)", lo=1.0, hi=8.0, size=True),
           Param("style", "choice", "Art", choices=("beams", "coffered", "skylight", "vent", "roof")),
           Param("mount_height", "float", "Wandhöhe (m)", lo=2.0, hi=6.0, default=3.0),
           Param("thickness", "float", "Stärke (m)", lo=0.1, hi=0.5),
       ])
def ceiling_module(rng, a):
    p = a.p
    size = _module(p, rng, "size")
    style = p.choice("style", ["beams", "coffered", "skylight", "vent", "roof"])
    h = p.value("mount_height", 3.0)
    t = p.float("thickness", 0.15, 0.25)
    mat = p.styled("M_Wall", ["M_Wall", "M_Metal", "M_Platform"])
    body = a.part("Body")
    a.meta.update({"size_m": size, "style": style, "thickness_m": round(t, 4)})
    zc = h + t / 2
    if style == "skylight":
        hole = size * rng.uniform(0.35, 0.55)
        rim = (size - hole) / 2
        for s in (-1, 1):
            cube(body, (size, rim, t), (0, s * (size - rim) / 2, zc), mat)
            cube(body, (rim, hole, t), (s * (size - rim) / 2, 0, zc), mat)
        cube(a.part("Glass"), (hole, hole, 0.04), (0, 0, h + t - 0.03), "M_Glass")
        for k in range(1, 3):  # mullions
            x = -hole / 2 + hole * k / 3
            cube(body, (0.05, hole, 0.08), (x, 0, h + t - 0.03), "M_RobotDark")
        a.meta["skylight_m"] = round(hole, 3)
    else:
        cube(body, (size, size, t), (0, 0, zc), mat, bevel=0.02)
    if style in ("beams", "skylight", "roof"):
        n = max(2, int(round(size)))
        for i in range(n):
            y = -size / 2 + size * (i + 0.5) / n
            cube(body, (size, 0.14, 0.2), (0, y, h - 0.1), "M_RobotDark")
    if style == "coffered":
        n = max(1, int(round(size / 1.0)))
        cell = size / n
        lights = a.part("Glow")
        glow = p.glow(weights=(0.8, 0.05, 0.15))
        for i in range(n):
            for j in range(n):
                x, y = -size / 2 + cell * (i + 0.5), -size / 2 + cell * (j + 0.5)
                cube(body, (cell * 0.8, cell * 0.8, 0.05), (x, y, h - 0.025), "M_RobotDark")
                cube(lights, (cell * 0.5, cell * 0.5, 0.02), (x, y, h - 0.06), glow)
        for k in range(n + 1):  # ribs between the coffers
            c = -size / 2 + cell * k
            cube(body, (0.08, size, 0.12), (c, 0, h - 0.06), mat)
            cube(body, (size, 0.08, 0.12), (0, c, h - 0.06), mat)
    if style == "vent":
        vw = size * rng.uniform(0.3, 0.45)
        cube(body, (vw + 0.1, vw + 0.1, 0.2), (0, 0, h - 0.1), "M_RobotDark", bevel=0.01)
        for k in range(6):
            y = -vw / 2 + vw * (k + 0.5) / 6
            cube(body, (vw, 0.03, 0.05), (0, y, h - 0.225), "M_Metal", rot=(math.radians(30), 0, 0))
        cyl(body, vw * 0.3, 0.3, (size * 0.3, size * 0.3, h + t + 0.15), "M_Metal", sides=8)
    if style == "roof":  # pitched roof on top of the slab, ridge along X
        ridge = size * rng.uniform(0.15, 0.3)
        body.add(prism([(-size / 2, 0.0), (size / 2, 0.0), (0.0, ridge)], size, p.material(["M_Wall", "M_RobotDark",
                                                                                              "M_Metal"])),
                 loc=(0, 0, h + t), basis=YZ_TO_X)
        cube(body, (size + 0.1, 0.12, 0.1), (0, 0, h + t + ridge + 0.02), "M_RobotDark")
        a.meta["ridge_m"] = round(ridge, 3)
    a.collider((size, size, t), (0, 0, zc))


# --------------------------------------------------------------------------
# archway
# --------------------------------------------------------------------------

ARCH_SHAPES = ("round", "pointed", "chamfer", "flat")


def _arch_curve(shape, w, oh):
    """Top edge of the opening from left to right, (x, z)."""
    if shape == "round":
        zs = oh - w / 2
        return [(math.cos(math.pi - math.pi * k / 10) * w / 2, zs + math.sin(math.pi * k / 10) * w / 2)
                for k in range(11)]
    if shape == "pointed":
        zs = oh - w * 0.6
        return [(-w / 2, zs), (-w * 0.38, zs + (oh - zs) * 0.55), (-w * 0.2, zs + (oh - zs) * 0.86), (0.0, oh),
                (w * 0.2, zs + (oh - zs) * 0.86), (w * 0.38, zs + (oh - zs) * 0.55), (w / 2, zs)]
    if shape == "chamfer":
        c = w * 0.2
        return [(-w / 2, oh - c), (-w / 2 + c, oh), (w / 2 - c, oh), (w / 2, oh - c)]
    return [(-w / 2, oh), (w / 2, oh)]


@model("archway", "Archway", "environment", "Archway / open passage as a wall module (no door): posts, round, "
       "pointed, chamfered or flat arch, trims, glow", params=[
           Param("length", "float", "Länge (m)", lo=1.5, hi=8.0, size=True),
           Param("height", "float", "Wandhöhe (m)", lo=2.0, hi=6.0, default=3.0),
           Param("thickness", "float", "Wandstärke (m)", lo=0.2, hi=1.0, default=0.5),
           Param("width", "float", "Durchgang Breite (m)", lo=0.8, hi=4.0, size=True),
           Param("opening_height", "float", "Durchgang Höhe (m)", lo=1.8, hi=5.5, size=True),
           Param("shape", "choice", "Bogen", choices=ARCH_SHAPES),
           Param("glow", "bool", "Glow-Leisten"),
       ])
def archway(rng, a):
    p = a.p
    length = _module(p, rng)
    h = p.value("height", 3.0)
    t = p.value("thickness", 0.5)
    w = p.float("width", 1.2, min(2.4, length - 0.6))
    oh = p.float("opening_height", 2.1, max(2.2, min(2.8, h - 0.4)))
    shape = p.choice("shape", list(ARCH_SHAPES))
    if w + 0.4 > length:
        if "width" in p.overrides and "length" not in p.overrides:  # a given passage: the module grows (2 m grid)
            length = 2.0 * math.ceil((w + 0.4) / 2.0 - 1e-9)
            p.used["length"] = length
        else:  # a given module: the passage fits into it
            w = length - 0.4
            p.used["width"] = w
    oh = min(oh, h - 0.3)  # keep a lintel
    curve = _arch_curve(shape, w, oh)
    if min(z for _, z in curve) < 0.8:  # too wide for the height: chamfer instead
        shape, curve = "chamfer", _arch_curve("chamfer", w, oh)
    mat = p.styled("M_Wall", ["M_Wall", "M_Metal"])
    m = a.part("Wall")
    a.meta.update({"length_m": length, "shape": shape, "opening_m": [round(w, 4), round(oh, 4)]})
    post = (length - w) / 2
    for s in (-1, 1):
        x = s * (w / 2 + post / 2)
        cube(m, (post, t, h), (x, 0, h / 2), mat)
        cube(m, (post, t + 0.06, 0.25), (x, 0, 0.125), "M_RobotDark")
        a.collider((post, t, h), (x, 0, h / 2))
    poly = [(-w / 2, h)] + curve + [(w / 2, h)]
    m.add(prism(poly, t, mat), basis=UPRIGHT)  # prism is centred: flush with the posts at y = ±t/2
    cube(m, (length, t + 0.08, 0.12), (0, 0, h - 0.06), "M_RobotDark")
    a.collider((w, t, h - oh), (0, 0, (h + oh) / 2))
    # frame band along the passage edge, front and back
    for y in (-t / 2 - 0.02, t / 2 + 0.02):
        for (x1, z1), (x2, z2) in zip(curve, curve[1:]):
            ln = math.hypot(x2 - x1, z2 - z1)
            cube(m, (ln + 0.06, 0.04, 0.12), ((x1 + x2) / 2, y, (z1 + z2) / 2), "M_RobotDark",
                 rot=(0, -math.atan2(z2 - z1, x2 - x1), 0))
        zs = curve[0][1]
        for x in (-w / 2, w / 2):
            cube(m, (0.12, 0.04, zs - 0.25), (x, y, 0.25 + (zs - 0.25) / 2), "M_RobotDark")
    if shape in ("round", "pointed"):  # keystone
        cube(m, (0.3, t + 0.1, 0.35), (0, 0, oh + 0.12), "M_Metal", bevel=0.02)
    if p.bool("glow", 0.5):
        glow = p.glow()
        lights = a.part("Glow")
        zs = curve[0][1]
        for s in (-1, 1):
            cube(lights, (0.03, t * 0.6, zs - 0.6), (s * (w / 2 + 0.015), 0, 0.3 + (zs - 0.6) / 2), glow)


# --------------------------------------------------------------------------
# wall cap and baseboard
# --------------------------------------------------------------------------

@model("wall_cap", "WallCap", "environment", "Wall cap (Wandabschluss) on top of a wall module: coping plate, "
       "bevelled, with railing or glow strip", pivot="wall", params=[
           Param("length", "float", "Länge (m)", lo=1.0, hi=8.0, size=True),
           Param("thickness", "float", "Wandstärke (m)", lo=0.2, hi=1.0, default=0.5),
           Param("height", "float", "Wandhöhe (m)", lo=2.0, hi=6.0, default=3.0),
           Param("style", "choice", "Art", choices=("flat", "bevel", "rail", "glow")),
       ])
def wall_cap(rng, a):
    p = a.p
    length = _module(p, rng)
    t = p.value("thickness", 0.5)
    h = p.value("height", 3.0)
    style = p.choice("style", ["flat", "bevel", "rail", "glow"])
    over = rng.uniform(0.03, 0.08)
    ct = rng.uniform(0.08, 0.15)
    m = a.part("Body")
    mat = p.material(["M_RobotDark", "M_Metal", "M_Wall"])
    a.meta.update({"length_m": length, "style": style})
    if style == "bevel":
        frustum(m, (length, t + 2 * over), (length, t * 0.6), h, h + ct * 1.5, mat)
    else:
        cube(m, (length, t + 2 * over, ct), (0, 0, h + ct / 2), mat, bevel=0.01)
    for k in range(int(length) + 1):  # joints / bolts along the cap
        x = -length / 2 + 0.05 + (length - 0.1) * k / max(1, int(length))
        cube(m, (0.04, t + 2 * over + 0.01, 0.03), (x, 0, h + 0.015), "M_Metal")
    if style == "rail":  # a railing on the wall top (walkable wall crowns, galleries)
        posts = max(2, int(round(length)) + 1)
        z0 = h + ct
        for i in range(posts):
            x = -length / 2 + 0.05 + (length - 0.1) * i / (posts - 1)
            cube(m, (0.06, 0.06, 1.0), (x, 0, z0 + 0.5), "M_Metal")
        for z in (z0 + 1.0, z0 + 0.5):
            cube(m, (length - 0.04, 0.05, 0.05), (0, 0, z), "M_Metal")
        a.collider((length, 0.1, 1.0), (0, 0, z0 + 0.5))
    if style == "glow":
        glow = p.glow()
        lights = a.part("Glow")
        for s in (-1, 1):
            cube(lights, (length * 0.9, 0.02, 0.03), (0, s * (t / 2 + over + 0.01), h + ct / 2), glow)


@model("baseboard", "Baseboard", "environment", "Baseboard / skirting along the foot of a wall (back at y = 0, "
       "against the wall face): plain, vent slots, glow line or cable duct", params=[
           Param("length", "float", "Länge (m)", lo=1.0, hi=8.0, size=True),
           Param("height", "float", "Höhe (m)", lo=0.08, hi=0.4),
           Param("style", "choice", "Art", choices=("plain", "vent", "glow", "duct")),
       ])
def baseboard(rng, a):
    p = a.p
    length = _module(p, rng)
    bh = p.float("height", 0.1, 0.25)
    style = p.choice("style", ["plain", "vent", "glow", "duct"])
    d = rng.uniform(0.03, 0.06) if style != "duct" else rng.uniform(0.08, 0.12)
    m = a.part("Body")
    mat = p.material(["M_RobotDark", "M_Metal", "M_Wall"])
    a.meta.update({"length_m": length, "style": style, "height_m": round(bh, 4)})
    cube(m, (length, d, bh), (0, -d / 2, bh / 2), mat)
    cube(m, (length, d + 0.01, 0.015), (0, -(d + 0.01) / 2, bh + 0.0075), "M_Metal")
    if style == "vent":
        n = int(length / 0.5)
        for i in range(n):
            x = -length / 2 + length * (i + 0.5) / n
            for k in range(3):
                cube(m, (0.2, 0.01, 0.015), (x, -d - 0.005, bh * (0.3 + 0.2 * k)), "M_Ground")
    elif style == "glow":
        cube(a.part("Glow"), (length * 0.96, 0.012, 0.02), (0, -d - 0.006, bh * 0.55), p.glow())
    elif style == "duct":
        for i in range(int(length) + 1):
            x = -length / 2 + 0.05 + (length - 0.1) * i / max(1, int(length))
            cube(m, (0.05, d + 0.01, bh + 0.01), (x, -(d + 0.01) / 2, bh / 2), "M_Metal")
        for k in range(rng.randint(1, 3)):
            cyl(m, 0.012, length, (0, -d - 0.012, 0.03 + k * 0.03), rng.choice(["M_HazardOrange", "M_RobotDark",
                                                                                   "M_Warning"]),
                sides=6, rot=(0, math.pi / 2, 0))
