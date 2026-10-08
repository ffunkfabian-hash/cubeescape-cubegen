"""Compound-fragment collision and effect-anchor regressions from Unity phase five."""
import unittest
from cubegen.models import generate_asset
from cubegen.params import Style
from cubegen.models.fracture import _convex, _convex_components, fracture_asset
from cubegen.families import MeshCollision, collision_boxes
from cubegen.pipeline import rig_data
from cubegen.contract import check_sidecar


class PhaseFiveTests(unittest.TestCase):
    def test_radial_partition_preserves_volume_triangles_materials_and_dimple(self):
        from cubegen.geometry import sphere, Mesh
        from cubegen.models.fracture import _radial_parts
        from collections import Counter
        primitive = sphere(1, 8, 4, "M_Metal"); primitive.verts[9] = (.42, 0, 0)
        parts = _radial_parts(primitive)
        self.assertTrue(1 < len(parts) <= 128)
        original = Mesh(); original.add(primitive); meshes = []
        exterior = []
        for part in parts:
            self.assertTrue(part.closed and _convex(part.verts, part.faces))
            self.assertTrue(all(len(f) == 3 for f in part.faces))
            mesh = Mesh(); mesh.add(part); meshes.append(mesh)
            exterior.extend(tuple(sorted(part.verts[v] for v in f)) for f, role in zip(part.faces, part.roles) if role == "M_Metal")
        wanted = [tuple(sorted(primitive.verts[v] for v in (f[0], f[i], f[i + 1]))) for f in primitive.faces for i in range(1, len(f) - 1)]
        self.assertEqual(Counter(exterior), Counter(wanted))
        self.assertAlmostEqual(sum(m.part_volume(m.parts[0]) for m in meshes), original.part_volume(original.parts[0]), places=9)
        self.assertFalse(any(MeshCollision(m, "radial").contains((.62, 0, 0)) for m in meshes))
        self.assertTrue(any(MeshCollision(m, "radial").contains((0, 0, -.2)) for m in meshes))

    def test_radial_partition_rejects_holes_open_nonmanifold_inverted_and_large_meshes(self):
        from cubegen.geometry import sphere, torus
        from cubegen.models.fracture import _radial_parts
        closed = sphere(1, 8, 4, "M_Metal")
        opened = sphere(1, 8, 4, "M_Metal"); opened.closed = False
        inverted = sphere(1, 8, 4, "M_Metal"); inverted.faces = [tuple(reversed(f)) for f in inverted.faces]
        nonmanifold = sphere(1, 8, 4, "M_Metal"); nonmanifold.faces.pop()
        hole = torus(.8, .15, 8, 6, "M_Metal")
        large = sphere(1, 16, 8, "M_Metal")
        for prim in (opened, inverted, nonmanifold, hole, large): self.assertIsNone(_radial_parts(prim))
        self.assertEqual(len(_radial_parts(closed)), 1)

    def test_radial_partition_transforms_and_historical_generations(self):
        from cubegen.geometry import sphere
        from cubegen.asset import Asset
        for generation in (1, 2, 3):
            asset = Asset("RadialProof"); primitive = sphere(1, 8, 4, "M_Metal"); primitive.verts[9] = (.42, 0, 0)
            asset.part("Body").add(primitive, loc=(1, 2, 3), rot=(.4, .7, 1.2), scale=(1.3, .8, 1.1))
            asset.normalize("floor"); asset.scale(.75)
            fracture_asset(asset, 42, "floor", pieces=1, generation=generation)
            self.assertEqual(asset.meta["fragments"], 1)
            if generation == 3:
                self.assertTrue(all(c.convex for c in asset.colliders)); self.assertGreater(len(asset.colliders), 1)
            else: self.assertEqual(len(asset.meshes()), 1)

    def test_radial_model_seeds_kernel_edge_cases_and_historical_states(self):
        from unittest.mock import patch
        from cubegen.seeds import model_seed
        for kind in ("rock", "rubble_pile", "scrap_heap", "hanging_crystals", "asteroid", "cocoon", "crashed_pod", "floating_island", "stalagmite"):
            for seed in (0, 1, 42, model_seed(42, kind, 0)):
                for generation in (1, 2, 3):
                    with self.subTest(kind=kind, seed=seed, generation=generation):
                        style = Style(generation=generation, damage="fractured")
                        with patch("cubegen.models.fracture._radial_parts", return_value=None): old = generate_asset(kind, seed, style=style)
                        current = generate_asset(kind, seed, style=style)
                        if generation < 3: self.assertEqual(current.digest(), old.digest())
                        else:
                            self.assertTrue(all(c.convex for c in current.colliders))
                            self.assertLessEqual(len(current.colliders), 256)
                            self.assertEqual(current.digest(), generate_asset(kind, seed, style=style).digest())
                            self.assertLessEqual(current.meta["fragments"], old.meta["fragments"])
            for state in ("intact", "damaged", "destroyed"):
                style = Style(generation=3, damage=state)
                with patch("cubegen.models.fracture._radial_parts", return_value=None): old = generate_asset(kind, 42, style=style)
                self.assertEqual(generate_asset(kind, 42, style=style).digest(), old.digest())

    def test_warped_box_partition_preserves_fan_volume_boundary_roles_and_dent(self):
        from cubegen.geometry import box, Mesh
        from cubegen.models.fracture import _deformed_box_parts
        primitive = box(2, 1, 1, "M_Metal", top_role="M_Warning", bottom_role="M_Wall")
        for i in (4, 6):
            x, y, z = primitive.verts[i]; primitive.verts[i] = (x, y, z - .45)
        parts = _deformed_box_parts(primitive)
        self.assertTrue(1 < len(parts) <= 12)
        old = Mesh(); old.add(primitive); meshes = []
        output = []
        for part in parts:
            self.assertTrue(part.closed and _convex(part.verts, part.faces))
            self.assertTrue(all(len(face) == 3 for face in part.faces))
            mesh = Mesh(); mesh.add(part); meshes.append(mesh)
            output.extend((tuple(sorted(part.verts[v] for v in face)), role) for face, role in zip(part.faces, part.roles))
        self.assertAlmostEqual(sum(m.part_volume(m.parts[0]) for m in meshes), old.part_volume(old.parts[0]), places=10)
        boundary = [(tuple(sorted(primitive.verts[v] for v in (face[0], face[i], face[i + 1]))), role)
                    for face, role in zip(primitive.faces, primitive.roles) for i in (1, 2)]
        from collections import Counter
        counts = Counter(output)
        for face in boundary: self.assertEqual(counts[face], 1, "Every original boundary triangle and material must survive once.")
        self.assertTrue(all(count == 2 for face, count in counts.items() if face not in boundary), "Internal faces must cancel in pairs.")
        shapes = [MeshCollision(m, "box") for m in meshes]
        self.assertFalse(any(s.contains((0, 0, .35)) for s in shapes), "A hull must not refill the jagged top.")
        self.assertTrue(any(s.contains((0, 0, -.2)) for s in shapes))

    def test_warped_box_convex_fan_keeps_one_shape_and_original_planar_boxes(self):
        from cubegen.geometry import box
        from cubegen.models.fracture import _deformed_box_parts
        primitive = box(2, 1, 1, "M_Metal")
        for i in (5, 7):
            x, y, z = primitive.verts[i]; primitive.verts[i] = (x, y, z - .45)
        self.assertTrue(_convex(primitive.verts, primitive.faces), "The former averaged-normal test accepts a warped quad.")
        parts = _convex_components(primitive)
        self.assertEqual(len(parts), 1)
        self.assertEqual(len(parts[0].faces), 12)
        self.assertEqual(parts[0].verts, primitive.verts)
        original = box(2, 1, 1, "M_Metal", top_scale=(.6, .8), top_offset=(.1, .2))
        self.assertIsNone(_deformed_box_parts(original))
        self.assertEqual(_convex_components(original), [original])

    def test_warped_box_partition_rejects_open_inverted_degenerate_and_other_topologies(self):
        import math
        from cubegen.geometry import box, prism
        from cubegen.models.fracture import _deformed_box_parts
        primitives = [box(2, 1, 1, "M_Metal") for _ in range(4)]
        primitives[0].closed = False
        primitives[1].verts = [(-x, y, z) for x, y, z in primitives[1].verts]
        primitives[2].verts[6] = primitives[2].verts[0]
        primitives[3].verts[4] = (math.nan, 0, 0)
        primitives.append(prism([(0, 0), (1, 0), (1, 1), (0, 1)], .2, "M_Metal"))
        for primitive in primitives: self.assertIsNone(_deformed_box_parts(primitive))

    def test_warped_box_transforms_and_generations_keep_compound_body(self):
        from cubegen.geometry import box
        from cubegen.asset import Asset
        for generation in (1, 2, 3):
            asset = Asset("WarpedBoxProof"); mesh = asset.part("Body")
            primitive = box(2, 1, 1, "M_Metal")
            for i in (4, 6):
                x, y, z = primitive.verts[i]; primitive.verts[i] = (x, y, z - .45)
            mesh.add(primitive, loc=(1, 2, 3), rot=(.4, .7, 1.2), scale=(1.3, .8, 1.1))
            asset.normalize("floor"); asset.scale(.75)
            fracture_asset(asset, 42, "floor", pieces=1, generation=generation)
            self.assertEqual(asset.meta["fragments"], 1)
            if generation == 3:
                self.assertTrue(1 < len(asset.colliders) <= 12)
                self.assertTrue(all(c.convex for c in asset.colliders))
                self.assertTrue(all(o.parent == "Fragment_01" for o in asset.meshes()))
            else: self.assertEqual(len(asset.meshes()), 1)

    def test_warped_box_model_seeds_forms_historical_states_and_wall_opening(self):
        from unittest.mock import patch
        from cubegen.seeds import model_seed
        for kind in ("broken_wall", "burnt_console", "fallen_pillar"):
            for seed in (0, 1, 42, model_seed(42, kind, 0)):
                for generation in (1, 2, 3):
                    with self.subTest(kind=kind, seed=seed, generation=generation):
                        style = Style(generation=generation, damage="fractured")
                        with patch("cubegen.models.fracture._box_topology", return_value=False): old = generate_asset(kind, seed, style=style)
                        current = generate_asset(kind, seed, style=style)
                        if generation < 3: self.assertEqual(current.digest(), old.digest())
                        else:
                            self.assertLessEqual(current.meta["fragments"], old.meta["fragments"])
                            self.assertTrue(all(c.convex for c in current.colliders))
                            self.assertLessEqual(len(current.colliders), 256)
                            self.assertEqual(current.digest(), generate_asset(kind, seed, style=style).digest())
            for state in ("intact", "damaged", "destroyed"):
                style = Style(generation=3, damage=state)
                with patch("cubegen.models.fracture._box_topology", return_value=False): old = generate_asset(kind, 42, style=style)
                self.assertEqual(generate_asset(kind, 42, style=style).digest(), old.digest())
        cases = (("broken_wall", {"length": length, "remaining": remaining, "hole": hole}) for length in (2, 4) for remaining in (.1, 1) for hole in (False, True))
        cases = list(cases) + [("burnt_console", {"width": w, "screens": n}) for w in (.6, 3) for n in (1, 3)] + [("fallen_pillar", {"width": w, "segments": n, "stump": stump}) for w in (.2, 2) for n in (1, 5) for stump in (False, True)]
        for kind, params in cases:
            asset = generate_asset(kind, 42, params=params, style=Style(generation=3, damage="fractured"))
            self.assertTrue(all(c.convex for c in asset.colliders), (kind, params))
            self.assertLessEqual(len(asset.colliders), 256)
        for seed in (0, 1, 2):
            params = {"hole": True, "remaining": .8}
            intact = generate_asset("broken_wall", seed, params=params, style=Style(generation=3))
            wall = intact.get("Wall").mesh
            slab = next(p for p in wall.parts if abs(wall.part_bbox(p)[1][2] - wall.part_bbox(p)[0][2] - .4) < .01
                        and abs(wall.part_bbox(p)[1][1] - wall.part_bbox(p)[0][1] - .5) < .01)
            lo, hi = wall.part_bbox(slab)
            opening = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2] + .9)
            current = generate_asset("broken_wall", seed, params=params, style=Style(generation=3, damage="fractured"))
            self.assertFalse(any(MeshCollision(o.mesh, o.name).contains(opening) for o in current.meshes()))

    def test_wide_short_pillar_stump_never_inverts_in_current_generation(self):
        params = {"width": 2, "segments": 1, "stump": True}
        old = generate_asset("fallen_pillar", 42, params=params, style=Style(generation=1)).get("Pillar").mesh
        new = generate_asset("fallen_pillar", 42, params=params, style=Style(generation=3)).get("Pillar").mesh
        old_part, new_part = old.parts[1], new.parts[1]
        self.assertLess(min(old.verts[old_part.v0 + i][2] for i in (4, 5, 6, 7)), old.verts[old_part.v0][2])
        self.assertGreater(min(new.verts[new_part.v0 + i][2] for i in (4, 5, 6, 7)), max(new.verts[new_part.v0 + i][2] for i in range(4)))

    def test_axial_frusta_keep_volume_boundary_materials_and_neck_clearance(self):
        from cubegen.geometry import lathe, Mesh
        primitive = lathe([(0, 0), (.3, 0), (.6, .2), (.3, .4), (.3, .7), (0, .7)], 8,
                          ["M_Warning", "M_Metal", "M_Wall", "M_RobotDark", "M_Crystal"])
        parts = _convex_components(primitive)
        self.assertEqual(len(parts), 3)
        old = Mesh(); old.add(primitive)
        meshes = []
        for piece in parts:
            self.assertTrue(piece.closed and _convex(piece.verts, piece.faces))
            mesh = Mesh(); mesh.add(piece); meshes.append(mesh)
        self.assertAlmostEqual(sum(m.part_volume(m.parts[0]) for m in meshes), old.part_volume(old.parts[0]), places=9)
        # Existing non-cap boundary faces retain their material roles exactly.
        boundary = {(tuple(sorted(primitive.verts[v] for v in f)), r) for f, r in zip(primitive.faces, primitive.roles) if len({primitive.verts[v][2] for v in f}) > 1}
        output = {(tuple(sorted(p.verts[v] for v in f)), r) for p in parts for f, r in zip(p.faces, p.roles)}
        self.assertTrue(boundary <= output)
        self.assertTrue(any(r == "M_Warning" for p in parts for r in p.roles))
        self.assertTrue(any(r == "M_Crystal" for p in parts for r in p.roles))
        shapes = [MeshCollision(m, "frustum") for m in meshes]
        self.assertFalse(any(s.contains((.45, 0, .55)) for s in shapes))
        self.assertTrue(any(s.contains((0, 0, .55)) for s in shapes))

    def test_radial_dish_keeps_original_shell_volume_and_open_bowl(self):
        from cubegen.geometry import lathe, Mesh
        profile = [(0, -.08), (.35, -.05), (1, .22), (.94, .24), (.3, .02), (0, 0)]
        primitive = lathe(profile, 12, ["M_Metal", "M_Platform", "M_RobotDark", "M_Wall", "M_Warning"])
        parts = _convex_components(primitive)
        self.assertEqual(len(parts), 24)
        old = Mesh(); old.add(primitive)
        meshes = []
        for piece in parts:
            self.assertTrue(piece.closed and _convex(piece.verts, piece.faces))
            self.assertTrue(set(piece.verts) <= set(primitive.verts))
            mesh = Mesh(); mesh.add(piece); meshes.append(mesh)
        self.assertAlmostEqual(sum(m.part_volume(m.parts[0]) for m in meshes), old.part_volume(old.parts[0]), places=9)
        boundary = {(tuple(sorted(primitive.verts[v] for v in f)), r) for f, r in zip(primitive.faces, primitive.roles)}
        output = {(tuple(sorted(p.verts[v] for v in f)), r) for p in parts for f, r in zip(p.faces, p.roles)}
        self.assertTrue(boundary <= output)
        shapes = [MeshCollision(m, "dish") for m in meshes]
        self.assertFalse(any(s.contains((0, 0, .1)) for s in shapes))
        self.assertTrue(any(s.contains((.7, 0, .12)) for s in shapes))

    def test_lathe_recipes_reject_warped_open_invalid_and_unbounded_profiles(self):
        from cubegen.geometry import lathe, cylinder
        primitive = lathe([(.3, 0), (.6, .2), (.3, .4)], 8, "M_Metal")
        primitive.verts[9] = tuple(v + .07 for v in primitive.verts[9])
        from cubegen.models.fracture import _convex_recipe_parts
        self.assertIsNone(_convex_recipe_parts(primitive), "Warped procedural recipe must still be rejected.")
        # 0.11 can instead prove a separate exact triangle partition of the whole solid.
        parts = _convex_components(primitive)
        self.assertTrue(all(p.closed and _convex(p.verts, p.faces) and all(len(f) == 3 for f in p.faces) for p in parts))
        self.assertIsNone(lathe([(.3, 0), (.6, .2), (.3, .4)], 8, "M_Metal", cap_top=False).convex_faces)
        self.assertIsNone(lathe([(.3, k * .01) for k in range(129)], 8, "M_Metal").convex_faces)
        self.assertIsNone(lathe([(0, 0), (1, 1), (1, 0), (0, 1)], 8, "M_Metal").convex_faces)
        convex = cylinder(.3, .4, 8, "M_Metal", bevel=.03)
        self.assertEqual(_convex_components(convex), [convex], "Existing convex bodies must not grow extra shapes.")

    def test_lathe_model_seeds_forms_transforms_budgets_and_historical_output(self):
        from unittest.mock import patch
        from cubegen.seeds import model_seed
        from cubegen.asset import Asset
        from cubegen.geometry import lathe
        for kind in ("antenna", "crystal_cluster", "transformer"):
            for seed in (0, 1, 42, model_seed(42, kind, 0)):
                for generation in (1, 2, 3):
                    with self.subTest(kind=kind, seed=seed, generation=generation):
                        style = Style(generation=generation, damage="fractured")
                        with patch("cubegen.geometry._lathe_convex_faces", return_value=None): old = generate_asset(kind, seed, style=style)
                        current = generate_asset(kind, seed, style=style)
                        self.assertEqual(current.meta["fragments"], old.meta["fragments"])
                        if generation < 3: self.assertEqual(current.digest(), old.digest())
                        else:
                            self.assertTrue(all(c.convex for c in current.colliders))
                            self.assertLessEqual(len(current.colliders), 256)
                            self.assertEqual(current.digest(), generate_asset(kind, seed, style=style).digest())
            for state in ("intact", "damaged", "destroyed"):
                style = Style(generation=3, damage=state)
                with patch("cubegen.geometry._lathe_convex_faces", return_value=None): old = generate_asset(kind, 42, style=style)
                self.assertEqual(generate_asset(kind, 42, style=style).digest(), old.digest())
        for form in ("mast", "radar", "dish"):
            for height in (.8, 6):
                asset = generate_asset("antenna", 42, params={"style": form, "height": height}, style=Style(generation=3, damage="fractured"))
                self.assertTrue(all(c.convex for c in asset.colliders))
                self.assertLessEqual(len(asset.colliders), 256)
        asset = Asset("LatheTransform"); mesh = asset.part("Body")
        mesh.add(lathe([(.3, 0), (.6, .2), (.3, .4)], 8, "M_Metal"), loc=(1, 2, 3), rot=(.4, .7, 1.2), scale=(1.3, .8, 1.1))
        asset.normalize("floor"); asset.scale(.75)
        fracture_asset(asset, 42, "floor", pieces=1, generation=3)
        self.assertEqual(asset.meta["fragments"], 1)
        self.assertTrue(all(c.convex for c in asset.colliders))

    def test_concave_extrusions_preserve_volume_caps_materials_and_free_notches(self):
        from cubegen.geometry import prism, Mesh
        polygon = [(0, 0), (3, 0), (3, 1), (1, 1), (1, 3), (0, 3)]
        for points in (polygon, list(reversed(polygon))):
            original = prism(points, .4, "M_Metal", cap_role="M_Warning")
            parts = _convex_components(original)
            self.assertEqual(len(parts), 2, "Adjacent ears should merge into two convex profile regions.")
            meshes = []
            for part in parts:
                self.assertTrue(part.closed and _convex(part.verts, part.faces))
                mesh = Mesh(); mesh.add(part); meshes.append(mesh)
                for face, role in zip(part.faces, part.roles):
                    self.assertEqual(role, "M_Warning" if len({part.verts[v][2] for v in face}) == 1 else "M_Metal")
            self.assertAlmostEqual(sum(m.part_volume(m.parts[0]) for m in meshes), 2, places=9)
            shapes = [MeshCollision(m, "profile") for m in meshes]
            self.assertFalse(any(s.contains((2, 2, 0)) for s in shapes))
            for point in ((.5, 2, 0), (2, .5, 0)):
                self.assertTrue(any(s.contains(point) for s in shapes))
            # Every original perimeter face remains as a real boundary face.
            original_edges = {tuple(sorted(original.verts[v] for v in face)) for face in original.faces[2:]}
            after_edges = {tuple(sorted(p.verts[v] for v in face)) for p in parts for face in p.faces if len({p.verts[v][2] for v in face}) > 1}
            self.assertTrue(original_edges <= after_edges)

    def test_invalid_polygon_profiles_do_not_get_a_dynamic_recipe(self):
        import math
        from cubegen.geometry import prism
        polygons = ([(0, 0), (2, 2), (0, 2), (2, 0)],
                    [(0, 0), (2, 0), (1, 0), (1, 1), (0, 1)],
                    [(0, 0), (1, 0), (1, 0), (0, 1)],
                    [(math.cos(i * 2 * math.pi / 129), math.sin(i * 2 * math.pi / 129)) for i in range(129)])
        for polygon in polygons:
            primitive = prism(polygon, .2, "M_Metal")
            self.assertIsNone(primitive.convex_faces)
            self.assertEqual(_convex_components(primitive), [primitive])
        self.assertIsNone(prism([(0, 0), (1, 0), (1, 1), (0, 1)], .2, "M_Metal").convex_faces)

    def test_extrusion_recipes_survive_affine_transforms_without_adding_bodies(self):
        import math
        from cubegen.asset import Asset
        from cubegen.geometry import prism
        primitive = prism([(0, 0), (3, 0), (3, 1), (1, 1), (1, 3), (0, 3)], .4, "M_Metal")
        for generation in (1, 2, 3):
            asset = Asset("ExtrusionProof"); mesh = asset.part("Body")
            mesh.add(primitive, loc=(1, 2, 3), rot=(math.pi / 2, .2, .4), scale=(1.3, .8, 1.1))
            asset.normalize("center"); asset.scale(.75)
            fracture_asset(asset, 42, "center", pieces=1, generation=generation)
            self.assertEqual(asset.meta["fragments"], 1)
            self.assertEqual(len(asset.meshes()), 2 if generation == 3 else 1)
            if generation == 3: self.assertTrue(all(c.convex for c in asset.colliders))
        primitive.verts[3] = (4, 4, .1)
        self.assertEqual(_convex_components(primitive), [primitive], "A deformed recipe must stay exact and fixed.")

    def test_concave_model_seeds_arch_forms_and_shape_budgets(self):
        from unittest.mock import patch
        from cubegen.seeds import model_seed
        for kind in ("archway", "girders", "symbol_plate", "fungus_carpet", "puddle"):
            for seed in (0, 1, 42, model_seed(42, kind, 0)):
                with self.subTest(kind=kind, seed=seed):
                    style = Style(generation=3, damage="fractured")
                    with patch("cubegen.geometry._convex_polygon_parts", return_value=None):
                        old = generate_asset(kind, seed, style=style)
                    current = generate_asset(kind, seed, style=style)
                    self.assertEqual(current.meta["fragments"], old.meta["fragments"])
                    self.assertTrue(all(c.convex for c in current.colliders))
                    self.assertLessEqual(len(current.colliders), 256)
                    self.assertEqual(current.digest(), generate_asset(kind, seed, style=style).digest())
        for shape in ("round", "pointed", "chamfer", "flat"):
            for width, height in ((1.2, 3), (2.4, 6)):
                asset = generate_asset("archway", 42, params={"shape": shape, "width": width, "height": height},
                                       style=Style(generation=3, damage="fractured"))
                self.assertTrue(all(c.convex for c in asset.colliders))
                opening_height = asset.meta["opening_m"][1]
                shapes = [MeshCollision(o.mesh, o.name) for o in asset.meshes()]
                self.assertFalse(any(s.contains((0, 0, opening_height * .3)) for s in shapes))


    def test_merged_structural_profiles_recover_exact_closed_convex_parts(self):
        from cubegen.geometry import u_channel, angle_profile, tee_profile, i_beam, Mesh
        for primitive, count in ((u_channel(2, 1, .4, .1), 3),
                                 (angle_profile(2, 1, .4, .1), 2),
                                 (tee_profile(2, 1, .4, .1), 2),
                                 (i_beam(2, 1, .4, .1, .1), 3)):
            pieces = _convex_components(primitive)
            self.assertEqual(len(pieces), count)
            original = Mesh(); part = original.add(primitive)
            split = Mesh()
            for piece in pieces:
                self.assertTrue(piece.closed and _convex(piece.verts, piece.faces))
                split.add(piece)
            self.assertEqual(split.verts, original.verts)
            self.assertEqual(split.faces, original.faces)
            self.assertEqual(split.roles, original.roles)
            self.assertAlmostEqual(sum(split.part_volume(p) for p in split.parts), original.part_volume(part), places=10)

    def test_u_profile_has_three_shapes_on_one_body_and_preserves_its_opening_after_rotation(self):
        import math
        from cubegen.asset import Asset
        from cubegen.geometry import u_channel
        for generation in (1, 2, 3):
            asset = Asset("Profile")
            asset.part("Body").add(u_channel(2, 1, .4, .1), rot=(math.pi / 2, 0, .4), loc=(1, 2, 3))
            fracture_asset(asset, 42, "center", pieces=1, generation=generation)
            if generation < 3:
                self.assertEqual(len(asset.meshes()), 1)
                continue
            self.assertEqual(asset.meta["fragments"], 1)
            self.assertEqual(len(asset.meshes()), 3)
            self.assertTrue(all(c.convex for c in asset.colliders))
            self.assertTrue(all(o.parent == "Fragment_01" for o in asset.meshes()))
            shapes = [MeshCollision(o.mesh, o.name) for o in asset.meshes()]
            self.assertFalse(any(s.contains((1, 2, 3)) for s in shapes))
            self.assertTrue(any(s.contains((1, 2, 2.55)) for s in shapes))

    def test_open_and_genuinely_concave_shapes_are_never_silently_hulled(self):
        from cubegen.geometry import pipe_section, torus, _merge_prims, box, Prim
        pipe = pipe_section(.2, 1, .04); pipe.convex_faces = None
        unknown_ring = torus(.4, .08, 10, 4, "M_Metal"); unknown_ring.convex_faces = None
        for primitive in (pipe, unknown_ring,
                          _merge_prims(box(1, 1, 1, "M_Metal"), torus(.4, .08, 10, 4, "M_Metal"))):
            self.assertEqual(_convex_components(primitive), [primitive])
        cube = box(1, 1, 1, "M_Metal")
        broken = Prim(cube.verts, cube.faces[:-1], cube.roles[:-1], closed=True)
        malformed = _merge_prims(cube, broken)
        self.assertEqual(_convex_components(malformed), [malformed])

    def test_profile_models_are_deterministic_and_do_not_add_fragment_bodies(self):
        from unittest.mock import patch
        for kind in ("test_scanner_pad", "test_warning_beacon", "test_pipe_rack", "test_utility_trench"):
            for seed in (0, 42, 1019132231):
                style = Style(generation=3, damage="fractured")
                with patch("cubegen.models.fracture._convex_components", side_effect=lambda p: [p]):
                    before = generate_asset(kind, seed, style=style)
                after = generate_asset(kind, seed, style=style)
                self.assertEqual(after.meta["fragments"], before.meta["fragments"])
                self.assertEqual(after.digest(), generate_asset(kind, seed, style=style).digest())
                self.assertLessEqual(len(after.colliders), 256)
                self.assertTrue(all(c.convex for c in after.colliders))

    def test_round_wall_recipes_preserve_external_faces_and_real_volume(self):
        import math
        from collections import Counter
        from cubegen.geometry import pipe_section, ring, torus, Mesh
        for sides in (6, 8, 10, 16):
            samples = ((pipe_section(.4, 1.2, .08, sides),
                        sides * .5 * math.sin(2 * math.pi / sides) * (.4 ** 2 - .32 ** 2) * 1.2),
                       (ring(.32, .4, .12, sides, "M_Metal"),
                        sides * .5 * math.sin(2 * math.pi / sides) * (.4 ** 2 - .32 ** 2) * .12),
                       (torus(.4, .08, sides, 6, "M_Metal"), None))
            for primitive, expected in samples:
                pieces = _convex_components(primitive)
                self.assertEqual(len(pieces), sides)
                self.assertTrue(all(p.closed and _convex(p.verts, p.faces) for p in pieces))
                def surfaces(p):
                    return Counter((tuple(sorted(p.verts[i] for i in face)), role) for face, role in zip(p.faces, p.roles))
                new = Counter()
                volume = 0
                for p in pieces:
                    new.update(surfaces(p)); mesh = Mesh(); volume += mesh.part_volume(mesh.add(p))
                self.assertFalse(surfaces(primitive) - new, "Original surfaces and material roles must remain.")
                if expected is None:
                    mesh = Mesh(); expected = mesh.part_volume(mesh.add(primitive))
                self.assertAlmostEqual(volume, expected, places=9)
                shapes = []
                for p in pieces:
                    mesh = Mesh(); mesh.add(p); shapes.append(MeshCollision(mesh, "sector"))
                for z in (-.03, 0, .03):
                    self.assertFalse(any(s.contains((0, 0, z)) for s in shapes), "Central opening remains empty.")
                self.assertTrue(any(s.contains((.36, 0, 0)) for s in shapes), "Wall remains solid.")

    def test_round_recipes_survive_transform_and_stay_on_one_fragment_body(self):
        import math
        from cubegen.asset import Asset
        from cubegen.geometry import pipe_section, torus, transform_points
        for primitive in (pipe_section(.4, 1.2, .08, 8), torus(.4, .08, 10, 6, "M_Metal")):
            for generation in (1, 2, 3):
                asset = Asset("RoundProof"); mesh = asset.part("Body")
                mesh.add(primitive, loc=(1, 2, 3), rot=(math.pi / 2, .2, .4), scale=(1.3, .8, 1.1))
                asset.normalize("center"); asset.scale(.75)
                fracture_asset(asset, 42, "center", pieces=1, generation=generation)
                self.assertEqual(asset.meta["fragments"], 1)
                if generation < 3:
                    self.assertEqual(len(asset.meshes()), 1)
                else:
                    self.assertEqual(len(asset.meshes()), len(primitive.convex_faces))
                    self.assertTrue(all(c.convex for c in asset.colliders))

    def test_invalid_or_deformed_round_recipes_keep_exact_fixed_collision(self):
        from cubegen.geometry import torus, pipe_section
        for p in (torus(.08, .4, 10, 6, "M_Metal"), pipe_section(.4, 1, 0, 8)):
            self.assertEqual(_convex_components(p), [p])
        p = torus(.4, .08, 10, 6, "M_Metal")
        p.verts[0] = (0, 0, 1)
        self.assertEqual(_convex_components(p), [p])

    def test_compound_fragments_preserve_volume_geometry_and_convexity_per_shape(self):
        for kind in ("crate", "cage", "pipe", "wall", "safe", "machine", "tank", "cryo_pod"):
            for seed in (0, 1, 42):
                with self.subTest(kind=kind, seed=seed):
                    asset = generate_asset(kind, seed, style=Style(generation=3, damage="fractured"))
                    groups = [o for o in asset.objects if o.name.startswith("Fragment_")]
                    self.assertEqual(len(groups), asset.meta["fragments"])
                    self.assertTrue(all(o.is_empty for o in groups))
                    self.assertTrue(all(o.pivot == tuple(round(v, 4) for v in o.pivot) for o in groups))
                    group_names = {o.name for o in groups}
                    self.assertEqual({c.part for c in asset.colliders}, {o.name for o in asset.meshes()})
                    for obj, shape in zip(asset.meshes(), asset.colliders):
                        self.assertIn(obj.parent, group_names)
                        self.assertEqual(len(obj.mesh.parts), 1)
                        self.assertEqual(shape.convex, obj.mesh.parts[0].closed and _convex(obj.mesh.verts, obj.mesh.faces))
                    old = generate_asset(kind, seed, style=Style(generation=2, damage="fractured"))
                    volume = lambda a: sum(o.mesh.part_volume(p) for o in a.meshes() for p in o.mesh.parts)
                    self.assertAlmostEqual(volume(asset), volume(old), delta=volume(old) * .01 + 1e-4)
                    self.assertEqual(asset.digest(), generate_asset(kind, seed, style=Style(generation=3, damage="fractured")).digest())
                    data = rig_data(asset, {"type": kind, "name": asset.name, "seed": seed, "style": {"generation": 3, "damage": "fractured"}}, 42)
                    self.assertFalse(check_sidecar(data)[0])

    def test_fractured_cage_gaps_remain_empty_in_real_shapes(self):
        asset = generate_asset("cage", 42, style=Style(generation=3, damage="fractured"))
        exact = [MeshCollision(o.mesh, o.name) for o in asset.meshes()]
        shapes = collision_boxes(asset, "cage")
        lo, hi = asset.bbox(); points = []
        for x in range(1, 9):
            for y in range(1, 9):
                p = (lo[0]+(hi[0]-lo[0])*x/9, lo[1]+(hi[1]-lo[1])*y/9, (lo[2]+hi[2])/2)
                if not any(s.contains(p) for s in exact): points.append(p)
        self.assertTrue(points)
        self.assertTrue(all(not any(s.contains(p) for s in shapes) for p in points))

    def test_fractured_draw_calls_do_not_assume_static_batching(self):
        from cubegen.quality import draw_calls
        asset = generate_asset("cage", 42, style=Style(generation=3, damage="fractured"))
        self.assertEqual(draw_calls(asset), sum(len(set(o.mesh.roles)) for o in asset.meshes()))
        self.assertGreater(draw_calls(asset), len({r for o in asset.meshes() for r in o.mesh.roles}))
        from cubegen.palette import draw_calls as palette_calls, material_map
        palette = material_map(asset)
        self.assertEqual(palette_calls(asset), sum(len({palette(o.name, r) for r in o.mesh.roles}) for o in asset.meshes()))

    def test_old_generations_keep_their_original_single_hulls(self):
        for generation in (1, 2):
            asset = generate_asset("cage", 42, style=Style(generation=generation, damage="fractured"))
            self.assertEqual(len(asset.meshes()), asset.meta["fragments"])
            self.assertTrue(all(o.name.startswith("Fragment_") for o in asset.objects))
            self.assertTrue(all(c.convex for c in asset.colliders))

    def test_steam_anchor_exists_for_both_forms_only_in_current_generation(self):
        for form in ("grate", "pipe"):
            for damage in ("intact", "damaged"):
                for seed in (0, 42):
                    asset = generate_asset("steam_vent", seed, params={"style": form}, style=Style(generation=3, damage=damage))
                    anchor = asset.get("FX_Steam")
                    self.assertIsNotNone(anchor)
                    self.assertTrue(anchor.is_empty)
                    self.assertEqual(anchor.parent, "Body")
                    self.assertEqual(anchor.pivot, asset.get("Audio_Hiss").pivot)
            for generation in (1, 2):
                self.assertIsNone(generate_asset("steam_vent", 42, params={"style": form}, style=Style(generation=generation)).get("FX_Steam"))


