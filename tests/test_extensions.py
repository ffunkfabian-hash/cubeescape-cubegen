"""Roadmap phase 3: snapping, palette mode, symmetric sweep, families with props, fractured state, text on models,
anchors for sound and effects, and the new model types."""

import json
import math
import os
import struct
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen import palette  # noqa: E402
from cubegen.cli import main  # noqa: E402
from cubegen.contract import check_sidecar  # noqa: E402
from cubegen.families import JOINS, RULES, connectors  # noqa: E402
from cubegen.models import generate_asset, model_types  # noqa: E402
from cubegen.models.anchors import ANCHORS  # noqa: E402
from cubegen.models.buildkit import _arch_curve  # noqa: E402
from cubegen.models.lettering import CHARSET, check_text, strokes, text_width  # noqa: E402
from cubegen.params import Style  # noqa: E402
from cubegen.pipeline import rig_data  # noqa: E402
from cubegen.quality import draw_calls, z_fighting  # noqa: E402
from cubegen.snapping import connector_data, occupied, place, snap  # noqa: E402

NEW_TYPES = ("ramp", "ceiling_module", "archway", "wall_cap", "baseboard", "push_block", "sequence_panel",
             "water_level", "laser_filter", "symbol_plate", "crane", "countdown", "lab_device", "galley", "washroom",
             "floor_plan", "floodlight", "light_strip", "emergency_light", "patrol_drone", "vent_crawler", "robot_dog",
             "mech", "vines", "cocoon", "wall_roots", "fungus_carpet", "puddle", "escape_pod", "solar_panel",
             "asteroid", "planet_window", "crashed_pod", "burnt_console", "collapsed_catwalk")


def manifest_seed(out, name):
    with open(os.path.join(out, "manifest.json"), encoding="utf-8") as fh:
        return next(m["seed"] for m in json.load(fh)["models"] if m["name"] == name)


def sidecar_errors(asset, model_type, seed=0):
    rig = rig_data(asset, {"type": model_type, "seed": seed, "style": {}}, 1)
    return check_sidecar(rig, f"{asset.name}.cubegen.json")[0]


