"""--unique: variants that look alike are skipped, names and seeds stay those of their index."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.models import generate_asset  # noqa: E402
from cubegen.pipeline import BatchConfig, plan_models  # noqa: E402
from cubegen.seeds import model_seed  # noqa: E402
from cubegen.variety import pick_unique, signature, similar  # noqa: E402


class VarietyTests(unittest.TestCase):
    def test_same_model_is_similar(self):
        a, b = signature(generate_asset("crate", 5)), signature(generate_asset("crate", 5))
        self.assertTrue(similar(a, b))
        self.assertTrue(similar(signature(generate_asset("crate", 5)),
                                signature(generate_asset("crate", 5, scale=1.02))))  # 2 % bigger: alike
        self.assertFalse(similar(a, signature(generate_asset("crate", 5, scale=1.5))))
        self.assertFalse(similar(a, signature(generate_asset("door", 5))))

    def test_unique_plan(self):
        # 0.19.0: the laser mirror's first eight differ since its variety details - the pressure plate still has
        # look-alikes among them
        config = BatchConfig(seed=42, models={"pressure_plate": 8}, out_dir="unused", unique=True)
        specs = plan_models(config)
        self.assertEqual(len(specs), 8)
        indices = [s["index"] for s in specs]
        self.assertEqual(indices[0], 0)
        self.assertGreater(indices[-1], 7)  # some of the first 8 looked alike and were skipped
        for spec in specs:
            self.assertEqual(spec["seed"], model_seed(42, "pressure_plate", spec["index"]))
            self.assertEqual(spec["name"], f"PressurePlate_{spec['index']:03d}")
        sigs = [signature(generate_asset("pressure_plate", s["seed"])) for s in specs]
        for i, a in enumerate(sigs):
            for b in sigs[i + 1:]:
                self.assertFalse(similar(a, b))
        self.assertEqual(plan_models(config), specs)  # deterministic

    def test_without_unique_nothing_changes(self):
        specs = plan_models(BatchConfig(seed=42, models={"laser_mirror": 8}, out_dir="unused"))
        self.assertEqual([s["index"] for s in specs], list(range(8)))

    def test_gives_up(self):
        found, tried = pick_unique(5, lambda i: generate_asset("crate", 1), max_tries=10)  # always the same
        self.assertEqual((found, tried), ([0], 10))


if __name__ == "__main__":
    unittest.main()
