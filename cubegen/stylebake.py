"""Neutral mask bake for paint schemes (``cubegen/paint.py``) - runs inside Blender (experimental, 0.17.0).

One bake per model, independent of any scheme: weight maps of the painted game materials (three per RGB image),
ambient occlusion, an edge mask (Cycles' bevel normal against the true normal: rounded edges, any mesh) and an "up"
mask (world normal Z: dust, moss). Like ``bake.bake_asset`` it bakes a temporary joined copy of the parts on one shared
atlas (``BakeUV``). ``apply_paint`` composes a scheme from the maps with numpy and gives the parts one material.
"""

import os

import bpy

from . import bake as bk
from .paint import PAINTED, detail_map, weight_layout

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


def bake_masks(collection, name, out_dir, size, samples=16, device="cpu", base_of=None, cached=None):
    """Bake the neutral maps of one model; returns ``{"layout", "weights", "ao", "edge", "up", "device", "uvs"}``
    (paths; ``uvs``: the atlas, ``bake.read_uvs``) or None, with tile textures (``base_of``: material name -> game
    material, e.g. ``MT_Metal`` -> ``M_Metal``) also ``"diffuse"`` and ``"normal"``. The parts keep the atlas as UV
    map ``BakeUV`` for ``apply_paint``. ``cached`` (0.26.0, shared cache): ``{"uvs", "maps"}`` of an earlier bake
    with exactly these inputs - its maps are already in ``out_dir``, only the UVs are applied (ignored when they do
    not fit the objects)."""
    base_of = base_of or {}
    objects = bk._mesh_objects(collection)
    if not objects:
        return None
    scene = bpy.context.scene
    if cached and bk.apply_uvs(objects, cached["uvs"]):
        bk.bake_settings(scene, samples, device, size)
        return dict(cached["maps"], uvs=None)
    engine = scene.render.engine
    scene.render.engine = "CYCLES"
    used = bk.bake_settings(scene, samples, device, size)
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
    return dict(paths, layout=[list(g) for g in layout], weights=weights, device=used, uvs=bk.read_uvs(objects))


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


def pack_maps(maps, seed):
    """The packed neutral maps (``neutral.pack``: W0..W2 with noise and detail in alpha, Fields) of ``bake_masks``'
    maps; read once per model (every scheme of a run composes from the same)."""
    from .neutral import noise, pack

    if _LOADED.get("maps") is not maps or _LOADED.get("seed") != seed:  # the same model's maps for every scheme
        _LOADED.clear()
        _LOADED.update(maps=maps, seed=seed)
    if "packed" not in _LOADED:
        weights = [_load(p) for p in maps["weights"]]
        ao, edge, up = (_load(maps[k])[..., 0] for k in ("ao", "edge", "up"))
        layout = [tuple(g) for g in maps["layout"]]
        detail = detail_map(weights, layout, _load(maps["diffuse"], True)) if maps.get("diffuse") else None
        height = _load(maps["height"])[..., 0] if maps.get("height") else None
        _LOADED["packed"] = pack(weights, layout, ao, edge, up, height, noise(ao.shape[0], seed), detail)
    return _LOADED["packed"]


def compose_paint(maps, name, paint, out_dir, seed, prefix="", emission=True):
    """The maps of ``paint`` from ``bake_masks``' maps - no Blender bake involved: Albedo and Emission (sRGB),
    Roughness (grey) and MetallicSmoothness (R metallic, A smoothness - Unity's layout) as PNG. ``emission=False``:
    no Emission file (a scheme without glowing edges would write a black one).

    0.24.0: composed from the packed neutral maps (``pack_maps``, 8 bit as a shader samples them - noise and detail
    included), so ``neutral.compose_packed`` on the ``MTN_`` files gives exactly these maps."""
    import numpy as np

    from .neutral import compose_packed

    result = compose_packed(pack_maps(maps, seed), maps["layout"], paint)
    base = os.path.join(out_dir, f"{prefix}{name}_{paint}_")
    rough = result["roughness"]
    return {
        "albedo": _write(_to_srgb(result["albedo"]), f"{name}_{paint}_Albedo", base + "Albedo.png"),
        **({"emission": _write(_to_srgb(result["emission"]), f"{name}_{paint}_Emission", base + "Emission.png")}
           if emission else {}),
        "roughness": _write(np.repeat(rough[..., None], 3, axis=2), f"{name}_{paint}_Roughness", base + "Roughness.png"),
        "metallic_smoothness": _write(np.repeat(result["metallic"][..., None], 3, axis=2),
                                      f"{name}_{paint}_MetallicSmoothness", base + "MetallicSmoothness.png",
                                      alpha=1.0 - rough),
    }


