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
from .params import DAMAGE_STATES, GENERATIONS, LATEST_GENERATION, Style, parse_param_overrides
from .paint import PAINTS, paint_names
from .palette import palette_names
from .pipeline import FORMATS, BatchConfig, build_spec, generate_batch, plan_models
from .seeds import parse_seed

# recipe keys that map 1:1 onto BatchConfig fields
_RECIPE_FIELDS = ("formats", "prefix", "scale", "blend", "rig_data", "render", "engine", "render_size", "samples",
                  "icon_size", "icon_background", "models_dir", "library_dir", "icons_dir", "icon_azimuth",
                  "icon_elevation", "icon_zoom", "textures", "texture_size", "texture_set", "textures_dir",
                  "palette", "unique", "lods", "jobs", "bake_device", "variant_set", "paint")
RECIPE_KEYS = ("seed", "models", "params", "style", "out", "family", "dims", "description") + _RECIPE_FIELDS
# global style options: CLI flag -> Style field
_STYLE_FLAGS = {"size": "size", "snap": "snap", "glow": "glow", "material_style": "material", "warning": "warning",
                "wear": "wear", "detail": "detail", "damage": "damage", "clutter": "clutter",
                "theme": "theme", "generation": "generation"}


def _csv(value: str) -> List[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def _jobs(value: str) -> int:
    """``--jobs auto`` -> 0 (the pipeline decides), else a number >= 1."""
    if value.strip().lower() == "auto":
        return 0
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("a number >= 1 or 'auto'") from None
    if number < 1:
        raise argparse.ArgumentTypeError("a number >= 1 or 'auto'")
    return number


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


def load_recipe(path: str, family_file: bool = False) -> Dict:
    """Read and check a recipe (or a family file). Keys starting with ``_`` are comments.

    ``models`` comes back as {type: count | [indices]}; entries with their own ``params``
    (``{"type": "wall", "pick": [2], "params": {"opening": "door"}}``) also fill
    ``variant_params`` {type: {index: params}}.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            recipe = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: not valid JSON ({exc})") from exc
    if not isinstance(recipe, dict):
        raise ValueError(f"{path}: a recipe is a JSON object {{...}}")
    recipe = {k: v for k, v in recipe.items() if not k.startswith("_")}
    allowed = RECIPE_KEYS
    for key in recipe:
        if key not in allowed:
            raise unknown_key(path, key, allowed)
    if "family" in recipe and not isinstance(recipe["family"], str):
        raise ValueError(f"{path}: family must be a name")
    if not isinstance(recipe.get("dims", {}), dict):
        raise ValueError(f"{path}: dims must be an object")
    models = recipe.get("models", {})
    variant_params: Dict[str, Dict[int, Dict]] = {}
    if isinstance(models, list):  # [{"type": "crate", "count": 3}, {"type": "door", "pick": [0, 7]}, ...]
        result: Dict = {}
        for i, entry in enumerate(models):
            where = f"{path}: models[{i}]"
            if not isinstance(entry, dict) or "type" not in entry:
                raise ValueError(f'{where}: expected {{"type": ..., "count": n}} or {{"type": ..., "pick": [...]}}')
            for key in entry:
                if key not in ("type", "count", "pick", "params") and not key.startswith("_"):
                    raise unknown_key(where, key, ("type", "count", "pick", "params"))
            if "count" in entry and "pick" in entry:
                raise ValueError(f"{where}: use either count or pick")
            t = entry["type"]
            value = _count_or_indices(f"{where} ({t})", entry["pick"] if "pick" in entry else entry.get("count", 1))
            indices = list(range(value)) if isinstance(value, int) else value
            if t in result:  # the same type twice: distinct variants, each entry with its own params
                before = list(range(result[t])) if isinstance(result[t], int) else result[t]
                clash = sorted(set(before) & set(indices))
                if clash:
                    raise ValueError(f"{where}: {t} variant(s) {clash} listed twice - use distinct pick indices")
                result[t] = sorted(before + indices)
            else:
                result[t] = value
            if "params" in entry:
                if not isinstance(entry["params"], dict):
                    raise ValueError(f"{where}: params must be an object")
                for index in indices:
                    variant_params.setdefault(t, {})[index] = dict(entry["params"])
        models = result
    elif isinstance(models, dict):
        models = {t: _count_or_indices(f"{path}: models.{t}", v) for t, v in models.items()}
    else:
        raise ValueError(f"{path}: models must be an object {{type: count}} or a list")
    recipe["models"] = models
    recipe["variant_params"] = variant_params
    for key in ("params", "style"):
        if not isinstance(recipe.get(key, {}), dict):
            raise ValueError(f"{path}: {key} must be an object")
    for model_type, values in recipe.get("params", {}).items():
        if not isinstance(values, dict):
            raise ValueError(f'{path}: params.{model_type} must be an object like {{"style": "airlock"}}')
    return recipe


def build_config(args: argparse.Namespace) -> BatchConfig:
    from .families import load_family, resolve

    recipe = load_recipe(args.recipe) if args.recipe else {}
    family = None
    family_name = getattr(args, "family", None) or recipe.get("family")
    if family_name:
        from .families import check_dims, find_family

        base = os.path.dirname(os.path.abspath(args.recipe)) if args.recipe else None
        try:
            path = find_family(family_name, base)
        except ValueError:
            path = None
        # An overlay named lab.json can reference the built-in lab family. Its
        # filename alone must not turn it into a new, dimensionless definition.
        if path is not None and args.recipe and os.path.samefile(path, args.recipe) and "dims" not in recipe:
            from .families import FAMILY_DIR
            builtin = os.path.join(FAMILY_DIR, family_name + ".json")
            if os.path.isfile(builtin) and not os.path.samefile(builtin, args.recipe):
                path = builtin
        defines = args.recipe and recipe.get("family") == family_name and not getattr(args, "family", None) and \
            (path is None or os.path.samefile(path, args.recipe))
        if defines:  # the recipe is the family definition itself
            family, recipe = dict(recipe, _path=args.recipe), {}
            family["dims"] = check_dims(family.get("dims", {}), f"{args.recipe}: dims")
        elif path is None:
            raise ValueError(f"unknown family {family_name!r}; list: python -m cubegen families")
        else:
            family = load_family(path, base)
    match = None
    if getattr(args, "match", None):
        with open(args.match, "r", encoding="utf-8") as fh:
            match = json.load(fh)
        if not isinstance(match, dict) or "type" not in match:
            raise ValueError(f"--match: {args.match} is not a .cubegen.json")

    if args.pick:
        models: Optional[Dict] = {}
        for item in args.pick:
            model_type, _, index = item.partition(":")
            if not index.isdigit():
                raise ValueError(f"--pick expects TYPE:INDEX, e.g. crate:3 (got {item!r})")
            models.setdefault(model_type, []).append(int(index))
    elif args.types:
        types = model_types() if args.types == ["all"] else args.types
        models = {t: args.count if args.count is not None else 1 for t in types}
    else:
        models = None  # the recipe's / family's kit

    style = {}
    for flag, key in _STYLE_FLAGS.items():
        if getattr(args, flag) is not None:
            style[key] = getattr(args, flag)
    resolved = resolve(family, recipe, models=models, extra_params=parse_param_overrides(args.param or []),
                       extra_style=style, match=match)
    merged = resolved["values"]
    seed = parse_seed(args.seed if args.seed is not None else merged.get("seed"))
    models = merged["models"]
    if models and args.count is not None and not args.pick and not args.types:
        models = {t: args.count for t in models}
    if not models:
        models = {t: args.count if args.count is not None else 1 for t in model_types()}

    values = {k: merged[k] for k in _RECIPE_FIELDS if k in merged}
    if isinstance(values.get("jobs"), str):  # a recipe may say "jobs": "auto" like the command line
        try:
            values["jobs"] = _jobs(values["jobs"])
        except argparse.ArgumentTypeError as exc:
            raise ValueError(f"recipe jobs: {exc}") from None
    cli = {
        "formats": args.formats, "prefix": args.prefix, "scale": args.scale, "engine": args.engine,
        "render_size": args.render_size, "samples": args.samples, "icon_size": args.icon_size,
        "icon_background": args.icon_bg, "models_dir": args.models_dir, "icons_dir": args.icons_dir,
        "library_dir": args.library_dir, "textures": args.textures, "texture_size": args.texture_size,
        "texture_set": args.texture_set, "textures_dir": args.textures_dir, "palette": args.palette,
        "bake_device": args.bake_device,
    }
    values.update({k: v for k, v in cli.items() if v is not None})
    if args.palette:  # a colour palette means palette mode
        if values.get("textures", "none") not in ("none", "palette") and args.textures:
            raise ValueError(f"--palette needs --textures palette (not {args.textures})")
        values["textures"] = "palette"
    values["params"] = merged["params"]
    values["variant_params"] = {t: v for t, v in merged["variant_params"].items() if t in models}
    values["param_sources"] = resolved["param_sources"]
    values["family"] = resolved["family"]
    values["style"] = Style.from_dict(merged["style"])
    if args.unique:
        values["unique"] = True
    if args.lods:
        values["lods"] = True
    if args.force:
        values["force"] = True
    if args.jobs is not None:
        values["jobs"] = args.jobs
    if args.variant_set:
        values["variant_set"] = True
    if args.paint:
        values["paint"] = args.paint
    if values.get("paint"):  # a paint scheme is a baked atlas
        if values.get("textures", "baked") not in ("baked", "none"):
            raise ValueError(f"--paint needs --textures baked (not {values['textures']})")
        values["textures"] = "baked"
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
    if args.repair_safe:
        values["repair_safe"] = True
    recipe = merged
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
    specs = plan_models(config)
    if args.validate_only or args.strict:
        validation_report = validate_batch(config, specs, strict=args.strict)
        if args.validate_only:
            if args.report:
                _write_json(args.report, validation_report)
            print(f"validation: {validation_report['severity']} ({len(validation_report['assets'])} asset(s))")
            return 1 if validation_report["severity"] == "error" else 0
        if validation_report["severity"] == "error":
            if args.report:
                _write_json(args.report, validation_report)
            print("strict validation failed; export was not started", file=sys.stderr)
            return 1
    else:
        validation_report = None
    manifest = generate_batch(config, log=lambda m: print("  " + m))
    if args.report:
        if validation_report:
            manifest["validation"] = validation_report
        _write_json(args.report, manifest)
    return 0


def _write_json(path: str, data: Dict) -> None:
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def validate_batch(config: BatchConfig, specs: List[Dict], *, strict: bool = False) -> Dict:
    """Build and validate planned assets without invoking Blender or writing model exports."""
    from datetime import datetime, timezone

    from .pipeline import build_spec, code_fingerprint, family_fit
    from .quality import asset_quality_report, check
    from .variety import signature, similar

    if not specs:
        raise ValueError("nothing to validate (all counts are 0)")
    assets = []
    signatures: Dict[str, List] = {}
    for spec in specs:
        asset = build_spec(spec)
        errors = []
        try:
            asset.validate_contract(spec["type"])
        except ValueError as exc:
            errors.append(str(exc))
        entry = REGISTRY[spec["type"]]
        quality = check(asset, entry.category, entry.pivot,
                        budget_scale=1.5 if config.style.detail == "high" else 1.0,
                        palette=config.textures == "palette")
        summary = asset_quality_report(
            asset, entry.pivot, entry.category,
            budget_scale=1.5 if config.style.detail == "high" else 1.0,
            palette=config.textures == "palette", checked=quality,
        )
        errors.extend(quality["errors"])
        warnings = quality["warnings"]
        severity = "error" if errors or (strict and warnings) else "warning" if warnings else "pass"
        asset_signature = signature(asset)
        similar_to = next((prior_name for prior_name, prior_signature in signatures.get(spec["type"], [])
                           if similar(asset_signature, prior_signature)), None)
        signatures.setdefault(spec["type"], []).append((spec["name"], asset_signature))
        assets.append({
            "name": spec["name"], "type": spec["type"], "seed": spec["seed"],
            "asset_hash": asset.digest(), "stats": asset.stats(),
            "severity": severity, "errors": errors, "warnings": warnings,
            "quality": summary, "quality_score": summary["score"], "similar_to": similar_to,
            "safe_repairs": asset.meta.get("safe_repairs", []),
        })
    for model_type in {row["type"] for row in assets}:
        ranked = sorted((row for row in assets if row["type"] == model_type),
                        key=lambda row: (-row["quality_score"], row["stats"]["triangles"], row["name"]))
        for rank, row in enumerate(ranked, 1):
            row["quality_rank"] = rank
    family = family_fit(specs, dims=config.family["dims"]) if config.family else None
    has_error = any(row["severity"] == "error" for row in assets) or bool(family and family["problems"])
    has_warning = any(row["severity"] == "warning" for row in assets) or bool(family and family["look"])
    return {
        "generator": "cubegen", "version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_hash": code_fingerprint(), "seed": config.seed, "strict": strict,
        "severity": "error" if has_error else "warning" if has_warning else "pass",
        "family": family, "assets": assets,
    }


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
    print("        --damage intact|damaged|destroyed|fractured  --clutter none|clean|lived-in|chaotic")
    print("        --generation 1|2|3")
    print("        --icon-angle AZIMUT,ELEVATION  --icon-zoom 1.2")
    return 0


#: generate options a game UI may offer (style and textures); everything else is batch plumbing
CATALOG_OPTIONS = ("theme", "size", "snap", "glow", "material_style", "warning", "wear", "detail", "damage", "clutter",
                   "generation", "textures", "texture_size", "palette")


def catalog_data() -> Dict[str, object]:
    """Everything a front end needs to offer generation: types with their parameter schema, the style and texture
    options of ``generate`` (read from its argument parser - one source), palettes and families.

    ``typical`` is one reference build per type (seed 0, default style, pure Python, no Blender): its behaviours and
    size are a hint - parameters and damage states may change both.
    """
    from .families import family_files, load_family
    from .palette import COLOR_PALETTES, palette_material

    commands = next(a for a in make_parser()._actions if isinstance(a, argparse._SubParsersAction))  # noqa: SLF001
    options: Dict[str, object] = {}
    for action in commands.choices["generate"]._actions:  # noqa: SLF001
        if action.dest not in CATALOG_OPTIONS:
            continue
        kind = "choice" if action.choices else "float" if action.type is float else "int" if action.type is int else "text"
        options[action.dest] = {"flag": action.option_strings[0], "kind": kind,
                                "choices": [str(c) for c in action.choices] if action.choices else [],
                                "help": action.help or ""}
    types = {}
    for entry in REGISTRY.values():
        params = []
        for p in entry.params:
            params.append({"name": p.name, "kind": p.kind, "label": p.label, "description": p.description,
                           "min": p.lo, "max": p.hi, "choices": [str(c) for c in p.choices], "unity": p.unity,
                           "size": p.size, "default": p.default})
        typical = generate_asset(entry.name, 0)
        lo, hi = typical.bbox()
        types[entry.name] = {"title": entry.title, "category": entry.category, "pivot": entry.pivot,
                             "view": entry.view, "description": entry.description, "params": params,
                             "experimental": entry.name.startswith("test_") or entry.name == "geometry_test",
                             "typical": {"static": not typical.behaviours,
                                         "behaviours": sorted({str(b["script"]) for b in typical.behaviours}),
                                         "size": [round(hi[i] - lo[i], 3) for i in range(3)]}}
    families = {}
    for name, path in family_files().items():
        fam = load_family(path)
        families[name] = {"description": fam.get("description", ""), "dims": fam.get("dims", {}),
                          "style": fam.get("style", {}), "palette": fam.get("palette"),
                          "kit": {t: (len(v) if isinstance(v, list) else v) for t, v in fam.get("models", {}).items()}}
    palettes = {name: {"material": palette_material(name),
                       "description": str(COLOR_PALETTES.get(name, {}).get("description", ""))}
                for name in palette_names()}
    return {"catalog": 1, "generator": f"cubegen {__version__}", "version": __version__,
            "generations": list(GENERATIONS), "latestGeneration": LATEST_GENERATION, "formats": list(FORMATS),
            "options": options, "palettes": palettes, "families": families, "types": types,
            "paints": {name: {"label": PAINTS[name]["label"], "glow": PAINTS[name]["glow"]} for name in paint_names()}}


def cmd_catalog(args) -> int:
    """Machine-readable catalog for game front ends (Cube Escape's workbench builds its fields from it)."""
    text = json.dumps(catalog_data(), indent=2 if args.pretty else None, ensure_ascii=False, sort_keys=True)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text + "\n")
    return 0


def cmd_family_check(args) -> int:
    """Fit checks of a family kit, without Blender."""
    from .pipeline import family_fit

    gen = make_parser().parse_args(["generate", "--family", args.family]
                                   + (["--seed", str(args.seed)] if args.seed is not None else [])
                                   + (["--recipe", args.recipe] if args.recipe else [])
                                   + (["--types", ",".join(args.types), "--count", str(args.count)]
                                      if args.types else []))
    config = build_config(gen)
    config.validate()
    specs = plan_models(config)
    print(f"family {config.family['name']}: {len(specs)} model(s), seed {config.seed}")
    for d in config.family["deviations"]:
        print(f"  deviation {d['what']}: family {d['family']} -> {d['used']} ({d['source']})")
    fit = family_fit(specs, lambda m: print("  " + m), config.family["dims"])
    if args.json:
        print(json.dumps(fit, indent=2))
    return 1 if fit["problems"] or fit["look"] else 0


def cmd_check(args) -> int:
    """Quality report: triangles vs budget, draw calls, z-fighting, colliders, distinct variants."""
    if args.export:
        return cmd_export_check(args)
    if args.family:
        return cmd_family_check(args)
    from .models import REGISTRY as registry
    from .quality import DRAW_CALL_BUDGET, DRAW_CALLS_PER_OBJECT, report
    from .seeds import model_seed

    types = model_types() if not args.types or args.types == ["all"] else args.types
    for t in types:
        if t not in registry:
            raise ValueError(f"unknown model type {t!r}; available: {', '.join(model_types())}")
    master = parse_seed(args.seed if args.seed is not None else "42")
    style = Style.from_dict({"detail": args.detail} if args.detail else {})
    rows = report(types, lambda t, i: generate_asset(t, model_seed(master, t, i), style=style), registry,
                  args.count, budget_scale=1.5 if args.detail == "high" else 1.0, palette=args.palette)
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(f"seed {master}, {args.count} variants per type{', detail ' + args.detail if args.detail else ''}"
              f"{', draw calls in palette mode' if args.palette else ''}")
        print(f"{'type':<17}{'tris':>6}{'budget':>8}{'draws':>7}  {'z-fighting':<22}{'distinct':>9}")
        for t, r in rows.items():
            zf = f"{r['z_fighting_pairs']} pair(s) in {r['z_fighting_variants']}" if r["z_fighting_pairs"] else "-"
            flag = " !" if r["errors"] else ""
            draws = f"{r['draw_calls']}{'*' if r['draw_calls_over'] else ''}"
            print(f"{t:<17}{r['triangles']:>6}{r['budget']:>8}{draws:>7}  {zf:<22}"
                  f"{r['distinct_variants']:>5}/{args.count}{flag}")
        over = [t for t, r in rows.items() if r["errors"]]
        fights = [t for t, r in rows.items() if r["z_fighting_pairs"]]
        loose = [t for t, r in rows.items() if r["uncovered_variants"]]
        print(f"\n{len(over)} type(s) over the triangle budget{': ' + ', '.join(over) if over else ''}")
        print(f"{len(fights)} type(s) with z-fighting (coplanar faces of different materials / objects)")
        print(f"{len(loose)} type(s) with solid geometry outside every collider"
              + "".join(f"\n  {t}: {r['uncovered_variants']} variant(s), e.g. {r['uncovered_example']['object']} "
                        f"{r['uncovered_example']['min']} .. {r['uncovered_example']['max']}"
                        for t, r in rows.items() if t in loose))
        print(f"* more than {DRAW_CALL_BUDGET} draw calls (materials per object, summed) and more than "
              f"{DRAW_CALLS_PER_OBJECT} per object")
    return 1 if any(r["errors"] for r in rows.values()) else 0


def cmd_export_check(args) -> int:
    """An exported models folder against the Unity import contract (cubegen/contract.py)."""
    from .contract import check_export

    if not os.path.isdir(args.export):
        raise ValueError(f"--export: {args.export!r} is not a folder")
    result = check_export(args.export)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for model, r in result.items():
            for e in r["errors"]:
                print(f"{model}: {e}")
            for o in r["open"]:
                print(f"{model}: open - {o.split(': ', 1)[-1]}")
        bad = sum(1 for r in result.values() if r["errors"])
        print(f"\n{len(result)} model(s): {bad} rejected by the Unity import, "
              f"{sum(1 for r in result.values() if r['open'])} with an open item assignment")
    return 1 if any(r["errors"] for r in result.values()) or not result else 0


def cmd_contract(args) -> int:
    """The Unity import contract as JSON (cubegen/contract.json) - for the game's importer."""
    import shutil

    from .contract import CONTRACT_FILE

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        shutil.copyfile(CONTRACT_FILE, args.out)
        print(f"contract -> {args.out}")
    else:
        with open(CONTRACT_FILE, "r", encoding="utf-8") as fh:
            sys.stdout.write(fh.read())
    return 0


def cmd_families(args) -> int:
    """Built-in families with their measures and kit."""
    from .families import DIMS, family_files, load_family

    if args.dims:
        for key, (label, members) in DIMS.items():
            print(f"{key:<15} {label:<30} {', '.join(f'{t}.{p}' for t, p in members)}")
        return 0
    for name, path in family_files().items():
        fam = load_family(path)
        kit = ", ".join(f"{t} x{len(v) if isinstance(v, list) else v}" for t, v in fam["models"].items())
        print(f"{name}: {fam.get('description', '')}")
        print("  dims:  " + ", ".join(f"{k}={v}" for k, v in fam["dims"].items()))
        print("  style: " + ", ".join(f"{k}={v}" for k, v in fam.get("style", {}).items()))
        print(f"  kit:   {kit}")
    return 0


def cmd_palettes(args) -> int:
    """Colour palettes of palette mode (``--textures palette --palette NAME``)."""
    from .families import family_files, load_family
    from .palette import COLOR_PALETTES, DEFAULT_PALETTE, palette_material, palette_names, write_swatches

    used = {}
    for name, path in family_files().items():
        fam = load_family(path)
        if fam.get("palette"):
            used.setdefault(fam["palette"], []).append(name)
    for name in palette_names():
        entry = COLOR_PALETTES.get(name, {"description": "die Farben des Spiels (M_-Materialien)"})
        families = f"  (Familie: {', '.join(used[name])})" if name in used else ""
        print(f"{name:<11} {palette_material(name):<22} {entry['description']}{families}")
    if args.swatches:
        write_swatches(args.swatches)
        print(f"swatches ({', '.join(palette_names())}, one row each) -> {args.swatches}")
    print(f"\nuse: python -m cubegen generate --palette NAME ...  (default {DEFAULT_PALETTE})")
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


def cmd_gui(args) -> int:
    from .gui import main as gui_main

    return gui_main()


# ---------------------------------------------------------------------------

def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cubegen", description="Seeded low-poly asset generator for Cube Escape.")
    parser.add_argument("--version", action="version", version=f"cubegen {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="generate a batch of assets")
    g.add_argument("--seed", help="master seed (int or any text); random if omitted")
    g.add_argument("--recipe", help="JSON recipe with seed and model counts")
    g.add_argument("--family", help="model family (name or file): shared measures, materials and kit; without "
                                    "--types/--pick the whole kit (list: python -m cubegen families)")
    g.add_argument("--match", metavar="SIDECAR",
                   help="matching addition to an existing model: take its measures and look from its "
                        "<Name>.cubegen.json, e.g. --match Gen_Pipe_003.cubegen.json --types pipe_bend")
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
    st.add_argument("--damage", choices=list(DAMAGE_STATES),
                    help="damaged: dents, knocked-off parts; destroyed: ruin (static, goes to the library); "
                         "fractured: split into fragments Fragment_<n> that Unity drops when it is destroyed")
    st.add_argument("--clutter", choices=["none", "clean", "lived-in", "chaotic"],
                    help="separate small props on explicitly supported table surfaces; deterministic by seed")
    st.add_argument("--generation", type=int, choices=list(GENERATIONS),
                    help=f"model generation (default {LATEST_GENERATION}): 1 rebuilds models exported with cubegen "
                         "0.9.0 bit for bit; 2 lifts flush details against flickering, two materials per moving part; "
                         "3 (cubegen 0.10.0) adds empties for sound and effects (Audio_*, FX_*) and colliders for "
                         "every solid piece")
    tx = g.add_argument_group("textures (optional, default: none = plain M_ materials)")
    tx.add_argument("--textures", choices=["none", "tiled", "baked", "palette"],
                    help="tiled: ImageMagick tile textures as MT_ materials; baked: + per-asset grime atlas; "
                         "palette: one material MP_Palette with a colour palette texture per model (one material per mesh; batching is a Unity release decision)")
    tx.add_argument("--texture-size", type=int, help="texture resolution in px (default 512)")
    tx.add_argument("--texture-set", help="name of a texture variant (own seed and MT_<set>_ material names)")
    tx.add_argument("--textures-dir", help="where the textures go (default <models dir>/Textures)")
    tx.add_argument("--paint", choices=paint_names(), metavar="SCHEME",
                    help=f"paint scheme ({', '.join(paint_names())}): one neutral bake per model, the scheme composed "
                         "into a baked atlas (implies --textures baked); decorative glow takes the scheme's colour")
    tx.add_argument("--bake-device", choices=["auto", "cpu", "gpu"],
                    help="Cycles device for --textures baked (default auto: GPU from 1024 px if there is one, "
                         "below that the CPU is faster); CPU and GPU differ in the noise")
    tx.add_argument("--palette", metavar="NAME", help="colour palette for palette mode (implies --textures palette): "
                                                     f"{', '.join(palette_names())} -> material MP_Palette_<Name>")
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
    g.add_argument("--set", dest="variant_set", action="store_true",
                   help="variant set (with --count): every variant keeps variant 0's outline (length, height, size "
                        "parameters ...) and differs inside - pieces to stand side by side; set_<type>.png shows them "
                        "in a row, the manifest says whether the type keeps its outline")
    g.add_argument("--jobs", type=_jobs, help="Blender processes in parallel: a number or auto (default auto: up to "
                                              "cores - 1, only as many as pay for their start)")
    g.add_argument("--force", action="store_true",
                   help="rebuild everything (default: models unchanged since the last run in --out are reused)")
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
    g.add_argument("--validate-only", action="store_true",
                   help="build and validate assets without exporting or requiring Blender")
    g.add_argument("--strict", action="store_true", help="treat validation warnings as failures before export")
    g.add_argument("--relaxed", action="store_true",
                   help="allow warnings (default; cannot be combined with --strict)")
    g.add_argument("--repair-safe", action="store_true",
                   help="remove only unreferenced empty mesh objects and record each repair in the report")
    g.add_argument("--report", metavar="FILE", help="write the build manifest or validation report as JSON")
    g.add_argument("-v", "--verbose", action="store_true", help="show Blender output")
    g.set_defaults(func=cmd_generate)

    ls = sub.add_parser("list", help="list model types and formats")
    ls.add_argument("--json", action="store_true")
    ls.set_defaults(func=cmd_list)

    pa = sub.add_parser("params", help="list the parameters of the model types")
    pa.add_argument("type", nargs="?", help="only this model type")
    pa.set_defaults(func=cmd_params)

    cg = sub.add_parser("catalog", help="types, parameter schema, style options, palettes and families as JSON "
                                        "(for game front ends)")
    cg.add_argument("--json", action="store_true", help="accepted for symmetry with list; output is always JSON")
    cg.add_argument("--pretty", action="store_true", help="indent the JSON")
    cg.add_argument("--out", help="write it to this file instead of stdout")
    cg.set_defaults(func=cmd_catalog)

    c = sub.add_parser("check", help="quality report: triangle budget, draw calls, z-fighting, colliders, "
                                     "distinct variants")
    c.add_argument("--types", type=_csv, help="comma separated model types (default: all)")
    c.add_argument("--seed", help="master seed (default 42; with --family the family's / recipe's seed)")
    c.add_argument("--count", type=int, default=10, help="variants per type (default 10)")
    c.add_argument("--detail", choices=["low", "normal", "high"], help="check this detail level")
    c.add_argument("--palette", action="store_true", help="count draw calls as with --textures palette")
    c.add_argument("--json", action="store_true")
    c.add_argument("--family", help="instead: fit checks of a family kit (sizes, joints, free passages, colliders)")
    c.add_argument("--recipe", help="with --family: a kit recipe on top of the family")
    c.add_argument("--export", metavar="DIR", help="instead: check an exported models folder against the Unity "
                                                   "import contract (every .cubegen.json, with its FBX)")
    c.set_defaults(func=cmd_check)

    ct = sub.add_parser("contract", help="the Unity import contract as JSON (shared with the game's importer)")
    ct.add_argument("--out", help="write it to this file (e.g. <Unity>/Assets/Editor/Cubegen/cubegen_contract.json)")
    ct.set_defaults(func=cmd_contract)

    f = sub.add_parser("families", help="list the built-in model families (--dims: all measures)")
    f.add_argument("--dims", action="store_true", help="list the measures and the parameters they set")
    f.set_defaults(func=cmd_families)

    pl = sub.add_parser("palettes", help="list the colour palettes of palette mode (--swatches FILE: compare them)")
    pl.add_argument("--swatches", metavar="PNG", help="write one row of colour squares per palette to this file")
    pl.set_defaults(func=cmd_palettes)

    d = sub.add_parser("doctor", help="check Blender and ImageMagick installation")
    d.add_argument("--blender")
    d.add_argument("--magick")
    d.set_defaults(func=cmd_doctor)

    ui = sub.add_parser("gui", help="open the desktop interface")
    ui.set_defaults(func=cmd_gui)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        if getattr(args, "strict", False) and getattr(args, "relaxed", False):
            raise ValueError("--strict and --relaxed cannot be used together")
        return args.func(args)
    except (BlenderError, ImageMagickError, ValueError, KeyError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
