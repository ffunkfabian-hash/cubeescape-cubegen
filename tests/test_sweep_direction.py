"""Signed symmetric sweeps preserve geometry, anchors and colliders."""
import math
import unittest
from cubegen.models import generate_asset

class SweepDirectionTests(unittest.TestCase):
    def test_signed_sweeps_mirror_the_start_and_keep_the_same_range(self):
        for kind, target in (("camera", "Rotor"), ("turret", "Turret")):
            with self.subTest(kind=kind):
                models = [generate_asset(kind, 42, params={"speed": speed, "sweep": 90}) for speed in (30, -30)]
                for asset, speed in zip(models, (30, -30)):
                    recipe = next(b for b in asset.behaviours if b["script"] == "Rotator" and b["parts"]["target"] == target)
                    self.assertEqual(recipe["fields"]["speed"], speed)
                    self.assertEqual(asset.meta["sweep_deg"], [-45, 45])
                # Undo the signed baked start: both complete target meshes must coincide.
                verts = []
                for asset, angle in zip(models, (-math.pi/4, math.pi/4)):
                    obj = next(o for o in asset.objects if o.name == target)
                    c, s = math.cos(angle), math.sin(angle)
                    verts.append([(round(c*(x-obj.pivot[0])-s*(y-obj.pivot[1]), 6),
                                   round(s*(x-obj.pivot[0])+c*(y-obj.pivot[1]), 6), round(z-obj.pivot[2], 6))
                                  for x,y,z in obj.mesh.verts])
                self.assertEqual(verts[0], verts[1])

    def test_explicit_zero_is_stationary_and_generation_one_keeps_its_legacy_sweep(self):
        from cubegen.params import Style
        for kind in ("camera", "turret"):
            asset = generate_asset(kind, 42, params={"speed": 0, "sweep": 90})
            recipe = next(b for b in asset.behaviours if b["script"] == "Rotator")
            self.assertEqual(recipe["fields"]["speed"], 0)
            legacy = generate_asset(kind, 42, params={"speed": 0, "sweep": 90}, style=Style(generation=1))
            self.assertEqual(next(b for b in legacy.behaviours if b["script"] == "Rotator")["fields"]["speed"], 30)

    def test_generation_three_pressure_plates_export_fixed_and_moving_solid_surfaces(self):
        from cubegen.params import Style
        for shape in ("square", "round"):
            asset = generate_asset("pressure_plate", 42, params={"shape": shape})
            self.assertEqual({c.part for c in asset.colliders}, {"Body", "Plate"})
            self.assertTrue(all(c.kind == "mesh" and c.convex for c in asset.colliders))
            legacy = generate_asset("pressure_plate", 42, params={"shape": shape}, style=Style(generation=1))
            self.assertFalse(legacy.colliders)

    def test_generation_three_sweeping_models_have_fixed_and_nested_moving_collision(self):
        from cubegen.params import Style
        for kind, parts in (("camera", {"Body", "Rotor"}), ("turret", {"Body", "Turret", "Gun"})):
            for speed in (30, -30):
                asset = generate_asset(kind, 42, params={"speed": speed, "sweep": 90})
                self.assertEqual({c.part for c in asset.colliders}, parts)
                self.assertTrue(all(c.kind == "mesh" and c.convex for c in asset.colliders))
            self.assertFalse(generate_asset(kind, 42, style=Style(generation=1)).colliders)
