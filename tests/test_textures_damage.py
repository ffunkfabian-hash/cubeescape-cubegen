"""Optional textures (ImageMagick) and damaged / destroyed variants."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.cli import main  # noqa: E402
from cubegen.imagemagick import find_imagemagick  # noqa: E402
from cubegen.models import REGISTRY, generate_asset, model_types  # noqa: E402
from cubegen.params import Style  # noqa: E402
from cubegen.textures import RECIPES, build_texture_set, material_map, textured_name  # noqa: E402

IM = find_imagemagick()


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


class DamageTests(unittest.TestCase):
    def test_all_types_damaged_and_destroyed_are_valid(self):
        for t in model_types():
            for level in ("damaged", "destroyed"):
                for seed in range(15):
                    with self.subTest(type=t, damage=level, seed=seed):
                        asset = generate_asset(t, seed, style=Style(damage=level))
                        self.assertTrue(asset.meshes())
                        for obj in asset.meshes():
                            for part in obj.mesh.parts:
                                if part.closed:
                                    self.assertGreater(obj.mesh.part_volume(part), 0, f"{obj.name}/{part.name}")
                        self.assertEqual(asset.meta["damage"], level)

    def test_destroyed_is_a_static_ruin_of_the_same_seed(self):
        for seed in range(10):
            intact = generate_asset("machine", seed)
            ruin = generate_asset("machine", seed, style=Style(damage="destroyed"))
            self.assertTrue(intact.behaviours)
            self.assertEqual(ruin.behaviours, [])
            for obj in ruin.meshes():  # every light is dead
                self.assertFalse({"M_GlowRed", "M_GlowCyan", "M_GlowOrange"} & set(obj.mesh.roles), obj.name)
            self.assertLess(ruin.get("Body").mesh.bbox()[1][2], intact.get("Body").mesh.bbox()[1][2])

    def test_damage_is_deterministic(self):
        a = generate_asset("wall", 4, style=Style(damage="destroyed"))
        b = generate_asset("wall", 4, style=Style(damage="destroyed"))
        self.assertEqual([o.mesh.verts for o in a.meshes()], [o.mesh.verts for o in b.meshes()])

    def test_ruin_types(self):
        ruins = [t for t, e in REGISTRY.items() if e.category == "ruins"]
        self.assertEqual(len(ruins), 7)
        for t in ruins:
            self.assertFalse(generate_asset(t, 1).behaviours, t)  # static decoration


@unittest.skipUnless(IM, "ImageMagick not installed")
class TextureTests(unittest.TestCase):
    def test_texture_set(self):
        with tempfile.TemporaryDirectory() as out:
            result = build_texture_set(IM, out, size=64, texture_set="Lab", log=lambda m: None)
            self.assertEqual(set(result), set(RECIPES))
            for info in result.values():
                self.assertTrue(info["name"].startswith("MT_Lab_"))
                for path in info["paths"].values():
                    self.assertTrue(os.path.getsize(path) > 0, path)
            manifest = json.loads(read(os.path.join(out, "CubeEscape_Textures.json")))
            self.assertEqual(len(manifest["materials"]), len(RECIPES))
        self.assertEqual(textured_name("M_Metal"), "MT_Metal")
        self.assertNotIn("M_GlowCyan", material_map())  # status materials are never textured

    def test_textures_default_off_and_obj_fallback(self):
        with tempfile.TemporaryDirectory() as plain, tempfile.TemporaryDirectory() as tex:
            main(["generate", "--seed", "5", "--types", "crate", "--no-blender", "--out", plain])
            self.assertNotIn("MT_", read(os.path.join(plain, "models", "Crate_000.obj")))
            self.assertFalse(os.path.isdir(os.path.join(plain, "models", "Textures")))
            main(["generate", "--seed", "5", "--types", "crate", "--no-blender", "--textures", "tiled",
                  "--texture-size", "64", "--out", tex])
            self.assertIn("usemtl MT_", read(os.path.join(tex, "models", "Crate_000.obj")))
            mtl = read(os.path.join(tex, "models", "CubeEscape_Materials.mtl"))
            self.assertIn("map_Kd Textures/MT_Metal_Albedo.png", mtl)
            rig = json.loads(read(os.path.join(tex, "models", "Crate_000.cubegen.json")))
            self.assertEqual(rig["textures"]["mode"], "tiled")
            self.assertTrue(all(not m.startswith("M_") or m.startswith("M_Glow")
                                for p in rig["parts"] for m in p["materials"]))


if __name__ == "__main__":
    unittest.main()
