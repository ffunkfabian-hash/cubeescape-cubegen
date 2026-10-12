"""Runs *inside* Blender: builds the assets, exports them and renders previews.

Invoked by :mod:`cubegen.blender` as::

    blender -b --factory-startup --python-exit-code 3 -P cubegen/blender_worker.py -- --job job.json

Conventions are the ones of the game's ``generate_assets.py``: 1 unit = 1 m,
Z up, front towards -Y, objects only have a location (rotation 0, scale 1),
materials named like the Unity materials (``M_...``), FBX settings that give
clean transforms in Unity.
"""

import argparse
import json
import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from cubegen.bpy_builder import (build_collection, create_materials, create_palette_material,  # noqa: E402
                                 create_textured_materials, export_collection)
from cubegen.palette import material_map as palette_map  # noqa: E402
from cubegen.fbxread import check_asset  # noqa: E402
from cubegen.models import REGISTRY, generate_asset  # noqa: E402
from cubegen.params import Style  # noqa: E402


def log(msg):
    print(f"[cubegen] {msg}", flush=True)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="blender_worker")
    p.add_argument("--job")
    p.add_argument("--probe")
    p.add_argument("--engine", default="workbench")
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# scene / materials
# ---------------------------------------------------------------------------

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    return scene


def _generate(spec):
    asset = generate_asset(spec["type"], spec["seed"], name=spec["name"], scale=spec.get("scale", 1.0),
                           params=spec.get("params"), style=Style.from_dict(spec.get("style")))
    if spec.get("repair_safe"):
        asset.repair_safe()
    return asset


def build_asset(spec, material_map=None, palette=None):
    """Objects of a spec in a new collection. With ``spec["lod"]``: + the low detail build, objects
    named <part>_LOD0 / <part>_LOD1 (LOD1 hidden in previews). Returns (asset, LOD1 asset or None, collection).
    ``palette``: name of the colour palette - materials per part from the asset (palette mode)."""
    asset = _generate(spec)
    if palette:
        material_map = palette_map(asset, palette)
    collection = bpy.data.collections.new(asset.name)
    bpy.context.scene.collection.children.link(collection)
    tags = {"cubegen_type": spec["type"], "cubegen_seed": str(spec["seed"])}
    lod = _generate(dict(spec, style=dict(spec.get("style") or {}, detail="low"))) if spec.get("lod") else None
    suffix = "_LOD0" if lod else ""
    objects = build_collection(asset, collection, object_name=lambda part: part + suffix, material_map=material_map,
                               tags=tags)
    if "Damage" in objects:  # in the game only visible while the machine is broken
        objects["Damage"].hide_render = True
    if lod is not None:
        for obj in build_collection(lod, collection, object_name=lambda part: part + "_LOD1",
                                    material_map=material_map, tags=tags).values():
            obj.hide_render = True
            obj["cubegen_lod"] = 1
    return asset, lod, collection


# ---------------------------------------------------------------------------
# preview rendering
# ---------------------------------------------------------------------------

ENGINES = {
    "workbench": ["BLENDER_WORKBENCH"],
    "eevee": ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"],
    "cycles": ["CYCLES"],
}


def setup_render(scene, engine, size, samples, textured=False):
    for ident in ENGINES[engine]:
        try:
            scene.render.engine = ident  # EEVEE's identifier changed in Blender 4.2
            break
        except TypeError:
            continue
    r = scene.render
    r.resolution_x = r.resolution_y = size
    r.resolution_percentage = 100
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"  # keep material colours true

    if engine == "workbench":  # like the game's render_icons()
        shading = scene.display.shading
        shading.light = "STUDIO"
        shading.color_type = "TEXTURE" if textured else "MATERIAL"
        shading.show_cavity = True
    elif engine == "cycles":
        scene.cycles.samples = samples
        scene.cycles.use_denoising = False
        scene.cycles.device = "CPU"
        scene.cycles.max_bounces = 3
    elif engine == "eevee":
        try:
            scene.eevee.taa_render_samples = samples
        except AttributeError:
            pass

    world = bpy.data.worlds.new("cubegen_world")
    if world.node_tree is None:  # Blender < 5 (use_nodes is deprecated in 5.x, nodes always exist there)
        world.use_nodes = True
    bg = world.node_tree.nodes.get("Background") if world.node_tree else None
    if bg is not None:
        bg.inputs["Color"].default_value = (0.75, 0.78, 0.85, 1.0)
        bg.inputs["Strength"].default_value = 0.8
    world.color = (0.75, 0.78, 0.85)
    scene.world = world

    cam_data = bpy.data.cameras.new("cubegen_camera")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("cubegen_camera", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    sun_data = bpy.data.lights.new("cubegen_sun", type="SUN")
    sun_data.energy = 3.0
    sun_data.angle = math.radians(8)
    sun = bpy.data.objects.new("cubegen_sun", sun_data)
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))
    scene.collection.objects.link(sun)
    return cam


