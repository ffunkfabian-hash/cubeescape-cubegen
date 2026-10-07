"""Ruins: rubble piles, scrap heaps, broken walls, fallen pillars, girders, crate piles, cable mess.

All static decoration (no game scripts) - put them into Art/Models/Library/Ruins.
"""

from __future__ import annotations

import math

from ..geometry import prism, sphere
from ..params import Param
from .common import add_vec, cube, cyl, deg, rotated
from .registry import model

CHUNK_MATS = ["M_Wall", "M_Ground", "M_RobotDark", "M_Wall", "M_Metal"]


def _jitter(mesh, part, rng, amount):
    for vi in part.vertex_indices():
        x, y, z = mesh.verts[vi]
        mesh.verts[vi] = (x + rng.uniform(-amount, amount), y + rng.uniform(-amount, amount),
                          z + rng.uniform(-amount, amount))


def _mound(rng, a, mesh, radius, height, material="M_Ground"):
    """Low jagged hill that fills the gaps under a pile."""
    part = mesh.add(sphere(1.0, rng.randint(6, 8), 3, material), loc=(0, 0, 0),
                    scale=(radius, radius * rng.uniform(0.75, 1.0), height))
    _jitter(mesh, part, rng, min(radius, height) * 0.15)
    for vi in part.vertex_indices():  # flat underside on the floor
        x, y, z = mesh.verts[vi]
        mesh.verts[vi] = (x, y, max(z, 0.0))


def _chunks(rng, a, mesh, count, radius, height, size):
    for _ in range(count):
        r = radius * math.sqrt(rng.random())
        ang = rng.uniform(0, 2 * math.pi)
        s = size * rng.uniform(0.5, 1.3)
        z = max(0.0, height * (1 - r / radius)) * rng.uniform(0.5, 0.95)
        cube(mesh, (s * rng.uniform(0.7, 1.4), s * rng.uniform(0.6, 1.2), s * rng.uniform(0.4, 0.9)),
             (math.cos(ang) * r, math.sin(ang) * r, z + s * 0.2), a.p.material(CHUNK_MATS),
             rot=(deg(rng.uniform(-35, 35)), deg(rng.uniform(-35, 35)), rng.uniform(0, 2 * math.pi)))


def _rebar(rng, mesh, count, radius, height):
    for _ in range(count):
        ang = rng.uniform(0, 2 * math.pi)
        r = radius * rng.uniform(0.1, 0.6)
        ln = height * rng.uniform(0.5, 1.1)
        base = (math.cos(ang) * r, math.sin(ang) * r, height * (1 - r / radius) * 0.6)
        tilt = (deg(rng.uniform(-50, 50)), deg(rng.uniform(-50, 50)), 0)
        cyl(mesh, 0.015, ln, (base[0], base[1], base[2] + ln * 0.3), "M_Metal", sides=4, rot=tilt)


def _cable(rng, mesh, start, segments, step, thickness=0.035, material="M_RobotDark"):
    """A cable lying on the floor: a random walk of short cylinders. Returns the end point."""
    x, y = start
    heading = rng.uniform(0, 2 * math.pi)
    for _ in range(segments):
        heading += rng.uniform(-0.8, 0.8)
        dx, dy = math.cos(heading) * step, math.sin(heading) * step
        cyl(mesh, thickness, step * 1.08, (x + dx / 2, y + dy / 2, thickness), material, sides=5,
            rot=(0, math.pi / 2, heading))
        x, y = x + dx, y + dy
    return x, y


@model("rubble_pile", "RubblePile", "ruins", "Schutthaufen: Brocken, Platten, Bewehrungsstahl, Kabel", params=[
    Param("radius", "float", "Radius (m)", lo=0.3, hi=5.0, size=True, snap_factor=2),
    Param("height", "float", "Höhe (m)", lo=0.2, hi=3.0, size=True),
    Param("chunks", "int", "Brocken", lo=3, hi=60),
    Param("plates", "bool", "Platten"),
    Param("rebar", "bool", "Bewehrungsstahl"),
    Param("cable", "bool", "Kabel"),
])
def rubble_pile(rng, a):
    p = a.p
    radius = p.float("radius", 0.8, 2.2)
    height = p.float("height", radius * 0.35, radius * 0.7)
    m = a.part("Rubble")
    _mound(rng, a, m, radius * 0.85, height * 0.7)
    _chunks(rng, a, m, p.int("chunks", 10, 24), radius, height, radius * 0.22)
    if p.bool("plates", 0.7):
        for _ in range(rng.randint(1, 3)):
            ang = rng.uniform(0, 2 * math.pi)
            r = radius * rng.uniform(0.3, 0.8)
            cube(m, (radius * 0.6, radius * 0.4, 0.05), (math.cos(ang) * r, math.sin(ang) * r, height * 0.35),
                 rng.choice(["M_Platform", "M_Metal", "M_Wall"]),
                 rot=(deg(rng.uniform(-40, 40)), deg(rng.uniform(-40, 40)), ang))
    if p.bool("rebar", 0.6):
        _rebar(rng, m, rng.randint(2, 6), radius, height)
    if p.bool("cable", 0.4):
        _cable(rng, m, (radius * 0.6, 0.0), rng.randint(4, 8), radius * 0.25, material="M_HazardOrange")


