"""The Unity importer's sidecar contract, checked in Python (Cube Escape: Docs/CUBEGEN_IMPORT.md).

The game's editor import (``CubegenImporter``) skips a model when its
``<Name>.cubegen.json`` breaks the contract or disagrees with the FBX. The rules
live in ``cubegen/contract.json`` (machine-readable, shared with the Unity import:
``python -m cubegen contract --out <file>``); this module applies them before a
file leaves the generator:

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

import json
import math
import os
from typing import Dict, List, Optional, Sequence, Tuple

CONTRACT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contract.json")


def load_contract(path: str = CONTRACT_FILE) -> Dict:
    """The machine-readable contract (``cubegen/contract.json``) - the same file the Unity import can read."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


CONTRACT = load_contract()
ROOT_KEYS = set(CONTRACT["root"]["keys"])
ROOT_REQUIRED = tuple(CONTRACT["root"]["required"])
PART_KEYS = set(CONTRACT["part"]["keys"])
PART_REQUIRED = tuple(CONTRACT["part"]["required"])
PIVOTS = tuple(CONTRACT["root"]["pivots"])
AXES = tuple(CONTRACT["axes"])
SIGNAL_MODES = tuple(CONTRACT["signal_modes"])
RULES = CONTRACT["rules"]
TOL = CONTRACT["tolerances"]

# script -> (required roles, optional roles, allowed fields)
BEHAVIOURS: Dict[str, Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...]]] = {
    name: (tuple(b["required"]), tuple(b["optional"]), tuple(b["fields"])) for name, b in CONTRACT["behaviours"].items()
}
BEHAVIOUR_KEYS = set(CONTRACT["behaviour_keys"])

