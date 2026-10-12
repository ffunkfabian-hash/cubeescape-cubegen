"""A small desktop front end for the cubegen command line."""

from __future__ import annotations

import json
import math
import os
import queue
import subprocess
import sys
import tempfile
import threading
from typing import Optional

from . import __version__
from .paint import paint_names
from .palette import palette_names

#: the texture modes the GUI offers (label, value of --textures); "none" keeps the game's one-colour M_ materials
TEXTURE_CHOICES = [("Keine (einfarbige Spielmaterialien)", "none"), ("Kacheln (tiled)", "tiled"),
                   ("Kacheln + Gebrauchsspuren (baked)", "baked"), ("Farbpalette (palette)", "palette")]
TEXTURE_SIZES = ["256", "512", "1024", "2048"]


def texture_args(textures: str, size: str = "", palette: str = "") -> list:
    """The --textures/--texture-size/--palette arguments for the GUI's choice; none = no arguments at all."""
    textures = (textures or "none").strip()
    if textures not in [value for _, value in TEXTURE_CHOICES]:
        raise ValueError(f"Unbekannte Texturart: {textures}")
    if textures == "none":
        return []
    args = ["--textures", textures]
    size = (size or "").strip()
    if size:
        if not size.isdigit() or int(size) < 16:
            raise ValueError("Die Texturgröße muss eine ganze Zahl in Pixeln sein (mindestens 16).")
        args.extend(["--texture-size", size])
    palette = (palette or "").strip()
    if textures == "palette" and palette:
        if palette not in palette_names():
            raise ValueError(f"Unbekannte Farbpalette: {palette}")
        args.extend(["--palette", palette])
    return args


def _load_obj_preview(path: str):
    """Read generated OBJ geometry and its material colours for the GUI's lightweight 3D view."""
    vertices = []
    faces = []
    materials = {}
    current_material = "M_Metal"
    current_object_visible = True
    material_path = None

    with open(path, "r", encoding="utf-8") as obj_file:
        for line in obj_file:
            fields = line.split()
            if not fields:
                continue
            if fields[0] == "mtllib" and len(fields) > 1:
                material_path = os.path.join(os.path.dirname(path), " ".join(fields[1:]))
            elif fields[0] == "o":
                current_object_visible = not fields[1].endswith("_LOD1") if len(fields) > 1 else True
            elif fields[0] == "usemtl" and len(fields) > 1:
                current_material = fields[1]
            elif fields[0] == "v" and len(fields) >= 4:
                vertices.append(tuple(float(value) for value in fields[1:4]))
            elif fields[0] == "f" and current_object_visible and len(fields) >= 4:
                indices = []
                for value in fields[1:]:
                    index = int(value.split("/", 1)[0])
                    indices.append(index - 1 if index > 0 else len(vertices) + index)
                faces.append((tuple(indices), current_material))

    if material_path and os.path.isfile(material_path):
        current = None
        with open(material_path, "r", encoding="utf-8") as mtl_file:
            for line in mtl_file:
                fields = line.split()
                if fields and fields[0] == "newmtl" and len(fields) > 1:
                    current = fields[1]
                elif fields and fields[0] == "Kd" and current and len(fields) >= 4:
                    linear = tuple(float(value) for value in fields[1:4])
                    srgb = tuple(round(255 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055))
                                 for c in linear)
                    materials[current] = "#%02x%02x%02x" % srgb

    if not vertices or not faces:
        raise ValueError(f"Die OBJ-Datei enthält keine darstellbare Geometrie: {path}")
    return vertices, faces, materials


