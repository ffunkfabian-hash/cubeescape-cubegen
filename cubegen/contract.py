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
* ``textures``: only ``mode``, ``manifest`` and ``baked``; baked maps (section ``baked_maps``) only in mode ``baked``,
  the required ones present, one file per map; ``check_export`` also finds the files

* ``textures.zones`` and root key ``effects`` (version 4): paint zones of the painted parts (section ``zones``) and the
  model's effect materials with proposed runtime parameters (section ``effects``)
* ``textures.neutral`` (version 3): the packed neutral maps of ``--paint`` (section ``neutral_maps``) with
  ``textures.weight_layout``; root key ``paint``: a built-in scheme's name or a custom scheme as data (section
  ``paint_scheme``)

The contract is versioned (``version``, ``history``): version 2 (0.22.0) adds ``baked_maps`` with ``Emission``,
version 3 (0.24.0) the neutral maps and the scheme, version 4 (0.30.0) the zone map and the effects block. ``contract_for(v)`` is the file an importer of version ``v``
reads, ``check_sidecar(data, version=v)`` the sidecar it accepts - ``generate --contract v`` writes such sidecars
(what a version does not know stays in the manifest only).

``check_sidecar(data)`` returns ``(errors, open_items)``.
"""

from __future__ import annotations

import copy
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

CONTRACT_VERSION: int = CONTRACT["version"]
SUPPORTED_VERSIONS = tuple(range(1, CONTRACT_VERSION + 1))
BAKED_MAPS = CONTRACT["baked_maps"]
#: the sidecar's "textures" object (CubegenMaterials reads exactly these in versions 1 and 2)
TEXTURE_KEYS = tuple(CONTRACT["textures"]["keys"])
NEUTRAL_MAPS = CONTRACT["neutral_maps"]
PAINT_SCHEME = CONTRACT["paint_scheme"]
#: material names split off M_Crystal (version 3, cubegen/materials.py CRYSTAL_SPLIT)
SPLIT_MATERIALS = tuple(CONTRACT["materials"]["split"])
ZONES = CONTRACT["zones"]
EFFECTS = CONTRACT["effects"]
#: what a version added to the file: an importer of an older version rejects unknown sections
_SECTIONS_SINCE = {2: ("history", "baked_maps"), 3: ("textures", "neutral_maps", "materials", "paint_scheme"),
                   4: ("zones", "effects")}


def _since(table: Dict, key: str) -> int:
    return int(table.get("since", {}).get(key, 1))


def root_keys(version: int = CONTRACT_VERSION) -> Tuple[str, ...]:
    """The sidecar root keys an importer of ``version`` accepts (``paint`` from version 3)."""
    check_version(version)
    return tuple(k for k in CONTRACT["root"]["keys"] if _since(CONTRACT["root"], k) <= version)


def texture_keys(version: int = CONTRACT_VERSION) -> Tuple[str, ...]:
    """The keys of the sidecar's ``textures`` for ``version`` (``neutral``, ``weight_layout`` from version 3)."""
    check_version(version)
    return tuple(k for k in TEXTURE_KEYS if _since(CONTRACT["textures"], k) <= version)


def check_version(version: int) -> int:
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(f"contract version {version!r} unknown (supported: "
                         f"{', '.join(str(v) for v in SUPPORTED_VERSIONS)})")
    return version


def contract_for(version: int = CONTRACT_VERSION) -> Dict:
    """The contract as an importer of ``version`` reads it: version 1 is the file of cubegen 0.21 (same rules, without
    ``history`` and ``baked_maps``), version 2 the file of cubegen 0.22/0.23 (without the neutral maps and the
    scheme)."""
    data = copy.deepcopy(CONTRACT)
    check_version(version)
    for since, sections in _SECTIONS_SINCE.items():
        if version < since:
            for key in sections:
                data.pop(key, None)
    root = data["root"]
    root["keys"] = list(root_keys(version))
    root["since"] = {k: v for k, v in root.get("since", {}).items() if v <= version}
    if not root["since"]:
        root.pop("since")
    if "textures" in data:
        textures = data["textures"]
        textures["keys"] = list(texture_keys(version))
        textures["since"] = {k: v for k, v in textures.get("since", {}).items() if v <= version}
    if "history" in data:
        data["history"] = {k: v for k, v in data["history"].items() if int(k) <= version}
    data["version"] = version
    return data


