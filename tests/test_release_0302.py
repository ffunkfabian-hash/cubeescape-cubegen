"""cubegen 0.30.2 "Shape Depth": voxel/facet forms keep the walkable top of the smooth model."""

import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from cubegen import shapes  # noqa: E402
from cubegen.models import generate_asset  # noqa: E402
from cubegen.params import Style  # noqa: E402

STEP = 0.05
FACET_SLACK = 0.1   # m: a hull may sit this far in from a rim (faces between kept vertices)
ROUND_TYPES = ("tank", "fan", "turbine", "pressure_tank", "vent")  # CE shape tests: round tops sank by 0.1 - 1.1 m


def top_map(asset, step=STEP):
    """Highest surface of the model above each (x, y) cell of a ``step`` grid (barycentric test per triangle)."""
    heights = {}
    for obj in asset.meshes():
        verts = obj.mesh.verts
        for face in obj.mesh.faces:
            for k in range(1, len(face) - 1):
                a, b, c = verts[face[0]], verts[face[k]], verts[face[k + 1]]
                det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
                if abs(det) < 1e-12:
                    continue
                for ix in range(math.ceil(min(a[0], b[0], c[0]) / step - 0.5), math.floor(max(a[0], b[0], c[0]) / step - 0.5) + 1):
                    px = (ix + 0.5) * step
                    for iy in range(math.ceil(min(a[1], b[1], c[1]) / step - 0.5),
                                    math.floor(max(a[1], b[1], c[1]) / step - 0.5) + 1):
                        py = (iy + 0.5) * step
                        l1 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / det
                        l2 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / det
                        l3 = 1 - l1 - l2
                        if min(l1, l2, l3) < -1e-9:
                            continue
                        z = l1 * a[2] + l2 * b[2] + l3 * c[2]
                        if heights.get((ix, iy), -math.inf) < z:
                            heights[(ix, iy)] = z
    return heights


def foot_level(heights, x, y, radius=0.2, step=0.02):
    """Height a sphere of ``radius`` rests at over (x, y) on a ``top_map`` made with ``step``."""
    best, k = -math.inf, int(radius / step)
    ix, iy = int(math.floor(x / step)), int(math.floor(y / step))
    for i in range(-k, k + 1):
        for j in range(-k, k + 1):
            z = heights.get((ix + i, iy + j))
            if z is None:
                continue
            d2 = ((i + .5 - (x / step - ix)) ** 2 + (j + .5 - (y / step - iy)) ** 2) * step * step
            if d2 <= radius * radius:
                best = max(best, z + math.sqrt(radius * radius - d2) - radius)
    return best


def sag(smooth, derived, reach, step=STEP):
    """Largest amount by which the derived top lies under the smooth top, where the derived form may be taken from
    anywhere within ``reach`` metres sideways (an inset rim of cubes moves an edge, it does not sink a surface)."""
    r = math.ceil(reach / step - 1e-9)
    worst = 0.0
    for (ix, iy), z in smooth.items():
        best = max(derived.get((ix + i, iy + j), -math.inf) for i in range(-r, r + 1) for j in range(-r, r + 1))
        worst = max(worst, z - best)
    return worst


class ShapeTopTest(unittest.TestCase):
    """The top surface (what the player stands on, what a ball bounces from) stays within one fine layer."""

    def check_type(self, model_type, seed, form, limit=None):
        smooth = generate_asset(model_type, seed)
        derived = generate_asset(model_type, seed, style=Style(shape=form))
        reach = shapes.cell_size(smooth) if form == "voxel" else FACET_SLACK
        got = sag(top_map(smooth), top_map(derived), reach)
        self.assertLessEqual(got, limit if limit is not None else shapes.TOP_STEP + 0.01, f"{form} {model_type} {seed}")
        return got

    def test_round_parts_keep_their_top_in_the_facet_form(self):
        for t in ROUND_TYPES:
            for seed in (42, 7, 1609661247, 2112677424, 1740103380):  # the last three: Cube Escape's shape tests
                self.check_type(t, seed, "facet")

    def test_round_parts_keep_their_top_in_the_voxel_form(self):
        for t in ROUND_TYPES:
            for seed in (42, 7, 963211038, 2112677424):
                # flat tops: one fine layer; the tapered turbine housing loses slope x cell on top of that
                self.check_type(t, seed, "voxel", limit=0.1)

    def test_a_sloped_top_loses_at_most_one_cell(self):
        for t in ("stairs", "ramp", "compressor", "cryo_pod"):
            smooth = generate_asset(t, 42)
            self.check_type(t, 42, "voxel", limit=shapes.cell_size(smooth))

    def test_the_cap_is_one_fine_layer_and_inside_the_part(self):
        # a cylinder 0.5 m high on a 0.2 grid: the top cell ends at 0.4, the cap adds the 0.1 that still fits
        planes = [((0.0, 0.0, 1.0), 0.5, 1.0, ""), ((0.0, 0.0, -1.0), 0.0, 1.0, ""),
                  ((1.0, 0.0, 0.0), 1.0, 1.0, ""), ((-1.0, 0.0, 0.0), 1.0, 1.0, ""),
                  ((0.0, 1.0, 0.0), 1.0, 1.0, ""), ((0.0, -1.0, 0.0), 1.0, 1.0, "")]
        caps = shapes._cap_layers({(0, 0, 0), (0, 0, 1)}, planes, 0.2, 4)  # cells reach 0.4; fine layer 0.05
        self.assertEqual(sorted(c[2] for c in caps), [8, 9])
        self.assertEqual(shapes._top_z(planes, 0.3, 0.3), 0.5)
        self.assertIsNone(shapes._top_z(planes, 1.5, 0.0))

    def test_a_foot_sphere_finds_the_same_ground_on_a_round_voxel_tank(self):
        # Cube Escape's shape test (SphereCast, radius 0.2, 7 x 7 probes): the rim of the lid must not step down
        for t, seed in (("tank", 963211038), ("tank", 42), ("tank", 7), ("pressure_tank", 42), ("turbine", 7)):
            smooth = generate_asset(t, seed)
            derived = generate_asset(t, seed, style=Style(shape="voxel"))
            lo, hi = smooth.bbox()
            sm, dm = top_map(smooth, 0.02), top_map(derived, 0.02)
            for i in range(7):
                for j in range(7):
                    x = lo[0] + (hi[0] - lo[0]) * (i + .5) / 7
                    y = lo[1] + (hi[1] - lo[1]) * (j + .5) / 7
                    ground = foot_level(sm, x, y)
                    if ground > -math.inf:
                        self.assertLessEqual(ground - foot_level(dm, x, y), 0.08, f"{t} {seed} {i},{j}")

    def test_a_flat_top_is_unchanged_by_the_voxel_form(self):
        for t in ("crate", "locker"):
            self.check_type(t, 42, "voxel", limit=0.011)


if __name__ == "__main__":
    unittest.main()
