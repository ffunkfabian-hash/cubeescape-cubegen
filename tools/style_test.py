"""Style test for paint schemes (experimental, 0.17.0 "Prism"): the robot generator's skin principle on environment
models - one neutral bake per model, every paint scheme composed from it.

    python3 tools/style_test.py                                   # wall, platform, pillar, crate x industrial, crystal
    python3 tools/style_test.py --models wall,door --paints industrial --size 512 --out /tmp/st
    python3 tools/style_test.py --concept concept.png              # + crops of a concept sheet as reference column

Writes per model the neutral maps (<Name>_W<n>/AO/Edge/Up.png), per scheme the composed maps
(<Name>_<paint>_Albedo/Emission.png), previews (EEVEE) and ``style_test.png``: rows = today's game colours and every
scheme, columns = models. Times per step in ``style_test.json``. Inside Blender (``-P``) the same file is the worker.
"""

import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# crops of the user's concept sheet (1536 x 1024, "Cube Escape - Umgebungs Konzepte"): x, y, w, h per scheme
CONCEPT_CROPS = {"industrial": (14, 108, 122, 200), "crystal": (364, 108, 112, 200)}


def worker(job_path):
    import bpy  # noqa: F401 - only inside Blender

    from cubegen import blender_worker as bw
    from cubegen import stylebake
    from cubegen.paint import PAINTS

    with open(job_path, "r", encoding="utf-8") as fh:
        job = json.load(fh)
    scene = bw.clear_scene()
    bw.create_materials(overwrite=True)
    textures = job.get("textures") or {}
    material_map = {plain: info["name"] for plain, info in textures.items()}
    base_of = {info["name"]: plain for plain, info in textures.items()}
    if textures:
        bw.create_textured_materials(textures)
    glow_materials = {g: bw.bpy.data.materials.get("M_Glow" + g.capitalize()) for g in ("cyan", "orange", "red")}
    cam = bw.setup_render(scene, "eevee", job["render_size"], job["samples"])
    out = job["out"]
    timings, done = {}, []
    for spec in job["models"]:
        t0 = time.time()
        asset, _, collection = bw.build_asset(spec)  # game materials: today's look
        for other in done:
            other.hide_render = True
        bw.frame_camera(cam, collection, 33.0, 24.0, 1.0)
        bw.render_preview(scene, os.path.join(out, f"{asset.name}_today.png"))
        collection.hide_render = True
        textured = bw.build_asset(dict(spec, name=spec["name"]), material_map)[2] if textures else collection
        textured.hide_render = False
        if textures:
            bw.frame_camera(cam, textured, 33.0, 24.0, 1.0)
            bw.render_preview(scene, os.path.join(out, f"{asset.name}_tiled.png"))
        today_collection, collection = collection, textured
        t1 = time.time()
        maps = stylebake.bake_masks(collection, asset.name, out, job["size"], samples=job["bake_samples"],
                                    device=job["device"], base_of=base_of)
        t2 = time.time()
        originals = {o: [s.material for s in o.material_slots] for o in collection.all_objects if o.type == "MESH"}
        compose_s = render_s = 0.0
        for paint in job["paints"]:
            scheme = PAINTS[paint]
            t = time.time()
            painted = stylebake.compose_paint(maps, asset.name, paint, out, spec["seed"])
            compose_s += time.time() - t
            stylebake.apply_paint(collection, maps, paint, painted, scheme["roughness"], tuple(base_of))
            for o in originals:  # decorative glow takes the scheme's colour; status red stays red
                for slot in o.material_slots:
                    if slot.material and slot.material.name in ("M_GlowCyan", "M_GlowOrange"):
                        slot.material = glow_materials[scheme["glow"]]
            t = time.time()
            bw.frame_camera(cam, collection, 33.0, 24.0, 1.0)
            bw.render_preview(scene, os.path.join(out, f"{asset.name}_{paint}.png"))
            render_s += time.time() - t
            for o, mats in originals.items():
                for slot, mat in zip(o.material_slots, mats):
                    slot.material = mat
        timings[asset.name] = {"today_render": round(t1 - t0, 2), "bake": round(t2 - t1, 2),
                               "compose": round(compose_s, 2), "render": round(render_s, 2),
                               "device": maps["device"], "weight_maps": len(maps["weights"])}
        print(f"[style] {asset.name}: bake {t2 - t1:.1f}s ({maps['device']}, {len(maps['weights'])} weight map(s)), "
              f"{len(job['paints'])} scheme(s) composed in {compose_s:.1f}s", flush=True)
        done += [today_collection] + ([collection] if collection is not today_collection else [])
    with open(os.path.join(out, "worker.json"), "w", encoding="utf-8") as fh:
        json.dump(timings, fh, indent=2)


