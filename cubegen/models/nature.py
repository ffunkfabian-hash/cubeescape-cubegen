"""Nature: rock formations, floating islands, hanging crystals, alien plants, hydroponic beds, stalagmites and
mushrooms.

Static decoration - goes into Art/Models/Library/Nature. Shapes are jittered
low-poly spheres and cones; the walkable top of a floating island stays flat
at z = 0 like the platforms.
"""

from __future__ import annotations

import math

from ..geometry import lathe, sphere
from ..params import Param
from .common import ALONG_X, add_vec, cube, cyl, deg, rotated, strut
from .registry import model

ROCK = ["M_Ground", "M_Ground", "M_Wall", "M_RobotDark"]


def _jitter(mesh, part, rng, amount, keep=lambda v: False):
    for vi in part.vertex_indices():
        v = mesh.verts[vi]
        if keep(v):
            continue
        mesh.verts[vi] = (v[0] + rng.uniform(-amount, amount), v[1] + rng.uniform(-amount, amount),
                          v[2] + rng.uniform(-amount, amount))


def _boulder(rng, mesh, center, size, material, flat_bottom=True):
    """One jittered low-poly boulder; with ``flat_bottom`` it sits on z = center z."""
    sx, sy, sz = size
    part = mesh.add(sphere(1.0, rng.choice([5, 6, 7]), 3, material), loc=(center[0], center[1], center[2] + sz * 0.5),
                    scale=(sx / 2, sy / 2, sz / 2), rot=(0, 0, rng.uniform(0, math.pi)))
    _jitter(mesh, part, rng, min(sx, sy, sz) * 0.12)
    if flat_bottom:
        for vi in part.vertex_indices():
            x, y, z = mesh.verts[vi]
            mesh.verts[vi] = (x, y, max(z, center[2]))
    return part


def _crystal(mesh, foot, length, radius, tilt, sides=6):
    """Crystal: prism + pointed tip along the tilted axis, starting at ``foot``."""
    cyl(mesh, radius, length * 0.7, add_vec(foot, rotated(tilt, (0, 0, length * 0.35))), "M_Crystal", sides=sides,
        radius_top=radius * 0.9, rot=tilt)
    cyl(mesh, radius * 0.9, length * 0.3, add_vec(foot, rotated(tilt, (0, 0, length * 0.85))), "M_Crystal",
        sides=sides, radius_top=0.0, rot=tilt)


@model("rock", "Rock", "nature", "Rock formation: a cluster of jittered boulders, optional spire and crystals",
       params=[
           Param("size", "float", "Größe (m)", lo=0.3, hi=4.0, size=True),
           Param("boulders", "int", "Brocken", lo=1, hi=8),
           Param("spire", "bool", "Felsnadel"),
           Param("crystals", "int", "Kristalle", lo=0, hi=8),
       ])
def rock(rng, a):
    p = a.p
    s = p.float("size", 0.8, 2.0)
    m = a.part("Rock")
    mat = p.material(ROCK)
    n = p.int("boulders", 2, 5)
    _boulder(rng, m, (0, 0, 0), (s, s * rng.uniform(0.7, 1.0), s * rng.uniform(0.5, 0.9)), mat)
    for _ in range(n - 1):
        ang = rng.uniform(0, 2 * math.pi)
        k = rng.uniform(0.3, 0.6)
        dist = s * rng.uniform(0.35, 0.6)
        _boulder(rng, m, (math.cos(ang) * dist, math.sin(ang) * dist, 0), (s * k, s * k * rng.uniform(0.7, 1.0),
                                                                           s * k * rng.uniform(0.5, 0.9)),
                 rng.choice(ROCK))
    if p.bool("spire", 0.35):
        h = s * rng.uniform(1.0, 1.6)
        part = m.add(lathe([(s * 0.25, 0.0), (s * 0.18, h * 0.6), (0.0, h)], rng.choice([5, 6]), mat))
        _jitter(m, part, rng, s * 0.04, keep=lambda v: v[2] < 1e-6)
    n_cr = p.int("crystals", 0, 3)
    if n_cr:
        cr = a.part("Crystals")
        for _ in range(n_cr):
            ang = rng.uniform(0, 2 * math.pi)
            dist = s * rng.uniform(0.2, 0.45)
            tilt = (deg(-math.sin(ang) * rng.uniform(15, 40)), deg(math.cos(ang) * rng.uniform(15, 40)), 0.0)
            _crystal(cr, (math.cos(ang) * dist, math.sin(ang) * dist, s * 0.2), s * rng.uniform(0.3, 0.6),
                     s * rng.uniform(0.04, 0.08), tilt)
    a.meta["boulders"] = n


