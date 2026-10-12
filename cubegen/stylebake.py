"""Neutral mask bake for paint schemes (``cubegen/paint.py``) - runs inside Blender (experimental, 0.17.0).

One bake per model, independent of any scheme: weight maps of the painted game materials (three per RGB image),
ambient occlusion, an edge mask (Cycles' bevel normal against the true normal: rounded edges, any mesh) and an "up"
mask (world normal Z: dust, moss). Like ``bake.bake_asset`` it bakes a temporary joined copy of the parts on one shared
atlas (``BakeUV``). ``apply_paint`` composes a scheme from the maps with numpy and gives the parts one material.
"""

import os

import bpy

from . import bake as bk
from .paint import PAINTED, compose, detail_map, weight_layout

EDGE_RADIUS = 0.03   # m, a little more than the models' 2 cm bevels
EDGE_GAIN = 6.0      # 1 - dot(bevel normal, normal) is small: scale it to a 0..1 mask


def _with_emission(objects, materials, image, socket_for):
    """Bake ``EMIT`` with every material's surface temporarily replaced by an emission of ``socket_for(mat, nodes,
    links)`` (a colour or float socket, or an RGB tuple)."""
    restore = []
    for mat in materials:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        out = next((n for n in nodes if n.type == "OUTPUT_MATERIAL"), None)
        if out is None:
            continue
        old = [l.from_socket for l in out.inputs["Surface"].links]
        before = set(nodes)
        emit = nodes.new("ShaderNodeEmission")
        source = socket_for(mat, nodes, links)
        if isinstance(source, tuple):
            emit.inputs["Color"].default_value = (*source, 1.0)
        else:
            links.new(source, emit.inputs["Color"])
        links.new(emit.outputs["Emission"], out.inputs["Surface"])
        restore.append((mat, out, [n for n in nodes if n not in before], old))
    try:
        bk._bake(objects, materials, image, "EMIT")
    finally:
        for mat, out, temp, old in restore:
            for node in temp:
                mat.node_tree.nodes.remove(node)
            for socket in old:
                mat.node_tree.links.new(socket, out.inputs["Surface"])


def _edge_socket(mat, nodes, links):
    geometry = nodes.new("ShaderNodeNewGeometry")
    bevel = nodes.new("ShaderNodeBevel")
    bevel.inputs["Radius"].default_value = EDGE_RADIUS
    bevel.samples = 8
    dot = nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    links.new(bevel.outputs["Normal"], dot.inputs[0])
    links.new(geometry.outputs["Normal"], dot.inputs[1])
    inv = nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    links.new(dot.outputs["Value"], inv.inputs[1])
    gain = nodes.new("ShaderNodeMath")
    gain.operation = "MULTIPLY"
    gain.use_clamp = True
    gain.inputs[1].default_value = EDGE_GAIN
    links.new(inv.outputs[0], gain.inputs[0])
    return gain.outputs[0]


def _up_socket(mat, nodes, links):
    geometry = nodes.new("ShaderNodeNewGeometry")
    split = nodes.new("ShaderNodeSeparateXYZ")
    links.new(geometry.outputs["Normal"], split.inputs[0])
    clamp = nodes.new("ShaderNodeMath")
    clamp.operation = "MAXIMUM"
    clamp.inputs[1].default_value = 0.0
    links.new(split.outputs["Z"], clamp.inputs[0])
    return clamp.outputs[0]


def _height_socket(z_min, z_max):
    def socket(mat, nodes, links):
        geometry = nodes.new("ShaderNodeNewGeometry")
        split = nodes.new("ShaderNodeSeparateXYZ")
        links.new(geometry.outputs["Position"], split.inputs[0])
        span = nodes.new("ShaderNodeMapRange")
        span.inputs["From Min"].default_value = z_min
        span.inputs["From Max"].default_value = z_max
        links.new(split.outputs["Z"], span.inputs["Value"])
        return span.outputs["Result"]
    return socket


