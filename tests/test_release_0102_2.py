import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.asset import Asset
from cubegen import __version__
from cubegen.cli import main
from cubegen.families import compatibility_matrix
from cubegen.models import generate_asset
from cubegen.quality import check


class Release01022Tests(unittest.TestCase):
    def test_safe_repair_only_removes_unreferenced_faceless_meshes(self):
        asset = Asset("repair")
        asset.part("Unused")
        asset.part("Used")
        asset.empty("Child", (0.0, 0.0, 0.0), parent="Used")

        self.assertEqual(asset.repair_safe(), ["Unused"])
        self.assertIsNone(asset.get("Unused"))
        self.assertIsNotNone(asset.get("Used"))
        self.assertEqual(asset.meta["safe_repairs"][0]["object"], "Unused")

    def test_quality_check_has_severity(self):
        asset = generate_asset("crate", 42)
        result = check(asset, "props")
        self.assertIn(result["severity"], {"pass", "warning", "error"})

    def test_family_compatibility_matrix(self):
        wall = generate_asset("wall", 1, params={"opening": "door", "door_style": "sliding",
                                                 "door_width": 2.0, "door_height": 2.2})
        door = generate_asset("door", 2, params={"style": "sliding", "width": 2.0, "height": 2.2})
        matrix = compatibility_matrix([("Wall", wall, "wall"), ("Door", door, "door")])
        self.assertEqual(matrix["pairs"][0]["status"], "compatible")
        closed_wall = generate_asset("wall", 1)
        disconnected = compatibility_matrix([("Wall", closed_wall, "wall"), ("Door", door, "door")])
        self.assertEqual(disconnected["pairs"][0]["status"], "no_matching_connector")

    def test_validate_only_writes_report_without_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_path = os.path.join(tmp, "validation.json")
            out = os.path.join(tmp, "unused-output")
            code = main(["generate", "--seed", "42", "--types", "crate", "--count", "3", "--validate-only",
                         "--report", report_path, "--out", out])
            self.assertEqual(code, 0)
            self.assertFalse(os.path.exists(out))
            with open(report_path, encoding="utf-8") as fh:
                report = json.load(fh)
            self.assertEqual(report["version"], __version__)
            self.assertIn("source_hash", report)
            self.assertEqual(sorted(row["quality_rank"] for row in report["assets"]), [1, 2, 3])
            for row in report["assets"]:
                self.assertIn("asset_hash", row)
                self.assertIn(row["severity"], {"pass", "warning", "error"})
                self.assertGreaterEqual(row["quality_score"], 0)
                self.assertLessEqual(row["quality_score"], 100)
                self.assertIn("triangle_budget", row["quality"]["passes"])
                self.assertIn("similar_to", row)

    def test_gui_command_is_registered(self):
        with patch("cubegen.gui.main", return_value=0) as gui_main:
            self.assertEqual(main(["gui"]), 0)
        gui_main.assert_called_once_with()

    def test_strict_and_relaxed_are_mutually_exclusive(self):
        self.assertEqual(main(["generate", "--types", "crate", "--strict", "--relaxed"]), 2)


if __name__ == "__main__":
    unittest.main()
