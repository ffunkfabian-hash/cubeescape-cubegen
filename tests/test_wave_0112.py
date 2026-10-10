"""Cubegen 0.11.2: the first asset wave from IDEEN.md, its variants and the prototype collision fix."""
import unittest

from cubegen.families import collision_boxes, connectors
from cubegen.models import REGISTRY, generate_asset
from cubegen.params import Style
from cubegen.quality import uncovered_geometry, z_fighting

WAVE = {  # type: (registry category, pivot)
    "airlock_chamber": ("environment", "floor"),
    "ceiling_beam": ("environment", "wall"),
    "pipe_rack": ("industrial", "floor"),
    "coolant_loop": ("industrial", "floor"),
    "pressure_tank": ("industrial", "floor"),
    "turbine": ("industrial", "floor"),
    "compressor": ("industrial", "floor"),
    "relay_box": ("industrial", "wall"),
    "diagnostics_port": ("tech", "wall"),
    "warning_beacon": ("tech", "floor"),
    "emergency_case": ("props", "wall"),
}
PROTOTYPES = ("test_utility_trench", "test_pipe_rack", "test_relay_box", "test_coolant_loop", "test_warning_beacon",
              "test_lens_array", "test_magnetic_lock", "test_scanner_pad", "test_power_routing", "test_thermal_switch")


def free(asset, kind, point) -> bool:
    """No shape of the real Unity import contains the point."""
    return not any(shape.contains(point) for shape in collision_boxes(asset, kind))


def blocked_along_y(asset, kind, x, z, y0=-0.3, y1=0.3, step=0.002) -> bool:
    """Something solid on the line through (x, z) along Y - thin plates included."""
    shapes = collision_boxes(asset, kind)
    n = int(round((y1 - y0) / step))
    return any(shape.contains((x, y0 + (y1 - y0) * i / n, z)) for i in range(n + 1) for shape in shapes)


def geometry(asset):
    return [(o.name, o.pivot, o.mesh.verts if o.mesh else None) for o in asset.objects]


class WaveTypesTests(unittest.TestCase):
    def test_every_candidate_is_registered_with_its_category_and_pivot(self):
        for kind, (category, pivot) in WAVE.items():
            self.assertIn(kind, REGISTRY)
            self.assertEqual((REGISTRY[kind].category, REGISTRY[kind].pivot), (category, pivot), kind)
        self.assertEqual(REGISTRY["ceiling_beam"].view, "below")

    def test_seeds_are_deterministic_and_vary(self):
        for kind in WAVE:
            with self.subTest(kind=kind):
                self.assertEqual(generate_asset(kind, 7).digest(), generate_asset(kind, 7).digest())
                self.assertGreater(len({generate_asset(kind, s).digest() for s in range(6)}), 3)

    def test_static_by_default_with_exact_mesh_collision_in_every_state(self):
        for style in (Style(), Style(damage="damaged"), Style(wear="heavy"), Style(detail="low"), Style(size="L")):
            for kind, (_, pivot) in WAVE.items():
                for seed in range(4):
                    with self.subTest(kind=kind, seed=seed, style=style.to_dict()):
                        asset = generate_asset(kind, seed, style=style)
                        self.assertFalse(asset.behaviours)
                        physical = {o.name for o in asset.meshes() if o.name != "Wear"}
                        self.assertEqual({c.part for c in asset.colliders}, physical)
                        self.assertTrue(all(c.kind == "mesh" and not c.convex for c in asset.colliders))
                        self.assertEqual(uncovered_geometry(asset, pivot), [])
                        self.assertEqual(z_fighting(asset, pivot=pivot), [])

    def test_gameplay_scripts_only_on_explicit_request(self):
        turbine = generate_asset("turbine", 3, params={"machine": True})
        self.assertEqual({b["script"] for b in turbine.behaviours}, {"Machine", "Rotator"})
        self.assertTrue(next(c for c in turbine.colliders if c.part == "Rotor").convex)  # the moving rotor
        self.assertEqual({b["script"] for b in generate_asset("compressor", 3, params={"machine": True}).behaviours},
                         {"Machine"})
        beacon = generate_asset("warning_beacon", 3, params={"signal": True, "mode": "Pulse"})
        self.assertEqual(len(set(beacon.get("Glow").mesh.roles)), 1, "the signal part has one material")
        self.assertEqual(beacon.behaviours[0]["script"], "SignalLight")
        self.assertEqual(beacon.behaviours[0]["fields"]["mode"], "Pulse")

    def test_free_space_stays_free(self):
        # under the lowest pipe run of a rack, between two frames
        rack = generate_asset("pipe_rack", 4, params={"length": 4.0, "levels": 2})
        lowest = min(rack.meta["levels_m"])
        self.assertTrue(free(rack, "pipe_rack", (0.5, 0.0, 0.3)))
        self.assertTrue(free(rack, "pipe_rack", (0.5, 0.0, lowest - rack.meta["radius"] - 0.3)))
        # the inside of the coolant loop
        loop = generate_asset("coolant_loop", 4)
        self.assertTrue(free(loop, "coolant_loop", (0.3, 0.0, loop.meta["axis_height"] + 0.5)))
        # an open airlock: walk straight through both doorways
        lock = generate_asset("airlock_chamber", 4, params={"state": "open"})
        length = lock.meta["inner_m"][1]
        for y in (-length / 2 - 0.2, -length / 2, 0.0, length / 2, length / 2 + 0.2):
            for z in (0.4, 1.2, 1.9):
                self.assertTrue(free(lock, "airlock_chamber", (0.0, y, z)), (y, z))
        closed = generate_asset("airlock_chamber", 4, params={"state": "closed"})
        self.assertFalse(free(closed, "airlock_chamber", (0.1, -length / 2, 1.2)), "a closed door blocks")
        self.assertFalse(free(closed, "airlock_chamber", (-0.1, length / 2, 1.2)))
        # the open emergency case is a hollow box behind its glass, not a solid block
        case = generate_asset("emergency_case", 4, params={"content": "axe"})
        lo, hi = case.bbox()
        self.assertTrue(free(case, "emergency_case", (-(hi[0] - lo[0]) * 0.3, 0.0, (lo[2] + hi[2]) / 2)))

    def test_pipe_ends_fit_the_pipe_family(self):
        rack = generate_asset("pipe_rack", 2, params={"levels": 2, "pipes": 2})
        ends = [c for c in connectors(rack, "pipe_rack") if c["kind"] == "pipe"]
        self.assertEqual(len(ends), 2 * 2 * 2)
        self.assertTrue(all(c["radius"] in (0.09, 0.18) for c in ends))
        for kind in ("coolant_loop", "pressure_tank", "compressor"):
            asset = generate_asset(kind, 1, params={"receiver": True} if kind == "compressor" else None)
            self.assertTrue(any(c["kind"] == "pipe" for c in connectors(asset, kind)), kind)
        beam = connectors(generate_asset("ceiling_beam", 1), "ceiling_beam")
        self.assertEqual({c["kind"] for c in beam}, {"beam_end"})
        self.assertTrue(all(abs(c["pos"][2] - 3.0) < 1e-9 for c in beam), "beam top at the default wall height")

    def test_wall_pieces_stand_on_the_wall_face(self):
        for kind in ("relay_box", "diagnostics_port", "emergency_case"):
            for seed in range(5):
                lo, hi = generate_asset(kind, seed).bbox()
                self.assertAlmostEqual(hi[1], 0.1, places=3, msg=f"{kind} {seed}: back on the wall at y = +0.1")


