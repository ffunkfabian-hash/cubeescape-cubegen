"""Model families: kits whose types fit together optically AND geometrically.

A family is a recipe (``cubegen/family_data/<name>.json`` or any recipe file)
with two more keys:

* ``"family"`` - its name
* ``"dims"``   - the binding measures every member follows: wall height and
  thickness, module length, door / window openings, walkway width, rail and
  deck height, platform size, pipe radius and axis height ...

Everything else is the ordinary recipe format: ``seed``, ``style`` (materials,
glow, warning paint, wear, detail, grid snapping, theme), the texture keys,
``params`` and ``models`` (the kit). A recipe that says ``"family": "station"``
starts from that family; its own keys are the explicit deviations, and they
are recorded as such in the manifest.

:data:`DIMS` maps every measure to the parameters of the types that follow it
- the one place where "the door fits the wall" is defined. A shared seed alone
doesn't make parts fit; the measures do. Rolled details (panel layouts,
stripes, wear ...) still vary per variant.

Connectors (:func:`connectors`) describe where a model joins others: walkway
ends, wall ends, openings, door frames, pipe ends - position, direction and
size. :func:`fit_report` places the members of a kit against each other and
checks sizes, positions, directions, free passages and collision shapes.
"""

from __future__ import annotations

import itertools
import json
import math
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .geometry import euler_matrix, mat_mul_vec

FAMILY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "family_data")

# measure -> (label, [(type, parameter)]) - every type listed follows the measure
DIMS: Dict[str, Tuple[str, Tuple[Tuple[str, str], ...]]] = {
    "wall_height": ("Wandhöhe (m)", (("wall", "height"), ("window_wall", "height"), ("wall_corner", "height"))),
    "wall_thickness": ("Wandstärke (m)", (("wall", "thickness"), ("window_wall", "thickness"),
                                          ("wall_corner", "thickness"))),
    "module": ("Modullänge (m)", (("wall", "length"), ("catwalk", "length"), ("pipe", "length"),
                                  ("retractable_bridge", "length"), ("window_wall", "length"),
                                  ("cable_tray", "length"))),
    "door_style": ("Tür-Stil (Rahmenprofil)",
                   (("door", "style"), ("wall", "door_style"), ("portal_frame", "frame_style"))),
    "door_width": ("Türöffnung Breite (m)", (("door", "width"), ("wall", "door_width"), ("portal_frame", "width"))),
    "door_height": ("Türöffnung Höhe (m)",
                    (("door", "height"), ("wall", "door_height"), ("portal_frame", "height"))),
    "window_width": ("Fenster Breite (m)", (("wall", "window_width"),)),
    "window_height": ("Fenster Höhe (m)", (("wall", "window_height"),)),
    "window_sill": ("Fenster Brüstung (m)", (("wall", "window_sill"), ("window_wall", "sill"))),
    "walk_width": ("Laufstegbreite (m)", (("catwalk", "width"), ("retractable_bridge", "width"),
                                          ("stairs", "width"))),
    "rail_height": ("Geländerhöhe (m)", (("catwalk", "rail_height"), ("railing", "height"))),
    "deck_height": ("Höhe der oberen Ebene (m)", (("stairs", "rise"), ("lift", "travel"))),
    "platform_size": ("Plattformgröße (m)", (("platform", "size"), ("phase_platform", "size"),
                                             ("turntable", "size"), ("breakable_platform", "size"))),
    "pipe_radius": ("Rohr-Radius (m)", (("pipe", "radius"), ("pipe_bend", "radius"), ("wall", "duct_radius"),
                                        ("fluid_basin", "pipe_radius"))),
    "pipe_height": ("Rohr-Achshöhe (m)", (("pipe", "axis_height"), ("pipe_bend", "axis_height"),
                                          ("wall", "duct_height"), ("wall", "pipe_height"),
                                          ("fluid_basin", "outlet_height"))),
}

# types with a measure built in that they can't change: a family with another value can't use them
FIXED: Dict[Tuple[str, str], float] = {}

