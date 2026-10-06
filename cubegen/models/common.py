"""Helpers shared by the model builders (all in asset space, metres, front = -Y)."""

from __future__ import annotations

import math

from ..geometry import Mesh, basis_matrix, box, chamfer_box, cylinder, euler_matrix, mat_mul_vec, v_cross, v_len, \
    v_norm, v_sub
from ..params import DETAIL

ALONG_X = (0.0, math.pi / 2, 0.0)   # rotate a Z cylinder so it runs along X
ALONG_Y = (math.pi / 2, 0.0, 0.0)   # ... along Y (e.g. lenses and wheels facing the front)


def deg(a: float) -> float:
    return math.radians(a)


def cube(mesh: Mesh, size, center, material: str, bevel: float = 0.0, rot=(0.0, 0.0, 0.0)):
    """Box with optional chamfer - the workhorse, like ``MeshBuilder.box`` in the game."""
    if DETAIL.get() == "low":
        bevel = 0.0
    prim = chamfer_box(size[0], size[1], size[2], material, bevel) if bevel > 0 else box(*size, material)
    return mesh.add(prim, loc=center, rot=rot)


def detail_sides(sides: int) -> int:
    """Cylinder sides for the current detail level (low: 3/4, high: 1.5x, always even, >= 6)."""
    level = DETAIL.get()
    if level == "low":
        return max(6, int(round(sides * 0.75 / 2)) * 2) if sides > 6 else sides
    if level == "high":
        return int(round(sides * 1.5 / 2)) * 2
    return sides


def cyl(mesh: Mesh, radius: float, depth: float, center, material: str, sides: int = 8, radius_top=None,
        bevel: float = 0.0, rot=(0.0, 0.0, 0.0)):
    if DETAIL.get() == "low":
        bevel = 0.0
    prim = cylinder(radius, depth, detail_sides(sides), material, radius_top=radius_top, bevel=bevel)
    return mesh.add(prim, loc=center, rot=rot)


def frustum(mesh: Mesh, bottom_size, top_size, z_bottom: float, z_top: float, material: str, center_xy=(0.0, 0.0)):
    """Box that is wider at one end (tapered undersides of platforms)."""
    h = z_top - z_bottom
    prim = box(bottom_size[0], bottom_size[1], h, material,
               top_scale=(top_size[0] / bottom_size[0], top_size[1] / bottom_size[1]))
    return mesh.add(prim, loc=(center_xy[0], center_xy[1], z_bottom + h / 2))


def stripes(mesh: Mesh, length: float, center, along_x: bool = True, count: int = 6, width: float = 0.14,
            height: float = 0.012, material: str = "M_Warning"):
    """Yellow warning stripes as a flat band (only the yellow ones are geometry)."""
    for i in range(count):
        t = -length / 2 + length * (i + 0.5) / count
        pos = (center[0] + (t if along_x else 0), center[1] + (0 if along_x else t), center[2])
        size = (length / count * 0.5, width, height) if along_x else (width, length / count * 0.5, height)
        cube(mesh, size, pos, material)


def rail(mesh: Mesh, length: float, along_x: bool, offset: float, height: float = 1.0, material: str = "M_Metal"):
    """A railing: posts about every metre, a top bar and a middle bar."""
    posts = max(2, int(round(length)) + 1)
    for i in range(posts):
        t = -length / 2 + length * i / (posts - 1)
        pos = (t, offset, height / 2) if along_x else (offset, t, height / 2)
        cube(mesh, (0.07, 0.07, height), pos, material, bevel=0.01)
    for z in (height, height * 0.5):
        size = (length, 0.06, 0.06) if along_x else (0.06, length, 0.06)
        cube(mesh, size, (0, offset, z) if along_x else (offset, 0, z), material, bevel=0.01)


def valve_wheel(mesh: Mesh, center, radius: float = 0.28, rim: str = "M_HazardOrange"):
    """A valve wheel in the XZ plane facing the front (-Y). Make it its own object with pivot = center."""
    cx, cy, cz = center
    cyl(mesh, 0.06, 0.12, center, "M_RobotDark", rot=ALONG_Y)
    n = 10
    for i in range(n):
        a = 2 * math.pi * i / n
        cube(mesh, (2 * math.pi * radius / n * 1.05, 0.05, 0.05),
             (cx + math.cos(a) * radius, cy, cz + math.sin(a) * radius), rim, rot=(0, math.pi / 2 - a, 0))
    for i in range(3):
        a = 2 * math.pi * i / 3
        cube(mesh, (radius, 0.04, 0.04), (cx + math.cos(a) * radius / 2, cy, cz + math.sin(a) * radius / 2),
             "M_Metal", rot=(0, -a, 0))


