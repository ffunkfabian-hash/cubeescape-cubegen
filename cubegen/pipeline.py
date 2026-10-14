"""Batch pipeline: seeds -> Blender (export, previews, overview .blend) -> ImageMagick (icons, sheet) -> manifest."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from . import __version__
from .blender import BlenderError, blender_version, find_blender, resolve_engine, run_job
from .imagemagick import ImageMagick, ImageMagickError
from .cache import OutputCache, input_key
from .asset import to_unity
from .models import REGISTRY, asset_name, generate_asset, model_types
from .objwriter import write_mtl, write_obj
from .params import Style
from .materials import KEEP_OWN, LEGACY_NAMES, MATERIALS
from .textures import TEXTURE_MODES, build_texture_set, plan_texture_set
from .paint import BUILTIN_PAINTS, PAINTS, check_paint, load_scheme, register_scheme
from .variety import pick_unique
from .contract import (CONTRACT_VERSION, baked_map_keys, check_fbx, check_runtime_budget, check_sidecar, check_version,
                       texture_keys)
from .families import join_table, unity_connectors
from . import palette as palette_mod

BAKE_KEEP = set(KEEP_OWN)  # = bake.KEEP
from .seeds import model_seed

FORMATS = ("fbx", "glb", "gltf", "obj")
BAKE_DEVICES = ("auto", "cpu", "gpu")  # = bake.DEVICES
#: the baked maps a sidecar names come from the contract (``contract.baked_map_keys``, section ``baked_maps``)

# Time budget per stage (seconds), measured 0.15.0 on an Apple M5 with headroom of about 3x; a slower stage only
# warns (log + manifest "timings"), it never fails a run. "per_model" counts the models built in this run.
# textures / images: wall clock of this process; bake / export / render: the Blender workers' own clocks, summed
# over parallel processes (so the budget does not depend on --jobs).
STAGE_BUDGETS = {
    "textures": {"total": 15.0, "scale": "texture"},     # 33 maps, 512 px: 4.8 s
    "bake": {"per_model": 4.0, "scale": "texture"},      # 512 px, joined copy: 1.0-1.7 s
    "export": {"per_model": 1.5},                        # FBX + contract check: 0.2-0.4 s
    "render": {"per_model": 3.0, "scale": "render"},     # Workbench, 384 px
    "images": {"per_model": 0.5},                        # icon (+ share of the contact sheet)
}


@dataclass
class BatchConfig:
    seed: int
    models: Dict[str, Union[int, List[int]]]  # type -> count (indices 0..n-1) or explicit variant indices
    out_dir: str
    unique: bool = False           # counts: skip variants that look like an earlier one (see variety.py)
    lods: bool = False             # static models: + low detail level, FBX objects <part>_LOD0 / _LOD1
    force: bool = False            # rebuild everything (default: reuse unchanged models of the last run)
    jobs: int = 0                  # Blender processes in parallel (work packages, biggest first); 0 = auto_jobs
    variant_set: bool = False      # --set: the variants of a type share variant 0's outline (OUTLINE_PARAMS) and differ
    #                                inside - pieces that stand side by side without repeating (manifest "sets")
    formats: List[str] = field(default_factory=lambda: ["fbx"])
    prefix: str = ""
    scale: float = 1.0
    blend: bool = True
    rig_data: bool = True  # write <Name>.cubegen.json (parts, pivots, script wiring) next to the models
    use_blender: bool = True
    render: bool = True
    engine: str = "auto"
    render_size: int = 384
    samples: int = 32
    icon_size: int = 256
    icon_background: Optional[str] = None
    models_dir: Optional[str] = None
    library_dir: Optional[str] = None  # static decoration goes to <library_dir>/<Category> (Unity: Art/Models/Library)
    icons_dir: Optional[str] = None
    params: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # type -> {parameter: value}
    variant_params: Dict[str, Dict[int, Dict[str, Any]]] = field(default_factory=dict)  # type -> {index: params}
    param_sources: Dict[str, Dict[str, str]] = field(default_factory=dict)  # type -> {parameter: where from}
    family: Optional[Dict[str, Any]] = None  # name, file, dims, deviations (families.resolve)
    style: Style = field(default_factory=Style)
    icon_azimuth: float = 33.0     # degrees, like the ICONS table of generate_assets.py (+ = from the right)
    icon_elevation: float = 31.0
    icon_zoom: float = 1.0         # > 1 = closer
    textures: str = "none"         # none | tiled (ImageMagick tile textures) | baked (+ per-asset grime atlas)
    #                                | palette (one MP_Palette material per model: 1 draw call, palette.py)
    texture_size: int = 512
    texture_set: str = ""          # name of the texture variant -> material names MT_<set>_<Material>
    palette: str = ""              # colour palette of palette mode (palette.COLOR_PALETTES) -> MP_Palette_<Name>;
    #                                "" / "standard" = the game's colours (MP_Palette); ignored in other modes
    textures_dir: Optional[str] = None  # default: <models dir>/Textures
    bake_device: str = "auto"      # --textures baked: auto (GPU from 1024 px) | cpu | gpu (bake.use_device)
    paint_file: str = ""           # custom paint scheme (JSON, paint.load_scheme): sets paint to its name
    paint_scheme: Optional[Dict[str, Any]] = None  # the loaded custom scheme (passed to the Blender worker)
    paint: str = ""                # paint scheme (paint.PAINTS): baked atlas composed from one neutral bake; needs
    #                                textures "baked"; decorative glow follows the scheme unless --glow says otherwise
    blender: Optional[str] = None
    magick: Optional[str] = None
    verbose: bool = False
    repair_safe: bool = False
    single_renderer: bool = False  # static models with decorative parts only: one mesh object (Asset.merge_static)
    contract: int = CONTRACT_VERSION  # the importer's contract version the sidecars are written for (--contract):
    #                                   1 = Cube Escape before the Emission map (the map stays in the manifest)

    def validate(self) -> None:
        check_version(self.contract)
        if self.paint_file:
            name, self.paint_scheme = load_scheme(self.paint_file)
            register_scheme(name, self.paint_scheme)
            self.paint = name
            if self.textures == "none":
                self.textures = "baked"
        if self.paint:
            check_paint(self.paint)
            if self.textures != "baked":
                raise ValueError("--paint needs --textures baked (the scheme is composed into a baked atlas)")
            if not self.use_blender:
                raise ValueError("--paint needs Blender (the neutral maps are baked) - not with --no-blender")
            if self.style.glow is None and not self.style.theme:  # the scheme's light (Industrial orange, Dark red);
                # an explicit --glow or a --theme (which rolls the glow) wins
                self.style = Style.from_dict(dict(self.style.to_dict(), glow=PAINTS[self.paint]["glow"]))
        unknown = [t for t in self.models if t not in model_types()]
        if unknown:
            raise ValueError(f"unknown model type(s): {', '.join(unknown)}. Available: {', '.join(model_types())}")
        bad = [f for f in self.formats if f not in FORMATS]
        if bad:
            raise ValueError(f"unknown format(s): {', '.join(bad)}. Available: {', '.join(FORMATS)}")
        for t, value in self.models.items():
            indices = value if isinstance(value, list) else [value]
            if any(not isinstance(i, int) or i < 0 for i in indices):
                raise ValueError(f"{t}: counts and variant indices must be integers >= 0")
        if isinstance(self.style, dict):
            self.style = Style.from_dict(self.style)
        self.style.validate()
        for t, overrides in self.params.items():
            if t not in REGISTRY:
                raise ValueError(f"--param: unknown model type {t!r}")
            for name, value in overrides.items():
                REGISTRY[t].param(name).parse(value)
        for t, variants in self.variant_params.items():
            if t not in REGISTRY:
                raise ValueError(f"models: unknown model type {t!r}")
            for index, overrides in variants.items():
                for name, value in overrides.items():
                    REGISTRY[t].param(name).parse(value)
        if self.textures not in TEXTURE_MODES:
            raise ValueError(f"textures must be one of {', '.join(TEXTURE_MODES)}")
        if self.texture_size < 64 or self.texture_size & (self.texture_size - 1):
            raise ValueError("texture size must be a power of two >= 64")
        if self.texture_set and not self.texture_set.replace("_", "").isalnum():
            raise ValueError("texture set: letters, digits and _ only")
        self.palette = palette_mod.check_palette(self.palette)
        if self.icon_zoom <= 0:
            raise ValueError("icon zoom must be > 0")
        if not isinstance(self.jobs, int) or isinstance(self.jobs, bool) or self.jobs < 0:
            raise ValueError("jobs must be a number >= 1 (or 0 = auto)")
        if self.bake_device not in BAKE_DEVICES:
            raise ValueError(f"bake device must be one of {', '.join(BAKE_DEVICES)}")
        if self.lods and self.textures == "baked":
            raise ValueError("--lods can't be combined with --textures baked (the atlas is baked per object)")


def _spec(config: BatchConfig, model_type: str, index: int) -> Dict:
    params = dict(config.params.get(model_type, {}))
    sources = dict(config.param_sources.get(model_type, {}))
    own = config.variant_params.get(model_type, {}).get(index, {})
    params.update(own)
    sources.update({k: "kit" for k in own})
    spec = {
        "name": asset_name(model_type, index, config.prefix),
        "type": model_type,
        "index": index,
        "seed": model_seed(config.seed, model_type, index),
        "scale": config.scale,
        "params": params,
        "style": config.style.to_dict(),
    }
    if sources:
        spec["param_sources"] = {k: v for k, v in sources.items() if k in params}
    if config.family:
        spec["family"] = config.family["name"]
    if config.repair_safe:
        spec["repair_safe"] = True
    if config.single_renderer:
        spec["single_renderer"] = True
    if config.contract < 3:  # an importer before version 3 knows M_Crystal only (materials.LEGACY_NAMES)
        spec["legacy_materials"] = True
    return spec


#: manifest.json format (0.22.0): 1 = until cubegen 0.21 (no "format" key), 2 = + "format", "joins", "dressings",
#: sets[].faces_unity / bounds, models[].set / dressing, connectors[].moves and the Emission map only for glowing
#: paint schemes. Only additions: a reader of format 1 keeps working; a key changes meaning only with a new format.
MANIFEST_FORMAT = 2
#: look parameters of a type that are "dressings" (ROADMAP ToDo 30): geometry a paint scheme cannot give, never rolled
DRESSING_PARAMS = ("dressing", "crystals")
#: the paint scheme each dressing was made for (concepts "Ruin" and "Organic") - a suggestion, never enforced
DRESSING_PAINTS = {"ruin": ["ruin"], "organic": ["organic"]}


def split_materials(written: bool = True) -> Dict[str, Any]:
    """Manifest ``materials``: every name split off ``M_Crystal`` (0.24.0) with its values - sRGB colour, Unity
    smoothness, metallic, emission strength - what it is for and the name an older importer reads instead."""
    from .materials import CRYSTAL_SPLIT, to_hex

    return {"written": written, "like": "M_Crystal",
            "split": {name: {"srgb": to_hex(name), "smoothness": MATERIALS[name][1], "metallic": MATERIALS[name][2],
                             "emission": MATERIALS[name][3], "use": use, "legacy": LEGACY_NAMES[name]}
                      for name, use in CRYSTAL_SPLIT.items()}}


def sidecar_paint(paint: str, scheme: Optional[Dict[str, Any]] = None):
    """Root key ``paint`` of a sidecar (contract version 3): a built-in scheme by name, a custom one as complete data
    (``name`` + every ``SCHEME_KEYS`` key) - the shader needs exactly those values."""
    if paint in BUILTIN_PAINTS:
        return paint
    data = scheme if scheme is not None else PAINTS[paint]
    return {"name": paint, **{k: (dict(v) if isinstance(v, dict) else v) for k, v in data.items()}}


def dressing_params(model_type: str) -> Dict[str, Any]:
    """The type's dressing parameters (choices only - ``crystals`` of the rock types is a count, not a dressing)."""
    return {p.name: p for p in REGISTRY[model_type].params if p.name in DRESSING_PARAMS and p.kind == "choice"}


