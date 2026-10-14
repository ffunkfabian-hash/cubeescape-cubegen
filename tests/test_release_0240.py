"""cubegen 0.24.0 "Primer": neutral maps of --paint for Cube Escape's recolouring shader (contract version 3) - packed
W0..W2 (weights, noise and detail in alpha), Fields (AO, edge, up, height), Normal - the scheme as data in the sidecar,
the paint catalog, reference maps per scheme (tools/paint_reference.py) and the Unity-check probe "neutral"."""

import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

from cubegen import neutral  # noqa: E402
from cubegen.blender import find_blender  # noqa: E402
from cubegen.contract import (CONTRACT, CONTRACT_VERSION, NEUTRAL_MAPS, PAINT_SCHEME, check_export,  # noqa: E402
                              check_sidecar, contract_for, root_keys, texture_keys)
from cubegen.imagemagick import find_imagemagick  # noqa: E402
from cubegen.models import generate_asset  # noqa: E402
from cubegen.paint import (AMOUNT_KEYS, BUILTIN_PAINTS, COLOR_KEYS, GLOW_COLORS, PAINTED, PAINTS,  # noqa: E402
                           SCHEME_KEYS, compose, load_scheme, scheme_glows)
from cubegen.pipeline import rig_data, sidecar_paint  # noqa: E402

try:  # numpy ships with Blender's Python; the packing tests run where it is installed
    import numpy as np
except ImportError:  # pragma: no cover - depends on the interpreter
    np = None

HAS_TOOLS = find_blender() is not None and find_imagemagick() is not None
FIXTURE_V2 = os.path.join(ROOT, "tests", "fixtures", "contract_v2.json")
EXAMPLE = os.path.join(ROOT, "paints", "custom_example.json")
LAYOUT_1 = [["M_RobotDark", "M_Metal", "M_Warning"]]
LAYOUT_3 = [["M_Ground", "M_Wall", "M_Platform"], ["M_HazardOrange", "M_RobotBody", "M_RobotDark"], ["M_Metal"]]


def neutral_rig(layout=LAYOUT_1, paint="dark", maps=None, version_maps=("Albedo", "Normal", "MetallicSmoothness")):
    asset = generate_asset("crate", 3)
    rig = rig_data(asset, {"type": "crate", "seed": 3, "style": {}}, 1)
    keys = maps if maps is not None else ["W0", "W1", "Fields", "Normal"] + (["W2"] if len(layout) == 3 else [])
    rig["textures"] = {"mode": "baked", "manifest": "Textures/CubeEscape_Textures.json",
                       "baked": {k: f"Textures/MTP_Crate_000_dark_{k}.png" for k in version_maps},
                       "neutral": {k: f"Textures/MTN_Crate_000_{k}.png" for k in keys},
                       "weight_layout": layout}
    rig["paint"] = paint
    return rig


def _random_inputs(size, layout, seed=1):
    rng = np.random.RandomState(seed)
    weights = []
    for group in layout:
        w = rng.rand(size, size, 3).astype(np.float32)
        w[..., len(group):] = 0.0
        weights.append(w)
    fields = [rng.rand(size, size).astype(np.float32) for _ in range(4)]
    return weights, fields, neutral.noise(size, seed), (0.35 + 1.45 * rng.rand(size, size)).astype(np.float32)


