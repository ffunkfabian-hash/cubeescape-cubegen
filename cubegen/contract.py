"""The Unity importer's sidecar contract, checked in Python (Cube Escape: Docs/CUBEGEN_IMPORT.md).

The game's editor import (``CubegenImporter``) skips a model when its
``<Name>.cubegen.json`` breaks the contract or disagrees with the FBX. This
module applies the same rules before a file leaves the generator:

* only the known root keys, part keys, behaviours, roles and fields
* values of the right type (vectors with exactly three finite numbers ...)
* referenced parts exist; one motion controller per transform; two door leaves move apart
* colliders: positive box sizes, normalised quaternions, convex meshes on moving parts
* ``ItemPickup`` needs ``fields.itemId`` - except ``item`` with ``params.kind`` ``energy_cell``
  (reported as an *open* assignment, not an error: cubegen never invents item ids)
* with the FBX: every part exists once, same parent, mesh/empty, local position within 1 cm,
  model bounds within 2.5 cm + 1 % of the size vector, part bounds against the part's own mesh

``check_sidecar(data)`` returns ``(errors, open_items)``.
"""

from __future__ import annotations

import math
import os
from typing import Dict, List, Optional, Sequence, Tuple

ROOT_KEYS = {"model", "type", "category", "pivot", "static", "bounds", "parts", "behaviours", "seed", "masterSeed",
             "generator", "params", "style", "textures", "collision", "colliders"}
ROOT_REQUIRED = ("model", "type", "category", "pivot", "static", "bounds", "parts", "behaviours")
PART_KEYS = {"name", "parent", "localPosition", "empty", "materials", "bounds"}
PART_REQUIRED = ("name", "parent", "localPosition", "empty", "materials")
PIVOTS = ("floor", "top", "center", "wall")
AXES = ("right", "up", "forward")
SIGNAL_MODES = ("Steady", "Blink", "Pulse", "Rotate", "Status")

# script -> (required roles, optional roles, allowed fields)
BEHAVIOURS: Dict[str, Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...]]] = {
    "Door": (("panels", "statusLights", "colliders"), ("upperFrame",),
             ("openOffset", "secondOffset", "speed", "startsOpen", "upperFrame")),
    "Machine": (("body", "glow"), ("rotor", "damage", "colliders"), ("needsPower",)),
    "Rotator": (("target",), ("colliders",), ("axis", "speed", "arc")),
    "Rotatable": (("target", "glow"), ("body", "colliders"), ("axis", "step", "speed", "target", "interactive")),
    "SignalLight": (("glow",), ("rotor", "body", "colliders"),
                    ("mode", "color", "brightness", "startsOn", "lightPosition", "range", "intensity")),
    "SignalIndicator": (("renderers",), ("body", "colliders"), ("offMaterial", "onMaterial")),
    "ItemPickup": (("model",), (), ("spin", "itemId")),
}
BEHAVIOUR_KEYS = {"script", "parts", "fields", "note"}

POSITION_TOL = 0.01


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _vec(v, n=3) -> bool:
    return isinstance(v, list) and len(v) == n and all(_num(c) for c in v)


def _segment(text) -> bool:
    return isinstance(text, str) and text not in ("", ".", "..") and not any(c in text for c in "/\\:")


def _bounds_ok(b) -> bool:
    return isinstance(b, dict) and set(b) == {"center", "size"} and _vec(b["center"]) and _vec(b["size"])


def _role_parts(value) -> Optional[List[str]]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and value and all(isinstance(v, str) for v in value):
        return value
    return None