TOL = 0.01  # 1 cm, like the Unity importer's pivot tolerance


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

def family_files() -> Dict[str, str]:
    """Built-in families (name -> file)."""
    if not os.path.isdir(FAMILY_DIR):
        return {}
    return {name[:-5]: os.path.join(FAMILY_DIR, name) for name in sorted(os.listdir(FAMILY_DIR))
            if name.endswith(".json")}


def find_family(name: str, base_dir: Optional[str] = None) -> str:
    """Path of a family given by name (built-in or ./families/<name>.json) or by path."""
    candidates = [name] if name.endswith(".json") else []
    for folder in filter(None, (base_dir, os.getcwd())):
        candidates += [os.path.join(folder, "families", f"{name}.json"), os.path.join(folder, f"{name}.json")]
    candidates.append(os.path.join(FAMILY_DIR, f"{name}.json"))
    for path in candidates:
        if os.path.isfile(path):
            return path
    raise ValueError(f"unknown family {name!r}; available: {', '.join(family_files()) or '-'}")


def check_dims(dims: Dict[str, Any], where: str = "dims") -> Dict[str, Any]:
    """Validate measures: known names, values at least one mapped parameter accepts (each type that is
    built checks its own range in :func:`derived_params`)."""
    from .models import REGISTRY

    out = {}
    for key, value in dims.items():
        if key.startswith("_"):
            continue
        if key not in DIMS:
            import difflib

            close = difflib.get_close_matches(key, list(DIMS), n=1)
            raise ValueError(f"{where}: unknown measure {key!r}{f' (did you mean {close[0]!r}?)' if close else ''}"
                             f"; known: {', '.join(DIMS)}")
        errors = []
        for model_type, param in DIMS[key][1]:
            try:
                REGISTRY[model_type].param(param).parse(value)
            except (ValueError, KeyError) as exc:
                errors.append(f"{model_type}.{param}: {exc}")
        if len(errors) == len(DIMS[key][1]):
            raise ValueError(f"{where}.{key} = {value!r} fits no parameter: {'; '.join(errors)}")
        out[key] = value
    return out


def derived_params(dims: Dict[str, Any], types: Iterable[str]) -> Dict[str, Dict[str, Tuple[Any, str]]]:
    """{type: {parameter: (value, "dims.<measure>")}} for the given types."""
    from .models import REGISTRY

    types = set(types)
    result: Dict[str, Dict[str, Tuple[Any, str]]] = {}
    for key, value in dims.items():
        for model_type, param in DIMS.get(key, ("", ()))[1]:
            if model_type in types:
                try:
                    parsed = REGISTRY[model_type].param(param).parse(value)
                except ValueError as exc:
                    raise ValueError(f"{model_type} can't follow {key} = {value!r}: {exc}") from None
                result.setdefault(model_type, {})[param] = (parsed, f"dims.{key}")
    for (model_type, key), fixed in FIXED.items():
        if model_type in types and key in dims and abs(float(dims[key]) - fixed) > 1e-9:
            raise ValueError(f"{model_type} has a fixed {key} of {fixed} m - it can't follow {key} = {dims[key]} "
                             "(use wall with an opening instead)")
    return result


def misfits(dims: Dict[str, Any], types: Iterable[str]) -> Dict[str, str]:
    """{type: reason} for the types that can't follow these measures (a fixed size, a value out of range)."""
    out = {}
    for model_type in types:
        try:
            derived_params(dims, [model_type])
        except ValueError as exc:
            out[model_type] = str(exc)
    return out


def load_family(name_or_path: str, base_dir: Optional[str] = None) -> Dict[str, Any]:
    """The family recipe (checked like any recipe, plus "family" and "dims")."""
    from .cli import load_recipe

    path = find_family(name_or_path, base_dir)
    data = load_recipe(path, family_file=True)
    if not isinstance(data.get("family"), str) or not data["family"]:
        raise ValueError(f"{path}: a family file needs \"family\": \"<name>\"")
    data["dims"] = check_dims(data.get("dims", {}), f"{path}: dims")
    data["_path"] = path
    return data


