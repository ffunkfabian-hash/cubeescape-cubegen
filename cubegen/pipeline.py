"""Batch pipeline: seeds -> Blender (export, previews, overview .blend) -> ImageMagick (icons, sheet) -> manifest."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Optional, Union

from . import __version__
from .blender import BlenderError, find_blender, resolve_engine, run_job
from .imagemagick import ImageMagick, ImageMagickError
from .models import asset_name, generate_asset, model_types
from .objwriter import write_mtl, write_obj
from .seeds import model_seed

FORMATS = ("fbx", "glb", "gltf", "obj")


@dataclass
class BatchConfig:
    seed: int
    models: Dict[str, Union[int, List[int]]]  # type -> count (indices 0..n-1) or explicit variant indices
    out_dir: str
    formats: List[str] = field(default_factory=lambda: ["fbx"])
    prefix: str = ""
    scale: float = 1.0
    blend: bool = True
    use_blender: bool = True
    render: bool = True
    engine: str = "auto"
    render_size: int = 384
    samples: int = 32
    icon_size: int = 256
    icon_background: Optional[str] = None
    models_dir: Optional[str] = None
    icons_dir: Optional[str] = None
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


def plan_models(config: BatchConfig) -> List[Dict]:
    """Names and seeds of every asset in the batch (deterministic)."""
    specs = []
    for model_type, value in config.models.items():
        indices = sorted(set(value)) if isinstance(value, list) else range(value)
        for index in indices:
            specs.append({
                "name": asset_name(model_type, index, config.prefix),
                "type": model_type,
                "index": index,
                "seed": model_seed(config.seed, model_type, index),
                "scale": config.scale,
            })
    return specs


def _rel(path: Optional[str], base: str) -> Optional[str]:
    return os.path.relpath(path, base).replace(os.sep, "/") if path else None


def generate_batch(config: BatchConfig, log: Callable[[str], None] = print) -> Dict:
    config.validate()
    specs = plan_models(config)
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

    im = ImageMagick(config.magick)
    swatch = im.material_swatch(os.path.join(out, "materials.png"))

    results: Dict[str, Dict] = {}
    blender_info: Dict[str, object] = {}
    formats = list(config.formats)
    blend_path = None
    if config.use_blender:
        blender = find_blender(config.blender)
        if not blender:
            raise BlenderError("Blender not found. Install Blender, set $BLENDER, pass --blender PATH "
                               "or use --no-blender for a pure-Python OBJ export.")
        engine = resolve_engine(blender, config.engine, log) if config.render else None
        blend_path = os.path.join(out, f"CubeEscape_Generated_{config.seed}.blend") if config.blend else None
        job = {
            "models": specs,
            "formats": formats,
            "models_dir": dirs["models"],
            "previews_dir": dirs["previews"],
            "blend": blend_path,
            "render": {"enabled": config.render, "engine": engine, "size": config.render_size,
                       "samples": config.samples},
        }
        log(f"Blender: {blender} - {len(specs)} asset(s), formats: {', '.join(formats)}")
        with tempfile.TemporaryDirectory(prefix="cubegen_job_") as work:
            result = run_job(blender, job, work, config.verbose, log)
        results = {r["name"]: r for r in result["models"]}
        blender_info = {"version": result.get("blender"),
                        "render_engine": result.get("engine") if config.render else None}
    else:
        if formats != ["obj"]:
            log("--no-blender: only OBJ export is available, ignoring other formats")
        formats = ["obj"]
        write_mtl(os.path.join(dirs["models"], "CubeEscape_Materials.mtl"))
        for spec in specs:
            asset = generate_asset(spec["type"], spec["seed"], spec["name"], spec["scale"])
            path = os.path.join(dirs["models"], f"{spec['name']}.obj")
            write_obj(asset, path, "CubeEscape_Materials.mtl")
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

    # --- manifest -----------------------------------------------------------
    entries = []
    for spec in specs:
        asset = generate_asset(spec["type"], spec["seed"], spec["name"], spec["scale"])
        res = results.get(spec["name"], {})
        entries.append({
            "name": spec["name"],
            "type": spec["type"],
            "index": spec["index"],
            "seed": spec["seed"],
            "files": {k: _rel(v, out) for k, v in res.get("files", {}).items()},
            "preview": _rel(res.get("preview"), out),
            "icon": _rel(res.get("icon"), out),
            "pivots": {o.name: [round(c, 4) for c in o.pivot] for o in asset.objects if any(o.pivot)},
            "stats": asset.stats(),
            "meta": {k: v for k, v in asset.meta.items() if k not in ("type", "seed")},
        })
    cfg = asdict(config)
    for key in ("out_dir", "models_dir", "icons_dir", "blender", "magick", "verbose"):
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