def dressing_table() -> Dict[str, Dict[str, Any]]:
    """For the manifest: per dressing parameter its values, default, the types that have it and (``dressing``) the
    paint scheme each value belongs to."""
    table: Dict[str, Dict[str, Any]] = {}
    for model_type in sorted(REGISTRY):
        for name, param in dressing_params(model_type).items():
            entry = table.setdefault(name, {"values": list(param.choices), "default": param.default, "types": []})
            entry["types"].append(model_type)
    if "dressing" in table:
        table["dressing"]["paints"] = DRESSING_PAINTS
    return table


def _faces_unity(faces, box) -> List[Dict[str, Any]]:
    """The set's joining faces in Unity coordinates: outward ``direction`` and ``distance_m`` of the face from the
    pivot along it (``x-`` of a 4 m floor tile: direction [1, 0, 0], 2.0)."""
    lo, hi = box
    out = []
    for face in faces:
        axis = "xyz".index(face[0])
        sign = 1.0 if face[1] == "+" else -1.0
        normal = tuple(sign if i == axis else 0.0 for i in range(3))
        out.append({"face": face, "direction": list(to_unity(normal)),
                    "distance_m": round(sign * (hi if sign > 0 else lo)[axis], 4) + 0.0})
    return out


#: parameters that define a piece's outline (with every ``Param(size=True)``): fixed for all members of a variant set
OUTLINE_PARAMS = ("length", "width", "height", "thickness", "depth", "radius", "size", "span", "diameter")
SET_TOLERANCE_M = 0.01  # members whose bounding box differs more are reported: the type is not set-ready


def outline_params(model_type: str, used: Dict[str, Any]) -> Dict[str, Any]:
    """The outline values among the resolved parameters of a model (plus the type's own ``set_pins``)."""
    entry = REGISTRY[model_type]
    specs = {p.name: p for p in entry.params}
    return {k: v for k, v in sorted(used.items())
            if k in specs and (specs[k].size or k in OUTLINE_PARAMS or k in entry.set_pins)}


def _set_spec(config: BatchConfig, model_type: str, index: int, pinned: Dict[str, Any]) -> Dict:
    spec = _spec(config, model_type, index)
    own = set(config.params.get(model_type, {})) | set(config.variant_params.get(model_type, {}).get(index, {}))
    spec["params"] = dict(spec["params"], **{k: v for k, v in pinned.items() if k not in own})
    spec["set"] = {"name": f"{model_type}_set", "pinned": pinned}
    return spec


