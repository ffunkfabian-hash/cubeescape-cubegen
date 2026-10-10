"""The second station wave: known types, explicit robot capabilities and exact collision."""
import json
from pathlib import Path
import unittest

from cubegen.models import REGISTRY, generate_asset
from cubegen.params import Style
from cubegen.quality import uncovered_geometry
from cubegen.seeds import model_seed
from cubegen.families import collision_boxes

RECIPE = json.loads((Path(__file__).resolve().parents[1] / "recipes/station_wave2.json").read_text())


class SecondStationWaveTests(unittest.TestCase):
    def test_collapsed_catwalk_posts_are_solid_in_generation_three(self):
        asset = generate_asset("collapsed_catwalk", 113, params={"length": 3.0, "width": 1.5, "height": 1.5})
        shapes = collision_boxes(asset, "collapsed_catwalk")
        mesh = asset.get("Wreck").mesh
        posts = []
        for part in mesh.parts:
            verts = mesh.verts[part.v0:part.v1]
            size = [max(v[i] for v in verts) - min(v[i] for v in verts) for i in range(3)]
            if abs(size[0] - 0.12) < 1e-6 and abs(size[1] - 0.12) < 1e-6 and size[2] > 1.0:
                posts.append(tuple(sum(v[i] for v in verts) / len(verts) for i in range(3)))
        self.assertEqual(len(posts), 2)
        self.assertTrue(all(any(shape.contains(point) for shape in shapes) for point in posts))
        self.assertEqual({c.part for c in asset.colliders}, {"Wreck", "Rubble"})
        for generation in (1, 2):
            historical = generate_asset("collapsed_catwalk", 113, style=Style(generation=generation))
            self.assertEqual([c.kind for c in historical.colliders], ["box"])

    def test_recipe_keeps_robots_stationary_and_other_models_static(self):
        for kind in RECIPE["models"]:
            asset = generate_asset(kind, model_seed(RECIPE["seed"], kind, 0), params=RECIPE["params"].get(kind), style=Style(generation=3))
            scripts = [b["script"] for b in asset.behaviours]
            self.assertEqual(scripts, ["SignalLight"] if REGISTRY[kind].category == "robots" else [], kind)
            self.assertTrue(asset.colliders, kind)
            self.assertEqual(uncovered_geometry(asset, REGISTRY[kind].pivot), [], kind)
            self.assertTrue(all(c.kind == "mesh" and not c.convex for c in asset.colliders), kind)

    def test_every_state_and_seed_has_collision_for_all_solid_parts(self):
        for kind in RECIPE["models"]:
            for damage in ("intact", "damaged", "destroyed"):
                for seed in (0, 7, 113):
                    with self.subTest(kind=kind, damage=damage, seed=seed):
                        asset = generate_asset(kind, seed, params=RECIPE["params"].get(kind), style=Style(generation=3, damage=damage))
                        self.assertTrue(asset.colliders)
                        self.assertEqual(uncovered_geometry(asset, REGISTRY[kind].pivot), [])
                        self.assertTrue(all(c.kind == "mesh" and not c.convex for c in asset.colliders))

    def test_recipe_generation_is_deterministic(self):
        for kind in RECIPE["models"]:
            args = {"params": RECIPE["params"].get(kind), "style": Style(generation=3)}
            seed = model_seed(RECIPE["seed"], kind, 0)
            self.assertEqual(generate_asset(kind, seed, **args).digest(), generate_asset(kind, seed, **args).digest(), kind)
