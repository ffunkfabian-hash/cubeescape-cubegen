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


for cls in (addon.CUBEGEN_PT_main, addon.CUBEGEN_PT_grid, addon.CUBEGEN_PT_export):
    try:
        cls.draw(type("P", (), {"layout": Fake()})(), Ctx)
    except Exception as exc:
        problems.append(f"{cls.__name__}: {exc!r}")
prefs = bpy.context.preferences.addons["cubegen_addon"].preferences
addon.CUBEGEN_Preferences.draw(type("P", (), {"layout": Fake(), "bl_rna": prefs.bl_rna})(), Ctx)

bpy.ops.cubegen.clear()
assert addon.PREVIEW_COLLECTION not in bpy.data.collections and addon.GRID_COLLECTION not in bpy.data.collections
bpy.ops.preferences.addon_disable(module="cubegen_addon")

print("PROBLEMS", problems)
assert not problems
print("ADDON_SMOKE_OK")
