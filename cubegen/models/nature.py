"""Nature: rock formations, floating islands and hanging crystals.

Static decoration - goes into Art/Models/Library/Nature. Shapes are jittered
low-poly spheres and cones; the walkable top of a floating island stays flat
at z = 0 like the platforms.
"""

from __future__ import annotations

import math

from ..geometry import lathe, sphere
from ..params import Param
from .common import add_vec, cyl, deg, rotated
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