@model("scrap_heap", "ScrapHeap", "ruins", "Schrotthaufen: Rohrstücke, Zahnräder, Gehäuse, Platten", params=[
    Param("radius", "float", "Radius (m)", lo=0.3, hi=5.0, size=True, snap_factor=2),
    Param("height", "float", "Höhe (m)", lo=0.2, hi=3.0, size=True),
    Param("pieces", "int", "Teile", lo=3, hi=50),
    Param("gears", "bool", "Zahnräder"),
])
def scrap_heap(rng, a):
    p = a.p
    radius = p.float("radius", 0.7, 2.0)
    height = p.float("height", radius * 0.35, radius * 0.6)
    m = a.part("Scrap")
    _mound(rng, a, m, radius * 0.8, height * 0.6, "M_RobotDark")
    for _ in range(p.int("pieces", 8, 18)):
        r = radius * math.sqrt(rng.random())
        ang = rng.uniform(0, 2 * math.pi)
        x, y = math.cos(ang) * r, math.sin(ang) * r
        z = max(0.0, height * (1 - r / radius)) * rng.uniform(0.4, 0.9)
        rot = (deg(rng.uniform(-40, 40)), deg(rng.uniform(-40, 40)), rng.uniform(0, 2 * math.pi))
        kind = rng.random()
        s = radius * rng.uniform(0.12, 0.3)
        if kind < 0.35:      # pipe piece
            cyl(m, s * 0.25, s * 2.2, (x, y, z + s * 0.25), rng.choice(["M_Metal", "M_Wall"]), sides=8, rot=rot)
        elif kind < 0.65:    # housing / box
            cube(m, (s * 1.2, s, s * 0.8), (x, y, z + s * 0.4), a.p.material(["M_Wall", "M_Metal", "M_RobotDark"]),
                 bevel=0.01, rot=rot)
        else:                # plate
            cube(m, (s * 1.8, s * 1.2, 0.04), (x, y, z + 0.05), rng.choice(["M_Platform", "M_Metal", "M_HazardOrange"]),
                 rot=rot)
    if p.bool("gears", 0.6):
        for _ in range(rng.randint(1, 2)):
            gr = radius * rng.uniform(0.15, 0.25)
            ang = rng.uniform(0, 2 * math.pi)
            c = (math.cos(ang) * radius * 0.4, math.sin(ang) * radius * 0.4, height * 0.5)
            tilt = (deg(rng.uniform(40, 80)), 0, ang)
            cyl(m, gr, gr * 0.3, c, "M_Metal", sides=10, rot=tilt)
            for i in range(10):
                t = 2 * math.pi * i / 10
                tooth = add_vec(c, rotated(tilt, (math.cos(t) * gr * 1.1, math.sin(t) * gr * 1.1, 0)))
                cube(m, (gr * 0.25, gr * 0.25, gr * 0.3), tooth, "M_Metal", rot=(tilt[0], tilt[1], tilt[2] + t))


@model("broken_wall", "BrokenWall", "ruins", "Zerstörtes Wandstück: gezackte Oberkante, Loch, Bewehrung, Schutt",
       params=[
           Param("length", "choice", "Länge (m)", choices=(2.0, 4.0)),
           Param("remaining", "float", "Resthöhe (Anteil von 3 m)", lo=0.1, hi=1.0),
           Param("hole", "bool", "Loch"),
           Param("rebar", "bool", "Bewehrungsstahl"),
       ])
