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
from cubegen.seeds import MAX_SEED, StableRandom, model_seed, parse_seed, sub_rng  # noqa: E402

SEEDS_PER_TYPE = 40
MOVING_PARTS = ("Rotor", "Wheel", "Panel", "Panel_B", "Lever", "Fitting", "Mirror", "Plate", "Deck", "Head",
                "Turret", "Arm_Lower", "Arm_Upper", "Gripper", "Button", "Prism", "Field", "Plug", "Gun", "Grille",
                "Beam")
MOVING_PREFIXES = ("Rotor_", "Roller_", "Gear_", "Button_", "Leg_", "Dial_", "Tile_", "Switch_", "Pan_")
# fields every behaviour of a game script must carry (see docs/UNITY_INTEGRATION.md)
SCRIPT_FIELDS = {
    # upperFrame is optional (the Unity import accepts only Frame_Top there): bridges and spike traps have none
    "Door": ({"panels", "statusLights", "colliders"}, {"openOffset", "speed"}),
    "Machine": ({"body", "glow"}, {"needsPower"}),
    "Rotator": ({"target"}, {"axis", "speed"}),
    "Rotatable": ({"target", "glow"}, {"axis", "step", "speed", "target", "interactive"}),
    "SignalLight": ({"glow"}, {"mode"}),
    "SignalIndicator": ({"renderers"}, {"offMaterial", "onMaterial"}),
    "ItemPickup": ({"model"}, {"spin"}),
}


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

    def test_stable_random_matches_this_python(self):
        # StableRandom freezes CPython's algorithms; on the versions we support it must still agree with them
        import random

        for seed in (0, 1, 42, 691206113, "text"):
            a, b = StableRandom(seed), random.Random(seed)
            for n in range(300):
                self.assertEqual(a.uniform(-2, 3), b.uniform(-2, 3))
                self.assertEqual(a.randint(0, n), b.randint(0, n))
                self.assertEqual(a.randrange(n + 1), b.randrange(n + 1))
                self.assertEqual(a.randrange(-5, 50, 3), b.randrange(-5, 50, 3))
                seq = list(range(n % 30 + 1))
                self.assertEqual(a.choice(seq), b.choice(seq))
                self.assertEqual(a.sample(seq, len(seq) // 2), b.sample(seq, len(seq) // 2))
                self.assertEqual(a.sample(range(200), 7), b.sample(range(200), 7))
                self.assertEqual(a.choices(seq, k=3), b.choices(seq, k=3))
                self.assertEqual(a.choices(seq, weights=[i + 1 for i in seq], k=2),
                                 b.choices(seq, weights=[i + 1 for i in seq], k=2))
                x, y = list(seq), list(seq)
                a.shuffle(x)
                b.shuffle(y)
                self.assertEqual(x, y)
                self.assertEqual(a.random(), b.random())

    def test_sub_streams(self):
        self.assertEqual(sub_rng(5, "a").random(), sub_rng(5, "a").random())
        self.assertNotEqual(sub_rng(5, "a").random(), sub_rng(5, "b").random())
        self.assertNotEqual(sub_rng(5, "a").random(), sub_rng(6, "a").random())
        asset = generate_asset("crate", 77)
        self.assertEqual(asset.seed, 77)
        self.assertEqual(asset.sub("x").random(), sub_rng(77, "x").random())

    def test_parse_seed(self):
        self.assertEqual(parse_seed("17"), 17)
        self.assertEqual(parse_seed("level-3"), parse_seed("level-3"))
        self.assertNotEqual(parse_seed("level-3"), parse_seed("level-4"))


class ModelTests(unittest.TestCase):
    def test_registry(self):
        self.assertGreaterEqual(len(model_types()), 121)
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
                    if obj.name in MOVING_PARTS or obj.name.startswith(MOVING_PREFIXES):
                        # pivot on (or within 5 cm of) the part - e.g. an off-axis beacon reflector
                        lo, hi = obj.mesh.bbox()
                        for i in range(3):
                            self.assertTrue(lo[i] - 0.05 <= obj.pivot[i] <= hi[i] + 0.05,
                                            f"{model_type} {seed} {obj.name}")

    def test_status_parts_have_one_material(self):
        # the game swaps renderer.sharedMaterial (slot 0 only) on these parts
        status = ("Glow", "Indicator", "StatusLight_Front", "StatusLight_Back", "Screen", "Plate_Light")
        for model_type in model_types():
            for seed in range(SEEDS_PER_TYPE):
                for obj in generate_asset(model_type, seed).meshes():
                    if obj.name in status:
                        self.assertEqual(len(set(obj.mesh.roles)), 1, f"{model_type} {seed} {obj.name}")

    def test_door_offsets_match_game_recipes(self):
        from cubegen.models.environment import _door_offset
        self.assertEqual(_door_offset("sliding", 2.0, 2.6, None), [2.05, 0.0, 0.0])
        self.assertEqual(_door_offset("heavy", 3.0, 3.0, None), [0.0, -3.1, 0.0])
        self.assertEqual(_door_offset("security", 2.0, 2.6, None), [0.0, -2.7, 0.0])
        self.assertEqual(_door_offset("elevator", 2.4, 2.8, "x"), [1.25, 0.0, 0.0])
        self.assertEqual(_door_offset("airlock", 2.4, 2.8, "z"), [0.0, 1.45, 0.0])
        self.assertEqual(_door_offset("blast", 4.0, 3.4, None), [0.0, 3.5, 0.0])

    def test_behaviours(self):
        for seed in range(SEEDS_PER_TYPE):
            door = generate_asset("door", seed)
            self.assertEqual([b["script"] for b in door.behaviours], ["Door"])
            machine = generate_asset("machine", seed)
            scripts = {b["script"]: b for b in machine.behaviours}
            self.assertIn("Machine", scripts)
            self.assertEqual("Rotor" in scripts["Machine"]["parts"].values(), machine.get("Rotor") is not None)
        self.assertFalse(generate_asset("crate", 1).behaviours)  # static decoration
        scaled = generate_asset("door", 3, scale=2.0).behaviours[0]["fields"]["openOffset"]
        base = generate_asset("door", 3).behaviours[0]["fields"]["openOffset"]
        self.assertEqual(scaled, [round(c * 2, 4) for c in base])

    def test_behaviours_use_known_scripts_and_fields(self):
        for model_type in model_types():
            for seed in range(SEEDS_PER_TYPE):
                for b in generate_asset(model_type, seed).behaviours:
                    self.assertIn(b["script"], SCRIPT_FIELDS, model_type)
                    parts, fields = SCRIPT_FIELDS[b["script"]]
                    self.assertTrue(parts <= set(b["parts"]), f"{model_type} {b}")
                    self.assertTrue(fields <= set(b["fields"]), f"{model_type} {b}")
                    if "axis" in b["fields"]:
                        self.assertIn(b["fields"]["axis"], ("right", "up", "forward"))

    def test_puzzle_pieces(self):
        for seed in range(SEEDS_PER_TYPE):
            for t in ("socket", "chip_reader"):
                self.assertIsNotNone(generate_asset(t, seed).get("Slot"), t)
            fuse = generate_asset("fuse_box", seed)
            slots = [o for o in fuse.objects if o.name.startswith("Slot_")]
            self.assertEqual(len(slots), fuse.meta["slots"])
            self.assertTrue(all(o.is_empty for o in slots))
            fitting = generate_asset("pipe_fitting", seed)
            rot = next(b for b in fitting.behaviours if b["script"] == "Rotatable")
            self.assertEqual((rot["parts"]["target"], rot["fields"]["axis"], rot["fields"]["step"]),
                             ("Fitting", "up", 90))
            lift = generate_asset("lift", seed).behaviours[0]
            self.assertEqual(lift["parts"]["panels"], ["Deck"])
            self.assertGreater(lift["fields"]["openOffset"][1], 0)  # moves up (Unity Y)
            conveyor = generate_asset("conveyor", seed)
            rollers = [o.name for o in conveyor.objects if o.name.startswith("Roller_")]
            self.assertEqual(sorted(b["parts"]["target"] for b in conveyor.behaviours), sorted(rollers))

    def test_new_puzzle_mechanics(self):
        for seed in range(SEEDS_PER_TYPE):
            gears = generate_asset("gear_puzzle", seed)
            rotators = [b for b in gears.behaviours if b["script"] == "Rotator"]
            present = [o.name for o in gears.objects if o.name.startswith("Gear_")]
            self.assertEqual(sorted(b["parts"]["target"] for b in rotators), sorted(present))
            missing = gears.meta.get("missing_gear")
            self.assertEqual(len(present), gears.meta["gears"] - (1 if missing else 0))
            self.assertEqual(gears.get("Slot") is not None, bool(missing))
            speeds = {b["parts"]["target"]: b["fields"]["speed"] for b in rotators}
            for name, speed in speeds.items():  # neighbouring gears turn in opposite directions
                index = int(name.split("_")[1])
                self.assertEqual(speed > 0, index % 2 == 1, name)

            splitter = generate_asset("laser_splitter", seed)
            self.assertEqual({splitter.get("Beam_A").parent, splitter.get("Beam_B").parent}, {"Prism"})

            field = generate_asset("force_field", seed).behaviours[0]
            self.assertEqual((field["script"], field["parts"]["panels"]), ("Door", ["Field"]))
            self.assertLess(field["fields"]["openOffset"][1], 0)  # drops into the floor
            shutter = generate_asset("shutter", seed).behaviours[0]
            self.assertGreater(shutter["fields"]["openOffset"][1], 0)  # rolls up

            plug = generate_asset("cable_plug", seed)
            slots = [o for o in plug.objects if o.name.startswith("Slot_")]
            self.assertEqual(len(slots), plug.meta["sockets"])
            self.assertLessEqual(plug.meta["target_slot"], plug.meta["sockets"])
            self.assertGreater(plug.get("Plug").mesh.bbox()[0][2], 0.0)  # hangs above the floor

            safe = generate_asset("safe", seed)
            self.assertIsNotNone(safe.get("Slot"))
            self.assertEqual(safe.get("Glow").parent, "Panel")  # status LED sits on the door
            if safe.meta["lock"] == "dial":
                self.assertEqual(safe.get("Wheel").parent, "Panel")

            hatch = generate_asset("hatch", seed)
            lid = next(b for b in hatch.behaviours if b["parts"]["target"] == "Panel")
            self.assertEqual(lid["fields"]["axis"], "right")
            self.assertLess(lid["fields"]["step"], 0)  # negative around Unity right = swings up

    def test_new_items(self):
        for t in ("tool", "clue", "spare_part"):
            self.assertEqual(REGISTRY[t].pivot, "center")
            kinds = set()
            for seed in range(SEEDS_PER_TYPE):
                asset = generate_asset(t, seed)
                kinds.add(asset.meta["kind"])
                pickup = [b for b in asset.behaviours if b["script"] == "ItemPickup"]
                self.assertEqual(len(pickup), 1, t)
                self.assertEqual(set(pickup[0]["parts"]["model"]), {o.name for o in asset.meshes()})
            self.assertEqual(kinds, set(REGISTRY[t].param("kind").choices), t)

    def test_robot_arm_joint_chain(self):
        for seed in range(SEEDS_PER_TYPE):
            arm = generate_asset("robot_arm", seed)
            parents = {o.name: o.parent for o in arm.objects}
            self.assertEqual((parents["Turret"], parents["Arm_Lower"], parents["Arm_Upper"], parents["Gripper"]),
                             (None, "Turret", "Arm_Lower", "Arm_Upper"))
            drone = generate_asset("drone", seed)
            self.assertEqual(sum(b["script"] == "Rotator" for b in drone.behaviours), drone.meta["rotors"])

    def test_ceiling_pieces_are_viewed_from_below(self):
        self.assertEqual({t for t, e in REGISTRY.items() if e.view == "below"}, {"ceiling_panel", "hanging_crystals"})

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


WALKABLE = ("stairs", "catwalk", "platform", "floor_tile", "floating_island", "hatch", "floor_grate", "vent_shaft",
            "lift", "force_field", "spiral_stairs", "railing", "cage", "crusher", "shock_plate")


def box_corners(c):
    from itertools import product

    from cubegen.geometry import euler_matrix, mat_mul_vec
    rot = euler_matrix(*c.rot)
    for sx, sy, sz in product((-1, 1), repeat=3):
        v = mat_mul_vec(rot, (sx * c.size[0] / 2, sy * c.size[1] / 2, sz * c.size[2] / 2))
        yield tuple(c.center[i] + v[i] for i in range(3))


class ColliderTests(unittest.TestCase):
    def test_walkable_types_have_colliders(self):
        for model_type in WALKABLE:
            for seed in range(SEEDS_PER_TYPE):
                self.assertTrue(generate_asset(model_type, seed).colliders, f"{model_type} {seed}")

    def test_colliders_stay_inside_the_model(self):
        for model_type in model_types():
            for seed in range(SEEDS_PER_TYPE):
                asset = generate_asset(model_type, seed)
                lo, hi = asset.bbox()
                for c in asset.colliders:
                    if c.part is not None:
                        self.assertIsNotNone(asset.get(c.part), f"{model_type} {seed} {c.part}")
                    if c.kind == "mesh":
                        self.assertFalse(asset.get(c.part).is_empty)
                        continue
                    self.assertTrue(all(v > 0 for v in c.size))
                    for corner in box_corners(c):
                        for i in range(3):
                            self.assertTrue(lo[i] - 0.1 <= corner[i] <= hi[i] + 0.1,
                                            f"{model_type} {seed} {c.part} {corner}")

    def test_unity_rotation_matches_the_mesh_transform(self):
        import itertools
        import random

        from cubegen.asset import to_unity, unity_rotation
        from cubegen.geometry import euler_matrix, mat_mul_vec

        def rotate(q, v):  # v' = q v q* (Unity's Quaternion * Vector3)
            x, y, z, w = q
            t = (2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0]))
            return (v[0] + w * t[0] + y * t[2] - z * t[1], v[1] + w * t[1] + z * t[0] - x * t[2],
                    v[2] + w * t[2] + x * t[1] - y * t[0])

        rng = random.Random(5)
        for _ in range(100):
            rot = [rng.uniform(-math.pi, math.pi) for _ in range(3)]
            q = unity_rotation(rot)
            self.assertAlmostEqual(sum(c * c for c in q), 1.0, places=5)
            for corner in itertools.product((-1, 1), repeat=3):
                blender = mat_mul_vec(euler_matrix(*rot), corner)
                unity = rotate(q, to_unity(corner))
                for a, b in zip(to_unity(blender), unity):
                    self.assertAlmostEqual(a, b, places=3)
        self.assertEqual(unity_rotation((0.0, 0.0, 0.0)), (0.0, 0.0, 0.0, 1.0))

    def test_collider_data(self):
        from cubegen.pipeline import rig_data
        hatch = generate_asset("hatch", 4)
        data = hatch.collider_data()
        lid = [c for c in data if c["part"] == "Panel"]
        self.assertEqual(len(lid), 1)
        self.assertEqual(lid[0]["type"], "box")
        panel = hatch.get("Panel")
        lo, hi = panel.mesh.bbox()
        self.assertAlmostEqual(lid[0]["size"][0], hi[0] - lo[0], delta=0.03)  # Unity X = lid width
        self.assertAlmostEqual(lid[0]["size"][1], 0.06, places=4)             # Unity Y = lid thickness
        spec = {"type": "hatch", "seed": 4, "style": {}}
        self.assertEqual(rig_data(hatch, spec, 1)["colliders"], data)
        self.assertNotIn("colliders", rig_data(generate_asset("crate", 4), {"type": "crate", "seed": 4}, 1))
        self.assertEqual(generate_asset("platform", 1).collider_data(),
                         [{"type": "mesh", "part": "Deck", "convex": True}])

    def test_colliders_follow_scale_and_damage(self):
        from cubegen.params import Style
        a, b = generate_asset("stairs", 3), generate_asset("stairs", 3, scale=2.0)
        for ca, cb in zip(a.colliders, b.colliders):
            self.assertEqual(cb.size, tuple(v * 2 for v in ca.size))
        self.assertFalse(generate_asset("stairs", 3, style=Style(damage="destroyed")).colliders)
        self.assertTrue(generate_asset("stairs", 3, style=Style(damage="damaged")).colliders)

    def test_ramp_has_no_gaps(self):
        stairs = generate_asset("stairs", 0, params={"style": "ramp", "rails": "none"})
        run, rise = stairs.meta["run_m"], stairs.get("Body").mesh.bbox()[1][2]
        # sample points just under the slope: each one lies in some collider box
        for k in range(1, 20):
            y = -run / 2 + run * k / 20
            z = rise * k / 20 - 0.05
            inside = False
            for c in stairs.colliders:
                (x0, y0, z0), (x1, y1, z1) = [tuple(min(p[i] for p in box_corners(c)) for i in range(3)),
                                              tuple(max(p[i] for p in box_corners(c)) for i in range(3))]
                if c.rot == (0.0, 0.0, 0.0) and y0 <= y <= y1 and z0 <= z <= z1:
                    inside = True
                elif c.rot != (0.0, 0.0, 0.0):  # slope box: distance below the slope plane < thickness
                    slope = c.rot[0]
                    depth = (rise * (y + run / 2) / run - z) * math.cos(slope)
                    inside = inside or 0 <= depth <= c.size[2] + 1e-6
            self.assertTrue(inside, (y, z))


