"""Quality checks: z-fighting detection works, triangle budgets hold, z-fighting never gets worse, colliders cover
the solid geometry."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import golden_cases  # noqa: E402
from cubegen.asset import Asset  # noqa: E402
from cubegen.models.common import cube  # noqa: E402
from cubegen.quality import DECAL_OFFSET, check, fix_z_fighting, uncovered_geometry, z_fighting  # noqa: E402


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

    def test_fix_lifts_the_smaller_face(self):
        a = Asset("t")
        body = a.part("Body")
        cube(body, (1, 1, 1), (0, 0, 0.5), "M_Wall")
        cube(body, (0.4, 0.2, 0.3), (0, -0.4, 0.5), "M_Warning")  # stripe flush with the front
        self.assertEqual(fix_z_fighting(a), 1)
        self.assertEqual(z_fighting(a), [])
        ys = sorted({round(v[1], 6) for v in body.verts})
        self.assertEqual(ys[0], round(-0.5 - DECAL_OFFSET, 6))  # the stripe now sits 2 mm proud ...
        self.assertIn(-0.5, ys)  # ... the body's front stays where it was

    def test_check_reports_budget(self):
        a = Asset("t")
        for i in range(400):
            cube(a.part("Body"), (0.1, 0.1, 0.1), (i * 0.2, 0, 0.05), "M_Wall")  # 4800 triangles
        result = check(a, "props")
        self.assertTrue(result["errors"])


class ColliderCoverageTests(unittest.TestCase):
    def test_finds_solid_geometry_without_collider(self):
        a = Asset("t")
        body = a.part("Body")
        cube(body, (2, 0.5, 3), (0, 0, 1.5), "M_Wall")
        a.collider((2, 0.5, 3), (0, 0.25, 1.5))  # half a wall thickness off, like the archway once was
        found = uncovered_geometry(a)
        self.assertEqual([f["object"] for f in found], ["Body"])
        self.assertAlmostEqual(found[0]["uncovered"], 1 / 3, places=3)
        self.assertTrue(check(a, "environment")["warnings"])
        a.colliders.clear()
        a.collider((2, 0.5, 3), (0, 0, 1.5))
        self.assertEqual(uncovered_geometry(a), [])

    def test_ignores_what_needs_no_collider(self):
        a = Asset("t")
        body = a.part("Body")
        cube(body, (1, 1, 1), (0, 0, 0.5), "M_Wall")
        a.collider((1, 1, 1), (0, 0, 0.5))
        cube(body, (2, 0.05, 0.05), (0, 1, 2), "M_Metal")  # a rail: too thin
        cube(body, (0.3, 0.3, 0.3), (0, 2, 0.15), "M_Metal")  # a small box: too small (0.027 m3)
        cube(a.part("Damage"), (0.6, 0.6, 0.6), (2, 0, 0.3), "M_Metal")  # only shows while broken
        self.assertEqual(uncovered_geometry(a), [])
        cube(body, (0.6, 0.6, 0.6), (0, 0, -0.5), "M_Metal")  # under the floor of a platform
        self.assertEqual(uncovered_geometry(a, pivot="top"), [])
        self.assertTrue(uncovered_geometry(a, pivot="floor"))


class BaselineTests(unittest.TestCase):
    def test_colliders_cover_solid_geometry(self):
        # every solid piece a player can walk into has a collision shape - in every state and detail level
        from cubegen.models import REGISTRY, generate_asset, model_types
        from cubegen.params import Style

        for style in (Style(), Style(damage="damaged"), Style(damage="destroyed"), Style(damage="fractured"),
                      Style(wear="heavy"), Style(detail="low"), Style(size="L")):
            for t in model_types():
                for seed in range(3):
                    found = uncovered_geometry(generate_asset(t, seed, style=style), REGISTRY[t].pivot)
                    self.assertEqual(found, [], f"{t} {seed} {style.to_dict()}")

    def test_no_z_fighting_in_any_state(self):
        # generate_asset lifts flush details (quality.fix_z_fighting) - in every state and detail level
        from cubegen.models import REGISTRY, generate_asset, model_types
        from cubegen.params import Style

        for style in (Style(damage="damaged"), Style(damage="destroyed"), Style(damage="fractured"), Style(wear="heavy"),
                      Style(detail="low")):
            for t in model_types():
                for seed in range(3):
                    found = z_fighting(generate_asset(t, seed, style=style), pivot=REGISTRY[t].pivot)
                    self.assertEqual(found, [], f"{t} {seed} {style.to_dict()}")

    def test_draw_call_budget_in_any_state(self):
        # 16 per model, or 2 per object + 2 for models of many separately moving objects; static: per material
        from cubegen.models import generate_asset, model_types
        from cubegen.params import Style
        from cubegen.quality import draw_call_budget, draw_calls

        for style in (Style(), Style(damage="damaged"), Style(damage="destroyed"), Style(damage="fractured"),
                      Style(wear="heavy"), Style(detail="high")):
            for t in model_types():
                for seed in range(3):
                    a = generate_asset(t, seed, style=style)
                    self.assertLessEqual(draw_calls(a), draw_call_budget(a), f"{t} {seed} {style.to_dict()}")

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
