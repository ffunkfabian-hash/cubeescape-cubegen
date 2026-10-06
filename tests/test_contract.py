"""Every sidecar keeps the Unity importer's contract (Cube Escape Docs/CUBEGEN_IMPORT.md, see cubegen/contract.py)."""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen.contract import check_sidecar  # noqa: E402
from cubegen.models import model_types  # noqa: E402
from cubegen.params import Style  # noqa: E402
from cubegen.pipeline import BatchConfig, build_spec, lod_spec, plan_models, rig_data, wants_lod  # noqa: E402

PICKUPS = {"item", "keycard", "key", "tool", "clue", "spare_part", "flashlight", "cable_reel"}


def sidecars(seed, count, style=None, lods=False):
    config = BatchConfig(seed=seed, models={t: count for t in model_types()}, out_dir="-", prefix="Gen_",
                         style=style or Style())
    for spec in plan_models(config):
        asset = build_spec(spec)
        lod = build_spec(lod_spec(spec)) if lods and wants_lod(spec, asset) else None
        yield spec, rig_data(asset, spec, seed, lod=lod)


class ContractTests(unittest.TestCase):
    def test_all_types_keep_the_contract(self):
        for seed, style, lods in ((42, None, False), (7, Style(damage="damaged", wear="heavy"), False),
                                  (3, Style(damage="destroyed"), False), (11, Style(theme="labor-3"), True)):
            for spec, data in sidecars(seed, 3, style, lods):
                errors, open_items = check_sidecar(data, spec["name"] + ".cubegen.json")
                self.assertEqual(errors, [], spec["name"])
                if open_items:  # only the pickups miss an item id, never anything else
                    self.assertIn(spec["type"], PICKUPS)

    def test_destroyed_hierarchies_keep_their_parents(self):
        # 0.8.0: a broken-off parent part was dropped while its children still pointed at it
        from cubegen.models import generate_asset

        for t in ("balance_scale", "robot_arm", "service_robot", "turret"):
            for seed in range(60):
                asset = generate_asset(t, seed, style=Style(damage="destroyed"))
                names = {o.name for o in asset.objects}
                self.assertTrue(all(o.parent is None or o.parent in names for o in asset.objects), f"{t} {seed}")

    def test_behaviours_only_name_parts_with_geometry(self):
        from cubegen.models import generate_asset

        for seed in range(300):  # pipe with valve and its only glow ring under the valve (0.8.0: missing Glow)
            asset = generate_asset("pipe", seed)
            for b in asset.behaviours:
                for value in b["parts"].values():
                    for name in value if isinstance(value, list) else [value]:
                        self.assertIsNotNone(asset.get(name), f"pipe {seed}: {name}")

    def test_item_id_closes_the_assignment(self):
        config = BatchConfig(seed=42, models={t: 1 for t in PICKUPS}, out_dir="-",
                             params={t: {"item_id": "servo_battery"} for t in PICKUPS})
        for spec in plan_models(config):
            errors, open_items = check_sidecar(rig_data(build_spec(spec), spec, 42))
            self.assertEqual((errors, open_items), ([], []), spec["name"])

    def test_detects_violations(self):
        spec, good = next((s, d) for s, d in sidecars(42, 1) if s["type"] == "door")
        self.assertEqual(check_sidecar(good)[0], [])
        cases = {
            "root: unknown key": lambda d: d.update(lods={}),
            "unknown key 'colour'": lambda d: d["parts"][0].update(colour="red"),
            "unknown field 'travel'": lambda d: d["behaviours"][0]["fields"].update(travel=1.0),
            "names unknown part": lambda d: d["behaviours"][0]["parts"].update(panels=["Nope"]),
            "speed": lambda d: d["behaviours"][0]["fields"].update(speed=0),
            "upperFrame only accepts Frame_Top": lambda d: d["behaviours"][0]["parts"].update(upperFrame=["Panel"]),
            "already moved": lambda d: d["behaviours"].append(
                {"script": "Rotator", "parts": {"target": "Panel"}, "fields": {"axis": "up"}}),
            "normalised": lambda d: d.update(colliders=[{"type": "box", "part": None, "center": [0, 0, 0],
                                                         "size": [1, 1, 1], "rotation": [0, 0, 0, 2]}]),
            "must be convex": lambda d: d.update(colliders=[{"type": "mesh", "part": "Panel", "convex": False}]),
            "single path segment": lambda d: d.update(model="../x"),
        }
        for expected, change in cases.items():
            data = copy.deepcopy(good)
            change(data)
            errors = check_sidecar(data)[0]
            self.assertTrue(any(expected in e for e in errors), f"{expected}: {errors}")


if __name__ == "__main__":
    unittest.main()
