"""Damaged / destroyed variants of any model (global style ``damage``).

Uses its own random stream (derived from the asset seed), so the destroyed
version of seed 42 is always the ruin of the intact seed 42.

* ``damaged``   - dents, a few small parts knocked off onto the floor, some dead
                  decoration LEDs; the asset keeps working (scripts stay)
* ``destroyed`` - a jagged break line: everything above it is cut off, loose pieces
                  lie on the floor (or are gone), fracture faces, all lights dead,
                  rubble around it. The asset becomes static decoration (no scripts).
"""

from __future__ import annotations

import math
from ..geometry import euler_matrix, mat_mul_vec
from ..seeds import StableRandom
from .wear import apply_wear

LIGHT_PARTS = ("Glow", "Lights", "Screen", "StatusLight_Front", "StatusLight_Back", "Crystals")
GLOW = {"M_GlowCyan", "M_GlowRed", "M_GlowOrange", "M_Crystal"}
DEAD = "M_RobotDark"
FRACTURE = "M_Ground"


def _parts(asset):
    for obj in asset.meshes():
        for part in list(obj.mesh.parts):
            yield obj, part


def _dent(mesh, part, rng, strength):
    (x0, y0, z0), (x1, y1, z1) = mesh.part_bbox(part)
    amount = min(x1 - x0, y1 - y0, z1 - z0) * strength
    before = mesh.verts[part.v0:part.v1]
    for vi in part.vertex_indices():
        x, y, z = mesh.verts[vi]
        mesh.verts[vi] = (x + rng.uniform(-amount, amount), y + rng.uniform(-amount, amount),
                          z + rng.uniform(-amount, amount))
    if part.closed and mesh.part_volume(part) <= 0:  # thin, tilted parts can turn inside out: keep them intact
        mesh.verts[part.v0:part.v1] = before


def _drop(mesh, part, rng, footprint):
    """Rotate a part around its centre and put it on the floor next to the model."""
    (x0, y0, z0), (x1, y1, z1) = mesh.part_bbox(part)
    c = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    # long pieces fall over: if the part is tallest upright, lay it down first, then a slight tilt
    lay = math.pi / 2 if (z1 - z0) > max(x1 - x0, y1 - y0) else 0.0
    rot = euler_matrix(lay + rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), rng.uniform(0, 2 * math.pi))
    pts = [mat_mul_vec(rot, (v[0] - c[0], v[1] - c[1], v[2] - c[2])) for v in mesh.verts[part.v0:part.v1]]
    (fx0, fy0), (fx1, fy1) = footprint
    ang = rng.uniform(0, 2 * math.pi)
    rx, ry = (fx1 - fx0) / 2, (fy1 - fy0) / 2
    reach = rng.uniform(0.6, 1.25)
    tx, ty = (fx0 + fx1) / 2 + math.cos(ang) * rx * reach, (fy0 + fy1) / 2 + math.sin(ang) * ry * reach
    zmin = min(p[2] for p in pts)
    for i, p in zip(part.vertex_indices(), pts):
        mesh.verts[i] = (p[0] + tx, p[1] + ty, p[2] - zmin)


def _kill_lights(asset, rng, share):
    for obj in asset.meshes():
        mesh = obj.mesh
        if obj.name in LIGHT_PARTS and share >= 1.0:
            mesh.roles = [DEAD if r in GLOW else r for r in mesh.roles]
            continue
        for part in mesh.parts:
            if rng.random() < share:
                for fi in part.face_indices():
                    if mesh.roles[fi] in GLOW:
                        mesh.roles[fi] = DEAD


def damage_asset(asset, seed: int, level: str, pivot: str) -> None:
    if level == "intact":
        return
    rng = StableRandom(seed ^ 0xD35)
    (x0, y0, z0), (x1, y1, z1) = asset.bbox()
    footprint = ((x0, y0), (x1, y1))
    total = max((x1 - x0) * (y1 - y0) * (z1 - z0), 1e-6)

    if level == "damaged":
        for obj, part in _parts(asset):
            mesh = obj.mesh
            (px0, py0, pz0), (px1, py1, pz1) = mesh.part_bbox(part)
            small = (px1 - px0) * (py1 - py0) * (pz1 - pz0) < total * 0.02
            if small and pivot in ("floor", "wall") and rng.random() < 0.15 and len(mesh.parts) > 1:
                _drop(mesh, part, rng, footprint)
            elif rng.random() < 0.3:
                _dent(mesh, part, rng, 0.06)
        for obj in asset.meshes():  # decoration LEDs only - status parts must keep one material
            if obj.name == "Lights":
                for part in obj.mesh.parts:
                    if rng.random() < 0.3:
                        for fi in part.face_indices():
                            obj.mesh.roles[fi] = DEAD
        if pivot == "floor":
            apply_wear(asset, seed, "light")
        asset.meta["damage"] = "damaged"
        return

    # destroyed: jagged break line
    axis = 0 if pivot == "top" else 2          # platforms break sideways, everything else from the top
    lo, hi = (x0, x1) if axis == 0 else (z0, z1)
    span = hi - lo
    h0 = rng.uniform(0.35, 0.6)
    f1, f2 = rng.uniform(1.5, 4.0), rng.uniform(1.5, 4.0)
    ph1, ph2 = rng.uniform(0, 6.3), rng.uniform(0, 6.3)
    tilt = rng.uniform(-0.25, 0.25)

    def cut(x, y, z):
        a, b = (y, z) if axis == 0 else (x, y)
        return lo + span * (h0 + 0.08 * (math.sin(a * f1 + ph1) + math.sin(b * f2 + ph2)) / 2) + tilt * a * 0.3

    for obj in asset.meshes():
        mesh = obj.mesh
        remove = []
        for part in list(mesh.parts):
            idx = list(part.vertex_indices())
            above = [i for i in idx if mesh.verts[i][axis] > cut(*mesh.verts[i])]
            if not above:
                continue
            if len(above) == len(idx):          # completely above the break: falls down or is gone
                if axis == 2 and rng.random() < 0.55:
                    _drop(mesh, part, rng, footprint)
                else:
                    remove.append(part)
                continue
            for i in above:                      # partly above: broken off along the jagged line
                v = list(mesh.verts[i])
                v[axis] = cut(*v) - rng.uniform(0.0, span * 0.03)
                mesh.verts[i] = tuple(v)
            clamped = set(above)
            for fi in part.face_indices():       # fracture faces
                if all(vi in clamped for vi in mesh.faces[fi]) and mesh.roles[fi] not in GLOW:
                    mesh.roles[fi] = FRACTURE
            if mesh.part_volume(part) <= 1e-9:   # squashed flat -> gone
                remove.append(part)
        if remove:
            mesh.remove_parts(remove)
    asset.prune()
    _kill_lights(asset, rng, 1.0)
    asset.behaviours = []                        # a ruin does nothing: static decoration
    if pivot in ("floor", "wall"):
        apply_wear(asset, seed ^ 0x77, "heavy")
    asset.meta["damage"] = "destroyed"
