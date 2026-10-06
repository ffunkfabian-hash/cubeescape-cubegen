"""Model families: shared measures, fit checks, the three ways of working (same model, variant, matching part)."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.asset import Collider  # noqa: E402
from cubegen.cli import build_config, main, make_parser  # noqa: E402
from cubegen.families import (check_walk, connectors, family_files, fit_report, load_family, misfits,  # noqa: E402
                              resolve)
from cubegen.models import generate_asset, model_types  # noqa: E402
from cubegen.pipeline import build_spec, family_fit, plan_models  # noqa: E402

FAMILIES = ("station", "foundry", "lab")


def config(*args):
    cfg = build_config(make_parser().parse_args(["generate", *args]))
    cfg.validate()
    return cfg


def fit(cfg):
    return family_fit(plan_models(cfg), None, cfg.family["dims"], cfg.family.get("reference"))


class FamilyTests(unittest.TestCase):
    def test_builtin_families(self):
        self.assertEqual(set(family_files()), set(FAMILIES))

    def test_every_type_follows_the_builtin_families(self):
        # window_wall and wall_corner follow wall_height / wall_thickness / window_sill (foundry: 4 m, lab: 0.3 m)
        for name in FAMILIES:
            family = load_family(name)
            self.assertEqual(misfits(family["dims"], model_types()), {}, name)
            fine = {t: 1 for t in model_types()}
            self.assertEqual(set(resolve(family, None, models=fine)["values"]["models"]), set(fine))
        # a measure outside a type's range: that type is a misfit, and resolving it fails
        bad = misfits({"pipe_radius": 0.4}, model_types())
        self.assertEqual(set(bad), {"pipe", "pipe_bend", "fluid_basin"})
        with self.assertRaises(ValueError):
            resolve({"dims": {"pipe_radius": 0.4}}, None, models={"pipe": 1})

    def test_walls_follow_the_family(self):
        for name, h, t in (("foundry", 4.0, 0.5), ("lab", 3.0, 0.3)):
            cfg = config("--family", name, "--types", "window_wall,wall_corner", "--count", "3")
            for spec in plan_models(cfg):
                body = build_spec(spec).get("Wall").mesh.bbox()
                self.assertAlmostEqual(body[1][2] - body[0][2], h + 0.025, delta=0.01, msg=spec["name"])  # + trim
                depth = body[1][1] - body[0][1] if spec["type"] == "window_wall" else None
                if depth is not None:
                    self.assertAlmostEqual(depth, t + 0.1, delta=0.011, msg=spec["name"])  # wall + top trim
            self.assertEqual(fit(cfg)["problems"], [], name)

    def test_kits_fit_for_several_seeds(self):
        for name in FAMILIES:
            for seed in ("42", "7", "level-3"):
                cfg = config("--family", name, "--seed", seed)
                result = fit(cfg)
                self.assertGreater(result["joints"], 300, name)
                self.assertEqual(result["problems"], [], f"{name} {seed}")
                self.assertEqual(result["look"], [], f"{name} {seed}")

    def test_variants_within_a_family_keep_the_joints(self):
        # B: browse variants - details vary, measures and look stay
        cfg = config("--family", "station", "--types", "catwalk,stairs,wall,door,pipe,pipe_bend", "--count", "6",
                     "--seed", "11")
        specs = plan_models(cfg)
        self.assertEqual(fit(cfg)["problems"], [])
        catwalks = [build_spec(s) for s in specs if s["type"] == "catwalk"]
        self.assertGreater(len({c.digest() for c in catwalks}), 1)  # the variants differ ...
        widths = {c["width"] for a in catwalks for c in connectors(a, "catwalk")}
        self.assertEqual(widths, {2.0})  # ... the joints don't
        doors = [build_spec(s) for s in specs if s["type"] == "door"]
        self.assertEqual({tuple(d.meta["opening_m"]) for d in doors}, {(2.0, 2.2)})
        self.assertEqual({d.meta["style"] for d in doors}, {"sliding"})

    def test_same_model_again(self):
        # A: same variant, parameters and version = the same model
        a = [build_spec(s).digest() for s in plan_models(config("--family", "lab", "--seed", "3"))]
        b = [build_spec(s).digest() for s in plan_models(config("--family", "lab", "--seed", "3"))]
        self.assertEqual(a, b)

    def test_adding_to_a_kit_changes_nothing_else(self):
        base = {s["name"]: build_spec(s).digest() for s in plan_models(config("--family", "station", "--seed", "5"))}
        with tempfile.TemporaryDirectory() as tmp:
            recipe = os.path.join(tmp, "more.json")
            with open(recipe, "w", encoding="utf-8") as fh:  # the station kit plus more parts
                kit = json.load(open(family_files()["station"], encoding="utf-8"))["models"]
                kit += [{"type": "wall", "pick": [9], "params": {"opening": "door", "opening_x": 0.5}},
                        {"type": "crate", "count": 2}, {"type": "catwalk", "pick": [7], "params": {"shape": "tee"}}]
                json.dump({"family": "station", "models": kit}, fh)
            more = {s["name"]: build_spec(s).digest() for s in plan_models(config("--recipe", recipe, "--seed", "5"))}
        self.assertTrue(set(base) < set(more))
        self.assertEqual({k: more[k] for k in base}, base)

    def test_deviations_are_recorded_and_caught(self):
        cases = {"door.width=1.6": "frame 2.400", "catwalk.width=1.0": "width 1.000 m vs 2.000 m",
                 "stairs.rise=2.4": "upper level is 3.0", "wall.thickness=0.3": "wall thickness",
                 "pipe.radius=0.09": "radius"}
        for param, expected in cases.items():
            cfg = config("--family", "station", "--seed", "42", "--param", param)
            t, _, rest = param.partition(".")
            name = rest.split("=")[0]
            self.assertIn(f"params.{t}.{name}", [d["what"] for d in cfg.family["deviations"]])
            problems = [p for r in fit(cfg)["problems"] for p in r["problems"]]
            self.assertTrue(any(expected in p for p in problems), f"{param}: {problems[:3]}")

    def test_blocking_collider_at_a_joint_is_found(self):
        a = generate_asset("catwalk", 1, params={"width": 2.0, "length": 4.0, "rails": "both"})
        b = generate_asset("catwalk", 2, params={"width": 2.0, "length": 4.0, "rails": "both"})
        ca, cb = connectors(a, "catwalk")[1], connectors(b, "catwalk")[0]
        self.assertEqual(check_walk(a, "catwalk", ca, b, "catwalk", cb), [])
        b.colliders.append(Collider("box", None, (-1.9, 0.0, 0.8), (0.2, 1.5, 1.6)))  # a post in the passage
        self.assertTrue(any("inside a collider" in p for p in check_walk(a, "catwalk", ca, b, "catwalk", cb)))
        b.colliders = [c for c in b.colliders if c.part != "Deck"]  # no floor at the joint
        self.assertTrue(any("no walkable collider" in p for p in check_walk(a, "catwalk", ca, b, "catwalk", cb)))

    def test_wall_with_door_stays_open(self):
        wall = generate_asset("wall", 4, params={"opening": "door", "door_style": "sliding", "door_width": 2.0,
                                                 "door_height": 2.2})
        door = generate_asset("door", 4, params={"style": "sliding", "width": 2.0, "height": 2.2})
        report = fit_report([("Wall", wall, "wall"), ("Door", door, "door")])
        self.assertTrue(report)
        self.assertEqual([r for r in report if r["problems"]], [])
        closed = generate_asset("wall", 4)  # without the opening the door has nowhere to go
        self.assertFalse([r for r in fit_report([("Wall", closed, "wall"), ("Door", door, "door")])
                          if r["joint"].startswith("door")])

    def test_matching_addition(self):
        # C: a pipe bend and a wall pass-through for an existing pipe made without a family
        with tempfile.TemporaryDirectory() as tmp:
            main(["generate", "--seed", "9", "--pick", "pipe:4", "--prefix", "Gen_", "--no-blender",
                  "--out", os.path.join(tmp, "a")])
            sidecar = os.path.join(tmp, "a", "models", "Gen_Pipe_004.cubegen.json")
            rig = json.load(open(sidecar, encoding="utf-8"))
            cfg = config("--seed", "9", "--match", sidecar, "--types", "pipe_bend,wall", "--count", "2",
                         "--param", "wall.opening=pipe")
            result = fit(cfg)
            self.assertEqual(result["problems"], [])
            self.assertTrue(any(r["a"] == "Gen_Pipe_004" or r["b"] == "Gen_Pipe_004" for r in
                                fit_report([(s["name"], build_spec(s), s["type"]) for s in plan_models(cfg)])) or
                            result["joints"] > 12)
            for spec in plan_models(cfg):
                params = build_spec(spec).meta["params"]
                if spec["type"] == "pipe_bend":
                    self.assertEqual(params["radius"], rig["params"]["radius"])
                    self.assertAlmostEqual(params["axis_height"], rig["params"]["axis_height"])
                else:
                    self.assertAlmostEqual(params["duct_height"], rig["params"]["axis_height"])

    def test_manifest_records_family_sources_and_fit(self):
        with tempfile.TemporaryDirectory() as out:
            code = main(["generate", "--family", "station", "--types", "door,wall", "--param", "door.speed=2.5",
                         "--no-blender", "--out", out])
            self.assertEqual(code, 0)
            manifest = json.load(open(os.path.join(out, "manifest.json"), encoding="utf-8"))
            fam = manifest["family"]
            self.assertEqual(fam["name"], "station")
            self.assertEqual(fam["dims"]["door_width"], 2.0)
            self.assertEqual(fam["fit"]["problems"], [])
            door = next(m for m in manifest["models"] if m["type"] == "door")
            self.assertEqual(door["family"], "station")
            self.assertEqual(door["param_sources"]["width"], "dims.door_width")
            self.assertEqual(door["param_sources"]["speed"], "cli")
            self.assertEqual(door["connectors"][0]["kind"], "door")
            self.assertEqual(manifest["config"]["seed"] if "seed" in manifest["config"] else manifest["seed"],
                             manifest["seed"])

    def test_recipes_on_a_family(self):
        # a recipe that names a family and deviates from it keeps all other measures of the family
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg = config("--recipe", os.path.join(root, "recipes", "station_room.json"))
        self.assertEqual(cfg.family["name"], "station")
        self.assertEqual(cfg.family["dims"]["door_width"], 2.4)
        self.assertEqual(cfg.family["dims"]["wall_height"], 3.0)
        self.assertEqual([d["what"] for d in cfg.family["deviations"]], ["dims.door_width"])
        walls = [build_spec(s) for s in plan_models(cfg) if s["type"] == "wall"]
        self.assertEqual({w.meta["length_m"] for w in walls}, {4.0})
        self.assertEqual(fit(cfg)["problems"], [])
        door = next(build_spec(s) for s in plan_models(cfg) if s["type"] == "door")
        self.assertEqual(door.meta["opening_m"][0], 2.4)
        lab = config("--recipe", family_files()["lab"])  # a family file is a recipe too
        self.assertEqual((lab.family["name"], lab.textures, lab.texture_set), ("lab", "tiled", "lab"))

    def test_unknown_measure_and_unfit_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.json")
            json.dump({"family": "bad", "dims": {"wall_hieght": 3.0}, "models": {"wall": 1}}, open(path, "w"))
            with self.assertRaisesRegex(ValueError, "did you mean 'wall_height'"):
                config("--family", path)
            json.dump({"family": "bad", "dims": {"pipe_radius": 0.4}, "models": {"wall": 1}}, open(path, "w"))
            with self.assertRaisesRegex(ValueError, "pipe can.t follow pipe_radius"):
                config("--family", path, "--types", "pipe")


if __name__ == "__main__":
    unittest.main()