class NewTypeTests(unittest.TestCase):
    def test_all_new_types_are_registered(self):
        self.assertEqual(sorted(set(NEW_TYPES) - set(model_types())), [])
        self.assertEqual(len(model_types()), 175)

    def test_puzzle_solutions_and_wiring(self):
        for seed in range(20):
            seq = generate_asset("sequence_panel", seed)
            n = seq.meta["buttons"]
            self.assertTrue(all(1 <= k <= n for k in seq.meta["sequence"]))
            lights = seq.meta["deferred_behaviours"]
            self.assertEqual(len(lights), n)
            self.assertEqual([b["script"] for b in seq.behaviours], ["SignalLight"])
            for i in range(1, n + 1):
                self.assertEqual(seq.get(f"Light_{i}").parent, f"Button_{i}")
                self.assertEqual(lights[i - 1]["parts"]["renderers"], [f"Light_{i}"])
                self.assertEqual(lights[i - 1]["fields"]["onMaterial"], seq.meta["colours"][i - 1])
                self.assertIn(f"Light_{i}", palette.material_map(seq).keep_parts)

            water = generate_asset("water_level", seed)
            wheels = [b for b in water.behaviours if b["script"] == "Rotatable"]
            self.assertEqual([b["fields"]["target"] for b in wheels], [int(t * 4) for t in water.meta["targets"]])

            plates = generate_asset("symbol_plate", seed)
            turns = [b["fields"]["target"] for b in plates.behaviours if b["script"] == "Rotatable"]
            self.assertEqual([(t + k) % 4 for t, k in zip(turns, plates.meta["turned"])], [0] * plates.meta["plates"])

            crane = generate_asset("crane", seed)
            if crane.meta["style"] == "jib":
                self.assertEqual(crane.get("Glow").parent, "Jib")
                self.assertEqual(crane.behaviours[0]["fields"]["step"], 45)

            clock = generate_asset("countdown", seed)
            minutes, seconds = map(int, clock.meta["time"].split(":"))
            self.assertEqual(minutes * 60 + seconds, clock.meta["seconds_total"])

            block = generate_asset("push_block", seed)
            self.assertEqual(len(block.colliders), 1)
            self.assertFalse(block.behaviours)

    def test_robot_joints(self):
        for seed in range(20):
            dog = generate_asset("robot_dog", seed)
            self.assertEqual(sum(o.name.startswith("Leg_") for o in dog.objects), 4)
            self.assertEqual(dog.get("Glow").parent, "Head")
            mech = generate_asset("mech", seed)
            self.assertEqual((mech.get("Arm_L").parent, mech.get("Arm_R").parent), ("Torso", "Torso"))
            drone = generate_asset("patrol_drone", seed)
            rotors = sorted(b["fields"]["speed"] for b in drone.behaviours if b["parts"].get("target", "")
                            .startswith("Rotor_"))
            self.assertEqual(rotors[0], -rotors[1])  # the two fans turn against each other

    def test_static_and_scripted(self):
        for t in ("ramp", "archway", "wall_cap", "baseboard", "ceiling_module", "push_block", "galley", "washroom",
                  "vines", "puddle", "asteroid", "crashed_pod", "collapsed_catwalk"):
            self.assertFalse(generate_asset(t, 3).behaviours, t)
        for t in ("escape_pod", "laser_filter", "floodlight", "light_strip", "countdown", "floor_plan"):
            self.assertTrue(generate_asset(t, 3).behaviours, t)

    def test_floodlight_light_fields(self):
        light = generate_asset("floodlight", 2).behaviours[0]["fields"]
        self.assertEqual(len(light["lightPosition"]), 3)
        self.assertGreater(light["range"], 0)
        self.assertGreater(light["intensity"], 0)

    def test_ramp_ends(self):
        for seed in range(10):
            ramp = generate_asset("ramp", seed)
            cons = {c["name"]: c for c in connectors(ramp, "ramp")}
            self.assertAlmostEqual(cons["top"]["pos"][2], ramp.meta["rise_m"], places=4)
            self.assertAlmostEqual(cons["top"]["pos"][1] - cons["bottom"]["pos"][1], ramp.meta["run_m"], places=4)

    def test_solar_panel_legs_carry_the_array(self):
        # the legs once ran the wrong way: the front ones stuck through the array, the back ones ended below it
        for tilt in (10, 35, 60):
            for seed in range(4):
                panel = generate_asset("solar_panel", seed, params={"mount": "frame", "tilt": tilt})
                array = panel.get("Array").mesh
                slab = array.parts[0]
                def area(fi):
                    a, b, c = (array.verts[i] for i in array.faces[fi][:3])
                    return math.dist(a, b) * math.dist(b, c)  # the slab's faces are rectangles

                down = [fi for fi in range(slab.f0, slab.f1) if array.face_normal(fi)[2] < 0]
                bottom = max(down, key=area)  # the underside, not the front edge (which points down too)
                n = array.face_normal(bottom)
                p0 = array.verts[array.faces[bottom][0]]
                body = panel.get("Body").mesh
                legs = [part for part in body.parts if body.part_bbox(part)[1][0] - body.part_bbox(part)[0][0] < 0.07]
                self.assertEqual(len(legs), 4)
                for leg in legs:
                    (x0, y0, _), (x1, y1, top) = body.part_bbox(leg)
                    tip = ((x0 + x1) / 2, (y0 + y1) / 2, top)
                    gap = sum(n[i] * (tip[i] - p0[i]) for i in range(3))
                    self.assertAlmostEqual(gap, 0.0, delta=0.002, msg=(tilt, seed, tip))

    def test_archway_flush_with_posts(self):
        # the infill above the passage once sat half a wall thickness behind the posts
        for shape in ("round", "pointed", "chamfer", "flat"):
            for seed in range(4):
                arch = generate_asset("archway", seed, params={"shape": shape, "thickness": 0.6})
                (_, y0, _), (_, y1, _) = arch.bbox()
                self.assertAlmostEqual(y0, -y1, places=4, msg=(shape, seed))
                self.assertLessEqual(y1, 0.3 + 0.05 + 1e-6, (shape, seed))  # wall + keystone overhang
                # nothing (keystone, frame bands) reaches into the passage; 3 mm = the anti-flicker lift
                w, oh = arch.meta["opening_m"]
                curve = _arch_curve(arch.meta["shape"], w, oh)
                for obj in arch.meshes():
                    for x, _, z in obj.mesh.verts:
                        if abs(x) < w / 2 - 0.003 and z > 0.01:
                            top = next(z1 + (z2 - z1) * (x - x1) / (x2 - x1) if x2 > x1 else max(z1, z2)
                                       for (x1, z1), (x2, z2) in zip(curve, curve[1:]) if x1 <= x <= x2)
                            self.assertGreater(z, top - 0.003, (shape, seed, obj.name, x, z))


