"""End-to-end tests. Skipped automatically when ImageMagick / Blender are missing."""

import json
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.blender import find_blender  # noqa: E402
from cubegen.cli import main  # noqa: E402
from cubegen.imagemagick import find_imagemagick  # noqa: E402

HAS_MAGICK = find_imagemagick() is not None
HAS_BLENDER = find_blender() is not None


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def glb_json(path):
    with open(path, "rb") as fh:
        data = fh.read()
    length = struct.unpack("<I", data[12:16])[0]
    return json.loads(data[20:20 + length])


@unittest.skipUnless(HAS_MAGICK, "ImageMagick not installed")
class OBJFallbackTest(unittest.TestCase):
    def test_no_blender_batch(self):
        with tempfile.TemporaryDirectory() as out:
            code = main(["generate", "--seed", "11", "--types", "crate,door", "--count", "2", "--no-blender",
                         "--out", out])
            self.assertEqual(code, 0)
            manifest = json.loads(read(os.path.join(out, "manifest.json")))
            self.assertEqual([m["name"] for m in manifest["models"]],
                             ["Crate_000", "Crate_001", "Door_000", "Door_001"])
            self.assertTrue(os.path.isfile(os.path.join(out, "materials.png")))
            obj = read(os.path.join(out, "models", "Door_000.obj"))
            self.assertIn("mtllib CubeEscape_Materials.mtl", obj)
            self.assertIn("o Frame_Left", obj)
            self.assertIn("usemtl M_GlowRed", obj)
            self.assertIn("newmtl M_GlowCyan", read(os.path.join(out, "models", "CubeEscape_Materials.mtl")))

    def test_same_seed_same_files(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            for out in (a, b):
                main(["generate", "--seed", "abc", "--types", "machine", "--no-blender", "--out", out])
            self.assertEqual(read(os.path.join(a, "models", "Machine_000.obj")),
                             read(os.path.join(b, "models", "Machine_000.obj")))


@unittest.skipUnless(HAS_MAGICK and HAS_BLENDER, "Blender and ImageMagick required")
class BlenderTest(unittest.TestCase):
    def test_fbx_glb_preview_icon_blend(self):
        with tempfile.TemporaryDirectory() as out:
            code = main(["generate", "--seed", "3", "--types", "door", "--formats", "fbx,glb", "--engine", "cycles",
                         "--render-size", "64", "--samples", "4", "--out", out])
            self.assertEqual(code, 0)
            self.assertTrue(os.path.getsize(os.path.join(out, "models", "Door_000.fbx")) > 0)
            gltf = glb_json(os.path.join(out, "models", "Door_000.glb"))
            names = {n["name"] for n in gltf["nodes"]}
            self.assertTrue({"Frame_Left", "Frame_Top", "Panel", "StatusLight_Front"} <= names)
            self.assertTrue({m["name"] for m in gltf["materials"]} <= {
                "M_Wall", "M_RobotDark", "M_Metal", "M_Platform", "M_GlowRed", "M_GlowCyan", "M_Warning",
                "M_HazardOrange"})
            self.assertTrue(os.path.isfile(os.path.join(out, "icons", "Icon_Door_000.png")))
            self.assertTrue(os.path.isfile(os.path.join(out, "contact_sheet.png")))
            self.assertTrue(os.path.isfile(os.path.join(out, "CubeEscape_Generated_3.blend")))


if __name__ == "__main__":
    unittest.main()
