"""cubegen 0.21.0 "Monolith": one renderer for static models, the workbench budget in bytes, an index instead of
reading every file, named steps and bands, directories instead of searches (findings of Cube Escape 0.49)."""

import json
import os
import struct
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from cubegen import cache as cache_mod  # noqa: E402
from cubegen.asset import DECORATIVE_PARTS  # noqa: E402
from cubegen.contract import RUNTIME_BUDGET, check_runtime_budget, glb_summary, texture_bytes  # noqa: E402
from cubegen.models import generate_asset  # noqa: E402


def _glb(path, triangles=12, images=((64, 64),), materials=2, nodes=1, pad=0):
    """A minimal GLB: one indexed primitive, embedded PNG headers (only IHDR is read), optional padding bytes."""
    binary = b""
    views, imgs = [], []
    for w, h in images:
        png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I4sII", 13, b"IHDR", w, h) + b"\x08\x06\x00\x00\x00" + b"\x00" * 4
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(png)})
        imgs.append({"bufferView": len(views) - 1, "mimeType": "image/png"})
        binary += png
    binary += b"\x00" * pad
    binary += b"\x00" * (-len(binary) % 4)
    # each image as a base colour of one material (0.21.1: only textures a material loads count)
    mats = [{"name": f"M{i}"} for i in range(materials)]
    for k in range(len(imgs)):
        mats[k % materials].setdefault("pbrMetallicRoughness", {})["baseColorTexture"] = {"index": k}
    gltf = {"asset": {"version": "2.0"}, "nodes": [{"name": f"N{i}"} for i in range(nodes)],
            "materials": mats, "textures": [{"source": k} for k in range(len(imgs))],
            "accessors": [{"count": triangles * 3, "componentType": 5125, "type": "SCALAR"}],
            "meshes": [{"primitives": [{"indices": 0, "attributes": {}}]}],
            "bufferViews": views, "images": imgs, "buffers": [{"byteLength": len(binary)}]}
    text = json.dumps(gltf).encode("utf-8")
    text += b" " * (-len(text) % 4)
    data = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(text) + 8 + len(binary))
    data += struct.pack("<II", len(text), 0x4E4F534A) + text + struct.pack("<II", len(binary), 0x004E4942) + binary
    with open(path, "wb") as fh:
        fh.write(data)


class SingleRendererTest(unittest.TestCase):
    def test_static_model_becomes_one_object_with_the_same_look(self):
        for t, seed in (("crate", 1), ("console", 2), ("wall", 3), ("rock", 4), ("window_wall", 5)):
            a = generate_asset(t, seed)
            box, stats = a.bbox(), a.stats()
            joined = a.merge_static()
            self.assertTrue(joined, t)
            meshes = [o for o in a.objects if o.mesh is not None]
            self.assertEqual(len(meshes), 1, t)
            self.assertEqual(a.bbox(), box, t)
            self.assertEqual(a.stats()["triangles"], stats["triangles"], t)
            self.assertEqual(a.stats()["materials"], stats["materials"], t)  # materials stay sub-meshes
            a.validate_contract(t)  # colliders and children point at the kept object
            self.assertEqual(a.meta["single_renderer"]["joined"], joined)

    def test_gameplay_and_meaningful_parts_stay(self):
        door = generate_asset("door", 1)
        self.assertEqual(door.merge_static(), [])  # a behaviour: never
        for t in ("breakable_platform", "fluid_basin", "floor_grate", "airlock_chamber", "turbine"):
            a = generate_asset(t, 1)
            names = [o.name for o in a.objects if o.mesh is not None]
            self.assertEqual(a.merge_static(), [], t)  # Tile_<n>, Fluid, Panel ...: a Unity profile may bind them
            self.assertEqual([o.name for o in a.objects if o.mesh is not None], names, t)
        self.assertNotIn("Panel", DECORATIVE_PARTS)
        self.assertNotIn("Fluid", DECORATIVE_PARTS)

    def test_option_reaches_spec_manifest_and_leaves_the_default_alone(self):
        from cubegen.cli import build_config, make_parser
        from cubegen.pipeline import build_spec, generate_batch, plan_models

        args = ["generate", "--seed", "4", "--types", "crate,pillar", "--count", "1", "--no-blender"]
        plain = plan_models(build_config(make_parser().parse_args(args + ["--out", "x"])))
        single = plan_models(build_config(make_parser().parse_args(args + ["--single-renderer", "--out", "x"])))
        self.assertNotIn("single_renderer", plain[0])
        self.assertTrue(single[0]["single_renderer"])
        self.assertGreater(len([o for o in build_spec(plain[0]).objects if o.mesh is not None]), 1)
        with tempfile.TemporaryDirectory() as out:
            manifest = generate_batch(build_config(make_parser().parse_args(args + ["--single-renderer", "--out",
                                                                                    out])), log=lambda m: None)
        self.assertEqual({e["renderers"] for e in manifest["models"]}, {1})


