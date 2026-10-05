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

from cubegen.bpy_builder import build_collection, create_materials, export_collection  # noqa: E402
from cubegen.models import generate_asset  # noqa: E402
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


def build_asset(spec):
    asset = generate_asset(spec["type"], spec["seed"], name=spec["name"], scale=spec.get("scale", 1.0),
                           params=spec.get("params"), style=Style.from_dict(spec.get("style")))
    collection = bpy.data.collections.new(asset.name)
    bpy.context.scene.collection.children.link(collection)
    objects = build_collection(asset, collection,
                               tags={"cubegen_type": spec["type"], "cubegen_seed": str(spec["seed"])})
    if "Damage" in objects:  # in the game only visible while the machine is broken
        objects["Damage"].hide_render = True
    return asset, collection


# ---------------------------------------------------------------------------
# preview rendering
# ---------------------------------------------------------------------------

ENGINES = {
    "workbench": ["BLENDER_WORKBENCH"],
    "eevee": ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"],
    "cycles": ["CYCLES"],
}


def setup_render(scene, engine, size, samples):
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
        shading.color_type = "MATERIAL"
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
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.75, 0.78, 0.85, 1.0)
    bg.inputs["Strength"].default_value = 0.8
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


def run_job(job_path):
    with open(job_path, "r", encoding="utf-8") as fh:
        job = json.load(fh)
    scene = clear_scene()
    create_materials(overwrite=True)
    render = job.get("render") or {}
    cam = None
    if render.get("enabled"):
        cam = setup_render(scene, render.get("engine", "cycles"), render.get("size", 256), render.get("samples", 32))
        log(f"rendering previews with {scene.render.engine}")

    results, collections, biggest = [], [], 1.0
    total = len(job["models"])
    for i, spec in enumerate(job["models"], 1):
        t0 = time.time()
        asset, collection = build_asset(spec)
        files = {}
        for fmt in job["formats"]:
            path = os.path.join(spec.get("models_dir") or job["models_dir"], f"{asset.name}.{fmt}")
            export_collection(collection, fmt, path)
            files[fmt] = path
        preview = None
        if cam is not None:
            for other in collections:
                other.hide_render = True
            frame_camera(cam, collection, render.get("azimuth", 33.0), render.get("elevation", 31.0),
                         render.get("zoom", 1.0))
            preview = os.path.join(job["previews_dir"], f"{asset.name}.png")
            render_preview(scene, preview)
        results.append({"name": asset.name, "files": files, "preview": preview})
        log(f"({i}/{total}) {asset.name}: {asset.stats()['triangles']} tris, {time.time() - t0:.1f}s")

        # Object names are unique per .blend: rename the finished asset's parts
        # ("Body" -> "Crate_000.Body") so the next asset can use the same names.
        for obj in collection.objects:
            obj.name = f"{asset.name}.{obj.name}"
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
        json.dump({"blender": bpy.app.version_string, "engine": scene.render.engine, "models": results}, fh, indent=2)


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
