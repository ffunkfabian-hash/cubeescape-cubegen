"""cubegen 0.16.0 "Overdrive": --jobs auto, parallel ImageMagick (textures, icons, contact sheet), textures built while
Blender starts, one bake pass for roughness + metallic, load and worker statistics, faster quality checks."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.blender import find_blender  # noqa: E402
from cubegen.cli import build_config, make_parser  # noqa: E402
from cubegen.imagemagick import find_imagemagick  # noqa: E402
from cubegen.pipeline import BatchConfig, auto_jobs, generate_batch  # noqa: E402

HAS_MAGICK = find_imagemagick() is not None
HAS_BLENDER = find_blender() is not None


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def config(**values):
    return BatchConfig(seed=1, models={"crate": 1}, out_dir="x", **values)


class AutoJobsTest(unittest.TestCase):
    def test_only_as_many_processes_as_pay_off(self):
        cores = os.cpu_count() or 1
        self.assertEqual(auto_jobs(1, config(render=False), None), 1)
        self.assertEqual(auto_jobs(10, config(render=False), None), 1)  # 0.3 s of export: one process
        many = auto_jobs(1000, config(), "workbench")
        self.assertEqual(many, max(1, min(cores - 1, 1000)))
        self.assertLessEqual(auto_jobs(1000, config(), "eevee"), 3)  # the GPU is busy from 3-4 processes
        self.assertLessEqual(auto_jobs(100, config(textures="baked", bake_device="cpu"), "workbench"), 2)
        self.assertLessEqual(auto_jobs(100, config(textures="baked", texture_size=1024), "workbench"), 3)

    def test_cli_accepts_auto_and_numbers(self):
        parse = make_parser().parse_args
        self.assertIsNone(parse(["generate"]).jobs)  # not given -> BatchConfig default 0 = auto
        self.assertEqual(parse(["generate", "--jobs", "auto"]).jobs, 0)
        self.assertEqual(parse(["generate", "--jobs", "3"]).jobs, 3)
        with self.assertRaises(SystemExit):
            parse(["generate", "--jobs", "0"])
        self.assertEqual(BatchConfig(seed=1, models={}, out_dir="x").jobs, 0)


class QualitySpeedupTest(unittest.TestCase):
    def test_prepared_ray_faces_give_the_same_answers(self):
        from cubegen.models import generate_asset
        from cubegen.quality import _inside_solid, ray_faces

        asset = generate_asset("machine", 42)
        mesh = asset.meshes()[0].mesh
        part = mesh.parts[0]
        verts = mesh.verts[part.v0:part.v1]
        faces = [tuple(i - part.v0 for i in mesh.faces[fi]) for fi in range(part.f0, part.f1)]
        lo = [min(v[i] for v in verts) for i in range(3)]
        hi = [max(v[i] for v in verts) for i in range(3)]
        prepared = ray_faces(verts, faces)
        points = [tuple(lo[i] + (hi[i] - lo[i]) * (k + 0.5) / 7 for i in range(3)) for k in range(7)]
        points += [tuple(lo[i] - 0.1 for i in range(3)), tuple(hi[i] + 0.1 for i in range(3))]
        self.assertEqual([_inside_solid(p, verts, faces) for p in points],
                         [_inside_solid(p, verts, faces, prepared) for p in points])
        self.assertTrue(any(_inside_solid(p, verts, faces, prepared) for p in points))


@unittest.skipUnless(HAS_MAGICK, "ImageMagick not installed")
class ParallelImageMagickTest(unittest.TestCase):
    def test_parallel_texture_set_is_byte_identical(self):
        from cubegen.textures import build_texture_set, plan_texture_set

        im = find_imagemagick()
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            one = build_texture_set(im, a, 64, log=lambda m: None, workers=1)
            many = build_texture_set(im, b, 64, log=lambda m: None, workers=0)
            self.assertEqual(one, plan_texture_set(a))  # Blender may start with the plan before the maps exist
            self.assertEqual(many, plan_texture_set(b))
            for info in one.values():
                for kind, path in info["paths"].items():
                    other = os.path.join(b, os.path.basename(path))
                    self.assertEqual(read_bytes(path), read_bytes(other), os.path.basename(path))

    def test_contact_sheet_in_blocks_has_the_same_pixels(self):
        im = find_imagemagick()
        with tempfile.TemporaryDirectory() as d:
            images = []
            for k in range(31):  # block of 24 + 7: a short last block and a short last row
                path = os.path.join(d, f"p{k:02d}.png")
                im.run(["-size", "48x48", f"xc:rgb({(k * 37) % 256},{(k * 91) % 256},{(k * 53) % 256})", path])
                images.append(path)
            labels = [f"Model_{k:03d}" for k in range(len(images))]
            for count in (5, 24, 25, 31):
                one, blocks = os.path.join(d, f"one{count}.png"), os.path.join(d, f"blocks{count}.png")
                im.contact_sheet(images[:count], labels[:count], one, title="Sheet", workers=1)
                im.contact_sheet(images[:count], labels[:count], blocks, title="Sheet", workers=0)
                diff = subprocess.run(["magick", "compare", "-metric", "AE", one, blocks, "null:"],
                                      capture_output=True, text=True)
                self.assertEqual(diff.stderr.split()[0], "0", count)

    def test_timings_report_load_and_workers(self):
        with tempfile.TemporaryDirectory() as out:
            args = make_parser().parse_args(["generate", "--seed", "3", "--types", "crate", "--no-blender",
                                             "--out", out])
            generate_batch(build_config(args), log=lambda m: None)
            with open(os.path.join(out, "manifest.json"), "r", encoding="utf-8") as fh:
                timings = json.load(fh)["timings"]
            self.assertEqual(timings["load"]["cores"], os.cpu_count())
            self.assertIn("start", timings["load"])
            self.assertIn("end", timings["load"])
            self.assertEqual(timings["workers"], [])  # no Blender
            self.assertEqual(timings["overlap"], [])


@unittest.skipUnless(HAS_MAGICK and HAS_BLENDER, "Blender and ImageMagick required")
class OverlapTest(unittest.TestCase):
    def test_blender_starts_while_the_textures_are_built(self):
        with tempfile.TemporaryDirectory() as out:
            lines = []
            args = make_parser().parse_args(["generate", "--seed", "3", "--types", "crate,door", "--textures", "tiled",
                                             "--texture-size", "64", "--no-render", "--no-blend", "--jobs", "2",
                                             "--out", out])
            generate_batch(build_config(args), log=lines.append)
            with open(os.path.join(out, "manifest.json"), "r", encoding="utf-8") as fh:
                manifest = json.load(fh)
            self.assertEqual(manifest["timings"]["overlap"], ["textures"])
            self.assertEqual(len(manifest["timings"]["workers"]), 2)
            self.assertEqual(sum(w["models"] for w in manifest["timings"]["workers"]), 2)
            self.assertTrue(os.path.isfile(os.path.join(out, "models", "Textures", "MT_Metal_Albedo.png")))
            self.assertTrue(any("2 process(es)" in line for line in lines), lines)


@unittest.skipUnless(HAS_MAGICK, "ImageMagick not installed")
class ProfileToolTest(unittest.TestCase):
    def test_profile_run_prints_the_expensive_functions(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        run = subprocess.run([sys.executable, os.path.join(root, "tools", "profile_run.py"), "--top", "5", "--",
                              "check", "--types", "crate", "--count", "1"], capture_output=True, text=True, cwd=root)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("function calls", run.stdout)
        self.assertIn("quality.py", run.stdout)


if __name__ == "__main__":
    unittest.main()
