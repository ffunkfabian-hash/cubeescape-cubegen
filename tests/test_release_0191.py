"""cubegen 0.19.1: reproducible PNGs with ImageMagick 6 too (GitHub Actions' Ubuntu ignored the exclude define)."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.imagemagick import _png_output, find_imagemagick, strip_png_dates  # noqa: E402


def _png(chunks):
    """A PNG built from (type, data) chunks (CRC is not checked by the filter, a fixed one is enough here)."""
    import struct
    import zlib

    out = [b"\x89PNG\r\n\x1a\n"]
    for kind, data in chunks:
        out.append(struct.pack(">I4s", len(data), kind) + data + struct.pack(">I", zlib.crc32(kind + data)))
    return b"".join(out)


class StripPngDatesTest(unittest.TestCase):
    def test_drops_time_and_date_text_only(self):
        ihdr = (b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00")
        keep = (b"tEXt", b"comment\x00cubegen")
        chunks = [ihdr, (b"tIME", b"\x07\xea\x0a\x0d\x05\x27\x37"), (b"tEXt", b"date:create\x002026-10-13"),
                  keep, (b"zTXt", b"date:modify\x00\x00x"), (b"IDAT", b"x"), (b"IEND", b"")]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "a.png")
            with open(path, "wb") as fh:
                fh.write(_png(chunks))
            self.assertTrue(strip_png_dates(path))
            with open(path, "rb") as fh:
                self.assertEqual(fh.read(), _png([ihdr, keep, (b"IDAT", b"x"), (b"IEND", b"")]))
            self.assertFalse(strip_png_dates(path))  # nothing left to drop: the file stays as it is
            with open(path + ".txt", "w") as fh:
                fh.write("not a png")
            self.assertFalse(strip_png_dates(path + ".txt"))

    def test_output_argument_with_a_format_prefix(self):
        self.assertEqual(_png_output("PNG24:/x/a.png"), "/x/a.png")
        self.assertEqual(_png_output("png8:b.PNG"), "b.PNG")
        self.assertIsNone(_png_output("null:"))
        self.assertIsNone(_png_output("/x/a.jpg"))

    @unittest.skipUnless(find_imagemagick() is not None, "ImageMagick required")
    def test_a_png_written_without_the_define_ends_up_like_one_with_it(self):
        # what ImageMagick 6 did: write the chunks despite the define - simulated by leaving the define out
        im = find_imagemagick()
        if not os.path.basename(im.convert[0]).lower().startswith("magick"):
            self.skipTest("the comparison needs ImageMagick 7 (it honours the define)")
        with tempfile.TemporaryDirectory() as d:
            raw, clean = os.path.join(d, "raw.png"), os.path.join(d, "clean.png")
            draw = ["-size", "32x32", "xc:red", "-fill", "blue", "-draw", "circle 16,16 16,4"]
            subprocess.run(im.convert + draw + [raw], check=True)
            im.run(draw + [clean])
            self.assertTrue(strip_png_dates(raw))
            with open(raw, "rb") as a, open(clean, "rb") as b:
                self.assertEqual(a.read(), b.read())


if __name__ == "__main__":
    unittest.main()
