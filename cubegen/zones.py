"""Paint zones from part names (0.30.0, TECHNIK.md 3).

A zone is a group of mesh objects that belong together visually: ``Frame_Left``/``Frame_Right``/``Frame_Top`` are the
zone ``Frame``, ``Leg_1``..``Leg_4`` the zone ``Leg``. A scheme that wants a second colour exactly on such a group
(door frame, rotor blades, status lights) reads the table from the manifest (``zones``); nothing about the zone enters
the sidecar, the geometry or the baked maps - a zone *map* needs a new channel in the Unity contract and a shader in
Cube Escape (ROADMAP ToDo 27), which this version does not touch.

Pure Python; the table depends only on the asset's object names and face materials, so it is part of no cache key.
"""

from __future__ import annotations

import re
from typing import Dict, List

from .paint import PAINTED

#: name tokens that tell members of one group apart (``Frame_Left`` / ``Frame_Right``, ``Panel_Inner_B``)
SIDE_TOKENS = {"L", "R", "A", "B", "Left", "Right", "Top", "Bottom", "Front", "Back", "Inner", "Outer", "Upper",
               "Lower"}
_NUMBER = re.compile(r"^\d+$")


def zone_name(object_name: str) -> str:
    """The zone of a mesh object: its name without trailing numbers and side/position tokens (``Rotor_2`` -> ``Rotor``,
    ``Panel_Outer_B`` -> ``Panel``); a name made only of such tokens stays as it is. Order prefixes of rail kits
    (``03_AngleProfile``) are dropped."""
    parts = [p for p in object_name.split("_") if p]
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