def broken_wall(rng, a):
    p = a.p
    length = p.choice("length", [2.0, 4.0, 4.0])
    keep = p.float("remaining", 0.3, 0.8)
    m = a.part("Wall")
    slab = 0.5
    n = int(length / slab)
    hole = p.bool("hole", 0.4)
    hole_slab = rng.randrange(n) if hole else -1
    base_h = 3.0 * keep
    for i in range(n):
        x = -length / 2 + slab * (i + 0.5)
        h = max(0.3, base_h * rng.uniform(0.55, 1.15) - abs(i - n / 2) * rng.uniform(0.0, 0.25))
        h = min(h, 3.0)
        if i == hole_slab:
            cube(m, (slab, 0.5, 0.4), (x, 0, 0.2), "M_Wall")
            if h > 1.6:
                cube(m, (slab, 0.5, h - 1.5), (x, 0, 1.5 + (h - 1.5) / 2), "M_Wall")
        else:
            part = cube(m, (slab, 0.5, h), (x, 0, h / 2), "M_Wall")
            for vi in part.vertex_indices():  # jagged top edge
                vx, vy, vz = m.verts[vi]
                if vz > h - 1e-6:
                    m.verts[vi] = (vx, vy, vz - rng.uniform(0.0, min(0.25, h * 0.3)))
            for fi in part.face_indices():
                if all(m.verts[v][2] > 0.3 for v in m.faces[fi]) and m.face_normal(fi)[2] > 0.3:
                    m.roles[fi] = "M_Ground"  # fracture surface
            if h > 1.0 and rng.random() < 0.5:  # panel remains on the front
                cube(m, (slab * 0.85, 0.04, min(1.4, h - 0.5)), (x, -0.27, 0.35 + min(1.4, h - 0.5) / 2), "M_Ground")
    cube(m, (length, 0.56, 0.25), (0, 0, 0.125), "M_RobotDark", bevel=0.01)
    if p.bool("rebar", 0.7):
        for _ in range(rng.randint(3, 8)):
            x = rng.uniform(-length / 2 + 0.1, length / 2 - 0.1)
            ln = rng.uniform(0.3, 0.8)
            cyl(m, 0.012, ln, (x, rng.uniform(-0.15, 0.15), base_h * 0.8 + ln * 0.3), "M_Metal", sides=4,
                rot=(deg(rng.uniform(-40, 40)), deg(rng.uniform(-40, 40)), 0))
    _chunks(rng, a, a.part("Rubble"), rng.randint(5, 12), length * 0.55, 0.3, 0.25)
    a.meta.update({"length_m": length, "hole": hole})


@model("fallen_pillar", "FallenPillar", "ruins", "Umgestürzte Säule in Stücken, mit Stumpf und Brocken", params=[
    Param("width", "float", "Breite (m)", lo=0.2, hi=2.0, size=True),
    Param("segments", "int", "Bruchstücke", lo=1, hi=5),
    Param("stump", "bool", "Stumpf steht noch"),
])
def fallen_pillar(rng, a):
    p = a.p
    w = p.float("width", 0.4, 1.0)
    mat = p.material(["M_Wall", "M_Metal"])
    m = a.part("Pillar")
    heading = rng.uniform(0, 2 * math.pi)
    x, y = 0.0, 0.0
    if p.bool("stump", 0.7):
        sh = rng.uniform(0.4, 1.2)
        cube(m, (w + 0.15, w + 0.15, 0.25), (0, 0, 0.125), "M_RobotDark", bevel=0.02)
        part = cube(m, (w, w, sh), (0, 0, sh / 2), mat)
        for vi in part.vertex_indices():
            vx, vy, vz = m.verts[vi]
            if vz > sh - 1e-6:
                m.verts[vi] = (vx, vy, vz - rng.uniform(0, w * 0.4))
        x, y = math.cos(heading) * w, math.sin(heading) * w
    for i in range(p.int("segments", 2, 3)):
        ln = rng.uniform(0.6, 1.4)
        yaw = heading + rng.uniform(-0.35, 0.35)
        cx, cy = x + math.cos(yaw) * ln / 2, y + math.sin(yaw) * ln / 2
        # lying on its side: the pillar's long axis is horizontal
        cube(m, (ln, w, w), (cx, cy, w / 2), mat, rot=(rng.uniform(-0.2, 0.2), 0, yaw))
        if i == 0 and rng.random() < 0.6:
            cube(m, (0.2, w + 0.15, w + 0.15), (x + math.cos(yaw) * 0.1, y + math.sin(yaw) * 0.1, (w + 0.15) / 2),
                 "M_RobotDark", rot=(0, 0, yaw))
        x, y = cx + math.cos(yaw) * (ln / 2 + 0.15), cy + math.sin(yaw) * (ln / 2 + 0.15)
    _chunks(rng, a, a.part("Rubble"), rng.randint(3, 8), w * 2.0, 0.2, w * 0.3)