def fan(mesh: Mesh, center, radius: float, blades: int, material: str = "M_Wall", axis: str = "z", pitch: float = 20):
    """A fan / rotor: hub and pitched blades around ``axis`` (z = horizontal fan, y = facing the front)."""
    cx, cy, cz = center
    hub_rot = (0.0, 0.0, 0.0) if axis == "z" else ALONG_Y
    cyl(mesh, radius * 0.25, radius * 0.25, center, "M_RobotDark", rot=hub_rot)
    for i in range(blades):
        a = 2 * math.pi * i / blades
        if axis == "z":
            pos = (cx + math.cos(a) * radius * 0.55, cy + math.sin(a) * radius * 0.55, cz)
            cube(mesh, (radius * 0.8, radius * 0.28, 0.02), pos, material, rot=(deg(pitch), 0, a))
        else:
            pos = (cx + math.cos(a) * radius * 0.55, cy, cz + math.sin(a) * radius * 0.55)
            cube(mesh, (radius * 0.8, 0.02, radius * 0.28), pos, material, rot=(deg(pitch), -a, 0))


def rotated(rot, v):
    """Vector ``v`` rotated by euler ``rot`` - to place things on tilted parts."""
    return mat_mul_vec(euler_matrix(*rot), v)


def add_vec(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def strut(mesh: Mesh, start, end, radius: float, material: str, sides: int = 6, radius_end=None):
    """Cylinder from point ``start`` to point ``end`` (legs, cables, braces, limbs)."""
    d = v_sub(end, start)
    length = v_len(d)
    if length < 1e-6:
        return None
    z = v_norm(d)
    helper = (0.0, 0.0, 1.0) if abs(z[2]) < 0.9 else (1.0, 0.0, 0.0)
    x = v_norm(v_cross(helper, z))
    y = v_cross(z, x)  # right-handed basis: keeps the normals pointing outwards
    prim = cylinder(radius, length, detail_sides(sides), material, radius_top=radius_end, align_flat=False)
    mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2, (start[2] + end[2]) / 2)
    return mesh.add(prim, loc=mid, basis=basis_matrix(x, y, z))


def gear(mesh: Mesh, center, radius: float, thickness: float, material: str, hub: str = "M_RobotDark",
         phase: float = 0.0) -> int:
    """A gear in the XZ plane facing the front (-Y): disc, teeth on the pitch ``radius`` and a hub.

    Returns the number of teeth (about one per 6 cm of circumference, at least 8).
    """
    cx, cy, cz = center
    teeth = max(8, int(round(2 * math.pi * radius / 0.06 / 2)) * 2)
    tooth = min(0.05, radius * 0.25)
    cyl(mesh, radius - tooth * 0.5, thickness, center, material, sides=max(10, min(teeth, 16)), rot=ALONG_Y)
    for i in range(teeth):
        a = phase + 2 * math.pi * i / teeth
        cube(mesh, (2 * math.pi * radius / teeth * 0.5, thickness, tooth * 1.2),
             (cx + math.cos(a) * radius, cy, cz + math.sin(a) * radius), material, rot=(0, math.pi / 2 - a, 0))
    cyl(mesh, radius * 0.3, thickness * 1.6, center, hub, sides=8, rot=ALONG_Y)
    if radius > 0.12:  # lightening holes as dark plugs on the front
        for i in range(4):
            a = phase + math.pi / 4 + i * math.pi / 2
            hole = (cx + math.cos(a) * radius * 0.58, cy, cz + math.sin(a) * radius * 0.58)
            cyl(mesh, radius * 0.16, thickness * 1.1, hole, hub, sides=6, rot=ALONG_Y)
    return teeth


def flat_wheel(mesh: Mesh, center, radius: float, rim: str = "M_HazardOrange", spokes: int = 3):
    """A valve wheel lying flat (XY plane, axis = Z) - on hatches and tank lids."""
    cx, cy, cz = center
    cyl(mesh, 0.05, 0.08, center, "M_RobotDark", sides=8)
    n = 10
    for i in range(n):
        a = 2 * math.pi * i / n
        cube(mesh, (0.045, 2 * math.pi * radius / n * 1.05, 0.045),
             (cx + math.cos(a) * radius, cy + math.sin(a) * radius, cz), rim, rot=(0, 0, a))
    for i in range(spokes):
        a = 2 * math.pi * i / spokes
        cube(mesh, (radius, 0.035, 0.035), (cx + math.cos(a) * radius / 2, cy + math.sin(a) * radius / 2, cz),
             "M_Metal", rot=(0, 0, a))
