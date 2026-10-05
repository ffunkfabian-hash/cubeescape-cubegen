"""Blender-side building blocks, shared by the CLI worker and the Blender add-on.

Only import this inside Blender (it needs ``bpy``).
"""

import bpy

from .geometry import box_uvs
from .materials import MATERIALS, srgb_to_linear


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


def build_collection(asset, collection, object_name=None, tags=None):
    """Create Blender objects for ``asset`` in ``collection``.

    Objects only get a location (their pivot); children are parented and placed
    relative to their parent. ``object_name(part)`` renames objects (default:
    the part name), ``tags`` become custom properties on the root objects.
    """
    objects = {}
    for o in asset.objects:
        name = object_name(o.name) if object_name else o.name
        if o.is_empty:
            obj = bpy.data.objects.new(name, None)
            obj.empty_display_type = "PLAIN_AXES"
            obj.empty_display_size = 0.2
        else:
            obj = bpy.data.objects.new(name, make_mesh(f"{asset.name}.{o.name}", o))
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


def make_mesh(name, asset_object):
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


def select_collection(collection):
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
    for obj in collection.all_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = next(iter(collection.all_objects), None)


def export_collection(collection, fmt, path):
    select_collection(collection)
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