def plan_models(config: BatchConfig, log: Optional[Callable[[str], None]] = None) -> List[Dict]:
    """Names and seeds of every asset in the batch (deterministic).

    With ``config.unique`` a count takes the first indices whose models differ
    from each other (Crate_000, Crate_002, ...): names and seeds stay the ones
    of those indices, so ``--pick`` rebuilds them exactly.
    """
    specs = []
    for model_type, value in config.models.items():
        if config.variant_set and not isinstance(value, list) and value > 1:
            # variant set: variant 0 decides the outline, every member keeps it (rolled values are still drawn, so
            # variant 0 itself stays the same model)
            pinned = outline_params(model_type, build_spec(_spec(config, model_type, 0)).p.used)
            make = (lambda t, pv: lambda i: _set_spec(config, t, i, pv))(model_type, pinned)
            if config.unique:
                indices, tried = pick_unique(value, lambda i: build_spec(make(i)))
                if len(indices) < value and log:
                    log(f"{model_type}: only {len(indices)} different set members among the first {tried}")
            else:
                indices = list(range(value))
            specs.extend(make(i) for i in indices)
            continue
        if isinstance(value, list):
            indices = sorted(set(value))
        elif config.unique and value > 1 and not config.variant_params.get(model_type):
            indices, tried = pick_unique(value, lambda i: build_spec(_spec(config, model_type, i)))
            if len(indices) < value and log:
                log(f"{model_type}: only {len(indices)} different variants among the first {tried} - "
                    "using those")
        else:
            indices = list(range(value))
        specs.extend(_spec(config, model_type, index) for index in indices)
    return specs


def _part_entries(asset, material_map: Optional[Dict[str, str]], suffix: str = "") -> List[Dict]:
    parts = []
    for o in asset.objects:
        parent = asset.get(o.parent) if o.parent else None
        local = tuple(o.pivot[i] - (parent.pivot[i] if parent else 0.0) for i in range(3))
        entry_part = {
            "name": o.name + suffix,
            "parent": o.parent + suffix if o.parent else None,
            "localPosition": list(to_unity(local)),
            "empty": o.is_empty,
            "materials": [] if o.is_empty else sorted({palette_mod.resolve(material_map, o.name, r)
                                                       for r in o.mesh.roles}),
        }
        if not o.is_empty:  # box collider hint relative to the part's own pivot (Unity coordinates)
            (bx0, by0, bz0), (bx1, by1, bz1) = o.mesh.bbox()
            center = tuple((lo_ + hi_) / 2 - o.pivot[i] for i, (lo_, hi_) in enumerate(((bx0, bx1), (by0, by1), (bz0, bz1))))
            entry_part["bounds"] = {"center": list(to_unity(center)),
                                    "size": [abs(c) for c in to_unity((bx1 - bx0, by1 - by0, bz1 - bz0))]}
        parts.append(entry_part)
    return parts


def rig_data(asset, spec: Dict, master_seed: int, material_map: Optional[Dict[str, str]] = None,
             lod=None) -> Dict:
    """Everything a Unity prefab builder needs besides the FBX, in Unity coordinates.

    Animations are not baked into the FBX: the game's scripts move parts with
    fields set by the prefab builders, so this file carries those values.
    With ``lod`` (static models, ``--lods``) the parts are named as in the FBX:
    ``<part>_LOD0`` and ``<part>_LOD1``; colliders sit on LOD0. Only keys of the
    Unity reader's contract are written (see docs/UNITY_INTEGRATION.md).
    """
    entry = REGISTRY[spec["type"]]
    if lod is None:
        parts = _part_entries(asset, material_map)
        lo, hi = asset.bbox()
    else:
        parts = _part_entries(asset, material_map, "_LOD0") + _part_entries(lod, material_map, "_LOD1")
        (a0, a1), (b0, b1) = asset.bbox(), lod.bbox()
        lo, hi = tuple(min(a0[i], b0[i]) for i in range(3)), tuple(max(a1[i], b1[i]) for i in range(3))
    colliders = asset.collider_data()
    if lod is not None:
        colliders = [dict(c, part=c["part"] + "_LOD0" if c["part"] else None) for c in colliders]
    center = to_unity(tuple((lo[i] + hi[i]) / 2 for i in range(3)))
    size = to_unity(tuple(hi[i] - lo[i] for i in range(3)))
    return {
        "generator": f"cubegen {__version__}",
        "model": asset.name,
        "type": spec["type"],
        "category": entry.category,
        "pivot": entry.pivot,
        "seed": spec["seed"],
        "masterSeed": master_seed,
        "static": not asset.behaviours,
        "params": asset.meta.get("params", {}),
        "style": Style.from_dict(spec.get("style")).resolved().to_dict(),  # as built (theme filled in)
        "bounds": {"center": list(center), "size": [abs(c) for c in size]},
        "parts": parts,
        "behaviours": asset.behaviours,
        # Explicit shapes win. Static imports may use a hull; gameplay imports
        # only build collision from recipe roles, never a blanket hull.
        **({"colliders": colliders} if asset.colliders else {}),
    }


def check_contract(specs: List[Dict], master_seed: int, log: Callable[[str], None] = print,
                   build: Optional[Callable[[Dict], Any]] = None, build_lod: Optional[Callable[[Dict], Any]] = None
                   ) -> List[str]:
    """Every sidecar of the batch against the Unity importer's contract (``cubegen/contract.py``).

    Raises ``ValueError`` listing all violations; returns (and logs) the open item assignments
    (``ItemPickup`` without ``item_id`` - Unity skips those models until an id is set)."""
    errors, open_items = [], []
    for spec in specs:
        asset = (build or build_spec)(spec)
        lod = (build_lod or (lambda s: build_spec(lod_spec(s))))(spec) if spec.get("lod") else None
        rig = rig_data(asset, spec, master_seed, lod=lod)
        problems, missing = check_sidecar(rig, f"{spec['name']}.cubegen.json")
        errors += [f"{spec['name']}: {p}" for p in problems]
        open_items += missing
    if errors:
        raise ValueError("these models break the Unity import contract (the importer would skip them):\n  "
                         + "\n  ".join(errors))
    for item in open_items:
        log(f"note: {item} - set it with --param <type>.item_id=<ItemData id>")
    return open_items


def lod_data(asset, lod) -> Dict:
    """``"lods"`` of a manifest entry (not in the sidecar: the Unity reader rejects unknown root keys)."""
    return {"objects": "<part>_LOD<level>", "note": "Unity builds the LODGroup on import from the _LOD names",
            "levels": [{"suffix": "_LOD0", "triangles": asset.stats()["triangles"]},
                       {"suffix": "_LOD1", "triangles": lod.stats()["triangles"]}]}


def build_spec(spec: Dict):
    """The asset a planned spec describes (same call as inside Blender)."""
    asset = generate_asset(spec["type"], spec["seed"], spec["name"], spec["scale"], params=spec.get("params"),
                           style=Style.from_dict(spec.get("style")))
    if spec.get("legacy_materials"):
        asset.legacy_materials()
    if spec.get("repair_safe"):
        asset.repair_safe()
    if spec.get("single_renderer"):
        asset.merge_static()
    return asset


LOD_MIN_SAVING = 0.15  # a LOD1 must have at least 15 % fewer triangles, else it isn't worth a level


def lod_spec(spec: Dict) -> Dict:
    """LOD1 of a spec: the same model with detail "low" (same rolls: no bevels, fewer cylinder sides)."""
    return dict(spec, style=dict(spec.get("style") or {}, detail="low"))


def wants_lod(spec: Dict, asset=None) -> bool:
    """LODs only for static models (scripts move parts by name - a LOD1 copy would stand still)."""
    asset = asset or build_spec(spec)
    if asset.behaviours or (spec.get("style") or {}).get("detail") == "low":
        return False
    lod = build_spec(lod_spec(spec))
    return lod.stats()["triangles"] <= (1.0 - LOD_MIN_SAVING) * asset.stats()["triangles"]


