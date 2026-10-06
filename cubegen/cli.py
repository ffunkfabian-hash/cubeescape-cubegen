"""Command line interface: ``python -m cubegen <command>``."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
from typing import Dict, List, Optional

from . import __version__
from .blender import BlenderError, blender_version, find_blender, probe_engine
from .imagemagick import ImageMagickError, find_imagemagick
from .models import REGISTRY, generate_asset, model_types
from .params import Style, parse_param_overrides
from .pipeline import FORMATS, BatchConfig, build_spec, generate_batch, plan_models
from .seeds import parse_seed

# recipe keys that map 1:1 onto BatchConfig fields
_RECIPE_FIELDS = ("formats", "prefix", "scale", "blend", "rig_data", "render", "engine", "render_size", "samples",
                  "icon_size", "icon_background", "models_dir", "library_dir", "icons_dir", "icon_azimuth",
                  "icon_elevation", "icon_zoom", "textures", "texture_size", "texture_set", "textures_dir",
                  "unique", "lods")
RECIPE_KEYS = ("seed", "models", "params", "style", "out") + _RECIPE_FIELDS
# global style options: CLI flag -> Style field
_STYLE_FLAGS = {"size": "size", "snap": "snap", "glow": "glow", "material_style": "material", "warning": "warning",
                "wear": "wear", "detail": "detail", "damage": "damage", "theme": "theme"}


def _csv(value: str) -> List[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def unknown_key(what: str, key: str, allowed) -> ValueError:
    """``unknown key 'stlye' (did you mean 'style'?)`` - typos must not be silently ignored."""
    close = difflib.get_close_matches(key, list(allowed), n=1)
    hint = f" (did you mean {close[0]!r}?)" if close else ""
    return ValueError(f"{what}: unknown key {key!r}{hint}; allowed: {', '.join(allowed)}")


def _count_or_indices(where: str, value):
    """A model entry: a count (int) or a list of variant indices."""
    if isinstance(value, bool):
        raise ValueError(f"{where}: expected a count or a list of variant indices, got {value!r}")
    if isinstance(value, str) and value.strip().isdigit():  # "3" was accepted before 0.8
        value = int(value)
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, list) and value and all(isinstance(i, int) and not isinstance(i, bool) and i >= 0
                                                 for i in value):
        return value
    raise ValueError(f"{where}: expected a count >= 0 or a list of variant indices like [0, 3, 7], got {value!r}")


def _load_recipe(path: str) -> Dict:
    """Read and check a recipe. Keys starting with ``_`` are comments."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            recipe = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: not valid JSON ({exc})") from exc
    if not isinstance(recipe, dict):
        raise ValueError(f"{path}: a recipe is a JSON object {{...}}")
    recipe = {k: v for k, v in recipe.items() if not k.startswith("_")}
    for key in recipe:
        if key not in RECIPE_KEYS:
            raise unknown_key(path, key, RECIPE_KEYS)
    models = recipe.get("models", {})
    if isinstance(models, list):  # [{"type": "crate", "count": 3}, {"type": "door", "pick": [0, 7]}, ...]
        result = {}
        for i, entry in enumerate(models):
            where = f"{path}: models[{i}]"
            if not isinstance(entry, dict) or "type" not in entry:
                raise ValueError(f'{where}: expected {{"type": ..., "count": n}} or {{"type": ..., "pick": [...]}}')
            for key in entry:
                if key not in ("type", "count", "pick") and not key.startswith("_"):
                    raise unknown_key(where, key, ("type", "count", "pick"))
            if "count" in entry and "pick" in entry:
                raise ValueError(f"{where}: use either count or pick")
            value = entry["pick"] if "pick" in entry else entry.get("count", 1)
            result[entry["type"]] = _count_or_indices(f"{where} ({entry['type']})", value)
        models = result
    elif isinstance(models, dict):
        models = {t: _count_or_indices(f"{path}: models.{t}", v) for t, v in models.items()}
    else:
        raise ValueError(f"{path}: models must be an object {{type: count}} or a list")
    recipe["models"] = models
    for key in ("params", "style"):
        if not isinstance(recipe.get(key, {}), dict):
            raise ValueError(f"{path}: {key} must be an object")
    for model_type, values in recipe.get("params", {}).items():
        if not isinstance(values, dict):
            raise ValueError(f'{path}: params.{model_type} must be an object like {{"style": "airlock"}}')
    return recipe


