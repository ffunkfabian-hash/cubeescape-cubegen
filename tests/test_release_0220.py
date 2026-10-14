"""cubegen 0.22.0 "Beacon": the Emission map of glowing paint schemes in the sidecar (contract version 2, version 1
still writable) and the manifest data Cube Escape needs for sets, connectors and dressings (manifest format 2)."""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from cubegen.blender import find_blender  # noqa: E402
from cubegen.contract import (BAKED_MAPS, CONTRACT_FILE, CONTRACT_VERSION, baked_map_keys,  # noqa: E402
                              check_export, check_sidecar, contract_for)
from cubegen.families import JOINS, RULES, join_table  # noqa: E402
from cubegen.imagemagick import find_imagemagick  # noqa: E402
from cubegen.models import REGISTRY, generate_asset  # noqa: E402
from cubegen.paint import PAINTS, scheme_glows  # noqa: E402
from cubegen.pipeline import MANIFEST_FORMAT, BatchConfig, rig_data  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAS_TOOLS = find_blender() is not None and find_imagemagick() is not None
#: the top-level keys Cube Escape's contract reader (CubegenContract.cs, checked with Cube Escape 0.54) accepts in
#: version 1 - it rejects any other key
CE_V1_KEYS = {"contract", "version", "source", "note", "file", "root", "part", "behaviour_keys", "field_types", "axes",
              "signal_modes", "behaviours", "rules", "colliders", "tolerances"}
#: the baked maps Cube Escape's CubegenMaterials accepted until contract version 2
V1_MAPS = ("Albedo", "Normal", "MetallicSmoothness", "Roughness", "AO", "Height")


def baked_rig(maps):
    asset = generate_asset("crate", 3)
    rig = rig_data(asset, {"type": "crate", "seed": 3, "style": {}}, 1)
    rig["textures"] = {"mode": "baked", "manifest": "Textures/CubeEscape_Textures.json",
                       "baked": {k: f"Textures/MTP_Crate_000_dark_{k}.png" for k in maps}}
    return rig