def family_fit(specs: List[Dict], log: Optional[Callable[[str], None]] = None,
               dims: Optional[Dict[str, Any]] = None, reference: Optional[Dict[str, Any]] = None) -> Dict:
    """Fit checks and pair matrix of a family batch."""
    from .families import compatibility_matrix, fit_report, same_look

    members = [(s["name"], build_spec(s), s["type"]) for s in specs]
    if reference:  # --match: the existing model takes part in the checks
        members.append((reference["model"], generate_asset(reference["type"], reference["seed"], reference["model"],
                                                           params=reference["params"],
                                                           style=Style.from_dict(reference["style"])),
                        reference["type"]))
    report = fit_report(members, dims)
    matrix = compatibility_matrix(members, dims, report)
    problems = [{"a": r["a"], "b": r["b"], "joint": r["joint"], "problems": r["problems"]}
                for r in report if r["problems"]]
    look = same_look(specs)
    if log:
        log(f"family fit: {len(report)} joint(s) checked, {len(problems)} don't fit"
            f"{', ' + look[0] if look else ''}")
        for p in problems[:10]:
            log(f"  {p['a']} {p['joint']} {p['b']}: {'; '.join(p['problems'])}")
    return {"joints": len(report), "problems": problems, "look": look, "compatibility": matrix}


def _rel(path: Optional[str], base: str) -> Optional[str]:
    return os.path.relpath(path, base).replace(os.sep, "/") if path else None


def _abs(path: Optional[str], base: str) -> Optional[str]:
    return os.path.normpath(os.path.join(base, path)) if path else None


_CODE_FINGERPRINT: List[str] = []


def code_fingerprint() -> str:
    """Hash of the cubegen sources: a changed generator rebuilds everything, even without a version bump."""
    if not _CODE_FINGERPRINT:
        root = os.path.dirname(os.path.abspath(__file__))
        h = hashlib.sha256()
        for folder, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for name in sorted(f for f in files if f.endswith(".py")):
                path = os.path.join(folder, name)
                h.update(os.path.relpath(path, root).replace(os.sep, "/").encode())
                with open(path, "rb") as fh:
                    h.update(fh.read())
        _CODE_FINGERPRINT.append(h.hexdigest())
    return _CODE_FINGERPRINT[0]


