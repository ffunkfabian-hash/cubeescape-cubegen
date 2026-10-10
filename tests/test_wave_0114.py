"""Geometry regressions from the model browser review."""
import unittest
from cubegen.models import generate_asset, REGISTRY
from cubegen.params import Style
from cubegen.families import collision_boxes
from cubegen.quality import uncovered_geometry, z_fighting

class ReviewedGeometryTests(unittest.TestCase):
    def test_sink_has_a_free_recess_and_a_solid_floor(self):
        for seed in (0, 1, 7, 113):
            a = generate_asset("washroom", seed, params={"style":"sink"})
            shapes = collision_boxes(a, "washroom")
            mesh = a.get("Body").mesh; part = mesh.parts[0]
            verts = mesh.verts[part.v0:part.v1]
            centre = tuple(sum(v[i] for v in verts)/len(verts) for i in range(3))
            recess = (centre[0], centre[1], centre[2]+.07)
            self.assertFalse(any(s.contains(recess) for s in shapes))
            self.assertTrue(any(s.contains(centre) for s in shapes))
            old = generate_asset("washroom", seed, params={"style":"sink"}, style=Style(generation=2))
            self.assertTrue(any(s.contains(recess) for s in collision_boxes(old, "washroom")))

    def test_coffee_reservoir_has_multiple_glass_walls_and_a_cradle(self):
        for form in ("counter", "standing"):
            for seed in (0, 7, 113):
                a = generate_asset("coffee_machine", seed, params={"style":form})
                glass = a.get("Glass").mesh
                self.assertEqual(len(glass.parts), 5)
                self.assertEqual(uncovered_geometry(a, "floor"), [])
                self.assertEqual(z_fighting(a, pivot="floor"), [])

    def test_bridge_posts_have_solid_connections_to_the_landing(self):
        a = generate_asset("retractable_bridge", 113, params={"width":2.0})
        shapes = collision_boxes(a, "retractable_bridge")
        for y in (-1.1, 1.1):
            self.assertTrue(any(s.contains((-.08, y, -.05)) for s in shapes))
        self.assertEqual(uncovered_geometry(a, "top"), [])

class FamilyOverlayTests(unittest.TestCase):
    def test_an_overlay_named_like_its_family_keeps_builtin_dimensions(self):
        import tempfile, json
        from pathlib import Path
        from cubegen.cli import make_parser, build_config
        with tempfile.TemporaryDirectory() as folder:
            recipe = Path(folder)/"lab.json"
            recipe.write_text(json.dumps({"family":"lab","models":{"wall":1,"stairs":1},"seed":114}))
            config = build_config(make_parser().parse_args(["generate","--recipe",str(recipe)]))
            self.assertEqual(config.params["wall"]["height"], 3.0)
            self.assertEqual(config.params["wall"]["thickness"], .3)
            self.assertEqual(config.params["stairs"]["rise"], 2.4)
