"""Regression tests for deterministic, separate clutter props."""

import os
import sys
import unittest
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.models import generate_asset  # noqa: E402
from cubegen.params import Style  # noqa: E402


class ClutterTests(unittest.TestCase):
    def make_table(self, density):
        return generate_asset(
            "table",
            42017,
            params={"style": "table", "clutter": False},
            style=Style(clutter=density),
        )

    def test_none_preserves_the_regular_table(self):
        default = generate_asset("table", 42017, params={"style": "table"})
        explicit_none = generate_asset("table", 42017, params={"style": "table"},
                                       style=Style(clutter="none"))
        self.assertEqual(default.digest(), explicit_none.digest())
        self.assertFalse(any(obj.name.startswith("Clutter_") for obj in default.objects))

    def test_unsupported_table_variant_keeps_legacy_clutter(self):
        plain = generate_asset("table", 42017, params={"style": "round"})
        requested = generate_asset("table", 42017, params={"style": "round"},
                                   style=Style(clutter="lived-in"))
        self.assertEqual(plain.digest(), requested.digest())

    def test_explicit_legacy_clutter_cannot_be_silently_overridden(self):
        with self.assertRaisesRegex(ValueError, "table.clutter=true conflicts"):
            generate_asset("table", 42017, params={"style": "table", "clutter": True},
                           style=Style(clutter="lived-in"))

    def test_clutter_is_deterministic_and_kept_as_separate_objects(self):
        first = self.make_table("lived-in")
        second = self.make_table("lived-in")
        self.assertEqual(first.digest(), second.digest())
        props = [obj for obj in first.meshes() if obj.name.startswith("Clutter_")]
        self.assertTrue(props)
        self.assertEqual(len(props), len({obj.name for obj in props}))
        self.assertEqual(first.meta["clutter_pass"]["density"], "lived-in")
        self.assertFalse(first.meta["params"]["clutter"])
        self.assertEqual(len(first.meta["clutter_pass"]["placed"]),
                         len({obj.name.rsplit("_", 1)[0] for obj in props}))

    def test_props_fit_the_declared_surface_without_overlapping(self):
        asset = self.make_table("chaotic")
        bounds = asset.meta["clutter_pass"]["surfaces"][0]["bounds"]
        x0, x1, y0, y1, z = bounds
        groups = defaultdict(list)
        for obj in asset.meshes():
            if obj.name.startswith("Clutter_"):
                groups[obj.name.rsplit("_", 1)[0]].extend(obj.mesh.verts)

        boxes = []
        for name, vertices in groups.items():
            lo = tuple(min(vertex[i] for vertex in vertices) for i in range(3))
            hi = tuple(max(vertex[i] for vertex in vertices) for i in range(3))
            self.assertGreaterEqual(lo[0], x0 - 0.0001, name)
            self.assertLessEqual(hi[0], x1 + 0.0001, name)
            self.assertGreaterEqual(lo[1], y0 - 0.0001, name)
            self.assertLessEqual(hi[1], y1 + 0.0001, name)
            self.assertAlmostEqual(lo[2], z, delta=0.0001)
            boxes.append((lo, hi))

        for i, (lo, hi) in enumerate(boxes):
            for other_lo, other_hi in boxes[i + 1:]:
                separated = (hi[0] + 0.024 < other_lo[0] or other_hi[0] + 0.024 < lo[0] or
                             hi[1] + 0.024 < other_lo[1] or other_hi[1] + 0.024 < lo[1])
                self.assertTrue(separated)

    def test_individual_prop_type_remains_independently_generatable(self):
        prop = generate_asset("tool", 17)
        self.assertTrue(prop.meshes())
        self.assertFalse(any(obj.name.startswith("Clutter_") for obj in prop.objects))

    def test_density_and_damage_validation(self):
        with self.assertRaisesRegex(ValueError, "clutter requires damage='intact'"):
            Style(clutter="clean", damage="damaged").validate()
        with self.assertRaisesRegex(ValueError, "style clutter"):
            Style(clutter="messy").validate()


if __name__ == "__main__":
    unittest.main()
