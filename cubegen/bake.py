"""Per-asset baked textures (``--textures baked``) - runs inside Blender.

For one asset (a collection):

1. a shared atlas UV map for all its mesh objects (Smart UV Project)
2. Cycles bakes of the tiled ``MT_`` materials into that atlas: colour, roughness,
   tangent normals, metallic (via a temporary emission), ambient occlusion
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

KEEP = {"M_GlowCyan", "M_GlowRed", "M_GlowOrange", "M_Crystal", "M_Glass"}
BAKE_UV = "BakeUV"


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


def _metallic_bake(objects, materials, image):
    """Metallic has no bake pass: temporarily route the metallic value through an emission shader."""
    restore = []
    for mat in materials:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        out = next((n for n in nodes if n.type == "OUTPUT_MATERIAL"), None)
        bsdf = nodes.get("Principled BSDF")
        if out is None or bsdf is None:
            continue
        old = [l.from_socket for l in out.inputs["Surface"].links]
        value = bsdf.inputs["Metallic"].default_value
        emit = nodes.new("ShaderNodeEmission")
        emit.inputs["Color"].default_value = (value, value, value, 1.0)
        links.new(emit.outputs["Emission"], out.inputs["Surface"])
        restore.append((mat, out, emit, old))
    try:
        _bake(objects, materials, image, "EMIT")
    finally:
        for mat, out, emit, old in restore:
            mat.node_tree.nodes.remove(emit)
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
    proc = subprocess.run(list(cmd) + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ImageMagick failed: {proc.stderr.strip()}")


def bake_asset(collection, asset_name, out_dir, size, magick_cmd, samples=16, seed=0):
    """Bake one asset; returns ``{"material": name, "maps": {kind: path}}`` or None (nothing to bake)."""
    objects = _mesh_objects(collection)
    if not objects:
        return None
    scene = bpy.context.scene
    engine = scene.render.engine
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.cycles.device = "CPU"
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, f"{asset_name}_Bake")
    paths = {k: f"{base}{k}.png" for k in ("Color", "AO", "Roughness", "Metallic")}
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
    try:
        _atlas_uvs(objects)
        materials = _materials(objects)
        images = {}
        for kind, non_color in (("Color", False), ("AO", True), ("Roughness", True), ("Metallic", True),
                                ("Normal", True)):
            images[kind] = _image(f"{asset_name}_{kind}", size, non_color)
        _bake(objects, materials, images["Color"], "DIFFUSE", pass_filter={"COLOR"})
        _bake(objects, materials, images["AO"], "AO")
        _bake(objects, materials, images["Roughness"], "ROUGHNESS")
        _bake(objects, materials, images["Normal"], "NORMAL", normal_space="TANGENT")
        _metallic_bake(objects, materials, images["Metallic"])
        for kind in ("Color", "AO", "Roughness", "Metallic"):
            _save(images[kind], paths[kind])
        _save(images["Normal"], final["Normal"])
    finally:
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
    _magick(magick_cmd, [paths["Roughness"], "-colorspace", "gray", "(", paths["AO"], "-colorspace", "gray",
                         "-negate", "-evaluate", "multiply", "0.25", ")", "-compose", "Plus", "-composite",
                         f"PNG8:{final['Roughness']}"])
    _magick(magick_cmd, [paths["Metallic"], "-colorspace", "gray", "(", final["Roughness"], "-negate", ")",
                         "-alpha", "off", "-compose", "CopyOpacity", "-composite",
                         f"PNG32:{final['MetallicSmoothness']}"])
    for p in paths.values():
        os.remove(p)
    for img in images.values():
        bpy.data.images.remove(img)

    material = _baked_material(f"MTA_{asset_name}", final)
    for o in objects:
        for slot in o.material_slots:
            if slot.material and slot.material.name not in KEEP:
                slot.material = material
        # the atlas becomes the only UV map -> UV0 in Unity
        tiled = o.data.uv_layers.get("UVMap")
        if tiled is not None:
            o.data.uv_layers.remove(tiled)
        o.data.uv_layers[BAKE_UV].name = "UVMap"
    return {"material": material.name, "maps": final}


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