class ContractVersion3Test(unittest.TestCase):
    def test_version_3_is_current_and_older_versions_stay_byte_for_byte_what_they_were(self):
        self.assertEqual(CONTRACT_VERSION, 3)
        self.assertEqual(sorted(CONTRACT["history"]), ["1", "2", "3"])
        with open(FIXTURE_V2, "r", encoding="utf-8") as fh:
            self.assertEqual(contract_for(2), json.load(fh))  # the file of cubegen 0.22/0.23
        self.assertNotIn("neutral_maps", contract_for(2))
        self.assertNotIn("paint", contract_for(2)["root"]["keys"])
        self.assertEqual(set(contract_for(1)) - {"version"}, set(contract_for(2)) - {"version", "history",
                                                                                     "baked_maps"})
        self.assertIn("paint", root_keys(3))
        self.assertNotIn("paint", root_keys(2))
        self.assertEqual(texture_keys(2), ("mode", "manifest", "baked"))
        self.assertEqual(texture_keys(3), ("mode", "manifest", "baked", "neutral", "weight_layout"))

    def test_contract_sections_equal_the_code(self):
        self.assertEqual(NEUTRAL_MAPS["keys"], list(neutral.NEUTRAL_KEYS))
        self.assertEqual(NEUTRAL_MAPS["required"], list(neutral.NEUTRAL_REQUIRED))
        self.assertEqual(NEUTRAL_MAPS["channels"], neutral.CHANNELS)
        self.assertEqual(NEUTRAL_MAPS["detail_range"], list(neutral.DETAIL_RANGE))
        self.assertEqual(NEUTRAL_MAPS["file_prefix"], neutral.PREFIX)
        self.assertEqual(NEUTRAL_MAPS["srgb"], [])  # data maps: all linear
        self.assertEqual(PAINT_SCHEME["keys"], list(SCHEME_KEYS))
        self.assertEqual(PAINT_SCHEME["painted"], list(PAINTED))
        self.assertEqual(PAINT_SCHEME["amounts"], list(AMOUNT_KEYS))
        self.assertEqual(PAINT_SCHEME["colors"], list(COLOR_KEYS))
        self.assertEqual(PAINT_SCHEME["glow"], list(GLOW_COLORS))

    def test_contract_command_writes_every_version(self):
        from cubegen.cli import main

        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "v2.json")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["contract", "--version", "2", "--out", path]), 0)
            with open(path, "r", encoding="utf-8") as fh, open(FIXTURE_V2, "r", encoding="utf-8") as fix:
                self.assertEqual(json.load(fh), json.load(fix))


class SidecarNeutralTest(unittest.TestCase):
    def test_valid_neutral_sidecar_for_version_3_rejected_by_older_importers(self):
        self.assertEqual(check_sidecar(neutral_rig())[0], [])
        self.assertEqual(check_sidecar(neutral_rig(LAYOUT_3))[0], [])
        # the root key is found first (the importer stops there, like check_sidecar)
        self.assertEqual(check_sidecar(neutral_rig(), version=2)[0],
                         ["root: unknown key 'paint' (contract version 3, this importer reads version 2)"])
        self.assertEqual(len(check_sidecar(neutral_rig(), version=1)[0]), 1)
        rig = neutral_rig()
        del rig["paint"]
        errors = check_sidecar(rig, version=2)[0]
        self.assertIn("textures: unknown key 'neutral' (contract version 3, this importer reads version 2)", errors)
        self.assertIn("textures: unknown key 'weight_layout' (contract version 3, this importer reads version 2)",
                      errors)

    def test_neutral_map_rules(self):
        def errors(rig):
            return check_sidecar(rig)[0]

        self.assertIn("textures.neutral: missing map 'W1'", errors(neutral_rig(maps=["W0", "Fields", "Normal"])))
        self.assertIn("textures.neutral: W2 goes with a third weight group (weight_layout has 1)",
                      errors(neutral_rig(maps=["W0", "W1", "W2", "Fields", "Normal"])))
        self.assertIn("textures.neutral: W2 goes with a third weight group (weight_layout has 3)",
                      errors(neutral_rig(LAYOUT_3, maps=["W0", "W1", "Fields", "Normal"])))
        self.assertIn("textures.neutral: unknown map 'Noise'",
                      errors(neutral_rig(maps=["W0", "W1", "Fields", "Normal", "Noise"])))
        self.assertTrue(any("paint_scheme.painted order" in e
                            for e in errors(neutral_rig([["M_Metal", "M_Ground"]]))))
        self.assertTrue(any("groups of three" in e for e in errors(neutral_rig([["M_Ground"], ["M_Wall"]]))))
        self.assertTrue(any("is not a painted material" in e for e in errors(neutral_rig([["M_Crystal"]]))))
        rig = neutral_rig()
        rig["textures"]["neutral"]["W1"] = rig["textures"]["neutral"]["W0"]
        self.assertIn("textures.neutral: every map needs its own file", errors(rig))
        rig = neutral_rig()
        del rig["paint"]
        self.assertIn("textures.neutral needs the paint scheme (root key 'paint')", errors(rig))
        rig = neutral_rig()
        del rig["textures"]["weight_layout"]
        self.assertIn("textures: neutral and weight_layout go together", errors(rig))
        rig = neutral_rig()
        rig["textures"]["mode"] = "tiled"
        del rig["textures"]["baked"]
        self.assertIn("textures: neutral maps need mode baked", errors(rig))

    def test_paint_is_a_builtin_name_or_a_complete_custom_scheme(self):
        self.assertIn("paint: 'rainbow' is no built-in scheme", check_sidecar(neutral_rig(paint="rainbow"))[0][0])
        name, scheme = load_scheme(EXAMPLE)
        custom = sidecar_paint(name, scheme)
        self.assertEqual(set(custom), set(SCHEME_KEYS) | {"name"})
        self.assertEqual(sorted(custom["colors"]), sorted(PAINTED))  # complete: the shader needs every colour
        self.assertEqual(check_sidecar(neutral_rig(paint=custom))[0], [])
        self.assertEqual(sidecar_paint("crystal"), "crystal")
        broken = dict(custom, wear=2.0)
        self.assertIn("wear must be a number from 0 to 1", check_sidecar(neutral_rig(paint=broken))[0][0])
        self.assertIn("is a built-in scheme", check_sidecar(neutral_rig(paint=dict(custom, name="dark")))[0][0])
        partial = dict(custom, colors={"M_Wall": "#112233"})
        self.assertIn("paint.colors: missing", check_sidecar(neutral_rig(paint=partial))[0][0])

    def test_export_check_finds_missing_neutral_files(self):
        with tempfile.TemporaryDirectory() as d:
            rig = neutral_rig()
            with open(os.path.join(d, rig["model"] + ".cubegen.json"), "w", encoding="utf-8") as fh:
                json.dump(rig, fh)
            os.makedirs(os.path.join(d, "Textures"))
            for path in list(rig["textures"]["baked"].values()) + list(rig["textures"]["neutral"].values()):
                if "Fields" not in path:
                    open(os.path.join(d, path), "wb").close()
            self.assertEqual(check_export(d)[rig["model"]]["errors"],
                             ["textures.neutral.Fields: file 'Textures/MTN_Crate_000_Fields.png' missing"])