class FragmentExportTests(unittest.TestCase):
    def test_radial_real_fbx_preserves_explicit_triangles_and_single_compound_body(self):
        import json, os, subprocess, tempfile
        from cubegen.blender import find_blender
        from cubegen.contract import check_export
        blender = find_blender()
        if not blender: self.skipTest("Blender not installed")
        script = os.path.join(os.path.dirname(__file__), "blender", "round_export.py")
        with tempfile.TemporaryDirectory() as out:
            run = subprocess.run([blender, "-b", "--factory-startup", "--python-exit-code", "3", "--python", script,
                                  "--", "--out", out, "--family", "radial"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout)
            self.assertEqual(run.stdout.count("explicit FBX triangle geometry checked"), 3)
            self.assertTrue(all(not row["errors"] and not row["open"] for row in check_export(out + "/models").values()))
            for kind in ("Boulder", "Shell", "Island"):
                with open(out + "/models/Gen_RadialFixture_" + kind + ".cubegen.json") as stream: data = json.load(stream)
                self.assertTrue(1 < len(data["colliders"]) <= 128)
                self.assertTrue(all(c["convex"] for c in data["colliders"]))
                self.assertEqual(sum(p["empty"] for p in data["parts"]), 1)

    def test_warped_box_real_fbx_retains_explicit_triangle_geometry(self):
        import json, os, subprocess, tempfile
        from cubegen.blender import find_blender
        from cubegen.contract import check_export
        blender = find_blender()
        if not blender: self.skipTest("Blender not installed")
        script = os.path.join(os.path.dirname(__file__), "blender", "round_export.py")
        with tempfile.TemporaryDirectory() as out:
            run = subprocess.run([blender, "-b", "--factory-startup", "--python-exit-code", "3", "--python", script,
                                  "--", "--out", out, "--family", "box"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout)
            self.assertEqual(run.stdout.count("explicit FBX triangle geometry checked"), 3)
            self.assertTrue(all(not row["errors"] and not row["open"] for row in check_export(out + "/models").values()))
            for kind in ("Wall", "Console", "Pillar"):
                with open(out + "/models/Gen_BoxFixture_" + kind + ".cubegen.json") as stream: data = json.load(stream)
                self.assertTrue(1 < len(data["colliders"]) <= 12)
                self.assertTrue(all(c["convex"] for c in data["colliders"]))
                self.assertEqual(sum(p["empty"] for p in data["parts"]), 1)

    def test_lathe_real_fbx_contracts_keep_one_body_and_exact_profile_shapes(self):
        import json, os, subprocess, tempfile
        from cubegen.blender import find_blender
        from cubegen.contract import check_export
        blender = find_blender()
        if not blender: self.skipTest("Blender not installed")
        script = os.path.join(os.path.dirname(__file__), "blender", "round_export.py")
        with tempfile.TemporaryDirectory() as out:
            run = subprocess.run([blender, "-b", "--factory-startup", "--python-exit-code", "3", "--python", script,
                                  "--", "--out", out, "--family", "lathe"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout)
            self.assertTrue(all(not row["errors"] and not row["open"] for row in check_export(out + "/models").values()))
            for kind, count in (("Dish", 24), ("Insulator", 6), ("Socket", 5)):
                with open(out + "/models/Gen_LatheFixture_" + kind + ".cubegen.json") as stream: data = json.load(stream)
                self.assertEqual(len(data["colliders"]), count)
                self.assertTrue(all(c["convex"] for c in data["colliders"]))
                self.assertEqual(sum(p["empty"] for p in data["parts"]), 1)

    def test_concave_profile_real_fbx_contracts_have_three_reused_convex_shapes(self):
        import json
        import os
        import subprocess
        import tempfile
        from cubegen.blender import find_blender
        from cubegen.contract import check_export
        blender = find_blender()
        if not blender: self.skipTest("Blender not installed")
        script = os.path.join(os.path.dirname(__file__), "blender", "round_export.py")
        with tempfile.TemporaryDirectory() as out:
            run = subprocess.run([blender, "-b", "--factory-startup", "--python-exit-code", "3", "--python", script,
                                  "--", "--out", out, "--family", "extrusion"],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout)
            self.assertTrue(all(not row["errors"] and not row["open"] for row in check_export(out + "/models").values()))
            for kind in ("Arch", "Beam", "Arrow"):
                with open(out + "/models/Gen_ExtrusionFixture_" + kind + ".cubegen.json") as stream:
                    data = json.load(stream)
                self.assertEqual(len(data["colliders"]), 3)
                self.assertTrue(all(c["convex"] for c in data["colliders"]))
                self.assertEqual(sum(p["empty"] for p in data["parts"]), 1)

    def test_round_real_fbx_contracts_survive_sequential_collection_rebuilds(self):
        import json
        import os
        import subprocess
        import tempfile
        from cubegen.blender import find_blender
        from cubegen.contract import check_export
        blender = find_blender()
        if not blender: self.skipTest("Blender not installed")
        script = os.path.join(os.path.dirname(__file__), "blender", "round_export.py")
        with tempfile.TemporaryDirectory() as out:
            run = subprocess.run([blender, "-b", "--factory-startup", "--python-exit-code", "3",
                                  "--python", script, "--", "--out", out],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout)
            self.assertTrue(all(not row["errors"] and not row["open"] for row in check_export(out + "/models").values()))
            for kind, count in (("Pipe", 8), ("Band", 10), ("Torus", 10)):
                with open(out + "/models/Gen_RoundFixture_" + kind + ".cubegen.json") as stream:
                    data = json.load(stream)
                self.assertEqual(len(data["colliders"]), count)
                self.assertTrue(all(c["convex"] for c in data["colliders"]))
                self.assertEqual(sum(p["empty"] for p in data["parts"]), 1)

    def test_cryo_pod_fragment_empty_pivots_survive_real_fbx_rounding(self):
        import tempfile
        from cubegen.blender import find_blender
        from cubegen.cli import main
        from cubegen.contract import check_export
        if not find_blender(): self.skipTest("Blender not installed")
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(main(["generate", "--seed", "42", "--types", "cryo_pod", "--damage", "fractured", "--generation", "3", "--clutter", "none", "--no-render", "--no-blend", "--out", out]), 0)
            self.assertTrue(all(not row["errors"] and not row["open"] for row in check_export(out + "/models").values()))
