"""cubegen 0.25.0 "Quartermaster": shared image cache, numpy tests without skips, one heavy run at a time."""

import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
import zlib
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from cubegen import cache as cache_mod  # noqa: E402
from cubegen import migrate  # noqa: E402
from cubegen import pipeline  # noqa: E402
from cubegen.blender import find_blender  # noqa: E402
from cubegen.cache import OutputCache, Store, file_hash, png_content_hash  # noqa: E402
from cubegen.cli import build_config, make_parser  # noqa: E402
from cubegen.imagemagick import ImageMagick, find_imagemagick  # noqa: E402

import run_tests  # noqa: E402
import unity_check  # noqa: E402

HAS_MAGICK = find_imagemagick() is not None
HAS_TOOLS = HAS_MAGICK and find_blender() is not None
HOUR = 3600.0


def png(path, pixels=b"\x00\x10\x20", text=None):
    """A 1x1 RGB PNG, optionally with a tEXt chunk (what Blender stamps into its previews)."""
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    if text:
        data += chunk(b"tEXt", text)
    data += chunk(b"IDAT", zlib.compress(b"\x00" + pixels)) + chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def write(path, data: bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def age(path, seconds, now):
    os.utime(path, (now - seconds, now - seconds))


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = Store(os.path.join(self.dir, "store"))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_location_and_limit_from_the_environment(self):
        self.assertIsNone(cache_mod.store_root({"CUBEGEN_CACHE": "0"}))
        self.assertIsNone(cache_mod.store_root({"CUBEGEN_CACHE": "off"}))
        self.assertEqual(cache_mod.store_root({"CUBEGEN_CACHE": "/x/y"}), os.path.abspath("/x/y"))
        home = os.path.expanduser("~")
        self.assertEqual(cache_mod.default_root({}, "darwin"), os.path.join(home, "Library", "Caches", "Cubegen",
                                                                            "cache"))
        self.assertEqual(cache_mod.default_root({"XDG_CACHE_HOME": "/xdg"}, "linux"), "/xdg/cubegen/cache")
        self.assertEqual(cache_mod.default_root({}, "linux"), os.path.join(home, ".cache", "cubegen", "cache"))
        self.assertEqual(cache_mod.limit_bytes({}), 4 * 1024 ** 3)
        self.assertEqual(cache_mod.limit_bytes({"CUBEGEN_CACHE_LIMIT_GB": "0.5"}), 512 * 1024 ** 2)

    def test_reuse_in_another_folder_with_relative_roles(self):
        a, b = os.path.join(self.dir, "a"), os.path.join(self.dir, "b")
        first = OutputCache(a, store=self.store)
        icon = write(os.path.join(a, "icons", "Icon_X.png"), b"icon")
        first.put("icon:icons/Icon_X.png", "k1", [icon], place={"out": icon})
        textures = [write(os.path.join(a, "T", n), n.encode()) for n in ("m_Albedo.png", "m_Normal.png")]
        first.put("texture_set", "k2", textures, data={"m": 1}, place=os.path.join(a, "T"))
        second = OutputCache(b, store=self.store)
        target = os.path.join(b, "icons", "Icon_Y.png")  # another name: a single file goes where the caller says
        self.assertIsNotNone(second.get("icon:icons/Icon_Y.png", "k1", place={"out": target}))
        self.assertEqual(read(target), b"icon")
        hit = second.get("texture_set", "k2", place=os.path.join(b, "T"))
        self.assertEqual(hit["data"], {"m": 1})
        self.assertEqual(read(os.path.join(b, "T", "m_Normal.png")), b"m_Normal.png")
        self.assertEqual(second.shared, 2)
        for path in self.walk(self.store.root):  # nothing in the store names a folder
            if path.endswith(".json"):
                self.assertNotIn(self.dir, read(path).decode("utf-8"))
        self.assertIsNone(second.get("x", "unknown", place={"out": target}))

    @staticmethod
    def walk(root):
        return [os.path.join(r, f) for r, _, fs in os.walk(root) for f in fs]

    def test_folder_index_is_relative_and_survives_a_move(self):
        folder = os.path.join(self.dir, "out")
        path = write(os.path.join(folder, "icons", "Icon_A.png"), b"a")
        cache = OutputCache(folder, store=None)
        cache.put("icon:" + cache.rel(path), "k", [path])
        cache.digest(path)
        cache.save()
        text = read(os.path.join(folder, cache_mod.CACHE_NAME)).decode()
        self.assertNotIn(self.dir, text)
        self.assertEqual(json.loads(text)["format"], 2)
        moved = os.path.join(self.dir, "elsewhere")
        os.rename(folder, moved)
        again = OutputCache(moved, store=None)
        self.assertIsNotNone(again.get("icon:icons/Icon_A.png", "k"))

    def test_old_absolute_cache_file_is_read_relative(self):
        folder = os.path.join(self.dir, "out")
        path = write(os.path.join(folder, "materials.png"), b"s")
        write(os.path.join(folder, cache_mod.CACHE_NAME), json.dumps({"format": 1, "entries": {
            "swatch": {"key": "k", "files": {path: file_hash(path)}, "stats": {}, "data": None},
            f"icon:{path}": {"key": "k", "files": {path: file_hash(path)}, "stats": {}, "data": None}},
            "index": {path: [1, 2, "x"]}}).encode())
        cache = OutputCache(folder, store=None)
        self.assertEqual(sorted(cache.entries), ["icon:materials.png", "swatch"])
        self.assertEqual(list(cache.entries["swatch"]["files"]), ["materials.png"])
        self.assertEqual(cache.index, {})  # 0.24 held file hashes, 0.25 content hashes
        self.assertIsNotNone(cache.get("swatch", "k"))

    def test_force_never_reuses_but_records(self):
        folder = os.path.join(self.dir, "out")
        path = write(os.path.join(folder, "s.png"), b"s")
        OutputCache(folder, enabled=False, store=self.store).put("swatch", "k", [path], place={"out": path})
        self.assertIsNotNone(self.store.lookup("k"))
        self.assertIsNone(OutputCache(folder, enabled=False, store=self.store).get("swatch", "k", {"out": path}))

    def test_a_broken_object_never_reaches_a_folder(self):
        folder = os.path.join(self.dir, "out")
        path = write(os.path.join(folder, "s.png"), b"good")
        OutputCache(folder, store=self.store).put("swatch", "k", [path], place={"out": path})
        write(self.store.object_path(file_hash(path)), b"evil")
        target = write(os.path.join(self.dir, "other", "s.png"), b"mine")
        self.assertIsNone(OutputCache(os.path.dirname(target), store=self.store).get("swatch", "k", {"out": target}))
        self.assertEqual(read(target), b"mine")
        self.assertFalse(os.path.exists(self.store.object_path(file_hash(path))))

    def test_png_content_hash_ignores_render_stamps_only(self):
        a = png(os.path.join(self.dir, "a.png"), text=b"Date\x002026/10/15 10:17:00")
        b = png(os.path.join(self.dir, "b.png"), text=b"Date\x002026/10/15 11:00:00")
        c = png(os.path.join(self.dir, "c.png"), pixels=b"\x00\x10\x21")
        self.assertNotEqual(file_hash(a), file_hash(b))
        self.assertEqual(png_content_hash(a), png_content_hash(b))
        self.assertNotEqual(png_content_hash(a), png_content_hash(c))
        plain = write(os.path.join(self.dir, "x.bin"), b"xyz")
        self.assertEqual(png_content_hash(plain), file_hash(plain))

    def test_pruning_drops_least_recently_used_and_keeps_the_last_two_hours(self):
        now = time.time()
        folder = os.path.join(self.dir, "out")
        shared = write(os.path.join(folder, "shared.png"), b"S" * 1000)
        entries = {}
        for name, hours in (("old", 10), ("older", 20), ("middle", 5), ("recent", 1)):
            own = write(os.path.join(folder, name + ".png"), name.encode() * 400)
            files = {"own": (own, file_hash(own)), "shared": (shared, file_hash(shared))}
            self.store.put(name, files)
            entries[name] = own
            age(self.store.entry_path(name), hours * HOUR, now)
            age(self.store.object_path(file_hash(own)), hours * HOUR, now)
        age(self.store.object_path(file_hash(shared)), 1 * HOUR, now)  # still used by "recent"
        orphan = self.store.object_path("ab" + "0" * 62)
        write(orphan, b"o" * 500)
        age(orphan, 3 * HOUR, now)
        self.assertIsNotNone(self.store.lookup("middle"))  # a hit makes "middle" the most recently used

        total = self.store.usage()["bytes"]
        result = self.store.prune(limit=total - 3500, now=now)  # the orphan and the two oldest entries
        self.assertFalse(os.path.exists(orphan))
        self.assertIsNone(self.store.lookup("older"))
        self.assertIsNone(self.store.lookup("old"))
        self.assertIsNotNone(self.store.lookup("middle"))
        self.assertIsNotNone(self.store.lookup("recent"))
        self.assertTrue(os.path.exists(self.store.object_path(file_hash(shared))))
        self.assertEqual(result["entries_removed"], 2)

        result = self.store.prune(limit=0, now=now)  # nothing used in the last two hours is removed
        self.assertIsNotNone(self.store.lookup("middle"))
        self.assertIsNotNone(self.store.lookup("recent"))
        self.assertEqual(result["entries_removed"], 0)
        self.assertTrue(os.path.isfile(os.path.join(self.store.root, "pruned")))

    def test_pruning_is_rare_during_runs(self):
        self.store.prune()
        with mock.patch.object(Store, "prune", side_effect=AssertionError("pruned again")):
            self.assertIsNone(self.store.maybe_prune())  # the stamp is younger than an hour

    def test_concurrent_writers_leave_whole_entries(self):
        script = textwrap.dedent("""
            import os, sys
            sys.path.insert(0, sys.argv[1])
            from cubegen.cache import OutputCache, Store
            store, worker = Store(sys.argv[2]), int(sys.argv[3])
            folder = os.path.join(sys.argv[4], f"w{worker}")
            for i in range(25):
                for key in (f"shared{i % 5}", f"own{worker}_{i}"):
                    path = os.path.join(folder, key + ".png")
                    os.makedirs(folder, exist_ok=True)
                    with open(path, "wb") as fh:
                        fh.write((key * 2000).encode())
                    cache = OutputCache(folder, store=store)
                    cache.put(key, key, [path], place={"out": path})
                    cache.save()
                    other = os.path.join(folder, "got.png")
                    if cache.get("again" + key, f"shared{(i + 1) % 5}", place={"out": other}):
                        assert open(other, "rb").read().startswith(b"shared")
            """)
        procs = [subprocess.Popen([sys.executable, "-c", script, ROOT, self.store.root, str(w), self.dir])
                 for w in range(6)]
        self.assertEqual([p.wait(timeout=120) for p in procs], [0] * 6)
        entries, objects, temps = self.store.scan()
        self.assertEqual(temps, [])
        self.assertEqual(len(entries), 5 + 6 * 25)
        for _, path, _, shas in entries:
            key = os.path.basename(path)[:-len(".json")]
            self.assertEqual(json.loads(read(path))["key"], key)
            for sha in shas:
                self.assertEqual(file_hash(objects[sha][0]), sha)
                self.assertEqual(read(objects[sha][0]), (key * 2000).encode())


class ImageCodeTest(unittest.TestCase):
    def test_image_keys_hash_only_the_image_code(self):
        self.assertEqual(pipeline.module_closure(*pipeline.IMAGE_MODULES),
                         ["imagemagick", "materials", "seeds", "textures"])
        self.assertIn("models.registry", pipeline.module_closure("pipeline"))  # relative imports in subpackages
        self.assertNotIn("models.REGISTRY", pipeline.module_closure("pipeline"))  # a name, not a module (macOS!)
        with tempfile.TemporaryDirectory() as d:
            copy = os.path.join(d, "cubegen")
            shutil.copytree(os.path.join(ROOT, "cubegen"), copy, ignore=shutil.ignore_patterns("__pycache__"))
            same = pipeline.module_fingerprint(*pipeline.IMAGE_MODULES, root=copy)
            self.assertEqual(same, pipeline.image_code())  # the location is no input
            with open(os.path.join(copy, "pipeline.py"), "a", encoding="utf-8") as fh:
                fh.write("\n# another generator change\n")
            self.assertEqual(pipeline.module_fingerprint(*pipeline.IMAGE_MODULES, root=copy), same)
            with open(os.path.join(copy, "materials.py"), "a", encoding="utf-8") as fh:
                fh.write("\n# a colour change\n")
            self.assertNotEqual(pipeline.module_fingerprint(*pipeline.IMAGE_MODULES, root=copy), same)

    def test_the_set_row_command_is_part_of_its_key(self):
        self.assertNotEqual(pipeline.set_row_key(["a"], "IM7"), pipeline.set_row_key(["a"], "IM7", code="x"))
        with mock.patch.object(pipeline, "SET_ROW_EACH", ("-resize", "300x300")):
            changed = pipeline.set_row_key(["a"], "IM7")
        self.assertNotEqual(changed, pipeline.set_row_key(["a"], "IM7"))

    def test_0240_made_its_images_with_todays_image_code(self):
        # the migration only trusts a release whose image code is today's; a change to imagemagick/textures/
        # materials/seeds ends it on purpose (then remove the entry here and in migrate.MIGRATABLE)
        self.assertEqual(list(migrate.MIGRATABLE.values()), [pipeline.image_code()])


class MigrationTest(unittest.TestCase):
    """A 0.24-style folder (format 1, absolute paths, keys with the whole generator's hash) moves into the store."""

    SOURCE = "s" * 64
    MAGICK = "Version: ImageMagick 7.1.2-32 Q16-HDRI"

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.out = os.path.join(self.dir, "seed_7")
        self.store = Store(os.path.join(self.dir, "store"))
        patcher = mock.patch.dict(migrate.MIGRATABLE, {self.SOURCE: pipeline.image_code()})
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def make_folder(self):
        out, s, m = self.out, self.SOURCE, self.MAGICK
        previews = {n: png(os.path.join(out, "previews", n + ".png"), pixels=bytes([i, 2, 3]),
                           text=b"Date\x00yesterday") for i, n in enumerate(("Crate_000", "Crate_001"))}
        icons = {n: write(os.path.join(out, "icons", f"Icon_{n}.png"), n.encode()) for n in previews}
        swatch = write(os.path.join(out, "materials.png"), b"swatch")
        sheet = write(os.path.join(out, "contact_sheet.png"), b"sheet")
        row = write(os.path.join(out, "set_crate.png"), b"row")
        textures = os.path.join(out, "models", "Textures")
        maps = [write(os.path.join(textures, f"MT_Metal_{k}.png"), k.encode()) for k in ("Albedo", "Normal")]
        maps.append(write(os.path.join(textures, "CubeEscape_Textures.json"), b"{}"))
        fh = {p: file_hash(p) for p in list(previews.values())}
        names = list(previews)
        entries = {
            "swatch": (pipeline.swatch_key(m, code=s), swatch),
            "contact_sheet": (pipeline.sheet_key(names, [fh[previews[n]] for n in names],
                                                 pipeline.sheet_title(7, None), m, code=s), sheet),
            f"set:{row}": (pipeline.set_row_key([fh[previews[n]] for n in names], m, code=s, legacy=True), row),
        }
        for n in names:
            entries[f"icon:{icons[n]}"] = (pipeline.icon_key(fh[previews[n]], 256, None, m, code=s), icons[n])
        write(os.path.join(out, cache_mod.CACHE_NAME), json.dumps({"format": 1, "entries": {
            name: {"key": key, "files": {path: file_hash(path)}, "stats": {}, "data": None}
            for name, (key, path) in entries.items()}}).encode())
        data = {"Metal": {"name": "MT_Metal", "maps": {k: f"MT_Metal_{k}.png" for k in ("Albedo", "Normal")},
                          "paths": {k: os.path.join(textures, f"MT_Metal_{k}.png") for k in ("Albedo", "Normal")}}}
        write(os.path.join(textures, cache_mod.CACHE_NAME), json.dumps({"format": 1, "entries": {"texture_set": {
            "key": pipeline.texture_key(64, "", m, code=s, legacy_dir=textures),
            "files": {p: file_hash(p) for p in maps}, "stats": {}, "data": data}}}).encode())
        manifest = {"version": "0.24.0", "source_hash": s, "imagemagick": m, "seed": 7, "family": None,
                    "config": {"icon_size": 256, "icon_background": None, "texture_size": 64, "texture_set": ""},
                    "textures": {"mode": "tiled", "dir": "models/Textures"},
                    "sets": [{"preview": "set_crate.png", "members": names}],
                    "models": [{"name": n, "preview": f"previews/{n}.png"} for n in names]}
        write(os.path.join(out, "manifest.json"), json.dumps(manifest).encode())
        return previews, icons

    def test_verified_entries_move_under_todays_keys(self):
        previews, icons = self.make_folder()
        result = migrate.migrate_folder(self.out, self.store)
        self.assertEqual((result["migrated"], result["skipped"]), (6, 0))  # swatch, 2 icons, sheet, row, textures
        other = OutputCache(os.path.join(self.dir, "next"), store=self.store)
        icon = os.path.join(self.dir, "next", "icons", "Icon_Crate_001.png")
        content = png_content_hash(previews["Crate_001"])
        self.assertTrue(other.get("icon:x", pipeline.icon_key(content, 256, None, self.MAGICK), {"out": icon}))
        self.assertEqual(read(icon), b"Crate_001")
        textures = os.path.join(self.dir, "next", "Textures")
        hit = other.get("texture_set", pipeline.texture_key(64, "", self.MAGICK), place=textures)
        self.assertEqual(hit["data"]["Metal"]["paths"]["Normal"], "MT_Metal_Normal.png")  # relative now
        self.assertEqual(read(os.path.join(textures, "MT_Metal_Normal.png")), b"Normal")

    def test_changed_files_and_other_generators_stay_behind(self):
        previews, icons = self.make_folder()
        write(icons["Crate_000"], b"edited by hand")
        result = migrate.migrate_folder(self.out, self.store)
        self.assertEqual((result["migrated"], result["skipped"]), (5, 1))
        with mock.patch.dict(migrate.MIGRATABLE, {self.SOURCE: "other image code"}):
            result = migrate.migrate_folder(self.out, Store(os.path.join(self.dir, "store2")))
        self.assertEqual(result["migrated"], 0)
        self.assertIn("other image code", result["reason"])

    def test_once_per_store(self):
        self.make_folder()
        first = migrate.migrate_once(self.store, log=lambda m: None, roots=[self.dir])
        self.assertEqual([f["migrated"] for f in first["folders"]], [6])
        self.assertTrue(os.path.isfile(os.path.join(self.store.root, migrate.MARKER)))
        self.assertIsNone(migrate.migrate_once(self.store, log=lambda m: None, roots=[self.dir]))


_RUN = ImageMagick.run


def _only_version(self, args, montage=False):
    if list(args) == ["-version"]:  # the version is part of every key
        return _RUN(self, args, montage)
    raise AssertionError(f"ImageMagick ran: {list(args)[:4]}")


def no_image_work():
    return mock.patch.object(ImageMagick, "run", _only_version)


def generate(out, *extra):
    from cubegen.pipeline import generate_batch

    lines = []
    generate_batch(build_config(make_parser().parse_args(["generate", "--seed", "5", "--out", out, *extra])),
                   log=lines.append)
    return lines


@unittest.skipUnless(HAS_MAGICK, "ImageMagick required")
class SharedPipelineTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        patcher = mock.patch.dict(os.environ, {"CUBEGEN_CACHE": os.path.join(self.dir, "store")})
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_second_folder_needs_no_imagemagick(self):
        args = ("--types", "crate,wall", "--no-blender", "--textures", "tiled", "--texture-size", "64")
        a, b = os.path.join(self.dir, "a"), os.path.join(self.dir, "b")
        generate(a, *args)
        with no_image_work():
            lines = generate(b, *args)
        self.assertTrue(any(line.startswith("textures from the shared cache") for line in lines), lines)
        for rel in ("materials.png", "models/Textures/MT_Metal_Albedo.png",
                    "models/Textures/CubeEscape_Textures.json"):
            self.assertEqual(read(os.path.join(a, rel)), read(os.path.join(b, rel)), rel)
        lines = generate(b, *args)  # third run: this folder's own files are current
        self.assertTrue(any(line.startswith("textures unchanged") for line in lines), lines)

    def test_two_checkouts_share_the_cache(self):
        env = dict(os.environ, PYTHONPATH="")
        outs = []
        for name in ("main", "worktree"):
            checkout = os.path.join(self.dir, name)
            shutil.copytree(os.path.join(ROOT, "cubegen"), os.path.join(checkout, "cubegen"),
                            ignore=shutil.ignore_patterns("__pycache__"))
            out = os.path.join(checkout, "output")
            result = subprocess.run([sys.executable, "-m", "cubegen", "generate", "--seed", "3", "--types", "crate",
                                     "--no-blender", "--textures", "tiled", "--texture-size", "64", "--out", out],
                                    cwd=checkout, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            outs.append(result.stdout)
        self.assertNotIn("from the shared cache", outs[0])
        self.assertIn("textures from the shared cache", outs[1])
        self.assertIn("shared cache: 1 image(s)", outs[1])  # the swatch


@unittest.skipUnless(HAS_TOOLS, "Blender and ImageMagick required")
class SharedPreviewImagesTest(unittest.TestCase):
    def test_icons_sheet_and_set_rows_from_another_folder(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"CUBEGEN_CACHE": os.path.join(d, "s")}):
            args = ("--types", "crate", "--count", "2", "--set", "--textures", "tiled", "--texture-size", "64",
                    "--no-blend")
            a, b = os.path.join(d, "a"), os.path.join(d, "b")
            generate(a, *args)
            lines = generate(b, *args)  # Blender renders again: other render stamps, the same pixels
            previews = ["previews/Crate_000.png", "previews/Crate_001.png"]
            if any(png_content_hash(os.path.join(a, p)) != png_content_hash(os.path.join(b, p)) for p in previews):
                self.skipTest("this renderer gave other pixels the second time (Workbench/EEVEE do not)")
            self.assertIn("icons: 0 new, 2 reused", lines)
            self.assertTrue(any(line.startswith("shared cache: 5 image(s)") for line in lines), lines)
            for rel in ("icons/Icon_Crate_000.png", "icons/Icon_Crate_001.png", "contact_sheet.png", "set_crate.png"):
                self.assertEqual(read(os.path.join(a, rel)), read(os.path.join(b, rel)), rel)


class HeavyLockTest(unittest.TestCase):
    HOLD = textwrap.dedent("""
        import fcntl, json, os, sys, time
        fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o644)
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.ftruncate(fd, 0)
        os.pwrite(fd, json.dumps({"pid": os.getpid(), "what": "test holder", "checkout": "/ce", "since": "now"}).encode(), 0)
        print("held", flush=True)
        time.sleep(float(sys.argv[2]))
        """)
    TRY = textwrap.dedent("""
        import fcntl, os, sys
        fd = os.open(sys.argv[1], os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            print("free")
        except OSError:
            print("held")
        """)

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "CubeEscape", "heavy-run.lock")  # the folder does not exist yet
        env = {"CE_HEAVY_LOCK_FILE": self.path}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("CE_HEAVY_LOCK", None)
        os.environ.pop("CE_HEAVY_HELD", None)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_contract_path(self):
        self.assertEqual(unity_check.HEAVY_LOCK, os.path.join(os.path.expanduser("~"), "Library", "Caches",
                                                              "CubeEscape", "heavy-run.lock"))

    def test_waits_for_the_holder_and_says_who_it_is(self):
        os.makedirs(os.path.dirname(self.path))
        holder = subprocess.Popen([sys.executable, "-c", self.HOLD, self.path, "1.0"], stdout=subprocess.PIPE,
                                  text=True)
        self.assertEqual(holder.stdout.readline().strip(), "held")
        lines = []
        lock = unity_check.HeavyLock("Cubegen test", out=lines.append, poll=0.05)
        lock.acquire()
        try:
            self.assertGreater(lock.waited, 0.3)
            self.assertIn("belegt von test holder (PID", lines[0])
            self.assertIn("CE_HEAVY_LOCK=0", lines[0])
            with open(self.path, encoding="utf-8") as fh:
                info = json.load(fh)
            self.assertEqual((info["pid"], info["what"]), (os.getpid(), "Cubegen test"))
            self.assertEqual(os.environ.get("CE_HEAVY_HELD"), "1")  # verify.sh below us must not wait for us
        finally:
            lock.release()
            holder.wait(timeout=10)
            holder.stdout.close()
        self.assertNotIn("CE_HEAVY_HELD", os.environ)
        self.assertEqual(os.path.getsize(self.path), 0)  # nobody reads an old holder

    def test_children_never_inherit_the_lock(self):
        with unity_check.HeavyLock("Cubegen test", out=lambda m: None) as lock:
            lock.acquire()
            self.assertTrue(os.path.isfile(self.path))  # created when missing
            self.assertFalse(os.get_inheritable(lock.fd))
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)"], close_fds=False)
            self.assertEqual(subprocess.run([sys.executable, "-c", self.TRY, self.path], capture_output=True,
                                            text=True).stdout.strip(), "held")
        try:  # released although the background child still runs
            self.assertEqual(subprocess.run([sys.executable, "-c", self.TRY, self.path], capture_output=True,
                                            text=True).stdout.strip(), "free")
        finally:
            child.kill()
            child.wait()

    def test_opt_out_and_inside_a_holder(self):
        for env, reason in (({"CE_HEAVY_LOCK": "0"}, "CE_HEAVY_LOCK=0"), ({"CE_HEAVY_HELD": "1"}, "CE_HEAVY_HELD=1")):
            with mock.patch.dict(os.environ, env):
                lock = unity_check.HeavyLock("Cubegen test", out=lambda m: None)
                lock.acquire()
                self.assertIn(reason, lock.skipped)
                self.assertIsNone(lock.fd)
                lock.release()
        self.assertFalse(os.path.exists(self.path))


