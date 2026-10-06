"""Smoke test for the Blender add-on - run inside Blender:

    BLENDER_USER_SCRIPTS=/tmp/s BLENDER_USER_CONFIG=/tmp/c \
    blender -b --factory-startup -P tests/blender/addon_smoke.py -- dist/cubegen_blender_addon.zip OUTDIR

(The environment variables keep the test install out of your real Blender preferences.)

Installs the zip, enables the add-on, builds preview and variant grid, exports
selected variants and draws every panel with a checking fake layout.
"""
import os
import sys

import bpy

zip_path, out = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.preferences.addon_install(filepath=zip_path, overwrite=True)
bpy.ops.preferences.addon_enable(module="cubegen_addon")
bpy.context.scene.cubegen.model_type = "wall"  # an enabled add-on with a preview, then install again
bpy.ops.preferences.addon_install(filepath=zip_path, overwrite=True)
bpy.ops.preferences.addon_enable(module="cubegen_addon")
import cubegen_addon as addon  # noqa: E402

scene = bpy.context.scene
s = scene.cubegen
problems = []

# --- preview with live update ----------------------------------------------------
s.model_type = "door"          # live update builds the preview
s.master_seed = "42"
s.variant = 1
prev = bpy.data.collections[addon.PREVIEW_COLLECTION]
names = sorted(o.name for o in prev.objects)
print("PREVIEW", names)
assert "Gen_Door_001.Panel" in names, names
panel = bpy.data.objects["Gen_Door_001.Panel"]
assert panel.location.z > 0.5 and tuple(panel.rotation_euler) == (0, 0, 0), panel.location
assert "M_GlowRed" in bpy.data.materials

bpy.ops.cubegen.step(delta=1)
assert s.variant == 2 and "Gen_Door_002.Frame_Top" in bpy.data.objects
bpy.ops.cubegen.step(random=True)

# --- grid + selection --------------------------------------------------------------
s.model_type = "crate"
s.grid_count, s.grid_start = 6, 0
bpy.ops.cubegen.grid()
grid = bpy.data.collections[addon.GRID_COLLECTION]
print("GRID", [c.name for c in grid.children])
assert len(grid.children) == 6
for o in bpy.context.view_layer.objects:
    o.select_set(False)
bpy.data.objects["Gen_Crate_001.Body"].select_set(True)
bpy.data.objects["Gen_Crate_004.Label"].select_set(True)
picks = addon.selected_variants(bpy.context)
print("PICKS", picks)
assert picks == [("42", "crate", 1), ("42", "crate", 4)], picks

bpy.context.view_layer.objects.active = bpy.data.objects["Gen_Crate_004.Body"]
bpy.ops.cubegen.use_active()
assert s.model_type == "crate" and s.variant == 4

# "Nur unterschiedliche": same variants as the CLI's --unique
s.model_type, s.unique = "laser_mirror", True
bpy.ops.cubegen.grid()
grid_names = sorted(c.name for c in bpy.data.collections[addon.GRID_COLLECTION].children)
cli = addon.pipeline.plan_models(addon.pipeline.BatchConfig(seed=42, models={"laser_mirror": 6}, out_dir="-",
                                                            prefix="Gen_", unique=True))
print("UNIQUE", grid_names)
assert grid_names == sorted(spec["name"] for spec in cli), (grid_names, cli)
s.unique, s.model_type = False, "crate"
bpy.ops.cubegen.grid()  # back to the crate grid for the selection export below

# --- export of the selection (synchronous in background mode) ----------------------
s.export_dir = os.path.join(out, "Models")
s.icons_dir = os.path.join(out, "Icons")
s.out_dir = os.path.join(out, "cubegen")
s.fmt_glb = True
for o in bpy.context.view_layer.objects:
    o.select_set(False)
bpy.data.objects["Gen_Crate_001.Body"].select_set(True)
bpy.data.objects["Gen_Crate_004.Glow"].select_set(True)
result = bpy.ops.cubegen.export(mode="SELECTED")
print("EXPORT", result, s.status)
assert result == {"FINISHED"}, s.status
for f in ("Models/Gen_Crate_001.fbx", "Models/Gen_Crate_004.fbx", "Models/Gen_Crate_004.glb",
          "Icons/Icon_Gen_Crate_001.png", "cubegen/seed_42/manifest.json"):
    assert os.path.isfile(os.path.join(out, f)), f