def dims_from_model(rig: Dict[str, Any]) -> Dict[str, Any]:
    """Measures an existing model (its .cubegen.json) fixes - for a matching addition (``--match``)."""
    model_type, params = rig.get("type"), rig.get("params") or {}
    dims: Dict[str, Any] = {}
    for key, (_, members) in DIMS.items():
        for t, param in members:
            if t == model_type and param in params and key not in dims:
                dims[key] = params[param]
    if model_type == "door":  # the door's own size (rig params hold the generated values)
        dims.setdefault("door_style", params.get("style"))
    return {k: v for k, v in dims.items() if v is not None}


# ---------------------------------------------------------------------------
# resolution: family -> recipe -> kit entry -> command line / add-on
# ---------------------------------------------------------------------------

def resolve(family: Optional[Dict[str, Any]], recipe: Optional[Dict[str, Any]], models: Optional[Dict] = None,
            extra_params: Optional[Dict[str, Dict[str, Any]]] = None, extra_style: Optional[Dict[str, Any]] = None,
            match: Optional[Dict[str, Any]] = None, extra_source: str = "cli") -> Dict[str, Any]:
    """Merge a family, a recipe on top of it and command line / add-on values; record where each value comes from.

    Returns {"values": recipe-like dict (seed, style, params, models, variant_params, other keys),
    "param_sources": {type: {param: source}}, "family": manifest info or None}.
    """
    family = family or {}
    recipe = recipe or {}
    dims = dict(family.get("dims", {}))
    deviations: List[Dict[str, Any]] = []
    if match:  # a matching addition: the measures the existing model fixes
        for key, value in dims_from_model(match).items():
            if key in dims and dims[key] != value:
                deviations.append({"what": f"dims.{key}", "family": dims[key], "used": value,
                                   "source": f"match:{match.get('model')}"})
            dims[key] = value
    for key, value in check_dims(recipe.get("dims", {}), "recipe dims").items():
        if key in dims and dims[key] != value:
            deviations.append({"what": f"dims.{key}", "family": dims[key], "used": value, "source": "recipe"})
        dims[key] = value
    values: Dict[str, Any] = {k: v for k, v in family.items() if k not in ("family", "dims", "description", "_path",
                                                                           "params", "style", "variant_params")}
    values.update({k: v for k, v in recipe.items() if k not in ("family", "dims", "description", "_path", "params",
                                                                "style", "variant_params")})
    style = dict((match or {}).get("style") or {})
    if match and "generation" not in style:  # sidecars without a generation were built by cubegen 0.9.0 or older
        style["generation"] = 1
    style = {k: v for k, v in style.items() if v is not None and k in ("material", "glow", "warning", "wear",
                                                                       "detail", "snap", "theme", "generation")}
    style.update(family.get("style", {}))
    style.update(recipe.get("style", {}))
    style.update(extra_style or {})
    values["style"] = style
    if models is not None:
        values["models"] = models
        variant_params: Dict[str, Dict[int, Dict[str, Any]]] = {}
    else:
        values.setdefault("models", {})
        variant_params = recipe.get("variant_params") if "models" in recipe else family.get("variant_params")
        variant_params = variant_params or {}
    types = list(values["models"])
    params: Dict[str, Dict[str, Any]] = {}
    sources: Dict[str, Dict[str, str]] = {}

    from .models import REGISTRY

    def put(layer, source):
        for t, entries in (layer or {}).items():
            for name, value in entries.items():
                if t in REGISTRY:
                    value = REGISTRY[t].param(name).parse(value)  # "2.0" from the command line = 2.0
                old = params.get(t, {}).get(name)
                if t in params and name in params[t] and old != value and sources[t][name].startswith("dims"):
                    deviations.append({"what": f"params.{t}.{name}", "family": old, "used": value, "source": source})
                params.setdefault(t, {})[name] = value
                sources.setdefault(t, {})[name] = source

    put({t: {k: v for k, (v, _) in d.items()} for t, d in derived_params(dims, types).items()}, "dims")
    for t, d in derived_params(dims, types).items():
        for k, (_, src) in d.items():
            sources[t][k] = src
    put(family.get("params"), "family")
    put(recipe.get("params"), "recipe")
    put(extra_params, extra_source)
    values["params"] = params
    values["variant_params"] = variant_params
    info = None
    if family or match:
        info = {"name": family.get("family") or f"match:{(match or {}).get('model')}",
                "file": family.get("_path"), "description": family.get("description", ""), "dims": dims,
                "deviations": deviations}
        if match:  # the existing model, rebuilt for the fit checks from its seed, parameters and style
            info["reference"] = {k: match.get(k) for k in ("model", "type", "seed", "params", "style")}
    return {"values": values, "param_sources": sources, "family": info}