def bake_masks(collection, name, out_dir, size, samples=16, device="cpu", base_of=None):
    """Bake the neutral maps of one model; returns ``{"layout", "weights", "ao", "edge", "up", "device"}`` (paths)
    or None, with tile textures (``base_of``: material name -> game material, e.g. ``MT_Metal`` -> ``M_Metal``) also
    ``"diffuse"`` and ``"normal"``. The parts keep the atlas as UV map ``BakeUV`` for ``apply_paint``."""
    base_of = base_of or {}
    objects = bk._mesh_objects(collection)
    if not objects:
        return None
    scene = bpy.context.scene
    engine = scene.render.engine
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    used = bk.use_device(scene, device, size)
    os.makedirs(out_dir, exist_ok=True)
    hidden_colls = {c: c.hide_render for c in bpy.data.collections if c != collection}
    hidden_objs = {o: o.hide_render for o in collection.all_objects}
    for c in hidden_colls:
        c.hide_render = True
    for o in hidden_objs:
        o.hide_render = False
    target = None
    paths = {}
    try:
        bk._atlas_uvs(objects)
        materials = bk._materials(objects)
        layout = weight_layout([base_of.get(m.name, m.name) for m in materials])
        target = bk._joined_copy(objects)
        for o in objects:
            o.hide_render = True
        bake = [target]
        weights = []
        for k, group in enumerate(layout):
            image = bk._image(f"{name}_W{k}", size, True)
            _with_emission(bake, materials, image,
                           lambda mat, nodes, links, g=group: tuple(1.0 if base_of.get(mat.name, mat.name) == m
                                                                    else 0.0 for m in g)
                           + (0.0,) * (3 - len(g)))
            weights.append(_save(image, os.path.join(out_dir, f"{name}_W{k}.png")))
        image = bk._image(f"{name}_AO", size, True)
        bk._bake(bake, materials, image, "AO")
        paths["ao"] = _save(image, os.path.join(out_dir, f"{name}_AO.png"))
        image = bk._image(f"{name}_Edge", size, True)
        _with_emission(bake, materials, image, _edge_socket)
        paths["edge"] = _save(image, os.path.join(out_dir, f"{name}_Edge.png"))
        image = bk._image(f"{name}_Up", size, True)
        _with_emission(bake, materials, image, _up_socket)
        paths["up"] = _save(image, os.path.join(out_dir, f"{name}_Up.png"))
        zs = [(o.matrix_world @ v.co).z for o in objects for v in o.data.vertices]
        image = bk._image(f"{name}_Height", size, True)
        _with_emission(bake, materials, image, _height_socket(min(zs), max(zs)))
        paths["height"] = _save(image, os.path.join(out_dir, f"{name}_Height.png"))
        if base_of:  # tile textures: their detail (brightness, normals) is part of the neutral bake too
            image = bk._image(f"{name}_Diffuse", size, False)
            bk._bake(bake, materials, image, "DIFFUSE", pass_filter={"COLOR"})
            paths["diffuse"] = _save(image, os.path.join(out_dir, f"{name}_Diffuse.png"))
            image = bk._image(f"{name}_Normal", size, True)
            bk._bake(bake, materials, image, "NORMAL", normal_space="TANGENT")
            paths["normal"] = _save(image, os.path.join(out_dir, f"{name}_Normal.png"))
    finally:
        if target is not None:
            bk._remove(target)
        scene.render.engine = engine
        for c, state in hidden_colls.items():
            c.hide_render = state
        for o, state in hidden_objs.items():
            o.hide_render = state
    return dict(paths, layout=[list(g) for g in layout], weights=weights, device=used)


def _save(image, path):
    bk._save(image, path)
    bpy.data.images.remove(image)
    return path


# ---------------------------------------------------------------------------
# composing a scheme (numpy, Blender's bundled one)
# ---------------------------------------------------------------------------