def baked_map_keys(version: int = CONTRACT_VERSION) -> Tuple[str, ...]:
    """The baked maps an importer of ``version`` accepts in ``textures.baked`` (version 1: without Emission)."""
    check_version(version)
    return tuple(k for k in BAKED_MAPS["keys"] if BAKED_MAPS["since"].get(k, 1) <= version)


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


def check_sidecar(data, file_name: Optional[str] = None,
                  version: int = CONTRACT_VERSION) -> Tuple[List[str], List[str]]:
    """Contract errors and open item assignments of a sidecar (parsed JSON), for an importer of contract
    ``version``."""
    errors: List[str] = []
    open_items: List[str] = []
    if not isinstance(data, dict):
        return ["root: expected an object"], open_items
    allowed_root = root_keys(version)
    for key in data:
        if key not in allowed_root:
            since = _since(CONTRACT["root"], key) if key in ROOT_KEYS else None
            errors.append(f"root: unknown key {key!r}" + (
                f" (contract version {since}, this importer reads version {version})" if since and since > 1 else ""))
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
        errors += _check_textures(data["textures"], version)
    if "paint" in data:
        errors += _check_paint(data["paint"])
    if "effects" in data:
        errors += _check_effects(data["effects"])
    if version < 3:  # a behaviour that swaps materials (SignalIndicator onMaterial) names one too
        for b in data["behaviours"] if isinstance(data["behaviours"], list) else []:
            fields = b.get("fields") if isinstance(b, dict) else None
            for key, value in (fields.items() if isinstance(fields, dict) else ()):
                if value in SPLIT_MATERIALS:
                    errors.append(f"{b.get('script')}.{key}: material {value} (contract version 3, this importer "
                                  f"reads version {version}: M_Crystal)")
    tex = data.get("textures")
    if isinstance(tex, dict) and "neutral" in tex and "paint" not in data:
        errors.append("textures.neutral needs the paint scheme (root key 'paint')")

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
            elif version < 3 and any(m in SPLIT_MATERIALS for m in part["materials"]):
                split = ", ".join(m for m in part["materials"] if m in SPLIT_MATERIALS)
                errors.append(f"part {name!r}: material {split} (contract version 3, this importer reads version "
                              f"{version}: M_Crystal)")
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


def _check_textures(tex, version: int) -> List[str]:
    """The sidecar's ``textures``: mode and manifest; in mode baked the maps of ``baked_maps`` (as CubegenMaterials
    reads them: unknown maps and missing required ones reject the model, one file per map); from version 3 the neutral
    maps (``neutral_maps``) with their ``weight_layout``."""
    if not isinstance(tex, dict) or tex.get("mode") not in CONTRACT["root"]["texture_modes"] or \
            not isinstance(tex.get("manifest"), str):
        return ["textures: expected {mode: tiled|baked|palette, manifest: path}"]
    allowed_keys = texture_keys(version)
    errors = []
    for key in tex:
        if key not in allowed_keys:
            since = _since(CONTRACT["textures"], key) if key in TEXTURE_KEYS else None
            errors.append(f"textures: unknown key {key!r}" + (
                f" (contract version {since}, this importer reads version {version})" if since and since > 1 else ""))
    baked = tex.get("baked")
    if tex["mode"] != "baked":
        if baked is not None:
            errors.append("textures: baked maps need mode baked")
        if "neutral" in tex:
            errors.append("textures: neutral maps need mode baked")
        return errors
    if not isinstance(baked, dict) or not all(isinstance(v, str) and v for v in baked.values()):
        return errors + ["textures: mode baked needs baked: {map: path}"]
    allowed = baked_map_keys(version)
    for key in baked:
        if key not in allowed:
            since = BAKED_MAPS["since"].get(key)
            errors.append(f"textures.baked: unknown map {key!r}" + (
                f" (contract version {since}, this importer reads version {version})" if since else ""))
    for key in BAKED_MAPS["required"]:
        if key not in baked:
            errors.append(f"textures.baked: missing map {key!r}")
    if BAKED_MAPS["distinct_files"] and len(set(baked.values())) != len(baked):
        errors.append("textures.baked: every map needs its own file")
    if "neutral" in tex or "weight_layout" in tex:
        errors += _check_neutral(tex.get("neutral"), tex.get("weight_layout"))
    if "zones" in tex:
        errors += _check_zones(tex["zones"], tex)
    return errors


