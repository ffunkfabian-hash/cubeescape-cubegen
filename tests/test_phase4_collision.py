"""Collision regressions discovered during the Cube Escape phase-four integration."""
import unittest
from cubegen.models import generate_asset
from cubegen.params import Style
from cubegen.families import collision_boxes
from cubegen.quality import uncovered_geometry
from cubegen.quality import check


class PhaseFourCollisionTests(unittest.TestCase):
    def test_static_models_have_authored_shapes_or_exact_mesh_collision(self):
        from cubegen.models import model_types
        for kind in model_types():
            for seed in (0, 42):
                with self.subTest(kind=kind, seed=seed):
                    asset = generate_asset(kind, seed, style=Style(generation=3))
                    if not asset.behaviours:
                        self.assertTrue(asset.colliders)

    def test_static_debris_keeps_empty_space_inside_its_overall_bounds(self):
        from cubegen.families import MeshCollision
        for kind in ("crate_pile", "debris", "rubble_pile"):
            asset = generate_asset(kind, 42)
            actual = [MeshCollision(o.mesh, o.name) for o in asset.meshes()]
            lo, hi = asset.bbox()
            empty = []
            for x in range(1, 10):
                for y in range(1, 10):
                    point = (lo[0]+(hi[0]-lo[0])*x/10, lo[1]+(hi[1]-lo[1])*y/10, (lo[2]+hi[2])/2)
                    if not any(shape.contains(point) for shape in actual):
                        empty.append(point)
            self.assertTrue(empty, kind)
            imported = collision_boxes(asset, kind)
            self.assertTrue(all(not any(shape.contains(p) for shape in imported) for p in empty), kind)

    def test_destroyed_generation_three_uses_exact_fixed_meshes_and_no_envelope(self):
        from cubegen.models import model_types
        for kind in model_types():
            for seed in (0, 42):
                with self.subTest(kind=kind, seed=seed):
                    asset = generate_asset(kind, seed, style=Style(generation=3, damage="destroyed"))
                    self.assertFalse(asset.behaviours)
                    physical = {o.name for o in asset.meshes() if o.name != "Wear"}
                    self.assertEqual({c.part for c in asset.colliders}, physical)
                    self.assertTrue(all(c.kind == "mesh" and not c.convex for c in asset.colliders))

    def test_destroyed_old_generations_keep_their_historical_outputs(self):
        for kind in ("wall", "crate", "safe", "cage", "stairs", "steam_vent"):
            for generation in (1, 2):
                asset = generate_asset(kind, 42, style=Style(generation=generation, damage="destroyed"))
                self.assertFalse(asset.behaviours)
                self.assertFalse(asset.colliders)

    def test_gameplay_fallback_keeps_fixed_openings_exact_and_moving_parts_convex(self):
        for kind in ("safe", "fuse_box", "valve", "fan", "robot_arm", "conveyor"):
            asset = generate_asset(kind, 42)
            self.assertTrue(asset.colliders, kind)
            body = next(c for c in asset.colliders if c.part == "Body" or c.part == "Base")
            self.assertEqual(body.kind, "mesh")
            self.assertFalse(body.convex, kind)  # a convex hull would close a safe or a cage
            for behaviour in asset.behaviours:
                if behaviour["script"] in ("Rotatable", "Rotator"):
                    target = behaviour["parts"]["target"]
                    self.assertTrue(next(c for c in asset.colliders if c.part == target).convex, kind)

    def test_fallback_preserves_authored_shapes_old_generations_and_pickup_triggers(self):
        from cubegen.collision import complete_gameplay_collision
        for kind in ("door", "crusher", "phase_platform", "portal_frame", "fluid_basin"):
            asset = generate_asset(kind, 42)
            before = asset.digest(); complete_gameplay_collision(asset)
            self.assertEqual(before, asset.digest(), kind)
        for kind in ("safe", "valve", "fan"):
            for generation in (1, 2):
                self.assertFalse(generate_asset(kind, 42, style=Style(generation=generation)).colliders)
        for kind in ("item", "keycard", "tool"):
            self.assertFalse(generate_asset(kind, 42).colliders)

    def test_gameplay_audit_does_not_invent_a_static_envelope(self):
        asset = generate_asset("steam_vent", 42, params={"style": "pipe", "size": 1.5, "valve": False})
        asset.colliders.clear()
        self.assertTrue(collision_boxes(asset, "steam_vent", gameplay_import=False))  # historical layout estimate
        self.assertFalse(collision_boxes(asset, "steam_vent"))
        self.assertFalse(collision_boxes(asset, "steam_vent", gameplay_import=True))
        self.assertTrue(uncovered_geometry(asset, gameplay_import=True))
        self.assertTrue(check(asset, "puzzle")["errors"])

    def test_a_fixed_mesh_opening_stays_empty_in_the_collision_checker(self):
        from cubegen.asset import Asset
        from cubegen.models.common import cube
        asset = Asset("open frame")
        body = asset.part("Body")
        cube(body, (.2, .2, 2), (-1,0,1), "M_Metal")
        cube(body, (.2, .2, 2), (1,0,1), "M_Metal")
        asset.mesh_collider("Body", convex=False)
        shape = collision_boxes(asset, "")[0]
        self.assertFalse(shape.contains((0,0,1)))
        self.assertTrue(shape.contains((1,0,1)))
        self.assertFalse(shape.moved((0,2,0)).contains((0,2,1)))

    def test_phase_four_models_cover_solid_geometry_with_real_import_collision(self):
        for kind in ("crusher", "saw_blade", "steam_vent", "shock_plate", "spike_trap",
                     "phase_platform", "breakable_platform", "fluid_basin", "portal_frame"):
            for seed in range(10):
                with self.subTest(kind=kind, seed=seed):
                    asset = generate_asset(kind, seed)
                    from cubegen.models import REGISTRY
                    self.assertFalse(uncovered_geometry(asset, REGISTRY[kind].pivot, gameplay_import=True))

    def test_steam_vents_have_fixed_and_optional_wheel_collision(self):
        for shape in ("grate", "pipe"):
            for valve in (False, True):
                with self.subTest(shape=shape, valve=valve):
                    asset = generate_asset("steam_vent", 42, params={"style": shape, "valve": valve})
                    self.assertEqual({c.part for c in asset.colliders}, {"Body", "Wheel"} if valve else {"Body"})
                    self.assertTrue(all(c.kind == "mesh" and c.convex for c in asset.colliders))
                    for generation in (1, 2):
                        old = generate_asset("steam_vent", 42, params={"style": shape, "valve": valve}, style=Style(generation=generation))
                        self.assertFalse(old.colliders)
