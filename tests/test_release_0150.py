"""cubegen 0.15.0 "Stoppuhr": byte-identical PNGs, output cache, stage timings, work packages, bake device, test tiers."""

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.blender import find_blender  # noqa: E402
from cubegen.cache import OutputCache, input_key  # noqa: E402
from cubegen.cli import build_config, main, make_parser  # noqa: E402
from cubegen.imagemagick import find_imagemagick  # noqa: E402
from cubegen.pipeline import BatchConfig, generate_batch, model_cost, stage_report  # noqa: E402

HAS_MAGICK = find_imagemagick() is not None
HAS_BLENDER = find_blender() is not None


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def png_chunks(path):
    data, pos, kinds = read_bytes(path), 8, []
    while pos < len(data):
        length = int.from_bytes(data[pos:pos + 4], "big")
        kinds.append((data[pos + 4:pos + 8], data[pos + 8:pos + 8 + length]))
        pos += 12 + length
    return kinds


def pngs(folder):
    out = {}
    for root, _, files in os.walk(folder):
        for name in files:
            if name.endswith(".png"):
                path = os.path.join(root, name)
                out[os.path.relpath(path, folder)] = read_bytes(path)
    return out


def config(out, *extra):
    return build_config(make_parser().parse_args(["generate", "--seed", "7", "--types", "crate,door", "--out", out,
                                                  *extra]))


@unittest.skipUnless(HAS_MAGICK, "ImageMagick not installed")
class ReproduciblePngTest(unittest.TestCase):
    def test_imagemagick_writes_no_time_stamps(self):
        # 0.14.2: every PNG carried tIME / date:create - same pixels, different bytes on every run
        from cubegen.textures import build_texture_set

        im = find_imagemagick()
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            build_texture_set(im, a, 64, log=lambda m: None)
            build_texture_set(im, b, 64, log=lambda m: None)
            first, second = pngs(a), pngs(b)
            self.assertGreater(len(first), 20)
            self.assertEqual(first, second)
            source = os.path.join(a, sorted(first)[0])
            for out in (a, b):
                im.make_icon(source, os.path.join(out, "icon.png"), 64)
                im.contact_sheet([source, source], ["one", "two"], os.path.join(out, "sheet.png"), title="t")
                im.material_swatch(os.path.join(out, "swatch.png"), size=32)
            for name in ("icon.png", "sheet.png", "swatch.png"):
                self.assertEqual(read_bytes(os.path.join(a, name)), read_bytes(os.path.join(b, name)), name)
                kinds = png_chunks(os.path.join(a, name))
                self.assertNotIn(b"tIME", [k for k, _ in kinds], name)
                self.assertFalse(any(b"date:" in body for k, body in kinds if k in (b"tEXt", b"zTXt", b"iTXt")), name)


class OutputCacheTest(unittest.TestCase):
    def test_reuse_only_with_same_key_and_untouched_files(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "a.png")
            with open(path, "wb") as fh:
                fh.write(b"one")
            cache = OutputCache(folder)
            cache.put("a", "k1", [path], data={"x": 1})
            cache.save()
            again = OutputCache(folder)
            self.assertEqual(again.get("a", "k1")["data"], {"x": 1})
            self.assertIsNone(again.get("a", "k2"))  # other inputs
            self.assertIsNone(OutputCache(folder, enabled=False).get("a", "k1"))  # --force
            with open(path, "wb") as fh:
                fh.write(b"two")  # changed by someone else
            self.assertIsNone(again.get("a", "k1"))
            os.remove(path)
            self.assertIsNone(again.get("a", "k1"))
        self.assertEqual(input_key("a", 1, {"b": 2}), input_key("a", 1, {"b": 2}))
        self.assertNotEqual(input_key("a", 1), input_key("a", 2))

    def test_broken_cache_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            with open(os.path.join(folder, ".cubegen_cache.json"), "w", encoding="utf-8") as fh:
                fh.write("{not json")
            self.assertEqual(OutputCache(folder).entries, {})


@unittest.skipUnless(HAS_MAGICK, "ImageMagick not installed")
class PipelineCacheTest(unittest.TestCase):
    def test_unchanged_textures_and_swatch_are_not_rebuilt(self):
        with tempfile.TemporaryDirectory() as out:
            cfg = config(out, "--no-blender", "--textures", "tiled", "--texture-size", "64")
            generate_batch(cfg, log=lambda m: None)
            textures = os.path.join(out, "models", "Textures")
            albedo = os.path.join(textures, "MT_Metal_Albedo.png")
            swatch = os.path.join(out, "materials.png")
            original = read_bytes(albedo)
            stamps = {p: os.stat(p).st_mtime_ns for p in (albedo, swatch)}

            lines = []
            generate_batch(cfg, log=lines.append)
            self.assertTrue(any(line.startswith("textures unchanged") for line in lines), lines)
            self.assertEqual({p: os.stat(p).st_mtime_ns for p in stamps}, stamps)

            with open(albedo, "ab") as fh:  # a file changed behind the cache's back is rebuilt
                fh.write(b"x")
            lines = []
            generate_batch(cfg, log=lines.append)
            self.assertFalse(any(line.startswith("textures unchanged") for line in lines))
            self.assertEqual(read_bytes(albedo), original)

            cfg.force = True
            lines = []
            generate_batch(cfg, log=lines.append)
            self.assertFalse(any(line.startswith("textures unchanged") for line in lines))
            self.assertEqual(read_bytes(albedo), original)

    def test_manifest_reports_stage_timings(self):
        with tempfile.TemporaryDirectory() as out:
            lines = []
            generate_batch(config(out, "--no-blender", "--textures", "tiled", "--texture-size", "64"),
                           log=lines.append)
            with open(os.path.join(out, "manifest.json"), "r", encoding="utf-8") as fh:
                timings = json.load(fh)["timings"]
            self.assertEqual(timings["models_built"], 2)
            self.assertTrue({"plan", "textures", "export", "images"} <= set(timings["seconds"]))
            self.assertTrue({"textures", "export", "images"} <= set(timings["budgets"]))
            self.assertIsInstance(timings["slow"], list)
            self.assertTrue(any(line.startswith("timings: ") for line in lines))