def check_sidecar(data, file_name: Optional[str] = None) -> Tuple[List[str], List[str]]:
    """Contract errors and open item assignments of a sidecar (parsed JSON)."""
    errors: List[str] = []
    open_items: List[str] = []
    if not isinstance(data, dict):
        return ["root: expected an object"], open_items
    for key in data:
        if key not in ROOT_KEYS:
            errors.append(f"root: unknown key {key!r}")
    for key in ROOT_REQUIRED:
        if key not in data:
            errors.append(f"root: missing {key!r}")
    if errors:
        return errors, open_items

    if not _segment(data["model"]):
        errors.append(f"model: {data['model']!r} is not a single path segment")
    elif file_name and os.path.basename(file_name).split(".cubegen.json")[0] != data["model"]:
        errors.append(f"model: {data['model']!r} does not match the file name {os.path.basename(file_name)!r}")
    if not _segment(data["category"]) or data["category"] == "Generated":
        errors.append(f"category: {data['category']!r} not allowed")
    if data["pivot"] not in PIVOTS:
        errors.append(f"pivot: {data['pivot']!r} not in {PIVOTS}")
    if not isinstance(data["static"], bool):
        errors.append("static: expected true/false")
    if not _bounds_ok(data["bounds"]):
        errors.append("bounds: expected {center: [x,y,z], size: [x,y,z]}")
    for key in ("params", "style"):
        if key in data and not isinstance(data[key], dict):
            errors.append(f"{key}: expected an object")
    if "generator" in data and not isinstance(data["generator"], str):
        errors.append("generator: expected text")
    for key in ("seed", "masterSeed"):
        if key in data and not (isinstance(data[key], int) and not isinstance(data[key], bool)):
            errors.append(f"{key}: expected an integer")
    if "collision" in data and data["collision"] not in ("envelope", "mesh", "parts", "none"):
        errors.append(f"collision: {data['collision']!r} not allowed")
    if "textures" in data:
        tex = data["textures"]
        if not isinstance(tex, dict) or tex.get("mode") not in ("tiled", "baked") or \
                not isinstance(tex.get("manifest"), str):
            errors.append("textures: expected {mode: tiled|baked, manifest: path}")

    # -- parts ---------------------------------------------------------------
    parts: Dict[str, Dict] = {}
    if not isinstance(data["parts"], list):
        errors.append("parts: expected a list")
    else:
        for i, part in enumerate(data["parts"]):
            where = f"parts[{i}]"
            if not isinstance(part, dict):
                errors.append(f"{where}: expected an object")
                continue
            for key in part:
                if key not in PART_KEYS:
                    errors.append(f"{where}: unknown key {key!r}")
            missing = [k for k in PART_REQUIRED if k not in part]
            if missing:
                errors.append(f"{where}: missing {', '.join(missing)}")
                continue
            name = part["name"]
            if not isinstance(name, str) or not name:
                errors.append(f"{where}: name must be text")
                continue
            if name in parts:
                errors.append(f"part {name!r}: declared twice")
            parts[name] = part
            if part["parent"] is not None and not isinstance(part["parent"], str):
                errors.append(f"part {name!r}: parent must be a name or null")
            if not _vec(part["localPosition"]):
                errors.append(f"part {name!r}: localPosition needs three numbers")
            if not isinstance(part["empty"], bool):
                errors.append(f"part {name!r}: empty must be true/false")
            if not isinstance(part["materials"], list) or not all(isinstance(m, str) for m in part["materials"]):
                errors.append(f"part {name!r}: materials must be a list of names")
            elif not part["empty"] and not part["materials"]:
                errors.append(f"part {name!r}: a mesh part needs materials")
            if "bounds" in part and not _bounds_ok(part["bounds"]):
                errors.append(f"part {name!r}: bad bounds")
        for name, part in parts.items():
            if part["parent"] is not None and part["parent"] not in parts:
                errors.append(f"part {name!r}: parent {part['parent']!r} is not a declared part")

    def children(name):
        result = []
        for n, prt in parts.items():
            if prt["parent"] == name:
                result += [n] + children(n)
        return result

    # -- behaviours ----------------------------------------------------------
    moved: Dict[str, str] = {}   # transform -> controller
    moving: set = set()          # moving transforms and everything below them
    if not isinstance(data["behaviours"], list):
        errors.append("behaviours: expected a list")
        behaviours = []
    else:
        behaviours = data["behaviours"]
    for i, b in enumerate(behaviours):
        where = f"behaviours[{i}]"
        if not isinstance(b, dict) or b.get("script") not in BEHAVIOURS:
            errors.append(f"{where}: unknown behaviour {b.get('script') if isinstance(b, dict) else b!r}")
            continue
        script = b["script"]
        where = f"{where} {script}"
        for key in b:
            if key not in BEHAVIOUR_KEYS:
                errors.append(f"{where}: unknown key {key!r}")
        required, optional, allowed_fields = BEHAVIOURS[script]
        roles = b.get("parts", {})
        fields = b.get("fields", {})
        if not isinstance(roles, dict) or not isinstance(fields, dict):
            errors.append(f"{where}: parts and fields must be objects")
            continue
        for role in roles:
            if role not in required and role not in optional:
                errors.append(f"{where}: unknown role {role!r}")
        for role in required:
            if role not in roles:
                errors.append(f"{where}: missing role {role!r}")
        for role, value in roles.items():
            names = _role_parts(value)
            if names is None:
                errors.append(f"{where}: role {role!r} must name parts")
                continue
            for n in names:
                if n not in parts:
                    errors.append(f"{where}: role {role!r} names unknown part {n!r}")
        for name in fields:
            if name not in allowed_fields:
                errors.append(f"{where}: unknown field {name!r}")
        errors += _check_fields(where, script, fields, roles)

        motion = []
        if script == "Door":
            motion = _role_parts(roles.get("panels")) or []
            if not 1 <= len(motion) <= 2:
                errors.append(f"{where}: one or two panels")
            if len(motion) == 2 and all(n in parts for n in motion) and _vec(fields.get("openOffset")):
                errors += _check_leaves(where, [parts[n]["localPosition"] for n in motion], fields)
            upper = roles.get("upperFrame")
            if upper is not None and _role_parts(upper) != ["Frame_Top"]:
                errors.append(f"{where}: role upperFrame only accepts Frame_Top")
        elif script in ("Rotator", "Rotatable"):
            motion = _role_parts(roles.get("target")) or []
        elif script == "SignalLight" and fields.get("mode") == "Rotate":
            if "rotor" not in roles:
                errors.append(f"{where}: mode Rotate needs a rotor")
            motion = _role_parts(roles.get("rotor")) or []
        for n in motion:
            if n in moved and not (moved[n] == "Rotator" and script == "Rotator" and False):
                errors.append(f"{where}: {n!r} is already moved by {moved[n]}")
            moved[n] = script
            moving.update([n] + children(n))
        if script == "ItemPickup" and "itemId" not in fields:
            kind = (data.get("params") or {}).get("kind")
            if not (data["type"] == "item" and kind == "energy_cell"):
                open_items.append(f"{data['model']}: ItemPickup needs fields.itemId (type {data['type']})")

    # -- colliders -----------------------------------------------------------
    for i, c in enumerate(data.get("colliders", []) if isinstance(data.get("colliders", []), list) else [None]):
        where = f"colliders[{i}]"
        if not isinstance(c, dict) or c.get("type") not in ("box", "mesh"):
            errors.append(f"{where}: expected a box or mesh collider")
            continue
        keys = {"type", "part", "center", "size", "rotation"} if c["type"] == "box" else {"type", "part", "convex"}
        if set(c) != keys:
            errors.append(f"{where}: keys {sorted(c)} - expected {sorted(keys)}")
            continue
        part = c["part"]
        if part is not None and part not in parts:
            errors.append(f"{where}: unknown part {part!r}")
            continue
        if c["type"] == "box":
            if not _vec(c["center"]) or not _vec(c["size"]) or not _vec(c["rotation"], 4):
                errors.append(f"{where}: center/size need 3 numbers, rotation 4")
                continue
            if min(c["size"]) <= 0:
                errors.append(f"{where}: size must be positive")
            if abs(math.sqrt(sum(q * q for q in c["rotation"])) - 1.0) > 1e-3:
                errors.append(f"{where}: rotation is not a normalised quaternion")
        else:
            if part is None or parts[part]["empty"]:
                errors.append(f"{where}: a mesh collider needs a mesh part")
            elif part in moving and c["convex"] is not True:
                errors.append(f"{where}: {part!r} moves - its mesh collider must be convex")
    return errors, open_items


