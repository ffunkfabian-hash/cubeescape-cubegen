"""Dressings: geometry a paint scheme cannot give (concepts "Ruin" and "Organic").

A dressing is a parameter ``dressing = none | ruin | organic`` of a model type - never rolled, so every existing
variant stays exactly as it was. It rolls from its own stream (``asset.sub("dressing")``): the builder's rolls stay
untouched. Rules for set pieces (``--set``): a dressing stays inside the type's ``set_faces`` and nothing reaches below
the floor (``on_floor``), otherwise the asset re-pivots and the joint breaks. Visual only: pieces are small (no
collider) - a dressing never blocks a way.
"""

from __future__ import annotations

import math

from ..params import Param
from .alien import _wiggle
from .common import cube, strut
from .nature import _boulder

DRESSINGS = ("none", "ruin", "organic")


def dressing_param(description: str) -> Param:
    # quiet: "none" is not recorded - the sidecar of every existing variant stays as it was
    return Param("dressing", "choice", "Ausstattung", choices=DRESSINGS, default="none", quiet=True,
                 description=description)


def _inside(rng, span, reach):
    """A position in ``span`` (lo, hi) for a piece reaching ``reach`` from its centre: it stays inside the span."""
    lo, hi = span[0] + reach, span[1] - reach
    return rng.uniform(lo, hi) if hi > lo else (span[0] + span[1]) / 2


def on_floor(mesh, part, floor: float = 0.0) -> None:
    """Flatten what a tilted piece pushes below ``floor``: the foot of the model must stay where it is."""
    for vi in part.vertex_indices():
        x, y, z = mesh.verts[vi]
        mesh.verts[vi] = (x, y, max(z, floor))


def rubble(rng, m, xs, ys, z, count, size=(0.05, 0.15), materials=("M_Wall", "M_RobotDark", "M_Metal")) -> None:
    """Broken chunks lying on the plane ``z`` inside ``xs`` x ``ys`` (ranges)."""
    for _ in range(count):
        s = rng.uniform(*size)
        chunk = cube(m, (s * rng.uniform(0.8, 1.5), s * rng.uniform(0.7, 1.2), s * rng.uniform(0.5, 0.9)),
                     (_inside(rng, xs, s), _inside(rng, ys, s), z + s * 0.3), rng.choice(materials),
                     rot=(math.radians(rng.uniform(-30, 30)), math.radians(rng.uniform(-30, 30)),
                          rng.uniform(0, math.pi)))
        on_floor(m, chunk, z)


def torn_plate(rng, m, x, y, z, size=(0.5, 0.7)) -> None:
    """A loose plate leaning on something, flattened onto ``z``."""
    w = rng.uniform(*size)
    plate = cube(m, (w, 0.03, w * 1.2), (x, y, z + w * 0.5), "M_Metal", bevel=0.01,
                 rot=(math.radians(rng.uniform(14, 24)), 0.0, math.radians(rng.uniform(-20, 20))))
    on_floor(m, plate, z)


def stones(rng, m, xs, ys, z, count, size=(0.12, 0.28), material="M_Wall") -> None:
    for _ in range(count):
        s = rng.uniform(*size)
        on_floor(m, _boulder(rng, m, (_inside(rng, xs, s * 0.8), _inside(rng, ys, s * 0.8), z), (s * 1.3, s, s * 0.7),
                             material), z)


def tufts(rng, m, xs, ys, z, count, height=(0.18, 0.3)) -> None:
    """Bushes / grass tufts: rotated blades in the ground material (a paint scheme colours them)."""
    for _ in range(count):
        bx, by = _inside(rng, xs, 0.2), _inside(rng, ys, 0.2)
        for _ in range(rng.randint(5, 8)):
            yaw, hb = rng.uniform(0, 2 * math.pi), rng.uniform(*height)
            blade = cube(m, (0.06, 0.012, hb), (bx + math.cos(yaw) * 0.06, by + math.sin(yaw) * 0.06, z + hb / 2),
                         "M_Ground", rot=(math.radians(rng.uniform(-35, 35)), math.radians(rng.uniform(-35, 35)), yaw))
            on_floor(m, blade, z)


def moss_pads(rng, m, xs, ys, z, count, size=(0.15, 0.45)) -> None:
    """Flat moss cushions lying on ``z`` (4 mm above it: no shared plane with the surface below)."""
    for _ in range(count):
        s = rng.uniform(*size)
        pad = _boulder(rng, m, (_inside(rng, xs, s * 0.6), _inside(rng, ys, s * 0.6), z + 0.004),
                       (s, s * rng.uniform(0.6, 1.0), 0.06), "M_Ground")
        on_floor(m, pad, z + 0.004)


def hanging_vines(rng, m, xs, y, z_top, count, drop=(4, 9), floor=0.3, leaves=0.75) -> None:
    """Vines hanging down from ``z_top`` at depth ``y``, clamped to ``xs`` (they never cross a joint), with leaves."""
    lo, hi = xs
    for _ in range(count):
        steps = rng.randint(*drop)
        pts = [(max(lo, min(hi, x)), py, pz)
               for x, py, pz in _wiggle(rng, (rng.uniform(lo, hi), y, z_top), -0.28, steps, 0.1, floor=floor)]
        for k, (p1, p2) in enumerate(zip(pts, pts[1:])):
            strut(m, p1, p2, 0.022 * (1 - k / (steps + 1)) + 0.008, "M_Ground", sides=5)
            if rng.random() < leaves:
                ang = rng.uniform(-60, 60)
                lx = max(lo + 0.07, min(hi - 0.07, p2[0] + 0.05 * (1 if ang > 0 else -1)))
                cube(m, (0.13, 0.012, 0.07), (lx, p2[1] - 0.01, p2[2]), "M_Ground", rot=(0.0, math.radians(ang), 0.0))


