"""tools/atlas_check.py (0.30.0): occupancy, overlap and margin of atlas UVs, and the GLB reader."""

import json
import os
import struct
import sys
import tempfile
import unittest

try:
    import numpy as np
except ImportError:  # the numpy group of tools/run_tests.py runs this with Blender's Python
    np = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import atlas_check  # noqa: E402
from cubegen.blender import find_blender  # noqa: E402
from cubegen.imagemagick import find_imagemagick  # noqa: E402


def square(x, y, w, h=None):
    h = w if h is None else h
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def glb(path, triangles, material="MTA_Test"):
    """A one-primitive GLB: ``triangles`` are UV triples, positions are dummies."""
    uv = [p for tri in triangles for p in tri]
    uv_bytes = b"".join(struct.pack("<ff", u, 1.0 - v) for u, v in uv)
    pos_bytes = b"".join(struct.pack("<fff", u, v, 0.0) for u, v in uv)
    idx_bytes = b"".join(struct.pack("<H", i) for i in range(len(uv)))
    blob = pos_bytes + uv_bytes + idx_bytes
    doc = {"asset": {"version": "2.0"}, "buffers": [{"byteLength": len(blob)}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes)},
                           {"buffer": 0, "byteOffset": len(pos_bytes), "byteLength": len(uv_bytes)},
                           {"buffer": 0, "byteOffset": len(pos_bytes) + len(uv_bytes), "byteLength": len(idx_bytes)}],
           "accessors": [{"bufferView": 0, "componentType": 5126, "count": len(uv), "type": "VEC3"},
                         {"bufferView": 1, "componentType": 5126, "count": len(uv), "type": "VEC2"},
                         {"bufferView": 2, "componentType": 5123, "count": len(uv), "type": "SCALAR"}],
           "materials": [{"name": material}, {"name": "M_GlowCyan"}],
           "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "TEXCOORD_0": 1}, "indices": 2, "material": 0},
                                      {"attributes": {"POSITION": 0, "TEXCOORD_0": 1}, "indices": 2, "material": 1}]}]}
    text = json.dumps(doc).encode()
    text += b" " * (-len(text) % 4)
    blob += b"\0" * (-len(blob) % 4)
    body = (struct.pack("<I4s", len(text), b"JSON") + text + struct.pack("<I4s", len(blob), b"BIN\0") + blob)
    with open(path, "wb") as fh:
        fh.write(b"glTF" + struct.pack("<II", 2, 12 + len(body)) + body)


@unittest.skipUnless(np is not None, "numpy required (Blender's Python has it)")
class AtlasMeasureTest(unittest.TestCase):
    def test_islands_follow_shared_uv_vertices(self):
        a, b = square(0.1, 0.1, 0.2), square(0.5, 0.5, 0.2)
        # a quad of island a split into two faces that share an edge, plus a separate island b
        faces = [[a[0], a[1], a[2]], [a[0], a[2], a[3]], b]
        self.assertEqual(atlas_check._islands(faces), [0, 0, 1])

    def test_a_clean_atlas(self):
        polys = [square(0.05, 0.05, 0.4), square(0.55, 0.05, 0.4), square(0.05, 0.55, 0.9, 0.4)]
        stats = atlas_check.analyse(polys, 128)
        self.assertAlmostEqual(stats["occupancy"], 0.16 + 0.16 + 0.36, places=4)
        self.assertTrue(stats["in_range"])
        self.assertEqual((stats["overlap_texels"], stats["margin_texels"]), (0, 0))
        self.assertEqual(atlas_check.problems("m", stats, 0.68), [])

    def test_overlapping_islands_and_tight_gaps_are_found(self):
        polys = [square(0.1, 0.1, 0.4), square(0.4, 0.1, 0.4)]  # 0.1 of overlap
        stats = atlas_check.analyse(polys, 128)
        self.assertGreater(stats["overlap_share"], 0.1)
        self.assertTrue(any("shared by two islands" in p for p in atlas_check.problems("m", stats)))
        tight = atlas_check.analyse([square(0.1, 0.1, 0.4), square(0.5 + 2 / 128, 0.1, 0.4)], 128)  # a 2 px gap
        self.assertEqual(tight["overlap_texels"], 0)
        self.assertGreater(tight["margin_texels"], 0)
        wide = atlas_check.analyse([square(0.1, 0.1, 0.4), square(0.5 + 12 / 128, 0.1, 0.4)], 128)
        self.assertEqual(wide["margin_texels"], 0)

    def test_range_and_manifest_checks(self):
        stats = atlas_check.analyse([square(0.5, 0.5, 0.8)], 64)
        self.assertFalse(stats["in_range"])
        self.assertTrue(any("outside 0..1" in p for p in atlas_check.problems("m", stats)))
        ok = atlas_check.analyse([square(0.1, 0.1, 0.5)], 64)
        self.assertTrue(any("manifest" in p for p in atlas_check.problems("m", ok, 0.9)))
        self.assertTrue(any("occupancy" in p for p in atlas_check.problems("m", ok)))  # 0.25 < the minimum

    def test_the_glb_reader_takes_baked_primitives_only(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.glb")
            tris = [[(0.1, 0.1), (0.4, 0.1), (0.1, 0.4)], [(0.5, 0.5), (0.9, 0.5), (0.5, 0.9)]]
            glb(path, tris)
            polys = atlas_check.read_glb_uvs(path)
            self.assertEqual(len(polys), 2)  # the M_GlowCyan primitive (same data) is skipped
            for got, want in zip(polys, tris):
                for (gu, gv), (wu, wv) in zip(got, want):
                    self.assertAlmostEqual(gu, wu, places=5)
                    self.assertAlmostEqual(gv, wv, places=5)

    def test_the_picture_marks_every_island(self):
        stats = atlas_check.analyse([square(0.1, 0.1, 0.3), square(0.6, 0.6, 0.3)], 64)
        with tempfile.TemporaryDirectory() as d:
            path = atlas_check.draw(stats, os.path.join(d, "uv.png"))
            from cubegen import neutral

            image = neutral.read_png(path)
            self.assertEqual(image.shape, (64, 64, 3))
            self.assertEqual(len({tuple(p) for p in image.reshape(-1, 3)}), 3)  # background + two islands


@unittest.skipUnless(os.environ.get("CUBEGEN_SLOW_TESTS") and np is not None and find_blender() is not None
                     and find_imagemagick() is not None, "slow: CUBEGEN_SLOW_TESTS=1 with Blender and ImageMagick")
class AtlasRunTest(unittest.TestCase):
    def test_the_fixed_set_has_clean_atlases(self):
        with tempfile.TemporaryDirectory() as out:
            folders = atlas_check.generate(out)
            self.assertEqual(len(folders), len(atlas_check.SET))
            for folder in folders:
                measured = atlas_check.measure(folder)
                self.assertTrue(measured)
                for name, stats in measured.items():
                    self.assertEqual(atlas_check.problems(name, stats, stats["manifest_occupancy"]), [], name)


if __name__ == "__main__":
    unittest.main()