# ---------------------------------------------------------------------------
# connectors
# ---------------------------------------------------------------------------

def _con(name, kind, pos, direction, **dims) -> Dict[str, Any]:
    return {"name": name, "kind": kind, "pos": tuple(float(c) for c in pos),
            "dir": tuple(float(c) for c in direction), **dims}


def connectors(asset, model_type: str) -> List[Dict[str, Any]]:
    """Where a model joins others (asset space: metres, Z up, front -Y)."""
    from .models.kit import CATWALK_ARMS, stair_flights

    meta, params = asset.meta, asset.meta.get("params", {})
    out: List[Dict[str, Any]] = []
    if model_type == "catwalk":
        ln, w = meta["length_m"], meta["width_m"]
        shape = params.get("shape", meta.get("shape", "straight"))
        for dx, dy in CATWALK_ARMS[shape]:
            out.append(_con(f"walk_{dx:+d}{dy:+d}", "walk", (dx * ln / 2, dy * ln / 2, 0), (dx, dy, 0), width=w))
    elif model_type == "retractable_bridge":
        span, w = meta["length_m"], meta["width_m"]
        out.append(_con("landing", "walk", (-span, 0, 0), (-1, 0, 0), width=w))
        out.append(_con("deck_out", "walk", (span, 0, 0), (1, 0, 0), width=w,
                        moves={"part": "Deck", "offset": (span, 0.0, 0.3)}))
    elif model_type == "stairs":
        w, rise = params["width"], params["rise"]
        if meta.get("layout"):
            geo = stair_flights(meta["layout"], w, rise)
            (bp, bd), (tp, td) = geo["bottom"], geo["top"]
        else:
            run = meta["run_m"]
            bp, bd, tp, td = (0, -run / 2, 0), (0, -1), (0, run / 2, rise), (0, 1)
        out.append(_con("bottom", "floor_walk", bp, (bd[0], bd[1], 0), width=w))  # on the ground floor
        out.append(_con("top", "walk", tp, (td[0], td[1], 0), width=w))
    elif model_type in ("platform", "phase_platform", "turntable", "breakable_platform"):
        s = meta.get("outer_m", meta["size_m"])
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            out.append(_con(f"edge_{dx:+d}{dy:+d}", "walk_edge", (dx * s / 2, dy * s / 2, 0), (dx, dy, 0), width=s))
    elif model_type == "wall":
        ln = meta["length_m"]
        h, t = params.get("height", 3.0), params.get("thickness", 0.5)
        for s in (-1, 1):
            out.append(_con(f"end_{s:+d}", "wall_end", (s * ln / 2, 0, 0), (s, 0, 0), height=h, thickness=t))
        hole = meta.get("opening")
        if hole:
            kind = {"door": "opening", "window": "window", "pipe": "duct"}[hole["kind"]]
            pos = (hole["center_x"], 0, hole["z0"] if kind != "duct" else hole["duct_height"])
            out.append(_con(hole["kind"], kind, pos, (0, -1, 0), width=hole["width"], height=hole["height"],
                            thickness=t, **({"radius": hole["duct_radius"]} if kind == "duct" else {})))
    elif model_type == "window_wall":
        ln = meta["length_m"]
        h, t = params.get("height", 3.0), params.get("thickness", 0.5)
        for s in (-1, 1):
            out.append(_con(f"end_{s:+d}", "wall_end", (s * ln / 2, 0, 0), (s, 0, 0), height=h, thickness=t))
    elif model_type == "wall_corner":  # walls join the faces that aren't exposed
        h, t = params.get("height", 3.0), params.get("thickness", 0.5)
        sides = {"corner": ((1, 0), (0, 1)), "end": ((1, 0),), "tee": ((-1, 0), (1, 0), (0, 1))}[meta["style"]]
        for dx, dy in sides:
            out.append(_con(f"end_{dx:+d}{dy:+d}", "wall_end", (dx * t / 2, dy * t / 2, 0), (dx, dy, 0), height=h,
                            thickness=t))
    elif model_type == "door":
        from .models.environment import door_frame_outer

        w, h = meta["opening_m"]
        ow, oh = door_frame_outer(meta["style"], w, h)
        out.append(_con("frame", "door", (0, 0, 0), (0, -1, 0), width=ow, height=oh, clear=(w, h)))
    elif model_type == "portal_frame" and meta.get("mount") == "wall":
        (ow, oh), (w, h) = meta["outer_m"], meta["opening_m"]
        out.append(_con("frame", "door", (0, 0, 0), (0, -1, 0), width=ow, height=oh, clear=(w, h)))
    elif model_type == "pipe":
        r, ln = meta["radius"], meta["length"]
        z = _axis(params, r)
        for s in (-1, 1):
            out.append(_con(f"end_{s:+d}", "pipe", (s * ln / 2, 0, z), (s, 0, 0), radius=r))
    elif model_type == "pipe_bend":
        from .models.machinery import BEND_ARMS

        r, arm = meta["radius"], meta["arm_m"]
        z = _axis(params, r)
        for d in BEND_ARMS[meta["kind"]]:  # the up arm of elbow_up rises: it joins no horizontal pipe
            kind = "pipe" if d[2] == 0 else "pipe_up"
            out.append(_con(f"arm_{d[0]:+d}{d[1]:+d}{d[2]:+d}", kind, (d[0] * arm, d[1] * arm, z + d[2] * arm), d,
                            radius=r))
    elif model_type == "fluid_basin":
        r = params.get("pipe_radius", 0.09)
        if "outlet" in meta.get("pipe_ends", {}):  # the inlet pours in over the rim: no pipe joint
            out.append(_con("outlet", "pipe", meta["pipe_ends"]["outlet"], (-1, 0, 0), radius=r))
    return out


