"""cubegen 0.21.1: the workbench's texture budget counted like Cube Escape 0.51 (CubegenTextures)."""

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from cubegen.blender import find_blender  # noqa: E402
from cubegen.contract import check_runtime_budget, glb_summary, texture_bytes  # noqa: E402
from cubegen.imagemagick import find_imagemagick  # noqa: E402
from test_release_0210 import _glb  # noqa: E402

HAS_TOOLS = find_blender() is not None and find_imagemagick() is not None


class TextureAccountingTest(unittest.TestCase):
    def test_same_bytes_in_the_same_role_count_once(self):
        import json
        import struct

        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "a.glb")
            # two images with the same PNG bytes, one other - base colour of three materials, the first also as normal
            _glb(path, images=((512, 512), (512, 512), (256, 256)), materials=3)
            data = bytearray(open(path, "rb").read())
            n = struct.unpack_from("<I", data, 12)[0]
            gltf = json.loads(bytes(data[20:20 + n]))
            gltf["materials"][0]["normalTexture"] = {"index": 0}  # same image, other role: counts again
            gltf["materials"][1]["pbrMetallicRoughness"]["metallicRoughnessTexture"] = {"index": 2}
            text = json.dumps(gltf).encode()
            text += b" " * (-len(text) % 4)
            rest = bytes(data[20 + n:])
            out = struct.pack("<III", 0x46546C67, 2, 20 + len(text) + len(rest)) + struct.pack("<II", len(text),
                                                                                              0x4E4F534A)
            with open(path, "wb") as fh:
                fh.write(out + text + rest)
            info = glb_summary(path)
            roles = sorted((t["role"], t["size"]) for t in info["textures"])
            # images 0 and 1 have the same bytes: one albedo; + normal of image 0; + albedo and metallic of image 2
            self.assertEqual(roles, [("albedo", (256, 256)), ("albedo", (512, 512)), ("metallic_gloss", (256, 256)),
                                     ("normal", (512, 512))])
            self.assertEqual(texture_bytes(512, 512), 512 * 512 * 4 // 3)


def _crate(size, out):
    from cubegen.cli import main

    assert main(["generate", "--seed", "4242", "--types", "crate", "--count", "1", "--textures", "tiled",
                 "--texture-size", str(size), "--formats", "glb", "--no-render", "--no-blend", "--out", out]) == 0
    return os.path.join(out, "models", "Crate_000.glb")


@unittest.skipUnless(HAS_TOOLS, "Blender and ImageMagick required")
class CrateRegressionTest(unittest.TestCase):
    """Cube Escape 0.51 fixture CrateTiled2048_000 (cubegen 0.21.0, seed 4242): 8 textures, 42.7 MB - in budget;
    0.21.0 counted 268 MB and warned. Which maps share their bytes does not depend on the size: the quick test builds
    the crate at 256 px and scales to 2048, ``CUBEGEN_SLOW_TESTS=1`` builds it at 2048 (minutes)."""

    def test_tiled_crate_has_8_textures_and_fits_at_2048(self):
        out = tempfile.mkdtemp()
        try:
            info = glb_summary(_crate(256, out))
            self.assertEqual(len(info["textures"]), 8)
            self.assertEqual({t["size"] for t in info["textures"]}, {(256, 256)})
            self.assertAlmostEqual(8 * texture_bytes(2048, 2048) / 2 ** 20, 42.7, delta=0.1)
            self.assertLessEqual(8 * texture_bytes(2048, 2048), 64 * 1024 * 1024)
        finally:
            shutil.rmtree(out, ignore_errors=True)

    @unittest.skipUnless(os.environ.get("CUBEGEN_SLOW_TESTS") == "1", "real 2048 px run: CUBEGEN_SLOW_TESTS=1")
    def test_tiled_2048_crate_fits_the_budget(self):
        out = tempfile.mkdtemp()
        try:
            glb = _crate(2048, out)
            info = glb_summary(glb)
            self.assertEqual(len(info["textures"]), 8)
            self.assertAlmostEqual(sum(texture_bytes(*t["size"]) for t in info["textures"]) / 2 ** 20, 42.7, delta=0.1)
            self.assertEqual(check_runtime_budget(glb), [])
        finally:
            shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