def host(argv=None) -> int:
    from cubegen.blender import find_blender
    from cubegen.cli import build_config, make_parser
    from cubegen.imagemagick import ImageMagick
    from cubegen.paint import PAINTS, check_paint
    from cubegen.pipeline import plan_models

    p = argparse.ArgumentParser(description="style test: neutral bake once, paint schemes composed from it")
    p.add_argument("--models", default="wall,platform,pillar,crate", help="types (variant 0 of each)")
    p.add_argument("--paints", default="industrial,crystal")
    p.add_argument("--seed", default="42")
    p.add_argument("--size", type=int, default=1024, help="atlas size in px")
    p.add_argument("--render-size", type=int, default=512)
    p.add_argument("--samples", type=int, default=32, help="EEVEE samples of the previews")
    p.add_argument("--bake-samples", type=int, default=16)
    p.add_argument("--device", default="auto", choices=["auto", "cpu", "gpu"])
    p.add_argument("--concept", help="concept sheet (1536 x 1024) for a reference column")
    p.add_argument("--no-tiles", action="store_true", help="bake without the tile textures' surface detail")
    p.add_argument("--out", default=os.path.join(ROOT, "output", "style_test"))
    args = p.parse_args(argv)
    paints = [check_paint(n) for n in args.paints.split(",") if n]
    types = [t for t in args.models.split(",") if t]
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    config = build_config(make_parser().parse_args(["generate", "--seed", args.seed, "--pick",
                                                    ",".join(f"{t}:0" for t in types), "--no-blender", "--out", out]))
    specs = plan_models(config, lambda m: None)
    textures = {}
    if not args.no_tiles:  # the tile textures give the neutral bake its surface detail (grooves, rivets, scratches)
        from cubegen.textures import build_texture_set

        textures = build_texture_set(ImageMagick(), os.path.join(out, "Textures"), 512, log=lambda m: None)
    job = {"models": specs, "paints": paints, "out": out, "size": args.size, "render_size": args.render_size,
           "samples": args.samples, "bake_samples": args.bake_samples, "device": args.device, "textures": textures}
    job_path = os.path.join(out, "job.json")
    with open(job_path, "w", encoding="utf-8") as fh:
        json.dump(job, fh, indent=2, default=str)
    blender = find_blender()
    if not blender:
        raise SystemExit("Blender not found")
    start = time.time()
    run = subprocess.run([blender, "-b", "--factory-startup", "--python-exit-code", "3", "-P", os.path.abspath(__file__),
                          "--", "--worker", job_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in run.stdout.splitlines():
        if line.startswith("[style]"):
            print(line)
    if run.returncode != 0:
        print(run.stdout[-3000:])
        return run.returncode
    blender_s = time.time() - start

    # comparison sheet: rows = today + schemes, columns = models (+ concept crop)
    im = ImageMagick().single_threaded()
    cell = 300
    names = [s["name"] for s in specs]
    rows = [("today", "Heute: Spielfarben")] + ([("tiled", "Heute: Kacheln")] if not args.no_tiles else []) \
        + [(n, PAINTS[n]["label"]) for n in paints]
    row_files = []
    for key, label in rows:
        tiles = []
        for name in names:
            tiles += ["(", os.path.join(out, f"{name}_{key}.png"), "-background", "none", "-resize", f"{cell}x{cell}",
                      "-gravity", "center", "-extent", f"{cell}x{cell}", ")"]
        if args.concept:
            crop = CONCEPT_CROPS.get(key)
            if crop:
                x, y, w, h = crop
                tiles += ["(", args.concept, "-gravity", "northwest", "-crop", f"{w}x{h}+{x}+{y}", "+repage", "-resize", f"{cell}x{cell}",
                          "-gravity", "center", "-background", "#1e1e24", "-extent", f"{cell}x{cell}", ")"]
            else:
                tiles += ["(", "-size", f"{cell}x{cell}", "xc:#1e1e24", ")"]
        row = os.path.join(out, f".row_{key}.png")
        im.run(tiles + ["-background", "#1e1e24", "+append", "(", "-size", f"{220}x{cell}", "xc:#1e1e24", "-fill",
                        "#e8e8e8", "-pointsize", "22", "-gravity", "west", "-annotate", "+16+0", label, ")",
                        "+swap", "+append", row])
        row_files.append(row)
    header = ["-size", f"{220}x40", "xc:#1e1e24"]
    for name in names + (["Konzept"] if args.concept else []):
        header += ["(", "-size", f"{cell}x40", "xc:#1e1e24", "-fill", "#9aa0a8", "-pointsize", "18", "-gravity",
                   "center", "-annotate", "+0+0", name, ")"]
    head = os.path.join(out, ".row_header.png")
    im.run(header + ["+append", head])
    sheet = os.path.join(out, "style_test.png")
    im.run([head] + row_files + ["-background", "#1e1e24", "-append", sheet])
    for f in row_files + [head]:
        os.remove(f)
    with open(os.path.join(out, "worker.json"), "r", encoding="utf-8") as fh:
        per_model = json.load(fh)
    with open(os.path.join(out, "style_test.json"), "w", encoding="utf-8") as fh:
        json.dump({"paints": paints, "models": names, "size": args.size, "blender_seconds": round(blender_s, 1),
                   "per_model": per_model}, fh, indent=2)
    print(f"style test: {len(names)} model(s) x {len(paints)} scheme(s) in {blender_s:.0f} s -> {sheet}")
    return 0


if __name__ == "__main__":
    if "--worker" in sys.argv:
        worker(sys.argv[sys.argv.index("--worker") + 1])
    else:
        sys.exit(host())
