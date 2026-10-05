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

from cubegen.geometry import box_uvs  # noqa: E402
from cubegen.materials import MATERIALS, srgb_to_linear  # noqa: E402
from cubegen.models import generate_asset  # noqa: E402


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


def _input(node, *names):
    for name in names:
        if name in node.inputs:
            return node.inputs[name]
    return None


def create_materials():
    """Same values as the game's generator - Unity remaps them by name anyway."""
    for name, (color, smoothness, metallic, emission) in MATERIALS.items():
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        linear = tuple(srgb_to_linear(c) for c in color)
        mat.diffuse_color = (*linear, 1.0)  # colour in the solid viewport / Workbench
        mat.use_backface_culling = True
        if mat.node_tree is None:
            mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF") if mat.node_tree else None
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*linear, 1.0)
            bsdf.inputs["Roughness"].default_value = 1.0 - smoothness
            bsdf.inputs["Metallic"].default_value = metallic
            if emission:
                color_in = _input(bsdf, "Emission Color", "Emission")
                strength_in = _input(bsdf, "Emission Strength")
                if color_in is not None:
                    color_in.default_value = (*linear, 1.0)
                if strength_in is not None:
                    strength_in.default_value = emission


# ---------------------------------------------------------------------------
# asset -> Blender objects
# ---------------------------------------------------------------------------

def build_asset(spec):
    asset = generate_asset(spec["type"], spec["seed"], name=spec["name"], scale=spec.get("scale", 1.0))
    collection = bpy.data.collections.new(asset.name)
    bpy.context.scene.collection.children.link(collection)
    objects = {}
    for o in asset.objects:
        if o.is_empty:
            obj = bpy.data.objects.new(o.name, None)
            obj.empty_display_type = "PLAIN_AXES"
            obj.empty_display_size = 0.2
        else:
            obj = bpy.data.objects.new(o.name, _make_mesh(f"{asset.name}.{o.name}", o))
        collection.objects.link(obj)
        if o.parent:
            parent = asset.get(o.parent)
            obj.parent = objects[o.parent]
            obj.location = tuple(o.pivot[i] - parent.pivot[i] for i in range(3))
        else:
            obj.location = o.pivot
            obj["cubegen_type"] = spec["type"]
            obj["cubegen_seed"] = str(spec["seed"])
        objects[o.name] = obj
    return asset, collection


def _make_mesh(name, asset_object):
    src = asset_object.mesh
    verts = asset_object.local_verts()
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], src.faces)
    materials = sorted(set(src.roles))
    for m in materials:
        me.materials.append(bpy.data.materials[m])
    uv_layer = me.uv_layers.new(name="UVMap")
    for fi, poly in enumerate(me.polygons):
        poly.material_index = materials.index(src.roles[fi])
        poly.use_smooth = False  # flat shading = crisp low-poly look
        uvs = box_uvs([verts[i] for i in src.faces[fi]], src.face_normal(fi))
        for loop_index, uv in zip(poly.loop_indices, uvs):
            uv_layer.data[loop_index].uv = uv
    me.validate(clean_customdata=False)
    me.update()
    return me


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

def _select(collection):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in collection.all_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = next(iter(collection.all_objects), None)


def export(collection, fmt, path):
    _select(collection)
    if fmt == "fbx":
        # identical to the game's export_fbx(): rotation 0 / scale 1 in Unity, +Z forward
        bpy.ops.export_scene.fbx(
            filepath=path, use_selection=True, object_types={"MESH", "EMPTY"}, apply_unit_scale=True,
            apply_scale_options="FBX_SCALE_ALL", axis_forward="-Z", axis_up="Y", bake_space_transform=True,
            use_mesh_modifiers=True, mesh_smooth_type="FACE", add_leaf_bones=False, bake_anim=False,
            use_custom_props=True,
        )
    elif fmt in ("glb", "gltf"):
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB" if fmt == "glb" else "GLTF_SEPARATE",
                                  use_selection=True, export_apply=True, export_extras=True, export_yup=True)
    elif fmt == "obj":
        if "obj_export" in dir(bpy.ops.wm):
            bpy.ops.wm.obj_export(filepath=path, export_selected_objects=True, export_materials=True)
        else:  # Blender < 3.2
            bpy.ops.export_scene.obj(filepath=path, use_selection=True)
    else:
        raise ValueError(f"unknown export format {fmt!r}")


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


def frame_camera(cam, collection, margin=1.12):
    """Orthographic camera from front-right-above (front = -Y), tightly framed."""
    corners = []
    for obj in collection.all_objects:
        if obj.type == "MESH":
            corners += [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    if not corners:
        return
    center = sum(corners, Vector()) / len(corners)
    radius = max((c - center).length for c in corners) or 1.0
    direction = Vector((0.85, -1.3, 0.9)).normalized()
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
    create_materials()
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
            path = os.path.join(job["models_dir"], f"{asset.name}.{fmt}")
            export(collection, fmt, path)
            files[fmt] = path
        preview = None
        if cam is not None:
            for other in collections:
                other.hide_render = True
            frame_camera(cam, collection)
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
