"""0.13: the desktop GUI offers the texture modes of the command line."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.cli import make_parser
from cubegen.gui import TEXTURE_CHOICES, texture_args
from cubegen.palette import palette_names


class GuiTextureTests(unittest.TestCase):
    def test_no_texture_adds_no_arguments(self):
        self.assertEqual(texture_args("none", "512", "rust"), [])
        self.assertEqual(texture_args("", "", ""), [])

    def test_every_mode_the_gui_offers_is_accepted_by_the_command_line(self):
        parser = make_parser()
        for _, mode in TEXTURE_CHOICES:
            args = ["generate", "--types", "crate"] + texture_args(mode, "1024", palette_names()[-1])
            parsed = parser.parse_args(args)
            self.assertEqual(getattr(parsed, "textures", None), None if mode == "none" else mode)

    def test_palette_only_with_palette_mode(self):
        name = palette_names()[-1]
        self.assertEqual(texture_args("palette", "", name), ["--textures", "palette", "--palette", name])
        self.assertEqual(texture_args("tiled", "", name), ["--textures", "tiled"])

    def test_wrong_values_are_refused(self):
        with self.assertRaises(ValueError):
            texture_args("photo")
        with self.assertRaises(ValueError):
            texture_args("tiled", "gross")
        with self.assertRaises(ValueError):
            texture_args("palette", "", "no_such_palette")


if __name__ == "__main__":
    unittest.main()