def frame_camera(cam, collection, azimuth=33.0, elevation=31.0, zoom=1.0):
    """Orthographic camera looking at the front (-Y), tightly framed.

    azimuth / elevation in degrees like the ICONS table of the game's generate_assets.py
    (positive azimuth = from the right); zoom > 1 moves closer.
    """
    corners = []
    for obj in collection.all_objects:
        if obj.type == "MESH" and not obj.hide_render:
            corners += [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    if not corners:
        return
    center = sum(corners, Vector()) / len(corners)
    radius = max((c - center).length for c in corners) or 1.0
    az, el = math.radians(azimuth), math.radians(elevation)
    direction = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    margin = 1.12 / max(zoom, 0.01)
    cam.location = center + direction * radius * 4.0
    cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()

    inv = cam.matrix_world.inverted()
    pts = [inv @ c for c in corners]
    xs, ys = [p.x for p in pts], [p.y for p in pts]
    cam.data.ortho_scale = max(max(xs) - min(xs), max(ys) - min(ys)) * margin
    shift = Vector(((max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0, 0.0))
    cam.location = cam.location + cam.matrix_world.to_3x3() @ shift
    cam.data.clip_end = radius * 10.0
    bpy.context.view_layer.update()


def render_preview(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------------
# entry points
# ---------------------------------------------------------------------------

def run_probe(path, engine):
    scene = clear_scene()
    setup_render(scene, engine, 16, 1)
    render_preview(scene, path)


def layout_overview(collections, spacing):
    """Lay the assets out in a grid so the .blend is easy to browse (after exporting!)."""
    for i, collection in enumerate(collections):
        offset = Vector(((i % 10) * spacing, (i // 10) * spacing, 0.0))
        for obj in collection.objects:
            if obj.parent is None:
                obj.location += offset


def _set_aside(collection, asset):
    """Object names are unique per .blend: rename the finished asset's parts ("Body" -> "Crate_000.Body")
    so the next asset can use the same names. The overview shows LOD0; LOD1 stays in the file, hidden."""
    for obj in collection.objects:
        obj.name = f"{asset.name}.{obj.name}"
        if obj.get("cubegen_lod"):
            obj.hide_set(True)


def _claim(queue, name):
    """Work package: the first process that creates ``<queue>/<name>.claim`` builds the model."""
    try:
        os.close(os.open(os.path.join(queue, f"{name}.claim"), os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        return True
    except FileExistsError:
        return False


def wait_ready(path, timeout=1800.0):
    """The host builds the tile textures while this process starts: wait for its ``ok`` (or its error)."""
    end = time.time() + timeout
    while not os.path.isfile(path):
        if time.time() > end:
            raise RuntimeError(f"textures not ready after {timeout:.0f} s")
        time.sleep(0.02)
    with open(path, "r", encoding="utf-8") as fh:
        state = fh.read().strip()
    if state != "ok":
        raise RuntimeError(f"texture build failed: {state}")


def run_job(job_path):
    started = time.time()
    with open(job_path, "r", encoding="utf-8") as fh:
        job = json.load(fh)
    scene = clear_scene()
    create_materials(overwrite=True)
    textures = job.get("textures") or {}
    material_map = {plain: info["name"] for plain, info in textures.items()}
    palette = job.get("palette")
    if palette:
        create_palette_material(palette)
    render = job.get("render") or {}
    cam = None
    if render.get("enabled"):
        cam = setup_render(scene, render.get("engine", "cycles"), render.get("size", 256), render.get("samples", 32),
                           textured=bool(job.get("textures") or palette))
        log(f"rendering previews with {scene.render.engine}")
    if textures:
        if job.get("textures_ready"):
            waited = time.time()
            wait_ready(job["textures_ready"])
            if time.time() - waited > 0.05:
                log(f"waited {time.time() - waited:.1f}s for the textures")
        create_textured_materials(textures)

    results, collections, biggest = [], [], 1.0
    queue = job.get("queue_dir")  # parallel run: the models are work packages, every process claims the next free one
    total = len(job["models"])
    for i, spec in enumerate(job["models"], 1):
        if queue and not spec.get("skip") and not _claim(queue, spec["name"]):
            continue
        t0 = time.time()
        timings = {}
        asset, lod, collection = build_asset(spec, material_map, palette=palette and palette["palette"])
        timings["build"] = time.time() - t0
        if spec.get("skip"):  # unchanged / exported by another process: only part of the overview .blend
            _set_aside(collection, asset)
            collections.append(collection)
            biggest = max(biggest, *asset.stats()["dimensions_m"])
            continue
        baked = None
        if job.get("texture_mode") == "baked" and textures:
            from cubegen.bake import bake_asset

            t = time.time()
            baked = bake_asset(collection, asset.name, job["textures_dir"], job.get("texture_size", 512),
                               job["magick"], seed=spec["seed"], device=job.get("bake_device", "cpu"))
            timings["bake"] = time.time() - t
        t = time.time()
        files = {}
        for fmt in job["formats"]:
            path = os.path.join(spec.get("models_dir") or job["models_dir"], f"{asset.name}.{fmt}")
            export_collection(collection, fmt, path)
            if fmt == "fbx":  # the FBX must say exactly what <Name>.cubegen.json says (parents, pivots, no rotation)
                problems = check_asset(path, asset, suffix="_LOD0" if lod else "")
                if lod is not None:
                    problems += check_asset(path, lod, suffix="_LOD1")
                if problems:
                    raise RuntimeError(f"{path} does not match its rig data:\n  " + "\n  ".join(problems))
            files[fmt] = path
        timings["export"] = time.time() - t
        preview = None
        if cam is not None:
            t = time.time()
            for other in collections:
                other.hide_render = True
            elevation = render.get("elevation", 31.0)
            if REGISTRY[spec["type"]].view == "below":  # ceiling pieces: look up at them
                elevation = -abs(elevation)
            frame_camera(cam, collection, render.get("azimuth", 33.0), elevation, render.get("zoom", 1.0))
            preview = os.path.join(job["previews_dir"], f"{asset.name}.png")
            render_preview(scene, preview)
            timings["render"] = time.time() - t
        entry = {"name": asset.name, "files": files, "preview": preview,
                 "timings": {k: round(v, 3) for k, v in timings.items()}}
        if baked:
            entry.update({"baked": baked["maps"], "baked_material": baked["material"], "bake_device": baked["device"]})
        results.append(entry)
        counter = "" if queue else f"({i}/{total}) "
        log(f"{counter}{asset.name}: {asset.stats()['triangles']} tris, {time.time() - t0:.1f}s")

        _set_aside(collection, asset)
        collections.append(collection)
        biggest = max(biggest, *asset.stats()["dimensions_m"])

    if job.get("blend"):
        for collection in collections:
            collection.hide_render = False
        if cam is not None:
            bpy.data.objects.remove(cam, do_unlink=True)
        layout_overview(collections, max(7.0, biggest + 2.0))
        bpy.ops.wm.save_as_mainfile(filepath=job["blend"])
        log(f"saved {job['blend']}")

    with open(job["result_path"], "w", encoding="utf-8") as fh:
        json.dump({"blender": bpy.app.version_string, "engine": scene.render.engine, "models": results,
                   "worker": {"pid": os.getpid(), "models": len(results), "seconds": round(time.time() - started, 2),
                              "blend": bool(job.get("blend"))}}, fh, indent=2)


def main():
    args = parse_args()
    if args.probe:
        run_probe(args.probe, args.engine)
    elif args.job:
        run_job(args.job)
    else:
        raise SystemExit("blender_worker: pass --job FILE or --probe FILE")


if __name__ == "__main__":
    main()
