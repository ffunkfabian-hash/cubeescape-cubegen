"""Pure-Python tests: geometry, seeds, materials and every model type."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.asset import Asset  # noqa: E402
from cubegen.geometry import Mesh, box, chamfer_box, cylinder, lathe, prism, sphere, torus  # noqa: E402
from cubegen.materials import MATERIALS  # noqa: E402
from cubegen.models import REGISTRY, asset_name, generate_asset, model_types  # noqa: E402
from cubegen.seeds import MAX_SEED, model_seed, parse_seed  # noqa: E402

SEEDS_PER_TYPE = 40


def volume(prim):
    m = Mesh()
    return m.part_volume(m.add(prim))


class GeometryTests(unittest.TestCase):
    def test_box_volume_and_orientation(self):
        self.assertAlmostEqual(volume(box(1, 2, 3, "M_Wall")), 6.0, places=6)

    def test_chamfer_box(self):
        b = 0.1
        prim = chamfer_box(1, 2, 3, "M_Wall", b)
        self.assertEqual(len(prim.faces), 26)
        expected = 6.0 - b * b / 2 * 4 * (1 + 2 + 3) + 8 * b ** 3 / 6 * 4  # box - edge prisms + corner fix-up
        self.assertAlmostEqual(volume(prim), expected, places=3)

    def test_cylinder_volume(self):
        sides = 64
        polygon_area = 0.5 * sides * math.sin(2 * math.pi / sides)
        self.assertAlmostEqual(volume(cylinder(1.0, 2.0, sides, "M_Wall")), polygon_area * 2.0, places=6)

    def test_flat_side_faces_front(self):
        prim = cylinder(1.0, 1.0, 8, "M_Wall")
        min_y = min(v[1] for v in prim.verts)
        self.assertEqual(sum(1 for v in prim.verts if abs(v[1] - min_y) < 1e-9), 4)  # an edge, not a corner

    def test_closed_primitives_point_outwards(self):
        prims = [
            lathe([(0.0, 0.0), (1.0, 0.5), (0.5, 1.0), (0.0, 1.5)], 7, "M_Wall"),
            cylinder(1.0, 2.0, 8, "M_Wall", radius_top=0.5, bevel=0.1),
            torus(1.0, 0.2, 8, 4, "M_Wall"),
            sphere(1.0, 6, 4, "M_Wall"),
            prism([(0, 0), (0, 1), (1, 1), (1, 0)], 0.5, "M_Wall"),  # clockwise input is fixed up
        ]
        for prim in prims:
            self.assertGreater(volume(prim), 0)

    def test_rotation_keeps_volume(self):
        m = Mesh()
        part = m.add(box(1, 2, 3, "M_Wall"), rot=(0.3, -1.1, 2.0), loc=(5, 5, 5))
        self.assertAlmostEqual(m.part_volume(part), 6.0, places=6)


class AssetTests(unittest.TestCase):
    def test_pivot_and_parent(self):
        a = Asset("T")
        a.part("Body").add(box(1, 1, 1, "M_Wall"), loc=(0, 0, 0.5))
        a.part("Rotor", pivot=(0, 0, 1)).add(box(0.2, 0.2, 0.2, "M_Metal"), loc=(0, 0, 1))
        a.empty("Hinge", (0, 0, 2), parent="Rotor")
        rotor = a.get("Rotor")
        self.assertAlmostEqual(min(v[2] for v in rotor.local_verts()), -0.1)
        with self.assertRaises(ValueError):
            a.empty("Bad", (0, 0, 0), parent="Missing")


class SeedTests(unittest.TestCase):
    def test_reference_values_are_stable(self):
        # Changing this breaks reproducibility of every existing batch!
        self.assertEqual(model_seed(42, "crate", 0), 691206113)

    def test_seed_range(self):
        for i in range(200):
            self.assertLessEqual(model_seed(i, "crate", i), MAX_SEED)

    def test_parse_seed(self):
        self.assertEqual(parse_seed("17"), 17)
        self.assertEqual(parse_seed("level-3"), parse_seed("level-3"))
        self.assertNotEqual(parse_seed("level-3"), parse_seed("level-4"))


class ModelTests(unittest.TestCase):
    def test_registry(self):
        self.assertGreaterEqual(len(model_types()), 18)
        for entry in REGISTRY.values():
            self.assertTrue(entry.description)
            self.assertIn(entry.pivot, ("floor", "top", "center", "wall"))
        self.assertEqual(asset_name("server_rack", 3, "Gen_"), "Gen_ServerRack_003")

    def test_all_models_are_valid(self):
        for model_type in model_types():
            pivot = REGISTRY[model_type].pivot
            for seed in range(SEEDS_PER_TYPE):
                with self.subTest(model=model_type, seed=seed):
                    asset = generate_asset(model_type, seed)
                    names = [o.name for o in asset.objects]
                    self.assertEqual(len(names), len(set(names)))
                    self.assertTrue(asset.meshes())
                    for obj in asset.meshes():
                        mesh = obj.mesh
                        self.assertGreater(len(mesh.faces), 0, obj.name)
                        self.assertEqual(len(mesh.faces), len(mesh.roles))
                        self.assertTrue(set(mesh.roles) <= set(MATERIALS))
                        for v in mesh.verts:
                            self.assertTrue(all(math.isfinite(c) for c in v))
                        for face in mesh.faces:
                            self.assertGreaterEqual(len(face), 3)
                            self.assertEqual(len(set(face)), len(face))
                        for part in mesh.parts:  # closed parts must have outward normals
                            if part.closed:
                                self.assertGreater(mesh.part_volume(part), 0, f"{obj.name}/{part.name}")
                    (x0, y0, z0), (x1, y1, z1) = asset.bbox()
                    self.assertLess(max(x1 - x0, y1 - y0, z1 - z0), 8.0)
                    self.assertLess(asset.stats()["triangles"], 6000)
                    # pivot conventions of the game
                    if pivot == "floor":
                        self.assertAlmostEqual(z0, 0.0, places=9)
                        self.assertTrue(x0 <= 0 <= x1 and y0 <= 0 <= y1)
                    elif pivot == "center":
                        for lo, hi in ((x0, x1), (y0, y1), (z0, z1)):
                            self.assertAlmostEqual(lo + hi, 0.0, places=9)
                    elif pivot == "top":
                        self.assertLess(z0, 0.0)
                    elif pivot == "wall":
                        self.assertGreater(z0, 0.0)

    def test_moving_parts_have_pivots_inside(self):
        for model_type in model_types():
            for seed in range(SEEDS_PER_TYPE):
                for obj in generate_asset(model_type, seed).meshes():
                    if obj.name in ("Rotor", "Wheel", "Panel", "Panel_B"):
                        # pivot on (or within 5 cm of) the part - e.g. an off-axis beacon reflector
                        lo, hi = obj.mesh.bbox()
                        for i in range(3):
                            self.assertTrue(lo[i] - 0.05 <= obj.pivot[i] <= hi[i] + 0.05,
                                            f"{model_type} {seed} {obj.name}")

    def test_doors_have_game_part_names(self):
        for seed in range(20):
            names = {o.name for o in generate_asset("door", seed).objects}
            self.assertTrue({"Frame_Left", "Frame_Right", "Frame_Top", "StatusLight_Front", "StatusLight_Back",
                             "Panel"} <= names)

    def test_models_are_deterministic(self):
        for model_type in model_types():
            a, b = generate_asset(model_type, 99), generate_asset(model_type, 99)
            for oa, ob in zip(a.objects, b.objects):
                self.assertEqual(oa.pivot, ob.pivot)
                if oa.mesh:
                    self.assertEqual(oa.mesh.verts, ob.mesh.verts)
                    self.assertEqual(oa.mesh.faces, ob.mesh.faces)
                    self.assertEqual(oa.mesh.roles, ob.mesh.roles)

    def test_seeds_create_variation(self):
        for model_type in model_types():
            shapes = {tuple(generate_asset(model_type, s).stats()["dimensions_m"]) for s in range(6)}
            self.assertGreater(len(shapes), 1, model_type)

    def test_scale(self):
        a = generate_asset("crate", 1).stats()["dimensions_m"]
        b = generate_asset("crate", 1, scale=2.0).stats()["dimensions_m"]
        for da, db in zip(a, b):
            self.assertAlmostEqual(db, da * 2.0, places=3)

    def test_reference_asset(self):
        asset = generate_asset("crate", 123)
        self.assertEqual(asset.stats()["triangles"], 348)
        self.assertAlmostEqual(asset.objects[0].mesh.verts[0][0], -0.4157090796552833, places=12)


if __name__ == "__main__":
    unittest.main()