def build_config(args: argparse.Namespace) -> BatchConfig:
    recipe = _load_recipe(args.recipe) if args.recipe else {}
    seed = parse_seed(args.seed if args.seed is not None else recipe.get("seed"))

    if args.pick:
        models: Dict = {}
        for item in args.pick:
            model_type, _, index = item.partition(":")
            if not index.isdigit():
                raise ValueError(f"--pick expects TYPE:INDEX, e.g. crate:3 (got {item!r})")
            models.setdefault(model_type, []).append(int(index))
    elif args.types:
        types = model_types() if args.types == ["all"] else args.types
        models = {t: args.count if args.count is not None else 1 for t in types}
    elif recipe.get("models"):
        models = dict(recipe["models"])
        if args.count is not None:
            models = {t: args.count for t in models}
    else:
        models = {t: args.count if args.count is not None else 1 for t in model_types()}

    values = {k: recipe[k] for k in _RECIPE_FIELDS if k in recipe}
    cli = {
        "formats": args.formats, "prefix": args.prefix, "scale": args.scale, "engine": args.engine,
        "render_size": args.render_size, "samples": args.samples, "icon_size": args.icon_size,
        "icon_background": args.icon_bg, "models_dir": args.models_dir, "icons_dir": args.icons_dir,
        "library_dir": args.library_dir, "textures": args.textures, "texture_size": args.texture_size,
        "texture_set": args.texture_set, "textures_dir": args.textures_dir,
    }
    values.update({k: v for k, v in cli.items() if v is not None})
    # parameters: recipe {"params": {"door": {"style": "airlock"}}}, then --param door.style=airlock
    params: Dict[str, Dict] = {t: dict(v) for t, v in recipe.get("params", {}).items()}
    for model_type, overrides in parse_param_overrides(args.param or []).items():
        params.setdefault(model_type, {}).update(overrides)
    values["params"] = params
    style = dict(recipe.get("style", {}))
    for flag, key in _STYLE_FLAGS.items():
        if getattr(args, flag) is not None:
            style[key] = getattr(args, flag)
    values["style"] = Style.from_dict(style)
    if args.unique:
        values["unique"] = True
    if args.lods:
        values["lods"] = True
    if args.icon_angle:
        az, _, el = args.icon_angle.partition(",")
        values["icon_azimuth"] = float(az)
        if el:
            values["icon_elevation"] = float(el)
    if args.icon_zoom is not None:
        values["icon_zoom"] = args.icon_zoom
    if args.no_render:
        values["render"] = False
    if args.no_blend:
        values["blend"] = False
    if args.no_rig_data:
        values["rig_data"] = False
    out = args.out or recipe.get("out") or os.path.join("output", f"seed_{seed}")
    return BatchConfig(seed=seed, models=models, out_dir=out, use_blender=not args.no_blender,
                       blender=args.blender, magick=args.magick, verbose=args.verbose, **values)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_generate(args) -> int:
    config = build_config(args)
    config.validate()
    print(f"cubegen {__version__} | seed {config.seed} | out {config.out_dir}")
    if config.style.theme is not None:
        r = config.style.resolved()
        print(f"theme {config.style.theme!r}: glow {r.glow}, material {r.material}, wear {r.wear}, "
              f"warning {r.warning or 'per asset'}")
    if args.dry_run:
        for spec in plan_models(config, log=lambda m: print("  " + m)):
            st = build_spec(spec).stats()
            dims = " x ".join(f"{d:.2f}" for d in st["dimensions_m"])
            print(f"  {spec['name']:<20} seed {spec['seed']:>10}  {st['triangles']:>5} tris  {dims} m  "
                  f"[{', '.join(st['objects'])}]")
        return 0
    generate_batch(config, log=lambda m: print("  " + m))
    return 0


