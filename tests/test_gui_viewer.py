import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.gui import _load_obj_preview
from cubegen.models import generate_asset
from cubegen.objwriter import write_mtl, write_obj


class ObjPreviewTests(unittest.TestCase):
    def test_reads_generated_obj_geometry_and_material_colours(self):
        with tempfile.TemporaryDirectory() as tmp:
            asset = generate_asset("crate", 42)
            obj_path = os.path.join(tmp, "Crate_000.obj")
            mtl_path = os.path.join(tmp, "CubeEscape_Materials.mtl")
            write_mtl(mtl_path)
            write_obj(asset, obj_path, os.path.basename(mtl_path))

            vertices, faces, materials = _load_obj_preview(obj_path)

        self.assertTrue(vertices)
        self.assertTrue(faces)
        self.assertIn("M_Wall", materials)
        self.assertTrue(all(0 <= index < len(vertices) for face, _ in faces for index in face))

    def test_excludes_lod1_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sample.obj")
            with open(path, "w", encoding="utf-8") as obj_file:
                obj_file.write("o Part_LOD0\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"
                               "o Part_LOD1\nv 0 0 1\nv 1 0 1\nv 0 1 1\nf 4 5 6\n")

            vertices, faces, _ = _load_obj_preview(path)

        self.assertEqual(len(vertices), 6)
        self.assertEqual(faces, [((0, 1, 2), "M_Metal")])


if __name__ == "__main__":
    unittest.main()