class ReferenceMapsTest(unittest.TestCase):
    def test_reference_maps_use_a_python_with_numpy(self):
        import paint_reference

        manifest = {"models": [{"name": "Crate_000"}]}
        with mock.patch.object(paint_reference, "load_manifest", return_value=manifest), \
                mock.patch.object(paint_reference, "models_with_maps", return_value=[1]), \
                mock.patch.object(paint_reference, "write_reference", side_effect=ImportError("numpy")):
            with mock.patch.object(run_tests, "numpy_python", return_value=("/blender/python3.13", "2.3.4")), \
                    mock.patch.object(unity_check.subprocess, "run",
                                      return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
                self.assertEqual(unity_check.paint_reference("/out"), os.path.join("/out", unity_check.REFERENCE))
            self.assertEqual(run.call_args[0][0][:2], ["/blender/python3.13",
                                                       os.path.join(ROOT, "tools", "paint_reference.py")])
            with mock.patch.object(run_tests, "numpy_python", return_value=(sys.executable, None)):
                self.assertIsNone(unity_check.paint_reference("/out"))  # no numpy anywhere: said, then skipped


class RunTestsTest(unittest.TestCase):
    def test_numpy_modules_get_their_own_group(self):
        plan = run_tests.groups("full")
        self.assertEqual(plan[run_tests.NUMPY], ["test_release_0180", "test_release_0240", "test_release_0300"])
        others = [m for name, members in plan.items() if name != run_tests.NUMPY for m in members]
        self.assertFalse(set(others) & set(plan[run_tests.NUMPY]))
        self.assertEqual(sorted(others + plan[run_tests.NUMPY]), run_tests.modules())

    def test_numpy_interpreter_has_numpy(self):
        python, version = run_tests.numpy_python()
        if version is None:
            self.assertEqual(python, sys.executable)  # nothing found: the tests skip with their reason, as before
        else:
            self.assertEqual(run_tests.numpy_version(python), version)
        for path in run_tests.blender_pythons():
            self.assertTrue(os.access(path, os.X_OK), path)

    def test_summary_lists_skip_reasons(self):
        output = ("test_a (tests.t.A.test_a) ... ok\n"
                  "test_b (tests.t.A.test_b) ... skipped 'real Unity run: CUBEGEN_UNITY_CHECK=1'\n"
                  "Docstring\nline ... skipped 'numpy required'\n\nRan 3 tests in 0.1s\n\nOK (skipped=2)\n")
        line, skipped = run_tests.summary(output)
        self.assertEqual(line, "Ran 3 tests in 0.1s | OK (skipped=2)")
        self.assertEqual(skipped, ["real Unity run: CUBEGEN_UNITY_CHECK=1", "numpy required"])


if __name__ == "__main__":
    unittest.main()