class StageBudgetTest(unittest.TestCase):
    def test_budgets_scale_and_flag_slow_stages(self):
        cfg = BatchConfig(seed=1, models={"crate": 1}, out_dir="x")
        report = stage_report({"textures": 1.0, "images": 9.0}, {"bake": 1.0}, 3, cfg)
        self.assertEqual(report["budgets"], {"textures": 15.0, "images": 1.5, "bake": 12.0})
        self.assertEqual(report["slow"], ["images"])
        cfg.texture_size = 1024  # four times the pixels
        report = stage_report({"textures": 1.0}, {"bake": 1.0}, 3, cfg)
        self.assertEqual(report["budgets"], {"textures": 60.0, "bake": 48.0})
        self.assertEqual(stage_report({"export": 0.1}, {}, 0, cfg)["budgets"], {"export": 1.5})  # at least one model

    def test_bake_device_is_validated(self):
        cfg = BatchConfig(seed=1, models={"crate": 1}, out_dir="x", bake_device="npu")
        with self.assertRaises(ValueError):
            cfg.validate()
        for device in ("auto", "cpu", "gpu"):
            BatchConfig(seed=1, models={"crate": 1}, out_dir="x", bake_device=device).validate()

    def test_work_packages_start_with_the_biggest_model(self):
        from cubegen.pipeline import plan_models

        specs = plan_models(build_config(make_parser().parse_args(
            ["generate", "--seed", "1", "--types", "crate,sliding_puzzle", "--no-blender", "--out", "x"])),
            lambda m: None)
        cost = {s["type"]: model_cost(s) for s in specs}
        self.assertGreater(cost["sliding_puzzle"], cost["crate"])


class TestTiersTest(unittest.TestCase):
    def test_every_module_runs_in_full_and_quick_leaves_out_sweeps_and_blender(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
        import run_tests

        full = [m for members in run_tests.groups("full").values() for m in members]
        self.assertEqual(sorted(full), run_tests.modules())
        self.assertEqual(len(full), len(set(full)))
        quick = {m for members in run_tests.groups("quick").values() for m in members}
        self.assertFalse(quick & set(run_tests.SWEEPS))
        self.assertIn("test_golden", quick)  # bit-identical models stay in every tier
        self.assertNotIn("CUBEGEN_SKIP_BLENDER", {k for k, v in run_tests.environment("full").items()
                                                  if k not in os.environ})
        self.assertEqual(run_tests.environment("quick")["CUBEGEN_SKIP_BLENDER"], "1")
        self.assertEqual(run_tests.environment("standard")["CUBEGEN_SKIP_BLENDER"], "1")

    def test_skip_blender_hides_only_an_implicit_blender(self):
        old = os.environ.get("CUBEGEN_SKIP_BLENDER")
        os.environ["CUBEGEN_SKIP_BLENDER"] = "1"
        try:
            self.assertIsNone(find_blender())
            with tempfile.NamedTemporaryFile() as fake:
                self.assertEqual(find_blender(fake.name), fake.name)
        finally:
            if old is None:
                os.environ.pop("CUBEGEN_SKIP_BLENDER")
            else:
                os.environ["CUBEGEN_SKIP_BLENDER"] = old


@unittest.skipUnless(HAS_MAGICK and HAS_BLENDER, "Blender and ImageMagick required")
class BakeTest(unittest.TestCase):
    def test_baked_atlas_is_byte_identical_across_runs_and_work_packages(self):
        # Roboter-Generator 1.8: Blender's UV packing can differ between runs. Measured 0.15.0: Cubegen's atlas
        # (Smart UV Project per asset) is stable - this keeps it that way, also with parallel work packages.
        # 0.26.0: without the shared cache - runs b and c would copy run a's unit (export + bake) instead of baking
        names = ("Crate_000", "Door_000", "Door_001")
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"CUBEGEN_CACHE": "0"}):
            outs = {}
            for run, extra in (("a", []), ("b", []), ("c", ["--jobs", "2"])):
                out = os.path.join(tmp, run)
                args = ["generate", "--seed", "7", "--pick", "crate:0,door:0,door:1",
                        "--textures", "baked", "--texture-size", "64", "--bake-device", "cpu", "--no-render",
                        "--no-blend", "--out", out, *extra]
                self.assertEqual(main(args), 0)
                outs[run] = out
            maps = {run: {k: v for k, v in pngs(os.path.join(out, "models", "Textures")).items()
                          if k.startswith("MTA_")} for run, out in outs.items()}
            self.assertEqual(len(maps["a"]), 4 * len(names))
            self.assertEqual(maps["a"], maps["b"])
            self.assertEqual(maps["a"], maps["c"])
            with open(os.path.join(outs["c"], "manifest.json"), "r", encoding="utf-8") as fh:
                manifest = json.load(fh)
            self.assertEqual([m["name"] for m in manifest["models"]], list(names))  # spec order, not finish order
            self.assertEqual({m["bake_device"] for m in manifest["models"]}, {"CPU"})
            self.assertIn("bake", manifest["timings"]["worker_seconds"])


if __name__ == "__main__":
    unittest.main()