def cmd_list(args) -> int:
    if args.json:
        print(json.dumps({e.name: {"title": e.title, "category": e.category, "pivot": e.pivot,
                                   "description": e.description} for e in REGISTRY.values()}, indent=2))
        return 0
    by_cat: Dict[str, List] = {}
    for entry in REGISTRY.values():
        by_cat.setdefault(entry.category, []).append(entry)
    for cat in sorted(by_cat):
        print(f"{cat}:")
        for e in sorted(by_cat[cat], key=lambda e: e.name):
            print(f"  {e.name:<16} {e.description}")
    print(f"\nformats: {', '.join(FORMATS)}")
    return 0


def cmd_params(args) -> int:
    """Parameters of one or all model types."""
    types = [args.type] if args.type else model_types()
    for t in types:
        if t not in REGISTRY:
            raise ValueError(f"unknown model type {t!r}; available: {', '.join(model_types())}")
        entry = REGISTRY[t]
        print(f"{t}  ({entry.title}, {entry.category})")
        for p in entry.params:
            print(f"  {t}.{p.describe()}")
        print()
    print("global: --theme TEXT  --size S|M|L  --snap 0.5  --glow cyan|red|orange")
    print("        --material-style metal|wall|dark|light")
    print("        --warning none|always  --wear none|light|heavy  --detail low|normal|high")
    print("        --damage intact|damaged|destroyed")
    print("        --icon-angle AZIMUT,ELEVATION  --icon-zoom 1.2")
    return 0


def cmd_doctor(args) -> int:
    ok = True
    print(f"python        {sys.version.split()[0]} ({sys.executable})")
    im = find_imagemagick(args.magick)
    if im:
        print(f"imagemagick   {im.version()}")
    else:
        ok = False
        print("imagemagick   NOT FOUND - install from https://imagemagick.org")
    try:
        blender = find_blender(args.blender)
    except BlenderError as exc:
        blender = None
        print(f"blender       {exc}")
    if blender:
        print(f"blender       {blender_version(blender)} ({blender})")
        for engine in ("workbench", "cycles"):
            state = "ok" if probe_engine(blender, engine) else "not available"
            print(f"  render {engine:<10} {state}")
    else:
        ok = False
        print("blender       NOT FOUND - install Blender >= 3.6, set $BLENDER or use --no-blender")
    print(f"model types   {len(model_types())}: {', '.join(model_types())}")
    return 0 if ok else 1


# ---------------------------------------------------------------------------

