#!/usr/bin/env python3
"""Reference maps for Cube Escape's paint shader: every scheme composed from a run's neutral maps (no Blender).

    python3 tools/paint_reference.py output/seed_19                       # every built-in scheme (+ the run's own)
    python3 tools/paint_reference.py output/seed_19 --paints crystal,dark --out /tmp/ref
    python3 tools/paint_reference.py output/seed_19 --check               # Python = Blender for the run's scheme

A ``generate --paint`` run writes per model the packed neutral maps ``MTN_<Model>_W0/W1[/W2]/Fields/Normal.png``
(manifest ``models[].neutral_maps``, sidecar ``textures.neutral`` from contract version 3). ``paint.compose`` on
their 8-bit values is the reference a shader has to reproduce (Cube Escape: ``SurfaceRenderTests``, recipe PAINT).
This tool writes, per scheme, the finished maps a real ``--paint <scheme>`` run would write - ``MTP_<Model>_<scheme>_
Albedo/Roughness/MetallicSmoothness[/Emission].png`` (Emission only for schemes with glowing edges) - into
``<out>/<scheme>/`` and an index ``<out>/reference.json`` (models, layout, neutral maps, scheme data, tolerance).

``--check`` composes the run's own scheme and compares it with the ``MTP_`` maps Blender saved in that run: they
must be identical (exit code 1 otherwise). Needs numpy - Blender's Python has it:
``blender -b --python tools/paint_reference.py -- <run> …``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from cubegen import __version__  # noqa: E402
from cubegen import neutral  # noqa: E402
from cubegen.paint import BUILTIN_PAINTS, PAINTS, register_scheme, scheme_glows  # noqa: E402

#: what a shader may differ by (8-bit values) - a suggestion for Cube Escape's comparison, not a rule of the reference:
#: the reference is exact; GPU float maths, hardware sRGB and 8-bit render targets differ by a step here and there
TOLERANCE = {"max_abs": 3, "mean_abs": 0.5, "note": "per channel 0..255, Albedo/Emission compared in sRGB"}
MAPS = ("Albedo", "Roughness", "MetallicSmoothness", "Emission")


def load_manifest(run: str) -> Dict:
    with open(os.path.join(run, "manifest.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def models_with_maps(manifest: Dict) -> List[Dict]:
    return [m for m in manifest.get("models", []) if m.get("neutral_maps") and m.get("weight_layout")]


def schemes(manifest: Dict, wanted: Optional[List[str]] = None) -> List[str]:
    """Built-in schemes plus the run's own custom one (registered from ``config.paint_scheme``)."""
    config = manifest.get("config") or {}
    own = config.get("paint")
    if own and own not in BUILTIN_PAINTS and config.get("paint_scheme"):
        if own not in PAINTS:
            register_scheme(own, config["paint_scheme"])
    names = sorted(BUILTIN_PAINTS) + ([own] if own and own not in BUILTIN_PAINTS else [])
    if wanted:
        unknown = [w for w in wanted if w not in names]
        if unknown:
            raise ValueError(f"unknown schemes {', '.join(unknown)} (known: {', '.join(names)})")
        names = [n for n in names if n in wanted]
    return names


def compose_model(run: str, entry: Dict, paint: str) -> Dict:
    """The finished maps (uint8, bottom-up) of ``paint`` for one manifest model."""
    paths = {k: os.path.join(run, v) for k, v in entry["neutral_maps"].items()}
    result = neutral.compose_packed(neutral.read_neutral(paths), entry["weight_layout"], paint)
    maps = neutral.final_maps(result)
    if not scheme_glows(paint):
        maps.pop("Emission")
    return maps


def write_reference(run: str, out: str, paints: Optional[List[str]] = None, log=print) -> Dict:
    manifest = load_manifest(run)
    models = models_with_maps(manifest)
    if not models:
        raise ValueError(f"{run}: no model with neutral maps (a generate --paint run of cubegen 0.24 or newer)")
    names = schemes(manifest, paints)
    index = {"cubegen": __version__, "run": os.path.abspath(run), "run_paint": (manifest.get("config") or {}).get(
        "paint"), "tolerance": TOLERANCE, "schemes": {n: PAINTS[n] for n in names}, "models": []}
    for entry in models:
        row = {"name": entry["name"], "type": entry["type"], "weight_layout": entry["weight_layout"],
               "neutral": {k: os.path.abspath(os.path.join(run, v)) for k, v in entry["neutral_maps"].items()},
               "references": {}}
        for paint in names:
            folder = os.path.join(out, paint)
            os.makedirs(folder, exist_ok=True)
            files = {}
            for key, image in compose_model(run, entry, paint).items():
                files[key] = neutral.write_png(os.path.join(folder, f"MTP_{entry['name']}_{paint}_{key}.png"), image)
            row["references"][paint] = {k: os.path.relpath(v, out) for k, v in files.items()}
        index["models"].append(row)
    with open(os.path.join(out, "reference.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2, ensure_ascii=False)
    log(f"paint reference: {len(models)} model(s) x {len(names)} scheme(s) -> {out}")
    return index


def check_run(run: str, log=print) -> List[str]:
    """The run's own scheme composed here against the ``MTP_`` maps Blender saved: [] when identical."""
    manifest = load_manifest(run)
    paint = (manifest.get("config") or {}).get("paint")
    schemes(manifest)  # registers a custom scheme
    problems = []
    for entry in models_with_maps(manifest):
        mine = compose_model(run, entry, paint)
        baked = entry.get("baked") or {}
        for key, image in mine.items():
            if key not in baked:
                problems.append(f"{entry['name']}: {key} missing in the run")
                continue
            theirs = neutral.read_png(os.path.join(run, baked[key]))
            if theirs.shape != image.shape:
                problems.append(f"{entry['name']}: {key} shape {theirs.shape} != {image.shape}")
                continue
            worst, share = neutral.max_difference(theirs, image)
            if worst:
                problems.append(f"{entry['name']}: {key} differs by up to {worst} at {share:.2%} of the pixels")
        log(f"{entry['name']}: {paint} {'identical' if not problems else 'DIFFERS'}")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run", help="output folder of a generate --paint run (with manifest.json)")
    ap.add_argument("--paints", help="schemes, comma separated (default: every built-in one + the run's own)")
    ap.add_argument("--out", help="where the reference goes (default <run>/paint_reference)")
    ap.add_argument("--check", action="store_true", help="only compare the run's own scheme with its MTP_ maps")
    if argv is None and "--" in sys.argv:  # inside Blender: blender -b --python tools/paint_reference.py -- <run>
        argv = sys.argv[sys.argv.index("--") + 1:]
    args = ap.parse_args(argv)
    try:
        if args.check:
            problems = check_run(args.run)
            for p in problems:
                print("  " + p)
            return 1 if problems else 0
        write_reference(args.run, args.out or os.path.join(args.run, "paint_reference"),
                        args.paints.split(",") if args.paints else None)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