def _load(path, srgb=False):
    """RGB as float32; ``srgb``: the file holds sRGB colours (a colour bake) -> linear."""
    import numpy as np

    img = bpy.data.images.load(path, check_existing=False)
    if not srgb:
        img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    data = np.empty(w * h * 4, dtype=np.float32)  # float32: Blender's own format, no conversion
    img.pixels.foreach_get(data)  # byte images: the stored (encoded) values, no colour management
    bpy.data.images.remove(img)
    rgb = data.reshape(h, w, 4)[..., :3]
    if srgb:
        rgb = np.where(rgb <= 0.04045, rgb / 12.92, np.power((rgb + 0.055) / 1.055, 2.4)).astype(np.float32)
    return rgb


_LOADED = {}  # neutral maps of the model being composed (one model at a time: memory stays bounded)


def _noise(size, seed, cells=48):
    """Deterministic noise 0..1 (bilinear upscaled random grid)."""
    import numpy as np

    grid = np.random.RandomState(seed % 2**31).rand(cells + 1, cells + 1).astype(np.float32)
    x = np.linspace(0, cells, size, dtype=np.float32)
    i = np.minimum(x.astype(np.int32), cells - 1)
    f = x - i
    rows = grid[i] * (1 - f)[:, None] + grid[i + 1] * f[:, None]
    return rows[:, i] * (1 - f)[None, :] + rows[:, i + 1] * f[None, :]


def _to_srgb(linear):
    import numpy as np

    return np.where(linear <= 0.0031308, linear * 12.92, 1.055 * np.power(linear, 1 / 2.4) - 0.055)


def _write(rgb, name, path, alpha=None):
    import numpy as np

    h, w = rgb.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=alpha is not None)
    a = np.ones((h, w, 1), dtype=np.float32) if alpha is None else alpha[..., None].astype(np.float32)
    rgba = np.concatenate([rgb, a], axis=2).astype(np.float32)
    img.pixels.foreach_set(rgba.ravel())
    bk._save(img, path)
    bpy.data.images.remove(img)
    return path


def compose_paint(maps, name, paint, out_dir, seed, prefix=""):
    """The maps of ``paint`` from ``bake_masks``' maps - no Blender bake involved: Albedo and Emission (sRGB),
    Roughness (grey) and MetallicSmoothness (R metallic, A smoothness - Unity's layout) as PNG."""
    import numpy as np

    if _LOADED.get("maps") is not maps:  # the same model's maps for every scheme: read the PNGs once
        _LOADED.clear()
        _LOADED["maps"] = maps

    def load(key, path, srgb=False):
        if key not in _LOADED:
            _LOADED[key] = _load(path, srgb)
        return _LOADED[key]

    weights = [load(f"w{i}", p) for i, p in enumerate(maps["weights"])]
    ao, edge, up = (load(k, maps[k])[..., 0] for k in ("ao", "edge", "up"))
    noise = 0.6 * _noise(ao.shape[0], seed, 32) + 0.4 * _noise(ao.shape[0], seed + 1, 160)
    layout = [tuple(g) for g in maps["layout"]]
    detail = detail_map(weights, layout, load("diffuse", maps["diffuse"], True)) if maps.get("diffuse") else None
    height = load("height", maps["height"])[..., 0] if maps.get("height") else None
    result = compose(weights, layout, ao, edge, up, noise, paint, detail, height)
    base = os.path.join(out_dir, f"{prefix}{name}_{paint}_")
    rough = result["roughness"]
    return {
        "albedo": _write(_to_srgb(result["albedo"]), f"{name}_{paint}_Albedo", base + "Albedo.png"),
        "emission": _write(_to_srgb(result["emission"]), f"{name}_{paint}_Emission", base + "Emission.png"),
        "roughness": _write(np.repeat(rough[..., None], 3, axis=2), f"{name}_{paint}_Roughness", base + "Roughness.png"),
        "metallic_smoothness": _write(np.repeat(result["metallic"][..., None], 3, axis=2),
                                      f"{name}_{paint}_MetallicSmoothness", base + "MetallicSmoothness.png",
                                      alpha=1.0 - rough),
    }


