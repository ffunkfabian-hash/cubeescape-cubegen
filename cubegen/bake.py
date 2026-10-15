"""Per-asset baked textures (``--textures baked``) - runs inside Blender.

For one asset (a collection):

1. a shared atlas UV map for all its mesh objects (Smart UV Project)
2. Cycles bakes of the tiled ``MT_`` materials into that atlas: colour, tangent normals,
   ambient occlusion and roughness + metallic in one pass (red / green of a temporary
   emission, like the robot generator's surface bake) - into one
   temporary joined copy of the parts (Cycles bakes every selected object in a session
   of its own; on Metal each session costs a GPU sync, on the CPU it is slower too)
3. ImageMagick puts grime into crevices (AO) with a little noise breakup
4. one material ``MTA_<Asset>`` replaces all non-glow materials; the atlas UV
   becomes the only UV map (Unity's UV0)

Glow / status materials, crystal and glass keep their plain ``M_`` material -
the game's scripts swap them at runtime.
"""

import math
import os
import subprocess

import bpy

from .imagemagick import REPRODUCIBLE, _png_output, strip_png_dates
from .materials import KEEP_OWN

KEEP = set(KEEP_OWN)  # glow, crystal, glass and (0.24) the names split off M_Crystal keep their own material
BAKE_UV = "BakeUV"
DEVICES = ("auto", "cpu", "gpu")
GPU_FROM = 1024  # auto: GPU from this atlas size; measured 0.15.0 (M5, Metal): 512 px CPU faster, 1024 px GPU ~1.8x
GPU_TYPES = ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI")


