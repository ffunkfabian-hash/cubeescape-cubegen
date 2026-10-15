"""Paint zones from part names (0.30.0, TECHNIK.md 3).

A zone is a group of mesh objects that belong together visually: ``Frame_Left``/``Frame_Right``/``Frame_Top`` are the
zone ``Frame``, ``Leg_1``..``Leg_4`` the zone ``Leg``. A scheme that wants a second colour exactly on such a group
(door frame, rotor blades, status lights) reads the table from the manifest (``zones``); nothing about the zone enters
the sidecar, the geometry or the baked maps - a zone *map* needs a new channel in the Unity contract and a shader in
Cube Escape (ROADMAP ToDo 27), which this version does not touch.

Pure Python; the table depends only on the asset's object names and face materials, so it is part of no cache key.

Since 0.30.0 (contract version 4) a *zone map* goes with ``--paint``: ``MTN_<model>_Zones.png`` holds the weights of up
to three zones (``paint_zones``: R, G, B, alpha 1) rasterised from the atlas UVs (``zone_map``, numpy, no Cycles pass:
hard 0/1 weights, exact at zone borders), and the sidecar's ``textures.zones`` names the slots. What the shader does
with them (a second scheme colour on a zone) is Cube Escape's.
"""

from __future__ import annotations

import re
from typing import Dict, List

from .materials import KEEP_OWN
from .paint import PAINTED

#: name tokens that tell members of one group apart (``Frame_Left`` / ``Frame_Right``, ``Panel_Inner_B``)
SIDE_TOKENS = {"L", "R", "A", "B", "Left", "Right", "Top", "Bottom", "Front", "Back", "Inner", "Outer", "Upper",
               "Lower"}
_NUMBER = re.compile(r"^\d+$")
_SUFFIX = re.compile(r"(?:_LOD\d+)?(?:\.\d{3})?$")  # an LOD level and Blender's duplicate counter
MAX_SLOTS = 3
BODY = "Body"  # the main body is the rest of the model: it gets no slot
CHANNELS = "rgb"


def zone_name(object_name: str) -> str:
    """The zone of a mesh object: its name without trailing numbers and side/position tokens (``Rotor_2`` -> ``Rotor``,
    ``Panel_Outer_B`` -> ``Panel``); a name made only of such tokens stays as it is. Order prefixes of rail kits
    (``03_AngleProfile``) are dropped."""
    parts = [p for p in _SUFFIX.sub("", object_name).split("_") if p]
    if len(parts) > 1 and _NUMBER.match(parts[0]):
        parts = parts[1:]
    while len(parts) > 1 and (_NUMBER.match(parts[-1]) or parts[-1] in SIDE_TOKENS):
        parts.pop()
    return "_".join(parts) or object_name


def zone_table(asset) -> List[Dict]:
    """``[{"zone", "objects", "painted"}]`` sorted by zone: the mesh objects of each zone and the painted game
    materials (``paint.PAINTED``) their faces use - a zone without any cannot take a scheme colour."""
    zones: Dict[str, Dict] = {}
    for obj in asset.meshes():
        entry = zones.setdefault(zone_name(obj.name), {"objects": [], "painted": set()})
        entry["objects"].append(obj.name)
        entry["painted"].update(r for r in obj.mesh.roles if r in PAINTED)
    return [{"zone": z, "objects": sorted(e["objects"]), "painted": sorted(e["painted"])}
            for z, e in sorted(zones.items())]


def paintable_zones(asset) -> int:
    """How many zones can take a scheme colour (a painted material in at least one face)."""
    return sum(1 for z in zone_table(asset) if z["painted"])


def paint_zones(names) -> List[Dict]:
    """The zone slots of the painted mesh objects ``names`` (those with a material the scheme paints or tiles, i.e. not
    only glow/crystal/glass): ``[{"channel", "zone", "objects"}]`` - zones in alphabetical order, ``Body`` left out, at
    most ``MAX_SLOTS``; empty (no map) for a model with one zone. The sidecar's ``textures.zones.slots``."""
    by_zone: Dict[str, List[str]] = {}
    for name in sorted(set(names)):
        by_zone.setdefault(zone_name(name), []).append(name)
    if len(by_zone) < 2:
        return []
    chosen = [z for z in sorted(by_zone) if z != BODY][:MAX_SLOTS]
    return [{"channel": CHANNELS[i], "zone": z, "objects": by_zone[z]} for i, z in enumerate(chosen)]


def painted_object_names(asset) -> List[str]:
    """Mesh objects of ``asset`` that take part in the bake (a face with a material that is not ``KEEP_OWN``)."""
    return [o.name for o in asset.meshes() if any(r not in KEEP_OWN for r in o.mesh.roles)]


def _shift(array, dy: int, dx: int):
    """``array`` moved by (dy, dx) rows/columns, zeros coming in (np.roll would carry a texel across the atlas edge)."""
    import numpy as np

    out = np.zeros_like(array)
    h, w = array.shape[:2]
    out[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = array[max(-dy, 0):h - max(dy, 0),
                                                                    max(-dx, 0):w - max(dx, 0)]
    return out


def zone_map(triangles, size: int, margin: int = 4):
    """The zone map (``size`` x ``size`` x 4 uint8, bottom-up rows) from ``triangles``: ``[(slot, ((u, v) x 3))]`` with
    ``slot`` 0..2 for a zone's channel and -1 for every other face (they only mark texels as used). Texels whose centre
    lies in a triangle get the slot's channel 255; empty texels within ``margin`` px of a used one take its value (the
    bake margin, so a filtered lookup at an island border stays inside its zone); alpha is 255."""
    import numpy as np

    weights = np.zeros((size, size, MAX_SLOTS), np.uint8)
    used = np.zeros((size, size), bool)
    for slot, tri in triangles:
        pts = np.asarray(tri, np.float64) * size
        x0, y0 = np.floor(pts.min(axis=0)).astype(int)
        x1, y1 = np.ceil(pts.max(axis=0)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = pts
        det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(det) < 1e-12:
            continue
        w0 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / det
        w1 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / det
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (1 - w0 - w1 >= -1e-9)
        window = (slice(y0, y1 + 1), slice(x0, x1 + 1))
        used[window] |= inside
        if slot >= 0:
            weights[window][..., slot][inside] = 255
        else:
            weights[window][inside] = 0  # a later plain face over an earlier zone texel (overlap): the last one wins
    for _ in range(margin):
        empty = ~used
        grown = np.zeros_like(used)
        value = np.zeros_like(weights)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            src_used = _shift(used, dy, dx)
            src_val = _shift(weights, dy, dx)
            take = empty & src_used & ~grown
            value[take] = src_val[take]
            grown |= take
        weights |= value
        used |= grown
    alpha = np.full((size, size, 1), 255, np.uint8)
    return np.concatenate([weights, alpha], axis=2)