def _axis(params, r) -> float:
    return max(params["axis_height"], r + 0.15)


def unity_connectors(asset, model_type: str) -> List[Dict[str, Any]]:
    """Connectors in Unity coordinates (for the manifest)."""
    from .asset import to_unity

    result = []
    for c in connectors(asset, model_type):
        entry = {k: v for k, v in c.items() if k not in ("pos", "dir", "moves")}
        entry["position"] = list(to_unity(c["pos"]))
        entry["direction"] = list(to_unity(c["dir"]))
        if "clear" in entry:
            entry["clear"] = [round(v, 4) for v in entry["clear"]]
        for key in ("width", "height", "thickness", "radius"):
            if key in entry:
                entry[key] = round(entry[key], 4)
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# collision shapes as the game builds them (for the fit checks)
# ---------------------------------------------------------------------------

class Box:
    """Oriented box: centre, rotation matrix (columns = axes), half sizes."""

    def __init__(self, center, rot, half, part=None):
        self.center, self.rot, self.half, self.part = tuple(center), rot, tuple(half), part

    def contains(self, point, margin=0.0) -> bool:
        d = [point[i] - self.center[i] for i in range(3)]
        for k in range(3):
            axis = (self.rot[0][k], self.rot[1][k], self.rot[2][k])
            if abs(sum(d[i] * axis[i] for i in range(3))) > self.half[k] - margin:
                return False
        return True

    def top_at(self, x, y) -> Optional[float]:
        """Height of the box's top face over (x, y) - level or sloped (ramps) - None outside its footprint."""
        k = max(range(3), key=lambda i: abs(self.rot[2][i]))  # the axis closest to vertical
        sign = 1.0 if self.rot[2][k] > 0 else -1.0
        n = [sign * self.rot[i][k] for i in range(3)]  # top face normal
        c = [self.center[i] + n[i] * self.half[k] for i in range(3)]  # top face centre
        z = c[2] - (n[0] * (x - c[0]) + n[1] * (y - c[1])) / n[2]
        inside = self.contains((x, y, z - 1e-4 * n[2]), margin=-1e-6)
        return z if inside else None

    def moved(self, offset):
        return Box(tuple(self.center[i] + offset[i] for i in range(3)), self.rot, self.half, self.part)

    def placed(self, rot_z, offset):
        r = euler_matrix(0.0, 0.0, rot_z)
        center = tuple(mat_mul_vec(r, self.center)[i] + offset[i] for i in range(3))
        rot = [[sum(r[i][k] * self.rot[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
        return Box(center, rot, self.half, self.part)


def collision_boxes(asset, model_type: str) -> List[Box]:
    """The collision shapes the Unity import builds: explicit colliders (mesh colliders as their part's box),
    else the Door/Machine collider parts, else one box around everything (the static envelope)."""
    ident = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    boxes = []
    if asset.colliders:
        for c in asset.colliders:
            if c.kind == "box":
                boxes.append(Box(c.center, euler_matrix(*c.rot), tuple(s / 2 for s in c.size), c.part))
            else:
                lo, hi = asset.get(c.part).mesh.bbox()
                boxes.append(Box([(lo[i] + hi[i]) / 2 for i in range(3)], ident,
                                 [(hi[i] - lo[i]) / 2 for i in range(3)], c.part))
        return boxes
    parts = []
    for b in asset.behaviours:
        for role in ("colliders", "body"):
            value = b["parts"].get(role)
            parts += value if isinstance(value, list) else ([value] if value else [])
    if parts:
        for name in dict.fromkeys(parts):
            obj = asset.get(name)
            if obj is not None and obj.mesh is not None:
                lo, hi = obj.mesh.bbox()
                boxes.append(Box([(lo[i] + hi[i]) / 2 for i in range(3)], ident,
                                 [(hi[i] - lo[i]) / 2 for i in range(3)], name))
        return boxes
    lo, hi = asset.bbox()
    return [Box([(lo[i] + hi[i]) / 2 for i in range(3)], ident, [(hi[i] - lo[i]) / 2 for i in range(3)])]


# ---------------------------------------------------------------------------
# fit checks
# ---------------------------------------------------------------------------

def _yaw(direction) -> float:
    return math.atan2(direction[1], direction[0])


def _place(b_con, a_con):
    """Rotation about Z and offset that put connector b onto connector a, facing it."""
    rot = _yaw(a_con["dir"]) + math.pi - _yaw(b_con["dir"])
    r = euler_matrix(0.0, 0.0, rot)
    bp = mat_mul_vec(r, b_con["pos"])
    return rot, tuple(a_con["pos"][i] - bp[i] for i in range(3))


def _boxes_for(asset, model_type, con):
    boxes = collision_boxes(asset, model_type)
    moves = con.get("moves")
    if moves:
        boxes = [b.moved(moves["offset"]) if b.part == moves["part"] else b for b in boxes]
    return boxes


def check_walk(a, a_type, ca, b, b_type, cb) -> List[str]:
    """Walkway joint: same width (an edge must be at least as wide), no gap, nothing blocking the passage."""
    problems = []
    width = min(ca["width"], cb["width"])
    if ca["kind"] == cb["kind"] == "walk" and abs(ca["width"] - cb["width"]) > TOL:
        problems.append(f"width {ca['width']:.3f} m vs {cb['width']:.3f} m")
    rot, offset = _place(cb, ca)
    boxes = _boxes_for(a, a_type, ca) + [box.placed(rot, offset) for box in _boxes_for(b, b_type, cb)]
    level = ca["pos"][2]
    dx, dy = ca["dir"][0], ca["dir"][1]
    px, py = -dy, dx  # across the walkway
    gaps = 0
    for side in (-0.06, 0.06):  # floor on both sides of the joint, across 80 % of the width
        for f in (-0.4, -0.2, 0.0, 0.2, 0.4):
            x = ca["pos"][0] + dx * side + px * f * width
            y = ca["pos"][1] + dy * side + py * f * width
            tops = [t for t in (box.top_at(x, y) for box in boxes) if t is not None]
            if not any(abs(t - level) <= 0.03 for t in tops):
                gaps += 1
    if gaps:
        problems.append(f"{gaps} of 10 floor samples at the joint have no walkable collider at {level:.2f} m")
    blocked = []
    half = max(0.05, width / 2 - 0.12)  # rails stand on the deck edges
    for along in (-0.3, -0.1, 0.1, 0.3):
        for f in (-1.0, -0.5, 0.0, 0.5, 1.0):
            for z in (0.15, 0.6, 1.2, 1.9):
                pt = (ca["pos"][0] + dx * along + px * f * half, ca["pos"][1] + dy * along + py * f * half,
                      level + z)
                if any(box.contains(pt) for box in boxes):
                    blocked.append(pt)
    if blocked:
        problems.append(f"{len(blocked)} points of the passage above the joint are inside a collider")
    return problems


def check_door(wall, wall_type, cw, door, door_type, cd) -> List[str]:
    """Door (or portal) in a wall opening: the frame fills the cut-out, the clear opening stays free."""
    problems = []
    if abs(cw["width"] - cd["width"]) > TOL or abs(cw["height"] - cd["height"]) > TOL:
        problems.append(f"opening {cw['width']:.3f} x {cw['height']:.3f} m, frame {cd['width']:.3f} x "
                        f"{cd['height']:.3f} m")
    offset = (cw["pos"][0], 0.0, 0.0)
    boxes = collision_boxes(wall, wall_type) + [
        b.placed(0.0, offset) for b in collision_boxes(door, door_type)
        if b.part not in ("Panel", "Panel_B", "Surface")]  # leaves open, the portal surface has no collider
    cwid, chei = cd["clear"]
    blocked = 0
    for fx in (-0.45, -0.25, 0.0, 0.25, 0.45):
        for fz in (0.05, 0.3, 0.6, 0.9):
            for y in (-0.6, -0.2, 0.2, 0.6):
                pt = (offset[0] + fx * (cwid - 0.1), y, 0.05 + fz * (chei - 0.15))
                if any(b.contains(pt) for b in boxes):
                    blocked += 1
    if blocked:
        problems.append(f"{blocked} points of the clear passage are inside a collider")
    return problems


def check_pipe(a, a_type, ca, b, b_type, cb) -> List[str]:
    """Pipe joint: same radius and axis height (both stand on the floor)."""
    problems = []
    if abs(ca["radius"] - cb["radius"]) > 1e-6:
        problems.append(f"radius {ca['radius']} vs {cb['radius']}")
    if abs(ca["pos"][2] - cb["pos"][2]) > TOL:
        problems.append(f"axis height {ca['pos'][2]:.3f} vs {cb['pos'][2]:.3f} m")
    return problems


def check_duct(wall, wall_type, cw, pipe, pipe_type, cp) -> List[str]:
    """Pipe through a wall pass-through: same axis height, room for the flange, nothing in the pipe's way."""
    problems = []
    r = cp["radius"]
    if abs(cw["pos"][2] - cp["pos"][2]) > TOL:
        problems.append(f"pass-through at {cw['pos'][2]:.3f} m, pipe axis at {cp['pos'][2]:.3f} m")
    if cw["width"] < 2 * r * 1.25 + 0.02:
        problems.append(f"pass-through {cw['width']:.3f} m too small for the flange ({2 * r * 1.25:.3f} m)")
    boxes = collision_boxes(wall, wall_type)
    zc, xc = cw["pos"][2], cw["pos"][0]
    hits = 0
    for k in range(12):
        ang = 2 * math.pi * k / 12
        for y in (-cw["thickness"] / 2 - 0.05, 0.0, cw["thickness"] / 2 + 0.05):
            pt = (xc + math.cos(ang) * r, y, zc + math.sin(ang) * r)
            if any(b.contains(pt) for b in boxes):
                hits += 1
    if hits:
        problems.append(f"{hits} points on the pipe surface are inside the wall's colliders")
    return problems


def check_wall_ends(a, a_type, ca, b, b_type, cb) -> List[str]:
    problems = []
    for key in ("height", "thickness"):
        if abs(ca[key] - cb[key]) > TOL:
            problems.append(f"wall {key} {ca[key]:.3f} vs {cb[key]:.3f} m")
    return problems


RULES = {  # (kind A, kind B) -> check
    ("walk", "walk"): check_walk, ("walk", "walk_edge"): check_walk,
    ("opening", "door"): check_door, ("duct", "pipe"): check_duct,
    ("pipe", "pipe"): check_pipe, ("wall_end", "wall_end"): check_wall_ends,
}


def fit_report(members: Sequence[Tuple[str, Any, str]], dims: Optional[Dict[str, Any]] = None
               ) -> List[Dict[str, Any]]:
    """Check every compatible connector pair of a kit. ``members`` = [(name, asset, type)].

    Returns one entry per checked joint: {"a", "b", "joint", "problems"} (empty problems = fits).
    With the family ``dims``: walkway ends of floor-standing models (stairs tops) must reach the upper
    level (``deck_height``) - walkway pieces with their top at z = 0 are placed there - and lifts must
    travel to it.
    """
    cons = [(name, asset, t, connectors(asset, t)) for name, asset, t in members]
    report = []
    level = (dims or {}).get("deck_height")
    if level is not None:
        for name, asset, t, cs in cons:
            for c in cs:
                if c["kind"] == "walk" and c["pos"][2] > 1e-6 and abs(c["pos"][2] - level) > TOL:
                    report.append({"a": name, "b": "-", "joint": f"{c['name']} level",
                                   "problems": [f"reaches {c['pos'][2]:.3f} m, the upper level is {level} m"]})
            if t == "lift" and abs(asset.meta.get("travel_m", level) - level) > TOL:
                report.append({"a": name, "b": "-", "joint": "travel",
                               "problems": [f"travels {asset.meta['travel_m']} m, the upper level is {level} m"]})
    for (na, a, ta, ca_list), (nb, b, tb, cb_list) in itertools.permutations(cons, 2):
        for ca in ca_list:
            for cb in cb_list:
                rule = RULES.get((ca["kind"], cb["kind"]))
                if rule is None or (ca["kind"] == cb["kind"] and na > nb):
                    continue  # symmetric joints once
                report.append({"a": na, "b": nb, "joint": f"{ca['name']} <-> {cb['name']}",
                               "problems": rule(a, ta, ca, b, tb, cb)})
    return report


def same_look(specs: Sequence[Dict[str, Any]]) -> List[str]:
    """Members must share material, glow, warning paint, wear, detail, snapping and textures."""
    from .params import Style

    keys = ("material", "glow", "warning", "wear", "detail", "snap", "theme", "generation")
    looks = {}
    for spec in specs:
        style = Style.from_dict(spec.get("style")).resolved()
        looks[spec["name"]] = tuple(getattr(style, k) for k in keys)
    if len(set(looks.values())) > 1:
        return [f"different style settings: {sorted(set(looks.values()))}"]
    return []


__all__ = ["DIMS", "FIXED", "family_files", "find_family", "load_family", "check_dims", "derived_params",
           "misfits", "dims_from_model", "connectors", "unity_connectors", "collision_boxes", "fit_report", "same_look"]