def _check_zones(zones, tex) -> List[str]:
    """``textures.zones`` (version 4): the zone map and its slots (section ``zones``)."""
    if not isinstance(zones, dict):
        return ["textures.zones: expected {map: path, slots: [...]}"]
    errors = [f"textures.zones: unknown key {k!r}" for k in zones if k not in ZONES["keys"]]
    if not isinstance(zones.get("map"), str) or not zones.get("map"):
        errors.append("textures.zones.map: expected a file path")
    elif zones["map"] in (tex.get("baked") or {}).values() or zones["map"] in (tex.get("neutral") or {}).values():
        errors.append("textures.zones: the zone map needs its own file")
    if "neutral" not in tex:
        errors.append("textures.zones needs the neutral maps (textures.neutral)")
    slots = zones.get("slots")
    if not isinstance(slots, list) or not 1 <= len(slots) <= ZONES["max_slots"]:
        return errors + [f"textures.zones.slots: expected 1-{ZONES['max_slots']} slots"]
    seen = set()
    for i, slot in enumerate(slots):
        where = f"textures.zones.slots[{i}]"
        if not isinstance(slot, dict) or set(slot) != set(ZONES["slot_keys"]):
            errors.append(f"{where}: expected exactly {', '.join(ZONES['slot_keys'])}")
            continue
        if slot["channel"] != ZONES["channels"][i]:
            errors.append(f"{where}.channel: slot {i} is channel {ZONES['channels'][i]!r}")
        if not isinstance(slot["zone"], str) or not slot["zone"] or slot["zone"] in seen:
            errors.append(f"{where}.zone: expected a name, once each")
        seen.add(slot["zone"])
        if not isinstance(slot["objects"], list) or not slot["objects"] or \
                not all(isinstance(o, str) and o for o in slot["objects"]):
            errors.append(f"{where}.objects: expected a list of part names")
    return errors


def _check_effects(effects) -> List[str]:
    """Root key ``effects`` (version 4): the model's effect materials (section ``effects``)."""
    if not isinstance(effects, list) or not effects:
        return ["effects: expected a non-empty list"]
    errors, seen = [], set()
    for i, entry in enumerate(effects):
        where = f"effects[{i}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: expected an object")
            continue
        for key in entry:
            if key not in EFFECTS["keys"]:
                errors.append(f"{where}: unknown key {key!r}")
        for key in ("material", "kind", "params"):
            if key not in entry:
                errors.append(f"{where}: missing {key!r}")
        name, kind = entry.get("material"), entry.get("kind")
        if name in seen:
            errors.append(f"{where}.material: {name!r} twice")
        seen.add(name)
        if kind not in EFFECTS["kinds"]:
            errors.append(f"{where}.kind: {kind!r} not in {', '.join(EFFECTS['kinds'])}")
            continue
        if not isinstance(name, str) or not name.startswith("M_"):
            errors.append(f"{where}.material: expected an M_ material name")
        if "color" in entry and not (_vec(entry["color"]) and all(0.0 <= c <= 1.0 for c in entry["color"])):
            errors.append(f"{where}.color: expected [r, g, b] in 0..1")
        for key in ("smoothness", "metallic"):
            if key in entry and not _num(entry[key]):
                errors.append(f"{where}.{key}: expected a number")
        if entry.get("emission") is not None and "emission" in entry and not _num(entry["emission"]):
            errors.append(f"{where}.emission: expected a number or null")
        params = entry.get("params")
        if not isinstance(params, dict):
            errors.append(f"{where}.params: expected an object")
            continue
        for key, value in params.items():
            kind_type = EFFECTS["kinds"][kind].get(key)
            if kind_type is None:
                errors.append(f"{where}.params: {key!r} is no parameter of kind {kind!r}")
            elif kind_type == "number" and not _num(value):
                errors.append(f"{where}.params.{key}: expected a number")
            elif kind_type == "bool" and not isinstance(value, bool):
                errors.append(f"{where}.params.{key}: expected true/false")
            elif kind_type == "vec2" and not _vec(value, 2):
                errors.append(f"{where}.params.{key}: expected [x, y]")
    return errors


