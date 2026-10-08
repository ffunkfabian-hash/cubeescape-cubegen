"""Export minimal procedural fragment fixtures and audited models in one Blender run."""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import bpy
from cubegen.asset import Asset, to_unity
from cubegen.geometry import pipe_section, ring, torus, prism, lathe, box, sphere, Prim
from cubegen.models import REGISTRY, generate_asset
from cubegen.models.fracture import fracture_asset
from cubegen.params import Style
from cubegen.pipeline import rig_data
from cubegen.bpy_builder import create_materials, build_collection, export_collection, remove_collection
from cubegen.fbxread import check_asset, read, unity_locals


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out", required=True)
parser.add_argument("--audit", help="Optional JSON from tools.audit_fragment_profiles")
parser.add_argument("--family", choices=("round", "extrusion", "lathe", "box", "radial"), default="round")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out = os.path.join(args.out, "models")
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.scale_length = 1
create_materials()


def check_triangle_geometry(path, asset):
    """Inspect real FBX triangle indices, not just bounds or triangle counts."""
    from collections import Counter
    root = read(path)
    objects = root.find("Objects")
    names = {m.props[0]: m.props[1].split("\x00")[0] for m in objects.find_all("Model")}
    geometries = {g.props[0]: g for g in objects.find_all("Geometry")}
    locals = unity_locals(path)
    for connection in root.find("Connections").find_all("C"):
        if connection.props[0] != "OO" or connection.props[1] not in geometries or connection.props[2] not in names:
            continue
        name = names[connection.props[2]]
        obj = asset.get(name)
        wanted = [to_unity(p) for p in obj.local_verts()]
        vertices = locals[name]["vertices"]
        mapping = []
        for p in vertices:
            index = min(range(len(wanted)), key=lambda i: max(abs(p[k] - wanted[i][k]) for k in range(3)))
            if max(abs(p[k] - wanted[index][k]) for k in range(3)) > 1e-4:
                raise AssertionError("FBX vertex does not match the explicit source triangle.")
            mapping.append(index)
        faces, face = [], []
        for v in geometries[connection.props[1]].find("PolygonVertexIndex").props[0]:
            face.append(mapping[-v - 1 if v < 0 else v])
            if v < 0:
                if len(face) != 3: raise AssertionError("Warped box must export explicit triangles.")
                faces.append(tuple(sorted(face))); face = []
        if Counter(faces) != Counter(tuple(sorted(f)) for f in obj.mesh.faces):
            raise AssertionError("FBX changed the render/collision triangulation.")
    print(asset.name, "explicit FBX triangle geometry checked", flush=True)


def export(asset, kind, seed, damage="fractured"):
    spec = {"type": kind, "seed": seed, "name": asset.name,
            "style": {"generation": 3, "damage": damage, "clutter": "none"}}
    collection = bpy.data.collections.new(asset.name)
    bpy.context.scene.collection.children.link(collection)
    try:
        build_collection(asset, collection)
        path = os.path.join(out, asset.name + ".fbx")
        export_collection(collection, "fbx", path)
        issues = check_asset(path, asset)
        if issues:
            raise RuntimeError(str(issues))
        if asset.name.startswith(("Gen_BoxFixture_", "Gen_RadialFixture_")):
            check_triangle_geometry(path, asset)
        with open(os.path.join(out, asset.name + ".cubegen.json"), "w", encoding="utf-8") as stream:
            json.dump(rig_data(asset, spec, 42), stream, indent=2)
        print(asset.name, asset.meta.get("fragments", 0), len(asset.colliders), "FBX checked", flush=True)
    finally:
        # Exercise repeated deletion/build/export without any caller view-layer refresh.
        remove_collection(collection)


if args.audit:
    with open(args.audit, encoding="utf-8") as stream:
        rows = json.load(stream)["rows"]
    for row in rows:
        if not row.get("changed", row["shapes_before"] != row["shapes_after"]):
            continue
        kind = row["type"]
        prefix = "Gen_" + args.family.title() + "Proof_"
        asset = generate_asset(kind, row["seed"], name=prefix + REGISTRY[kind].title + "_000",
                               style=Style(generation=3, damage="fractured"))
        export(asset, kind, row["seed"])

