import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.asset import Asset, AssetObject
from cubegen.families import load_family, validate_family_recipe
from cubegen.models import generate_asset
from cubegen.quality import asset_quality_report


class Release01021Tests(unittest.TestCase):
    def test_asset_contract_validation(self):
        asset = Asset("broken")
        asset.part("Body")
        asset.objects.append(AssetObject("Pivot", (0.0, 0.0, 0.0), "Missing", None))
        with self.assertRaises(ValueError):
            asset.validate_contract("door")

    def test_quality_summary_is_machine_readable(self):
        asset = generate_asset("crate", 11)
        report = asset_quality_report(asset)
        self.assertIn("score", report)
        self.assertIn("z_fighting_pairs", report)
        self.assertIn("passes", report)
        self.assertGreaterEqual(report["score"], 0)

    def test_family_recipe_validation(self):
        family = load_family("station")
        result = validate_family_recipe(family, family_name=family["family"])
        self.assertEqual(result["family"], "station")
        self.assertTrue(result["checked"])


if __name__ == "__main__":
    unittest.main()
