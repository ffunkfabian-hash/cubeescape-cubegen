"""cubegen 0.17.0 "Prism": paint schemes (experimental) - one neutral bake per model, schemes composed from it."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.blender import find_blender  # noqa: E402
from cubegen.imagemagick import find_imagemagick  # noqa: E402
from cubegen.materials import MATERIALS  # noqa: E402
from cubegen.paint import PAINTED, PAINTS, check_paint, hex_rgb, linear_colors, paint_names, weight_layout  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAS_TOOLS = find_blender() is not None and find_imagemagick() is not None


class PaintDataTest(unittest.TestCase):
    def test_every_scheme_is_complete_and_valid(self):
        self.assertEqual(paint_names(), ["crystal", "industrial"])
        keys = {"label", "colors", "glow", "edge_light", "wear", "wear_color", "grime", "rising_grime", "dust", "dust_color",
                "edge_glow", "edge_glow_color", "roughness"}
        for name, scheme in PAINTS.items():
            self.assertEqual(set(scheme), keys, name)
            self.assertEqual(set(scheme["colors"]), set(PAINTED), name)  # every painted game material has a colour
            for value in list(scheme["colors"].values()) + [scheme[k] for k in keys if k.endswith("_color")]:
                self.assertTrue(all(0.0 <= c <= 1.0 for c in hex_rgb(value)), (name, value))
            for k in ("edge_light", "wear", "grime", "rising_grime", "dust", "edge_glow", "roughness"):
                self.assertTrue(0.0 <= scheme[k] <= 1.0, (name, k))
            self.assertIn(scheme["glow"], ("cyan", "red", "orange"))  # the existing --glow colours
        self.assertTrue(set(PAINTED) <= set(MATERIALS))
        with self.assertRaises(ValueError):
            check_paint("neon")

    def test_weight_maps_pack_three_materials_per_image_in_a_fixed_order(self):
        self.assertEqual(weight_layout(["M_RobotDark", "M_Wall", "M_GlowCyan", "M_Metal", "M_Ground"]),
                         [("M_Ground", "M_Wall", "M_RobotDark"), ("M_Metal",)])
        self.assertEqual(weight_layout(["M_GlowCyan", "M_Glass"]), [])  # glow / glass keep their own material
        self.assertEqual(hex_rgb("#ff8000"), (1.0, 128 / 255, 0.0))
        self.assertAlmostEqual(linear_colors("industrial")["M_HazardOrange"][0], 0.807, places=3)  # #e8 = 232/255


class VariantSetTest(unittest.TestCase):
    """--set: the variants of a type keep variant 0's outline and differ inside (set pieces side by side)."""

    def plan(self, *types, extra=()):
        from cubegen.cli import build_config, make_parser
        from cubegen.pipeline import plan_models

        args = ["generate", "--seed", "42", "--types", ",".join(types), "--count", "5", "--set", "--no-blender",
                "--out", "x", *extra]
        return plan_models(build_config(make_parser().parse_args(args)), lambda m: None)

    def test_members_share_the_outline_and_variant_0_stays_the_same_model(self):
        from cubegen.cli import build_config, make_parser
        from cubegen.pipeline import build_spec, plan_models

        specs = self.plan("wall")
        self.assertEqual(len(specs), 5)
        self.assertTrue(all(s["set"]["name"] == "wall_set" for s in specs))
        self.assertEqual({s["params"]["length"] for s in specs}, {specs[0]["set"]["pinned"]["length"]})
        plain = plan_models(build_config(make_parser().parse_args(
            ["generate", "--seed", "42", "--types", "wall", "--count", "1", "--no-blender", "--out", "x"])))[0]
        self.assertEqual(build_spec(specs[0]).digest(), build_spec(plain).digest())  # pinning draws the same values
        digests = {build_spec(s).digest() for s in specs}
        self.assertEqual(len(digests), 5)  # five different pieces

    def test_user_parameters_win_over_the_pinned_outline(self):
        specs = self.plan("wall", extra=("--param", "wall.length=4.0"))
        self.assertEqual({str(s["params"]["length"]) for s in specs}, {"4.0"})

    def test_manifest_reports_which_types_keep_their_outline(self):
        from cubegen.cli import build_config, make_parser
        from cubegen.pipeline import generate_batch

        with tempfile.TemporaryDirectory() as out:
            args = make_parser().parse_args(["generate", "--seed", "42", "--types", "test_wall_modules,crate",
                                             "--count", "4", "--set", "--no-blender", "--out", out])
            manifest = generate_batch(build_config(args), log=lambda m: None)
            sets = {s["type"]: s for s in manifest["sets"]}
            self.assertTrue(sets["test_wall_modules"]["outline_ok"])
            self.assertEqual(sets["test_wall_modules"]["deviation_m"], 0.0)
            self.assertEqual(len(sets["test_wall_modules"]["members"]), 4)
            self.assertFalse(sets["crate"]["outline_ok"])  # depth is rolled inside the builder, not a parameter
            self.assertGreater(sets["crate"]["deviation_m"], 0.01)
            self.assertIsNone(sets["crate"]["preview"])  # no Blender, no previews, no row

    def test_set_pieces_join_without_a_random_scale(self):
        from cubegen.models import generate_asset

        for seed in range(8):
            lo, hi = generate_asset("test_wall_modules", seed).bbox()
            self.assertAlmostEqual(hi[2] - lo[2], 3.0, delta=0.005)
            self.assertAlmostEqual(lo[0], -1.0, delta=0.005)  # stripes may reach 2 mm past the joint
            self.assertAlmostEqual(hi[0], 1.0, delta=0.005)


@unittest.skipUnless(HAS_TOOLS, "Blender and ImageMagick required")
class StyleTestRunTest(unittest.TestCase):
    def test_one_bake_two_schemes_reproducible(self):
        def run(out):
            result = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "style_test.py"), "--models", "crate",
                                     "--size", "64", "--render-size", "64", "--samples", "4", "--bake-samples", "4",
                                     "--device", "cpu", "--out", out], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout

        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            log = run(a)
            run(b)
            self.assertIn("Crate_000: bake", log)
            with open(os.path.join(a, "style_test.json"), "r", encoding="utf-8") as fh:
                report = json.load(fh)
            self.assertEqual(report["paints"], ["industrial", "crystal"])
            self.assertEqual(report["per_model"]["Crate_000"]["device"], "CPU")
            for name in ("Crate_000_W0", "Crate_000_AO", "Crate_000_Edge", "Crate_000_Up", "Crate_000_Height",
                         "Crate_000_Diffuse",
                         "Crate_000_Normal", "Crate_000_industrial_Albedo", "Crate_000_crystal_Albedo",
                         "Crate_000_crystal_Emission"):
                with open(os.path.join(a, name + ".png"), "rb") as fa, open(os.path.join(b, name + ".png"), "rb") as fb:
                    self.assertEqual(fa.read(), fb.read(), name)  # same maps, same scheme -> same bytes
            self.assertTrue(os.path.isfile(os.path.join(a, "style_test.png")))
            for row in ("today", "tiled", "industrial", "crystal"):
                self.assertTrue(os.path.isfile(os.path.join(a, f"Crate_000_{row}.png")), row)


if __name__ == "__main__":
    unittest.main()
