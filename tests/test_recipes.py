"""Recipes are checked: typos and wrong values give a clear error instead of being ignored."""

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from cubegen.cli import build_config, make_parser  # noqa: E402
from cubegen.params import Style  # noqa: E402


def config_for(recipe, *extra):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(recipe, fh)
    try:
        return build_config(make_parser().parse_args(["generate", "--recipe", fh.name, *extra]))
    finally:
        os.unlink(fh.name)


class RecipeTests(unittest.TestCase):
    def test_shipped_recipes_load(self):
        folder = os.path.join(ROOT, "recipes")
        for name in sorted(os.listdir(folder)):
            config = build_config(make_parser().parse_args(["generate", "--recipe", os.path.join(folder, name)]))
            config.validate()
            self.assertTrue(config.models, name)

    def test_unknown_key_with_suggestion(self):
        with self.assertRaisesRegex(ValueError, "unknown key 'stlye' \\(did you mean 'style'\\?\\)"):
            config_for({"seed": 1, "stlye": {"glow": "red"}, "models": {"crate": 1}})
        with self.assertRaisesRegex(ValueError, "unknown key 'glwo' \\(did you mean 'glow'\\?\\)"):
            config_for({"seed": 1, "style": {"glwo": "red"}, "models": {"crate": 1}})
        with self.assertRaisesRegex(ValueError, "did you mean 'count'"):
            config_for({"seed": 1, "models": [{"type": "crate", "cuont": 2}]})

    def test_comments_are_ignored(self):
        config = config_for({"_comment": "level 3", "seed": 1, "models": {"crate": 1}})
        self.assertEqual(config.models, {"crate": 1})

    def test_variant_lists(self):
        config = config_for({"seed": 1, "models": {"door": [0, 7], "crate": 2}})
        self.assertEqual(config.models, {"door": [0, 7], "crate": 2})
        config = config_for({"seed": 1, "models": [{"type": "door", "pick": [3]}, {"type": "crate", "count": "2"}]})
        self.assertEqual(config.models, {"door": [3], "crate": 2})

    def test_bad_values(self):
        for models in ({"crate": -1}, {"crate": "many"}, {"crate": [1, "x"]}, {"crate": True}, "crate"):
            with self.assertRaises(ValueError, msg=repr(models)):
                config_for({"seed": 1, "models": models})
        with self.assertRaisesRegex(ValueError, "not valid JSON"):
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
                fh.write("{oops")
            try:
                build_config(make_parser().parse_args(["generate", "--recipe", fh.name]))
            finally:
                os.unlink(fh.name)

    def test_style_from_dict_rejects_typos(self):
        with self.assertRaisesRegex(ValueError, "did you mean 'detail'"):
            Style.from_dict({"detial": "low"})

    def test_clutter_style_in_recipe_and_cli_override(self):
        config = config_for({"seed": 42, "models": {"table": 1}, "style": {"clutter": "clean"}})
        self.assertEqual(config.style.clutter, "clean")
        config = config_for({"seed": 42, "models": {"table": 1}, "style": {"clutter": "clean"}},
                            "--clutter", "chaotic")
        self.assertEqual(config.style.clutter, "chaotic")


if __name__ == "__main__":
    unittest.main()
