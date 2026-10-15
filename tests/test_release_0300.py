"""cubegen 0.30.0 "Lattice": QA cache, paint zones, effect data, voxel shape, atlas occupancy field."""

import copy
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

try:
    import numpy as np
except ImportError:  # the numpy group of tools/run_tests.py runs these with Blender's Python
    np = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from cubegen import effects, shapes, zones  # noqa: E402
from cubegen.blender import find_blender  # noqa: E402
from cubegen.cache import Store  # noqa: E402
from cubegen.contract import (CONTRACT, CONTRACT_VERSION, EFFECTS, ZONES, check_sidecar, contract_for,  # noqa: E402
                              root_keys, texture_keys)
from cubegen.imagemagick import find_imagemagick  # noqa: E402
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


class DerivedShapeTest(unittest.TestCase):
    """--shape voxel | facet | holes: derived from the finished model, always inside it."""

    FORMS = (("voxel", 30), ("facet", 100), ("holes", 20))

    def test_smooth_is_the_default_and_changes_nothing(self):
        self.assertEqual(Style().shape, "smooth")
        for t in ("crate", "console"):
            self.assertEqual(generate_asset(t, 5).digest(), generate_asset(t, 5, style=Style(shape="smooth")).digest())

    def test_shape_needs_an_intact_model(self):
        with self.assertRaises(ValueError):
            Style(shape="voxel", damage="damaged").validate()
        with self.assertRaises(ValueError):
            Style(shape="cone").validate()

    def test_a_derived_form_lies_inside_the_smooth_one_and_keeps_colliders_and_parts(self):
        for form, at_least in self.FORMS:
            changed = 0
            for t in model_types():
                e = entry(t)
                smooth = generate_asset(t, 42)
                derived = generate_asset(t, 42, style=Style(shape=form))
                label = f"{form} {t}"
                self.assertEqual([o.name for o in smooth.objects], [o.name for o in derived.objects], label)
                self.assertEqual(smooth.behaviours, derived.behaviours, label)
                self.assertEqual([(c.kind, c.part, c.center, c.size) for c in smooth.colliders],
                                 [(c.kind, c.part, c.center, c.size) for c in derived.colliders], label)
                if shapes.META_KEY not in derived.meta:
                    self.assertEqual(smooth.digest(), derived.digest(), label)  # nothing fit: the model is unchanged
                    continue
                changed += 1
                self.assertEqual(derived.meta[shapes.META_KEY]["form"], form)
                (lo, hi), (dlo, dhi) = smooth.bbox(), derived.bbox()
                for i in range(3):  # (the flush-detail pass lifts a coplanar detail by DECAL_OFFSET, 2 mm, afterwards)
                    self.assertGreaterEqual(dlo[i], lo[i] - 2.5e-3, label)
                    self.assertLessEqual(dhi[i], hi[i] + 2.5e-3, label)
                self.assertLessEqual(len(uncovered_geometry(derived, e.pivot)), len(uncovered_geometry(smooth, e.pivot)),
                                     label)
                cs, cd = check(smooth, e.category, e.pivot), check(derived, e.category, e.pivot)
                self.assertFalse(cd["z_fighting"] and not cs["z_fighting"], label)
                if cs["triangles"] <= cs["budget"]:
                    self.assertLessEqual(cd["triangles"], cd["budget"], label)  # a form never breaks the budget
            self.assertGreater(changed, at_least, form)

    def test_the_hull_of_a_cube_and_the_facets_of_a_cylinder(self):
        corners = [(x, y, z) for x in (0.0, 1.0) for y in (0.0, 1.0) for z in (0.0, 1.0)]
        tris = shapes._hull(corners + [(0.5, 0.5, 0.5)])
        self.assertEqual(len(tris), 12)
        self.assertTrue(all(i < 8 for t in tris for i in t))  # the centre point (index 8) is inside: no face uses it
        for a, b, c in tris:  # outward winding: every face's normal points away from the centre
            n = shapes.v_cross(shapes.v_sub(corners[b], corners[a]), shapes.v_sub(corners[c], corners[a]))
            self.assertGreater(shapes.v_dot(n, shapes.v_sub(corners[a], (0.5, 0.5, 0.5))), 0)
        self.assertIsNone(shapes._hull([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 1.0, 0.0)]))
        asset = generate_asset("canister", 42)
        before = asset.stats()["triangles"]
        info = shapes.facet(asset)
        self.assertGreater(info["parts"], 0)
        self.assertLess(asset.stats()["triangles"], before)

    def test_plates_get_holes_that_a_collider_box_still_fits(self):
        asset = generate_asset("cargo_container", 42)
        before = asset.stats()["triangles"]
        info = shapes.perforate(asset, entry("cargo_container").pivot, budget=10 ** 6)
        self.assertGreater(info["parts"], 0)
        self.assertGreater(asset.stats()["triangles"], before)
        capped = generate_asset("cargo_container", 42)
        shapes.perforate(capped, "floor", budget=before + 10)
        self.assertLessEqual(capped.stats()["triangles"], before + 10)
        self.assertLessEqual(shapes.HOLE_MAX, 0.15)

    def test_neighbouring_faces_of_one_role_are_merged(self):
        cells = {(x, y, z) for x in range(4) for y in range(3) for z in range(2)}
        roles = {(a, s): "M_Wall" for a in range(3) for s in (1, -1)}
        quads = shapes._merged_faces(cells, roles, 0.1)
        self.assertEqual(len(quads), 6)  # a 4 x 3 x 2 block: one rectangle per side, not 2*(12+8+6) cells

    def test_the_cli_knows_the_option(self):
        from cubegen.cli import catalog_data

        self.assertIn("shape", catalog_data()["options"])