samples = (
    ("Pipe", pipe_section(.32, .8, .06, 8), (0, 0, 0)),
    ("Band", ring(.26, .32, .08, 10, "M_Metal"), (math.pi / 2, 0, 0)),
    ("Torus", torus(.32, .06, 10, 6, "M_Metal"), (math.pi / 2, 0, 0)))
if args.family == "extrusion":
    arch = [(-1.5, 0), (-1.5, 2), (1.5, 2), (1.5, 0), (1, 0), (1, 1.5), (-1, 1.5), (-1, 0)]
    beam = [(-1, 0), (1, 0), (1, .25), (.15, .25), (.15, 1.75), (1, 1.75), (1, 2), (-1, 2), (-1, 1.75), (-.15, 1.75), (-.15, .25), (-1, .25)]
    arrow = [(-.25, -1), (.25, -1), (.25, 0), (.6, 0), (0, 1), (-.6, 0), (-.25, 0)]
    samples = tuple((name, prism(poly, .25, "M_Metal"), (math.pi / 2, 0, 0)) for name, poly in (("Arch", arch), ("Beam", beam), ("Arrow", arrow)))
elif args.family == "lathe":
    profiles = (
        ("Dish", [(0, -.08), (.35, -.05), (1, .22), (.94, .24), (.3, .02), (0, 0)], 12),
        ("Insulator", [(.2, 0), (.2, .06), (.42, .12), (.2, .18), (.2, .3), (.42, .36), (.2, .42), (0, .42)], 8),
        ("Socket", [(.6, 0), (.9, .12), (.6, .25), (.6, .5), (.9, .65), (.6, .75)], 7))
    samples = tuple((name, lathe(profile, sides, "M_Metal"), (0, 0, 0)) for name, profile, sides in profiles)
elif args.family == "box":
    # Reproduce the independently discovered wide/short stump bug in real FBX states.
    for damage in ("intact", "fractured"):
        name = "Gen_BoxProof_FallenPillarWide_" + damage.title() + "_000"
        asset = generate_asset("fallen_pillar", 42, name=name, params={"width": 2, "segments": 1, "stump": True},
                               style=Style(generation=3, damage=damage))
        export(asset, "fallen_pillar", 42, damage)
    samples = []
    for name, dimensions, dent in (("Wall", (2, 1, 1), .45), ("Console", (1.4, .8, .4), .2), ("Pillar", (.8, .8, 1.5), .6)):
        primitive = box(*dimensions, "M_Metal", top_role="M_Warning")
        for i in (4, 6):
            x, y, z = primitive.verts[i]; primitive.verts[i] = (x, y, z - dent)
        if name == "Console":
            for i, (x, y, z) in enumerate(primitive.verts):
                primitive.verts[i] = (x + (.012 if i % 2 else -.008), y + (.01 if i % 3 else -.015), z + (.004 if i % 2 else -.006))
        samples.append((name, primitive, (0, 0, 0)))
elif args.family == "radial":
    for kind in ("cocoon", "stalagmite"):
        asset = generate_asset(kind, 1, name="Gen_RadialProof_" + REGISTRY[kind].title + "Seed1_000",
                               style=Style(generation=3, damage="fractured"))
        export(asset, kind, 1)
    boulder = sphere(1, 8, 4, "M_Metal"); boulder.verts[9] = (.42, 0, 0)
    samples = [("Boulder", boulder, (0, 0, 0))]
    for label, kind, objname, seed in (("Shell", "cocoon", "Shell", 1), ("Island", "floating_island", "Island", 1465968305)):
        source = generate_asset(kind, seed, style=Style(generation=3))
        mesh = source.get(objname).mesh; part = mesh.parts[0]
        primitive = Prim(mesh.verts[part.v0:part.v1], [tuple(v - part.v0 for v in mesh.faces[fi]) for fi in part.face_indices()],
                         [mesh.roles[fi] for fi in part.face_indices()], part.closed, part.convex_faces)
        samples.append((label, primitive, (0, 0, 0)))
for name, primitive, rotation in samples:
    asset = Asset("Gen_" + args.family.title() + "Fixture_" + name)
    asset.part("Body").add(primitive, rot=rotation)
    asset.normalize("floor")
    fracture_asset(asset, 42, "floor", pieces=1, generation=3)
    export(asset, "geometry_test", 42)
