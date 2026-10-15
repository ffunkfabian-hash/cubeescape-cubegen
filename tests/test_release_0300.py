"""cubegen 0.30.0 "Lattice": QA cache, paint zones, effect data, voxel shape, atlas occupancy field."""

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from cubegen import effects, shapes, zones  # noqa: E402
from cubegen.cache import Store  # noqa: E402
from cubegen.materials import KEEP_OWN  # noqa: E402
from cubegen.models import REGISTRY, generate_asset, model_types  # noqa: E402
from cubegen.params import Style  # noqa: E402
from cubegen.quality import check, check_cached, uncovered_geometry  # noqa: E402


def entry(t):
    return REGISTRY[t]


class QaCacheTest(unittest.TestCase):
    def test_a_hit_equals_the_computed_result_and_the_key_follows_the_asset(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            asset = generate_asset("crate", 3)
            e = entry("crate")
            first = check_cached(asset, e.category, e.pivot, store=store)
            self.assertEqual(sum(len(f) for _, _, f in os.walk(store.entries)), 1)
            second = check_cached(asset, e.category, e.pivot, store=store)
            self.assertEqual(first, second)
            self.assertEqual(second, check_cached(asset, e.category, e.pivot, store=None))
            self.assertEqual(first["severity"], check(asset, e.category, e.pivot)["severity"])
            check_cached(generate_asset("crate", 4), e.category, e.pivot, store=store)  # another asset: another key
            self.assertEqual(sum(len(f) for _, _, f in os.walk(store.entries)), 2)

    def test_the_checking_code_is_part_of_the_key(self):
        from cubegen import quality

        self.assertEqual(len(quality.qa_code()), 64)
        for module in ("quality", "families", "collision", "palette"):
            self.assertIn(module, quality.QA_MODULES)


class ZonesTest(unittest.TestCase):
    def test_names_fold_into_zones(self):
        for name, zone in (("Frame_Left", "Frame"), ("Panel_Outer_B", "Panel"), ("Rotor_2", "Rotor"),
                           ("03_AngleProfile", "AngleProfile"), ("Body", "Body"), ("Left", "Left")):
            self.assertEqual(zones.zone_name(name), zone)

    def test_the_table_lists_painted_materials_per_zone(self):
        asset = generate_asset("breakable_platform", 42)
        table = {z["zone"]: z for z in zones.zone_table(asset)}
        self.assertIn("Frame", table)
        self.assertEqual(sorted(o for z in table.values() for o in z["objects"]),
                         sorted(o.name for o in asset.meshes()))
        self.assertGreater(zones.paintable_zones(asset), 1)


class EffectsTest(unittest.TestCase):
    def test_every_own_material_has_a_kind_and_the_values_of_the_material(self):
        self.assertEqual(set(effects.KINDS), set(KEEP_OWN))
        self.assertEqual(set(effects.ROLES), set(KEEP_OWN))
        table = {e["material"]: e for e in effects.effects_table()}
        self.assertEqual(set(table), set(KEEP_OWN))
        from cubegen.materials import MATERIALS

        self.assertEqual(table["M_GlowCyan"]["emission"], MATERIALS["M_GlowCyan"][3])
        self.assertEqual(table["M_Glass"]["kind"], "glass")

    def test_a_model_lists_only_what_it_uses(self):
        asset = generate_asset("crate", 3)
        used = {r for o in asset.meshes() for r in o.mesh.roles}
        self.assertEqual({e["material"] for e in effects.effects_of(asset)}, used & set(KEEP_OWN))


class VoxelShapeTest(unittest.TestCase):
    def test_smooth_is_the_default_and_changes_nothing(self):
        self.assertEqual(Style().shape, "smooth")
        for t in ("crate", "console"):
            self.assertEqual(generate_asset(t, 5).digest(), generate_asset(t, 5, style=Style(shape="smooth")).digest())

    def test_shape_needs_an_intact_model(self):
        with self.assertRaises(ValueError):
            Style(shape="voxel", damage="damaged").validate()
        with self.assertRaises(ValueError):
            Style(shape="cone").validate()

    def test_a_voxel_form_lies_inside_the_smooth_one_and_keeps_colliders_and_parts(self):
        changed = 0
        for t in model_types():
            smooth = generate_asset(t, 42)
            voxel = generate_asset(t, 42, style=Style(shape="voxel"))
            self.assertEqual([o.name for o in smooth.objects], [o.name for o in voxel.objects], t)
            self.assertEqual(smooth.behaviours, voxel.behaviours, t)
            self.assertEqual([(c.kind, c.part, c.center, c.size) for c in smooth.colliders],
                             [(c.kind, c.part, c.center, c.size) for c in voxel.colliders], t)
            if "shape" not in voxel.meta:
                self.assertEqual(smooth.digest(), voxel.digest(), t)  # nothing solid enough: the model is unchanged
                continue
            changed += 1
            (lo, hi), (vlo, vhi) = smooth.bbox(), voxel.bbox()
            for i in range(3):
                self.assertGreaterEqual(vlo[i], lo[i] - 1e-5, t)
                self.assertLessEqual(vhi[i], hi[i] + 1e-5, t)
            self.assertLessEqual(len(uncovered_geometry(voxel, entry(t).pivot)),
                                 len(uncovered_geometry(smooth, entry(t).pivot)), t)
            self.assertFalse(check(voxel, entry(t).category, entry(t).pivot)["z_fighting"] and
                             not check(smooth, entry(t).category, entry(t).pivot)["z_fighting"], t)
        self.assertGreater(changed, 30)

    def test_neighbouring_faces_of_one_role_are_merged(self):
        cells = {(x, y, z) for x in range(4) for y in range(3) for z in range(2)}
        roles = {(a, s): "M_Wall" for a in range(3) for s in (1, -1)}
        quads = shapes._merged_faces(cells, roles, 0.1)
        self.assertEqual(len(quads), 6)  # a 4 x 3 x 2 block: one rectangle per side, not 2*(12+8+6) cells

    def test_the_cli_knows_the_option(self):
        from cubegen.cli import catalog_data

        self.assertIn("shape", catalog_data()["options"])


if __name__ == "__main__":
    unittest.main()