def _check_leaves(where, positions, fields) -> List[str]:
    """Two door leaves must move apart: the second one by ``secondOffset``, by default ``-openOffset``."""
    first = fields["openOffset"]
    second = fields.get("secondOffset")
    second = second if _vec(second) else [-c for c in first]
    gap = [b - a for a, b in zip(*positions)]
    opened = [g + s - f for g, s, f in zip(gap, second, first)]
    if sum(o * g for o, g in zip(opened, gap)) <= sum(g * g for g in gap):
        return [f"{where}: the two leaves don't move apart (openOffset {first}, secondOffset {second})"]
    return []


def _check_fields(where, script, fields, roles) -> List[str]:
    errors = []

    def bad(name, what):
        errors.append(f"{where}: field {name!r} {what}")

    for name, value in fields.items():
        if name in ("openOffset", "secondOffset", "lightPosition"):
            if not _vec(value):
                bad(name, "needs three numbers")
        elif name in ("startsOpen", "upperFrame", "needsPower", "interactive", "startsOn"):
            if not isinstance(value, bool):
                bad(name, "must be true/false")
        elif name == "axis":
            if value not in AXES:
                bad(name, f"must be one of {AXES}")
        elif name == "mode":
            if value not in SIGNAL_MODES:
                bad(name, f"must be one of {SIGNAL_MODES}")
        elif name == "target" and script == "Rotatable":
            if not isinstance(value, int) or isinstance(value, bool):
                bad(name, "must be an integer")
        elif name in ("offMaterial", "onMaterial", "itemId", "color"):
            if not isinstance(value, str) or not value:
                bad(name, "must be text")
        elif not _num(value):
            bad(name, "must be a number")
    if script == "Door" and "speed" in fields and _num(fields["speed"]) and fields["speed"] <= 0:
        bad("speed", "must be positive")
    if script == "Rotatable" and _num(fields.get("step", 90)) and not 1 <= abs(fields.get("step", 90)) <= 360:
        bad("step", "magnitude must be 1-360")
    if script == "Rotator" and _num(fields.get("arc", 0)) and not 0 <= fields.get("arc", 0) < 360:
        bad("arc", "must be 0 (full turns) or below 360")
    light = [k for k in ("lightPosition", "range", "intensity") if k in fields]
    if light and len(light) != 3:
        bad("lightPosition/range/intensity", "only together")
    if script == "ItemPickup" and "itemId" in fields and not str(fields["itemId"]).strip():
        bad("itemId", "must not be empty")
    return errors