def sagging_cable(m, start, end, sag, radius=0.018, material="M_RobotDark", segments=6) -> None:
    """A cable hanging between two points (parabola, ``sag`` metres at the middle)."""
    pts = []
    for i in range(segments + 1):
        t = i / segments
        pts.append(tuple(start[k] + (end[k] - start[k]) * t for k in range(3)))
        pts[-1] = (pts[-1][0], pts[-1][1], pts[-1][2] - sag * 4 * t * (1 - t))
    for p1, p2 in zip(pts, pts[1:]):
        strut(m, p1, p2, radius, material, sides=5)


def dangling_cable(rng, m, top, length, radius=0.016, material="M_RobotDark") -> None:
    """A torn cable end hanging down from ``top`` with a little sway."""
    x, y, z = top
    pts = [top]
    for k in range(1, 4):
        pts.append((x + rng.uniform(-0.06, 0.06), y + rng.uniform(-0.04, 0.04), z - length * k / 3))
    for p1, p2 in zip(pts, pts[1:]):
        strut(m, p1, p2, radius, material, sides=5)
    cube(m, (0.05, 0.05, 0.06), (pts[-1][0], pts[-1][1], pts[-1][2] - 0.03), "M_Metal")  # plug / torn end


# --------------------------------------------------------------------------
# dressings of the build-kit types (each stays inside the type's set_faces)
# --------------------------------------------------------------------------

def dress_floor(a, m, size, kind) -> None:
    """Floor tile (top at z = 0): rubble and a loose plate / moss, stones and tufts - 12 cm clear of the joints."""
    if kind == "none":
        return
    rng, lim = a.sub("dressing"), size / 2 - 0.12
    xs = ys = (-lim, lim)
    k = {1.0: 1, 2.0: 2}.get(size, 3)  # more on larger tiles, within the triangle budget
    if kind == "ruin":
        rubble(rng, m, xs, ys, 0.0, rng.randint(4, 8) * k)
        if rng.random() < 0.6:
            torn_plate(rng, m, rng.uniform(-lim + 0.35, lim - 0.35), rng.uniform(-lim + 0.35, lim - 0.35), 0.0,
                       size=(0.3, min(0.6, size * 0.3)))
    else:
        moss_pads(rng, m, xs, ys, 0.0, rng.randint(2, 3) * k)
        stones(rng, m, xs, ys, 0.0, rng.randint(0, 2) + k // 2, size=(0.1, 0.2))
        tufts(rng, m, xs, ys, 0.0, rng.randint(1, 2) * k, height=(0.08, 0.16))  # low: grass on a walkway
    a.meta["dressing"] = kind


def dress_catwalk(a, m, length, width, kind) -> None:
    """Catwalk (deck top at z = 0, joins at x = +-length/2): cables or vines hang below the deck."""
    if kind == "none":
        return
    rng, lim = a.sub("dressing"), length / 2 - 0.15
    if kind == "ruin":
        for _ in range(rng.randint(2, 3)):  # cables sagging along the underside
            y = rng.uniform(-width / 2 + 0.1, width / 2 - 0.1)
            x0 = rng.uniform(-lim, -lim / 3)
            x1 = rng.uniform(lim / 3, lim)
            sagging_cable(m, (x0, y, -0.2), (x1, y, -0.2), rng.uniform(0.15, 0.5))
        for _ in range(rng.randint(1, 3)):  # torn ends
            dangling_cable(rng, m, (rng.uniform(-lim, lim), rng.choice((-1, 1)) * (width / 2 - 0.06), -0.2),
                           rng.uniform(0.4, 1.1))
    else:
        for s in (-1, 1):  # vines over both edges (nothing on the deck: its top joins the next segment)
            hanging_vines(rng, m, (-lim, lim), s * (width / 2 + 0.02), -0.12, rng.randint(1, 3), drop=(3, 6),
                          floor=-2.5)
    a.meta["dressing"] = kind


def dress_pillar(a, m, w, h, kind) -> None:
    """Pillar (foot at z = 0, cap w + 0.15 wide): vines from under the cap, stones / rubble at the foot in front."""
    if kind == "none":
        return
    rng, half = a.sub("dressing"), w / 2 + 0.05
    if kind == "ruin":
        rubble(rng, m, (-half, half), (-w / 2 - 0.45, -w / 2 - 0.1), 0.0, rng.randint(5, 9))
        for _ in range(rng.randint(2, 4)):  # bent rebar out of a chipped edge
            x, z = rng.uniform(-w / 2 + 0.05, w / 2 - 0.05), rng.uniform(0.4, h - 0.6)
            strut(m, (x, -w / 2 + 0.02, z), (x + rng.uniform(-0.08, 0.08), -w / 2 - rng.uniform(0.12, 0.25),
                                              z + rng.uniform(-0.15, 0.1)), 0.012, "M_Metal", sides=4)
        dangling_cable(rng, m, (rng.uniform(-w / 3, w / 3), -w / 2 - 0.04, h - 0.25), rng.uniform(0.5, 1.2))
    else:
        for y in (-w / 2 - 0.03,):
            hanging_vines(rng, m, (-w / 2 + 0.03, w / 2 - 0.03), y, h - 0.24, rng.randint(2, 4), floor=0.4)
        stones(rng, m, (-half + 0.08, half - 0.08), (-w / 2 - 0.4, -w / 2 - 0.12), 0.0, rng.randint(1, 3),
               size=(0.1, min(0.24, half)))
        tufts(rng, m, (-half + 0.05, half - 0.05), (-w / 2 - 0.35, -w / 2 - 0.1), 0.0, rng.randint(1, 3))
    a.meta["dressing"] = kind