def use_device(scene, requested, size):
    """Point Cycles at the CPU or the GPU; returns what is used ("CPU" or e.g. "METAL").

    ``auto``: GPU from ``GPU_FROM`` px when there is one. GPU only (the CPU devices stay off) so a run gives the same
    pixels every time; CPU and GPU results differ in the noise."""
    scene.cycles.device = "CPU"
    if requested == "cpu" or (requested == "auto" and size < GPU_FROM):
        return "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in GPU_TYPES:
            try:
                prefs.compute_device_type = kind
            except TypeError:
                continue
            prefs.get_devices()
            if any(d.type != "CPU" for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type != "CPU"
                scene.cycles.device = "GPU"
                return kind
    except Exception:  # noqa: BLE001 - the GPU is optional
        pass
    return "CPU"


def _mesh_objects(collection):
    return [o for o in collection.all_objects if o.type == "MESH"
            and any(s.material and s.material.name not in KEEP for s in o.material_slots)]


def _select(objects):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


def _atlas_uvs(objects):
    for o in objects:
        uv = o.data.uv_layers.get(BAKE_UV) or o.data.uv_layers.new(name=BAKE_UV)
        o.data.uv_layers.active = uv  # bake target; "UVMap" stays active for rendering (tiled textures)
    _select(objects)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")


UV_FORMAT = 1  # file of a bake's atlas UVs (0.26.0, shared cache): {"format", "objects": {name: base64 float32}}


def read_uvs(objects):
    """The atlas UVs (``BakeUV``) of ``objects`` as JSON-ready data: per object its loops' (u, v) as float32 bytes
    (base64) - stored with a cached bake, so a reused bake always lies on exactly its UVs (Roboter-Generator 1.8:
    Blender's UV packing can differ between runs; Cubegen's is stable, test_release_0150 - the cache does not rely
    on it)."""
    import array
    import base64

    found = {}
    for o in objects:
        layer = o.data.uv_layers[BAKE_UV]
        values = array.array("f", [0.0]) * (2 * len(o.data.loops))
        layer.data.foreach_get("uv", values)
        found[o.name] = base64.b64encode(values.tobytes()).decode("ascii")
    return {"format": UV_FORMAT, "objects": found}


def apply_uvs(objects, data):
    """Give ``objects`` the atlas UVs ``read_uvs`` recorded (instead of Smart UV Project); False - nothing changed -
    when the objects or their loop counts are not the recorded ones."""
    import array
    import base64

    stored = data.get("objects") if isinstance(data, dict) and data.get("format") == UV_FORMAT else None
    if not stored or set(stored) != {o.name for o in objects}:
        return False
    values = {}
    for o in objects:
        values[o.name] = array.array("f")
        values[o.name].frombytes(base64.b64decode(stored[o.name]))
        if len(values[o.name]) != 2 * len(o.data.loops):
            return False
    for o in objects:
        layer = o.data.uv_layers.get(BAKE_UV) or o.data.uv_layers.new(name=BAKE_UV)
        o.data.uv_layers.active = layer
        layer.data.foreach_set("uv", values[o.name])
    # the same mode switch and selection as _atlas_uvs: edit mode writes the mesh back once (the export must not see
    # a difference)
    _select(objects)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    return True


def bake_settings(scene, samples, device, size):
    """Cycles settings a bake leaves behind (they stay for the rest of the Blender process - a Cycles preview after
    a bake renders with them): a reused bake sets them too, so what follows is the same as after a real bake."""
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    return use_device(scene, device, size)


def _joined_copy(objects):
    """One temporary object with the parts' meshes in world space (same atlas UVs, same material slots)."""
    scene = bpy.context.scene
    copies = []
    for o in objects:
        copy = o.copy()
        copy.data = o.data.copy()
        scene.collection.objects.link(copy)
        world = o.matrix_world.copy()
        copy.parent = None
        copy.data.transform(world)
        copy.matrix_world.identity()
        copies.append(copy)
    _select(copies)
    if len(copies) > 1:
        bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.data.uv_layers.active = joined.data.uv_layers[BAKE_UV]
    joined.hide_render = False
    return joined


def _remove(obj):
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh is not None and mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def _materials(objects):
    mats = []
    for o in objects:
        for slot in o.material_slots:
            if slot.material and slot.material.name not in KEEP and slot.material not in mats:
                mats.append(slot.material)
    return mats


def _bake(objects, materials, image, bake_type, **kwargs):
    """Bake into ``image`` through a temporary active image node in every material."""
    temp = []
    for mat in materials:
        node = mat.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        mat.node_tree.nodes.active = node
        temp.append((mat, node))
    _select(objects)
    try:
        bpy.ops.object.bake(type=bake_type, margin=4, use_clear=True, **kwargs)
    finally:
        for mat, node in temp:
            mat.node_tree.nodes.remove(node)


def _combine_node(nodes):
    try:
        return nodes.new("ShaderNodeCombineColor")
    except RuntimeError:  # Blender < 3.3
        return nodes.new("ShaderNodeCombineRGB")


def _feed(links, source, target):
    """``target`` gets what drives ``source``: its link (e.g. a roughness map) or its value."""
    if source.is_linked:
        links.new(source.links[0].from_socket, target)
    else:
        target.default_value = source.default_value


def _surface_bake(objects, materials, image):
    """Roughness (red) and metallic (green) in one pass: both routed through a temporary emission shader.
    Same values as the ROUGHNESS pass plus a metallic emission bake (0.15.0), one Cycles pass less."""
    restore = []
    for mat in materials:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        out = next((n for n in nodes if n.type == "OUTPUT_MATERIAL"), None)
        bsdf = nodes.get("Principled BSDF")
        if out is None or bsdf is None:
            continue
        old = [l.from_socket for l in out.inputs["Surface"].links]
        combine = _combine_node(nodes)
        _feed(links, bsdf.inputs["Roughness"], combine.inputs[0])
        _feed(links, bsdf.inputs["Metallic"], combine.inputs[1])
        combine.inputs[2].default_value = 0.0
        emit = nodes.new("ShaderNodeEmission")
        links.new(combine.outputs[0], emit.inputs["Color"])
        links.new(emit.outputs["Emission"], out.inputs["Surface"])
        restore.append((mat, out, (emit, combine), old))
    try:
        _bake(objects, materials, image, "EMIT")
    finally:
        for mat, out, temp, old in restore:
            for node in temp:
                mat.node_tree.nodes.remove(node)
            for socket in old:
                mat.node_tree.links.new(socket, out.inputs["Surface"])


def _image(name, size, non_color):
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, size, size, alpha=False)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    return img


def _save(img, path):
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()


