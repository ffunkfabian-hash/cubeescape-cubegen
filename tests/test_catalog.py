"""The machine-readable catalog for game front ends (``cubegen catalog``, 0.11.4)."""
import argparse
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.cli import CATALOG_OPTIONS, catalog_data, main, make_parser  # noqa: E402
from cubegen.families import family_files  # noqa: E402
from cubegen.models import REGISTRY  # noqa: E402
from cubegen.palette import palette_names  # noqa: E402


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.data = catalog_data()

    def test_every_registered_type_with_its_parameter_schema(self):
        self.assertEqual(set(self.data["types"]), set(REGISTRY))
        for name, entry in REGISTRY.items():
            listed = self.data["types"][name]
            self.assertEqual(listed["title"], entry.title)
            self.assertEqual(listed["pivot"], entry.pivot)
            self.assertEqual([p["name"] for p in listed["params"]], [p.name for p in entry.params])
            for param, spec in zip(listed["params"], entry.params):
                self.assertEqual(param["kind"], spec.kind)
                self.assertEqual(param["choices"], [str(c) for c in spec.choices])
                if spec.kind in ("float", "int"):
                    self.assertEqual((param["min"], param["max"]), (spec.lo, spec.hi))

    def test_style_options_come_from_the_generate_parser(self):
        commands = next(a for a in make_parser()._actions if isinstance(a, argparse._SubParsersAction))
        actions = {a.dest: a for a in commands.choices["generate"]._actions}
        self.assertEqual(set(self.data["options"]), set(CATALOG_OPTIONS))
        for key, option in self.data["options"].items():
            self.assertEqual(option["choices"], [str(c) for c in (actions[key].choices or [])], key)
            self.assertEqual(option["flag"], actions[key].option_strings[0])

    def test_families_and_palettes_are_listed(self):
        self.assertEqual(set(self.data["families"]), set(family_files()))
        for family in self.data["families"].values():
            self.assertTrue(family["dims"])
            self.assertTrue(family["kit"])
        self.assertEqual(set(self.data["palettes"]), set(palette_names()))

    def test_typical_behaviours_are_a_reference_build_hint(self):
        self.assertEqual(self.data["types"]["door"]["typical"]["behaviours"], ["Door"])
        self.assertTrue(self.data["types"]["crate"]["typical"]["static"])
        for entry in self.data["types"].values():
            self.assertEqual(entry["typical"]["static"], not entry["typical"]["behaviours"])
            self.assertTrue(all(v >= 0 for v in entry["typical"]["size"]))

    def test_output_is_deterministic_json(self):
        runs = []
        for _ in range(2):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["catalog", "--json"]), 0)
            runs.append(out.getvalue())
        self.assertEqual(runs[0], runs[1])
        self.assertEqual(json.loads(runs[0])["catalog"], 1)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "sub", "catalog.json")
            self.assertEqual(main(["catalog", "--out", path]), 0)
            with open(path, encoding="utf-8") as fh:
                self.assertEqual(fh.read() + "\n", runs[0])


if __name__ == "__main__":
    unittest.main()
