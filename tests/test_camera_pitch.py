"""Wall cameras watch the floor; historical geometry remains reproducible."""
import unittest
from cubegen.models import generate_asset
from cubegen.params import Style


class CameraPitchTests(unittest.TestCase):
    def lens_axis(self, asset):
        mesh = asset.get("Rotor").mesh
        caps = [mesh.face_normal(i) for part in mesh.parts for i in part.face_indices()
                if mesh.roles[i] == "M_Glass" and len(mesh.faces[i]) > 4]
        return next(n for n in caps if n[1] < 0)

    def test_box_camera_lenses_point_down_for_stationary_and_signed_sweeps(self):
        for seed in range(40):
            for speed, sweep in ((0, 0), (30, 90), (-30, 90)):
                asset = generate_asset("camera", seed, params={"style": "box", "speed": speed, "sweep": sweep})
                axis = self.lens_axis(asset)
                self.assertLess(axis[2], -.2, (seed, speed, sweep, axis))

    def test_old_generations_preserve_their_historical_pitch(self):
        for generation in (1, 2):
            asset = generate_asset("camera", 42, params={"style": "box"}, style=Style(generation=generation))
            self.assertGreater(self.lens_axis(asset)[2], .2)