def build_key(spec: Dict, settings: Dict) -> str:
    """Everything an asset's exported files depend on: its spec, the export / render settings, the code."""
    data = {k: v for k, v in spec.items() if k != "build_key"}
    text = json.dumps({"spec": data, "settings": settings, "code": code_fingerprint()}, sort_keys=True,
                      default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _previous_results(out: str, specs: List[Dict], render: bool) -> Dict[str, Dict]:
    """Results of the last run in ``out`` that are still valid: same build key, all files still there."""
    try:
        with open(os.path.join(out, "manifest.json"), "r", encoding="utf-8") as fh:
            old = {m["name"]: m for m in json.load(fh).get("models", [])}
    except (OSError, ValueError, KeyError, TypeError):
        return {}
    reuse = {}
    for spec in specs:
        entry = old.get(spec["name"])
        if not entry or entry.get("build_key") != spec["build_key"]:
            continue
        res = {"files": {k: _abs(v, out) for k, v in entry.get("files", {}).items() if k != "rig"},
               "preview": _abs(entry.get("preview"), out), "icon": _abs(entry.get("icon"), out), "reused": True}
        if entry.get("baked"):
            res.update({"baked": {k: _abs(v, out) for k, v in entry["baked"].items()},
                        "baked_material": entry.get("baked_material"), "bake_device": entry.get("bake_device")})
            if entry.get("neutral"):
                res.update({"paint": entry.get("paint"), "weight_layout": entry.get("weight_layout"),
                            "neutral": {k: (_abs(v, out) if isinstance(v, str) else [_abs(x, out) for x in v])
                                        for k, v in entry["neutral"].items()}})
            if entry.get("neutral_maps"):
                res["neutral_maps"] = {k: _abs(v, out) for k, v in entry["neutral_maps"].items()}
        paths = list(res["files"].values()) + list(res.get("baked", {}).values()) \
            + list(res.get("neutral_maps", {}).values())
        for value in (res.get("neutral") or {}).values():  # the neutral maps of a paint scheme (later shader)
            paths += value if isinstance(value, list) else [value]
        if render:
            paths.append(res["preview"])
        if res["files"] and all(p and os.path.isfile(p) for p in paths):
            reuse[spec["name"]] = res
    return reuse


def _previous_engine(out: str) -> Optional[str]:
    try:
        with open(os.path.join(out, "manifest.json"), "r", encoding="utf-8") as fh:
            return (json.load(fh).get("blender") or {}).get("render_engine")
    except (OSError, ValueError, AttributeError):
        return None


# --jobs auto (measured 0.16.0, Apple M5, 10 cores): a Blender process starts in about 0.6 s and should get at least
# MIN_WORKER_SECONDS of work. Cycles baking on the CPU already uses every core - 1 to 9 processes all took 69-77 s
# for the station kit -, so it gets two (one bakes while the other exports); GPU work at most three (the robot
# generator measured the GPU busy from 3-4 EEVEE processes). Export / Workbench previews: up to cores - 1.
MIN_WORKER_SECONDS = 2.0
SECONDS_PER_MODEL = {"export": 0.03, "workbench": 0.05, "render": 0.5, "bake": 1.7}


def auto_jobs(models: int, config: "BatchConfig", engine: Optional[str]) -> int:
    """How many Blender processes pay off for ``models`` models (``--jobs auto``)."""
    cores = os.cpu_count() or 1
    limit = max(1, cores - 1)
    per_model = SECONDS_PER_MODEL["export"]
    if config.render and engine:
        per_model += SECONDS_PER_MODEL["workbench" if engine == "workbench" else "render"]
        if engine != "workbench":
            limit = min(limit, 3)
    if config.textures == "baked":
        gpu = config.bake_device == "gpu" or (config.bake_device == "auto" and config.texture_size >= 1024)
        per_model += SECONDS_PER_MODEL["bake"] * (config.texture_size / 512) ** 2 * (2.5 if config.paint else 1.0)
        limit = min(limit, 3 if gpu else 2)
    worth = int(models * per_model / MIN_WORKER_SECONDS)
    return max(1, min(limit, models, worth))


class _Background:
    """Runs ``work`` in a thread and then marks ``ready`` (a file the Blender workers wait for): ``ok`` or the error."""

    def __init__(self, work: Callable[[], Any], ready: str):
        self.result = None
        self.error: Optional[BaseException] = None
        self.seconds = 0.0
        self.ready = ready
        self.thread = threading.Thread(target=self._run, args=(work,), daemon=True)
        self.thread.start()

    def _run(self, work):
        start = time.perf_counter()
        try:
            self.result = work()
        except BaseException as exc:  # noqa: BLE001 - re-raised in join()
            self.error = exc
        self.seconds = time.perf_counter() - start
        with open(self.ready, "w", encoding="utf-8") as fh:
            fh.write("ok" if self.error is None else f"error: {self.error}")

    def join(self):
        self.thread.join()
        if self.error is not None:
            raise self.error
        return self.result


def model_cost(spec: Dict, asset=None) -> int:
    """Rough work of a model for the order of the work packages: triangles + a share per part (export / bake).
    ``asset``: the already built asset of ``spec`` (it is built here otherwise)."""
    asset = asset if asset is not None else build_spec(spec)
    return asset.stats()["triangles"] + 100 * len(asset.objects)


def _run_jobs(blender: str, job: Dict, specs: List[Dict], todo: List[Dict], blend_path: Optional[str],
              jobs: int, verbose: bool, log: Callable[[str], None], cost: Callable[[Dict], int] = model_cost) -> Dict:
    """Run the worker: one process, or ``jobs`` processes + one that only builds the overview .blend.

    Parallel: every process gets the whole list, biggest model first, and builds the ones it claims (a claim file
    per model, created exclusively) - a process that finishes early takes the next model instead of idling while
    another works through a fixed share. ImageMagick runs with one thread in them (parallel OpenMP pools wait for
    each other). Blender keeps its thread pool: measured 0.15.0, ``-t cores/jobs`` made Cycles CPU baking slower
    (station kit, --jobs 3: 50-54 s instead of 47-49 s). The results are merged in the order of ``specs``."""
    todo_names = {s["name"] for s in todo}
    parallel = jobs > 1 and len(todo) > 1
    queue = tempfile.mkdtemp(prefix="cubegen_queue_") if parallel else None
    env = None
    if not parallel:
        models = [dict(s, skip=s["name"] not in todo_names) for s in specs] if blend_path else todo
        runs = [dict(job, models=models, blend=blend_path)]
    else:
        workers = min(jobs, len(todo))
        ordered = sorted(todo, key=lambda s: -cost(s))  # stable: equal costs keep the spec order
        runs = [dict(job, models=ordered, blend=None, queue_dir=queue) for _ in range(workers)]
        if blend_path:  # cheap: builds the meshes, no export / render / bake
            runs.append(dict(job, models=[dict(s, skip=True) for s in specs], blend=blend_path))
        env = {"MAGICK_THREAD_LIMIT": "1"}

    def run(index_job):
        index, run_spec = index_job
        prefix = f"[{index + 1}/{len(runs)}] " if len(runs) > 1 else ""
        with tempfile.TemporaryDirectory(prefix="cubegen_job_") as work:
            return run_job(blender, run_spec, work, verbose, lambda m: log(prefix + m), env=env)

    try:
        if len(runs) == 1:
            outputs = [run((0, runs[0]))]
        else:
            log(f"{len(runs)} Blender processes in parallel")
            with ThreadPoolExecutor(max_workers=len(runs)) as pool:
                futures = [pool.submit(run, item) for item in enumerate(runs)]
                errors = [f.exception() for f in futures if f.exception() is not None]
                if errors:
                    raise errors[0]
                outputs = [f.result() for f in futures]
    finally:
        if queue:
            shutil.rmtree(queue, ignore_errors=True)
    by_name = {m["name"]: m for o in outputs for m in o["models"]}
    missing = sorted(todo_names - set(by_name))
    if missing:
        raise BlenderError("no Blender process built: " + ", ".join(missing))
    merged = {"models": [by_name[s["name"]] for s in specs if s["name"] in by_name],
              "workers": [o["worker"] for o in outputs if o.get("worker")],
              "blender": outputs[0].get("blender"),
              "engine": next((o.get("engine") for o in outputs if o["models"]), outputs[0].get("engine"))}
    return merged


def _budget(stage: str, models: int, config: "BatchConfig") -> float:
    rule = STAGE_BUDGETS[stage]
    factor = {"texture": (config.texture_size / 512) ** 2, "render": (config.render_size / 384) ** 2}.get(
        rule.get("scale"), 1.0)
    base = rule["total"] if "total" in rule else rule["per_model"] * max(1, models)
    if stage == "bake" and config.paint:  # the neutral bake has 8 passes (weights, AO, edge, up, height, detail, normal)
        base *= 2.5
    return base * max(1.0, factor)


def system_load() -> Optional[float]:
    """1-minute load average (None where the OS has none, e.g. Windows)."""
    try:
        return round(os.getloadavg()[0], 2)
    except (AttributeError, OSError):
        return None


def stage_report(seconds: Dict[str, float], worker: Dict[str, float], models: int, config: "BatchConfig",
                 load: Optional[Dict] = None, workers: Optional[List[Dict]] = None,
                 steps: Optional[Dict[str, float]] = None) -> Dict:
    """For the manifest: ``seconds`` (wall clock per stage of this run), ``worker_seconds`` (summed in Blender),
    ``budgets`` and ``slow`` (stages over their budget), ``load`` (system load at start / end, cores) and ``workers``
    (per Blender process: models built, seconds) - times are only comparable on an idle machine."""
    measured = dict(seconds, **worker)
    budgets = {stage: round(_budget(stage, models, config), 1) for stage in measured if stage in STAGE_BUDGETS}
    slow = [stage for stage, limit in budgets.items() if measured[stage] > limit]
    return {"seconds": {k: round(v, 2) for k, v in seconds.items()},
            "worker_seconds": {k: round(v, 2) for k, v in worker.items()},
            "budgets": budgets, "models_built": models, "slow": slow, "load": load or {}, "workers": workers or [],
            # named steps inside the stages (0.21.0: measure the steps first, then optimise): Python model builds,
            # the contract check without its builds, planning (incl. --unique picks)
            "steps": {k: round(v, 2) for k, v in (steps or {}).items()}}


def _variant_sets(specs, results, asset_of, out, im, images, magick_version) -> List[Dict]:
    """Per variant set: members, the pinned outline, whether every member really has it (bounding boxes within
    ``SET_TOLERANCE_M``) and a row of the previews side by side (``set_<type>.png``) to check the variety."""
    sets = []
    groups: Dict[str, List[Dict]] = {}  # one pass over the specs instead of a search per set
    for s in specs:
        if s.get("set"):
            groups.setdefault(s["set"]["name"], []).append(s)
    for name in sorted(groups):
        members = groups[name]
        # what must match to join: the type's set_faces - a wall its left/right, bottom/top and back (parts may stick
        # out to the front: pipes, signs, crystals), a floor tile its four sides and bottom (details on top), ...
        faces = REGISTRY[members[0]["type"]].set_faces
        boxes = [asset_of(s).bbox() for s in members]
        edges = [[(hi if f[1] == "+" else lo)["xyz".index(f[0])] for f in faces] for lo, hi in boxes]
        deviation = max(abs(e[i] - edges[0][i]) for e in edges for i in range(len(faces)))
        previews = [results.get(s["name"], {}).get("preview") for s in members]
        previews = [p for p in previews if p and os.path.isfile(p)]
        row = None
        if len(previews) > 1:
            row = os.path.join(out, f"set_{members[0]['type']}.png")
            key = input_key("set", [images.digest(p) for p in previews], code_fingerprint(), magick_version)
            if not images.get("set:" + row, key):
                im.run([arg for p in previews for arg in ("(", p, "-resize", "320x320", ")")]
                       + ["-background", "#1e1e24", "-gravity", "south", "+append", row])
                images.put("set:" + row, key, [row])
        lo, hi = boxes[0]  # the outline every member keeps (variant 0's), Unity coordinates like a sidecar's bounds
        sets.append({"name": name, "type": members[0]["type"], "members": [s["name"] for s in members],
                     "pinned": members[0]["set"]["pinned"], "faces": list(faces),
                     "faces_unity": _faces_unity(faces, boxes[0]),
                     "bounds": {"center": list(to_unity(tuple((lo[i] + hi[i]) / 2 for i in range(3)))),
                                "size": [abs(c) for c in to_unity(tuple(hi[i] - lo[i] for i in range(3)))]},
                     "outline_ok": deviation <= SET_TOLERANCE_M,
                     "deviation_m": round(deviation, 4), "preview": row})
    return sets


def _texture_set(im: ImageMagick, textures_dir: str, config: BatchConfig, magick_version: str,
                 log: Callable[[str], None]) -> Dict[str, Dict]:
    """The tile textures of a set - rebuilt only when an input or a written file changed (``--force``: always)."""
    cache = OutputCache(textures_dir, enabled=not config.force)
    key = input_key("textures", config.texture_size, config.texture_set, textures_dir, code_fingerprint(),
                    magick_version)
    hit = cache.get("texture_set", key)
    if hit:
        log(f"textures unchanged ({len(hit['data'])} materials) -> {textures_dir}")
        return hit["data"]
    textures = build_texture_set(im, textures_dir, config.texture_size, config.texture_set, log=log)
    files = [p for info in textures.values() for p in info["paths"].values()]
    cache.put("texture_set", key, files + [os.path.join(textures_dir, "CubeEscape_Textures.json")], textures)
    cache.save()
    return textures


def generate_batch(config: BatchConfig, log: Callable[[str], None] = print) -> Dict:
    config.validate()
    seconds: Dict[str, float] = {}
    worker: Dict[str, float] = {}
    cores = os.cpu_count() or 1
    load = {"start": system_load(), "cores": cores}
    if load["start"] is not None and load["start"] > cores:
        log(f"warning: the machine is busy (load {load['start']:.1f} on {cores} cores) - times are not comparable")
    workers: List[Dict] = []
    overlap: List[str] = []  # stages that ran in parallel with "blender"
    clock = [time.perf_counter()]

    def lap(stage: str) -> None:  # time since the last lap -> stage
        now = time.perf_counter()
        seconds[stage] = seconds.get(stage, 0.0) + now - clock[0]
        clock[0] = now

    steps: Dict[str, float] = {"plan_models": 0.0, "build": 0.0, "contract": 0.0}
    started = time.perf_counter()
    specs = plan_models(config, log)
    steps["plan_models"] = time.perf_counter() - started
    built_assets: Dict[str, Any] = {}

    built_lods: Dict[str, Any] = {}

    def asset_of(spec: Dict):  # each model built once in Python: contract, export, library, work packages, manifest
        if spec["name"] not in built_assets:
            t = time.perf_counter()
            built_assets[spec["name"]] = build_spec(spec)
            steps["build"] += time.perf_counter() - t
        return built_assets[spec["name"]]

    def lod_of(spec: Dict):  # the same for the LOD1 build (--lods)
        if spec["name"] not in built_lods:
            t = time.perf_counter()
            built_lods[spec["name"]] = build_spec(lod_spec(spec))
            steps["build"] += time.perf_counter() - t
        return built_lods[spec["name"]]
    if not specs:
        raise ValueError("nothing to generate (all counts are 0)")

    out = os.path.abspath(config.out_dir)
    dirs = {
        "models": os.path.abspath(config.models_dir) if config.models_dir else os.path.join(out, "models"),
        "icons": os.path.abspath(config.icons_dir) if config.icons_dir else os.path.join(out, "icons"),
        "previews": os.path.join(out, "previews"),
    }
    os.makedirs(out, exist_ok=True)
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
    # scripted assets -> models dir (where the game's AddModel loads them), static decoration -> library
    for spec in specs:
        spec["models_dir"] = dirs["models"]
        if config.lods:
            spec["lod"] = wants_lod(spec)
        if config.library_dir:
            asset = asset_of(spec)
            if not asset.behaviours:
                category = REGISTRY[spec["type"]].category.capitalize()
                spec["models_dir"] = os.path.join(os.path.abspath(config.library_dir), category)
        os.makedirs(spec["models_dir"], exist_ok=True)

    if config.rig_data:  # the Unity import skips a model whose sidecar breaks its contract - stop before Blender
        t, before = time.perf_counter(), steps["build"]
        check_contract(specs, config.seed, log, build=asset_of, build_lod=lod_of)
        steps["contract"] = time.perf_counter() - t - (steps["build"] - before)  # without the builds it caused

    im = ImageMagick(config.magick)
    magick_version = im.version()
    images = OutputCache(out, enabled=not config.force)  # swatch, icons, contact sheet
    swatch = os.path.join(out, "materials.png")
    swatch_key = input_key("swatch", code_fingerprint(), magick_version)
    if not images.get("swatch", swatch_key):
        im.material_swatch(swatch)
        images.put("swatch", swatch_key, [swatch])
    lap("plan")

    textures: Dict[str, Dict] = {}
    textures_dir = None
    palette = None
    texture_job: Optional[_Background] = None
    if config.textures != "none":
        textures_dir = os.path.abspath(config.textures_dir) if config.textures_dir \
            else os.path.join(dirs["models"], "Textures")
    if config.textures == "palette":  # one material per model: written in pure Python
        palette = palette_mod.write_palette(textures_dir, log=log, name=config.palette)
    elif config.textures != "none" and config.use_blender:
        # Blender starts while ImageMagick builds the tile textures: the workers know the names and paths up front
        # and wait for the "ready" file before they load the images (robot generator: workers start before the bake)
        textures = plan_texture_set(textures_dir, config.texture_set)
        ready_dir = tempfile.mkdtemp(prefix="cubegen_ready_")
        texture_job = _Background(lambda: _texture_set(im, textures_dir, config, magick_version, log),
                                  os.path.join(ready_dir, "textures"))
    elif config.textures != "none":
        textures = _texture_set(im, textures_dir, config, magick_version, log)
    material_map = {plain: info["name"] for plain, info in textures.items()}
    if config.textures != "none" and texture_job is None:
        lap("textures")

    def asset_materials(asset):
        return palette_mod.material_map(asset, config.palette) if palette else material_map

    results: Dict[str, Dict] = {}
    blender_info: Dict[str, object] = {}
    formats = list(config.formats)
    blend_path = None
    if config.use_blender:
        blender = find_blender(config.blender)
        if not blender:
            raise BlenderError("Blender not found. Install Blender, set $BLENDER, pass --blender PATH "
                               "or use --no-blender for a pure-Python OBJ export.")
        blend_path = os.path.join(out, f"CubeEscape_Generated_{config.seed}.blend") if config.blend else None
        version = blender_version(blender).replace("Blender ", "", 1)
        settings = {"formats": formats, "blender": version, "textures": [config.textures, config.texture_size,
                                                                         config.texture_set, textures_dir]
                    + ([config.palette] if palette and config.palette != palette_mod.DEFAULT_PALETTE else [])
                    + ([config.bake_device, config.paint] if config.textures == "baked" else [])
                    + ([config.paint_scheme] if config.paint_scheme else []),
                    "render": [config.render, config.engine, config.render_size, config.samples,
                               config.icon_azimuth, config.icon_elevation, config.icon_zoom]}
        for spec in specs:
            spec["build_key"] = build_key(spec, dict(settings, models_dir=spec["models_dir"]))
        reused = {} if config.force else _previous_results(out, specs, config.render)
        todo = [s for s in specs if s["name"] not in reused]
        if reused:
            log(f"unchanged since the last run: {len(reused)} asset(s) (--force rebuilds them)")
        engine = resolve_engine(blender, config.engine, log) if config.render and todo else None
        job = {
            "formats": formats,
            "models_dir": dirs["models"],
            "previews_dir": dirs["previews"],
            "blend": blend_path,
            "textures": textures,
            "palette": palette,
            "texture_mode": config.textures,
            "texture_size": config.texture_size,
            "textures_dir": textures_dir,
            "magick": im.convert,
            "bake_device": config.bake_device,
            "paint": config.paint,
            "paint_scheme": config.paint_scheme,
            "textures_ready": texture_job.ready if texture_job else None,
            "render": {"enabled": config.render, "engine": engine, "size": config.render_size,
                       "samples": config.samples, "azimuth": config.icon_azimuth,
                       "elevation": config.icon_elevation, "zoom": config.icon_zoom},
        }
        results = dict(reused)
        blender_info = {"version": version, "render_engine": None}
        lap("plan")
        jobs = config.jobs or auto_jobs(len(todo), config, engine)
        blender_failed = False
        try:
            if todo or (blend_path and not os.path.isfile(blend_path)):
                log(f"Blender: {blender} - {len(todo)} asset(s), formats: {', '.join(formats)}, "
                    f"{jobs} process(es){' (auto)' if not config.jobs else ''}")
                result = _run_jobs(blender, job, specs, todo, blend_path, jobs, config.verbose, log,
                                   cost=lambda spec: model_cost(spec, asset_of(spec)))
            else:
                result = None
        except BaseException:
            blender_failed = True
            raise
        finally:
            if texture_job is not None:  # also when Blender failed: the thread must not outlive the run
                try:
                    built = texture_job.join()
                    if built != textures:
                        raise RuntimeError("texture set differs from its plan (textures.texture_info)")
                except Exception as texture_error:
                    if not blender_failed:
                        raise
                    log(f"textures failed too: {texture_error}")  # the Blender error is the one that propagates
                finally:
                    shutil.rmtree(os.path.dirname(texture_job.ready), ignore_errors=True)
                seconds["textures"] = texture_job.seconds  # its own duration, in parallel with Blender
                overlap.append("textures")
        if result is None:
            clock[0] = time.perf_counter()  # the wait for the textures is already in seconds["textures"]
        else:
            results.update({r["name"]: r for r in result["models"]})
            workers = result.get("workers", [])
            lap("blender")  # wall clock; overlaps "textures" when they were built in the background
            for r in result["models"]:  # the worker's own clock per model (summed over parallel processes)
                for stage, value in (r.get("timings") or {}).items():
                    worker[stage] = worker.get(stage, 0.0) + value
            blender_info = {"version": result.get("blender"),
                            "render_engine": result.get("engine") if config.render and todo else None}
        if config.render and not blender_info["render_engine"]:
            blender_info["render_engine"] = _previous_engine(out)
    else:
        if formats != ["obj"]:
            log("--no-blender: only OBJ export is available, ignoring other formats")
        if config.textures == "baked":
            log("--no-blender: baking needs Blender, using tiled textures")
        formats = ["obj"]
        for folder in {spec["models_dir"] for spec in specs}:
            write_mtl(os.path.join(folder, "CubeEscape_Materials.mtl"), textures, palette)
        settings = {
            "formats": formats,
            "textures": [config.textures, config.texture_size, config.texture_set, textures_dir,
                         sorted(material_map.items())],
            "palette": config.palette if palette else None,
        }
        for spec in specs:
            spec["build_key"] = build_key(spec, dict(settings, models_dir=spec["models_dir"]))
        reused = {} if config.force else _previous_results(out, specs, render=False)
        todo = [spec for spec in specs if spec["name"] not in reused]
        if reused:
            log(f"unchanged since the last run: {len(reused)} asset(s) (--force rebuilds them)")
        results.update(reused)
        lap("plan")
        for spec in todo:
            asset = asset_of(spec)
            path = os.path.join(spec["models_dir"], f"{spec['name']}.obj")
            write_obj(asset, path, "CubeEscape_Materials.mtl", asset_materials(asset),
                      lod=lod_of(spec) if spec.get("lod") else None)
            results[spec["name"]] = {"files": {"obj": path}, "preview": None}
            log(f"{spec['name']}: {asset.stats()['triangles']} tris")
        lap("export")

    # --- ImageMagick post processing (skipped where the inputs did not change) ------
    previews, labels, sources, icon_todo = [], [], [], []
    for spec in specs:
        res = results.get(spec["name"], {})
        if res.get("preview") and os.path.isfile(res["preview"]):
            icon = os.path.join(dirs["icons"], f"Icon_{spec['name']}.png")
            preview_hash = images.digest(res["preview"])  # read only if the preview changed (cache index)
            key = input_key("icon", preview_hash, config.icon_size, config.icon_background, code_fingerprint(),
                            magick_version)
            if not images.get(f"icon:{icon}", key):
                icon_todo.append((res["preview"], icon, key))
            res["icon"] = icon
            previews.append(res["preview"])
            labels.append(spec["name"])
            sources.append(preview_hash)
    made = len(icon_todo)
    if icon_todo:  # one ImageMagick process per icon, several at once (each with one thread)
        single = im.single_threaded() if made > 1 else im
        with ThreadPoolExecutor(max_workers=min(made, os.cpu_count() or 1)) as pool:
            list(pool.map(lambda t: single.make_icon(t[0], t[1], config.icon_size, config.icon_background),
                          icon_todo))
        for _, icon, key in icon_todo:
            images.put(f"icon:{icon}", key, [icon])
    images.prune("icon:", [os.path.join(dirs["icons"], f"Icon_{n}.png") for n in labels])
    sheet = None
    if previews:
        sheet = os.path.join(out, "contact_sheet.png")
        title = f"Cube Escape - {config.family['name'] + ' - ' if config.family else ''}seed {config.seed}"
        key = input_key("sheet", labels, sources, title, code_fingerprint(), magick_version)
        if not images.get("contact_sheet", key):
            im.contact_sheet(previews, labels, sheet, title=title)
            images.put("contact_sheet", key, [sheet])
            log(f"contact sheet -> {sheet}")
        else:
            log(f"contact sheet unchanged -> {sheet}")
    sets = _variant_sets(specs, results, asset_of, out, im, images, magick_version)
    images.save()
    if previews:
        log(f"icons: {made} new, {len(previews) - made} reused")
    lap("images")

    # --- manifest + rig data ----------------------------------------------------
    entries = []
    for spec in specs:
        asset = asset_of(spec)
        res = results.get(spec["name"], {})
        if config.rig_data:
            rig_path = os.path.join(spec["models_dir"], f"{spec['name']}.cubegen.json")
            with open(rig_path, "w", encoding="utf-8") as fh:
                asset_map = asset_materials(asset)
                if res.get("baked_material"):  # every non-glow material became the asset's atlas material
                    asset_map = {m: res["baked_material"] for m in MATERIALS if m not in BAKE_KEEP}
                rig = rig_data(asset, spec, config.seed, asset_map, lod=lod_of(spec) if spec.get("lod") else None)
                if textures and not (config.textures == "baked" and not res.get("baked")):
                    # (baked mode, nothing baked - only glow, crystal or glass materials: plain M_* parts, no
                    # textures entry - the importer requires the baked maps in mode baked)
                    rig["textures"] = {"mode": config.textures,
                                       "manifest": _rel(os.path.join(textures_dir, "CubeEscape_Textures.json"),
                                                        spec["models_dir"])}
                    if res.get("baked"):
                        # the maps the importer's contract version reads: version 2 with a paint scheme's Emission,
                        # version 1 without (it stays in the manifest)
                        allowed = baked_map_keys(config.contract)
                        rig["textures"]["baked"] = {k: _rel(v, spec["models_dir"]) for k, v in res["baked"].items()
                                                    if k in allowed}
                    if res.get("neutral_maps") and "neutral" in texture_keys(config.contract):
                        # version 3: the packed neutral maps and the scheme for a recolouring shader (ToDo 27)
                        rig["textures"]["neutral"] = {k: _rel(v, spec["models_dir"])
                                                      for k, v in res["neutral_maps"].items()}
                        rig["textures"]["weight_layout"] = [list(g) for g in res["weight_layout"]]
                        rig["paint"] = sidecar_paint(config.paint, config.paint_scheme)
                elif palette:
                    rig["textures"] = {"mode": "palette",
                                       "manifest": _rel(os.path.join(textures_dir,
                                                                     palette_mod.palette_manifest_name(config.palette)),
                                                        spec["models_dir"])}
                problems, _ = check_sidecar(rig, rig_path, config.contract)
                if problems:
                    raise RuntimeError(f"{rig_path} breaks the Unity import contract:\n  " + "\n  ".join(problems))
                json.dump(rig, fh, indent=2)
            res.setdefault("files", {})["rig"] = rig_path
            fbx = res.get("files", {}).get("fbx")
            if fbx and os.path.isfile(fbx):  # and what Unity reads from the FBX: parents, pivots, bounds
                fbx_errors = check_fbx(rig, fbx)
                if fbx_errors:
                    raise RuntimeError(f"{fbx} breaks the Unity import contract:\n  " + "\n  ".join(fbx_errors))
            glb = res.get("files", {}).get("glb")
            if glb and os.path.isfile(glb):  # Cube Escape's workbench budget (bytes, triangles, textures ...)
                over = check_runtime_budget(glb)
                if over:
                    res["runtime_budget"] = over
                    log(f"warning: {spec['name']}.glb exceeds the workbench budget: {'; '.join(over)}")
        entries.append({
            "name": spec["name"],
            "type": spec["type"],
            "index": spec["index"],
            "seed": spec["seed"],
            "files": {k: _rel(v, out) for k, v in res.get("files", {}).items()},
            "preview": _rel(res.get("preview"), out),
            "icon": _rel(res.get("icon"), out),
            "pivots": {o.name: [round(c, 4) for c in o.pivot] for o in asset.objects if any(o.pivot)},
            "behaviours": asset.behaviours,
            "stats": asset.stats(),
            "renderers": sum(1 for o in asset.objects if o.mesh is not None),  # Cube Escape: 1 = flat copy possible
            **({"runtime_budget": res["runtime_budget"]} if res.get("runtime_budget") else {}),
            "asset_hash": asset.digest(),
            **({"lods": lod_data(asset, lod_of(spec))} if spec.get("lod") else {}),
            "meta": {k: v for k, v in asset.meta.items() if k not in ("type", "seed")},
            **({"family": spec["family"]} if spec.get("family") else {}),
            **({"param_sources": spec["param_sources"]} if spec.get("param_sources") else {}),
            "connectors": unity_connectors(asset, spec["type"]),
            **({"set": spec["set"]["name"]} if spec.get("set") else {}),
            **({"dressing": {k: asset.p.used.get(k, param.default)
                             for k, param in dressing_params(spec["type"]).items()}}
               if dressing_params(spec["type"]) else {}),
            **({"build_key": spec["build_key"]} if spec.get("build_key") else {}),
            **({"baked": {k: _rel(v, out) for k, v in res["baked"].items()},
                "baked_material": res.get("baked_material"), "bake_device": res.get("bake_device")}
               if res.get("baked") else {}),
            **({"paint": res["paint"], "weight_layout": res.get("weight_layout"),
                "neutral": {k: (_rel(v, out) if isinstance(v, str) else [_rel(x, out) for x in v])
                            for k, v in res["neutral"].items()}} if res.get("neutral") else {}),
            # 0.24.0: the packed maps a shader reads (textures.neutral of contract version 3 - here for every version)
            **({"neutral_maps": {k: _rel(v, out) for k, v in res["neutral_maps"].items()}}
               if res.get("neutral_maps") else {}),
        })
    cfg = asdict(config)
    cfg["style"] = config.style.to_dict()
    family_info = None
    if config.family:
        family_info = dict(config.family, fit=family_fit(specs, log, config.family.get("dims"),
                                                         config.family.get("reference")))
        cfg.pop("family", None)
    for key in ("out_dir", "models_dir", "library_dir", "icons_dir", "blender", "magick", "verbose", "force", "jobs",
                "paint_file"):  # local paths stay out; the custom scheme itself is kept (paint_scheme)
        cfg.pop(key, None)
    manifest = {
        "generator": "cubegen",
        "format": MANIFEST_FORMAT,
        "version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_hash": code_fingerprint(),
        "seed": config.seed,
        "config": cfg,
        "blender": blender_info or None,
        "imagemagick": magick_version,
        "overview_blend": _rel(blend_path, out) if blend_path and os.path.isfile(blend_path) else None,
        "material_swatch": _rel(swatch, out),
        "textures": {"mode": config.textures, "dir": _rel(textures_dir, out),
                     "materials": material_map} if textures else
        ({"mode": "palette", "dir": _rel(textures_dir, out), "material": palette["name"], "palette": config.palette,
          "manifest": _rel(os.path.join(textures_dir, palette_mod.palette_manifest_name(config.palette)), out)}
         if palette else None),
        "contact_sheet": _rel(sheet, out),
        "sets": [dict(entry, preview=_rel(entry["preview"], out)) for entry in sets],
        # the light colours of the paint scheme for Unity (ToDo 26/28): glow parts keep M_Glow<colour>, crystal parts
        # M_Crystal - a crystal material there takes crystal_color (sRGB hex)
        "paint": ({"name": config.paint, "glow": PAINTS[config.paint]["glow"],
                   "crystal_color": PAINTS[config.paint]["crystal_color"],
                   "edge_glow_color": PAINTS[config.paint]["edge_glow_color"]} if config.paint else None),
        "family": family_info,
        # 0.24.0: the material names split off M_Crystal (contract section materials) with their values, so Cube Escape
        # can add them to its material library; "written": false = this run wrote M_Crystal (--contract 2 or 1)
        "materials": split_materials(written=config.contract >= 3),
        # which connector kinds (models[].connectors[].kind) join, and how (ROADMAP ToDo 16)
        "joins": join_table(),
        # dressing parameters per type and the paint scheme each value belongs to (ToDo 30)
        "dressings": dressing_table(),
        "timings": None,
        "models": entries,
    }
    lap("manifest")
    built = sum(1 for spec in specs if results.get(spec["name"]) and not results[spec["name"]].get("reused"))
    load["end"] = system_load()
    report = stage_report(seconds, worker, built, config, load, workers, steps)
    report["overlap"] = overlap
    manifest["timings"] = report
    log("timings: " + ", ".join(f"{k} {v:.1f} s" for k, v in report["seconds"].items())
        + ("; in Blender (sum over processes): " + ", ".join(f"{k} {v:.1f} s" for k, v in worker.items())
           if worker else ""))
    measured = dict(report["seconds"], **report["worker_seconds"])
    for stage in report["slow"]:
        log(f"warning: {stage} took {measured[stage]:.1f} s, budget {report['budgets'][stage]:.1f} s "
            f"({built} model(s) built)")
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    for key in ("previews", "icons"):  # empty folders are just noise
        if os.path.isdir(dirs[key]) and not os.listdir(dirs[key]):
            shutil.rmtree(dirs[key])
    log(f"done: {len(specs)} asset(s) in {out}")
    return manifest


__all__ = ["BatchConfig", "FORMATS", "generate_batch", "plan_models", "BlenderError", "ImageMagickError"]