def main() -> int:
    """Open the desktop GUI. Tkinter is loaded only when the GUI is requested."""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError as exc:
        raise ValueError("Tkinter is not available in this Python installation") from exc

    from .models import model_types

    class CubegenGUI:
        def __init__(self, root):
            self.root = root
            self.root.title(f"Cube Escape Model Generator {__version__}")
            screen_width, screen_height = root.winfo_screenwidth(), root.winfo_screenheight()
            window_width = max(900, min(1500, screen_width - 60))
            window_height = max(650, min(1100, screen_height - 100))
            self.root.geometry(f"{window_width}x{window_height}")
            self.root.minsize(900, 650)
            self.events = queue.Queue()
            self.process: Optional[subprocess.Popen] = None
            self.report_path: Optional[str] = None
            self.generated_models = {}
            self.preview_window = None
            self.preview_source = None
            self.preview_image = None
            self.viewer_geometry = None
            self.viewer_rotation = [0.7, 0.35]
            self.viewer_zoom = 1.0
            self.viewer_drag = None
            self.last_output = None

            self.filter_text = tk.StringVar()
            self.seed = tk.StringVar()
            self.count = tk.StringVar(value="4")
            self.output = tk.StringVar(value=os.path.abspath(os.path.join("output", "gui")))
            self.recipe = tk.StringVar()
            self.unique = tk.BooleanVar(value=True)
            self.variant_set = tk.BooleanVar(value=False)
            self.strict = tk.BooleanVar(value=False)
            self.force = tk.BooleanVar(value=False)
            self.no_blender = tk.BooleanVar(value=False)
            self.textures = tk.StringVar(value=TEXTURE_CHOICES[0][0])
            self.texture_size = tk.StringVar(value="512")
            self.palette = tk.StringVar(value="")
            self.paint = tk.StringVar(value="")
            self.paint_file = tk.StringVar(value="")

            root.columnconfigure(0, weight=1)
            root.rowconfigure(1, weight=1)
            header = ttk.Frame(root, padding=(12, 10))
            header.grid(row=0, column=0, sticky="ew")
            ttk.Label(header, text="Cube Escape Model Generator", font=("TkDefaultFont", 16, "bold")).pack(
                side="left")
            ttk.Label(header, text=f"Version {__version__}").pack(side="right")

            selection = ttk.LabelFrame(root, text="Modelltypen", padding=8)
            selection.grid(row=1, column=0, padx=12, pady=4, sticky="nsew")
            selection.columnconfigure(0, weight=1)
            selection.rowconfigure(1, weight=1)
            search_row = ttk.Frame(selection)
            search_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
            ttk.Label(search_row, text="Filter:").pack(side="left")
            search = ttk.Entry(search_row, textvariable=self.filter_text)
            search.pack(side="left", fill="x", expand=True, padx=(6, 12))
            ttk.Button(search_row, text="Alle", command=self.select_all).pack(side="left", padx=2)
            ttk.Button(search_row, text="Keine", command=self.select_none).pack(side="left", padx=2)
            self.type_list = tk.Listbox(selection, selectmode=tk.EXTENDED, height=12, exportselection=False)
            self.type_list.grid(row=1, column=0, sticky="nsew")
            scrollbar = ttk.Scrollbar(selection, orient="vertical", command=self.type_list.yview)
            scrollbar.grid(row=1, column=1, sticky="ns")
            self.type_list.configure(yscrollcommand=scrollbar.set)
            self.all_types = sorted(model_types())
            self.filtered_types = list(self.all_types)
            self.refresh_types()
            self.filter_text.trace_add("write", lambda *_: self.refresh_types())

            settings = ttk.LabelFrame(root, text="Build", padding=8)
            settings.grid(row=2, column=0, padx=12, pady=4, sticky="ew")
            settings.columnconfigure(1, weight=1)
            ttk.Label(settings, text="Seed (leer = zufällig):").grid(row=0, column=0, sticky="w", padx=4, pady=3)
            ttk.Entry(settings, textvariable=self.seed, width=24).grid(row=0, column=1, sticky="w", padx=4, pady=3)
            ttk.Label(settings, text="Varianten pro Typ:").grid(row=0, column=2, sticky="w", padx=4, pady=3)
            ttk.Entry(settings, textvariable=self.count, width=8).grid(row=0, column=3, sticky="w", padx=4, pady=3)
            ttk.Label(settings, text="Ausgabeordner:").grid(row=1, column=0, sticky="w", padx=4, pady=3)
            ttk.Entry(settings, textvariable=self.output).grid(row=1, column=1, columnspan=2, sticky="ew", padx=4,
                                                               pady=3)
            ttk.Button(settings, text="Ordner wählen…", command=self.choose_output).grid(row=1, column=3, padx=4,
                                                                                        pady=3)
            ttk.Label(settings, text="Rezept (optional):").grid(row=2, column=0, sticky="w", padx=4, pady=3)
            ttk.Entry(settings, textvariable=self.recipe).grid(row=2, column=1, columnspan=2, sticky="ew", padx=4,
                                                               pady=3)
            ttk.Button(settings, text="Datei wählen…", command=self.choose_recipe).grid(row=2, column=3, padx=4,
                                                                                       pady=3)

            # Textures (0.13): the same modes as --textures; ImageMagick paints them (cubegen doctor shows whether it is found)
            ttk.Label(settings, text="Texturen:").grid(row=3, column=0, sticky="w", padx=4, pady=3)
            texture_box = ttk.Combobox(settings, textvariable=self.textures, state="readonly", width=34,
                                       values=[label for label, _ in TEXTURE_CHOICES])
            texture_box.grid(row=3, column=1, sticky="w", padx=4, pady=3)
            ttk.Label(settings, text="Texturgröße (px):").grid(row=3, column=2, sticky="w", padx=4, pady=3)
            self.size_box = ttk.Combobox(settings, textvariable=self.texture_size, values=TEXTURE_SIZES, width=8)
            self.size_box.grid(row=3, column=3, sticky="w", padx=4, pady=3)
            ttk.Label(settings, text="Farbpalette:").grid(row=4, column=0, sticky="w", padx=4, pady=3)
            self.palette_box = ttk.Combobox(settings, textvariable=self.palette, state="readonly", width=24,
                                            values=[""] + palette_names())
            self.palette_box.grid(row=4, column=1, sticky="w", padx=4, pady=3)
            ttk.Label(settings, text="Anstrich:").grid(row=4, column=2, sticky="w", padx=4, pady=3)
            ttk.Combobox(settings, textvariable=self.paint, state="readonly", width=14,
                         values=[""] + paint_names()).grid(row=4, column=3, sticky="w", padx=4, pady=3)
            ttk.Label(settings, text="Eigenes Thema:").grid(row=5, column=0, sticky="w", padx=4, pady=3)
            paint_file_row = ttk.Frame(settings)
            paint_file_row.grid(row=5, column=1, sticky="w", padx=4, pady=3)
            ttk.Entry(paint_file_row, textvariable=self.paint_file, width=28).pack(side="left")
            ttk.Button(paint_file_row, text="…", width=2, command=self.choose_paint_file).pack(side="left", padx=2)
            ttk.Label(settings, text="Texturen brauchen ImageMagick; ohne Textur bleiben die Spielmaterialien M_….",
                      foreground="#667").grid(row=5, column=2, columnspan=2, sticky="w", padx=4, pady=3)
            self.textures.trace_add("write", lambda *_: self.update_texture_fields())
            self.update_texture_fields()

            options = ttk.Frame(root, padding=(12, 4))
            options.grid(row=3, column=0, sticky="ew")
            ttk.Checkbutton(options, text="Ähnliche Varianten überspringen", variable=self.unique).pack(side="left")
            ttk.Checkbutton(options, text="Variantenset (gleiche Außenmaße)", variable=self.variant_set).pack(
                side="left", padx=10)
            ttk.Checkbutton(options, text="Strikte Qualitätsprüfung", variable=self.strict).pack(side="left", padx=10)
            ttk.Checkbutton(options, text="Alles neu bauen", variable=self.force).pack(side="left", padx=10)
            ttk.Checkbutton(options, text="Nur OBJ (ohne Blender)", variable=self.no_blender).pack(side="left")

            actions = ttk.Frame(root, padding=(12, 4))
            actions.grid(row=4, column=0, sticky="ew")
            self.validate_button = ttk.Button(actions, text="Vorab prüfen", command=self.start_validation)
            self.validate_button.pack(side="left")
            self.generate_button = ttk.Button(actions, text="Assets erzeugen", command=self.start_generation)
            self.generate_button.pack(side="left", padx=8)
            self.stop_button = ttk.Button(actions, text="Abbrechen", command=self.stop, state="disabled")
            self.stop_button.pack(side="left")
            ttk.Button(actions, text="Modellvorschau öffnen", command=self.open_preview_window).pack(side="left",
                                                                                                   padx=8)
            self.status = tk.StringVar(value="Bereit")
            ttk.Label(actions, textvariable=self.status).pack(side="right")

            output_frame = ttk.LabelFrame(root, text="Ausgabe", padding=6)
            output_frame.grid(row=5, column=0, padx=12, pady=(4, 12), sticky="nsew")
            root.rowconfigure(5, weight=1)
            output_frame.columnconfigure(0, weight=1)
            output_frame.rowconfigure(0, weight=1)
            self.log = tk.Text(output_frame, height=12, wrap="word", state="disabled")
            self.log.grid(row=0, column=0, sticky="nsew")
            log_scroll = ttk.Scrollbar(output_frame, orient="vertical", command=self.log.yview)
            log_scroll.grid(row=0, column=1, sticky="ns")
            self.log.configure(yscrollcommand=log_scroll.set)

            root.protocol("WM_DELETE_WINDOW", self.close)
            self.poll_events()

        def open_preview_window(self):
            if self.preview_window is not None and self.preview_window.winfo_exists():
                self.preview_window.deiconify()
                self.preview_window.lift()
                return

            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            width = max(800, min(1500, screen_width - 60))
            height = max(500, min(950, screen_height - 100))
            self.preview_window = tk.Toplevel(self.root)
            self.preview_window.title(f"Modellvorschau – {__version__}")
            self.preview_window.geometry(f"{width}x{height}")
            self.preview_window.minsize(800, 500)
            self.preview_window.columnconfigure(0, weight=1)
            self.preview_window.rowconfigure(0, weight=1)
            self.preview_window.protocol("WM_DELETE_WINDOW", self.preview_window.withdraw)

            preview_frame = ttk.Frame(self.preview_window, padding=10)
            preview_frame.grid(row=0, column=0, sticky="nsew")
            preview_frame.columnconfigure(0, weight=1)
            preview_frame.columnconfigure(1, weight=1)
            preview_frame.rowconfigure(1, weight=1)
            preview_controls = ttk.Frame(preview_frame)
            preview_controls.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
            ttk.Label(preview_controls, text="Modell:").pack(side="left")
            self.preview_model = tk.StringVar()
            self.preview_select = ttk.Combobox(preview_controls, textvariable=self.preview_model, state="readonly")
            self.preview_select.pack(side="left", fill="x", expand=True, padx=8)
            self.preview_select.bind("<<ComboboxSelected>>", self.show_model_preview)
            ttk.Label(preview_controls, text="3D: ziehen zum Drehen, Mausrad zum Zoomen").pack(side="right")
            ttk.Label(preview_frame, text="Gerenderte Vorschau").grid(row=1, column=0, sticky="w")
            ttk.Label(preview_frame, text="Interaktive 3D-Ansicht").grid(row=1, column=1, sticky="w")
            self.image_canvas = tk.Canvas(preview_frame, background="#f1f1f1", highlightthickness=0)
            self.image_canvas.grid(row=2, column=0, sticky="nsew", padx=(0, 6))
            self.model_canvas = tk.Canvas(preview_frame, background="#202630", highlightthickness=0)
            self.model_canvas.grid(row=2, column=1, sticky="nsew", padx=(6, 0))
            preview_frame.rowconfigure(2, weight=1)
            self.image_canvas.bind("<Configure>", self.show_rendered_image)
            self.model_canvas.bind("<Configure>", self.draw_model)
            self.model_canvas.bind("<ButtonPress-1>", self.start_viewer_drag)
            self.model_canvas.bind("<B1-Motion>", self.drag_viewer)
            self.model_canvas.bind("<MouseWheel>", self.zoom_viewer)
            self.model_canvas.bind("<Button-4>", lambda _event: self.change_zoom(1.1))
            self.model_canvas.bind("<Button-5>", lambda _event: self.change_zoom(1 / 1.1))
            self.image_canvas.create_text(12, 12, anchor="nw", text="Nach dem Erzeugen erscheinen hier die Modelle.")
            self.model_canvas.create_text(12, 12, anchor="nw", fill="white",
                                          text="Nach dem Erzeugen erscheinen hier die Modelle.")

        def refresh_types(self):
            query = self.filter_text.get().strip().lower()
            selected = {self.filtered_types[i] for i in self.type_list.curselection()}
            self.filtered_types = [name for name in self.all_types if query in name.lower()]
            self.type_list.delete(0, tk.END)
            for index, name in enumerate(self.filtered_types):
                self.type_list.insert(tk.END, name)
                if name in selected:
                    self.type_list.selection_set(index)

        def select_all(self):
            self.type_list.selection_set(0, tk.END)

        def select_none(self):
            self.type_list.selection_clear(0, tk.END)

        def choose_output(self):
            selected = filedialog.askdirectory(initialdir=self.output.get() or os.getcwd())
            if selected:
                self.output.set(selected)

        def choose_recipe(self):
            selected = filedialog.askopenfilename(
                filetypes=[("Cubegen-Rezepte", "*.json"), ("Alle Dateien", "*")])
            if selected:
                self.recipe.set(selected)

        def choose_paint_file(self):
            selected = filedialog.askopenfilename(
                filetypes=[("Anstrich (JSON)", "*.json"), ("Alle Dateien", "*")])
            if selected:
                self.paint_file.set(selected)

        def texture_value(self) -> str:
            return dict(TEXTURE_CHOICES).get(self.textures.get(), "none")

        def update_texture_fields(self):
            mode = self.texture_value()
            self.size_box.configure(state="normal" if mode != "none" else "disabled")
            self.palette_box.configure(state="readonly" if mode == "palette" else "disabled")

        def command(self, validate: bool):
            recipe = self.recipe.get().strip()
            selected = [self.filtered_types[i] for i in self.type_list.curselection()]
            if not recipe and not selected:
                raise ValueError("Wähle mindestens einen Modelltyp oder ein Rezept aus.")
            try:
                count = int(self.count.get())
            except ValueError as exc:
                raise ValueError("Die Variantenanzahl muss eine ganze Zahl sein.") from exc
            if count < 1:
                raise ValueError("Die Variantenanzahl muss mindestens 1 sein.")
            output = self.output.get().strip()
            if not output:
                raise ValueError("Bitte gib einen Ausgabeordner an.")

            args = [sys.executable, "-m", "cubegen", "generate"]
            if recipe:
                args.extend(["--recipe", recipe])
            else:
                args.extend(["--types", ",".join(selected), "--count", str(count)])
            if self.seed.get().strip():
                args.extend(["--seed", self.seed.get().strip()])
            args.extend(["--out", os.path.abspath(output)])
            if self.paint_file.get().strip():  # an own scheme from a file wins over the list
                size = self.texture_size.get().strip()
                args.extend(["--paint-file", os.path.abspath(self.paint_file.get().strip())]
                            + (["--texture-size", size] if size else []))
            elif self.paint.get():  # a paint scheme is a baked atlas: --paint implies --textures baked
                size = self.texture_size.get().strip()
                args.extend(["--paint", self.paint.get()] + (["--texture-size", size] if size else []))
            else:
                args.extend(texture_args(self.texture_value(), self.texture_size.get(), self.palette.get()))
            if self.variant_set.get() and not recipe:
                args.append("--set")
            if self.unique.get():
                args.append("--unique")
            if self.strict.get():
                args.append("--strict")
            if self.force.get() and not validate:
                args.append("--force")
            if self.no_blender.get() and not validate:
                args.append("--no-blender")
            elif not validate:
                args.extend(["--formats", "fbx,obj"])
            if validate:
                descriptor, self.report_path = tempfile.mkstemp(prefix="cubegen-validation-", suffix=".json")
                os.close(descriptor)
                args.extend(["--validate-only", "--report", self.report_path])
            return args

        def start_validation(self):
            self.start(validate=True)

        def start_generation(self):
            self.start(validate=False)

        def start(self, validate: bool):
            if self.process:
                return
            try:
                args = self.command(validate)
                if not validate:
                    self.last_output = os.path.abspath(self.output.get().strip())
                self.process = subprocess.Popen(
                    args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", bufsize=1)
            except (OSError, ValueError) as exc:
                self.append(f"Fehler: {exc}")
                messagebox.showerror("Cubegen", str(exc))
                self.cleanup_report()
                return
            self.status.set("Vorabprüfung läuft…" if validate else "Export läuft…")
            self.set_busy(True)
            threading.Thread(target=self.read_process, daemon=True).start()

        def read_process(self):
            process = self.process
            if process is None:
                return
            assert process.stdout is not None
            for line in process.stdout:
                self.events.put(("line", line.rstrip()))
            self.events.put(("done", process.wait()))

        def poll_events(self):
            try:
                while True:
                    event, value = self.events.get_nowait()
                    if event == "line":
                        self.append(value)
                    else:
                        self.finish(value)
            except queue.Empty:
                pass
            self.root.after(100, self.poll_events)

        def finish(self, return_code: int):
            report_path = self.report_path
            self.process = None
            self.set_busy(False)
            self.status.set("Fertig" if return_code == 0 else f"Beendet mit Status {return_code}")
            if return_code == 0 and report_path is None:
                self.load_generated_models()
            if report_path and os.path.isfile(report_path):
                try:
                    with open(report_path, "r", encoding="utf-8") as report_file:
                        report = json.load(report_file)
                    ranked = sorted(report.get("assets", []),
                                    key=lambda row: (-row.get("quality_score", 0), row.get("type", ""),
                                                     row.get("name", "")))
                    if ranked:
                        self.append("Qualitätsranking (höchste Punktzahl zuerst):")
                        for row in ranked:
                            suffix = f" — ähnlich zu {row['similar_to']}" if row.get("similar_to") else ""
                            quality = row.get("quality", {})
                            self.append(f"  {row['type']} #{row.get('quality_rank', '?')} {row['name']}: "
                                        f"{row.get('quality_score', 0)}/100, {row['severity']}, "
                                        f"{quality.get('triangles', '?')} Tris{suffix}")
                except (OSError, ValueError, TypeError) as exc:
                    self.append(f"Validierungsreport konnte nicht gelesen werden: {exc}")
            self.cleanup_report()

        def load_generated_models(self):
            manifest_path = os.path.join(self.last_output or "", "manifest.json")
            try:
                with open(manifest_path, "r", encoding="utf-8") as manifest_file:
                    manifest = json.load(manifest_file)
                self.generated_models = {
                    entry["name"]: entry for entry in manifest.get("models", [])
                    if isinstance(entry, dict) and entry.get("name")
                }
            except (OSError, ValueError, TypeError, KeyError) as exc:
                self.append(f"Modellvorschau konnte das Build-Manifest nicht laden: {exc}")
                return
            names = list(self.generated_models)
            self.open_preview_window()
            self.preview_select.configure(values=names)
            if names:
                self.preview_model.set(names[0])
                self.show_model_preview()
            else:
                self.preview_model.set("")
                self.viewer_geometry = None
                self.image_canvas.delete("all")
                self.model_canvas.delete("all")
                self.image_canvas.create_text(12, 12, anchor="nw", text="Keine Modelle im Manifest gefunden.")
                self.model_canvas.create_text(12, 12, anchor="nw", fill="white",
                                              text="Keine Modelle im Manifest gefunden.")

        def show_model_preview(self, _event=None):
            name = self.preview_model.get()
            entry = self.generated_models.get(name)
            if not entry:
                return
            self.preview_image = None
            self.preview_source = None
            self.image_canvas.delete("all")
            preview_path = entry.get("preview")
            if preview_path:
                try:
                    self.preview_source = tk.PhotoImage(file=os.path.join(self.last_output, preview_path))
                    self.show_rendered_image()
                except (OSError, tk.TclError) as exc:
                    self.image_canvas.create_text(12, 12, anchor="nw",
                                                  text=f"Gerenderte Vorschau nicht verfügbar:\n{exc}")
            else:
                self.image_canvas.create_text(12, 12, anchor="nw",
                                              text="Kein Render vorhanden (Blender-Export erforderlich).")

            obj_path = entry.get("files", {}).get("obj")
            if not obj_path:
                self.viewer_geometry = None
                self.model_canvas.delete("all")
                self.model_canvas.create_text(12, 12, anchor="nw", fill="white",
                                              text="Kein OBJ für die 3D-Ansicht vorhanden.")
                return
            try:
                self.viewer_geometry = _load_obj_preview(os.path.join(self.last_output, obj_path))
                self.viewer_rotation = [0.7, 0.35]
                self.viewer_zoom = 1.0
                self.draw_model()
            except (OSError, ValueError, IndexError) as exc:
                self.viewer_geometry = None
                self.model_canvas.delete("all")
                self.model_canvas.create_text(12, 12, anchor="nw", fill="white",
                                              text=f"3D-Modell konnte nicht geladen werden:\n{exc}")

        def show_rendered_image(self, _event=None):
            self.image_canvas.delete("all")
            if self.preview_source is None:
                return
            width, height = self.image_canvas.winfo_width(), self.image_canvas.winfo_height()
            source_width, source_height = self.preview_source.width(), self.preview_source.height()
            target_scale = min(max(width - 24, 1) / source_width, max(height - 24, 1) / source_height)
            scale_num, scale_den = 1, 1
            for numerator in range(1, 7):
                for denominator in range(1, 7):
                    factor = numerator / denominator
                    if math.gcd(numerator, denominator) == 1 and scale_num / scale_den < factor <= target_scale:
                        scale_num, scale_den = numerator, denominator
            image = self.preview_source
            if scale_num > 1:
                image = image.zoom(scale_num, scale_num)
            if scale_den > 1:
                image = image.subsample(scale_den, scale_den)
            self.preview_image = image
            self.image_canvas.create_image(width // 2, height // 2, image=image, anchor="center")

        def start_viewer_drag(self, event):
            self.viewer_drag = (event.x, event.y)

        def drag_viewer(self, event):
            if self.viewer_drag is None:
                return
            last_x, last_y = self.viewer_drag
            self.viewer_rotation[0] += (event.x - last_x) * 0.01
            self.viewer_rotation[1] = max(-1.45, min(1.45, self.viewer_rotation[1] + (event.y - last_y) * 0.01))
            self.viewer_drag = (event.x, event.y)
            self.draw_model()

        def zoom_viewer(self, event):
            self.change_zoom(1.1 if event.delta > 0 else 1 / 1.1)

        def change_zoom(self, factor: float):
            self.viewer_zoom = max(0.25, min(5.0, self.viewer_zoom * factor))
            self.draw_model()

        def draw_model(self, _event=None):
            self.model_canvas.delete("all")
            if not self.viewer_geometry:
                return
            vertices, faces, materials = self.viewer_geometry
            width, height = self.model_canvas.winfo_width(), self.model_canvas.winfo_height()
            if width < 2 or height < 2:
                return
            center = [sum(vertex[axis] for vertex in vertices) / len(vertices) for axis in range(3)]
            azimuth, elevation = self.viewer_rotation
            ca, sa = math.cos(azimuth), math.sin(azimuth)
            ce, se = math.cos(elevation), math.sin(elevation)
            rotated = []
            for vertex in vertices:
                x, y, z = (vertex[i] - center[i] for i in range(3))
                x, z = x * ca + z * sa, -x * sa + z * ca
                rotated.append((x, y * ce - z * se, y * se + z * ce))
            min_x, max_x = min(v[0] for v in rotated), max(v[0] for v in rotated)
            min_y, max_y = min(v[1] for v in rotated), max(v[1] for v in rotated)
            span = max(max_x - min_x, max_y - min_y, 1e-6)
            scale = min(max(width - 36, 1), max(height - 36, 1)) / span * self.viewer_zoom
            projected = [(width / 2 + v[0] * scale, height / 2 - v[1] * scale, v[2]) for v in rotated]

            draw_faces = []
            for indices, material in faces:
                points = [projected[index] for index in indices]
                p0, p1, p2 = (rotated[index] for index in indices[:3])
                u = tuple(p1[i] - p0[i] for i in range(3))
                v = tuple(p2[i] - p0[i] for i in range(3))
                normal = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
                          u[0] * v[1] - u[1] * v[0])
                length = math.sqrt(sum(component * component for component in normal)) or 1.0
                light = max(0.0, (normal[0] * 0.35 + normal[1] * 0.45 + normal[2] * 0.82) / length)
                shade = 0.35 + 0.65 * light
                base = materials.get(material, "#9aa5b1")
                rgb = tuple(int(base[offset:offset + 2], 16) for offset in (1, 3, 5))
                fill = "#%02x%02x%02x" % tuple(min(255, round(channel * shade)) for channel in rgb)
                draw_faces.append((sum(point[2] for point in points) / len(points), points, fill))
            for _depth, points, fill in sorted(draw_faces, key=lambda item: item[0]):
                self.model_canvas.create_polygon(
                    [coordinate for point in points for coordinate in point[:2]], fill=fill, outline="#111820")

        def cleanup_report(self):
            if self.report_path:
                try:
                    os.unlink(self.report_path)
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    self.append(f"Temporärer Report konnte nicht entfernt werden: {exc}")
                self.report_path = None

        def set_busy(self, busy: bool):
            state = "disabled" if busy else "normal"
            self.validate_button.configure(state=state)
            self.generate_button.configure(state=state)
            self.stop_button.configure(state="normal" if busy else "disabled")

        def stop(self):
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.status.set("Abbruch angefordert…")

        def append(self, text: str):
            self.log.configure(state="normal")
            self.log.insert(tk.END, text + "\n")
            self.log.see(tk.END)
            self.log.configure(state="disabled")

        def close(self):
            if self.process and self.process.poll() is None:
                self.process.terminate()
            self.cleanup_report()
            self.root.destroy()

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise ValueError(f"could not open the desktop GUI: {exc}") from exc
    CubegenGUI(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