class PaintCatalogTest(unittest.TestCase):
    def test_paint_catalog_is_complete_and_fast(self):
        from cubegen.cli import main

        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["catalog", "--paints"]), 0)
        data = json.loads(out.getvalue())
        self.assertEqual(data["catalog"], 1)
        self.assertNotIn("types", data)  # only the schemes: no model builds
        self.assertEqual(data["paint_keys"], list(SCHEME_KEYS))
        self.assertEqual(sorted(data["paint_schemes"]), sorted(BUILTIN_PAINTS))
        for name, scheme in data["paint_schemes"].items():
            self.assertEqual(set(scheme), set(SCHEME_KEYS), name)
            self.assertEqual(sorted(scheme["colors"]), sorted(PAINTED), name)
            self.assertEqual(scheme, PAINTS[name])


@unittest.skipUnless(np is not None, "numpy required (Blender's Python has it)")
class PackingTest(unittest.TestCase):
    def test_noise_is_the_formula_of_0170(self):
        size, seed = 48, 19
        expected = 0.6 * neutral._grid_noise(size, seed, 32) + 0.4 * neutral._grid_noise(size, seed + 1, 160)
        self.assertTrue(np.array_equal(neutral.noise(size, seed), expected))
        self.assertTrue(np.array_equal(neutral.noise(size, seed), neutral.noise(size, seed)))
        self.assertFalse(np.array_equal(neutral.noise(size, seed), neutral.noise(size, seed + 2)))

    def test_detail_encoding_covers_the_clamp_of_detail_map(self):
        lo, hi = neutral.DETAIL_RANGE
        self.assertEqual(int(neutral.encode_detail(np.float32(lo))), 0)
        self.assertEqual(int(neutral.encode_detail(np.float32(hi))), 255)
        self.assertEqual(int(neutral.encode_detail(np.float32(9.0))), 255)
        values = np.linspace(lo, hi, 1000, dtype=np.float32)
        back = neutral.decode_detail(neutral.encode_detail(values))
        self.assertLess(float(np.abs(back - values).max()), (hi - lo) / 255 / 2 + 1e-6)
        self.assertAlmostEqual(float(neutral.decode_detail(neutral.encode_detail(np.float32(1.0)))), 1.0, delta=0.003)

    def test_pack_and_unpack_give_the_8_bit_values_a_shader_samples(self):
        size = 16
        for layout in (LAYOUT_1, LAYOUT_3):
            weights, (ao, edge, up, height), noise, detail = _random_inputs(size, layout)
            packed = neutral.pack(weights, layout, ao, edge, up, height, noise, detail)
            self.assertEqual(sorted(packed), sorted(["W0", "W1", "Fields"] + (["W2"] if len(layout) == 3 else [])))
            for key, image in packed.items():
                self.assertEqual(image.shape, (size, size, 4), key)
                self.assertEqual(image.dtype, np.uint8, key)
            if len(layout) == 1:
                self.assertEqual(int(packed["W1"][..., :3].max()), 0)  # no second group: black weights
            else:
                self.assertEqual(int(packed["W2"][..., 3].min()), 255)  # reserved alpha
            m = neutral.unpack(packed, layout)
            step = 1 / 255 / 2 + 1e-6
            self.assertLess(float(np.abs(m["noise"] - noise).max()), step)
            self.assertLess(float(np.abs(m["ao"] - ao).max()), step)
            self.assertLess(float(np.abs(m["height"] - height).max()), step)
            self.assertLess(float(np.abs(m["weights"][0] - weights[0]).max()), step)
            self.assertLess(float(np.abs(m["detail"] - detail).max()), 1.45 / 255 / 2 + 1e-6)
            again = neutral.pack(m["weights"], layout, m["ao"], m["edge"], m["up"], m["height"], m["noise"],
                                 m["detail"])
            for key in packed:  # stable: packing the unpacked values gives the same bytes
                self.assertTrue(np.array_equal(again[key], packed[key]), key)

    def test_compose_packed_is_compose_on_the_unpacked_values(self):
        weights, (ao, edge, up, height), noise, detail = _random_inputs(12, LAYOUT_1, seed=5)
        packed = neutral.pack(weights, LAYOUT_1, ao, edge, up, height, noise, detail)
        m = neutral.unpack(packed, LAYOUT_1)
        for paint in ("dark", "organic", "sand"):
            a = neutral.compose_packed(packed, LAYOUT_1, paint)
            b = compose(m["weights"], [tuple(g) for g in LAYOUT_1], m["ao"], m["edge"], m["up"], m["noise"], paint,
                        m["detail"], m["height"])
            for key in a:
                self.assertTrue(np.array_equal(a[key], b[key]), (paint, key))
            maps = neutral.final_maps(a)
            self.assertEqual(maps["MetallicSmoothness"].shape, (12, 12, 4))
            self.assertEqual(maps["Albedo"].shape, (12, 12, 3))

    def test_png_roundtrip_and_every_filter(self):
        rng = np.random.RandomState(3)
        with tempfile.TemporaryDirectory() as d:
            for channels in (1, 2, 3, 4):
                image = rng.randint(0, 256, (7, 5, channels)).astype(np.uint8)
                path = neutral.write_png(os.path.join(d, f"c{channels}.png"), image)
                self.assertTrue(np.array_equal(neutral.read_png(path), image), channels)
            # rows filtered with None, Sub, Up, Average and Paeth (Blender and ImageMagick use them)
            image = rng.randint(0, 256, (5, 6, 3)).astype(np.uint8)
            path = os.path.join(d, "filtered.png")
            _write_filtered(path, image[::-1])
            self.assertTrue(np.array_equal(neutral.read_png(path), image))
            once = neutral.write_png(os.path.join(d, "a.png"), image)
            with open(once, "rb") as a, open(neutral.write_png(os.path.join(d, "b.png"), image), "rb") as b:
                self.assertEqual(a.read(), b.read())  # deterministic bytes