# --- one of every type: grid + export of all types (static ones into the library) -------
s.per_type = 1
s.grid_start = 0
bpy.ops.cubegen.all_types()
grid = bpy.data.collections[addon.GRID_COLLECTION]
n_types = len(addon._all_types())
print("ALL_TYPES", len(grid.children))
assert len(grid.children) == n_types, len(grid.children)
assert {c["cubegen_type"] for c in grid.children} == set(addon._all_types())
s.render_icons = False
s.fmt_glb = False
s.library_dir = os.path.join(out, "Models", "Library")
result = bpy.ops.cubegen.export(mode="ALL")
assert result == {"FINISHED"}, s.status
assert os.path.isfile(os.path.join(out, "Models", "Gen_Door_000.fbx"))
assert os.path.isfile(os.path.join(out, "Models", "Library", "Props", "Gen_Crate_000.fbx"))
fbx = [f for _, _, files in os.walk(os.path.join(out, "Models")) for f in files if f.endswith(".fbx")]
print("ALL_EXPORT", len(fbx))

# --- parameters + style ---------------------------------------------------------------
s.model_type = "door"
s.variant = 1
door_params = s.type_params.door
door_params.style = "airlock"
door_params.use_width = True          # starts from the rolled value ...
door_params.width = 2.0               # ... then fixed to 2.0 m
info = addon._INFO
print("PARAMS", info["params"])
assert info["params"]["style"] == "airlock" and abs(info["params"]["width"] - 2.0) < 1e-6, info["params"]
assert "Gen_Door_001.Panel_B" in bpy.data.objects  # airlock = split door
s.detail = "low"
s.wear = "light"
s.model_type = "machine"
assert "Gen_Machine_001.Wear" in bpy.data.objects
cmd = addon._cli_command(s)
print("CLI", cmd)
assert "--wear light" in cmd and "--detail low" in cmd
s.model_type = "door"
assert "--param door.style=airlock" in addon._cli_command(s) and "--param door.width=2.0" in addon._cli_command(s)
s.render_icons = False
s.library_dir = ""
result = bpy.ops.cubegen.export(mode="PREVIEW")
assert result == {"FINISHED"}, s.status
import json  # noqa: E402
rig = json.load(open(os.path.join(out, "Models", "Gen_Door_001.cubegen.json")))
print("RIG", rig["params"], rig["style"]["detail"])
assert rig["params"]["style"] == "airlock" and rig["style"]["wear"] == "light"
bpy.ops.cubegen.reset_params()
assert s.type_params.door.style == addon.SEED and not s.type_params.door.use_width
s.detail, s.wear = "normal", addon.SEED

# --- item id (ItemPickup.itemId): text field, only written when given ----------------------
s.model_type = "keycard"
assert "keycard" not in addon._overrides(s)
s.type_params.keycard.item_id = "Key Card 2"
assert addon._overrides(s)["keycard"] == {"item_id": "Key Card 2"}, addon._overrides(s)
assert "--param 'keycard.item_id=Key Card 2'" in addon._cli_command(s), addon._cli_command(s)
bpy.ops.cubegen.reset_params()
assert s.type_params.keycard.item_id == ""
s.model_type = "door"

# --- room theme: the add-on's style = the CLI's --theme ------------------------------------
s.theme = "labor-3"
style = addon._style(s).resolved()
expected = addon.params_mod.theme_style("labor-3")
assert (style.glow, style.material, style.wear) == (expected["glow"], expected["material"], expected["wear"]), style
assert '--theme labor-3' in addon._cli_command(s), addon._cli_command(s)
s.theme = ""

# --- family: measures, kit, kit export = CLI --family -----------------------------------------
import json  # noqa: E402

s.family = "station"
s.model_type = "door"
info = addon._INFO
assert abs(info["params"]["width"] - 2.0) < 1e-9 and abs(info["params"]["height"] - 2.2) < 1e-9, info["params"]
assert info["params"]["style"] == "sliding", info["params"]
assert "--family station" in addon._cli_command(s)
bpy.ops.cubegen.kit()
kit_grid = bpy.data.collections[addon.GRID_COLLECTION]
entries, own = addon.kit_entries(s)
assert len(kit_grid.children) == len(entries) > 20, len(kit_grid.children)
door_wall = bpy.data.collections["Gen_Wall_001"]
assert json.loads(door_wall["cubegen_params"]) == {"opening": "door"}, door_wall["cubegen_params"]
s.render_icons = True
result = bpy.ops.cubegen.export(mode="KIT")
assert result == {"FINISHED"}, s.status
kit_out = os.path.join(out, "cubegen", "station_seed_42")
manifest = json.load(open(os.path.join(kit_out, "manifest.json")))
print("KIT", manifest["family"]["name"], manifest["family"]["fit"]["joints"], manifest["family"]["fit"]["problems"])
assert manifest["family"]["name"] == "station" and manifest["family"]["fit"]["problems"] == []
assert os.path.isfile(os.path.join(kit_out, "contact_sheet.png"))
rig = json.load(open(os.path.join(out, "Models", "Gen_Wall_001.cubegen.json")))
assert rig["params"]["opening"] == "door" and rig["params"]["door_width"] == 2.0, rig["params"]
# the same door from the command line: identical sidecar
from cubegen_addon.cubegen import cli as addon_cli  # noqa: E402
cli_out = os.path.join(out, "cli_family")
addon_cli.main(["generate", "--family", "station", "--seed", "42", "--pick", "door:0", "--prefix", "Gen_",
                "--no-render", "--no-blender", "--out", cli_out])