def paint_asset(collection, name, out_dir, size, paint, seed, base_of, samples=16, device="cpu"):
    """``--paint``: bake the neutral maps once, compose ``paint`` and give the model one material on the atlas (the
    atlas becomes UV0, like ``--textures baked``). Returns ``bake.bake_asset``'s shape - ``{"material", "maps",
    "device"}`` with Albedo, Normal, Roughness, MetallicSmoothness (what Unity's baked import reads) and Emission -
    plus ``"neutral"``: the neutral maps for a recolouring shader. None without paintable parts."""
    import shutil

    neutral_dir = os.path.join(out_dir, "Neutral")
    os.makedirs(neutral_dir, exist_ok=True)
    maps = bake_masks(collection, name, neutral_dir, size, samples=samples, device=device, base_of=base_of)
    if maps is None:
        return None
    painted = compose_paint(maps, name, paint, out_dir, seed, prefix="MTP_")
    final = {"Albedo": painted["albedo"], "Roughness": painted["roughness"],
             "MetallicSmoothness": painted["metallic_smoothness"], "Emission": painted["emission"],
             "Normal": os.path.join(out_dir, f"MTP_{name}_{paint}_Normal.png")}
    shutil.copyfile(maps["normal"], final["Normal"])
    # the material is named like --textures baked (MTA_<Asset>): Unity's baked import reads exactly that name; the
    # scheme is recorded in the manifest ("paint") and in the map file names (MTP_<Asset>_<scheme>_*.png)
    material = bk._baked_material(f"MTA_{name}", {k: v for k, v in final.items() if k != "Emission"})
    nodes, links = material.node_tree.nodes, material.node_tree.links
    emission = nodes.new("ShaderNodeTexImage")
    emission.image = bpy.data.images.load(final["Emission"], check_existing=True)
    bsdf = nodes.get("Principled BSDF")
    links.new(emission.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 3.0
    for o in bk._mesh_objects(collection):
        for slot in o.material_slots:
            if slot.material and slot.material.name not in bk.KEEP:
                slot.material = material
        tiled = o.data.uv_layers.get("UVMap")  # the atlas becomes the only UV map -> UV0 in Unity
        if tiled is not None:
            o.data.uv_layers.remove(tiled)
        o.data.uv_layers[bk.BAKE_UV].name = "UVMap"
    neutral = {k: v for k, v in maps.items() if k not in ("layout", "device")}
    return {"material": material.name, "maps": final, "device": maps["device"], "neutral": neutral,
            "layout": maps["layout"]}


def apply_paint(collection, maps, paint, textures, roughness, base_names=()):
    """One material ``MPS_<paint>`` with the composed maps on the atlas for every painted slot of the model."""
    mat = bpy.data.materials.new(f"MPS_{collection.name}_{paint}")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    uv = nodes.new("ShaderNodeUVMap")
    uv.uv_map = bk.BAKE_UV
    albedo = nodes.new("ShaderNodeTexImage")
    albedo.image = bpy.data.images.load(textures["albedo"], check_existing=True)
    emission = nodes.new("ShaderNodeTexImage")
    emission.image = bpy.data.images.load(textures["emission"], check_existing=True)
    for node in (albedo, emission):
        links.new(uv.outputs["UV"], node.inputs["Vector"])
    links.new(albedo.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(emission.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 3.0
    bsdf.inputs["Roughness"].default_value = roughness
    if maps.get("normal"):
        normal = nodes.new("ShaderNodeTexImage")
        normal.image = bpy.data.images.load(maps["normal"], check_existing=True)
        normal.image.colorspace_settings.name = "Non-Color"
        links.new(uv.outputs["UV"], normal.inputs["Vector"])
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.uv_map = bk.BAKE_UV
        links.new(normal.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    for o in bk._mesh_objects(collection):
        for slot in o.material_slots:
            if slot.material and (slot.material.name in PAINTED or slot.material.name in base_names):
                slot.material = mat
    return mat