def sidecar_with(asset_type="hologram", seed=3):
    from cubegen.pipeline import rig_data

    asset = generate_asset(asset_type, seed)
    rig = rig_data(asset, {"type": asset_type, "seed": seed, "style": {}}, 1)
    rig["effects"] = effects.effects_of(asset)
    return rig


class ContractVersion4Test(unittest.TestCase):
    def test_version_4_adds_zones_and_effects_and_leaves_version_3_alone(self):
        self.assertEqual(CONTRACT_VERSION, 4)
        self.assertEqual(sorted(CONTRACT["history"]), ["1", "2", "3", "4"])
        self.assertIn("effects", root_keys(4))
        self.assertNotIn("effects", root_keys(3))
        self.assertIn("zones", texture_keys(4))
        self.assertNotIn("zones", texture_keys(3))
        old = contract_for(3)
        self.assertNotIn("zones", old)
        self.assertNotIn("effects", old)
        self.assertNotIn("4", old["history"])
        self.assertNotIn("effects", old["root"]["since"])

    def test_the_contract_sections_equal_the_code(self):
        self.assertEqual({k: v for k, v in EFFECTS["kinds"].items()}, {k: v for k, v in effects.KIND_PARAMS.items()
                                                                       if k in set(effects.KINDS.values())})
        self.assertEqual(ZONES["max_slots"], zones.MAX_SLOTS)
        self.assertEqual(ZONES["channels"], list(zones.CHANNELS))
        for name in effects.KINDS:
            params = effects.params_of(name)
            self.assertTrue(set(params) <= set(effects.KIND_PARAMS[effects.KINDS[name]]), name)

    def test_effects_in_a_sidecar_pass_in_version_4_and_are_unknown_before(self):
        rig = sidecar_with()
        self.assertTrue(rig["effects"])
        self.assertEqual(check_sidecar(rig)[0], [])
        errors = check_sidecar(rig, version=3)[0]
        self.assertEqual(errors, ["root: unknown key 'effects' (contract version 4, this importer reads version 3)"])
        without = {k: v for k, v in rig.items() if k != "effects"}
        self.assertEqual(check_sidecar(without, version=3)[0], [])  # a sidecar without them reads as before

    def test_effect_rules(self):
        def errors(change):
            rig = sidecar_with()
            change(rig["effects"][0])
            return check_sidecar(rig)[0]

        self.assertTrue(any("unknown key 'colour'" in e for e in errors(lambda e: e.update(colour=1))))
        self.assertTrue(any("no parameter of kind" in e for e in errors(lambda e: e["params"].update(wobble=1.0))))
        self.assertTrue(any("expected a number" in e for e in errors(lambda e: e["params"].update(
            {next(iter(e["params"])): "x"}))))
        self.assertTrue(any(".kind:" in e for e in errors(lambda e: e.update(kind="plasma"))))
        self.assertTrue(any(".color:" in e for e in errors(lambda e: e.update(color=[2, 0, 0]))))
        rig = sidecar_with()
        rig["effects"] = rig["effects"] + rig["effects"][:1]
        self.assertTrue(any("twice" in e for e in check_sidecar(rig)[0]))
        rig["effects"] = []
        self.assertTrue(any("non-empty" in e for e in check_sidecar(rig)[0]))

    def test_zone_rules(self):
        from tests.test_release_0240 import neutral_rig

        def rig_with(zones_value):
            rig = neutral_rig()
            rig["textures"]["zones"] = zones_value
            return rig

        slot = {"channel": "r", "zone": "Frame", "objects": ["Frame_Left"]}
        good = {"map": "Textures/MTN_Crate_000_Zones.png", "slots": [slot]}
        self.assertEqual(check_sidecar(rig_with(good))[0], [])
        errors = check_sidecar(rig_with(good), version=3)[0]
        self.assertIn("textures: unknown key 'zones' (contract version 4, this importer reads version 3)", errors)
        self.assertTrue(check_sidecar(rig_with({"map": good["map"], "slots": []}))[0])
        self.assertTrue(check_sidecar(rig_with({"map": good["map"], "slots": [dict(slot, channel="g")]}))[0])
        self.assertTrue(check_sidecar(rig_with({"map": good["map"], "slots": [slot, slot]}))[0])
        self.assertTrue(check_sidecar(rig_with({"map": "Textures/MTN_Crate_000_W0.png", "slots": [slot]}))[0])
        self.assertTrue(check_sidecar(rig_with({"slots": [slot]}))[0])
        rig = rig_with(good)
        del rig["textures"]["neutral"], rig["textures"]["weight_layout"], rig["paint"]
        self.assertTrue(any("needs the neutral maps" in e for e in check_sidecar(rig)[0]))

    def test_a_default_run_writes_effects_and_contract_3_does_not(self):
        from cubegen.cli import main

        for contract, expected in ((None, True), (3, False)):
            with tempfile.TemporaryDirectory() as out, redirect_stdout(io.StringIO()):
                args = ["generate", "--seed", "5", "--pick", "hologram:0,crate:0", "--no-blender", "--out", out]
                self.assertEqual(main(args + (["--contract", str(contract)] if contract else [])), 0)
                with open(os.path.join(out, "models", "Hologram_000.cubegen.json"), "r", encoding="utf-8") as fh:
                    rig = json.load(fh)
                self.assertEqual("effects" in rig, expected)
                if expected:
                    self.assertIn("M_Hologram", [e["material"] for e in rig["effects"]])
                    self.assertEqual(check_sidecar(rig)[0], [])
                with open(os.path.join(out, "manifest.json"), "r", encoding="utf-8") as fh:
                    manifest = json.load(fh)
                self.assertTrue(manifest["models"][0]["effects"])  # the manifest keeps them for every version