class RuntimeBudgetTest(unittest.TestCase):
    def test_glb_summary_and_budget_in_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "a.glb")
            _glb(path, triangles=40, images=((256, 256), (128, 64)), materials=3, nodes=2)
            info = glb_summary(path)
            self.assertEqual((info["triangles"], info["materials"], info["nodes"]), (40, 3, 2))
            self.assertEqual(info["images"], [(256, 256), (128, 64)])
            self.assertEqual(info["bytes"], os.path.getsize(path))
            self.assertEqual(check_runtime_budget(path), [])
            # 0.21.1: Cube Escape 0.51 loads compressed (BC3, 1 byte per pixel) - 0.21.0 counted RGBA32 (4 bytes)
            self.assertEqual(texture_bytes(2048, 2048), 2048 * 2048 * 4 // 3)
            found = check_runtime_budget(path, {"triangles": 10, "texture_bytes": 1000, "glb_bytes": 100})
            self.assertEqual(len(found), 3)
            _glb(path, images=((4096, 4096),), materials=1)
            self.assertTrue(any("larger than 2048" in f for f in check_runtime_budget(path)))
        self.assertEqual(RUNTIME_BUDGET["glb_bytes"], 32 * 1024 * 1024)  # Cube Escape CubegenGlb.Limits.MaxBytes


class IndexTest(unittest.TestCase):
    def test_unchanged_files_are_not_read_again(self):
        with tempfile.TemporaryDirectory() as d:
            files = [os.path.join(d, f"f{k}.png") for k in range(3)]
            for k, path in enumerate(files):
                with open(path, "wb") as fh:
                    fh.write(bytes([k]) * 1000)
            cache = cache_mod.OutputCache(d)
            cache.put("x", "key", files)
            self.assertEqual(cache.digest(files[0]), cache_mod.file_hash(files[0]))
            cache.save()
            again = cache_mod.OutputCache(d)
            with mock.patch.object(cache_mod, "file_hash", side_effect=AssertionError("read")):
                self.assertIsNotNone(again.get("x", "key"))  # size and time unchanged: no file read
                self.assertEqual(again.digest(files[0]), cache.digest(files[0]))
            time.sleep(0.01)
            with open(files[1], "wb") as fh:
                fh.write(b"changed" * 100)
            self.assertIsNone(again.get("x", "key"))  # changed: hashed again and found different


class DirectoryTest(unittest.TestCase):
    def test_each_model_is_built_once_per_run(self):
        from cubegen import pipeline
        from cubegen.cli import build_config, make_parser

        calls = []
        real = pipeline.build_spec

        def counting(spec):
            calls.append(spec["name"])
            return real(spec)

        with tempfile.TemporaryDirectory() as out, mock.patch.object(pipeline, "build_spec", counting):
            config = build_config(make_parser().parse_args(["generate", "--seed", "3", "--types", "crate,door,wall",
                                                            "--count", "2", "--no-blender", "--out", out]))
            manifest = pipeline.generate_batch(config, log=lambda m: None)
        self.assertEqual(sorted(calls), sorted(e["name"] for e in manifest["models"]))  # 0.20: three builds each
        steps = manifest["timings"]["steps"]
        self.assertTrue({"plan_models", "build", "contract"} <= set(steps))


class PerfBandTest(unittest.TestCase):
    def test_load_classes_bands_and_verdicts(self):
        import perf_band

        self.assertEqual([perf_band.classify(v) for v in (0.2, 0.8, 1.5, None)], ["ruhig", "leicht", "stark", "ruhig"])
        rows = [{"values": {"wall": 10.0, "cpu": 4.0}, "class": "ruhig"},
                {"values": {"wall": 11.0, "cpu": 4.2}, "class": "leicht"},
                {"values": {"wall": 30.0, "cpu": 4.1}, "class": "stark"}]
        band = perf_band.band(rows)
        self.assertEqual(band["counted"], 2)
        self.assertEqual(band["steps"]["wall"]["max"], 11.0)  # the heavy run is not counted ...
        self.assertEqual(band["steps"]["cpu"]["median"], 4.1)  # ... except for the CPU time
        base = {"workloads": {"w": {"band": band}}}
        faster = perf_band.band([{"values": {"wall": 5.0, "cpu": 2.0}, "class": "ruhig"}])
        verdicts = {r["step"]: r["verdict"] for r in perf_band.compare(base, {"workloads": {"w": {"band": faster}}})["w"]}
        self.assertEqual(verdicts, {"wall": "schneller", "cpu": "schneller"})
        heavy = perf_band.band([{"values": {"wall": 50.0, "cpu": 4.15}, "class": "stark"}])
        verdicts = {r["step"]: r["verdict"] for r in perf_band.compare(base, {"workloads": {"w": {"band": heavy}}})["w"]}
        self.assertEqual(verdicts["cpu"], "gleich")
        self.assertIn("nicht gewertet", verdicts["Laufzeiten"])

    def test_unity_check_has_a_single_renderer_probe(self):
        import unity_check

        self.assertIn("--single-renderer", unity_check.PROBES["single"]["args"])


if __name__ == "__main__":
    unittest.main()
