"""Cube Escape Model Generator - Blender add-on.

3D Viewport > Sidebar (N) > "Cube Escape":

* pick a model type, a master seed and a variant -> live preview at the origin
* build a grid of variants, select the ones you like
* export them as FBX for Unity (plus icons) - in the background, with exactly
  the same pipeline and file names as ``python -m cubegen generate``

The add-on reuses the ``cubegen`` package: a copy inside the add-on (zip built
with ``tools/build_addon.py``) or, for development, the repository the add-on
folder lives in.
"""

bl_info = {
    "name": "Cube Escape Model Generator",
    "author": "cubegen",
    "version": (0, 2, 0),
    "blender": (3, 6, 0),
    "location": "3D Viewport > Sidebar (N) > Cube Escape",
    "description": "Seeded low-poly assets for Cube Escape: live preview, variant grid, FBX + icons for Unity",
    "category": "Add Mesh",
}

import importlib
import math
import os
import random
import sys
import threading
import traceback

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty


def _load_cubegen():
    try:
        from . import cubegen as pkg  # copy bundled into the add-on zip
    except ImportError:
        repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
        if os.path.isdir(os.path.join(repo, "cubegen")) and repo not in sys.path:
            sys.path.insert(0, repo)  # development: add-on folder symlinked from the repository
        import cubegen as pkg
    return {name: importlib.import_module(f"{pkg.__name__}.{name}")
            for name in ("models", "seeds", "pipeline", "bpy_builder")}, pkg.__version__


_CG, CUBEGEN_VERSION = _load_cubegen()
models, seeds, pipeline, builder = _CG["models"], _CG["seeds"], _CG["pipeline"], _CG["bpy_builder"]

PREVIEW_COLLECTION = "CubeEscape Vorschau"
GRID_COLLECTION = "CubeEscape Varianten"
DEFAULT_OUT = os.path.join(os.path.expanduser("~"), "CubeEscape_cubegen")

# Enum items must stay referenced while registered.
_TYPE_ITEMS = [
    (e.name, f"{e.title}", f"{e.description} ({e.category})")
    for e in sorted(models.REGISTRY.values(), key=lambda e: (e.category, e.name))
]
_INFO = {}  # last preview: shown in the panel


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _settings(context):
    return context.scene.cubegen


def _spec(s, variant=None, model_type=None):
    """(master seed, asset seed, asset name) - identical to the CLI's naming."""
    variant = s.variant if variant is None else variant
    model_type = model_type or s.model_type
    master = seeds.parse_seed(s.master_seed)
    seed = seeds.model_seed(master, model_type, variant)
    return master, seed, models.asset_name(model_type, variant, s.prefix)


def _all_types():
    """Every model type, in the order of the type menu (grouped by category)."""
    return [item[0] for item in _TYPE_ITEMS]


def _cli_command(s):
    seed = s.master_seed if s.master_seed.isdigit() else f'"{s.master_seed}"'
    cmd = f"python3 -m cubegen generate --seed {seed} --pick {s.model_type}:{s.variant}"
    return cmd + (f" --prefix {s.prefix}" if s.prefix else "")