# ---------------------------------------------------------------------------
# against the FBX
# ---------------------------------------------------------------------------

def check_fbx(data, fbx_path: str) -> List[str]:
    """Differences between a (contract-valid) sidecar and its FBX, with the importer's tolerances."""
    from .fbxread import unity_locals

    found = unity_locals(fbx_path)
    errors = []
    for name, info in found.items():
        if any(abs(r) > 1e-3 for r in info["rotation"]) or any(abs(s - 1) > 1e-4 for s in info["scale"]):
            errors.append(f"FBX {name!r}: rotation {info['rotation']} / scale {info['scale']} (expected 0 / 1)")

    def world(name) -> Tuple[float, float, float]:
        pos = [0.0, 0.0, 0.0]
        while name is not None:
            p = found[name]["position"]
            pos = [pos[i] + p[i] for i in range(3)]
            name = found[name]["parent"]
        return tuple(pos)  # type: ignore[return-value]

    for part in data["parts"]:
        name = part["name"]
        info = found.get(name)
        if info is None:
            errors.append(f"part {name!r}: missing in the FBX")
            continue
        if info["parent"] != part["parent"]:
            errors.append(f"part {name!r}: FBX parent {info['parent']!r}, sidecar {part['parent']!r}")
        if bool(info["vertices"]) == part["empty"]:
            errors.append(f"part {name!r}: FBX {'mesh' if info['vertices'] else 'empty'}, sidecar "
                          f"{'empty' if part['empty'] else 'mesh'}")
        delta = max(abs(a - b) for a, b in zip(info["position"], part["localPosition"]))
        if delta > POSITION_TOL:
            errors.append(f"part {name!r}: local position FBX {info['position']} vs sidecar "
                          f"{part['localPosition']} ({delta * 100:.1f} cm)")
        if "bounds" in part and info["vertices"]:
            errors += _bounds_diff(f"part {name!r}", part["bounds"], info["vertices"])
    points = []
    for name, info in found.items():
        origin = world(name)
        points += [tuple(v[i] + origin[i] for i in range(3)) for v in info["vertices"]]
    if points:
        errors += _bounds_diff("model", data["bounds"], points)
    return errors


def _bounds_diff(what, bounds, points: Sequence[Sequence[float]]) -> List[str]:
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    center = [(lo[i] + hi[i]) / 2 for i in range(3)]
    size = [hi[i] - lo[i] for i in range(3)]
    tol = 0.025 + 0.01 * math.sqrt(sum(s * s for s in bounds["size"]))
    off = max(max(abs(a - b) for a, b in zip(center, bounds["center"])),
              max(abs(a - b) for a, b in zip(size, bounds["size"])))
    if off > tol:
        return [f"{what}: bounds center {bounds['center']} size {bounds['size']}, geometry center "
                f"{[round(c, 4) for c in center]} size {[round(s, 4) for s in size]}"]
    return []


def check_export(models_dir: str) -> Dict[str, Dict[str, List[str]]]:
    """Every ``*.cubegen.json`` below ``models_dir`` (with its FBX if there is one): {model: {errors, open}}."""
    import json

    result = {}
    for folder, _, files in os.walk(models_dir):
        for name in sorted(f for f in files if f.endswith(".cubegen.json")):
            path = os.path.join(folder, name)
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            errors, open_items = check_sidecar(data, path)
            fbx = path[: -len(".cubegen.json")] + ".fbx"
            if not errors and os.path.isfile(fbx):
                errors += check_fbx(data, fbx)
            result[name[: -len(".cubegen.json")]] = {"errors": errors, "open": open_items}
    return result


__all__ = ["check_sidecar", "check_fbx", "check_export", "BEHAVIOURS", "ROOT_KEYS"]