@model("floating_island", "FloatingIsland", "nature", "Floating rock island (walkable top at z = 0): jagged "
       "underside, hanging rocks, optional crystals and glow", pivot="top", params=[
           Param("radius", "float", "Radius (m)", lo=0.8, hi=3.5, size=True, snap_factor=2),
           Param("depth", "float", "Tiefe (m)", lo=0.6, hi=4.0, size=True),
           Param("crystals", "int", "Kristalle", lo=0, hi=10),
           Param("glow", "bool", "Glow-Kante"),
       ])
def floating_island(rng, a):
    p = a.p
    r = p.float("radius", 1.2, 2.4)
    depth = p.float("depth", r * 0.7, r * 1.3)
    sides = rng.choice([7, 8, 9])
    m = a.part("Island")
    top_mat = p.material(["M_Platform", "M_Ground", "M_Wall"])
    profile = [(0.0, -depth), (r * 0.25, -depth * 0.75), (r * 0.6, -depth * 0.4), (r * 0.9, -0.3), (r, -0.12),
               (r, 0.0)]
    roles = ["M_Ground", "M_Ground", "M_Ground", "M_RobotDark", top_mat]
    part = m.add(lathe(profile, sides, roles, cap_top_role=top_mat, angle_offset=rng.uniform(0, math.pi)))
    _jitter(m, part, rng, r * 0.08, keep=lambda v: v[2] > -0.13)  # keep the top flat
    for _ in range(rng.randint(1, 3)):  # small rocks hanging under the island
        ang = rng.uniform(0, 2 * math.pi)
        dist = r * rng.uniform(0.3, 0.7)
        k = r * rng.uniform(0.15, 0.3)
        z = -depth * rng.uniform(0.35, 0.6) - k
        _boulder(rng, m, (math.cos(ang) * dist, math.sin(ang) * dist, z), (k, k, k * 1.2), "M_Ground", flat_bottom=False)
    n = p.int("crystals", 0, 4)
    if n:
        cr = a.part("Crystals")
        for i in range(n):
            ang = rng.uniform(0, 2 * math.pi)
            if i % 2 == 0:  # on the top, near the edge
                dist = r * rng.uniform(0.6, 0.85)
                foot = (math.cos(ang) * dist, math.sin(ang) * dist, -0.05)
                tilt = (deg(-math.sin(ang) * 20), deg(math.cos(ang) * 20), 0.0)
                length = r * rng.uniform(0.3, 0.6)
            else:  # hanging from the underside
                dist = r * rng.uniform(0.2, 0.45)
                foot = (math.cos(ang) * dist, math.sin(ang) * dist, -depth * 0.5)
                tilt = (math.pi + deg(rng.uniform(-15, 15)), deg(rng.uniform(-15, 15)), 0.0)
                length = depth * rng.uniform(0.4, 0.7)
            _crystal(cr, foot, length, r * rng.uniform(0.05, 0.09), tilt)
    if p.bool("glow", 0.4):
        cyl(a.part("Glow"), r * 1.005, 0.04, (0, 0, -0.2), p.glow(), sides=sides)
    a.meta.update({"radius_m": round(r, 3), "depth_m": round(depth, 3)})


