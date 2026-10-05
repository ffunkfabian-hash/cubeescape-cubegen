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
            declared = {p.name for p in REGISTRY[t].params}
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
        self.assertEqual(cfg.params, {"door": {"style": "airlock", "width": "2"}})
        self.assertEqual((cfg.style.size, cfg.style.snap, cfg.style.glow, cfg.style.wear), ("L", 0.5, "red", "light"))
        self.assertEqual((cfg.icon_azimuth, cfg.icon_elevation, cfg.icon_zoom), (-25.0, 15.0, 1.5))

    def test_cli_rejects_bad_param(self):
        args = make_parser().parse_args(["generate", "--types", "door", "--param", "door.colour=red"])
        with self.assertRaises(KeyError):
            build_config(args).validate()


if __name__ == "__main__":
    unittest.main()