class LetteringTests(unittest.TestCase):
    def test_font(self):
        self.assertEqual(check_text("b-12"), "B-12")
        for bad in ("", "A" * 30, "x@y"):
            with self.assertRaises(ValueError):
                check_text(bad)
        for char in CHARSET:
            self.assertEqual(check_text(char) if char != " " else " ", char)
        self.assertGreater(text_width("B-12", 0.1), text_width("B", 0.1))
        self.assertEqual(strokes(" "), [])

    def test_sign_door_countdown(self):
        plain = generate_asset("sign", 4)
        sign = generate_asset("sign", 4, params={"text": "Sektor 7"})
        self.assertEqual(sign.meta["text"], "SEKTOR 7")
        self.assertNotIn("text", plain.meta)
        self.assertGreater(sign.stats()["triangles"], plain.stats()["triangles"])
        with self.assertRaises(ValueError):
            generate_asset("sign", 4, params={"text": "a" * 17})
        door = generate_asset("door", 2, params={"label": "B-12"})
        self.assertIsNotNone(door.get("Label"))
        self.assertEqual(door.behaviours, generate_asset("door", 2).behaviours)  # the Door wiring stays
        self.assertFalse(z_fighting(door, pivot="floor"))
        clock = generate_asset("countdown", 1, params={"minutes": 5, "seconds": 0, "text": "Evakuierung"})
        self.assertEqual((clock.meta["time"], clock.meta["text"]), ("05:00", "EVAKUIERUNG"))
        plan = generate_asset("floor_plan", 3, params={"title": "Deck 3"})
        self.assertEqual(plan.meta["title"], "DECK 3")