@model("hanging_crystals", "HangingCrystals", "nature", "Crystal cluster hanging from the ceiling (mount height) "
       "on a rock base", pivot="wall", view="below", params=[
           Param("mount_height", "float", "Deckenhöhe (m)", lo=2.0, hi=6.0, default=3.0),
           Param("crystals", "int", "Kristalle", lo=1, hi=12),
           Param("length", "float", "Länge (m)", lo=0.3, hi=1.8, size=True),
       ])
def hanging_crystals(rng, a):
    p = a.p
    z = p.value("mount_height", 3.0)
    length = p.float("length", 0.6, 1.2)
    length = min(length, z - 0.4)
    n = p.int("crystals", 3, 7)
    base_r = length * rng.uniform(0.35, 0.5)
    m, cr = a.part("Rock"), a.part("Crystals")
    part = m.add(sphere(1.0, rng.choice([6, 7]), 3, "M_Ground"), loc=(0, 0, z - base_r * 0.3),
                 scale=(base_r, base_r * 0.8, base_r * 0.35))
    _jitter(m, part, rng, base_r * 0.1)
    for vi in part.vertex_indices():  # flat on the ceiling
        x, y, zz = m.verts[vi]
        m.verts[vi] = (x, y, min(zz, z))
    for i in range(n):
        if i == 0:
            foot, ln, tilt = (0.0, 0.0, z - base_r * 0.4), length, (math.pi, 0.0, 0.0)
        else:
            ang = rng.uniform(0, 2 * math.pi)
            dist = base_r * rng.uniform(0.3, 0.7)
            foot = (math.cos(ang) * dist, math.sin(ang) * dist, z - base_r * 0.35)
            ln = length * rng.uniform(0.35, 0.75)
            tilt = (math.pi + deg(math.sin(ang) * rng.uniform(10, 30)), deg(math.cos(ang) * rng.uniform(10, 30)), 0.0)
        _crystal(cr, foot, ln, base_r * rng.uniform(0.12, 0.22), tilt, sides=rng.choice([5, 6]))
    a.meta["crystals"] = n


# The game has no green material: plants are alien - glowing cyan (M_Crystal) or rust orange leaves.
LEAVES = ["M_Crystal", "M_HazardOrange", "M_Crystal", "M_Warning"]


def _leaf(mesh, foot, length, width, yaw, pitch, material):
    """A flat, pointed leaf from ``foot``, pointing out along ``yaw`` and up by ``pitch`` (radians)."""
    tilt = (0.0, math.pi / 2 - pitch, yaw)  # local +Z -> outwards and up
    mid = add_vec(foot, rotated(tilt, (0, 0, length * 0.35)))
    cube(mesh, (width, 0.012, length * 0.7), mid, material, rot=(tilt[0], tilt[1], tilt[2]))
    tip = add_vec(foot, rotated(tilt, (0, 0, length * 0.85)))
    cube(mesh, (width * 0.55, 0.012, length * 0.3), tip, material, rot=tilt)


@model("plant", "Plant", "nature", "Alien potted plant: fern, glowing bulbs or spikes; round, square or no pot",
       params=[
           Param("kind", "choice", "Art", choices=("fern", "bulbs", "spikes")),
           Param("pot", "choice", "Topf", choices=("round", "square", "none")),
           Param("height", "float", "Höhe (m)", lo=0.3, hi=2.5, size=True),
       ])