def _crystal_material(paint):
    """The game's ``M_Crystal`` in the scheme's ``crystal_color`` (previews, icons, the .blend; ``None``: the game's
    colour again). Exported under the same name - Unity resolves crystal parts by material name and reads the colour
    from the manifest."""
    from cubegen.materials import MATERIALS
    from cubegen.paint import PAINTS, hex_rgb, srgb_to_linear

    base = bpy.data.materials.get("M_Crystal")
    if base is None:
        return None
    srgb = hex_rgb(PAINTS[paint]["crystal_color"]) if paint else MATERIALS["M_Crystal"][0]  # sRGB like bpy_builder
    rgb = tuple(srgb_to_linear(c) for c in srgb) + (1.0,)
    if base.use_nodes:
        for node in base.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                node.inputs["Base Color"].default_value = rgb
                if "Emission Color" in node.inputs:
                    node.inputs["Emission Color"].default_value = rgb
    base.diffuse_color = rgb
    return base


def paint_asset(collection, name, out_dir, size, paint, seed, base_of, samples=16, device="cpu", cached=None):
    """``--paint``: bake the neutral maps once, compose ``paint`` and give the model one material on the atlas (the
    atlas becomes UV0, like ``--textures baked``). Returns ``bake.bake_asset``'s shape - ``{"material", "maps",
    "device"}`` with Albedo, Normal, Roughness, MetallicSmoothness and, for a scheme with glowing edges
    (``edge_glow`` > 0), Emission (contract ``baked_maps``, strength ``emission_intensity``) - plus ``"neutral"``: the
    raw neutral bake (``Textures/Neutral``) and ``"packed"``: the five maps a recolouring shader reads
    (``MTN_<model>_W0..W2/Fields/Normal.png``, ``cubegen/neutral.py``) and ``"uvs"`` (the atlas of a new bake, for
    the shared cache). None without paintable parts. ``cached``: a reused neutral bake (``bake_masks``)."""
    import shutil

    from cubegen.contract import BAKED_MAPS
    from cubegen.paint import scheme_glows

    neutral_dir = os.path.join(out_dir, "Neutral")
    os.makedirs(neutral_dir, exist_ok=True)
    maps = bake_masks(collection, name, neutral_dir, size, samples=samples, device=device, base_of=base_of,
                      cached=cached)
    if maps is None:
        return None
    uvs = maps.pop("uvs", None)
    glows = scheme_glows(paint)
    painted = compose_paint(maps, name, paint, out_dir, seed, prefix="MTP_", emission=glows)
    final = {"Albedo": painted["albedo"], "Roughness": painted["roughness"],
             "MetallicSmoothness": painted["metallic_smoothness"],
             "Normal": os.path.join(out_dir, f"MTP_{name}_{paint}_Normal.png")}
    if glows:  # the glowing edges (Crystal blue, Dark red ...): a black map would only cost texture memory
        final["Emission"] = painted["emission"]
    shutil.copyfile(maps["normal"], final["Normal"])
    # the neutral maps for a recolouring shader (contract version 3, textures.neutral): MTN_<model>_<map>.png
    from cubegen.neutral import file_name, write_neutral

    packed = write_neutral(pack_maps(maps, seed), name, out_dir)
    packed["Normal"] = os.path.join(out_dir, file_name(name, "Normal"))
    shutil.copyfile(maps["normal"], packed["Normal"])
    # the material is named like --textures baked (MTA_<Asset>): Unity's baked import reads exactly that name; the
    # scheme is recorded in the manifest ("paint") and in the map file names (MTP_<Asset>_<scheme>_*.png)
    material = bk._baked_material(f"MTA_{name}", {k: v for k, v in final.items() if k != "Emission"})
    if glows:
        nodes, links = material.node_tree.nodes, material.node_tree.links
        emission = nodes.new("ShaderNodeTexImage")
        emission.image = bpy.data.images.load(final["Emission"], check_existing=True)
        bsdf = nodes.get("Principled BSDF")
        links.new(emission.outputs["Color"], bsdf.inputs["Emission Color"])
        # the same strength Unity sets (_EmissionColor = white x emission_intensity)
        bsdf.inputs["Emission Strength"].default_value = BAKED_MAPS["emission_intensity"]
    crystal = _crystal_material(paint)
    for o in bk._mesh_objects(collection):
        for slot in o.material_slots:
            if slot.material and slot.material.name == "M_Crystal" and crystal is not None:
                slot.material = crystal  # the scheme's crystal colour (Unity maps the name, manifest crystal_color)
            elif slot.material and slot.material.name not in bk.KEEP:
                slot.material = material
        tiled = o.data.uv_layers.get("UVMap")  # the atlas becomes the only UV map -> UV0 in Unity
        if tiled is not None:
            o.data.uv_layers.remove(tiled)
        o.data.uv_layers[bk.BAKE_UV].name = "UVMap"
    neutral = {k: v for k, v in maps.items() if k not in ("layout", "device")}
    return {"material": material.name, "maps": final, "device": maps["device"], "neutral": neutral,
            "layout": maps["layout"], "packed": packed, "uvs": uvs}


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