@unittest.skipUnless(np is not None, "numpy required (Blender's Python has it)")
class ZoneMapTest(unittest.TestCase):
    def test_slots_follow_the_part_names(self):
        slots = zones.paint_zones(["Body", "Frame_Left", "Frame_Right", "Panel_Outer", "Rotor_2", "Wheel_1"])
        self.assertEqual([(s["channel"], s["zone"]) for s in slots], [("r", "Frame"), ("g", "Panel"), ("b", "Rotor")])
        self.assertEqual(slots[0]["objects"], ["Frame_Left", "Frame_Right"])
        self.assertEqual(zones.paint_zones(["Body"]), [])
        self.assertEqual(zones.paint_zones(["Body", "Body_LOD0", "Body.001"]), [])

    def test_the_map_has_hard_weights_a_margin_and_no_overlap(self):
        tris = [(0, ((0.1, 0.1), (0.4, 0.1), (0.1, 0.4))), (1, ((0.5, 0.5), (0.9, 0.5), (0.5, 0.9))),
                (-1, ((0.1, 0.6), (0.3, 0.6), (0.1, 0.9)))]
        a = zones.zone_map(tris, 64, margin=4)
        self.assertEqual(a.shape, (64, 64, 4))
        self.assertEqual(set(np.unique(a[..., :3])), {0, 255})
        self.assertEqual(int((a[..., :3].max(axis=2) > 0).sum() > 0), 1)
        self.assertEqual(int(((a[..., 0] > 0) & (a[..., 1] > 0)).sum()), 0)  # a texel is in one zone only
        self.assertTrue((a[..., 3] == 255).all())
        plain = zones.zone_map(tris, 64, margin=0)
        self.assertGreater(int((a[..., 0] > 0).sum()), int((plain[..., 0] > 0).sum()))  # the margin grows it
        self.assertEqual(a.tobytes(), zones.zone_map(tris, 64, margin=4).tobytes())  # deterministic
        self.assertEqual(int((a[8:20, 40:60, :3] > 0).sum() == 0), 1)  # the plain face's neighbourhood stays 0 in zones