cli_rig = json.load(open(os.path.join(cli_out, "models", "Gen_Door_000.cubegen.json")))
addon_rig = json.load(open(os.path.join(out, "Models", "Gen_Door_000.cubegen.json")))
for key in ("parts", "behaviours", "params", "bounds"):
    assert cli_rig[key] == addon_rig[key], key
# foundry (4 m walls): the kit builds, and every type - window_wall, wall_corner too - follows the measures
s.family = "foundry"
assert bpy.ops.cubegen.kit() == {"FINISHED"}
assert len(bpy.data.collections[addon.GRID_COLLECTION].children) == len(addon.kit_entries(s)[0])
assert addon._family_misfits(s) == {}, addon._family_misfits(s)
assert {t for t, _ in addon.all_type_entries(s)} >= {"wall_corner", "window_wall"}
s.family = addon.NO_FAMILY
s.render_icons = False

# --- textures (selection field) + destroyed state + ruins ---------------------------------
s.model_type = "crate"
s.textures = "tiled"
s.texture_size = "256"
body = bpy.data.objects["Gen_Crate_001.Body"]
mats = {slot.material.name for slot in body.material_slots}
print("TILED_PREVIEW", sorted(mats))
assert any(m.startswith("MT_") for m in mats), mats
s.damage = "destroyed"
assert addon._INFO["meta"].get("damage") == "destroyed"
s.model_type = "rubble_pile"
assert "Gen_RubblePile_001.Rubble" in bpy.data.objects
s.model_type = "machine"
s.damage = "intact"
s.textures = "baked"
s.render_icons = False
result = bpy.ops.cubegen.export(mode="PREVIEW")
assert result == {"FINISHED"}, s.status
rig = json.load(open(os.path.join(out, "Models", "Gen_Machine_001.cubegen.json")))
body_mats = next(p["materials"] for p in rig["parts"] if p["name"] == "Body")
print("BAKED", body_mats, rig["textures"]["mode"])
assert body_mats == ["MTA_Gen_Machine_001"], body_mats
assert os.path.isfile(os.path.join(out, "Models", "Textures", "MTA_Gen_Machine_001_Albedo.png"))
s.textures = "none"

# --- panels: draw with a fake layout that validates every prop / operator ----------
class Fake:
    def __init__(self):
        self.enabled = True
        self.scale_y = 1.0

    def _sub(self, *a, **k):
        return Fake()

    row = column = box = split = _sub

    def label(self, **k):
        pass

    def separator(self, **k):
        pass

    def prop(self, data, name, **k):
        if name not in data.bl_rna.properties:
            problems.append(f"missing property {name}")

    def operator(self, idname, **k):
        mod, op = idname.split(".")
        if not hasattr(getattr(bpy.ops, mod), op) or op not in dir(getattr(bpy.ops, mod)):
            problems.append(f"missing operator {idname}")

        class Props:
            pass
        return Props()


class Ctx:
    scene = bpy.context.scene
    preferences = bpy.context.preferences


panels = (addon.CUBEGEN_PT_main, addon.CUBEGEN_PT_family, addon.CUBEGEN_PT_params, addon.CUBEGEN_PT_style,
          addon.CUBEGEN_PT_grid, addon.CUBEGEN_PT_export)
s.live = False
for model_type in addon._all_types():  # the parameter panel differs per type
    s.model_type = model_type
    for cls in panels:
        try:
            cls.draw(type("P", (), {"layout": Fake()})(), Ctx)
        except Exception as exc:
            problems.append(f"{model_type} {cls.__name__}: {exc!r}")
s.family = "lab"
addon.CUBEGEN_PT_family.draw(type("P", (), {"layout": Fake()})(), Ctx)
s.family = addon.NO_FAMILY
s.live = True
prefs = bpy.context.preferences.addons["cubegen_addon"].preferences
addon.CUBEGEN_Preferences.draw(type("P", (), {"layout": Fake(), "bl_rna": prefs.bl_rna})(), Ctx)

bpy.ops.cubegen.clear()
assert addon.PREVIEW_COLLECTION not in bpy.data.collections and addon.GRID_COLLECTION not in bpy.data.collections
bpy.ops.preferences.addon_disable(module="cubegen_addon")

print("PROBLEMS", problems)
assert not problems
print("ADDON_SMOKE_OK")