class VariantTests(unittest.TestCase):
    def test_variants_are_quiet_options_and_keep_existing_seeds(self):
        for kind in ("door", "hatch", "keypad"):
            for seed in range(4):
                plain = generate_asset(kind, seed)
                self.assertNotIn("variant", plain.meta.get("params", {}), kind)
                self.assertEqual(geometry(plain), geometry(generate_asset(kind, seed, params={"variant": "standard"})))

    def test_iris_door_is_a_static_door_variant_with_a_free_centre_when_open(self):
        closed = generate_asset("door", 5, params={"variant": "iris"})
        self.assertFalse(closed.behaviours)
        self.assertIsNotNone(closed.get("Iris"))
        self.assertIsNone(closed.get("Panel"))
        w, h = closed.meta["opening_m"]
        r = closed.meta["iris"]["radius_m"]
        for x, dz in ((0.05, 0.03), (r * 0.3, -r * 0.2), (-r * 0.5, r * 0.4)):
            self.assertTrue(blocked_along_y(closed, "door", x, h / 2 + dz), "closed blades cover the opening")
        opened = generate_asset("door", 5, params={"variant": "iris", "iris_open": 1.0})
        self.assertFalse(blocked_along_y(opened, "door", 0.0, h / 2))
        self.assertFalse(blocked_along_y(opened, "door", r * 0.3, h / 2 - r * 0.2))
        self.assertGreater(opened.meta["iris"]["clear_radius_m"], 0.4 * min(w, h) * 0.475)
        # the frame still fits a wall door opening like any other door
        self.assertEqual(connectors(opened, "door")[0]["kind"], "door")

    def test_maintenance_hatch_keeps_lid_and_script(self):
        for seed in range(6):
            hatch = generate_asset("hatch", seed, params={"variant": "maintenance"})
            self.assertEqual(hatch.meta["shape"], "square")
            self.assertEqual([b["script"] for b in hatch.behaviours], ["Rotatable"])
            self.assertEqual(hatch.behaviours[0]["parts"]["target"], "Panel")
            self.assertTrue(free(hatch, "hatch", (0.0, 0.0, -0.6)), "the shaft below stays open")
        round_kept = generate_asset("hatch", 2, params={"variant": "maintenance", "shape": "round"})
        self.assertEqual(round_kept.meta["shape"], "round")

    def test_access_panel_is_a_keypad_variant_with_a_card_slot(self):
        panel = generate_asset("keypad", 3, params={"variant": "access"})
        self.assertEqual([b["script"] for b in panel.behaviours], ["SignalIndicator"])
        self.assertIsNotNone(panel.get("Slot"))
        self.assertGreater(panel.bbox()[1][0], generate_asset("keypad", 3).bbox()[1][0] + 0.1)


class PrototypeCollisionTests(unittest.TestCase):
    def test_generation_three_prototypes_no_longer_fill_their_gaps_with_one_box(self):
        for kind in PROTOTYPES:
            asset = generate_asset(kind, 1)
            self.assertTrue(asset.colliders, kind)
            self.assertTrue(all(c.kind == "mesh" and not c.convex for c in asset.colliders), kind)
        rack = generate_asset("test_pipe_rack", 1)
        self.assertTrue(free(rack, "test_pipe_rack", (0.0, 0.0, 0.25)), "under the lowest pipe run")
        trench = generate_asset("test_utility_trench", 1)
        lo, hi = trench.bbox()
        self.assertTrue(free(trench, "test_utility_trench", (0.0, 0.0, lo[2] + 0.15)), "inside the U-channel")

    def test_old_generations_keep_their_historical_box(self):
        for kind in PROTOTYPES:
            for generation in (1, 2):
                asset = generate_asset(kind, 1, style=Style(generation=generation))
                self.assertEqual([c.kind for c in asset.colliders], ["box"], kind)


if __name__ == "__main__":
    unittest.main()