class SweepTests(unittest.TestCase):
    def test_sweep_option_changes_nothing_without_it(self):
        for t in ("camera", "turret"):  # sweep 0 = as before (only "params" records the explicit 0)
            a, b = generate_asset(t, 5), generate_asset(t, 5, params={"sweep": 0})
            self.assertEqual(a.behaviours, b.behaviours)
            self.assertEqual([(o.name, o.parent, o.pivot, o.mesh and o.mesh.verts) for o in a.objects],
                             [(o.name, o.parent, o.pivot, o.mesh and o.mesh.verts) for o in b.objects])

    def test_symmetric_sweep(self):
        for t, part in (("camera", "Rotor"), ("turret", "Turret")):
            for seed in range(10):
                still = generate_asset(t, seed)
                swept = generate_asset(t, seed, params={"sweep": 120})
                rotator = next(b for b in swept.behaviours if b["script"] == "Rotator")
                self.assertEqual((rotator["fields"]["arc"], rotator["fields"]["speed"]), (120.0, 30.0))
                self.assertEqual(swept.meta["sweep_deg"], [-60.0, 60.0])
                self.assertEqual(sidecar_errors(swept, t, seed), [])
                # the part is built turned +60 degrees (Blender Z) around its own vertical axis
                a, b = still.get(part), swept.get(part)
                px, py = a.pivot[0], a.pivot[1]
                for va, vb in zip(a.mesh.verts, b.mesh.verts):
                    ang = math.radians(60)
                    x, y = va[0] - px, va[1] - py
                    expect = (px + math.cos(ang) * x - math.sin(ang) * y, py + math.sin(ang) * x + math.cos(ang) * y)
                    self.assertAlmostEqual(vb[0], expect[0], places=6)
                    self.assertAlmostEqual(vb[1], expect[1], places=6)
        camera = generate_asset("camera", 1, params={"sweep": 90, "speed": 20})
        self.assertEqual(camera.get("Glow").parent, "Rotor")  # the LED turns with the head
        self.assertEqual(next(b for b in camera.behaviours if b["script"] == "Rotator")["fields"]["speed"], 20.0)


class AnchorTests(unittest.TestCase):
    def test_generation_3_adds_only_empties(self):
        for t in model_types():
            new, old = generate_asset(t, 2), generate_asset(t, 2, style=Style(generation=2))
            added = [o for o in new.objects if o.name not in {p.name for p in old.objects}]
            self.assertTrue(all(o.is_empty and o.name.startswith(("Audio_", "FX_")) for o in added), t)
            self.assertEqual(bool(added), t in ANCHORS, t)
            for o in added:
                self.assertIsNotNone(new.get(o.parent), f"{t} {o.name}")
                lo, hi = new.get(o.parent).mesh.bbox()
                self.assertTrue(all(lo[i] - 1e-6 <= o.pivot[i] <= hi[i] + 1e-6 for i in range(3)), f"{t} {o.name}")
            same = [(o.name, o.mesh.verts, o.mesh.faces) for o in new.meshes()]
            self.assertEqual(same, [(o.name, o.mesh.verts, o.mesh.faces) for o in old.meshes()], t)

    def test_ruins_get_smoke(self):
        ruin = generate_asset("machine", 1, style=Style(damage="destroyed"))
        self.assertEqual([o.name for o in ruin.objects if o.is_empty], ["FX_Smoke"])
        self.assertFalse(any(o.is_empty for o in generate_asset("machine", 1, style=Style(damage="fractured"))
                             .objects))

    def test_damaged_doors_keep_their_frame(self):
        # generation 3: a piece knocked off a door frame no longer lies in the passage (the frame is a collider)
        for seed in range(30):
            door = generate_asset("door", seed, style=Style(damage="damaged"))
            for name in ("Frame_Left", "Frame_Right", "Frame_Top"):
                lo, hi = door.get(name).mesh.bbox()
                intact = generate_asset("door", seed).get(name).mesh.bbox()
                for i in range(3):
                    self.assertLess(abs(lo[i] - intact[0][i]), 0.2, f"{seed} {name}")
                    self.assertLess(abs(hi[i] - intact[1][i]), 0.2, f"{seed} {name}")


class FractureTests(unittest.TestCase):
    def test_fragments(self):
        for t in ("crate", "wall", "machine", "door", "pillar", "tank"):
            for seed in range(3):
                whole = generate_asset(t, seed)
                broken = generate_asset(t, seed, style=Style(damage="fractured"))
                names = [o.name for o in broken.objects]
                self.assertTrue(names and all(n.startswith("Fragment_") for n in names), names)
                self.assertEqual(broken.meta["fragments"], len(names))
                self.assertGreaterEqual(len(names), 3, t)
                self.assertFalse(broken.behaviours)
                self.assertEqual([(c.kind, c.part, c.convex) for c in broken.colliders],
                                 [("mesh", n, True) for n in names])
                vol = lambda a: sum(o.mesh.part_volume(p) for o in a.meshes() for p in o.mesh.parts)  # noqa: E731
                self.assertAlmostEqual(vol(broken), vol(whole), delta=vol(whole) * 0.01 + 1e-4, msg=t)
                for o in broken.meshes():
                    for p in o.mesh.parts:
                        self.assertGreater(o.mesh.part_volume(p), 0)
                    lo, hi = o.mesh.bbox()
                    self.assertTrue(all(lo[i] - 1e-6 <= o.pivot[i] <= hi[i] + 1e-6 for i in range(3)))
                self.assertEqual(sidecar_errors(broken, t, seed), [])
                self.assertEqual(broken.digest(), generate_asset(t, seed, style=Style(damage="fractured")).digest())