class ContractVersionTest(unittest.TestCase):
    def test_version_2_adds_the_emission_map_version_1_stays_as_it_was(self):
        # 0.24.0: the current version is 3 (test_release_0240) - version 2 is what contract_for(2) gives
        self.assertGreaterEqual(CONTRACT_VERSION, 2)
        self.assertEqual(baked_map_keys(1), V1_MAPS)
        self.assertEqual(baked_map_keys(2), V1_MAPS + ("Emission",))
        self.assertEqual(BAKED_MAPS["required"], ["Albedo", "Normal", "MetallicSmoothness"])
        self.assertEqual(BAKED_MAPS["emission_intensity"], 3.0)
        old = contract_for(1)
        self.assertEqual(set(old), CE_V1_KEYS)  # an importer of version 1 reads it unchanged
        self.assertEqual(old["version"], 1)
        v2 = contract_for(2)
        self.assertEqual({k: v for k, v in old.items() if k != "version"},
                         {k: v for k, v in v2.items() if k not in ("version", "history", "baked_maps")})
        self.assertEqual(sorted(v2["history"]), ["1", "2"])

    def test_contract_command_writes_either_version(self):
        from cubegen.cli import main

        with tempfile.TemporaryDirectory() as d:
            new, old = os.path.join(d, "v2.json"), os.path.join(d, "v1.json")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["contract", "--out", new]), 0)
                self.assertEqual(main(["contract", "--version", "1", "--out", old]), 0)
            with open(new, "rb") as a, open(CONTRACT_FILE, "rb") as b:
                self.assertEqual(a.read(), b.read())  # the file itself, byte for byte
            with open(old, "r", encoding="utf-8") as fh:
                self.assertEqual(json.load(fh), contract_for(1))

    def test_sidecar_textures_follow_the_importer_version(self):
        self.assertEqual(check_sidecar(baked_rig(V1_MAPS + ("Emission",)))[0], [])
        errors = check_sidecar(baked_rig(V1_MAPS + ("Emission",)), version=1)[0]
        self.assertEqual(len(errors), 1)
        self.assertIn("'Emission' (contract version 2, this importer reads version 1)", errors[0])
        self.assertEqual(check_sidecar(baked_rig(("Albedo", "Normal", "MetallicSmoothness")), version=1)[0], [])
        self.assertIn("textures.baked: missing map 'Normal'", check_sidecar(baked_rig(("Albedo",
                                                                                       "MetallicSmoothness")))[0])
        self.assertIn("textures.baked: unknown map 'Glow'", check_sidecar(baked_rig(V1_MAPS + ("Glow",)))[0])
        rig = baked_rig(V1_MAPS)
        rig["textures"]["baked"]["AO"] = rig["textures"]["baked"]["Albedo"]
        self.assertIn("textures.baked: every map needs its own file", check_sidecar(rig)[0])
        rig = baked_rig(V1_MAPS)
        rig["textures"]["mode"] = "tiled"
        self.assertIn("textures: baked maps need mode baked", check_sidecar(rig)[0])
        rig = baked_rig(V1_MAPS)
        del rig["textures"]["baked"]  # the importer requires the maps in mode baked
        self.assertIn("textures: mode baked needs baked: {map: path}", check_sidecar(rig)[0])
        rig = baked_rig(V1_MAPS)
        rig["textures"]["emission"] = 3.0
        self.assertIn("textures: unknown key 'emission'", check_sidecar(rig)[0])

    def test_export_check_finds_missing_maps(self):
        with tempfile.TemporaryDirectory() as d:
            rig = baked_rig(V1_MAPS + ("Emission",))
            name = rig["model"]
            with open(os.path.join(d, name + ".cubegen.json"), "w", encoding="utf-8") as fh:
                json.dump(rig, fh)
            os.makedirs(os.path.join(d, "Textures"))
            for key, path in rig["textures"]["baked"].items():
                if key != "Emission":
                    open(os.path.join(d, path), "wb").close()
            errors = check_export(d)[name]["errors"]
            self.assertEqual(errors, ["textures.baked.Emission: file 'Textures/MTP_Crate_000_dark_Emission.png' "
                                      "missing"])
            open(os.path.join(d, rig["textures"]["baked"]["Emission"]), "wb").close()
            self.assertEqual(check_export(d)[name]["errors"], [])
            self.assertEqual(len(check_export(d, 1)[name]["errors"]), 1)  # version 1 knows no Emission

    def test_only_glowing_schemes_write_an_emission_map(self):
        for name, scheme in PAINTS.items():
            self.assertEqual(scheme_glows(name), scheme["edge_glow"] > 0, name)
        self.assertFalse(scheme_glows("industrial"))
        self.assertTrue(scheme_glows("crystal") and scheme_glows("dark"))

    def test_config_and_cli_take_the_contract_version(self):
        from cubegen.cli import build_config, make_parser

        config = BatchConfig(seed=1, models={"crate": 1}, out_dir="x", contract=CONTRACT_VERSION + 1)
        with self.assertRaises(ValueError):
            config.validate()
        args = make_parser().parse_args(["generate", "--types", "crate", "--contract", "1", "--no-blender"])
        self.assertEqual(build_config(args).contract, 1)
        args = make_parser().parse_args(["generate", "--types", "crate", "--no-blender"])
        self.assertEqual(build_config(args).contract, CONTRACT_VERSION)

    def test_unity_check_writes_for_the_contract_cube_escape_keeps(self):
        import unity_check

        with tempfile.TemporaryDirectory() as ce:
            self.assertIsNone(unity_check.ce_contract_version(ce))
            path = os.path.join(ce, unity_check.CE_CONTRACT)
            os.makedirs(os.path.dirname(path))
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(contract_for(1), fh)
            self.assertEqual(unity_check.ce_contract_version(ce), 1)
        command = unity_check.generate_command("paint", "out", 1)
        self.assertEqual(command[command.index("--contract") + 1], "1")
        self.assertNotIn("--contract", unity_check.generate_command("paint", "out"))