def _check_layout(layout) -> List[str]:
    """``weight_layout``: the painted game materials of the model in ``paint_scheme.painted`` order, in groups of three
    (one RGB weight map per group), at most three groups."""
    painted = PAINT_SCHEME["painted"]
    if not isinstance(layout, list) or not 1 <= len(layout) <= 3 or \
            not all(isinstance(g, list) and 1 <= len(g) <= 3 and all(isinstance(m, str) for m in g) for g in layout):
        return ["textures.weight_layout: expected 1-3 groups of 1-3 material names"]
    flat = [m for g in layout for m in g]
    unknown = [m for m in flat if m not in painted]
    if unknown:
        return [f"textures.weight_layout: {', '.join(unknown)} is not a painted material ({', '.join(painted)})"]
    if flat != sorted(set(flat), key=painted.index) or any(len(g) != 3 for g in layout[:-1]):
        return ["textures.weight_layout: materials once each, in paint_scheme.painted order, groups of three"]
    return []


def _check_neutral(neutral, layout) -> List[str]:
    if neutral is None or layout is None:
        return ["textures: neutral and weight_layout go together"]
    errors = _check_layout(layout)
    if not isinstance(neutral, dict) or not all(isinstance(v, str) and v for v in neutral.values()):
        return errors + ["textures.neutral: expected {map: path}"]
    for key in neutral:
        if key not in NEUTRAL_MAPS["keys"]:
            errors.append(f"textures.neutral: unknown map {key!r}")
    for key in NEUTRAL_MAPS["required"]:
        if key not in neutral:
            errors.append(f"textures.neutral: missing map {key!r}")
    if not errors and ("W2" in neutral) != (len(layout) == 3):  # W0/W1 always (noise, detail), W2 for group 3
        errors.append(f"textures.neutral: W2 goes with a third weight group (weight_layout has {len(layout)})")
    if NEUTRAL_MAPS["distinct_files"] and len(set(neutral.values())) != len(neutral):
        errors.append("textures.neutral: every map needs its own file")
    return errors


def _check_paint(paint) -> List[str]:
    """Root key ``paint``: a built-in scheme by name, or a custom scheme as data (name + every scheme key)."""
    from .paint import BUILTIN_PAINTS, check_scheme

    if isinstance(paint, str):
        return [] if paint in BUILTIN_PAINTS else [f"paint: {paint!r} is no built-in scheme "
                                                   f"({', '.join(sorted(BUILTIN_PAINTS))})"]
    if not isinstance(paint, dict):
        return ["paint: expected a scheme name or {name, ...scheme}"]
    name = paint.get("name")
    if not isinstance(name, str) or not name or not all(c.isalnum() or c == "_" for c in name):
        return ["paint.name: letters, digits and _ only"]
    if name in BUILTIN_PAINTS:
        return [f"paint.name: {name!r} is a built-in scheme - name it as a text"]
    try:
        check_scheme({k: v for k, v in paint.items() if k != "name"}, "paint")
    except ValueError as exc:
        return [str(exc)]
    missing = [m for m in PAINT_SCHEME["painted"] if m not in paint["colors"]]
    if missing:
        return [f"paint.colors: missing {', '.join(missing)} (a sidecar carries the complete scheme)"]
    return []


def _baked_files(data, sidecar_path: str) -> List[str]:
    """Baked and neutral maps the sidecar names but the export lacks (paths relative to the sidecar, like Unity
    resolves them)."""
    tex = data.get("textures")
    if not isinstance(tex, dict):
        return []
    folder = os.path.dirname(os.path.abspath(sidecar_path))
    missing = []
    for section in ("baked", "neutral"):
        if isinstance(tex.get(section), dict):
            missing += [f"textures.{section}.{key}: file {path!r} missing"
                        for key, path in sorted(tex[section].items())
                        if isinstance(path, str) and not os.path.isfile(os.path.normpath(os.path.join(folder, path)))]
    zone_map = tex.get("zones", {}).get("map") if isinstance(tex.get("zones"), dict) else None
    if isinstance(zone_map, str) and not os.path.isfile(os.path.normpath(os.path.join(folder, zone_map))):
        missing.append(f"textures.zones.map: file {zone_map!r} missing")
    return missing


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