def _magick(cmd, args):
    proc = subprocess.run(list(cmd) + list(REPRODUCIBLE) + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ImageMagick failed: {proc.stderr.strip()}")
    target = _png_output(args[-1]) if args else None  # ImageMagick 6 ignores the define (0.19.1)
    if target and os.path.isfile(target):
        strip_png_dates(target)


def bake_asset(collection, asset_name, out_dir, size, magick_cmd, samples=16, seed=0, device="cpu", cached=None):
    """Bake one asset; returns ``{"material": name, "maps": {kind: path}, "device": "CPU" | "METAL" ..., "uvs"}``
    or None (nothing to bake). ``device``: auto | cpu | gpu (see :func:`use_device`). ``cached`` (0.26.0, shared
    cache): ``{"uvs", "maps", "device"}`` of an earlier bake with exactly these inputs - its maps are already in
    ``out_dir``, the atlas UVs are applied instead of baking; ignored when they do not fit the objects."""
    objects = _mesh_objects(collection)
    if not objects:
        return None
    if cached and apply_uvs(objects, cached["uvs"]):
        bake_settings(bpy.context.scene, samples, device, size)
        return _finish(objects, f"MTA_{asset_name}", dict(cached["maps"]), cached["device"], None)
    scene = bpy.context.scene
    engine = scene.render.engine
    scene.render.engine = "CYCLES"
    used = bake_settings(scene, samples, device, size)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, f"{asset_name}_Bake")
    paths = {k: f"{base}{k}.png" for k in ("Color", "AO", "Surface")}
    final = {k: os.path.join(out_dir, f"MTA_{asset_name}_{k}.png")
             for k in ("Albedo", "Normal", "Roughness", "MetallicSmoothness")}
    # only this asset may be visible while baking (other assets sit at the origin too and would shade the AO);
    # hidden parts like "Damage" must render or Blender refuses to bake them
    hidden_colls = {c: c.hide_render for c in bpy.data.collections if c != collection}
    hidden_objs = {o: o.hide_render for o in collection.all_objects}
    for c in hidden_colls:
        c.hide_render = True
    for o in hidden_objs:
        o.hide_render = False
    target = None
    try:
        _atlas_uvs(objects)
        materials = _materials(objects)
        images = {}
        for kind, non_color in (("Color", False), ("AO", True), ("Surface", True), ("Normal", True)):
            images[kind] = _image(f"{asset_name}_{kind}", size, non_color)
        target = _joined_copy(objects)
        for o in objects:  # the copy stands in for them (restored below); they'd double the AO occluders
            o.hide_render = True
        bake = [target]
        _bake(bake, materials, images["Color"], "DIFFUSE", pass_filter={"COLOR"})
        _bake(bake, materials, images["AO"], "AO")
        _bake(bake, materials, images["Normal"], "NORMAL", normal_space="TANGENT")
        _surface_bake(bake, materials, images["Surface"])
        for kind in ("Color", "AO", "Surface"):
            _save(images[kind], paths[kind])
        _save(images["Normal"], final["Normal"])
    finally:
        if target is not None:
            _remove(target)
        scene.render.engine = engine
        for c, state in hidden_colls.items():
            c.hide_render = state
        for o, state in hidden_objs.items():
            o.hide_render = state

    # grime in crevices: colour x AO (softened) x noise breakup; crevices also get rougher
    noise = ["(", "-size", f"{size}x{size}", "xc:gray50", "-seed", str(seed % 2**30 + 1), "+noise", "Random",
             "-channel", "G", "-separate", "+channel", "-blur", f"0x{size / 256:.2f}", "-auto-level",
             "+level", "82%,100%", ")"]
    _magick(magick_cmd, [paths["Color"], "(", paths["AO"], "-colorspace", "gray", "-evaluate", "pow", "1.6",
                         "+level", "30%,100%", ")", "-compose", "Multiply", "-composite"] + noise +
            ["-compose", "Multiply", "-composite", "-depth", "8", f"PNG24:{final['Albedo']}"])
    roughness = [paths["Surface"], "-channel", "R", "-separate", "+channel"]
    metallic = [paths["Surface"], "-channel", "G", "-separate", "+channel"]
    _magick(magick_cmd, roughness + ["-colorspace", "gray", "(", paths["AO"], "-colorspace", "gray",
                         "-negate", "-evaluate", "multiply", "0.25", ")", "-compose", "Plus", "-composite",
                         f"PNG8:{final['Roughness']}"])
    _magick(magick_cmd, metallic + ["-colorspace", "gray", "(", final["Roughness"], "-negate", ")",
                         "-alpha", "off", "-compose", "CopyOpacity", "-composite",
                         f"PNG32:{final['MetallicSmoothness']}"])
    for p in paths.values():
        os.remove(p)
    for img in images.values():
        bpy.data.images.remove(img)
    return _finish(objects, f"MTA_{asset_name}", final, used, read_uvs(objects))


def _finish(objects, name, final, used, uvs):
    """One material ``name`` on the maps for every non-glow slot; the atlas becomes the only UV map (UV0 in Unity)."""
    material = _baked_material(name, final)
    for o in objects:
        for slot in o.material_slots:
            if slot.material and slot.material.name not in KEEP:
                slot.material = material
        tiled = o.data.uv_layers.get("UVMap")
        if tiled is not None:
            o.data.uv_layers.remove(tiled)
        o.data.uv_layers[BAKE_UV].name = "UVMap"
    return {"material": material.name, "maps": final, "device": used, "uvs": uvs}


def _baked_material(name, maps):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    mat.use_backface_culling = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")

    def image_node(path, non_color, y):
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(path, check_existing=True)
        if non_color:
            node.image.colorspace_settings.name = "Non-Color"
        node.location = (-600, y)
        return node

    albedo = image_node(maps["Albedo"], False, 300)
    links.new(albedo.outputs["Color"], bsdf.inputs["Base Color"])
    rough = image_node(maps["Roughness"], True, 0)
    links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])
    metal = image_node(maps["MetallicSmoothness"], True, -250)
    links.new(metal.outputs["Color"], bsdf.inputs["Metallic"])
    normal = image_node(maps["Normal"], True, -500)
    nmap = nodes.new("ShaderNodeNormalMap")
    links.new(normal.outputs["Color"], nmap.inputs["Color"])
    links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    nodes.active = albedo
    return mat