def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cubegen", description="Seeded low-poly asset generator for Cube Escape.")
    parser.add_argument("--version", action="version", version=f"cubegen {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="generate a batch of assets")
    g.add_argument("--seed", help="master seed (int or any text); random if omitted")
    g.add_argument("--recipe", help="JSON recipe with seed and model counts")
    g.add_argument("--types", type=_csv, help="comma separated model types or 'all'")
    g.add_argument("--count", type=int, help="assets per type (default 1)")
    g.add_argument("--pick", type=_csv, help="only these variants, e.g. crate:3,door:7 (same names as with --count)")
    g.add_argument("--unique", action="store_true",
                   help="with --count: skip variants that look like an earlier one (same parts, sizes within 8%%)")
    g.add_argument("--param", action="append", metavar="TYPE.NAME=VALUE",
                   help="fix a parameter instead of rolling it, e.g. door.style=airlock (repeatable; "
                        "list: python -m cubegen params)")
    st = g.add_argument_group("style (all types)")
    st.add_argument("--theme", help="room theme (any text, e.g. lab-3): rolls glow, material style, wear and "
                                    "warning paint once for all assets; explicit options win")
    st.add_argument("--size", choices=["S", "M", "L"], help="size class: small / medium / large variants")
    st.add_argument("--snap", type=float, help="round main dimensions to multiples of this many metres (e.g. 0.5)")
    st.add_argument("--glow", choices=["cyan", "red", "orange"], help="fixed colour for decorative glow")
    st.add_argument("--material-style", choices=["metal", "wall", "dark", "light"], help="preferred body material")
    st.add_argument("--warning", choices=["none", "always"], help="warning stripes / bands never or always")
    st.add_argument("--wear", choices=["none", "light", "heavy"], help="rubble, plates and cables around models")
    st.add_argument("--detail", choices=["low", "normal", "high"], help="low: no bevels, fewer cylinder sides")
    st.add_argument("--damage", choices=["intact", "damaged", "destroyed"],
                    help="damaged: dents, knocked-off parts; destroyed: ruin (static, goes to the library)")
    tx = g.add_argument_group("textures (optional, default: none = plain M_ materials)")
    tx.add_argument("--textures", choices=["none", "tiled", "baked"],
                    help="tiled: ImageMagick tile textures as MT_ materials; baked: + per-asset grime atlas")
    tx.add_argument("--texture-size", type=int, help="texture resolution in px (default 512)")
    tx.add_argument("--texture-set", help="name of a texture variant (own seed and MT_<set>_ material names)")
    tx.add_argument("--textures-dir", help="where the textures go (default <models dir>/Textures)")
    g.add_argument("--icon-angle", help="preview/icon camera 'AZIMUTH,ELEVATION' in degrees (default 33,31)")
    g.add_argument("--icon-zoom", type=float, help="preview/icon zoom, > 1 = closer (default 1)")
    g.add_argument("--out", help="output directory (default output/seed_<seed>)")
    g.add_argument("--models-dir", help="write the model files here instead, e.g. <Unity>/Assets/Art/Models")
    g.add_argument("--library-dir", help="static decoration goes to <dir>/<Kategorie> instead, "
                                         "e.g. <Unity>/Assets/Art/Models/Library")
    g.add_argument("--icons-dir", help="write the icons here instead")
    g.add_argument("--formats", type=_csv, help=f"export formats: {', '.join(FORMATS)} (default fbx)")
    g.add_argument("--prefix", help="prefix for asset names, e.g. 'Gen_' -> Gen_Crate_000")
    g.add_argument("--scale", type=float, help="uniform scale factor (default 1.0 = metres)")
    g.add_argument("--lods", action="store_true",
                   help="static models: add a low detail level, FBX objects <part>_LOD0 / <part>_LOD1 "
                        "(Unity builds the LODGroup on import)")
    g.add_argument("--no-blend", action="store_true", help="don't save the overview .blend")
    g.add_argument("--no-rig-data", action="store_true",
                   help="don't write <Name>.cubegen.json (parts, pivots, script wiring for Unity)")
    g.add_argument("--no-blender", action="store_true", help="pure-Python OBJ export, no Blender needed")
    g.add_argument("--no-render", action="store_true", help="skip previews, icons and contact sheet")
    g.add_argument("--engine", choices=["auto", "workbench", "eevee", "cycles"], help="preview render engine")
    g.add_argument("--render-size", type=int, help="preview size in px (default 384)")
    g.add_argument("--samples", type=int, help="Cycles/Eevee samples (default 32)")
    g.add_argument("--icon-size", type=int, help="inventory icon size in px (default 256)")
    g.add_argument("--icon-bg", help="icon background colour, e.g. '#2b2b33' (default transparent)")
    g.add_argument("--blender", help="path to the Blender executable")
    g.add_argument("--magick", help="path to ImageMagick (magick or convert)")
    g.add_argument("--dry-run", action="store_true", help="only print names, seeds and stats")
    g.add_argument("-v", "--verbose", action="store_true", help="show Blender output")
    g.set_defaults(func=cmd_generate)

    ls = sub.add_parser("list", help="list model types and formats")
    ls.add_argument("--json", action="store_true")
    ls.set_defaults(func=cmd_list)

    pa = sub.add_parser("params", help="list the parameters of the model types")
    pa.add_argument("type", nargs="?", help="only this model type")
    pa.set_defaults(func=cmd_params)

    d = sub.add_parser("doctor", help="check Blender and ImageMagick installation")
    d.add_argument("--blender")
    d.add_argument("--magick")
    d.set_defaults(func=cmd_doctor)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        return args.func(args)
    except (BlenderError, ImageMagickError, ValueError, KeyError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