def _write_filtered(path, rows):
    """A PNG (RGB, top-down ``rows``) whose rows use filters 0..4 in turn."""
    h, w, c = rows.shape
    data = rows.astype(int)
    raw = b""
    for y in range(h):
        kind = y % 5
        line = data[y].reshape(-1)
        prev = data[y - 1].reshape(-1) if y else [0] * len(line)
        out = []
        for i, x in enumerate(line):
            a = line[i - c] if i >= c else 0
            b, cc = prev[i], (prev[i - c] if i >= c else 0)
            if kind == 0:
                pred = 0
            elif kind == 1:
                pred = a
            elif kind == 2:
                pred = b
            elif kind == 3:
                pred = (a + b) // 2
            else:
                p = a + b - cc
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - cc)
                pred = a if pa <= pb and pa <= pc else b if pb <= pc else cc
            out.append((x - pred) & 0xFF)
        raw += bytes([kind] + out)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


@unittest.skipUnless(np is not None, "numpy required (Blender's Python has it)")
class ReferenceToolTest(unittest.TestCase):
    def _fake_run(self, d, paint="crystal", scheme=None):
        """A run folder like generate --paint writes it: packed maps, the MTP_ maps of its scheme, a manifest."""
        import paint_reference as ref  # noqa: F401  (registers nothing yet)

        textures = os.path.join(d, "models", "Textures")
        os.makedirs(textures)
        weights, (ao, edge, up, height), noise, detail = _random_inputs(16, LAYOUT_3, seed=7)
        packed = neutral.pack(weights, LAYOUT_3, ao, edge, up, height, noise, detail)
        files = neutral.write_neutral(packed, "Thing_000", textures)
        files["Normal"] = neutral.write_png(os.path.join(textures, "MTN_Thing_000_Normal.png"),
                                            np.full((16, 16, 3), 128, np.uint8))
        if scheme:
            from cubegen.paint import register_scheme

            register_scheme(paint, scheme)
        baked = {}
        for key, image in neutral.final_maps(neutral.compose_packed(packed, LAYOUT_3, paint)).items():
            if key == "Emission" and not scheme_glows(paint):
                continue
            baked[key] = os.path.relpath(neutral.write_png(os.path.join(textures, f"MTP_Thing_000_{paint}_{key}.png"),
                                                           image), d)
        manifest = {"config": {"paint": paint, "paint_scheme": scheme},
                    "models": [{"name": "Thing_000", "type": "thing", "weight_layout": LAYOUT_3, "baked": baked,
                                "neutral_maps": {k: os.path.relpath(v, d) for k, v in files.items()}}]}
        with open(os.path.join(d, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh)
        return baked

    def test_reference_per_scheme_and_check_of_the_run(self):
        import paint_reference as ref

        with tempfile.TemporaryDirectory() as d:
            baked = self._fake_run(d)
            self.assertEqual(ref.check_run(d, log=lambda _: None), [])
            index = ref.write_reference(d, os.path.join(d, "ref"), log=lambda _: None)
            self.assertEqual(sorted(index["schemes"]), sorted(BUILTIN_PAINTS))
            row = index["models"][0]
            self.assertEqual(row["weight_layout"], LAYOUT_3)
            for paint, files in row["references"].items():
                self.assertEqual("Emission" in files, scheme_glows(paint), paint)
                for path in files.values():
                    self.assertTrue(os.path.isfile(os.path.join(d, "ref", path)), path)
            with open(os.path.join(d, "ref", row["references"]["crystal"]["Albedo"]), "rb") as a, \
                    open(os.path.join(d, baked["Albedo"]), "rb") as b:
                self.assertEqual(a.read(), b.read())  # the run's own scheme: the same file
            # a changed pixel in the run is found
            path = os.path.join(d, baked["Roughness"])
            image = neutral.read_png(path)
            image[3, 4, 0] ^= 8
            neutral.write_png(path, image)
            problems = ref.check_run(d, log=lambda _: None)
            self.assertEqual(len(problems), 1)
            self.assertIn("Roughness differs by up to 8", problems[0])

    def test_custom_scheme_of_the_run_is_part_of_the_reference(self):
        import paint_reference as ref

        name, scheme = load_scheme(EXAMPLE)
        with tempfile.TemporaryDirectory() as d:
            self._fake_run(d, name, scheme)
            index = ref.write_reference(d, os.path.join(d, "ref"), ["dark", name], log=lambda _: None)
            self.assertEqual(sorted(index["schemes"]), sorted(["dark", name]))
            self.assertEqual(ref.check_run(d, log=lambda _: None), [])
            with self.assertRaises(ValueError):
                ref.write_reference(d, os.path.join(d, "ref2"), ["rainbow"], log=lambda _: None)


class CrystalSplitTest(unittest.TestCase):
    """Cube Escape MATERIALS.md › Zuarbeit 4: M_Crystal is a real crystal only, the rest has its own names."""

    def test_only_crystal_types_use_m_crystal(self):
        from cubegen.materials import CRYSTAL_SPLIT, CRYSTAL_TYPES
        from cubegen.models import REGISTRY

        users, split = set(), set()
        for model_type in sorted(REGISTRY):
            variants = [{}]
            for param in REGISTRY[model_type].params:  # every choice once, so optional crystals show up too
                if param.kind == "choice":
                    variants += [{param.name: str(c)} for c in param.choices]
                elif param.kind == "bool":
                    variants.append({param.name: "true"})
            for seed in range(3):
                for params in variants:
                    for o in generate_asset(model_type, seed, params=params).meshes():
                        if "M_Crystal" in o.mesh.roles:
                            users.add(model_type)
                            self.assertIn(o.name, ("Crystals", "Rotor", "Glow", "Deck"), (model_type, o.name))
                        split.update(r for r in o.mesh.roles if r in CRYSTAL_SPLIT)
        self.assertLessEqual(users, set(CRYSTAL_TYPES), sorted(users - set(CRYSTAL_TYPES)))
        self.assertEqual(split, set(CRYSTAL_SPLIT))  # every new name is used

    def test_split_names_look_like_m_crystal_and_keep_their_own_material(self):
        from cubegen.materials import CRYSTAL_SPLIT, KEEP_OWN, LEGACY_NAMES, MATERIALS
        from cubegen.models.destruction import GLOW
        from cubegen.palette import uv

        self.assertEqual(list(MATERIALS)[-len(CRYSTAL_SPLIT):], list(CRYSTAL_SPLIT))  # appended at the end
        for name in CRYSTAL_SPLIT:
            self.assertEqual(MATERIALS[name], MATERIALS["M_Crystal"], name)
            self.assertEqual(LEGACY_NAMES[name], "M_Crystal")
            self.assertIn(name, KEEP_OWN)
            self.assertIn(name, GLOW)
            self.assertEqual(uv(name), uv("M_Crystal"))  # palette mode: the crystal's cell, image unchanged
        self.assertEqual(CONTRACT["materials"]["split"], CRYSTAL_SPLIT)

    def test_legacy_names_give_the_models_of_0230(self):
        """Only the names changed: mapped back, every changed golden case is the digest of cubegen 0.23.0."""
        import golden_cases
        from cubegen.params import Style

        with open(os.path.join(ROOT, "tests", "fixtures", "golden_0230_crystal.json"), "r", encoding="utf-8") as fh:
            old = json.load(fh)
        cases = {name: (seed, style) for name, seed, style in golden_cases.CASES}
        self.assertEqual(len(old), 20)
        for model_type, digests in sorted(old.items()):
            for case in ("seed0", "styled", "destroyed", "gen1_seed1"):
                if case not in digests:
                    continue
                seed, style = cases[case]
                asset = generate_asset(model_type, seed, style=Style.from_dict(style))
                self.assertNotEqual(asset.digest(), digests[case], (model_type, case))
                self.assertTrue(asset.legacy_materials(), model_type)
                self.assertEqual(asset.digest(), digests[case], (model_type, case))

    def test_contract_versions_and_the_rueckweg(self):
        from cubegen.cli import build_config, make_parser
        from cubegen.pipeline import build_spec, plan_models, split_materials

        self.assertNotIn("materials", contract_for(2))
        asset = generate_asset("water_level", 1, params={"fluid": "water"})
        rig = rig_data(asset, {"type": "water_level", "seed": 1, "style": {}}, 1)
        self.assertEqual(check_sidecar(rig)[0], [])
        errors = check_sidecar(rig, version=2)[0]
        self.assertTrue(errors and all("M_Liquid (contract version 3" in e for e in errors), errors)
        panel = generate_asset("sequence_panel", 0, params={"buttons": "6"})
        rig = rig_data(panel, {"type": "sequence_panel", "seed": 0, "style": {}}, 1)
        self.assertTrue(any("M_Signal (contract version 3" in e for e in check_sidecar(rig, version=2)[0]))
        rig = rig_data(generate_asset("crate", 1), {"type": "crate", "seed": 1, "style": {}}, 1)
        mesh = next(part["name"] for part in rig["parts"] if not part["empty"])
        rig["behaviours"].append({"script": "SignalIndicator", "parts": {"renderers": [mesh]},
                                  "fields": {"offMaterial": "M_RobotDark", "onMaterial": "M_Signal"}})
        rig["static"] = False
        self.assertTrue(any(e.startswith("SignalIndicator.onMaterial: material M_Signal")
                            for e in check_sidecar(rig, version=2)[0]))
        for contract, legacy in ((3, False), (2, True), (1, True)):
            args = make_parser().parse_args(["generate", "--types", "water_level,sequence_panel", "--no-blender",
                                             "--contract", str(contract)])
            config = build_config(args)
            config.validate()
            for spec in plan_models(config):
                self.assertEqual(bool(spec.get("legacy_materials")), legacy)
                rig = rig_data(build_spec(spec), spec, 1)
                self.assertEqual(check_sidecar(rig, version=contract)[0], [], (contract, spec["name"]))
        table = split_materials()
        self.assertEqual(table["split"]["M_Hologram"]["emission"], 2.5)
        self.assertEqual(table["split"]["M_Hologram"]["legacy"], "M_Crystal")
        self.assertFalse(split_materials(written=False)["written"])


class UnityCheckNeutralProbeTest(unittest.TestCase):
    def test_neutral_probe_runs_rejected_and_imported_below_version_3(self):
        import unity_check

        self.assertIn("neutral", unity_check.PROBES)
        self.assertIn("neutral", unity_check.QUICK)
        self.assertEqual(unity_check.PROBES["neutral"]["contract"], 3)
        self.assertIn("vending_machine", unity_check.PROBES["neutral"]["args"][1])  # three weight groups: W2
        self.assertEqual(unity_check.legs("neutral", 1), [{"contract": 3, "expect": "reject"},
                                                          {"contract": 1, "expect": "import"}])
        self.assertEqual(unity_check.legs("neutral", 2)[1], {"contract": 2, "expect": "import"})
        self.assertEqual(unity_check.legs("neutral", 3), [{"contract": 3, "expect": "import"}])
        self.assertEqual(unity_check.legs("neutral", None), [{"contract": 3, "expect": "import"}])
        self.assertEqual(unity_check.legs("paint", 1), [{"contract": 1, "expect": "import"}])
        command = unity_check.generate_command("neutral", "out", 3)
        self.assertEqual(command[command.index("--contract") + 1], "3")

    def test_expected_rejection_needs_a_failed_run_naming_every_model(self):
        import unity_check

        failed = ("Failed | bestanden 0 | fehlgeschlagen 1 |\nCrate_000: Unbekannter Schlüssel paint\n"
                  "Wall_000: Unbekannter Schlüssel paint\n")
        self.assertTrue(unity_check.expected_rejection(failed, ["Crate_000", "Wall_000"]))
        self.assertFalse(unity_check.expected_rejection(failed, ["Crate_000", "Pillar_000"]))
        self.assertFalse(unity_check.expected_rejection("Passed | bestanden 1 | fehlgeschlagen 0 |", ["Crate_000"]))
        line = unity_check.summary_line({"name": "neutral", "ok": True, "exports": 6, "seconds": {"unity": 1},
                                         "integration": {"gameplay": 0, "static": 6, "unmapped_items": 0,
                                                         "rejected": 0, "errors": 0},
                                         "rejected_as_expected": {"contract": 3, "models": 6, "ok": True}})
        self.assertIn("mit Vertrag 3 6 abgelehnt wie erwartet", line)


@unittest.skipUnless(HAS_TOOLS and np is not None, "Blender, ImageMagick and numpy required")
class NeutralExportTest(unittest.TestCase):
    """Real --paint runs (Blender): neutral maps in sidecar and manifest, Python reference = Blender's MTP_ maps."""

    def _run(self, out, *extra):
        from cubegen.cli import main

        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["generate", "--seed", "19", "--pick", "crate:0,vending_machine:0",
                                   "--texture-size", "64", "--no-render", "--no-blend", "--bake-device", "cpu",
                                   "--out", out, *extra]), 0)
        with open(os.path.join(out, "manifest.json"), "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _sidecar(self, out, name):
        with open(os.path.join(out, "models", f"{name}.cubegen.json"), "r", encoding="utf-8") as fh:
            return json.load(fh)

    def test_paint_run_writes_neutral_maps_and_the_scheme(self):
        import paint_reference as ref

        with tempfile.TemporaryDirectory() as out:
            manifest = self._run(out, "--paint", "dark")
            by_name = {m["name"]: m for m in manifest["models"]}
            vending = by_name["VendingMachine_000"]
            self.assertEqual(len(vending["weight_layout"]), 3)
            self.assertEqual(sorted(vending["neutral_maps"]), sorted(neutral.NEUTRAL_KEYS))
            self.assertEqual(sorted(by_name["Crate_000"]["neutral_maps"]), ["Fields", "Normal", "W0", "W1"])
            rig = self._sidecar(out, "VendingMachine_000")
            self.assertEqual(rig["paint"], "dark")
            self.assertEqual(rig["textures"]["weight_layout"], vending["weight_layout"])
            self.assertEqual(sorted(rig["textures"]["neutral"]), sorted(neutral.NEUTRAL_KEYS))
            self.assertEqual(rig["textures"]["neutral"]["W2"], "Textures/MTN_VendingMachine_000_W2.png")
            self.assertEqual(check_sidecar(rig)[0], [])
            self.assertEqual(sum(len(v["errors"]) for v in check_export(os.path.join(out, "models")).values()), 0)
            for entry in manifest["models"]:
                images = {k: neutral.read_png(os.path.join(out, v)) for k, v in entry["neutral_maps"].items()}
                for key in ("W0", "W1", "W2", "Fields"):
                    if key in images:
                        self.assertEqual(images[key].shape, (64, 64, 4), key)
                self.assertGreater(float(images["W0"][..., 3].std()), 0)  # the noise channel varies
            # Python composes exactly what Blender saved (the shader's reference)
            self.assertEqual(ref.check_run(out, log=lambda _: None), [])
            # the normal map: the same pixels as the scheme's normal
            normal = neutral.read_png(os.path.join(out, vending["neutral_maps"]["Normal"]))
            self.assertTrue(np.array_equal(normal, neutral.read_png(os.path.join(out, vending["baked"]["Normal"]))))

    def test_contract_2_leaves_the_neutral_maps_in_the_manifest_only(self):
        with tempfile.TemporaryDirectory() as out:
            manifest = self._run(out, "--paint", "crystal", "--contract", "2")
            rig = self._sidecar(out, "Crate_000")
            self.assertNotIn("paint", rig)
            self.assertEqual(sorted(rig["textures"]), ["baked", "manifest", "mode"])
            self.assertIn("Emission", rig["textures"]["baked"])
            self.assertEqual(check_sidecar(rig, version=2)[0], [])
            self.assertTrue(all(m.get("neutral_maps") for m in manifest["models"]))

    def test_custom_scheme_travels_as_data(self):
        with tempfile.TemporaryDirectory() as out:
            self._run(out, "--paint-file", EXAMPLE)
            rig = self._sidecar(out, "Crate_000")
            name, scheme = load_scheme(EXAMPLE)
            self.assertEqual(rig["paint"]["name"], name)
            self.assertEqual({k: v for k, v in rig["paint"].items() if k != "name"}, scheme)
            self.assertEqual(check_sidecar(rig)[0], [])

    def test_neutral_maps_are_reproducible(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first, second = self._run(a, "--paint", "ruin"), self._run(b, "--paint", "ruin")
            for m1, m2 in zip(first["models"], second["models"]):
                for key, path in m1["neutral_maps"].items():
                    with open(os.path.join(a, path), "rb") as f1, \
                            open(os.path.join(b, m2["neutral_maps"][key]), "rb") as f2:
                        self.assertEqual(f1.read(), f2.read(), (m1["name"], key))

    def test_paint_reference_tool_from_the_command_line(self):
        with tempfile.TemporaryDirectory() as out:
            self._run(out, "--paint", "toxic")
            tool = os.path.join(ROOT, "tools", "paint_reference.py")
            result = subprocess.run([sys.executable, tool, out, "--paints", "toxic,clean"], capture_output=True,
                                    text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with open(os.path.join(out, "paint_reference", "reference.json"), "r", encoding="utf-8") as fh:
                index = json.load(fh)
            self.assertEqual(sorted(index["schemes"]), ["clean", "toxic"])
            self.assertEqual(subprocess.run([sys.executable, tool, out, "--check"], capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
