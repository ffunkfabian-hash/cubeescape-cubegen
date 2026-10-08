"""Blender-side building blocks, shared by the CLI worker and the Blender add-on.

Only import this inside Blender (it needs ``bpy``).
"""

import bpy

from .geometry import box_uvs, face_normal
from .materials import MATERIALS, srgb_to_linear
from .palette import is_palette_material, resolve, uv as palette_uv


def _input(node, *names):
    for name in names:
        if name in node.inputs:
            return node.inputs[name]
    return None


def create_materials(overwrite=True):
    """Create the ``M_...`` materials with the game's values.

    ``overwrite=False`` keeps materials that already exist in the file (e.g. when
    the add-on runs inside the game's hand-made asset .blend).
    """
    for name, (color, smoothness, metallic, emission) in MATERIALS.items():
        mat = bpy.data.materials.get(name)
        if mat is not None and not overwrite:
            continue
        mat = mat or bpy.data.materials.new(name)
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


def create_textured_materials(textures):
    """``MT_...`` materials from a texture set: ``{plain material: {"name", "paths", "metallic", "color"}}``."""
    for info in textures.values():
        name = info["name"]
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        linear = tuple(srgb_to_linear(c) for c in info["color"])
        mat.diffuse_color = (*linear, 1.0)
        mat.use_backface_culling = True
        if mat.node_tree is None:
            mat.use_nodes = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        for node in [n for n in nodes if n.type == "TEX_IMAGE" or n.type == "NORMAL_MAP"]:
            nodes.remove(node)
        bsdf = nodes.get("Principled BSDF")
        if bsdf is None:
            continue
        paths = info["paths"]

        def image_node(path, non_color, x, y):
            node = nodes.new("ShaderNodeTexImage")
            node.image = bpy.data.images.load(path, check_existing=True)
            if non_color:
                node.image.colorspace_settings.name = "Non-Color"
            node.location = (x, y)
            return node

        albedo = image_node(paths["Albedo"], False, -600, 300)
        links.new(albedo.outputs["Color"], bsdf.inputs["Base Color"])
        rough = image_node(paths["Roughness"], True, -600, 0)
        links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])
        normal = image_node(paths["Normal"], True, -900, -300)
        normal_map = nodes.new("ShaderNodeNormalMap")
        normal_map.location = (-500, -300)
        links.new(normal.outputs["Color"], normal_map.inputs["Color"])
        links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
        bsdf.inputs["Metallic"].default_value = info["metallic"]
        nodes.active = albedo  # Workbench "Texture" colour mode shows the active image


def create_palette_material(palette):
    """``MP_Palette`` (or ``MP_Palette_<Name>``) from the palette maps (``palette.write_palette``): point-sampled colour, metallic and
    smoothness, emission for the glow cells."""
    name = palette["name"]
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_backface_culling = True
    if mat.node_tree is None:
        mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    for node in [n for n in nodes if n.type in ("TEX_IMAGE", "SEPARATE_COLOR", "SEPRGB", "MATH")]:
        nodes.remove(node)
    bsdf = nodes.get("Principled BSDF")
    if bsdf is None:
        return mat
    paths = palette["paths"]

    def image_node(path, non_color, y):
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(path, check_existing=True)
        node.interpolation = "Closest"  # one colour per cell, no blending into the neighbours
        if non_color:
            node.image.colorspace_settings.name = "Non-Color"
        node.location = (-600, y)
        return node

    albedo = image_node(paths["Albedo"], False, 300)
    links.new(albedo.outputs["Color"], bsdf.inputs["Base Color"])
    metal = image_node(paths["MetallicSmoothness"], True, 0)
    try:
        split = nodes.new("ShaderNodeSeparateColor")
    except RuntimeError:  # Blender < 3.3
        split = nodes.new("ShaderNodeSeparateRGB")
    links.new(metal.outputs["Color"], split.inputs[0])
    links.new(split.outputs[0], bsdf.inputs["Metallic"])
    rough = nodes.new("ShaderNodeMath")
    rough.operation = "SUBTRACT"
    rough.inputs[0].default_value = 1.0
    links.new(metal.outputs["Alpha"], rough.inputs[1])
    links.new(rough.outputs[0], bsdf.inputs["Roughness"])
    emission = image_node(paths["Emission"], False, -300)
    color_in = _input(bsdf, "Emission Color", "Emission")
    strength_in = _input(bsdf, "Emission Strength")
    if color_in is not None:
        links.new(emission.outputs["Color"], color_in)
    if strength_in is not None:
        strength_in.default_value = palette["emission"]
    mat.diffuse_color = (0.6, 0.62, 0.66, 1.0)
    nodes.active = albedo
    return mat


def build_collection(asset, collection, object_name=None, tags=None, material_map=None):
    """Create Blender objects for ``asset`` in ``collection``.

    Objects only get a location (their pivot); children are parented and placed
    relative to their parent. ``object_name(part)`` renames objects (default:
    the part name), ``tags`` become custom properties on the root objects,
    ``material_map`` swaps materials (``{"M_Metal": "MT_Metal"}`` for textures, a ``palette.PaletteMap`` per part).
    """
    objects = {}
    for o in asset.objects:
        name = object_name(o.name) if object_name else o.name
        if o.is_empty:
            obj = bpy.data.objects.new(name, None)
            obj.empty_display_type = "PLAIN_AXES"
            obj.empty_display_size = 0.2
        else:
            triangulate = asset.meta.get("damage") == "destroyed" and asset.p is not None and asset.p.style.generation >= 3
            obj = bpy.data.objects.new(name, make_mesh(f"{asset.name}.{o.name}", o, material_map, triangulate=triangulate))
        collection.objects.link(obj)
        if o.parent:
            parent = asset.get(o.parent)
            obj.parent = objects[o.parent]
            obj.location = tuple(o.pivot[i] - parent.pivot[i] for i in range(3))
        else:
            obj.location = o.pivot
            for key, value in (tags or {}).items():
                obj[key] = value
        objects[o.name] = obj
    return objects


