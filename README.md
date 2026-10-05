# Cube Escape – Model Generator Seed (`cubegen`)

Seed-basierter Low-Poly-Asset-Generator für **Cube Escape**. Ein *Master-Seed* erzeugt reproduzierbar ganze Batches
von Varianten im Stil der Station – Kisten, Kanister, Tanks, Rohre, Maschinen, Generatoren, Konsolen, Terminals,
Server-Racks, Lampen, Kristalle, Trümmer, Türen, Plattformen, Wände, Säulen, Lüftungen und Inventar-Items.

* **Blender CLI** baut die Meshes, exportiert **FBX für Unity** (optional GLB/glTF/OBJ), rendert Previews und
  speichert eine Übersichts-`.blend`.
* **ImageMagick** macht daraus **Inventar-Icons** (`Icon_<Name>.png`), einen **Kontaktbogen** zum Durchsehen und eine
  Material-Übersicht.

![Beispiel: Seed 42, zwei Varianten pro Typ](docs/example_seed_42.png)

## Kompatibel mit `generate_assets.py` des Spiels

Der Generator hält sich an dieselben Konventionen wie `Blender/Scripts/generate_assets.py`:

| Konvention | Umsetzung |
|---|---|
| 1 Blender-Einheit = 1 m, Z oben | ja |
| Front schaut nach **−Y** (Unity: +Z) | Bildschirme, Leitern, Ventile, Türfronten … zeigen nach −Y; 8-/10-/12-eckige Zylinder drehen eine flache Seite nach vorn (`align_flat`) |
| Pivot unten mittig | `floor`-Typen; Plattformen: begehbare Oberkante bei z = 0 (`top`); Items: Pivot in der Mitte (`center`); Wandmontiertes: Pivot am Boden darunter (`wall`) |
| Objekte haben nur eine Location | Rotation 0 / Skalierung 1, alles ist ins Mesh gebacken |
| Materialnamen = Unity-Materialien | exakt die `M_…`-Tabelle (`M_Wall`, `M_RobotDark`, `M_GlowCyan`, …) → Unity remappt automatisch |
| FBX-Exporteinstellungen | identisch zu `export_fbx()` (`bake_space_transform`, `axis_forward=-Z`, `axis_up=Y`, `FBX_SCALE_ALL`, …) |
| Teilenamen für Unity-Skripte | `Body`, `Glow` (wird umgefärbt), `Rotor` (dreht), `Wheel` (Ventilrad), `Screen`, `Deck`, `Rail`; Türen: `Frame_Left/Right/Top`, `StatusLight_Front/Back`, `Panel` (+ `Panel_B`) – mit Pivot im Dreh-/Bewegungspunkt |
| Icons | `Icon_<Name>.png`, 256 × 256, transparenter Hintergrund |

![Materialien](docs/materials.png)

## Voraussetzungen