@model("girders", "Girders", "ruins", "Eingestürzte Stahlträger (I-Profil), gekreuzt am Boden", params=[
    Param("count", "int", "Träger", lo=1, hi=8),
    Param("length", "float", "Länge (m)", lo=0.5, hi=8.0, size=True),
])
def girders(rng, a):
    p = a.p
    m = a.part("Girders")
    n = p.int("count", 2, 4)
    length = p.float("length", 1.5, 4.0)
    h, fw, t = 0.24, 0.16, 0.025
    profile = [(-fw / 2, 0), (fw / 2, 0), (fw / 2, t), (t / 2, t), (t / 2, h - t), (fw / 2, h - t), (fw / 2, h),
               (-fw / 2, h), (-fw / 2, h - t), (-t / 2, h - t), (-t / 2, t), (-fw / 2, t)]
    for i in range(n):
        yaw = rng.uniform(0, math.pi)
        lean = deg(rng.uniform(0, 12)) if i else 0.0
        ln = length * rng.uniform(0.7, 1.0)
        mat = rng.choice(["M_Metal", "M_RobotDark", "M_HazardOrange"])
        # I-profile drawn in the YZ plane, extruded along X, then turned to its heading
        m.add(prism([(py, pz) for py, pz in profile], ln, mat),
              loc=(rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), h * 0.5 * i),
              basis=((0, 0, 1), (1, 0, 0), (0, 1, 0)), rot=(lean, 0, yaw))
    _chunks(rng, a, a.part("Rubble"), rng.randint(2, 6), length * 0.5, 0.15, 0.15)


@model("crate_pile", "CratePile", "ruins", "Umgekippte und aufgebrochene Kisten", params=[
    Param("count", "int", "Kisten", lo=1, hi=12),
    Param("broken", "bool", "Eine Kiste aufgebrochen"),
])
def crate_pile(rng, a):
    p = a.p
    m = a.part("Crates")
    n = p.int("count", 3, 6)
    placed = []
    for i in range(n):
        s = rng.uniform(0.5, 0.9)
        if placed and rng.random() < 0.4:  # on top of an earlier crate, tilted
            bx, by, bz, bs = rng.choice(placed)
            x, y, z = bx + rng.uniform(-0.2, 0.2), by + rng.uniform(-0.2, 0.2), bz + bs / 2 + s / 2
            rot = (deg(rng.uniform(-12, 12)), deg(rng.uniform(-12, 12)), rng.uniform(0, 2 * math.pi))
        else:
            ang = rng.uniform(0, 2 * math.pi)
            r = rng.uniform(0.0, 1.2)
            x, y, z = math.cos(ang) * r, math.sin(ang) * r, s / 2
            rot = (0, deg(rng.choice([0, 0, 90])), rng.uniform(0, 2 * math.pi))
        body = a.p.material(["M_RobotDark", "M_Wall", "M_Metal"])
        cube(m, (s, s, s), (x, y, z), body, bevel=0.03, rot=rot)
        cube(m, (s * 1.04, s * 1.04, s * 0.12), (x, y, z), "M_RobotDark" if body != "M_RobotDark" else "M_Metal",
             rot=rot)
        placed.append((x, y, z, s))
    if p.bool("broken", 0.6):  # an opened crate: walls lying flat around it
        x, y = rng.uniform(1.0, 1.6), rng.uniform(-0.5, 0.5)
        s = rng.uniform(0.6, 0.8)
        cube(m, (s, s, 0.05), (x, y, 0.025), "M_Wall")
        for k in range(rng.randint(2, 4)):
            ang = math.pi / 2 * k
            cube(m, (s, 0.05, s * 0.9), (x + math.cos(ang) * s * 0.75, y + math.sin(ang) * s * 0.75, 0.04),
                 "M_Wall", rot=(deg(80), 0, ang + math.pi / 2))
        cube(m, (s * 0.3, s * 0.2, s * 0.2), (x, y, 0.15), "M_HazardOrange", rot=(0, 0, rng.uniform(0, 3)))


@model("cable_mess", "CableMess", "ruins", "Kabelsalat am Boden, optional mit Funken (Glow)", params=[
    Param("cables", "int", "Kabel", lo=1, hi=12),
    Param("sparks", "bool", "Funkende Enden (Glow)"),
])
def cable_mess(rng, a):
    p = a.p
    m = a.part("Cables")
    ends = []
    for _ in range(p.int("cables", 3, 6)):
        start = (rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5))
        mat = rng.choice(["M_RobotDark", "M_RobotDark", "M_HazardOrange", "M_Warning"])
        ends.append(_cable(rng, m, start, rng.randint(4, 10), rng.uniform(0.15, 0.3), rng.uniform(0.02, 0.045), mat))
    cube(m, (0.4, 0.3, 0.25), (0, 0, 0.125), "M_RobotDark", bevel=0.02)  # the junction box they come from
    if p.bool("sparks", 0.6):
        glow = a.part("Glow")
        for x, y in ends[: rng.randint(1, len(ends))]:
            cyl(glow, 0.04, 0.08, (x, y, 0.06), "M_GlowOrange", sides=6, radius_top=0.0)
        a.meta["sparks"] = True

