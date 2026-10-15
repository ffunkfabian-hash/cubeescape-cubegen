"""cubegen 0.26.0 "Stockpile": Blender results in the shared cache, a slimmer CI workflow, the release command."""

import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from cubegen import fbxpath, modelcache  # noqa: E402
from cubegen.blender import find_blender  # noqa: E402
from cubegen.cache import Store, file_hash, png_content_hash  # noqa: E402
from cubegen.cli import build_config, make_parser  # noqa: E402
from cubegen.imagemagick import find_imagemagick  # noqa: E402
from cubegen.modelcache import BakeCache, Folders, ModelCache, bake_key, model_code, model_key  # noqa: E402

import release  # noqa: E402

HAS_TOOLS = find_imagemagick() is not None and find_blender() is not None
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "crate_tiled.fbx")  # a real Blender FBX, folder /cubegen-fixture/out
FIXTURE_TEXTURES = "/cubegen-fixture/out/models/Textures"


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def write(path, data: bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def texture_strings(data):
    return [s for s in fbxpath.parse(data).strings() if b"Textures" in s]


class FbxPathTest(unittest.TestCase):
    def test_a_real_export_is_written_back_byte_for_byte(self):
        data = read(FIXTURE)
        self.assertEqual(fbxpath.parse(data).to_bytes(), data)
        self.assertEqual(fbxpath.concrete(data, {}), data)

    def test_folder_paths_become_tokens_and_back(self):
        data = read(FIXTURE)
        canonical, changed = fbxpath.canonical(data, {"textures": FIXTURE_TEXTURES, "models": "/cubegen-fixture/out/models"})
        self.assertGreater(changed, 0)
        self.assertNotIn(b"/cubegen-fixture", canonical)
        self.assertEqual(fbxpath.tokens(canonical), ["textures"])
        self.assertEqual(fbxpath.concrete(canonical, {"textures": FIXTURE_TEXTURES}), data)
        moved = fbxpath.concrete(canonical, {"textures": "/elsewhere/a much longer folder/Textures"})
        strings = texture_strings(moved)
        self.assertTrue(strings)
        absolute = [s for s in strings if s.startswith(b"/")]
        self.assertTrue(absolute and all(s.startswith(b"/elsewhere/a much longer folder/Textures/") for s in absolute))
        relative = [s for s in strings if not s.startswith(b"/")]  # RelativeFilename stays as Blender wrote it
        self.assertEqual(relative, [s for s in texture_strings(data) if not s.startswith(b"/")])
        self.assertEqual(fbxpath.parse(moved).to_bytes(), moved)  # offsets and footer padding written anew

    def test_only_whole_path_components_match(self):
        doc = fbxpath.parse(read(FIXTURE))
        doc.records[0].props.append(("S", b"/cubegen-fixture/out/models/Textures2/x.png"))
        doc.records[0].props.append(("S", b"note /cubegen-fixture/out/models/Textures/x.png"))
        data = doc.to_bytes()
        canonical, _ = fbxpath.canonical(data, {"textures": FIXTURE_TEXTURES})
        strings = fbxpath.parse(canonical).strings()
        self.assertIn(b"/cubegen-fixture/out/models/Textures2/x.png", strings)
        self.assertIn(b"note /cubegen-fixture/out/models/Textures/x.png", strings)

    def test_wide_offsets_of_newer_versions(self):
        doc = fbxpath.parse(read(FIXTURE))
        doc.version = 7500  # 64-bit record headers
        wide = doc.to_bytes()
        self.assertEqual(fbxpath.parse(wide).to_bytes(), wide)
        self.assertEqual(fbxpath.parse(wide).strings(), doc.strings())

    def test_an_unknown_layout_is_refused(self):
        data = bytearray(read(FIXTURE))
        data[-141] = 1  # the footer padding is no longer Blender's
        with self.assertRaises(ValueError):
            fbxpath.parse(bytes(data))
        with self.assertRaises(ValueError):
            fbxpath.parse(b"; ASCII FBX\n")

    def test_normalized_ignores_ids_time_and_folder(self):
        data = read(FIXTURE)
        doc = fbxpath.parse(fbxpath.concrete(fbxpath.canonical(data, {"textures": FIXTURE_TEXTURES})[0],
                                             {"textures": "/b/models/Textures"}))
        swap = {}
        for record in doc.records:  # other object IDs, as a second export draws them
            if record.name == b"Objects":
                for child in record.children:
                    if child.props and child.props[0][0] == "L":
                        new = struct.pack("<q", 1000 + len(swap))
                        swap[child.props[0][1]] = new
                        child.props[0] = ("L", new)

        def remap(record):
            record.props = [("L", swap.get(raw, raw)) if code == "L" else (code, raw) for code, raw in record.props]
            for child in record.children:
                remap(child)
        for record in doc.records:
            if record.name == b"Connections":
                remap(record)
        other = doc.to_bytes()
        self.assertNotEqual(other, data)
        self.assertEqual(fbxpath.normalized(other, {"textures": "/b/models/Textures"}),
                         fbxpath.normalized(data, {"textures": FIXTURE_TEXTURES}))
        doc.records[-1].props.append(("I", b"\x01\x00\x00\x00"))
        self.assertNotEqual(fbxpath.normalized(doc.to_bytes(), {"textures": "/b/models/Textures"}),
                            fbxpath.normalized(data, {"textures": FIXTURE_TEXTURES}))


def folders(base, textures="models/Textures", models="models"):
    out = os.path.join(base, "out")
    return Folders(os.path.join(out, models), os.path.join(out, "previews"),
                   os.path.join(out, textures) if textures else None, out)


def sample_job(f, **changes):
    job = {"formats": ["fbx"], "models_dir": f.models, "previews_dir": f.previews, "blend": "/x/out.blend",
           "textures": {"M_Metal": {"name": "MT_Metal", "maps": {"Albedo": "MT_Metal_Albedo.png"},
                                    "paths": {"Albedo": os.path.join(f.textures, "MT_Metal_Albedo.png")}}},
           "palette": None, "texture_mode": "baked", "texture_size": 128, "textures_dir": f.textures,
           "magick": "/opt/bin/magick", "bake_device": "auto", "paint": "crystal", "paint_scheme": None,
           "textures_ready": "/tmp/ready", "uv_dir": "/tmp/uvs",
           "render": {"enabled": True, "engine": "workbench", "size": 384, "samples": 32, "azimuth": 33.0,
                      "elevation": 31.0, "zoom": 1.0}}
    job.update(changes)
    return job


def sample_spec(f, **changes):
    spec = {"name": "Crate_000", "type": "crate", "index": 0, "seed": 123, "scale": 1.0, "params": {},
            "style": {"glow": "cyan"}, "models_dir": f.models, "build_key": "b" * 64}
    spec.update(changes)
    return spec


EXTRA = {"blender": "5.2.2 LTS", "magick": "ImageMagick 7.1.2", "texture_key": "t" * 64}


class ModelKeyTest(unittest.TestCase):
    def setUp(self):
        self.a, self.b = folders("/runs/a"), folders("/elsewhere/b")

    def key(self, f=None, spec=None, job=None, extra=None):
        f = f or self.a
        return model_key(spec or sample_spec(f), job or sample_job(f), f, extra or EXTRA)

    def test_the_same_inputs_in_another_folder_give_the_same_key(self):
        self.assertEqual(self.key(), self.key(self.b))
        self.assertEqual(bake_key(sample_spec(self.a), sample_job(self.a), self.a, EXTRA),
                         bake_key(sample_spec(self.b), sample_job(self.b), self.b, EXTRA))

    def test_every_input_changes_the_key(self):
        base = self.key()
        f = self.a
        variants = {
            "seed": self.key(spec=sample_spec(f, seed=124)),
            "name": self.key(spec=sample_spec(f, name="Gen_Crate_000")),
            "params": self.key(spec=sample_spec(f, params={"size": 1.2})),
            "style": self.key(spec=sample_spec(f, style={"glow": "red"})),
            "lod": self.key(spec=sample_spec(f, lod=True)),
            "formats": self.key(job=sample_job(f, formats=["fbx", "glb"])),
            "size": self.key(job=sample_job(f, texture_size=256)),
            "device": self.key(job=sample_job(f, bake_device="cpu")),
            "paint": self.key(job=sample_job(f, paint="dark")),
            "scheme": self.key(job=sample_job(f, paint="mine", paint_scheme={"colors": {"M_Wall": "#112233"}})),
            "palette": self.key(job=sample_job(f, palette={"name": "MP_Palette", "maps": {"Albedo": "a.png"}})),
            "render size": self.key(job=sample_job(f, render=dict(sample_job(f)["render"], size=256))),
            "engine": self.key(job=sample_job(f, render=dict(sample_job(f)["render"], engine="cycles"))),
            "blender": self.key(extra=dict(EXTRA, blender="4.5.3 LTS")),
            "magick": self.key(extra=dict(EXTRA, magick="ImageMagick 6.9")),
            "tile textures": self.key(extra=dict(EXTRA, texture_key="u" * 64)),
            "textures folder": self.key(f=folders("/runs/a", textures="tex")),
        }
        with mock.patch.object(modelcache, "host", lambda: ["plan9", "mips"]):  # no machine this runs on
            variants["host"] = self.key()
        with mock.patch.object(modelcache, "model_code", lambda: "c" * 64):
            variants["code"] = self.key()
        for what, key in variants.items():
            self.assertNotEqual(key, base, what)
        self.assertEqual(len(set(variants.values())), len(variants))

    def test_plumbing_and_folders_are_no_inputs(self):
        f = self.a
        same = self.key(spec=sample_spec(f, build_key="x", skip=True, bake_cache={"uvs": "/tmp/u"}),
                        job=sample_job(f, blend=None, textures_ready=None, magick="/usr/bin/convert",
                                       queue_dir="/q", uv_dir=None))
        self.assertEqual(same, self.key())

    def test_a_folder_outside_the_run_means_no_key(self):
        f = self.a
        self.assertIsNone(self.key(spec=sample_spec(f, params={"sign": "/Users/x/logo.png"})))
        self.assertIsNone(self.key(job=sample_job(f, palette={"file": "/opt/palette.png"})))

    def test_the_bake_key_leaves_out_what_comes_after_the_bake(self):
        f = self.a

        def bk(spec=None, job=None):
            return bake_key(spec or sample_spec(f), job or sample_job(f), f, EXTRA)
        base = bk()
        for job in (sample_job(f, formats=["glb"]), sample_job(f, paint="mine", paint_scheme={"wear": 0.2}),
                    sample_job(f, render=dict(sample_job(f)["render"], size=128, zoom=1.4, azimuth=10.0))):
            self.assertEqual(bk(job=job), base)
        for job in (sample_job(f, texture_size=256), sample_job(f, bake_device="gpu"),
                    sample_job(f, paint=""), sample_job(f, render=dict(sample_job(f)["render"], enabled=False)),
                    sample_job(f, render=dict(sample_job(f)["render"], engine="cycles"))):
            self.assertNotEqual(bk(job=job), base)
        self.assertNotEqual(bk(spec=sample_spec(f, style={"glow": "red"})), base)
        self.assertIsNone(bk(job=sample_job(f, texture_mode="tiled")))

    def test_model_code_ignores_the_version_only(self):
        with tempfile.TemporaryDirectory() as d:
            copy = os.path.join(d, "cubegen")
            shutil.copytree(os.path.join(ROOT, "cubegen"), copy, ignore=shutil.ignore_patterns("__pycache__"))
            same = model_code(copy)
            self.assertEqual(same, model_code())  # the location is no input
            init = os.path.join(copy, "__init__.py")
            write(init, re.sub(rb'__version__ = "[^"]+"', b'__version__ = "9.9.9"', read(init)))
            self.assertEqual(model_code(copy), same)
            for rel in ("bake.py", "models/kit.py", "contract.json"):
                path = os.path.join(copy, rel)
                original = read(path)
                write(path, original + (b"\n" if rel.endswith(".json") else b"\n# changed\n"))
                self.assertNotEqual(model_code(copy), same, rel)
                write(path, original)
            self.assertEqual(model_code(copy), same)


class ModelCacheTest(unittest.TestCase):
    """A worker result in folder a, recorded and copied into folder b (another layout too)."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = Store(os.path.join(self.dir, "store"))
        self.a = folders(os.path.join(self.dir, "a"))
        self.b = folders(os.path.join(self.dir, "b"), textures="lib/Tex", models="lib/Models")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def result(self, f):
        fbx = fbxpath.concrete(fbxpath.canonical(read(FIXTURE), {"textures": FIXTURE_TEXTURES})[0],
                               {"textures": f.textures})
        models = f.models
        files = {"fbx": write(os.path.join(models, "Crate_000.fbx"), fbx),
                 "glb": write(os.path.join(models, "Crate_000.glb"), b"glTF-binary"),
                 "obj": write(os.path.join(models, "Crate_000.obj"), b"mtllib Crate_000.mtl\no Body\nv 0 0 0\n"),
                 "gltf": write(os.path.join(models, "Crate_000.gltf"),
                               json.dumps({"buffers": [{"uri": "Crate_000.bin"}],
                                           "images": [{"uri": "Crate%20Albedo.png"},
                                                      {"uri": "data:image/png;base64,AA=="}]}).encode())}
        write(os.path.join(models, "Crate_000.mtl"), b"newmtl MTA_Crate_000\nmap_Kd Textures/a.png\n")
        write(os.path.join(models, "Crate_000.bin"), b"\x00\x01")
        write(os.path.join(models, "Crate Albedo.png"), b"albedo copy")
        neutral = os.path.join(f.textures, "Neutral")
        return {"name": "Crate_000", "files": files,
                "preview": write(os.path.join(f.previews, "Crate_000.png"), b"preview"),
                "baked": {"Albedo": write(os.path.join(f.textures, "MTP_Crate_000_crystal_Albedo.png"), b"albedo")},
                "baked_material": "MTA_Crate_000", "bake_device": "CPU", "paint": "crystal",
                "neutral": {"weights": [write(os.path.join(neutral, "Crate_000_W0.png"), b"w0")],
                            "ao": write(os.path.join(neutral, "Crate_000_AO.png"), b"ao")},
                "weight_layout": [["M_Metal", "M_Wall"]],
                "neutral_maps": {"W0": write(os.path.join(f.textures, "MTN_Crate_000_W0.png"), b"mtn")},
                "timings": {"bake": 1.0}, "engine": "BLENDER_WORKBENCH"}

    def test_a_unit_moves_into_another_folder(self):
        original = self.result(self.a)
        cache = ModelCache(self.store)
        self.assertTrue(cache.put("k" * 64, original, self.a), cache.refused)
        hit = ModelCache(self.store).fetch("k" * 64, self.b)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["files"]["fbx"], os.path.join(self.b.models, "Crate_000.fbx"))
        self.assertEqual(hit["neutral"]["weights"], [os.path.join(self.b.textures, "Neutral", "Crate_000_W0.png")])
        self.assertEqual(hit["weight_layout"], [["M_Metal", "M_Wall"]])
        self.assertEqual((hit["engine"], hit["bake_device"], hit["timings"], hit["reused"]),
                         ("BLENDER_WORKBENCH", "CPU", {}, True))
        for rel in ("Crate_000.glb", "Crate_000.obj", "Crate_000.mtl", "Crate_000.bin", "Crate Albedo.png"):
            self.assertEqual(read(os.path.join(self.b.models, rel)), read(os.path.join(self.a.models, rel)), rel)
        self.assertEqual(read(hit["preview"]), b"preview")
        moved = read(hit["files"]["fbx"])
        self.assertNotIn(self.a.out.encode(), moved)
        self.assertTrue(any(s.startswith(self.b.textures.encode() + b"/") for s in fbxpath.parse(moved).strings()))
        self.assertEqual(fbxpath.normalized(moved, {"textures": self.b.textures}),
                         fbxpath.normalized(read(original["files"]["fbx"]), {"textures": self.a.textures}))
        for folder, _, names in os.walk(self.store.root):  # nothing in the store names a folder of the runs
            for name in names:
                self.assertNotIn(self.dir.encode(), read(os.path.join(folder, name)), name)

    def test_a_broken_object_is_a_miss_and_goes(self):
        cache = ModelCache(self.store)
        self.assertTrue(cache.put("k" * 64, self.result(self.a), self.a))
        entry = self.store.lookup("k" * 64)
        fbx_sha = entry["files"][entry["data"]["canonical"][0]]
        write(self.store.object_path(fbx_sha), b"broken")
        self.assertIsNone(ModelCache(self.store).fetch("k" * 64, self.b))
        self.assertFalse(os.path.exists(self.store.object_path(fbx_sha)))
        self.assertIsNone(ModelCache(self.store).fetch("other", self.b))

    def test_what_names_a_folder_is_not_recorded(self):
        result = self.result(self.a)
        doc = fbxpath.parse(read(result["files"]["fbx"]))
        doc.records[0].props.append(("S", b"see " + self.a.out.encode()))
        write(result["files"]["fbx"], doc.to_bytes())
        cache = ModelCache(self.store)
        self.assertFalse(cache.put("k" * 64, result, self.a))
        self.assertIn("names a folder", cache.refused[0])
        outside = self.result(self.a)
        outside["preview"] = write(os.path.join(self.dir, "elsewhere.png"), b"x")
        self.assertFalse(cache.put("k" * 64, outside, self.a))
        self.assertIsNone(self.store.lookup("k" * 64))

    def test_a_bake_with_its_uvs(self):
        result = self.result(self.a)
        result["bake_uvs"] = write(os.path.join(self.dir, "uvs", "Crate_000.uvs.json"), b'{"format": 1}')
        cache = BakeCache(self.store)
        self.assertTrue(cache.put("u" * 64, result, self.a), cache.refused)
        uv_dir = os.path.join(self.dir, "uv_b")
        os.makedirs(uv_dir)
        hit = BakeCache(self.store).fetch("u" * 64, "Crate_000", self.b, uv_dir)
        self.assertEqual(read(hit["uvs"]), b'{"format": 1}')
        self.assertEqual(hit["device"], "CPU")
        self.assertEqual(hit["maps"]["layout"], [["M_Metal", "M_Wall"]])
        self.assertEqual(hit["maps"]["ao"], os.path.join(self.b.textures, "Neutral", "Crate_000_AO.png"))
        self.assertEqual(read(hit["maps"]["weights"][0]), b"w0")
        self.assertNotIn("Albedo", hit["maps"])  # a paint run reuses the neutral bake, the scheme is composed again
        result.pop("bake_uvs")
        self.assertFalse(BakeCache(self.store).put("v" * 64, result, self.a))  # no UVs, no bake entry


def generate(out, *extra, seed="19"):
    from cubegen.pipeline import generate_batch

    lines = []
    generate_batch(build_config(make_parser().parse_args(["generate", "--seed", seed, "--out", out, *extra])),
                   log=lines.append)
    return lines


def equivalent(test, a, b):
    """Folders a and b hold the same models: FBX trees (IDs, time, folder aside), the other model files and the
    maps byte for byte, previews pixel for pixel, sidecars but the generator line."""
    names = sorted(os.path.relpath(os.path.join(r, n), a) for r, _, ns in os.walk(a) for n in ns
                   if not n.startswith(".") and not n.endswith(".blend") and n != "manifest.json")
    other = sorted(os.path.relpath(os.path.join(r, n), b) for r, _, ns in os.walk(b) for n in ns
                   if not n.startswith(".") and not n.endswith(".blend") and n != "manifest.json")
    test.assertEqual(names, other)
    with open(os.path.join(b, "manifest.json"), "r", encoding="utf-8") as fh:
        engine = (json.load(fh).get("blender") or {}).get("render_engine")
    for rel in names:
        pa, pb = os.path.join(a, rel), os.path.join(b, rel)
        if rel.startswith(("previews", "icons", "contact_sheet", "set_")) and engine != "BLENDER_WORKBENCH":
            continue  # Cycles (headless CI) may render other noise each time; Workbench gives the same pixels
        if rel.endswith(".fbx"):
            fa = {"textures": os.path.join(a, "models", "Textures"), "models": os.path.join(a, "models")}
            fb = {"textures": os.path.join(b, "models", "Textures"), "models": os.path.join(b, "models")}
            test.assertEqual(fbxpath.normalized(read(pa), fa), fbxpath.normalized(read(pb), fb), rel)
        elif rel.endswith(".cubegen.json"):
            ja, jb = json.loads(read(pa)), json.loads(read(pb))
            test.assertEqual({k: v for k, v in ja.items() if k != "generator"},
                             {k: v for k, v in jb.items() if k != "generator"}, rel)
        elif rel.endswith(".png"):
            test.assertEqual(png_content_hash(pa), png_content_hash(pb), rel)
        else:
            test.assertEqual(read(pa), read(pb), rel)
    return names


@unittest.skipUnless(HAS_TOOLS, "Blender and ImageMagick required")
class SharedModelsTest(unittest.TestCase):
    ARGS = ("--types", "crate,pillar", "--count", "1", "--paint", "crystal", "--texture-size", "64")

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        patcher = mock.patch.dict(os.environ, {"CUBEGEN_CACHE": os.path.join(self.dir, "store")})
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def path(self, name):
        return os.path.join(self.dir, name)

    def test_a_second_folder_copies_the_models_and_equals_a_fresh_export(self):
        generate(self.path("a"), *self.ARGS, "--formats", "fbx,glb,obj")
        lines = generate(self.path("b"), *self.ARGS, "--formats", "fbx,glb,obj")
        self.assertIn("shared cache: 2 model(s) copied (export, bake, preview) from " + self.path("store"), lines)
        self.assertTrue(any(line.startswith("Blender: ") and " - 0 asset(s)" in line for line in lines), lines)
        with open(self.path("b/manifest.json"), "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
        self.assertEqual(manifest["timings"]["worker_seconds"], {})  # nothing built: the .blend only
        with open(self.path("a/manifest.json"), "r", encoding="utf-8") as fh:
            first = json.load(fh)
        self.assertEqual(manifest["blender"]["render_engine"], first["blender"]["render_engine"])
        with mock.patch.dict(os.environ, {"CUBEGEN_CACHE": "0"}):
            generate(self.path("fresh"), *self.ARGS, "--formats", "fbx,glb,obj")
        names = equivalent(self, self.path("b"), self.path("fresh"))
        self.assertTrue(any(n.endswith(".fbx") for n in names) and any("MTN_" in n for n in names))
        lines = generate(self.path("b"), *self.ARGS, "--formats", "fbx,glb,obj")  # third: the folder's own files
        self.assertIn("unchanged since the last run: 2 asset(s) (--force rebuilds them)", lines)

    def test_another_checkout_hits_the_cache(self):
        generate(self.path("a"), *self.ARGS, "--no-blend")
        checkout = self.path("checkout")
        shutil.copytree(os.path.join(ROOT, "cubegen"), os.path.join(checkout, "cubegen"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        result = subprocess.run([sys.executable, "-m", "cubegen", "generate", "--seed", "19", *self.ARGS, "--no-blend",
                                 "--out", os.path.join(checkout, "output")], cwd=checkout,
                                env=dict(os.environ, PYTHONPATH=""), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("shared cache: 2 model(s) copied", result.stdout)
        self.assertNotIn("Blender: ", result.stdout)  # no Blender start at all (no .blend wanted)

    def test_force_rebuilds_and_other_inputs_miss(self):
        generate(self.path("a"), *self.ARGS, "--no-blend")
        lines = generate(self.path("b"), *self.ARGS, "--no-blend", "--force")
        self.assertFalse(any("model(s) copied" in line for line in lines))
        self.assertTrue(any(" - 2 asset(s)" in line for line in lines), lines)
        lines = generate(self.path("c"), "--types", "crate,pillar", "--count", "1", "--paint", "crystal",
                         "--texture-size", "128", "--no-blend")
        self.assertFalse(any("shared cache: " in line and ("model" in line or "bake" in line) for line in lines))

    def test_a_bake_serves_other_formats_and_schemes(self):
        generate(self.path("a"), *self.ARGS, "--no-blend")
        lines = generate(self.path("b"), *self.ARGS, "--no-blend", "--formats", "glb", "--icon-zoom", "1.2")
        self.assertIn("shared cache: 2 bake(s) reused (maps and atlas UVs) - export and preview in Blender", lines)
        with mock.patch.dict(os.environ, {"CUBEGEN_CACHE": "0"}):
            generate(self.path("fresh"), *self.ARGS, "--no-blend", "--formats", "glb", "--icon-zoom", "1.2")
        equivalent(self, self.path("b"), self.path("fresh"))
        scheme = self.path("mine.json")  # crystal with other colours: the same neutral bake, another composition
        with open(scheme, "w", encoding="utf-8") as fh:
            json.dump({"name": "stockpile_test", "base": "crystal", "colors": {"M_Metal": "#336699"}, "wear": 0.3}, fh)
        args = ("--types", "crate,pillar", "--count", "1", "--paint-file", scheme, "--texture-size", "64",
                "--no-blend")
        lines = generate(self.path("c"), *args)
        self.assertIn("shared cache: 2 bake(s) reused (maps and atlas UVs) - export and preview in Blender", lines)
        with mock.patch.dict(os.environ, {"CUBEGEN_CACHE": "0"}):
            generate(self.path("fresh_c"), *args)
        equivalent(self, self.path("c"), self.path("fresh_c"))

    def test_a_plain_bake_too(self):
        args = ("--types", "crate", "--count", "1", "--textures", "baked", "--texture-size", "64", "--no-blend")
        generate(self.path("a"), *args)
        lines = generate(self.path("b"), *args, "--formats", "fbx,glb")
        self.assertIn("shared cache: 1 bake(s) reused (maps and atlas UVs) - export and preview in Blender", lines)
        with mock.patch.dict(os.environ, {"CUBEGEN_CACHE": "0"}):
            generate(self.path("fresh"), *args, "--formats", "fbx,glb")
        equivalent(self, self.path("b"), self.path("fresh"))


class WorkflowTest(unittest.TestCase):
    """GitHub Actions minutes are a budget (~/.claude/CLAUDE.md): the rules of the global file, checked as text."""

    def setUp(self):
        with open(os.path.join(ROOT, ".github", "workflows", "tests.yml"), "r", encoding="utf-8") as fh:
            self.text = fh.read()

    def section(self, name):
        match = re.search(rf"^  {name}:\n((?:    .*\n|\s*\n)+)", self.text, re.MULTILINE)
        self.assertIsNotNone(match, name)
        return match.group(1)

    def test_triggers(self):
        on = re.search(r"^on:\n((?:  .*\n)+)", self.text, re.MULTILINE).group(1)
        self.assertRegex(on, r"push:\n    branches: \[main\]\n    paths-ignore: \[\"\*\*\.md\", \"docs/\*\*\"")
        self.assertIn("  pull_request:\n    paths-ignore:", on)
        self.assertIn("  workflow_dispatch:", on)
        self.assertNotIn("schedule", self.text)
        self.assertNotIn("tags:", on)

    def test_one_job_per_run_unless_asked(self):
        self.assertRegex(self.text, r"concurrency:\n  group: tests-\$\{\{ github.ref \}\}\n  cancel-in-progress: true")
        jobs = re.findall(r"^  (\w+):\n    if: (.*)$", self.text, re.MULTILINE)
        self.assertEqual([name for name, _ in jobs], ["quick", "full"])
        conditions = dict(jobs)
        self.assertEqual(conditions["quick"], "github.event_name == 'push' || inputs.tier == 'quick'")
        self.assertNotIn("push", conditions["full"])  # a push to main runs the quick job only
        self.assertIn("inputs.tier == 'full' && '[\"3.11\", \"3.9\", \"3.13\"]' || '[\"3.11\"]'", self.text)
        for name in ("quick", "full"):
            body = self.section(name)
            self.assertRegex(body, r"timeout-minutes: \d+")
            self.assertIn("runs-on: ubuntu-latest", body)
        self.assertIn("--tier quick", self.section("quick"))
        self.assertIn("uses: actions/cache@v4", self.section("full"))  # the Blender download


def git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args], check=True, capture_output=True, text=True).stdout


class ReleaseTest(unittest.TestCase):
    """tools/release.py against temporary repositories: a bare "origin", a main checkout and a release worktree."""

    VERSION = "9.1.0"

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.origin = os.path.join(self.dir, "origin.git")
        self.main = os.path.join(self.dir, "main")
        self.wt = os.path.join(self.dir, "wt")
        subprocess.run(["git", "init", "--bare", "-q", "-b", "main", self.origin], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", self.main], check=True)
        for key, value in (("user.name", "Test"), ("user.email", "test@example.invalid"), ("commit.gpgsign", "false"),
                           ("tag.gpgsign", "false")):
            git(self.main, "config", key, value)
        self.files(self.main, "9.0.0", "Before", "2026-10-01")
        git(self.main, "add", "-A")
        git(self.main, "commit", "-q", "-m", "start")
        git(self.main, "remote", "add", "origin", self.origin)
        git(self.main, "push", "-q", "origin", "main")
        git(self.main, "worktree", "add", "-q", "-b", f"release/{self.VERSION}", self.wt)
        self.files(self.wt, self.VERSION, "Testpilot", "2026-10-15")
        git(self.wt, "add", "-A")
        git(self.wt, "commit", "-q", "-m", "release")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    @staticmethod
    def files(root, version, name, date):
        major, minor, patch = version.split(".")
        write(os.path.join(root, "pyproject.toml"), f'[project]\nname = "cubegen"\nversion = "{version}"\n'.encode())
        write(os.path.join(root, "cubegen", "__init__.py"), f'__version__ = "{version}"\n'.encode())
        write(os.path.join(root, "blender_addon", "cubegen_addon", "__init__.py"),
              f'bl_info = {{"name": "x", "version": ({major}, {minor}, {patch})}}\n'.encode())
        write(os.path.join(root, "CHANGELOG.md"), f"# Changelog\n\n## {version} „{name}“ – {date}\n\n* x\n".encode())
        write(os.path.join(root, f"VERSION_{version}.md"), f"# Cubegen {version} – {name}\n\nText.\n".encode())

    def run_release(self, *args, cwd=None):
        out = []
        with mock.patch("builtins.print", lambda *a, **k: out.append(" ".join(str(x) for x in a))):
            code = release.main(["-C", cwd or self.wt, *args])
        return code, "\n".join(out)

    def test_dry_run_checks_and_changes_nothing(self):
        before = (git(self.main, "rev-parse", "HEAD"), git(self.origin, "rev-parse", "main"))
        code, out = self.run_release()
        self.assertEqual(code, 0, out)
        self.assertIn("Probelauf - nichts geändert", out)
        self.assertIn(f"merge --no-ff release/{self.VERSION}", out)
        self.assertIn(f"push --atomic origin main release/{self.VERSION} v{self.VERSION}", out)
        self.assertNotIn("--force", out)
        self.assertEqual((git(self.main, "rev-parse", "HEAD"), git(self.origin, "rev-parse", "main")), before)
        self.assertEqual(git(self.main, "tag").strip(), "")

    def test_apply_merges_tags_and_pushes(self):
        code, out = self.run_release("--apply", "--trailer", "Co-Authored-By: Test <test@example.invalid>")
        self.assertEqual(code, 0, out)
        self.assertEqual(git(self.main, "log", "-1", "--format=%s%n%b", "main").strip(),
                         f"Cubegen {self.VERSION} – Release übernehmen\nCo-Authored-By: Test <test@example.invalid>")
        self.assertEqual(len(git(self.main, "log", "-1", "--format=%P", "main").split()), 2)  # --no-ff
        self.assertEqual(git(self.main, "cat-file", "-t", f"v{self.VERSION}").strip(), "tag")  # annotated
        self.assertIn(f"Cubegen {self.VERSION} – Testpilot", git(self.main, "tag", "-n1", f"v{self.VERSION}"))
        self.assertEqual(git(self.origin, "rev-parse", "main"), git(self.main, "rev-parse", "main"))
        self.assertEqual(git(self.origin, "rev-parse", f"release/{self.VERSION}"),
                         git(self.wt, "rev-parse", "HEAD"))
        self.assertEqual(git(self.origin, "rev-parse", f"v{self.VERSION}^{{commit}}"),
                         git(self.main, "rev-parse", "main"))
        code, out = self.run_release()  # released: the tag is taken now
        self.assertEqual(code, 1)
        self.assertIn(f"Tag v{self.VERSION} gibt es schon", out)

    def test_works_from_the_main_checkout_too(self):
        code, out = self.run_release("--branch", f"release/{self.VERSION}", cwd=self.main)
        self.assertEqual(code, 0, out)  # the branch's committed files count, not the main checkout's
        self.assertIn(f"Cubegen {self.VERSION} „Testpilot“", out)
        code, out = self.run_release(cwd=self.main)
        self.assertEqual(code, 1)
        self.assertIn("kein Release-Zweig: 'main'", out)

    def failing(self, *args):
        before = git(self.main, "rev-parse", "HEAD")
        code, out = self.run_release("--apply", *args)
        self.assertEqual(code, 1, out)
        self.assertEqual(git(self.main, "rev-parse", "HEAD"), before)  # nothing changed
        return out

    def test_unreleased_or_unchecked_versions_stop(self):
        write(os.path.join(self.wt, "CHANGELOG.md"), f"## {self.VERSION} „Testpilot“ – unveröffentlicht\n".encode())
        write(os.path.join(self.wt, f"VERSION_{self.VERSION}.md"),
              f"# Cubegen {self.VERSION} – Testpilot\n\n*ungeprüft: Blender-/Unity-Abnahme offen*\n".encode())
        git(self.wt, "commit", "-q", "-am", "draft")
        out = self.failing()
        self.assertIn("hat kein Datum", out)
        self.assertIn("ungeprüft", out)

    def test_versions_must_agree(self):
        write(os.path.join(self.wt, "cubegen", "__init__.py"), b'__version__ = "9.0.9"\n')
        git(self.wt, "commit", "-q", "-am", "mismatch")
        self.assertIn("Version nicht überall gleich", self.failing())

    def test_dirty_checkouts_stop(self):
        write(os.path.join(self.main, "notes.txt"), b"left over")
        self.assertIn("Haupt-Checkout", self.failing())
        os.remove(os.path.join(self.main, "notes.txt"))
        write(os.path.join(self.wt, "pyproject.toml"), read(os.path.join(self.wt, "pyproject.toml")) + b"# x\n")
        self.assertRegex(self.failing(), r"Release-Worktree \S+ hat offene Änderungen")

    def test_main_must_match_the_remote_and_be_merged(self):
        other = os.path.join(self.dir, "other")
        subprocess.run(["git", "clone", "-q", self.origin, other], check=True)
        git(other, "config", "user.name", "x")
        git(other, "config", "user.email", "x@example.invalid")
        write(os.path.join(other, "new.txt"), b"x")
        git(other, "add", "-A")
        git(other, "commit", "-q", "-m", "someone else")
        git(other, "push", "-q", "origin", "main")
        self.assertIn("weicht von origin/main ab", self.failing())
        git(self.main, "pull", "-q", "--ff-only", "origin", "main")
        self.assertIn("main ist nicht in release/9.1.0 enthalten", self.failing())

    def test_big_files_and_credentials_stop(self):
        big = os.path.join(self.wt, "big.bin")
        with open(big, "wb") as fh:
            fh.truncate(release.LIMIT + 1)
        token = "gh" + "p_" + "A1b2C3d4" * 5  # built here, so this file itself holds no token
        write(os.path.join(self.wt, "tools", "conf.py"), f'TOKEN = "{token}"\n'.encode())
        write(os.path.join(self.wt, "id_rsa"), b"x")
        git(self.wt, "add", "-A")
        git(self.wt, "commit", "-q", "-m", "oops")
        out = self.failing()
        self.assertIn("big.bin (100 MB)", out)
        self.assertIn("tools/conf.py:1: sieht aus wie ein GitHub-Token", out)
        self.assertIn("id_rsa: Dateiname einer Zugangsdatei", out)
        self.assertNotIn(token, out)  # never the value
        git(self.wt, "rm", "-q", "big.bin", "tools/conf.py", "id_rsa")
        git(self.wt, "commit", "-q", "-m", "removed again")
        self.assertIn("big.bin", self.failing())  # still in the history the push would send

    def test_secret_patterns(self):
        samples = {
            "privater Schlüssel": "-----BEGIN " + "OPENSSH PRIVATE KEY-----",
            "AWS-Zugangsschlüssel": "key = AKIA" + "ABCDEFGHIJKLMNOP",
            "Slack-Token": "xox" + "b-1234567890-abcdef",
            "Anthropic-Schlüssel": "sk-" + "ant-api03-" + "x" * 30,
            "Passwort in einer URL": "https://user:" + "hunter22@example.com/repo.git",
        }
        for what, line in samples.items():
            self.assertTrue(any(name == what and pattern.search(line) for name, pattern in release.SECRET_PATTERNS),
                            what)
        for line in ("git@github.com:ffunkfabian-hash/cubeescape-cubegen.git", "https://github.com/x/y",
                     "MTP_Crate_000_crystal_Albedo.png", "desk-chair", "sha256 " + "a" * 64):
            self.assertFalse(any(p.search(line) for _, p in release.SECRET_PATTERNS), line)
        self.assertTrue(release.SECRET_FILES.search("deploy/.env"))
        self.assertFalse(release.SECRET_FILES.search("docs/environment.md"))

    def test_links(self):
        self.assertEqual(release.github_url("https://github.com/ffunkfabian-hash/cubeescape-cubegen.git"),
                         "https://github.com/ffunkfabian-hash/cubeescape-cubegen")
        self.assertEqual(release.github_url("git@github.com:ffunkfabian-hash/cubeescape-cubegen.git"),
                         "https://github.com/ffunkfabian-hash/cubeescape-cubegen")
        self.assertIsNone(release.github_url("/tmp/origin.git"))


class RepoNameTest(unittest.TestCase):
    def test_the_old_repository_name_is_gone(self):
        old = "lowpoly_cubeescape" + "_model_generatior"
        for rel in ("AGENTS.md", "README.md", "docs/CLI.md", "tools/install.sh"):
            with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as fh:
                text = fh.read()
            self.assertNotIn(old, text, rel)
            self.assertIn("cubeescape-cubegen", text, rel)


if __name__ == "__main__":
    unittest.main()