def check_export(models_dir: str, version: int = CONTRACT_VERSION) -> Dict[str, Dict[str, List[str]]]:
    """Every ``*.cubegen.json`` below ``models_dir`` (with its FBX and its baked maps) for an importer of contract
    ``version``: {model: {errors, open}}."""
    result = {}
    for folder, _, files in os.walk(models_dir):
        for name in sorted(f for f in files if f.endswith(".cubegen.json")):
            path = os.path.join(folder, name)
            data, file_errors = read_sidecar(path)
            if data is None:
                result[name[: -len(".cubegen.json")]] = {"errors": file_errors, "open": []}
                continue
            errors, open_items = check_sidecar(data, path, version)
            errors = file_errors + errors + _baked_files(data, path)
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
           "CONTRACT_VERSION", "SUPPORTED_VERSIONS", "BAKED_MAPS", "NEUTRAL_MAPS", "ZONES", "EFFECTS", "PAINT_SCHEME", "contract_for",
           "baked_map_keys", "root_keys", "texture_keys", "check_version",
           "BEHAVIOURS", "ROOT_KEYS", "RUNTIME_BUDGET", "check_runtime_budget", "glb_summary", "texture_bytes"]


# --------------------------------------------------------------------------
# runtime budget of Cube Escape's workbench (GLB path)
# --------------------------------------------------------------------------

#: what the workbench imports at most per player model - Cube Escape ``CubegenImportBudget`` and
#: ``CubegenGlb.Limits.MaxBytes`` (checked 0.21.0). Limits on files and memory are BYTES: a UTF-8 character takes up
#: to three bytes, so a string's length is never compared with them (Cube Escape 0.49 found that mix-up in a reader).
#: Texture memory as Cube Escape 0.51 counts it (``CubegenTextures``): every different (role, image content) once.
RUNTIME_BUDGET = {"glb_bytes": 32 * 1024 * 1024, "triangles": 60_000, "parts": 512, "materials": 32,
                  "textures": 16, "texture_size": 2048, "texture_bytes": 64 * 1024 * 1024}


def texture_bytes(width: int, height: int) -> int:
    """GPU memory of a texture as Cube Escape 0.51 loads it: compressed BC3/DXT5 (1 byte per pixel) with its mip chain
    (x 4/3). Until 0.21.0: RGBA32 (4 bytes per pixel) - four times too much."""
    return width * height * 4 // 3


#: glTF texture slot -> the role Cube Escape loads it as. The metal/roughness source is converted into one
#: metallic-gloss map (the source is not kept), so it counts once, as that role.
TEXTURE_ROLES = (("baseColorTexture", "albedo"), ("metallicRoughnessTexture", "metallic_gloss"),
                 ("normalTexture", "normal"), ("emissiveTexture", "emission"), ("occlusionTexture", "occlusion"))


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
    import hashlib

    images, contents = [], []
    for image in gltf.get("images", []):
        view = views[image["bufferView"]] if "bufferView" in image else None
        blob = binary[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]] if view else b""
        if blob[:8] == b"\x89PNG\r\n\x1a\n":
            images.append(struct.unpack_from(">II", blob, 16))
        else:
            images.append(None)  # external or not a PNG: size unknown here
        contents.append(hashlib.sha256(blob).hexdigest() if blob else f"image:{len(contents)}")
    # what the materials load: (role, image content) - the same PNG bytes in the same role load once
    sources = [t.get("source") for t in gltf.get("textures", [])]
    used = {}
    for material in gltf.get("materials", []):
        slots = dict(material.get("pbrMetallicRoughness", {}), **material)
        for slot, role in TEXTURE_ROLES:
            ref = slots.get(slot)
            if isinstance(ref, dict) and ref.get("index") is not None and ref["index"] < len(sources):
                image = sources[ref["index"]]
                if image is not None and image < len(images):
                    used[(role, contents[image])] = images[image]
    return {"bytes": len(data), "length": length, "nodes": len(gltf.get("nodes", [])),
            "materials": len(gltf.get("materials", [])), "triangles": triangles, "images": images,
            "textures": [{"role": role, "content": content[:12], "size": size}
                         for (role, content), size in sorted(used.items(), key=lambda kv: kv[0])]}


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
    # Cube Escape 0.51: every different (role, image content) a material loads, once
    known = [t["size"] for t in info["textures"] if t["size"]]
    if len(info["textures"]) > rules["textures"]:
        found.append(f"{len(info['textures'])} textures > {rules['textures']}")
    too_big = [f"{w}x{h}" for w, h in known if max(w, h) > rules["texture_size"]]
    if too_big:
        found.append(f"textures larger than {rules['texture_size']} px: {', '.join(too_big)}")
    memory = sum(texture_bytes(w, h) for w, h in known)
    if memory > rules["texture_bytes"]:
        found.append(f"texture memory {memory} bytes > {rules['texture_bytes']}")
    return found
