"""Quality checks: z-fighting detection works, triangle budgets hold, z-fighting never gets worse."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import golden_cases  # noqa: E402
from cubegen.asset import Asset  # noqa: E402
from cubegen.models.common import cube  # noqa: E402
from cubegen.quality import check, z_fighting  # noqa: E402


class ZFightingTests(unittest.TestCase):
    def test_detects_flush_faces(self):
        a = Asset("t")
        body = a.part("Body")
        cube(body, (1, 1, 1), (0, 0, 0.5), "M_Wall")
        cube(body, (0.4, 0.2, 0.3), (0, -0.4, 0.5), "M_Warning")  # front face flush with the body's front
        found = z_fighting(a)
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0]["area"], 0.4 * 0.3, places=5)
        self.assertEqual(found[0]["materials"], ["M_Wall", "M_Warning"])

    def test_ignores_what_does_not_show(self):
        a = Asset("t")
        body = a.part("Body")
        cube(body, (1, 1, 1), (0, 0, 0.5), "M_Wall")
        cube(body, (0.4, 0.2, 0.3), (0, -0.41, 0.5), "M_Warning")  # 1 cm proud: fine
        cube(body, (0.5, 0.5, 0.2), (0, 0, 0.1), "M_Metal")  # inside, bottom on the floor: never seen
        cube(body, (0.3, 0.3, 0.3), (0.2, 0.2, 0.85), "M_Wall")  # same material, same object: identical pixels
        self.assertEqual(z_fighting(a), [])
        glow = a.part("Glow")
        cube(glow, (0.2, 0.2, 0.1), (-0.2, 0.2, 1.05), "M_Wall")  # sits on the top: faces opposite, fine
        self.assertEqual(z_fighting(a), [])
        cube(glow, (0.2, 0.2, 0.1), (-0.3, -0.2, 0.95), "M_Wall")  # top flush with the body's top
        self.assertEqual(len(z_fighting(a)), 1)  # other object, same material: scripts recolour it -> counts

    def test_check_reports_budget(self):
        a = Asset("t")
        for i in range(400):
            cube(a.part("Body"), (0.1, 0.1, 0.1), (i * 0.2, 0, 0.05), "M_Wall")  # 4800 triangles
        result = check(a, "props")
        self.assertTrue(result["errors"])


class BaselineTests(unittest.TestCase):
    def test_quality_never_gets_worse(self):
        baseline = golden_cases.load(golden_cases.QUALITY)
        current = golden_cases.quality()
        worse = []
        for t, row in current.items():
            base = baseline.get(t, {"z_fighting_pairs": 0, "z_fighting_variants": 0})  # new types: none at all
            if row["z_fighting_pairs"] > base["z_fighting_pairs"] or \
                    row["z_fighting_variants"] > base["z_fighting_variants"]:
                worse.append(f"{t}: z-fighting {row['z_fighting_pairs']} pair(s) in {row['z_fighting_variants']} "
                             f"variant(s), baseline {base['z_fighting_pairs']} in {base['z_fighting_variants']}")
        self.assertFalse(worse, "\n".join(worse) + "\n(python -m cubegen check --types TYPE shows details; "
                                                   "fixed on purpose? python3 tests/golden_cases.py --update)")

    def test_triangle_budgets(self):
        from cubegen.models import REGISTRY
        from cubegen.quality import DEFAULT_TRIANGLE_BUDGET, TRIANGLE_BUDGET

        for t, row in golden_cases.quality().items():
            budget = TRIANGLE_BUDGET.get(REGISTRY[t].category, DEFAULT_TRIANGLE_BUDGET)
            self.assertLessEqual(row["triangles"], budget, t)


if __name__ == "__main__":
    unittest.main()