class NewTypeTests(unittest.TestCase):
    def test_traps(self):
        for seed in range(SEEDS_PER_TYPE):
            crusher = generate_asset("crusher", seed)
            door = crusher.behaviours[0]
            self.assertEqual(door["script"], "Door")
            self.assertLess(door["fields"]["openOffset"][1], 0)  # slams down
            head = crusher.get("Panel").mesh.bbox()[0][2]
            self.assertAlmostEqual(head + door["fields"]["openOffset"][1], 0.08, places=3)  # lands on the plate
            saw = generate_asset("saw_blade", seed)
            self.assertEqual({b["script"] for b in saw.behaviours}, {"Rotator", "SignalLight"})
            self.assertTrue(generate_asset("steam_vent", seed).get("Steam").is_empty)

    def test_riddles(self):
        for seed in range(SEEDS_PER_TYPE):
            lock = generate_asset("combination_lock", seed)
            dials = [b for b in lock.behaviours if b["script"] == "Rotatable"]
            self.assertEqual(len(dials), lock.meta["dials"])
            self.assertEqual("".join(str(b["fields"]["target"]) for b in dials), lock.meta["code"])

            puzzle = generate_asset("sliding_puzzle", seed)
            n = puzzle.meta["grid"]
            flat = [v for row in puzzle.meta["layout"] for v in row]
            self.assertEqual(sorted(flat), list(range(n * n)))
            self.assertNotEqual(flat, list(range(1, n * n)) + [0])
            tiles = [v for v in flat if v]
            inversions = sum(1 for i in range(len(tiles)) for j in range(i + 1, len(tiles)) if tiles[i] > tiles[j])
            gap_row_from_bottom = n - flat.index(0) // n
            solvable = inversions % 2 == 0 if n % 2 else (inversions + gap_row_from_bottom) % 2 == 1
            self.assertTrue(solvable, puzzle.meta["layout"])
            self.assertEqual({o.name for o in puzzle.meshes() if o.name.startswith("Tile_")},
                             {f"Tile_{i}" for i in range(1, n * n)})

            scale = generate_asset("balance_scale", seed)
            self.assertEqual(scale.get("Pan_A").parent, "Beam")
            self.assertEqual(scale.get("Slot_B").parent, "Pan_B")

            panel = generate_asset("switch_panel", seed)
            self.assertEqual([b["fields"]["target"] for b in panel.behaviours if b["script"] == "Rotatable"],
                             panel.meta["pattern"])

    def test_more_items_and_kit(self):
        for t in ("flashlight", "key", "cable_reel"):
            self.assertEqual(REGISTRY[t].pivot, "center")
            for seed in range(SEEDS_PER_TYPE):
                self.assertEqual([b["script"] for b in generate_asset(t, seed).behaviours], ["ItemPickup"])
        for seed in range(SEEDS_PER_TYPE):
            cage = generate_asset("cage", seed)
            self.assertEqual(cage.get("Glow").parent, "Panel")
            self.assertTrue(any(c.part == "Panel" for c in cage.colliders))
            stairs = generate_asset("spiral_stairs", seed)
            self.assertGreaterEqual(len(stairs.colliders), stairs.meta["steps"] + 2)
        for t in ("railing", "coffee_machine", "vending_machine"):
            self.assertFalse(generate_asset(t, 2).behaviours)  # static decoration


if __name__ == "__main__":
    unittest.main()
