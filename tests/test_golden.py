"""Every model type must still produce exactly the models of the reference file (see golden_cases.py)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import golden_cases  # noqa: E402


class GoldenTests(unittest.TestCase):
    def test_models_match_the_reference(self):
        expected = golden_cases.load()
        actual = golden_cases.compute()
        missing = sorted(set(actual) - set(expected))
        self.assertFalse(missing, f"no reference for new type(s) {missing} - run: "
                                  "python3 tests/golden_cases.py --update")
        changed = [f"{t}/{case}" for t in sorted(expected) if t in actual
                   for case in expected[t] if actual[t].get(case) != expected[t][case]]
        self.assertFalse(changed, "these models changed - existing seeds would look different. Intended? "
                                  f"python3 tests/golden_cases.py --update\n{', '.join(changed)}")
        self.assertFalse(sorted(set(expected) - set(actual)), "reference has types that no longer exist")


if __name__ == "__main__":
    unittest.main()