def _tag_redraw(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _new_collection(context, name, parent=None):
    old = bpy.data.collections.get(name)
    if old is not None:
        builder.remove_collection(old)
    coll = bpy.data.collections.new(name)
    (parent.children if parent else context.scene.collection.children).link(coll)
    return coll


def _build(asset, coll, s, variant):
    model_type = asset.meta["type"]
    builder.build_collection(
        asset, coll, object_name=lambda part: f"{asset.name}.{part}",
        tags={"cubegen_type": model_type, "cubegen_seed": str(asset.meta["seed"])},
    )
    coll["cubegen_type"] = model_type
    coll["cubegen_variant"] = variant
    coll["cubegen_master_seed"] = s.master_seed


def rebuild_preview(context):
    s = _settings(context)
    builder.create_materials(overwrite=False)
    master, seed, name = _spec(s)
    asset = models.generate_asset(s.model_type, seed, name, s.scale)
    coll = _new_collection(context, PREVIEW_COLLECTION)
    _build(asset, coll, s, s.variant)
    stats = asset.stats()
    _INFO.clear()
    _INFO.update({
        "name": name, "seed": seed, "parts": stats["objects"], "tris": stats["triangles"],
        "dims": stats["dimensions_m"],
        "meta": {k: v for k, v in asset.meta.items() if k not in ("type", "seed") and not isinstance(v, (dict, list))},
    })


def build_grid(context, entries=None, columns=None):
    """Lay out variants behind the preview. ``entries`` = [(type, variant)], default: the grid settings."""
    s = _settings(context)
    builder.create_materials(overwrite=False)
    if entries is None:
        entries = [(s.model_type, v) for v in range(s.grid_start, s.grid_start + s.grid_count)]
    variants = [v for _, v in entries]
    assets = [models.generate_asset(t, _spec(s, v, t)[1], _spec(s, v, t)[2], s.scale) for t, v in entries]
    spacing = max(max(a.stats()["dimensions_m"][:2]) for a in assets) + 1.0
    cols = columns or math.ceil(math.sqrt(len(assets)))
    parent = _new_collection(context, GRID_COLLECTION)
    for k, (variant, asset) in enumerate(zip(variants, assets)):
        coll = bpy.data.collections.new(asset.name)
        parent.children.link(coll)
        _build(asset, coll, s, variant)
        # in the grid behind the preview (front is -Y), row by row
        offset = ((k % cols - (cols - 1) / 2) * spacing, spacing * (1 + k // cols), 0.0)
        for obj in coll.objects:
            if obj.parent is None:
                obj.location = tuple(obj.location[i] + offset[i] for i in range(3))
        curve = bpy.data.curves.new(f"{asset.name}.Label", "FONT")
        curve.body = asset.name
        curve.size = spacing * 0.07
        curve.align_x = "CENTER"
        label = bpy.data.objects.new(f"{asset.name}.Label", curve)
        label.location = (offset[0], offset[1] - spacing * 0.45, 0.01)
        coll.objects.link(label)


def all_type_entries(s):
    """One row per type: (type, variant) for variants grid_start .. grid_start + per_type - 1."""
    return [(t, v) for t in _all_types() for v in range(s.grid_start, s.grid_start + s.per_type)]


def selected_variants(context):
    """(master seed text, type, variant) of every grid / preview variant with a selected object."""
    picks = []
    roots = [bpy.data.collections.get(GRID_COLLECTION), bpy.data.collections.get(PREVIEW_COLLECTION)]
    for root in roots:
        if root is None:
            continue
        candidates = list(root.children) if root.name == GRID_COLLECTION else [root]
        for coll in candidates:
            if "cubegen_type" in coll and any(o.select_get() for o in coll.all_objects):
                pick = (coll["cubegen_master_seed"], coll["cubegen_type"], int(coll["cubegen_variant"]))
                if pick not in picks:
                    picks.append(pick)
    return picks


def make_configs(context, picks):
    """One BatchConfig per master seed (each writes its manifest to <out>/seed_<seed>)."""
    s = _settings(context)
    prefs = context.preferences.addons[__name__].preferences
    export_dir = bpy.path.abspath(s.export_dir).strip()
    if not export_dir:
        raise ValueError("Bitte zuerst einen Export-Ordner wählen")
    out_root = bpy.path.abspath(s.out_dir).strip() or DEFAULT_OUT
    formats = [f for f, on in (("fbx", s.fmt_fbx), ("glb", s.fmt_glb), ("obj", s.fmt_obj)) if on]
    if not formats:
        raise ValueError("Mindestens ein Format wählen")
    grouped = {}
    for master_text, model_type, variant in picks:
        grouped.setdefault(master_text, {}).setdefault(model_type, []).append(variant)
    configs = []
    for master_text, picked in grouped.items():
        master = seeds.parse_seed(master_text)
        configs.append(pipeline.BatchConfig(
            seed=master, models=picked, out_dir=os.path.join(out_root, f"seed_{master}"), formats=formats,
            prefix=s.prefix, scale=s.scale, blend=False, render=s.render_icons,
            models_dir=export_dir, icons_dir=bpy.path.abspath(s.icons_dir).strip() or None,
            library_dir=bpy.path.abspath(s.library_dir).strip() or None,
            blender=bpy.app.binary_path, magick=prefs.magick_path.strip() or None,
        ))
    return configs


# ---------------------------------------------------------------------------
# properties
# ---------------------------------------------------------------------------

def _on_change(self, context):
    if self.live and not self.running:
        try:
            rebuild_preview(context)
        except Exception:  # never break the UI because of a preview
            traceback.print_exc()


class CUBEGEN_Settings(bpy.types.PropertyGroup):
    model_type: EnumProperty(name="Typ", items=_TYPE_ITEMS, update=_on_change)
    master_seed: StringProperty(name="Master-Seed", default="42", update=_on_change,
                                description="Zahl oder Text, wie --seed auf der Kommandozeile")
    variant: IntProperty(name="Variante", default=0, min=0, max=9999, soft_max=99, update=_on_change,
                         description="Index der Variante (Crate_003 = Variante 3)")
    live: BoolProperty(name="Live-Vorschau", default=True, description="Vorschau bei jeder Änderung neu bauen")
    prefix: StringProperty(name="Präfix", default="Gen_", update=_on_change,
                           description="Vor den Asset-Namen, z. B. Gen_ -> Gen_Crate_003")
    scale: FloatProperty(name="Skalierung", default=1.0, min=0.01, soft_max=10.0, update=_on_change)

    grid_count: IntProperty(name="Anzahl", default=12, min=1, max=100)
    grid_start: IntProperty(name="Ab Variante", default=0, min=0, max=9999)
    per_type: IntProperty(name="Pro Typ", default=1, min=1, max=10,
                          description="Wie viele Varianten je Typ bei „Von jedem Typ“")

    export_dir: StringProperty(name="Modelle", subtype="DIR_PATH",
                               description="Mit Script: <Unity>/Assets/Art/Models · statische Deko: <Unity>/Assets/Art/Models/Library/<Kategorie>")
    library_dir: StringProperty(name="Bibliothek", subtype="DIR_PATH",
                                description="Optional: statische Deko (ohne Script) nach <Ordner>/<Kategorie>, "
                                            "z. B. <Unity>/Assets/Art/Models/Library. Leer = alles in „Modelle“")
    icons_dir: StringProperty(name="Icons", subtype="DIR_PATH",
                              description="Leer = Icons landen im Ausgabeordner")
    out_dir: StringProperty(name="Ausgabe", subtype="DIR_PATH",
                            description=f"Manifest, Previews, Kontaktbogen (leer = {DEFAULT_OUT})")
    fmt_fbx: BoolProperty(name="FBX", default=True)
    fmt_glb: BoolProperty(name="GLB", default=False)
    fmt_obj: BoolProperty(name="OBJ", default=False)
    render_icons: BoolProperty(name="Icons + Kontaktbogen", default=True,
                               description="Previews rendern und mit ImageMagick Icons erzeugen")

    running: BoolProperty(default=False)
    status: StringProperty(default="")


class CUBEGEN_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    magick_path: StringProperty(
        name="ImageMagick", subtype="FILE_PATH",
        description="Nur nötig, wenn ImageMagick nicht automatisch gefunden wird (z. B. /opt/homebrew/bin/magick)")

    def draw(self, context):
        self.layout.prop(self, "magick_path")
        self.layout.label(text=f"cubegen {CUBEGEN_VERSION}")


# ---------------------------------------------------------------------------
# operators
# ---------------------------------------------------------------------------

class CUBEGEN_OT_preview(bpy.types.Operator):
    bl_idname = "cubegen.preview"
    bl_label = "Vorschau erzeugen"
    bl_description = "Aktuelle Variante am Ursprung bauen"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        rebuild_preview(context)
        return {"FINISHED"}


class CUBEGEN_OT_step(bpy.types.Operator):
    bl_idname = "cubegen.step"
    bl_label = "Variante wechseln"
    bl_options = {"REGISTER", "UNDO"}

    delta: IntProperty(default=1)
    random: BoolProperty(default=False)

    @classmethod
    def description(cls, context, properties):
        if properties.random:
            return "Zufällige Variante"
        return "Nächste Variante" if properties.delta > 0 else "Vorherige Variante"

    def execute(self, context):
        s = _settings(context)
        s.variant = random.randint(0, 999) if self.random else max(0, s.variant + self.delta)
        if not s.live:
            rebuild_preview(context)
        return {"FINISHED"}


class CUBEGEN_OT_grid(bpy.types.Operator):
    bl_idname = "cubegen.grid"
    bl_label = "Raster erzeugen"
    bl_description = "Mehrere Varianten des Typs nebeneinander bauen - gute auswählen und exportieren"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        build_grid(context)
        s = _settings(context)
        self.report({"INFO"}, f"{s.grid_count} Varianten gebaut - gute auswählen, dann exportieren")
        return {"FINISHED"}


class CUBEGEN_OT_all_types(bpy.types.Operator):
    bl_idname = "cubegen.all_types"
    bl_label = "Von jedem Typ"
    bl_description = "Von jedem Modelltyp Varianten nebeneinander bauen (eine Reihe pro Typ)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = _settings(context)
        entries = all_type_entries(s)
        build_grid(context, entries, columns=s.per_type if s.per_type > 1 else 6)
        self.report({"INFO"}, f"{len(entries)} Modelle gebaut ({len(_all_types())} Typen × {s.per_type})")
        return {"FINISHED"}


class CUBEGEN_OT_use_active(bpy.types.Operator):
    bl_idname = "cubegen.use_active"
    bl_label = "Als Vorschau"
    bl_description = "Typ, Seed und Variante des aktiven Objekts übernehmen"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.active_object
        coll = next((c for c in obj.users_collection if "cubegen_type" in c), None)
        if coll is None:
            self.report({"WARNING"}, "Das aktive Objekt gehört zu keiner generierten Variante")
            return {"CANCELLED"}
        s = _settings(context)
        s.live = False
        s.model_type = coll["cubegen_type"]
        s.master_seed = coll["cubegen_master_seed"]
        s.variant = int(coll["cubegen_variant"])
        s.live = True
        rebuild_preview(context)
        return {"FINISHED"}


class CUBEGEN_OT_clear(bpy.types.Operator):
    bl_idname = "cubegen.clear"
    bl_label = "Aufräumen"
    bl_description = "Vorschau und Varianten-Raster entfernen"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        for name in (PREVIEW_COLLECTION, GRID_COLLECTION):
            coll = bpy.data.collections.get(name)
            if coll is not None:
                builder.remove_collection(coll)
        _INFO.clear()
        return {"FINISHED"}


class CUBEGEN_OT_copy_cli(bpy.types.Operator):
    bl_idname = "cubegen.copy_cli"
    bl_label = "CLI-Befehl kopieren"
    bl_description = "Den passenden Kommandozeilen-Befehl in die Zwischenablage kopieren"

    def execute(self, context):
        context.window_manager.clipboard = _cli_command(_settings(context))
        self.report({"INFO"}, "Befehl kopiert")
        return {"FINISHED"}


class CUBEGEN_OT_export(bpy.types.Operator):
    bl_idname = "cubegen.export"
    bl_label = "Exportieren"
    bl_description = "Als FBX (und Icons) exportieren - gleiche Pipeline wie die Kommandozeile"

    mode: EnumProperty(items=[
        ("PREVIEW", "Vorschau", "Die aktuelle Variante exportieren"),
        ("SELECTED", "Auswahl", "Alle Varianten exportieren, von denen ein Objekt ausgewählt ist"),
        ("ALL", "Alle Typen", "Von jedem Typ die Varianten aus „Pro Typ“ / „Ab Variante“ exportieren"),
    ], default="PREVIEW")

    _timer = None
    _thread = None

    @classmethod
    def poll(cls, context):
        return not context.scene.cubegen.running

    def _picks(self, context):
        s = _settings(context)
        if self.mode == "PREVIEW":
            return [(s.master_seed, s.model_type, s.variant)]
        if self.mode == "ALL":
            return [(s.master_seed, t, v) for t, v in all_type_entries(s)]
        return selected_variants(context)

    def execute(self, context):
        s = _settings(context)
        picks = self._picks(context)
        if not picks:
            self.report({"WARNING"}, "Keine Variante ausgewählt - Objekte im Raster anklicken")
            return {"CANCELLED"}
        try:
            configs = make_configs(context, picks)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self._lines, self._error, self._done = [], None, 0
        self._total = len(picks)

        def work():
            try:
                for cfg in configs:
                    pipeline.generate_batch(cfg, log=self._lines.append)
                    self._done += 1
            except Exception as exc:  # reported in modal()
                self._error = exc
                traceback.print_exc()

        if bpy.app.background:  # no event loop (tests, command line): run synchronously
            work()
            return self._finish(context)
        s.running, s.status = True, f"Export von {self._total} Asset(s) startet ..."
        self._thread = threading.Thread(target=work, daemon=True)
        self._thread.start()
        self._timer = context.window_manager.event_timer_add(0.3, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type != "TIMER":
            return {"PASS_THROUGH"}
        s = _settings(context)
        if self._lines:
            s.status = self._lines[-1][:90]
        _tag_redraw(context)
        if self._thread.is_alive():
            return {"PASS_THROUGH"}
        context.window_manager.event_timer_remove(self._timer)
        return self._finish(context)

    def _finish(self, context):
        s = _settings(context)
        s.running = False
        if self._error is not None:
            s.status = f"Fehler: {self._error}"[:120]
            self.report({"ERROR"}, f"Export fehlgeschlagen: {self._error}")
            return {"CANCELLED"}
        s.status = f"Fertig: {self._total} Asset(s) exportiert"
        self.report({"INFO"}, s.status)
        return {"FINISHED"}


class CUBEGEN_OT_open_folder(bpy.types.Operator):
    bl_idname = "cubegen.open_folder"
    bl_label = "Ordner öffnen"

    which: StringProperty(default="export_dir")

    def execute(self, context):
        s = _settings(context)
        path = bpy.path.abspath(getattr(s, self.which)).strip() or DEFAULT_OUT
        os.makedirs(path, exist_ok=True)
        bpy.ops.wm.path_open(filepath=path)
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# panels
# ---------------------------------------------------------------------------

class _Panel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cube Escape"


class CUBEGEN_PT_main(_Panel, bpy.types.Panel):
    bl_label = "Model Generator"

    def draw(self, context):
        s = _settings(context)
        layout = self.layout
        layout.prop(s, "model_type")
        layout.prop(s, "master_seed")
        row = layout.row(align=True)
        op = row.operator("cubegen.step", text="", icon="TRIA_LEFT")
        op.delta, op.random = -1, False
        row.prop(s, "variant")
        op = row.operator("cubegen.step", text="", icon="TRIA_RIGHT")
        op.delta, op.random = 1, False
        op = row.operator("cubegen.step", text="", icon="FILE_REFRESH")
        op.random = True
        row = layout.row(align=True)
        row.prop(s, "live")
        row.operator("cubegen.preview", icon="MESH_CUBE")

        _, seed, name = _spec(s)
        box = layout.box()
        box.label(text=f"{name}   (Seed {seed})", icon="OBJECT_DATA")
        if _INFO.get("name") == name:
            dims = " x ".join(f"{d:.2f}" for d in _INFO["dims"])
            box.label(text=f"{_INFO['tris']} Dreiecke · {dims} m")
            box.label(text="Teile: " + ", ".join(_INFO["parts"]))
            for key, value in list(_INFO["meta"].items())[:4]:
                box.label(text=f"{key}: {value}")
        row = layout.row(align=True)
        row.operator("cubegen.use_active", icon="EYEDROPPER")
        row.operator("cubegen.copy_cli", text="CLI", icon="COPYDOWN")


class CUBEGEN_PT_grid(_Panel, bpy.types.Panel):
    bl_label = "Varianten-Raster"
    bl_parent_id = "CUBEGEN_PT_main"

    def draw(self, context):
        s = _settings(context)
        layout = self.layout
        row = layout.row(align=True)
        row.prop(s, "grid_count")
        row.prop(s, "grid_start")
        row = layout.row(align=True)
        row.operator("cubegen.grid", icon="GRID")
        row.operator("cubegen.clear", icon="TRASH")
        layout.separator()
        row = layout.row(align=True)
        row.prop(s, "per_type")
        row.operator("cubegen.all_types", text=f"Von jedem Typ ({len(_all_types())} × {s.per_type})",
                     icon="MOD_ARRAY")
        layout.label(text="Gute Varianten im Viewport anklicken (Shift = mehrere)", icon="INFO")


class CUBEGEN_PT_export(_Panel, bpy.types.Panel):
    bl_label = "Export für Unity"
    bl_parent_id = "CUBEGEN_PT_main"

    def draw(self, context):
        s = _settings(context)
        layout = self.layout
        col = layout.column(align=True)
        col.prop(s, "export_dir")
        col.prop(s, "library_dir")
        col.prop(s, "icons_dir")
        col.prop(s, "out_dir")
        row = layout.row(align=True)
        row.prop(s, "prefix")
        row.prop(s, "scale")
        row = layout.row(align=True)
        row.prop(s, "fmt_fbx", toggle=True)
        row.prop(s, "fmt_glb", toggle=True)
        row.prop(s, "fmt_obj", toggle=True)
        layout.prop(s, "render_icons")
        col = layout.column(align=True)
        col.enabled = not s.running
        col.scale_y = 1.3
        col.operator("cubegen.export", text="Vorschau exportieren", icon="EXPORT").mode = "PREVIEW"
        n = len(selected_variants(context))
        op = col.operator("cubegen.export", text=f"Auswahl exportieren ({n})", icon="EXPORT")
        op.mode = "SELECTED"
        total = len(_all_types()) * s.per_type
        op = col.operator("cubegen.export", text=f"Alle Typen exportieren ({total})", icon="EXPORT")
        op.mode = "ALL"
        if s.status:
            layout.label(text=s.status, icon="TIME" if s.running else "CHECKMARK")
        row = layout.row(align=True)
        row.operator("cubegen.open_folder", text="Modelle", icon="FILE_FOLDER").which = "export_dir"
        row.operator("cubegen.open_folder", text="Ausgabe", icon="FILE_FOLDER").which = "out_dir"


CLASSES = (
    CUBEGEN_Settings, CUBEGEN_Preferences,
    CUBEGEN_OT_preview, CUBEGEN_OT_step, CUBEGEN_OT_grid, CUBEGEN_OT_all_types, CUBEGEN_OT_use_active,
    CUBEGEN_OT_clear,
    CUBEGEN_OT_copy_cli, CUBEGEN_OT_export, CUBEGEN_OT_open_folder,
    CUBEGEN_PT_main, CUBEGEN_PT_grid, CUBEGEN_PT_export,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cubegen = PointerProperty(type=CUBEGEN_Settings)


def unregister():
    del bpy.types.Scene.cubegen
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
