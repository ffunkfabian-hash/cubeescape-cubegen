"""cubegen 0.18.1: the glowing slot of test_wall_modules follows the style glow (a paint scheme's light colour)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class WallGlowFollowsTheStyleTest(unittest.TestCase):
    def glow_materials(self, *extra):
        from cubegen.cli import build_config, make_parser
        from cubegen.pipeline import build_spec, plan_models

        config = build_config(make_parser().parse_args(["generate", "--seed", "707652", "--types", "test_wall_modules",
                                                        "--count", "5", "--set", "--out", "x",
                                                        *extra]))
        config.validate()
        found = set()
        for spec in plan_models(config, lambda m: None):
            asset = build_spec(spec)
            found |= {r for o in asset.meshes() for r in o.mesh.roles if r.startswith("M_Glow")}
        return found

    def test_paint_scheme_colours_the_slot(self):
        # 0.18.0: always M_GlowOrange, so --paint organic (cyan light) showed an orange slot
        self.assertEqual(self.glow_materials("--paint", "organic"), {"M_GlowCyan"})
        self.assertEqual(self.glow_materials("--paint", "dark"), {"M_GlowRed"})
        self.assertEqual(self.glow_materials("--glow", "red"), {"M_GlowRed"})

    def test_without_a_style_the_slot_stays_orange(self):
        self.assertEqual(self.glow_materials(), {"M_GlowOrange"})  # unchanged default (golden data)


if __name__ == "__main__":
    unittest.main()
