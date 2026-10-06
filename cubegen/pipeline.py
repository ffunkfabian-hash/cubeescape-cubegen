"""Batch pipeline: seeds -> Blender (export, previews, overview .blend) -> ImageMagick (icons, sheet) -> manifest."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from . import __version__
from .blender import BlenderError, blender_version, find_blender, resolve_engine, run_job
from .imagemagick import ImageMagick, ImageMagickError
from .asset import to_unity
from .models import REGISTRY, asset_name, generate_asset, model_types
from .objwriter import write_mtl, write_obj
from .params import Style
from .materials import MATERIALS
from .textures import TEXTURE_MODES, build_texture_set
from .variety import pick_unique

BAKE_KEEP = {"M_GlowCyan", "M_GlowRed", "M_GlowOrange", "M_Crystal", "M_Glass"}  # = bake.KEEP
from .seeds import model_seed

FORMATS = ("fbx", "glb", "gltf", "obj")


@dataclass
class BatchConfig:
    seed: int
    models: Dict[str, Union[int, List[int]]]  # type -> count (indices 0..n-1) or explicit variant indices
    out_dir: str
    unique: bool = False           # counts: skip variants that look like an earlier one (see variety.py)
    lods: bool = False             # static models: + low detail level, FBX objects <part>_LOD0 / _LOD1
    force: bool = False            # rebuild everything (default: reuse unchanged models of the last run)
    jobs: int = 1                  # Blender processes working in parallel
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
    style: Style = field(default_factory=Style)
    icon_azimuth: float = 33.0     # degrees, like the ICONS table of generate_assets.py (+ = from the right)
    icon_elevation: float = 31.0
    icon_zoom: float = 1.0         # > 1 = closer
    textures: str = "none"         # none | tiled (ImageMagick tile textures) | baked (+ per-asset grime atlas)
    texture_size: int = 512
    texture_set: str = ""          # name of the texture variant -> material names MT_<set>_<Material>
    textures_dir: Optional[str] = None  # default: <models dir>/Textures
    blender: Optional[str] = None
    magick: Optional[str] = None
    verbose: bool = False

    def validate(self) -> None:
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
        if self.textures not in TEXTURE_MODES:
            raise ValueError(f"textures must be one of {', '.join(TEXTURE_MODES)}")
        if self.texture_size < 64 or self.texture_size & (self.texture_size - 1):
            raise ValueError("texture size must be a power of two >= 64")
        if self.texture_set and not self.texture_set.replace("_", "").isalnum():
            raise ValueError("texture set: letters, digits and _ only")
        if self.icon_zoom <= 0:
            raise ValueError("icon zoom must be > 0")
        if self.jobs < 1:
            raise ValueError("jobs must be >= 1")
        if self.lods and self.textures == "baked":
            raise ValueError("--lods can't be combined with --textures baked (the atlas is baked per object)")


def _spec(config: BatchConfig, model_type: str, index: int) -> Dict:
    return {
        "name": asset_name(model_type, index, config.prefix),
        "type": model_type,
        "index": index,
        "seed": model_seed(config.seed, model_type, index),
        "scale": config.scale,
        "params": dict(config.params.get(model_type, {})),
        "style": config.style.to_dict(),
    }


def plan_models(config: BatchConfig, log: Optional[Callable[[str], None]] = None) -> List[Dict]:
    """Names and seeds of every asset in the batch (deterministic).

    With ``config.unique`` a count takes the first indices whose models differ
    from each other (Crate_000, Crate_002, ...): names and seeds stay the ones
    of those indices, so ``--pick`` rebuilds them exactly.
    """
    specs = []
    for model_type, value in config.models.items():
        if isinstance(value, list):
            indices = sorted(set(value))
        elif config.unique and value > 1:
            indices, tried = pick_unique(value, lambda i: build_spec(_spec(config, model_type, i)))
            if len(indices) < value and log:
                log(f"{model_type}: only {len(indices)} different variants among the first {tried} - "
                    "using those")
        else:
            indices = list(range(value))
        specs.extend(_spec(config, model_type, index) for index in indices)
    return specs


def rig_data(asset, spec: Dict, master_seed: int, material_map: Optional[Dict[str, str]] = None) -> Dict:
    """Everything a Unity prefab builder needs besides the FBX, in Unity coordinates.

    Animations are not baked into the FBX: the game's scripts move parts with
    fields set by the prefab builders, so this file carries those values.
    """
    entry = REGISTRY[spec["type"]]
    parts = []
    for o in asset.objects:
        parent = asset.get(o.parent) if o.parent else None
        local = tuple(o.pivot[i] - (parent.pivot[i] if parent else 0.0) for i in range(3))
        entry_part = {
            "name": o.name,
            "parent": o.parent,
            "localPosition": list(to_unity(local)),
            "empty": o.is_empty,
            "materials": [] if o.is_empty else sorted({(material_map or {}).get(r, r) for r in o.mesh.roles}),
        }
        if not o.is_empty:  # box collider hint relative to the part's own pivot (Unity coordinates)
            (bx0, by0, bz0), (bx1, by1, bz1) = o.mesh.bbox()
            center = tuple((lo_ + hi_) / 2 - o.pivot[i] for i, (lo_, hi_) in enumerate(((bx0, bx1), (by0, by1), (bz0, bz1))))
            entry_part["bounds"] = {"center": list(to_unity(center)),
                                    "size": [abs(c) for c in to_unity((bx1 - bx0, by1 - by0, bz1 - bz0))]}
        parts.append(entry_part)
    lo, hi = asset.bbox()
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
        # explicit collision shapes (walkable pieces, moving lids / decks); missing = use a box hull
        **({"colliders": asset.collider_data()} if asset.colliders else {}),
    }


def lod_data(asset, lod) -> Dict:
    """``"lods"`` of <Name>.cubegen.json: the FBX objects are <part>_LOD0 / <part>_LOD1."""
    return {"objects": "<part>_LOD<level>", "note": "Unity builds the LODGroup on import from the _LOD names",
            "levels": [{"suffix": "_LOD0", "triangles": asset.stats()["triangles"]},
                       {"suffix": "_LOD1", "triangles": lod.stats()["triangles"]}]}


def build_spec(spec: Dict):
    """The asset a planned spec describes (same call as inside Blender)."""
    return generate_asset(spec["type"], spec["seed"], spec["name"], spec["scale"], params=spec.get("params"),
                          style=Style.from_dict(spec.get("style")))


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
                        "baked_material": entry.get("baked_material")})
        paths = list(res["files"].values()) + list(res.get("baked", {}).values())
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


def _run_jobs(blender: str, job: Dict, specs: List[Dict], todo: List[Dict], blend_path: Optional[str],
              jobs: int, verbose: bool, log: Callable[[str], None]) -> Dict:
    """Run the worker: one process, or ``jobs`` processes + one that only builds the overview .blend."""
    todo_names = {s["name"] for s in todo}
    if jobs <= 1 or len(todo) <= 1:
        models = [dict(s, skip=s["name"] not in todo_names) for s in specs] if blend_path else todo
        runs = [dict(job, models=models, blend=blend_path)]
    else:
        chunks = [todo[i::jobs] for i in range(min(jobs, len(todo)))]
        runs = [dict(job, models=chunk, blend=None) for chunk in chunks]
        if blend_path:  # cheap: builds the meshes, no export / render / bake
            runs.append(dict(job, models=[dict(s, skip=True) for s in specs], blend=blend_path))

    def run(index_job):
        index, run_spec = index_job
        prefix = f"[{index + 1}/{len(runs)}] " if len(runs) > 1 else ""
        with tempfile.TemporaryDirectory(prefix="cubegen_job_") as work:
            return run_job(blender, run_spec, work, verbose, lambda m: log(prefix + m))

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
    merged = {"models": [m for o in outputs for m in o["models"]], "blender": outputs[0].get("blender"),
              "engine": next((o.get("engine") for o in outputs if o["models"]), outputs[0].get("engine"))}
    return merged


def generate_batch(config: BatchConfig, log: Callable[[str], None] = print) -> Dict:
    config.validate()
    specs = plan_models(config, log)
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
            asset = build_spec(spec)
            if not asset.behaviours:
                category = REGISTRY[spec["type"]].category.capitalize()
                spec["models_dir"] = os.path.join(os.path.abspath(config.library_dir), category)
        os.makedirs(spec["models_dir"], exist_ok=True)

    im = ImageMagick(config.magick)
    swatch = im.material_swatch(os.path.join(out, "materials.png"))

    textures: Dict[str, Dict] = {}
    textures_dir = None
    if config.textures != "none":
        textures_dir = os.path.abspath(config.textures_dir) if config.textures_dir \
            else os.path.join(dirs["models"], "Textures")
        textures = build_texture_set(im, textures_dir, config.texture_size, config.texture_set, log=log)
    material_map = {plain: info["name"] for plain, info in textures.items()}

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
                                                                         config.texture_set, textures_dir],
                    "render": [config.render, config.engine, config.render_size, config.samples,
                               config.icon_azimuth, config.icon_elevation, config.icon_zoom]}
        for spec in specs:
            spec["build_key"] = build_key(spec, settings)
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
            "texture_mode": config.textures,
            "texture_size": config.texture_size,
            "textures_dir": textures_dir,
            "magick": im.convert,
            "render": {"enabled": config.render, "engine": engine, "size": config.render_size,
                       "samples": config.samples, "azimuth": config.icon_azimuth,
                       "elevation": config.icon_elevation, "zoom": config.icon_zoom},
        }
        results = dict(reused)
        blender_info = {"version": version, "render_engine": None}
        if todo or (blend_path and not os.path.isfile(blend_path)):
            log(f"Blender: {blender} - {len(todo)} asset(s), formats: {', '.join(formats)}")
            result = _run_jobs(blender, job, specs, todo, blend_path, config.jobs, config.verbose, log)
            results.update({r["name"]: r for r in result["models"]})
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
            write_mtl(os.path.join(folder, "CubeEscape_Materials.mtl"), textures)
        for spec in specs:
            asset = build_spec(spec)
            path = os.path.join(spec["models_dir"], f"{spec['name']}.obj")
            write_obj(asset, path, "CubeEscape_Materials.mtl", material_map,
                      lod=build_spec(lod_spec(spec)) if spec.get("lod") else None)
            results[spec["name"]] = {"files": {"obj": path}, "preview": None}
            log(f"{spec['name']}: {asset.stats()['triangles']} tris")

    # --- ImageMagick post processing --------------------------------------
    previews, labels = [], []
    for spec in specs:
        res = results.get(spec["name"], {})
        if res.get("preview") and os.path.isfile(res["preview"]):
            icon = os.path.join(dirs["icons"], f"Icon_{spec['name']}.png")
            im.make_icon(res["preview"], icon, config.icon_size, config.icon_background)
            res["icon"] = icon
            previews.append(res["preview"])
            labels.append(spec["name"])
    sheet = None
    if previews:
        sheet = im.contact_sheet(previews, labels, os.path.join(out, "contact_sheet.png"),
                                 title=f"Cube Escape - seed {config.seed}")
        log(f"contact sheet -> {sheet}")

    # --- manifest + rig data ----------------------------------------------------
    entries = []
    for spec in specs:
        asset = build_spec(spec)
        res = results.get(spec["name"], {})
        if config.rig_data:
            rig_path = os.path.join(spec["models_dir"], f"{spec['name']}.cubegen.json")
            with open(rig_path, "w", encoding="utf-8") as fh:
                asset_map = material_map
                if res.get("baked_material"):  # every non-glow material became the asset's atlas material
                    asset_map = {m: res["baked_material"] for m in MATERIALS if m not in BAKE_KEEP}
                rig = rig_data(asset, spec, config.seed, asset_map)
                if spec.get("lod"):
                    rig["lods"] = lod_data(asset, build_spec(lod_spec(spec)))
                if textures:
                    rig["textures"] = {"mode": config.textures,
                                       "manifest": _rel(os.path.join(textures_dir, "CubeEscape_Textures.json"),
                                                        spec["models_dir"])}
                    if res.get("baked"):
                        rig["textures"]["baked"] = {k: _rel(v, spec["models_dir"]) for k, v in res["baked"].items()}
                json.dump(rig, fh, indent=2)
            res.setdefault("files", {})["rig"] = rig_path
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
            **({"lods": lod_data(asset, build_spec(lod_spec(spec)))} if spec.get("lod") else {}),
            "meta": {k: v for k, v in asset.meta.items() if k not in ("type", "seed")},
            **({"build_key": spec["build_key"]} if spec.get("build_key") else {}),
            **({"baked": {k: _rel(v, out) for k, v in res["baked"].items()},
                "baked_material": res.get("baked_material")} if res.get("baked") else {}),
        })
    cfg = asdict(config)
    cfg["style"] = config.style.to_dict()
    for key in ("out_dir", "models_dir", "library_dir", "icons_dir", "blender", "magick", "verbose", "force", "jobs"):
        cfg.pop(key, None)
    manifest = {
        "generator": "cubegen",
        "version": __version__,
        "seed": config.seed,
        "config": cfg,
        "blender": blender_info or None,
        "imagemagick": im.version(),
        "overview_blend": _rel(blend_path, out) if blend_path and os.path.isfile(blend_path) else None,
        "material_swatch": _rel(swatch, out),
        "textures": {"mode": config.textures, "dir": _rel(textures_dir, out),
                     "materials": material_map} if textures else None,
        "contact_sheet": _rel(sheet, out),
        "models": entries,
    }
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    for key in ("previews", "icons"):  # empty folders are just noise
        if os.path.isdir(dirs[key]) and not os.listdir(dirs[key]):
            shutil.rmtree(dirs[key])
    log(f"done: {len(specs)} asset(s) in {out}")
    return manifest


__all__ = ["BatchConfig", "FORMATS", "generate_batch", "plan_models", "BlenderError", "ImageMagickError"]