* Python ≥ 3.9 (keine weiteren Pakete)
* [Blender](https://www.blender.org) ≥ 3.6 (getestet mit 4.0) – wird über `PATH`, `$BLENDER`, `--blender` oder
  `/Applications/Blender.app/...` gefunden
* [ImageMagick](https://imagemagick.org) 6 (`convert`/`montage`) oder 7 (`magick`)

```bash
python -m cubegen doctor      # prüft Blender, ImageMagick und die Render-Engines
```

## Blender-Add-on (GUI)

Das Add-on ist eine Oberfläche für denselben Generator, im 3D-Viewport unter **Seitenleiste (N) › Cube Escape**:

* **Typ, Master-Seed, Variante**: Pfeile ◀ ▶ blättern, 🔄 würfelt. Die Vorschau entsteht live am Ursprung, mit
  Dreiecken, Maßen und Teilenamen im Panel.
* **Varianten-Raster**: z. B. 12 Varianten nebeneinander, beschriftet. Gute Varianten im Viewport anklicken
  (Shift = mehrere) und **Auswahl exportieren**. **Als Vorschau** übernimmt die Variante des aktiven Objekts.
* **Export für Unity**: Modell-, Icon- und Ausgabeordner, Präfix, FBX/GLB/OBJ, Icons + Kontaktbogen. Der Export
  läuft im Hintergrund (Blender bleibt bedienbar) und nutzt exakt die Pipeline der Kommandozeile. Ein Export aus dem
  Add-on ergibt also dieselben Dateien wie `python -m cubegen generate --seed 42 --pick crate:3 --prefix Gen_`.
  Der Knopf **CLI** kopiert genau diesen Befehl.

**Installieren**

```bash
python3 tools/build_addon.py          # -> dist/cubegen_blender_addon.zip
```

In Blender: *Edit › Preferences › Add-ons › Install…* (ab 4.2: Pfeil-Menü oben rechts › *Install from Disk…*), die
Zip wählen und „Cube Escape Model Generator“ aktivieren. Findet das Add-on ImageMagick nicht (Blender aus dem Finder
gestartet), trägst du den Pfad in den Add-on-Einstellungen ein, z. B. `/opt/homebrew/bin/magick`. Standardmäßig wird
`/opt/homebrew/bin` aber schon durchsucht.

*Für die Entwicklung* kannst du statt der Zip den Ordner verlinken; das Add-on nutzt dann direkt den Code im Repository:

```bash
ln -s "$PWD/blender_addon/cubegen_addon" \
      ~/Library/Application\ Support/Blender/<Version>/scripts/addons/cubegen_addon
```

Das Add-on legt nur die Collections „CubeEscape Vorschau“ und „CubeEscape Varianten“ an und erzeugt fehlende
`M_…`-Materialien. Bestehende Materialien (z. B. in `CubeEscape_Assets.blend`) bleiben unverändert. **Aufräumen**
entfernt beides wieder.

## Schnellstart (Kommandozeile)

```bash
# alle 18 Typen je 2x, Seed 42 -> output/seed_42/
python -m cubegen generate --seed 42 --count 2

# nur bestimmte Typen, direkt ins Unity-Projekt
python -m cubegen generate --seed 7 --types crate,machine,door --count 3 --prefix Gen_ \
    --models-dir ../CubeEscape/Assets/Art/Models/Generated \
    --icons-dir  ../CubeEscape/Assets/Art/Icons/Generated

# Batch aus einem Rezept
python -m cubegen generate --recipe recipes/station_props.json

# einzelne Varianten gezielt (gleiche Namen/Seeds wie mit --count)
python -m cubegen generate --seed 42 --pick crate:3,door:7 --prefix Gen_

# erst ansehen, was entstehen würde (ohne Blender)
python -m cubegen generate --seed 42 --types door,pipe --count 3 --dry-run

python -m cubegen list        # alle Typen
```

Ohne Blender (z. B. CI oder schnelles Iterieren) schreibt `--no-blender` OBJ + MTL in reinem Python – gleiche
Geometrie und Materialien, aber ohne Pivots, Previews und Icons.

## Ausgabe

```
output/seed_42/
├── models/                       Gen_Crate_000.fbx, ...   (eine Datei pro Asset)
├── icons/                        Icon_Gen_Crate_000.png   (ImageMagick: getrimmt, zentriert, Schatten)
├── previews/                     Rohe Blender-Renders
├── contact_sheet.png             alle Previews mit Namen
├── materials.png                 Material-Übersicht
├── CubeEscape_Generated_42.blend Übersichtsdatei: alle Assets im Raster, Teile heißen <Asset>.<Teil>
└── manifest.json                 Seeds, Dateien, Pivots, Teilenamen, Maße, Dreiecke, Varianten-Infos
```

## Seeds & Reproduzierbarkeit

* Jedes Asset bekommt einen eigenen Seed `sha256(master, typ, index)` → gleiche Kommandozeile = gleiche Dateien.
* `--count` erhöhen oder Typen hinzufügen ändert **keine** bestehenden Assets (`Crate_002` bleibt `Crate_002`).
* Seeds dürfen Text sein (`--seed level-3`). Der Asset-Seed steht im `manifest.json` und als Custom-Property
  `cubegen_seed` am FBX-Objekt.

## Rezepte

```json
{
  "seed": "station-props-1",
  "formats": ["fbx"],
  "prefix": "Gen_",
  "models": { "crate": 4, "pipe": 3, "server_rack": 3 }
}
```

Weitere Schlüssel: `scale`, `blend`, `render`, `engine`, `render_size`, `samples`, `icon_size`, `icon_background`,
`models_dir`, `icons_dir`, `out`. Kommandozeilen-Optionen überschreiben das Rezept. Beispiele liegen in `recipes/`.

## Previews & Headless-Server

Previews werden wie im Spiel mit **Workbench** gerendert. Workbench/Eevee brauchen OpenGL – auf Servern ohne GPU
erkennt `--engine auto` das per Probe-Render und fällt auf **Cycles (CPU)** zurück. `--no-render` überspringt
Previews, Icons und Kontaktbogen.

## Eigenen Modelltyp hinzufügen

```python
# cubegen/models/props.py (oder ein neues Modul, das in models/__init__.py importiert wird)
from .common import cube, cyl, glow_material
from .registry import model

@model("beacon_box", "BeaconBox", "props", "Kiste mit Signalleuchte")
def beacon_box(rng, a):                       # rng = random.Random(asset-seed), a = Asset
    w = rng.uniform(0.6, 1.0)                 # nur rng benutzen -> deterministisch
    body, glow = a.part("Body"), a.part("Glow")
    cube(body, (w, w, w), (0, 0, w / 2), "M_RobotDark", bevel=0.03)
    center = (0, 0, w + 0.1)                  # drehender Teil: Pivot auf der Achse
    cyl(a.part("Rotor", pivot=center), 0.1, 0.2, center, glow_material(rng))
```

Koordinaten sind immer im Asset-Raum (Front = −Y); der Pivot eines Teils bestimmt nur, wo sein Ursprung liegt.
Danach `python -m unittest discover -s tests` – die Tests prüfen jeden Typ auf gültige Materialien, nach außen
zeigende Normalen, Pivot-Konvention und Determinismus.

## Projektstruktur

```
cubegen/
├── cli.py            Kommandozeile (generate / list / doctor)
├── pipeline.py       Batch: Seeds -> Blender -> ImageMagick -> manifest.json
├── seeds.py          deterministische Seed-Ableitung
├── geometry.py       reine Python-Geometrie (Box, gefaste Box, Lathe, Zylinder, Prisma …)
├── asset.py          Asset = benannte Objekte mit Pivots / Parents
├── materials.py      M_…-Materialtabelle des Spiels
├── models/           Modelltypen (props, industrial, tech, environment)
├── blender.py        Blender finden, Engines prüfen, Worker starten
├── blender_worker.py läuft IN Blender (CLI): Previews, Übersichts-.blend
├── bpy_builder.py    Blender-Objekte, Materialien, FBX/GLB/OBJ-Export (CLI + Add-on)
├── imagemagick.py    Icons, Kontaktbogen, Material-Swatch
└── objwriter.py      OBJ/MTL-Fallback ohne Blender
blender_addon/        Blender-Add-on (GUI)
tools/build_addon.py  baut dist/cubegen_blender_addon.zip
recipes/              Beispiel-Batches
tests/                unittest (Blender-/ImageMagick-Tests werden ohne die Tools übersprungen)
```