POSITION_TOL = TOL["position_m"]


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
    if not _segment(data["category"]) or data["category"] in CONTRACT["root"]["reserved_categories"]:
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
    if "collision" in data and data["collision"] not in CONTRACT["root"]["collision_modes"]:
        errors.append(f"collision: {data['collision']!r} not allowed")
    if "textures" in data:
        tex = data["textures"]
        if not isinstance(tex, dict) or tex.get("mode") not in CONTRACT["root"]["texture_modes"] or \
                not isinstance(tex.get("manifest"), str):
            errors.append("textures: expected {mode: tiled|baked|palette, manifest: path}")

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
    seen_scripts = set()
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
        if script in seen_scripts and script not in RULES["repeatable_behaviours"]:
            errors.append(f"{where}: duplicate behaviour {script}")
        seen_scripts.add(script)
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
            if role in RULES["single_part_roles"].get(script, []) and not isinstance(value, str):
                errors.append(f"{where}: role {role!r} must name a single part as text")
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

        motion = [n for role in CONTRACT["behaviours"][script]["moves"] for n in _role_parts(roles.get(role)) or []]
        if script == "Door":
            lo, hi = RULES["door_panels"]
            if not lo <= len(motion) <= hi:
                errors.append(f"{where}: {lo} to {hi} panels")
            if RULES["door_leaves_move_apart"] and len(motion) == 2 and all(n in parts for n in motion) and \
                    _vec(fields.get("openOffset")):
                errors += _check_leaves(where, [parts[n]["localPosition"] for n in motion], fields)
            upper = roles.get("upperFrame")
            if upper is not None and _role_parts(upper) != RULES["door_upper_frame"]:
                errors.append(f"{where}: role upperFrame only accepts {', '.join(RULES['door_upper_frame'])}")
        elif script == "SignalLight" and fields.get("mode") == "Rotate":
            if RULES["signal_light_rotate_needs_rotor"] and "rotor" not in roles:
                errors.append(f"{where}: mode Rotate needs a rotor")
            motion = _role_parts(roles.get("rotor")) or []
        for n in motion:
            if n in moved and RULES["one_motion_controller_per_transform"]:
                errors.append(f"{where}: {n!r} is already moved by {moved[n]}")
            moved[n] = script
            moving.update([n] + children(n))
        if script == "ItemPickup" and "itemId" not in fields:
            kind = (data.get("params") or {}).get("kind")
            free = RULES["item_pickup_without_id"]
            if not (data["type"] == free["type"] and kind == free["params.kind"]):
                open_items.append(f"{data['model']}: ItemPickup needs fields.itemId (type {data['type']})")

    # -- colliders -----------------------------------------------------------
    for i, c in enumerate(data.get("colliders", []) if isinstance(data.get("colliders", []), list) else [None]):
        where = f"colliders[{i}]"
        if not isinstance(c, dict) or c.get("type") not in ("box", "mesh"):
            errors.append(f"{where}: expected a box or mesh collider")
            continue
        keys = set(CONTRACT["colliders"][c["type"]])
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
            if abs(math.sqrt(sum(q * q for q in c["rotation"])) - 1.0) > TOL["quaternion_norm"]:
                errors.append(f"{where}: rotation is not a normalised quaternion")
        else:
            if part is None or parts[part]["empty"]:
                errors.append(f"{where}: a mesh collider needs a mesh part")
            elif part in moving and c["convex"] is not True and CONTRACT["colliders"]["moving_mesh_must_be_convex"]:
                errors.append(f"{where}: {part!r} moves - its mesh collider must be convex")
    if RULES["interactive_rotatable_requires_target_collider"] and isinstance(data.get("colliders"), list):
        turns = [b for b in behaviours if isinstance(b, dict) and b.get("script") == "Rotatable"]
        for b in turns:
            roles, fields = b.get("parts", {}), b.get("fields", {})
            if not isinstance(roles, dict) or not isinstance(fields, dict) or fields.get("interactive") is False:
                continue
            target = roles.get("target")
            if not isinstance(target, str) or target not in parts:
                continue
            reachable_parts = {target, *children(target)}
            colliders = [c for c in data["colliders"] if isinstance(c, dict)]
            reachable = any(c.get("part") in reachable_parts for c in colliders) if len(turns) > 1 else bool(colliders)
            if not reachable:
                errors.append(f"Rotatable: explicit colliders must make interactive target {target!r} reachable")
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

    types = CONTRACT["behaviours"][script]["fields"]
    for name, value in fields.items():
        kind = types.get(name)
        if kind == "vec3" and not _vec(value):
            bad(name, "needs three numbers")
        elif kind == "bool" and not isinstance(value, bool):
            bad(name, "must be true/false")
        elif kind == "axis" and value not in AXES:
            bad(name, f"must be one of {AXES}")
        elif kind == "mode" and value not in SIGNAL_MODES:
            bad(name, f"must be one of {SIGNAL_MODES}")
        elif kind == "int" and (not isinstance(value, int) or isinstance(value, bool)):
            bad(name, "must be an integer")
        elif kind == "text" and (not isinstance(value, str) or not value.strip()):
            bad(name, "must be text")
        elif kind == "number" and not _num(value):
            bad(name, "must be a number")
    if script == "Door" and RULES["door_speed_positive"] and _num(fields.get("speed")) and fields["speed"] <= 0:
        bad("speed", "must be positive")
    lo, hi = RULES["rotatable_step_abs"]
    if script == "Rotatable" and _num(fields.get("step", 90)) and not lo <= abs(fields.get("step", 90)) <= hi:
        bad("step", f"magnitude must be {lo}-{hi}")
    if script == "Rotator" and _num(fields.get("arc", 0)) and not 0 <= fields.get("arc", 0) < RULES["rotator_arc_below"]:
        bad("arc", f"must be 0 (full turns) or below {RULES['rotator_arc_below']}")
    together = RULES["signal_light_fields_together"]
    light = [k for k in together if k in fields]
    if light and len(light) != len(together):
        bad("/".join(together), "only together")
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
        if any(abs(r) > TOL["fbx_rotation"] for r in info["rotation"]) or \
                any(abs(s - 1) > TOL["fbx_scale"] for s in info["scale"]):
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
    tol = TOL["bounds_m"] + TOL["bounds_relative"] * math.sqrt(sum(s * s for s in bounds["size"]))
    off = max(max(abs(a - b) for a, b in zip(center, bounds["center"])),
              max(abs(a - b) for a, b in zip(size, bounds["size"])))
    if off > tol:
        return [f"{what}: bounds center {bounds['center']} size {bounds['size']}, geometry center "
                f"{[round(c, 4) for c in center]} size {[round(s, 4) for s in size]}"]
    return []


def read_sidecar(path: str) -> Tuple[Optional[Dict], List[str]]:
    """A sidecar file with the importer's file rules: size, nesting depth, no duplicate keys, valid JSON."""
    rules = CONTRACT["file"]
    size = os.path.getsize(path)
    if size > rules["max_bytes"]:
        return None, [f"file: {size} bytes > {rules['max_bytes']}"]
    duplicates: List[str] = []

    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                duplicates.append(key)
            seen[key] = value
        return seen

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh, object_pairs_hook=pairs)
    except (ValueError, RecursionError) as exc:
        return None, [f"file: not valid JSON ({exc})"]
    errors = []
    if duplicates and not rules["duplicate_keys"]:
        errors.append(f"file: duplicate key(s) {sorted(set(duplicates))}")

    def depth(value, level=1):
        if isinstance(value, dict):
            return max([level] + [depth(v, level + 1) for v in value.values()])
        if isinstance(value, list):
            return max([level] + [depth(v, level + 1) for v in value])
        return level - 1

    if depth(data) > rules["max_depth"]:
        errors.append(f"file: nested deeper than {rules['max_depth']} levels")
    return data, errors