def plant(rng, a):
    p = a.p
    kind = p.choice("kind", ["fern", "bulbs", "spikes"])
    pot = p.choice("pot", ["round", "square", "round", "none"])
    h = p.float("height", 0.6, 1.4)
    m = a.part("Plant")
    leaf = rng.choice(LEAVES)
    a.meta.update({"kind": kind, "pot": pot, "leaves": leaf})
    pr = max(0.12, h * rng.uniform(0.15, 0.22))
    ph = 0.0
    if pot != "none":
        ph = pr * rng.uniform(1.0, 1.6)
        pmat = p.material(["M_Wall", "M_Platform", "M_RobotDark", "M_HazardOrange"])
        if pot == "round":
            cyl(m, pr * 0.8, ph, (0, 0, ph / 2), pmat, sides=10, radius_top=pr)
            cyl(m, pr * 1.05, 0.05, (0, 0, ph - 0.025), "M_RobotDark", sides=10)
        else:
            cube(m, (pr * 1.8, pr * 1.8, ph), (0, 0, ph / 2), pmat, bevel=0.02)
        cyl(m, pr * 0.95, 0.02, (0, 0, ph), "M_Ground", sides=10)
    else:
        _boulder(rng, m, (0, 0, 0), (pr * 2.2, pr * 2.0, pr * 0.8), rng.choice(ROCK))
        ph = pr * 0.3
    stem_h = h - ph
    if kind == "fern":
        n = rng.randint(7, 12)
        for i in range(n):
            yaw = 2 * math.pi * i / n + rng.uniform(-0.2, 0.2)
            pitch = deg(rng.uniform(25, 70))
            length = stem_h * rng.uniform(0.7, 1.1)
            _leaf(m, (0, 0, ph), length, length * rng.uniform(0.12, 0.2), yaw, pitch, leaf)
    elif kind == "bulbs":
        bulbs = a.part("Lights")
        glow = p.glow_from(["M_GlowCyan", "M_GlowOrange", "M_GlowCyan"])
        for i in range(rng.randint(3, 6)):
            yaw = rng.uniform(0, 2 * math.pi)
            lean = rng.uniform(0.0, 0.35) * stem_h
            top = (math.cos(yaw) * lean, math.sin(yaw) * lean, ph + stem_h * rng.uniform(0.6, 1.0))
            mid = (top[0] * 0.4, top[1] * 0.4, ph + (top[2] - ph) * 0.55)
            strut(m, (0, 0, ph), mid, 0.015 + stem_h * 0.008, "M_RobotDark", sides=5)
            strut(m, mid, top, 0.012 + stem_h * 0.006, "M_RobotDark", sides=5)
            br = stem_h * rng.uniform(0.06, 0.1)
            bulbs.add(sphere(br, 6, 4, glow), loc=(top[0], top[1], top[2] + br * 0.8))
        for i in range(4):
            _leaf(m, (0, 0, ph), stem_h * 0.35, stem_h * 0.08, math.pi / 2 * i + 0.4, deg(20), leaf)
    else:  # spikes: thick cones like an alien succulent
        for i in range(rng.randint(4, 8)):
            yaw = rng.uniform(0, 2 * math.pi)
            dist = pr * rng.uniform(0.0, 0.6)
            length = stem_h * rng.uniform(0.5, 1.0)
            tilt = (deg(-math.sin(yaw) * rng.uniform(5, 30)), deg(math.cos(yaw) * rng.uniform(5, 30)), 0.0)
            foot = (math.cos(yaw) * dist, math.sin(yaw) * dist, ph)
            r = length * rng.uniform(0.08, 0.14)
            cyl(m, r, length, add_vec(foot, rotated(tilt, (0, 0, length / 2))), leaf, sides=6, radius_top=0.0,
                rot=tilt)


@model("hydroponic_bed", "HydroponicBed", "nature", "Hydroponic grow bed: trough on legs, rows of alien plants, "
       "grow lamp (Lights), water pipes", params=[
           Param("length", "float", "Länge (m)", lo=0.8, hi=4.0, size=True),
           Param("tiers", "int", "Ebenen", lo=1, hi=3),
           Param("lamp", "bool", "Pflanzenlampe"),
       ])
