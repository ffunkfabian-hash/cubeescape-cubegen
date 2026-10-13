"""cubegen 0.19.0 "Kaleidoscope": set-ready build kit, dressings on more types, faceted crystals, the crystal colour of
a paint scheme, variety details, the paint editor's catalog data and the Neural Engine report."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.blender import find_blender  # noqa: E402
from cubegen.imagemagick import find_imagemagick  # noqa: E402
from cubegen.models import REGISTRY, generate_asset  # noqa: E402
from cubegen.paint import COLOR_KEYS, PAINTS, SCHEME_KEYS, load_scheme  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAS_TOOLS = find_blender() is not None and find_imagemagick() is not None
BUILD_KIT = ("wall", "floor_tile", "ceiling_module", "ceiling_panel", "catwalk", "railing", "pillar", "crate", "stairs",
             "platform", "ramp", "wall_cap", "wall_corner")


def run_sets(types, seed, extra=()):
    from cubegen.cli import build_config, make_parser
    from cubegen.pipeline import generate_batch

    with tempfile.TemporaryDirectory() as out:
        args = make_parser().parse_args(["generate", "--seed", str(seed), "--types", ",".join(types), "--count", "5",
                                         "--set", "--unique", "--no-blender", "--out", out, *extra])
        return {s["type"]: s for s in generate_batch(build_config(args), log=lambda m: None)["sets"]}


class SetReadyBuildKitTest(unittest.TestCase):
    def test_every_build_kit_type_keeps_its_outline(self):
        # 0.18: 10 of these failed (crate 3.5 cm, floor_tile 4.6 cm, stairs 88 cm ...)
        for seed in (42, 7, 1234):
            sets = run_sets(BUILD_KIT, seed)
            bad = {t: s["deviation_m"] for t, s in sets.items() if not s["outline_ok"]}
            self.assertEqual(bad, {}, seed)
            self.assertEqual(sets["floor_tile"]["faces"], ["x-", "x+", "y-", "y+", "z-"])  # details may stand on top

    def test_set_pins_hold_the_shape_choices(self):
        sets = run_sets(("wall_corner", "stairs"), 42)
        self.assertIn("style", sets["wall_corner"]["pinned"])        # corner / end / tee are different pieces
        self.assertTrue({"style", "rails"} <= set(sets["stairs"]["pinned"]))

    def test_registry_checks_the_set_declaration(self):
        from cubegen.models.registry import model

        with self.assertRaises(ValueError):
            model("bad_faces_type", "Bad", "props", "x", set_faces=("x-", "w+"))(lambda rng, a: None)
        with self.assertRaises(ValueError):
            model("bad_pins_type", "Bad", "props", "x", set_pins=("nope",))(lambda rng, a: None)
        self.assertNotIn("bad_faces_type", REGISTRY)

    def test_rolled_sizes_became_parameters_without_moving_a_roll(self):
        # the value the builder rolled is now a parameter: an override replaces it, the rest of the model stays
        a = generate_asset("floor_tile", 3)
        b = generate_asset("floor_tile", 3, params={"depth": 0.3})
        self.assertAlmostEqual(a.bbox()[0][2], -a.p.used["depth"])
        self.assertAlmostEqual(b.bbox()[0][2], -0.3)
        self.assertEqual(a.meta["style"], b.meta["style"])

    def test_ceiling_slabs_stay_in_their_footprint(self):
        # 0.18: coffered ribs and the roof's ridge cap reached 4-5 cm into the neighbour (z-fighting at the joint)
        for seed in range(20):
            for style in ("coffered", "roof"):
                a = generate_asset("ceiling_module", seed, params={"style": style})
                lo, hi = a.bbox()
                size = a.p.used["size"]
                self.assertLessEqual(hi[0] - lo[0], size + 1e-6, (seed, style))
                self.assertLessEqual(hi[1] - lo[1], size + 1e-6, (seed, style))


class DressingTest(unittest.TestCase):
    def test_dressings_keep_the_set_faces_and_add_geometry(self):
        from cubegen.pipeline import outline_params

        for t in ("floor_tile", "catwalk", "pillar"):
            faces = REGISTRY[t].set_faces
            for kind in ("ruin", "organic"):
                pinned = outline_params(t, generate_asset(t, 0, params={"dressing": kind}).p.used)
                edges = []
                for seed in range(8):
                    a = generate_asset(t, seed, params=dict(pinned, dressing=kind))
                    lo, hi = a.bbox()
                    edges.append([(hi if f[1] == "+" else lo)["xyz".index(f[0])] for f in faces])
                    self.assertEqual(a.meta["dressing"], kind)
                spread = max(max(e[i] for e in edges) - min(e[i] for e in edges) for i in range(len(faces)))
                self.assertLess(spread, 0.01, (t, kind))
                plain = generate_asset(t, 1, params=dict(pinned, dressing="none")).stats()["triangles"]
                dressed = generate_asset(t, 1, params=dict(pinned, dressing=kind)).stats()["triangles"]
                self.assertGreater(dressed, plain, (t, kind))

    def test_none_is_not_recorded_so_existing_sidecars_stay(self):
        for t in ("floor_tile", "catwalk", "pillar", "rock"):
            used = generate_asset(t, 2).p.used
            self.assertNotIn("dressing", used, t)
            self.assertNotIn("crystal_cut", used, t)


class CrystalTest(unittest.TestCase):
    def test_faceted_cut_changes_only_the_crystals(self):
        prism = generate_asset("rock", 5, params={"crystals": 3})
        faceted = generate_asset("rock", 5, params={"crystals": 3, "crystal_cut": "faceted"})
        self.assertEqual(prism.get("Rock").mesh.verts, faceted.get("Rock").mesh.verts)  # own stream: rock untouched
        self.assertNotEqual(prism.get("Crystals").mesh.verts, faceted.get("Crystals").mesh.verts)
        self.assertEqual(set(faceted.get("Crystals").mesh.roles), {"M_Crystal"})

    def test_every_scheme_has_a_crystal_colour_and_old_files_still_load(self):
        self.assertIn("crystal_color", SCHEME_KEYS)
        self.assertIn("crystal_color", COLOR_KEYS)
        colours = {PAINTS[n]["crystal_color"] for n in PAINTS}
        self.assertGreaterEqual(len(colours), 8)  # the light of each theme, not one colour for all
        with tempfile.TemporaryDirectory() as folder:  # a 0.18 file without the key: it comes from the base
            path = os.path.join(folder, "old.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"name": "old", "base": "void"}, fh)
            self.assertEqual(load_scheme(path)[1]["crystal_color"], PAINTS["void"]["crystal_color"])

    @unittest.skipUnless(HAS_TOOLS, "Blender and ImageMagick required")
    def test_manifest_names_the_light_colours_of_the_scheme(self):
        from cubegen.cli import main

        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(main(["generate", "--seed", "2", "--pick", "hanging_crystals:0", "--paint", "void",
                                   "--param", "hanging_crystals.crystal_cut=faceted", "--texture-size", "64",
                                   "--no-render", "--no-blend", "--bake-device", "cpu", "--out", out]), 0)
            with open(os.path.join(out, "manifest.json"), "r", encoding="utf-8") as fh:
                manifest = json.load(fh)
        self.assertEqual(manifest["paint"], {"name": "void", "glow": "cyan",
                                             "crystal_color": PAINTS["void"]["crystal_color"],
                                             "edge_glow_color": PAINTS["void"]["edge_glow_color"]})


class VarietyTest(unittest.TestCase):
    def test_weakest_types_have_more_distinct_variants(self):
        from cubegen.seeds import model_seed, parse_seed
        from cubegen.variety import pick_unique

        master = parse_seed("42")
        # seed 42, 10 variants: 0.18 had ceiling_module 6, warning_beacon 6, the others 7
        for t in ("ceiling_module", "warning_beacon", "archway", "camera", "laser_mirror", "laser_receiver",
                  "laser_splitter", "tool"):
            distinct = len(pick_unique(10, lambda i, t=t: generate_asset(t, model_seed(master, t, i)),
                                       max_tries=10)[0])
            self.assertGreaterEqual(distinct, 9, t)

    def test_details_roll_from_their_own_stream(self):
        # without the details everything else is exactly the same: the moving parts and the rest of the body
        from collections import Counter
        from unittest import mock

        for t, module, helper, part in (("laser_mirror", "puzzle", "round_base", "Mirror"),
                                        ("camera", "puzzle", "wall_mount", "Rotor"),
                                        ("laser_splitter", "mechanisms", "round_base", "Prism"),
                                        ("warning_beacon", "station_wave", "pole_tower", "Glow")):
            with_details = generate_asset(t, 4)
            self.assertTrue(with_details.meta["details"], t)
            with mock.patch(f"cubegen.models.{module}.{helper}", lambda *args, **kw: None):
                plain = generate_asset(t, 4)
            self.assertEqual(with_details.get(part).mesh.verts, plain.get(part).mesh.verts, t)
            missing = Counter(plain.get("Body").mesh.verts) - Counter(with_details.get("Body").mesh.verts)
            self.assertFalse(missing, t)  # the body without details is all there, unmoved - the details only add


class CatalogTest(unittest.TestCase):
    def test_paint_editor_gets_the_full_schemes_and_the_keys(self):
        from cubegen.cli import catalog_data

        c = catalog_data()
        self.assertEqual(sorted(c["paint_schemes"]), sorted(c["paints"]))
        self.assertEqual(set(c["paint_schemes"]["ice"]), set(SCHEME_KEYS))
        self.assertEqual(c["paint_fields"]["colors"], list(COLOR_KEYS))
        self.assertEqual(c["paint_fields"]["glow"], ["cyan", "red", "orange"])
        self.assertEqual(c["paints"]["organic"], {"label": "Organic", "glow": "cyan"})  # unchanged for old readers


class VisionReportTest(unittest.TestCase):
    def test_icon_findings(self):
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        from vision_report import icon_findings

        self.assertEqual(icon_findings({"box": [0.25, 0.2, 0.5, 0.6], "objects": 1, "border": 0}), [])
        self.assertIn("angeschnitten (12 Randpixel)", icon_findings({"box": [0.2, 0.2, 0.5, 0.6], "objects": 1,
                                                                     "border": 12}))
        self.assertEqual(icon_findings({"box": [0, 0, 0, 0], "objects": 0, "border": 0}),
                         ["kein Blickpunkt gefunden"])
        self.assertTrue(any(f.startswith("klein") for f in
                            icon_findings({"box": [0.4, 0.4, 0.2, 0.2], "objects": 1, "border": 0})))

    @unittest.skipUnless(HAS_TOOLS and sys.platform == "darwin" and shutil.which("swiftc"),
                         "macOS with swiftc, Blender and ImageMagick required")
    def test_report_on_a_real_run(self):
        from cubegen.cli import main

        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(main(["generate", "--seed", "1", "--types", "crate", "--count", "2", "--no-blend",
                                   "--render-size", "128", "--icon-size", "128", "--out", out]), 0)
            result = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "vision_report.py"), out, "--json",
                                     os.path.join(out, "vision.json")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with open(os.path.join(out, "vision.json"), "r", encoding="utf-8") as fh:
                rep = json.load(fh)
            self.assertEqual((rep["previews"], rep["icons_checked"]), (2, 2))
            self.assertEqual(len(rep["closest"]), 1)  # one pair of the same type


if __name__ == "__main__":
    unittest.main()