def check_export(models_dir: str) -> Dict[str, Dict[str, List[str]]]:
    """Every ``*.cubegen.json`` below ``models_dir`` (with its FBX if there is one): {model: {errors, open}}."""
    result = {}
    for folder, _, files in os.walk(models_dir):
        for name in sorted(f for f in files if f.endswith(".cubegen.json")):
            path = os.path.join(folder, name)
            data, file_errors = read_sidecar(path)
            if data is None:
                result[name[: -len(".cubegen.json")]] = {"errors": file_errors, "open": []}
                continue
            errors, open_items = check_sidecar(data, path)
            errors = file_errors + errors
            fbx = path[: -len(".cubegen.json")] + ".fbx"
            if not errors and os.path.isfile(fbx):
                errors += check_fbx(data, fbx)
            entry = {"errors": errors, "open": open_items}
            glb = path[: -len(".cubegen.json")] + ".glb"
            if os.path.isfile(glb):  # the workbench's path: its budget (a note, the editor import has none)
                entry["runtime"] = check_runtime_budget(glb)
            result[name[: -len(".cubegen.json")]] = entry
    return result


__all__ = ["check_sidecar", "check_fbx", "check_export", "read_sidecar", "load_contract", "CONTRACT", "CONTRACT_FILE",
           "BEHAVIOURS", "ROOT_KEYS", "RUNTIME_BUDGET", "check_runtime_budget", "glb_summary", "texture_bytes"]


# --------------------------------------------------------------------------
# runtime budget of Cube Escape's workbench (GLB path)
# --------------------------------------------------------------------------

#: what the workbench imports at most per player model - Cube Escape ``CubegenImportBudget`` and
#: ``CubegenGlb.Limits.MaxBytes`` (checked 0.21.0). Limits on files and memory are BYTES: a UTF-8 character takes up
#: to three bytes, so a string's length is never compared with them (Cube Escape 0.49 found that mix-up in a reader).
RUNTIME_BUDGET = {"glb_bytes": 32 * 1024 * 1024, "triangles": 60_000, "parts": 512, "materials": 32,
                  "textures": 16, "texture_size": 2048, "texture_bytes": 64 * 1024 * 1024}


def texture_bytes(width: int, height: int) -> int:
    """GPU memory of an RGBA32 texture with its mip chain - counted like Cube Escape's budget (w * h * 4 * 4 / 3)."""
    return width * height * 4 * 4 // 3


def glb_summary(path: str) -> Dict:
    """What the workbench's GLB reader sees: bytes, nodes, materials, triangles and the embedded images' sizes."""
    import struct

    with open(path, "rb") as fh:
        data = fh.read()
    magic, _version, length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67:
        raise ValueError(f"{path}: not a GLB file")
    chunk_len, chunk_type = struct.unpack_from("<II", data, 12)
    gltf = json.loads(data[20:20 + chunk_len].decode("utf-8"))
    binary = b""
    offset = 20 + chunk_len
    if offset + 8 <= len(data):
        bin_len, _ = struct.unpack_from("<II", data, offset)
        binary = data[offset + 8:offset + 8 + bin_len]
    accessors, views = gltf.get("accessors", []), gltf.get("bufferViews", [])
    triangles = 0
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) != 4:
                continue
            if "indices" in prim:
                triangles += accessors[prim["indices"]]["count"] // 3
            elif "POSITION" in prim.get("attributes", {}):
                triangles += accessors[prim["attributes"]["POSITION"]]["count"] // 3
    images = []
    for image in gltf.get("images", []):
        view = views[image["bufferView"]] if "bufferView" in image else None
        blob = binary[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]] if view else b""
        if blob[:8] == b"\x89PNG\r\n\x1a\n":
            images.append(struct.unpack_from(">II", blob, 16))
        else:
            images.append(None)  # external or not a PNG: size unknown here
    return {"bytes": len(data), "length": length, "nodes": len(gltf.get("nodes", [])),
            "materials": len(gltf.get("materials", [])), "triangles": triangles, "images": images}


def check_runtime_budget(path: str, budget: Optional[Dict] = None) -> List[str]:
    """Where a GLB exceeds the workbench's budget (empty: it fits)."""
    rules = dict(RUNTIME_BUDGET, **(budget or {}))
    info = glb_summary(path)
    found = []
    if info["bytes"] > rules["glb_bytes"]:
        found.append(f"GLB {info['bytes']} bytes > {rules['glb_bytes']}")
    for key, label in (("triangles", "triangles"), ("nodes", "parts"), ("materials", "materials")):
        limit = rules[label]
        if info[key] > limit:
            found.append(f"{info[key]} {label} > {limit}")
    known = [size for size in info["images"] if size]
    if len(info["images"]) > rules["textures"]:
        found.append(f"{len(info['images'])} textures > {rules['textures']}")
    too_big = [f"{w}x{h}" for w, h in known if max(w, h) > rules["texture_size"]]
    if too_big:
        found.append(f"textures larger than {rules['texture_size']} px: {', '.join(too_big)}")
    memory = sum(texture_bytes(w, h) for w, h in known)
    if memory > rules["texture_bytes"]:
        found.append(f"texture memory {memory} bytes > {rules['texture_bytes']}")
    return found