def hydroponic_bed(rng, a):
    p = a.p
    length = p.float("length", 1.4, 2.8)
    width = rng.uniform(0.5, 0.8)
    tiers = p.int("tiers", 1, 2)
    frame = p.material(["M_Metal", "M_Platform", "M_Wall"])
    leaf = rng.choice(LEAVES)
    body, plants = a.part("Body"), a.part("Plants")
    lamp = p.bool("lamp", 0.7)
    glow = p.glow_from(["M_GlowOrange", "M_GlowRed", "M_GlowCyan"]) if lamp else None
    spacing = 0.75
    top = 0.35 + tiers * spacing
    for sx in (-1, 1):  # legs
        for sy in (-1, 1):
            cube(body, (0.05, 0.05, top + (0.5 if lamp else 0.0)),
                 (sx * (length / 2 - 0.05), sy * (width / 2 - 0.05), (top + (0.5 if lamp else 0.0)) / 2), frame)
    for t in range(tiers):
        z = 0.35 + t * spacing
        cube(body, (length, width, 0.04), (0, 0, z), frame)
        for sy in (-1, 1):  # trough walls
            cube(body, (length, 0.03, 0.18), (0, sy * (width / 2 - 0.015), z + 0.09), "M_RobotDark")
        for sx in (-1, 1):
            cube(body, (0.03, width, 0.18), (sx * (length / 2 - 0.015), 0, z + 0.09), "M_RobotDark")
        cube(body, (length - 0.06, width - 0.06, 0.1), (0, 0, z + 0.07), "M_Ground")
        rows = 2 if width > 0.6 else 1
        cols = max(2, int(length / 0.3))
        for r in range(rows):
            for c in range(cols):
                x = -length / 2 + 0.15 + c * (length - 0.3) / (cols - 1)
                y = 0.0 if rows == 1 else (r - 0.5) * width * 0.45
                size = rng.uniform(0.12, 0.25)
                for k in range(3):
                    _leaf(plants, (x, y, z + 0.12), size, size * 0.3, rng.uniform(0, 2 * math.pi) + k * 2.1,
                          deg(rng.uniform(35, 70)), leaf)
        if lamp:
            lz = z + spacing * 0.85 if t < tiers - 1 else top + 0.45
            cube(body, (length * 0.9, 0.18, 0.05), (0, 0, lz), "M_RobotDark")
            cube(a.part("Lights"), (length * 0.85, 0.12, 0.02), (0, 0, lz - 0.035), glow)
    cyl(body, 0.035, length, (0, width / 2 + 0.04, 0.3), "M_Metal", sides=8, rot=ALONG_X)  # water pipe
    for t in range(tiers):
        cyl(body, 0.015, 0.2, (length / 2 - 0.2, width / 2 + 0.04, 0.4 + t * spacing), "M_Metal", sides=6)
    a.meta.update({"tiers": tiers, "leaves": leaf})


@model("stalagmite", "Stalagmite", "nature", "Cave formation: stalagmite cluster, floor-to-ceiling column or "
       "crystal-tipped spikes", params=[
           Param("kind", "choice", "Art", choices=("cluster", "column", "crystal")),
           Param("height", "float", "Höhe (m)", lo=0.4, hi=4.0, size=True),
           Param("count", "int", "Spitzen", lo=1, hi=7),
       ])
