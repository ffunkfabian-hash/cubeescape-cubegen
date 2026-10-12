"""cubegen 0.18.0 "Chameleon": paint schemes on every type, own scheme from a file, dressings per theme."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.blender import find_blender  # noqa: E402
from cubegen.imagemagick import find_imagemagick  # noqa: E402
from cubegen.paint import (BUILTIN_PAINTS, PAINTS, check_scheme, compose, hex_rgb, load_scheme,  # noqa: E402
                           paint_names, register_scheme, weight_layout)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE = os.path.join(ROOT, "paints", "custom_example.json")  # not under recipes/: it is no recipe
HAS_TOOLS = find_blender() is not None and find_imagemagick() is not None
try:  # numpy ships with Blender's Python; the formula test runs where it is installed
    import numpy as np
except ImportError:  # pragma: no cover - depends on the interpreter
    np = None


def _write(folder, data, name="scheme.json"):
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


class GroundIsNeutralTest(unittest.TestCase):
    def test_ground_is_a_muted_base_in_every_scheme(self):
        # floors carry M_Ground: no accent colour (0.17.0 painted whole floors orange)
        for name in BUILTIN_PAINTS:
            colors = PAINTS[name]["colors"]
            r, g, b = hex_rgb(colors["M_Ground"])
            self.assertLess(max(r, g, b) - min(r, g, b), 0.4, name)  # sand may be sandy, never signal orange
            self.assertNotEqual(colors["M_Ground"], colors["M_HazardOrange"], name)

    @unittest.skipUnless(np is not None, "numpy required (Blender's Python has it)")
    def test_dust_and_moss_leave_patches_instead_of_covering_the_top(self):
        size = 64
        layout = weight_layout(["M_Wall"])
        weights = [np.zeros((size, size, 3), np.float32)]
        weights[0][..., 0] = 1.0
        ones, zeros = np.ones((size, size), np.float32), np.zeros((size, size), np.float32)
        noise = np.tile(np.linspace(0.0, 1.0, size, dtype=np.float32), (size, 1))
        for name in ("sand", "organic", "ice"):
            plain = compose(weights, layout, ones, zeros, zeros, noise, name)["albedo"]
            top = compose(weights, layout, ones, zeros, ones, noise, name)["albedo"]
            changed = np.abs(top - plain).sum(axis=2) > 0.02
            self.assertGreater(changed.mean(), 0.05, name)  # the top does get dust / moss / snow ...
            self.assertLess(changed.mean(), 0.9, name)      # ... but not everywhere


class CustomSchemeTest(unittest.TestCase):
    def test_example_file_fills_missing_keys_from_its_base(self):
        name, scheme = load_scheme(EXAMPLE)
        self.assertEqual(name, "rust_bucket")
        self.assertEqual(scheme["label"], "Rust Bucket")
        self.assertEqual(scheme["colors"]["M_Wall"], "#6b3a22")                   # given
        self.assertEqual(scheme["colors"]["M_Ground"], PAINTS["ruin"]["colors"]["M_Ground"])  # merged from ruin
        self.assertEqual(scheme["roughness"], PAINTS["ruin"]["roughness"])
        self.assertNotIn("rust_bucket", paint_names())  # the list offers only the built-in schemes
        self.assertIs(check_scheme(scheme), scheme)

    def test_bad_files_are_rejected(self):
        bad = [{"name": "industrial"},                       # a built-in name
               {"name": "x y"},                              # not a plain name
               {"name": "mine", "base": "neon"},            # unknown base
               {"name": "mine", "wear": 1.5},               # out of range
               {"name": "mine", "glow": "green"},           # no such glow colour
               {"name": "mine", "colors": {"M_Wall": "red"}},          # not #rrggbb
               {"name": "mine", "colors": {"M_GlowCyan": "#ffffff"}},  # not a painted material
               {"name": "mine", "colors": 3},                # not an object
               {"name": "mine", "shine": 0.5}]               # unknown key
        with tempfile.TemporaryDirectory() as folder:
            for data in bad:
                with self.assertRaises(ValueError, msg=data):
                    load_scheme(_write(folder, data))
        with self.assertRaises(ValueError):
            register_scheme("industrial", dict(PAINTS["industrial"]))

    def test_cli_and_recipe_load_the_file_and_imply_baked(self):
        from cubegen.cli import build_config, make_parser

        cfg = build_config(make_parser().parse_args(["generate", "--types", "wall", "--paint-file", EXAMPLE,
                                                     "--out", "x"]))
        cfg.validate()
        self.assertEqual((cfg.paint, cfg.textures, cfg.style.glow), ("rust_bucket", "baked", "red"))
        self.assertEqual(cfg.paint_scheme["colors"]["M_Metal"], "#8a4a2a")
        with tempfile.TemporaryDirectory() as folder:
            _write(folder, {"name": "teal", "base": "clean", "colors": {"M_Wall": "#2a7a7a"}}, "teal.json")
            recipe = _write(folder, {"models": {"wall": 1}, "paint_file": "teal.json"}, "recipe.json")
            cfg = build_config(make_parser().parse_args(["generate", "--recipe", recipe, "--out", "x"]))
            cfg.validate()  # the recipe's path is relative to the recipe
            self.assertEqual(cfg.paint, "teal")
            self.assertEqual(cfg.paint_scheme["colors"]["M_Wall"], "#2a7a7a")
            cfg = build_config(make_parser().parse_args(["generate", "--recipe", recipe, "--paint", "ice",
                                                         "--out", "x"]))
            cfg.validate()  # --paint on the command line wins over the recipe's own scheme
            self.assertEqual((cfg.paint, cfg.paint_scheme), ("ice", None))


class DressingTest(unittest.TestCase):
    def test_dressings_keep_the_set_outline(self):
        from cubegen.models import generate_asset

        for dressing in ("none", "ruin", "organic"):
            for seed in range(6):
                lo, hi = generate_asset("test_wall_modules", seed,
                                        params={"dressing": dressing, "crystals": "some"}).bbox()
                self.assertAlmostEqual(lo[2], 0.0, delta=1e-4, msg=(dressing, seed))  # nothing below the floor
                self.assertAlmostEqual(hi[2], 3.0, delta=0.005, msg=(dressing, seed))
                self.assertAlmostEqual(lo[0], -1.0, delta=0.005, msg=(dressing, seed))
                self.assertAlmostEqual(hi[0], 1.0, delta=0.005, msg=(dressing, seed))

    def test_dressing_adds_geometry(self):
        from cubegen.models import generate_asset

        tris = {d: generate_asset("test_wall_modules", 2, params={"dressing": d}).stats()["triangles"]
                for d in ("none", "ruin", "organic")}
        self.assertGreater(tris["ruin"], tris["none"])
        self.assertGreater(tris["organic"], tris["none"])


@unittest.skipUnless(HAS_TOOLS, "Blender and ImageMagick required")
class CustomPaintExportTest(unittest.TestCase):
    def test_own_scheme_reaches_blender_and_the_manifest(self):
        from cubegen.cli import main

        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(main(["generate", "--seed", "3", "--pick", "crate:0", "--paint-file", EXAMPLE,
                                   "--texture-size", "64", "--no-render", "--no-blend", "--bake-device", "cpu",
                                   "--out", out]), 0)
            with open(os.path.join(out, "manifest.json"), "r", encoding="utf-8") as fh:
                manifest = json.load(fh)
            entry = manifest["models"][0]
            self.assertEqual(entry["paint"], "rust_bucket")
            self.assertEqual(manifest["config"]["paint_scheme"]["label"], "Rust Bucket")
            self.assertNotIn("paint_file", manifest["config"])  # no local path in the manifest
            self.assertTrue(os.path.isfile(os.path.join(out, entry["baked"]["Albedo"])))


if __name__ == "__main__":
    unittest.main()