def families_with_palette():
    from cubegen.families import family_files, load_family

    return {name for name, path in family_files().items() if load_family(path).get("palette")}


class PaletteTests(unittest.TestCase):
    def test_cells(self):
        uvs = {m: palette.uv(m) for m in palette.ORDER}
        self.assertEqual(len(set(uvs.values())), len(uvs))
        for u, v in uvs.values():
            self.assertTrue(0 < u < 1 and 0 < v < 1)

    def test_material_map_and_draw_calls(self):
        crate = generate_asset("crate", 1)
        self.assertEqual(palette.draw_calls(crate), 1)
        self.assertLess(palette.draw_calls(crate), draw_calls(crate) + 1)
        window = generate_asset("window_wall", 1)
        self.assertEqual(palette.draw_calls(window), 2)  # glass stays transparent
        door = generate_asset("door", 1)
        pm = palette.material_map(door)
        self.assertEqual(pm("StatusLight_Front", "M_GlowRed"), "M_GlowRed")  # the Door script recolours it
        self.assertEqual(pm("Panel", "M_Metal"), palette.PALETTE_MATERIAL)
        for t in model_types():
            a = generate_asset(t, 0)
            self.assertLessEqual(palette.draw_calls(a), draw_calls(a), t)

    def test_export_without_blender(self):
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(main(["generate", "--seed", "3", "--types", "crate,door", "--no-blender",
                                   "--textures", "palette", "--out", out]), 0)
            tex = os.path.join(out, "models", "Textures")
            with open(os.path.join(tex, "CubeEscape_Palette.json"), encoding="utf-8") as fh:
                info = json.load(fh)
            self.assertEqual(info["name"], "MP_Palette")
            with open(os.path.join(tex, "MP_Palette_Albedo.png"), "rb") as fh:
                png = fh.read()
            self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
            width, height = struct.unpack(">II", png[16:24])
            self.assertEqual((width, height), tuple(info["size"]))
            idat = png[png.index(b"IDAT") + 4:png.index(b"IEND") - 8]
            raw = zlib.decompress(idat)
            self.assertEqual(len(raw), height * (1 + width * 4))
            with open(os.path.join(out, "models", "Door_000.cubegen.json"), encoding="utf-8") as fh:
                rig = json.load(fh)
            mats = {p["name"]: p["materials"] for p in rig["parts"]}
            self.assertEqual(mats["Panel"], ["MP_Palette"])
            self.assertEqual(mats["StatusLight_Front"], ["M_GlowRed"])
            self.assertEqual(rig["textures"], {"mode": "palette", "manifest": "Textures/CubeEscape_Palette.json"})
            from cubegen.contract import check_sidecar
            self.assertEqual(check_sidecar(rig)[0], [])
            with open(os.path.join(out, "models", "Crate_000.obj"), encoding="utf-8") as fh:
                obj = fh.read()
            self.assertIn("usemtl MP_Palette", obj)
            u, v = palette.uv(generate_asset("crate", manifest_seed(out, "Crate_000")).get("Body").mesh.roles[0])
            self.assertIn(f"vt {u:.6f} {v:.6f}", obj)
            with open(os.path.join(out, "manifest.json"), encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["textures"]["mode"], "palette")

    def test_color_palettes(self):
        from cubegen.materials import MATERIALS

        self.assertEqual(palette.palette_names()[0], "standard")
        self.assertEqual(palette.palette_material(None), "MP_Palette")
        self.assertEqual(palette.palette_material("Rust"), "MP_Palette_Rust")
        self.assertTrue(palette.is_palette_material("MP_Palette_Neon"))
        self.assertFalse(palette.is_palette_material("M_Metal"))
        with self.assertRaises(ValueError):
            palette.check_palette("bogus")
        self.assertEqual(palette.palette_colors("standard"), MATERIALS)
        seen = set()
        for name, entry in palette.COLOR_PALETTES.items():
            colors = entry["colors"]
            self.assertEqual(set(colors), set(MATERIALS) - {"M_Glass"}, name)  # glass keeps its own material
            for rgb in colors.values():
                self.assertTrue(all(0.0 <= c <= 1.0 for c in rgb), name)
            table = palette.palette_colors(name)
            self.assertEqual({m: v[1:3] for m, v in table.items()}, {m: v[1:3] for m, v in MATERIALS.items()})
            red, cyan = table["M_GlowRed"][0], table["M_GlowCyan"][0]
            self.assertGreater(red[0], max(red[1], red[2]) + 0.3, name)  # alarm red stays red
            self.assertNotEqual(red, cyan, name)
            key = tuple(table[m][0] for m in palette.ORDER)
            self.assertNotIn(key, seen, name)
            seen.add(key)
            if entry.get("family"):
                self.assertIn(entry["family"], families_with_palette())
        # the same model in another palette: same UVs, only the material name changes
        door = generate_asset("door", 1)
        pm = palette.material_map(door, "neon")
        self.assertEqual(pm("Panel", "M_Metal"), "MP_Palette_Neon")
        self.assertEqual(pm("StatusLight_Front", "M_GlowRed"), "M_GlowRed")

    def test_color_palette_export(self):
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(main(["generate", "--seed", "3", "--types", "crate", "--no-blender", "--palette", "neon",
                                   "--out", out]), 0)  # --palette implies --textures palette
            tex = os.path.join(out, "models", "Textures")
            self.assertEqual(sorted(os.listdir(tex)), ["CubeEscape_Palette_Neon.json", "MP_Palette_Neon_Albedo.png",
                                                       "MP_Palette_Neon_Emission.png",
                                                       "MP_Palette_Neon_MetallicSmoothness.png"])
            with open(os.path.join(tex, "CubeEscape_Palette_Neon.json"), encoding="utf-8") as fh:
                info = json.load(fh)
            self.assertEqual((info["name"], info["palette"]), ("MP_Palette_Neon", "neon"))
            with open(os.path.join(out, "models", "Crate_000.cubegen.json"), encoding="utf-8") as fh:
                rig = json.load(fh)
            self.assertEqual(rig["textures"], {"mode": "palette", "manifest": "Textures/CubeEscape_Palette_Neon.json"})
            from cubegen.contract import check_sidecar
            self.assertEqual(check_sidecar(rig)[0], [])
            self.assertEqual(info["cells"]["M_Metal"]["uv"], list(palette.uv("M_Metal")))
            with open(os.path.join(out, "models", "Crate_000.obj"), encoding="utf-8") as fh:
                self.assertIn("usemtl MP_Palette_Neon", fh.read())
            with open(os.path.join(out, "models", "CubeEscape_Materials.mtl"), encoding="utf-8") as fh:
                self.assertIn("map_Kd Textures/MP_Palette_Neon_Albedo.png", fh.read())
            with open(os.path.join(out, "manifest.json"), encoding="utf-8") as fh:
                textures = json.load(fh)["textures"]
            self.assertEqual((textures["material"], textures["palette"]), ("MP_Palette_Neon", "neon"))
            sheet = os.path.join(out, "swatches.png")
            self.assertEqual(main(["palettes", "--swatches", sheet]), 0)
            with open(sheet, "rb") as fh:
                self.assertEqual(struct.unpack(">II", fh.read()[16:24]), (24 * len(palette.ORDER),
                                                                         24 * len(palette.palette_names())))
        with tempfile.TemporaryDirectory() as out:  # a family's palette applies in palette mode only
            self.assertEqual(main(["generate", "--family", "foundry", "--types", "crate", "--no-blender",
                                   "--textures", "palette", "--out", out]), 0)
            with open(os.path.join(out, "manifest.json"), encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["textures"]["material"], "MP_Palette_Rust")
        self.assertEqual(main(["generate", "--types", "crate", "--no-blender", "--palette", "neon",
                               "--textures", "tiled"]), 2)  # a colour palette needs palette mode