class ManifestDataTest(unittest.TestCase):
    """What Cube Escape's model browser reads from manifest.json (ROADMAP ToDo 16, 25, 30, 31)."""

    @classmethod
    def setUpClass(cls):
        from cubegen.cli import main

        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = cls.tmp.name
        with redirect_stdout(io.StringIO()):
            main(["generate", "--seed", "42", "--types", "floor_tile,test_wall_modules,retractable_bridge", "--count",
                  "3", "--set", "--param", "floor_tile.dressing=ruin", "--param", "test_wall_modules.crystals=some",
                  "--no-blender", "--out", cls.out])
        with open(os.path.join(cls.out, "manifest.json"), "r", encoding="utf-8") as fh:
            cls.manifest = json.load(fh)
        cls.models = {m["name"]: m for m in cls.manifest["models"]}
        cls.sets = {s["type"]: s for s in cls.manifest["sets"]}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_format_and_contract_version(self):
        self.assertEqual(self.manifest["format"], MANIFEST_FORMAT)
        self.assertEqual(MANIFEST_FORMAT, 2)
        self.assertEqual(self.manifest["config"]["contract"], CONTRACT_VERSION)

    def test_sets_name_their_joining_faces_in_unity_coordinates(self):
        tile = self.sets["floor_tile"]
        self.assertEqual(tile["members"], ["FloorTile_000", "FloorTile_001", "FloorTile_002"])
        self.assertTrue(tile["outline_ok"])
        faces = {f["face"]: f for f in tile["faces_unity"]}
        self.assertEqual(list(faces), tile["faces"])
        size = tile["pinned"]["size"]
        # Blender x- (left) is Unity +x, Blender front -Y is Unity +z, Blender up is Unity up
        self.assertEqual(faces["x-"]["direction"], [1.0, 0.0, 0.0])
        self.assertEqual(faces["y-"]["direction"], [0.0, 0.0, 1.0])
        self.assertEqual(faces["z-"]["direction"], [0.0, -1.0, 0.0])
        for face in ("x-", "x+", "y-", "y+"):
            self.assertAlmostEqual(faces[face]["distance_m"], size / 2, places=3)
        self.assertAlmostEqual(faces["z-"]["distance_m"], tile["pinned"]["depth"], places=3)  # the slab's underside
        for s in self.sets.values():  # the set's bounds are its members' sidecar bounds (the outline they keep)
            with open(os.path.join(self.out, "models", s["members"][0] + ".cubegen.json"), "r",
                      encoding="utf-8") as fh:
                bounds = json.load(fh)["bounds"]
            for key in ("center", "size"):
                for a, b in zip(s["bounds"][key], bounds[key]):
                    self.assertAlmostEqual(a, b, places=3)
            for member in s["members"]:
                self.assertEqual(self.models[member]["set"], s["name"])

    def test_dressings_per_model_and_per_type(self):
        self.assertEqual(self.models["FloorTile_001"]["dressing"], {"dressing": "ruin"})
        self.assertEqual(self.models["TestWallModules_000"]["dressing"], {"crystals": "some", "dressing": "none"})
        self.assertNotIn("dressing", self.models["RetractableBridge_000"])
        table = self.manifest["dressings"]
        self.assertEqual(table["dressing"]["values"], ["none", "ruin", "organic"])
        self.assertEqual(table["dressing"]["types"], ["catwalk", "floor_tile", "pillar", "test_wall_modules"])
        self.assertEqual(table["dressing"]["paints"], {"ruin": ["ruin"], "organic": ["organic"]})
        self.assertEqual(table["crystals"]["types"], ["test_wall_modules"])  # rock types count crystals: no dressing
        for name in table["dressing"]["paints"]:
            self.assertIn(name, PAINTS)
        for entry in table.values():
            for t in entry["types"]:
                self.assertIn(t, REGISTRY)

    def test_joins_and_moving_connectors(self):
        self.assertEqual(self.manifest["joins"], join_table())
        self.assertEqual(len(self.manifest["joins"]), len(JOINS))
        walk = next(j for j in self.manifest["joins"] if (j["a"], j["b"]) == ("walk", "walk"))
        self.assertEqual(walk, {"a": "walk", "b": "walk", "mode": "face", "fit_check": True})
        for j in self.manifest["joins"]:
            self.assertEqual(j["fit_check"], (j["a"], j["b"]) in RULES or (j["b"], j["a"]) in RULES)
        bridge = {c["name"]: c for c in self.models["RetractableBridge_000"]["connectors"]}
        span = bridge["landing"]["position"][0]
        # the deck's end joins only once the deck has moved out: Unity offset of the part Deck
        self.assertEqual(bridge["deck_out"]["moves"], {"part": "Deck", "offset": [-span, 0.3, 0.0]})
        self.assertNotIn("moves", bridge["landing"])