def stalagmite(rng, a):
    p = a.p
    kind = p.choice("kind", ["cluster", "cluster", "column", "crystal"])
    h = p.float("height", 1.0, 2.2) if kind != "column" else p.value("height", 3.0)
    n = p.int("count", 2, 5)
    m = a.part("Rock")
    mat = p.material(ROCK)
    a.meta["kind"] = kind
    if kind == "column":  # stalagmite meets stalactite
        r = h * rng.uniform(0.12, 0.18)
        neck = rng.uniform(0.4, 0.6)
        profile = [(r, 0.0), (r * 0.7, h * 0.2), (r * 0.3, h * neck), (r * 0.6, h * 0.8), (r * 1.1, h)]
        part = m.add(lathe(profile, rng.choice([6, 7, 8]), mat, cap_bottom=True, cap_top=True))
        _jitter(m, part, rng, r * 0.12, keep=lambda v: v[2] < 1e-6 or v[2] > h - 1e-6)
        _boulder(rng, m, (0, 0, 0), (r * 3, r * 2.6, r * 0.8), rng.choice(ROCK))
        n = 1
    else:
        crystals = a.part("Crystals") if kind == "crystal" else None
        for i in range(n):
            ang = rng.uniform(0, 2 * math.pi)
            dist = 0.0 if i == 0 else h * rng.uniform(0.15, 0.35)
            hh = h if i == 0 else h * rng.uniform(0.3, 0.7)
            r = hh * rng.uniform(0.15, 0.22)
            foot = (math.cos(ang) * dist, math.sin(ang) * dist, 0.0)
            profile = [(r, 0.0), (r * 0.65, hh * 0.4), (r * 0.3, hh * 0.75), (0.0, hh)]
            part = m.add(lathe(profile, rng.choice([5, 6, 7]), mat if i == 0 else rng.choice(ROCK)), loc=foot)
            _jitter(m, part, rng, r * 0.12, keep=lambda v: v[2] < 1e-6)
            if crystals is not None:
                tilt = (deg(rng.uniform(-20, 20)), deg(rng.uniform(-20, 20)), 0.0)
                _crystal(crystals, (foot[0], foot[1], hh * 0.55), hh * rng.uniform(0.3, 0.5), r * 0.35, tilt)
        _boulder(rng, m, (0, 0, 0), (h * 0.5, h * 0.45, h * 0.12), rng.choice(ROCK))
    a.meta["spikes"] = n


@model("mushroom", "Mushroom", "nature", "Cluster of alien mushrooms with glowing gills (Lights), from small "
       "to giant", params=[
           Param("count", "int", "Pilze", lo=1, hi=8),
           Param("height", "float", "Höhe größter (m)", lo=0.2, hi=3.0, size=True),
           Param("spots", "bool", "Punkte auf den Hüten"),
       ])
def mushroom(rng, a):
    p = a.p
    n = p.int("count", 2, 5)
    h = p.float("height", 0.4, 1.6)
    spots = p.bool("spots", 0.5)
    m, gills = a.part("Mushroom"), a.part("Lights")
    cap = rng.choice(["M_HazardOrange", "M_Crystal", "M_Platform", "M_Warning", "M_RobotBody"])
    stem = rng.choice(["M_PortalPanel", "M_Platform", "M_Wall"])
    glow = p.glow_from(["M_GlowCyan", "M_GlowCyan", "M_GlowOrange"])
    for i in range(n):
        ang = rng.uniform(0, 2 * math.pi)
        dist = 0.0 if i == 0 else h * rng.uniform(0.25, 0.6)
        hh = h if i == 0 else h * rng.uniform(0.25, 0.65)
        cr = hh * rng.uniform(0.35, 0.55)
        foot = (math.cos(ang) * dist, math.sin(ang) * dist, 0.0)
        lean = (deg(-math.sin(ang) * rng.uniform(0, 15)), deg(math.cos(ang) * rng.uniform(0, 15)), 0.0)
        top = add_vec(foot, rotated(lean, (0, 0, hh)))
        strut(m, foot, top, cr * 0.22, stem, sides=7, radius_end=cr * 0.16)
        m.add(lathe([(cr, 0.0), (cr * 0.95, cr * 0.2), (cr * 0.6, cr * 0.5), (0.0, cr * 0.62)], 9, cap,
                    cap_bottom=True), loc=(top[0], top[1], top[2] - cr * 0.1), rot=lean)
        cyl(gills, cr * 0.92, cr * 0.1, add_vec(top, rotated(lean, (0, 0, -cr * 0.12))), glow, sides=9,
            radius_top=cr * 0.5, rot=lean)
        if spots:
            for k in range(rng.randint(2, 4)):
                sa = rng.uniform(0, 2 * math.pi)
                sp = add_vec(top, rotated(lean, (math.cos(sa) * cr * 0.55, math.sin(sa) * cr * 0.55, cr * 0.32)))
                cyl(m, cr * 0.09, cr * 0.04, sp, "M_Platform" if cap != "M_Platform" else "M_RobotDark", sides=6,
                    rot=lean)
    a.meta["count"] = n
