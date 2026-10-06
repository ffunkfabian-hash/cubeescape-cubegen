"""Parameters and global style."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.cli import build_config, make_parser  # noqa: E402
from cubegen.models import REGISTRY, generate_asset, model_types  # noqa: E402
from cubegen.params import Style, parse_param_overrides  # noqa: E402

SEEDS = range(12)


def fingerprint(asset):
    return [(o.name, o.pivot, o.mesh.verts if o.mesh else None, o.mesh.roles if o.mesh else None)
            for o in asset.objects]


def check_valid(test, asset, label):
    test.assertTrue(asset.meshes(), label)
    for obj in asset.meshes():
        test.assertTrue(obj.mesh.faces, f"{label} {obj.name}")
        for part in obj.mesh.parts:
            if part.closed:
                test.assertGreater(obj.mesh.part_volume(part), 0, f"{label} {obj.name}/{part.name}")


def sample_values(prm):
    if prm.kind == "choice":
        return list(prm.choices)
    if prm.kind == "bool":
        return [True, False]
    if prm.kind == "int":
        return [int(prm.lo), int(prm.hi)]
    if prm.kind == "text":
        return ["energy_cell", "Key Card 2"]
    return [prm.lo, (prm.lo + prm.hi) / 2, prm.hi]


class ParamTests(unittest.TestCase):
    def test_no_params_is_unchanged(self):
        for t in model_types():
            for seed in SEEDS:
                self.assertEqual(fingerprint(generate_asset(t, seed)),
                                 fingerprint(generate_asset(t, seed, params={}, style=Style())))

    def test_every_declared_param_is_used(self):
        for t in model_types():
            used = set()
            for seed in range(40):
                used |= set(generate_asset(t, seed).meta["params"])
            # text and quiet options are only written when given
            declared = {p.name for p in REGISTRY[t].params if p.kind != "text" and not p.quiet}
            self.assertEqual(declared - used, set(), f"{t}: declared but never read")

    def test_every_param_value_builds_valid_models(self):
        for t in model_types():
            for prm in REGISTRY[t].params:
                for value in sample_values(prm):
                    for seed in range(4):
                        with self.subTest(type=t, param=prm.name, value=value, seed=seed):
                            asset = generate_asset(t, seed, params={prm.name: value})
                            check_valid(self, asset, f"{t}.{prm.name}={value}")
                            used = asset.meta["params"]
                            if prm.name in used:  # conditional ones (rotor_speed without flywheel) aren't read
                                self.assertEqual(used[prm.name], prm.parse(value))

    def test_item_id(self):
        pickups = [t for t in model_types()
                   if any(b["script"] == "ItemPickup" for b in generate_asset(t, 0).behaviours)]
        self.assertEqual(len(pickups), 8)
        for t in pickups:
            fields = generate_asset(t, 0).behaviours[0]["fields"]
            self.assertNotIn("itemId", fields, t)  # never invented
            given = generate_asset(t, 0, params={"item_id": "servo_battery"})
            self.assertEqual(given.behaviours[0]["fields"]["itemId"], "servo_battery", t)
            self.assertEqual(given.digest() != generate_asset(t, 0).digest(), True)
        with self.assertRaises(ValueError):
            REGISTRY["key"].param("item_id").parse("  ")

    def test_override_only_changes_its_property(self):
        base = generate_asset("crate", 5).meta["params"]
        changed = generate_asset("crate", 5, params={"style": "rims"}).meta["params"]
        self.assertEqual({k: v for k, v in base.items() if k != "style"},
                         {k: v for k, v in changed.items() if k != "style"})

    def test_parse_and_errors(self):
        self.assertEqual(parse_param_overrides(["door.style=airlock", "door.width=2", "wall.pipe=ja"]),
                         {"door": {"style": "airlock", "width": "2"}, "wall": {"pipe": "ja"}})
        with self.assertRaises(KeyError):
            generate_asset("door", 1, params={"colour": "red"})
        with self.assertRaises(ValueError):
            generate_asset("door", 1, params={"style": "garage"})
        with self.assertRaises(ValueError):
            generate_asset("door", 1, params={"width": 99})
        with self.assertRaises(ValueError):
            parse_param_overrides(["door-style=airlock"])

    def test_door_unity_values(self):
        door = generate_asset("door", 3, params={"style": "sliding", "width": 2.0, "speed": 5})
        self.assertEqual(door.behaviours[0]["fields"], {"openOffset": [2.05, 0.0, 0.0], "speed": 5.0})


class StyleTests(unittest.TestCase):
    def test_size_classes(self):
        for t in ("crate", "machine", "tank", "server_rack"):
            for seed in SEEDS:
                dims = {c: generate_asset(t, seed, style=Style(size=c)).stats()["dimensions_m"] for c in "SML"}
                self.assertLessEqual(dims["S"][0], dims["M"][0] + 1e-9, t)
                self.assertLessEqual(dims["M"][0], dims["L"][0] + 1e-9, t)

    def test_snap(self):
        for seed in SEEDS:
            used = generate_asset("machine", seed, style=Style(snap=0.5)).meta["params"]
            for key in ("width", "depth", "height"):
                self.assertAlmostEqual(used[key] / 0.5, round(used[key] / 0.5), places=9)
            r = generate_asset("tank", seed, style=Style(snap=0.5)).meta["params"]["radius"]
            self.assertAlmostEqual(2 * r / 0.5, round(2 * r / 0.5), places=9)  # the diameter snaps

    def test_glow_material_warning(self):
        for seed in SEEDS:
            crate = generate_asset("crate", seed, style=Style(glow="orange", material="metal", warning="none"))
            self.assertEqual(set(crate.get("Glow").mesh.roles), {"M_GlowOrange"})
            self.assertIn("M_Metal", crate.get("Body").mesh.roles)
            self.assertNotIn("M_Warning", crate.get("Body").mesh.roles)
            self.assertTrue(generate_asset("crate", seed, style=Style(warning="always")).meta["params"]["stripes"])
            # status parts keep their state colour
            machine = generate_asset("machine", seed, style=Style(glow="cyan"))
            self.assertEqual(set(machine.get("Glow").mesh.roles), {"M_GlowRed"})

    def test_generation(self):
        from cubegen.params import LATEST_GENERATION
        from cubegen.pipeline import build_spec, plan_models
        from cubegen.quality import z_fighting

        self.assertEqual(Style().generation, LATEST_GENERATION)
        self.assertEqual(Style.from_dict({"generation": "1"}).generation, 1)
        with self.assertRaises(ValueError):
            Style(generation=4).validate()
        old = generate_asset("door", 0, style=Style(generation=1))
        new = generate_asset("door", 0)
        self.assertTrue(z_fighting(old, pivot="floor"))  # 0.9.0: the frame's warning band flickers
        self.assertFalse(z_fighting(new, pivot="floor"))
        cfg = build_config(make_parser().parse_args(["generate", "--types", "door", "--generation", "1"]))
        self.assertEqual(cfg.style.generation, 1)
        self.assertEqual(build_spec(plan_models(cfg)[0]).digest(),
                         generate_asset("door", plan_models(cfg)[0]["seed"], plan_models(cfg)[0]["name"],
                                        style=Style(generation=1)).digest())
        import io
        from contextlib import redirect_stderr

        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):  # argparse: only 1, 2 or 3
            make_parser().parse_args(["generate", "--generation", "4"])

    def test_match_rebuilds_old_sidecars_as_generation_1(self):
        from cubegen.families import resolve

        rig = {"model": "Gen_Pipe_000", "type": "pipe", "seed": 1, "params": {"radius": 0.18}, "style": {}}
        self.assertEqual(resolve(None, None, match=rig)["values"]["style"]["generation"], 1)
        rig["style"] = {"generation": 2}
        self.assertEqual(resolve(None, None, match=rig)["values"]["style"]["generation"], 2)

    def test_readme_lists_every_parameter(self):
        # README.md's table is generated from the registry: python3 tools/param_table.py --write
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
        import param_table

        with open(param_table.README, encoding="utf-8") as fh:
            self.assertEqual(param_table.readme_table(fh.read()), param_table.table(),
                             "README parameter table is outdated: python3 tools/param_table.py --write")

    def test_detail_and_wear(self):
        for t in model_types():
            low = generate_asset(t, 2, style=Style(detail="low")).stats()["triangles"]
            normal = generate_asset(t, 2).stats()["triangles"]
            high = generate_asset(t, 2, style=Style(detail="high")).stats()["triangles"]
            self.assertLessEqual(low, normal, t)
            self.assertLessEqual(normal, high, t)
            worn = generate_asset(t, 2, style=Style(wear="heavy"))
            self.assertEqual(worn.get("Wear") is not None, REGISTRY[t].pivot == "floor", t)
            check_valid(self, worn, t)
            # wear never changes the model itself
            plain = generate_asset(t, 2)
            self.assertEqual(fingerprint(plain), [f for f in fingerprint(worn) if f[0] != "Wear"])

    def test_theme(self):
        from cubegen.params import theme_style

        self.assertEqual(theme_style("labor-3"), theme_style(" labor-3 "))
        rolled = [theme_style(f"room-{i}") for i in range(40)]
        for key in ("glow", "material", "wear", "warning"):
            self.assertGreater(len({r[key] for r in rolled}), 1, key)
        themed = Style(theme="labor-3").resolved()
        self.assertEqual((themed.glow, themed.material, themed.wear, themed.warning),
                         tuple(theme_style("labor-3")[k] for k in ("glow", "material", "wear", "warning")))
        explicit = Style(theme="labor-3", glow="orange", wear="none").resolved()  # explicit settings win
        self.assertEqual((explicit.glow, explicit.wear, explicit.material), ("orange", "none", themed.material))
        self.assertEqual(Style().resolved().wear, "none")
        a = generate_asset("crate", 3, style=Style(theme="labor-3"))
        b = generate_asset("crate", 3, style=Style(**{k: v for k, v in themed.to_dict().items() if k != "theme"}))
        self.assertEqual(a.digest(), b.digest())  # a theme is exactly its rolled settings
        with self.assertRaises(ValueError):
            Style(theme="  ").validate()

    def test_style_validation(self):
        with self.assertRaises(ValueError):
            generate_asset("crate", 1, style=Style(size="XL"))


class CliTests(unittest.TestCase):
    def test_cli_params_and_style(self):
        args = make_parser().parse_args([
            "generate", "--seed", "1", "--types", "door", "--param", "door.style=airlock",
            "--param", "door.width=2", "--size", "L", "--snap", "0.5", "--glow", "red", "--wear", "light",
            "--icon-angle=-25,15", "--icon-zoom", "1.5"])
        cfg = build_config(args)
        cfg.validate()
        self.assertEqual(cfg.params, {"door": {"style": "airlock", "width": 2.0}})
        self.assertEqual((cfg.style.size, cfg.style.snap, cfg.style.glow, cfg.style.wear), ("L", 0.5, "red", "light"))
        self.assertEqual((cfg.icon_azimuth, cfg.icon_elevation, cfg.icon_zoom), (-25.0, 15.0, 1.5))

    def test_cli_rejects_bad_param(self):
        args = make_parser().parse_args(["generate", "--types", "door", "--param", "door.colour=red"])
        with self.assertRaises(KeyError):
            build_config(args).validate()


if __name__ == "__main__":
    unittest.main()