@unittest.skipUnless(HAS_TOOLS, "Blender and ImageMagick required")
class EmissionMapTest(unittest.TestCase):
    def run_paint(self, out, paint, *extra):
        result = subprocess.run([sys.executable, "-m", "cubegen", "generate", "--seed", "3", "--pick", "crate:0",
                                 "--paint", paint, "--texture-size", "64", "--no-render", "--no-blend",
                                 "--bake-device", "cpu", "--formats", "fbx,glb", "--out", out, *extra],
                                capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with open(os.path.join(out, "manifest.json"), "r", encoding="utf-8") as fh:
            entry = json.load(fh)["models"][0]
        with open(os.path.join(out, "models", "Crate_000.cubegen.json"), "r", encoding="utf-8") as fh:
            rig = json.load(fh)
        return entry, rig

    def test_glowing_scheme_names_its_emission_map_everywhere(self):
        from cubegen.contract import glb_summary

        with tempfile.TemporaryDirectory() as out:
            entry, rig = self.run_paint(out, "dark")
            self.assertIn("Emission", entry["baked"])
            self.assertEqual(sorted(rig["textures"]["baked"]), sorted(V1_MAPS[:4] + ("Emission",)))
            self.assertTrue(os.path.isfile(os.path.join(out, "models", rig["textures"]["baked"]["Emission"])))
            roles = [t["role"] for t in glb_summary(os.path.join(out, "models", "Crate_000.glb"))["textures"]]
            self.assertIn("emission", roles)
            result = check_export(os.path.join(out, "models"))
            self.assertEqual(result["Crate_000"]["errors"], [])

    def test_scheme_without_glow_writes_no_black_map(self):
        from cubegen.contract import glb_summary

        with tempfile.TemporaryDirectory() as out:
            entry, rig = self.run_paint(out, "industrial")
            self.assertNotIn("Emission", entry["baked"])
            self.assertNotIn("Emission", rig["textures"]["baked"])
            self.assertFalse([f for f in os.listdir(os.path.join(out, "models", "Textures")) if "Emission" in f])
            roles = [t["role"] for t in glb_summary(os.path.join(out, "models", "Crate_000.glb"))["textures"]]
            self.assertNotIn("emission", roles)  # one texture less in the workbench budget

    def test_model_without_baked_material_names_no_textures(self):
        # 0.21: Puddle_000 of seed 0 is crystal only - nothing to bake, yet the sidecar said {"mode": "baked"} without
        # maps, which Cube Escape's CubegenMaterials rejects (it requires the maps in mode baked)
        with tempfile.TemporaryDirectory() as out:
            result = subprocess.run([sys.executable, "-m", "cubegen", "generate", "--seed", "0", "--pick", "puddle:0",
                                     "--textures", "baked", "--texture-size", "64", "--no-render", "--no-blend",
                                     "--bake-device", "cpu", "--out", out], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            sidecar = next(os.path.join(folder, f) for folder, _, files in os.walk(out) for f in files
                           if f == "Puddle_000.cubegen.json")
            with open(sidecar, "r", encoding="utf-8") as fh:
                rig = json.load(fh)
            self.assertNotIn("textures", rig)
            # 0.24.0: the slime is M_Liquid now (M_Crystal only for real crystals, test_release_0240)
            self.assertEqual({m for part in rig["parts"] for m in part["materials"]}, {"M_Liquid"})

    def test_contract_1_keeps_the_map_in_the_manifest_only(self):
        with tempfile.TemporaryDirectory() as out:
            entry, rig = self.run_paint(out, "dark", "--contract", "1")
            self.assertIn("Emission", entry["baked"])
            self.assertNotIn("Emission", rig["textures"]["baked"])
            for version in (1, 2):  # a version-1 sidecar is valid for both importers
                self.assertEqual(check_export(os.path.join(out, "models"), version)["Crate_000"]["errors"], [])


if __name__ == "__main__":
    unittest.main()