def make_mesh(name, asset_object, material_map=None, *, triangulate=False):
    src = asset_object.mesh
    verts = asset_object.local_verts()
    me = bpy.data.meshes.new(name)
    faces, source_faces = [], []
    for fi, face in enumerate(src.faces):
        emitted = [(face[0], face[i], face[i+1]) for i in range(1, len(face)-1)] if triangulate else [face]
        faces.extend(emitted); source_faces.extend([fi] * len(emitted))
    # Jagged fracture caps are non-planar n-gons. Unity can discard their entire
    # material slot while triangulating FBX; explicit triangles retain the cap.
    me.from_pydata(verts, [], faces)
    roles = [resolve(material_map, asset_object.name, src.roles[fi]) for fi in source_faces]
    materials = sorted(set(roles))
    for m in materials:
        me.materials.append(bpy.data.materials[m])
    uv_layer = me.uv_layers.new(name="UVMap")
    for fi, poly in enumerate(me.polygons):
        poly.material_index = materials.index(roles[fi])
        try:
            poly.use_smooth = False  # flat shading = crisp low-poly look
        except AttributeError:  # newer Blender: from_pydata already creates flat faces
            pass
        if is_palette_material(roles[fi]):  # palette mode: the centre of the colour's cell
            uvs = [palette_uv(src.roles[source_faces[fi]])] * len(faces[fi])
        else:
            points = [verts[i] for i in faces[fi]]
            uvs = box_uvs(points, face_normal(points))
        for loop_index, uv in zip(poly.loop_indices, uvs):
            uv_layer.data[loop_index].uv = uv
    me.validate(clean_customdata=False)
    me.update()
    return me


def select_collection(collection):
    # Removing/rebuilding a collection can leave stale view-layer entries in Blender.
    # Refresh before iteration so sequential exports never select deleted objects.
    bpy.context.view_layer.update()
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
    for obj in collection.all_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = next(iter(collection.all_objects), None)


def _patch_fbx_nested_bake():
    """Fix the FBX exporter's local matrix of objects nested two or more levels deep.

    With ``bake_space_transform`` the exporter writes a child's local matrix as
    ``P_fbx^-1 @ P @ L @ G^-1`` (``P_fbx`` = the parent's matrix in FBX space,
    ``G`` = axis conversion). For a child of a root object ``P_fbx = P @ G^-1``
    and this is the correct ``G @ L @ G^-1``. One level deeper ``P_fbx`` already
    is ``G @ P @ G^-1``, the conversion is applied twice: the part gets a wrong
    position and a 90 degree rotation (balance_scale Slot_A, robot_arm Arm_Upper,
    turret Glow in cubegen 0.7.0). For those objects this returns ``G @ L @ G^-1``;
    everything else keeps the exporter's own (correct) value.
    """
    import importlib

    try:
        fbx_utils = importlib.import_module("io_scene_fbx.fbx_utils")
    except ImportError:
        return
    wrapper = getattr(fbx_utils, "ObjectWrapper", None)
    original = getattr(wrapper, "fbx_object_matrix", None)
    if original is None or getattr(original, "_cubegen_patched", False):
        return

    def fbx_object_matrix(self, scene_data, rest=False, local_space=False, global_space=False):
        try:
            nested = (not local_space and not global_space and self._tag == "OB"
                      and not self.parented_to_armature and self.has_valid_parent(scene_data.objects)
                      and self.use_bake_space_transform(scene_data))
            parent = self.parent if nested else None
            nested = (parent is not None and parent._tag == "OB" and parent.use_bake_space_transform(scene_data)
                      and parent.has_valid_parent(scene_data.objects))
        except AttributeError:  # exporter internals changed: keep its result (the export check reports errors)
            nested = False
        if not nested:
            return original(self, scene_data, rest=rest, local_space=local_space, global_space=global_space)
        local = self.matrix_rest_local if rest else self.matrix_local
        return scene_data.settings.global_matrix @ local @ scene_data.settings.global_matrix_inv

    fbx_object_matrix._cubegen_patched = True
    wrapper.fbx_object_matrix = fbx_object_matrix


def export_collection(collection, fmt, path):
    select_collection(collection)
    if fmt == "fbx":
        _patch_fbx_nested_bake()
        # identical to the game's export_fbx(): rotation 0 / scale 1 in Unity, +Z forward;
        # textures (if any) are referenced relative to the FBX, not embedded
        bpy.ops.export_scene.fbx(
            filepath=path, use_selection=True, object_types={"MESH", "EMPTY"}, apply_unit_scale=True,
            apply_scale_options="FBX_SCALE_ALL", axis_forward="-Z", axis_up="Y", bake_space_transform=True,
            use_mesh_modifiers=True, mesh_smooth_type="FACE", add_leaf_bones=False, bake_anim=False,
            use_custom_props=True, path_mode="RELATIVE",
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


def remove_collection(collection):
    """Delete a collection with its child collections, objects and their (now unused) data."""
    for child in list(collection.children):
        remove_collection(child)
    for obj in list(collection.objects):
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data is not None and data.users == 0:
            if isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Curve):
                bpy.data.curves.remove(data)
    bpy.data.collections.remove(collection)