class SnappingTests(unittest.TestCase):
    def test_joins_cover_the_fit_rules(self):
        for a, b in RULES:
            self.assertTrue((a, b) in JOINS or (b, a) in JOINS, (a, b))

    def test_catwalk_chain(self):
        a = connector_data(generate_asset("catwalk", 1, params={"length": 4.0, "width": 2.0}), "catwalk")
        b = connector_data(generate_asset("catwalk", 2, params={"length": 4.0, "width": 2.0}), "catwalk")
        pose_a = (0.4, (1.0, 2.0, 0.0))
        result = snap(b, (1.0, (6.0, 3.5, 0.2)), [("A", a, pose_a)], "B")
        self.assertEqual(result["mode"], "face")
        joined = occupied([("A", a, pose_a), ("B", b, result["pose"])])
        self.assertEqual(len(joined), 2)
        # the next catwalk snaps onto the free end, not onto the joint that is taken
        c = connector_data(generate_asset("catwalk", 3, params={"length": 4.0, "width": 2.0}), "catwalk")
        again = snap(c, (0.0, (3.0, 4.0, 0.0)), [("A", a, pose_a), ("B", b, result["pose"])], "C")
        self.assertNotIn((again["target"], again["target_connector"]), joined)

    def test_door_wall_cap_baseboard(self):
        wall = generate_asset("wall", 3, params={"opening": "door", "door_style": "sliding", "door_width": 2.0,
                                                 "door_height": 2.2, "length": 4.0})
        cw = connector_data(wall, "wall")
        pose_w = (math.pi / 2, (10.0, 0.0, 0.0))
        for t, params, mine, theirs in (
                ("door", {"style": "sliding", "width": 2.0, "height": 2.2}, "frame", "door"),
                ("wall_cap", {"length": 4.0}, "cap", "top"),
                ("baseboard", {"length": 4.0}, "back", "face_front")):
            cons = connector_data(generate_asset(t, 1, params=params), t)
            near = place(next(c for c in cw if c["name"] == theirs), pose_w)[0]
            result = snap(cons, (0.0, (near[0] + 0.5, near[1] - 0.3, 0.0)), [("W", cw, pose_w)], t)
            self.assertEqual((result["connector"], result["target_connector"]), (mine, theirs), t)
            self.assertEqual(result["mode"], "align")
            self.assertAlmostEqual(math.cos(result["pose"][0] - pose_w[0]), 1.0, places=6)  # same orientation

    def test_nothing_to_snap(self):
        crate = connector_data(generate_asset("crate", 1), "crate")
        self.assertIsNone(snap(crate, (0.0, (0, 0, 0)), [("W", connector_data(generate_asset("wall", 1), "wall"),
                                                                              (0.0, (5, 0, 0)))]))
        a = connector_data(generate_asset("catwalk", 1), "catwalk")
        self.assertIsNone(snap(a, (0.0, (0, 0, 0)), [("B", a, (0.0, (50, 0, 0)))], max_distance=5.0))


if __name__ == "__main__":
    unittest.main()