@unittest.skipUnless(find_blender() is not None and find_imagemagick() is not None and np is not None,
                     "Blender, ImageMagick and numpy required")
class ZoneRunTest(unittest.TestCase):
    def test_a_paint_run_writes_the_zone_map_and_the_sidecar_slots(self):
        from cubegen.cli import main
        from cubegen.contract import check_export

        with tempfile.TemporaryDirectory() as out:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["generate", "--seed", "7", "--pick", "breakable_platform:0,crate:0",
                                       "--paint", "dark", "--texture-size", "64", "--no-render", "--no-blend",
                                       "--bake-device", "cpu", "--out", out]), 0)
            with open(os.path.join(out, "models", "BreakablePlatform_000.cubegen.json"), "r", encoding="utf-8") as fh:
                rig = json.load(fh)
            tz = rig["textures"]["zones"]
            self.assertEqual([s["zone"] for s in tz["slots"]], ["Frame", "Tile"])
            from cubegen import neutral

            image = neutral.read_png(os.path.join(out, "models", tz["map"]))
            self.assertEqual(image.shape, (64, 64, 4))
            self.assertGreater(int((image[..., 0] > 0).sum()), 0)
            self.assertGreater(int((image[..., 1] > 0).sum()), 0)
            self.assertEqual(int(((image[..., 0] > 0) & (image[..., 1] > 0)).sum()), 0)
            with open(os.path.join(out, "models", "Crate_000.cubegen.json"), "r", encoding="utf-8") as fh:
                self.assertNotIn("zones", json.load(fh)["textures"])  # one zone: no map
            self.assertEqual(sum(len(v["errors"]) for v in check_export(os.path.join(out, "models")).values()), 0)
            with open(os.path.join(out, "manifest.json"), "r", encoding="utf-8") as fh:
                manifest = json.load(fh)
            self.assertEqual(manifest["models"][0]["zone_map"], "models/" + tz["map"])


if __name__ == "__main__":
    unittest.main()
