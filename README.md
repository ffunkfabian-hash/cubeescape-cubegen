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
| Teilenamen für Unity-Skripte | `Body`, `Glow` (wird umgefärbt, genau ein Material), `Rotor` (dreht), `Wheel` (Ventilrad), `Damage` (Maschine defekt), `Screen`, `Deck`, `Rail`, `Lights` (Deko-LEDs); Türen: `Frame_Left/Right/Top`, `StatusLight_Front/Back`, `Panel` (+ `Panel_B`) – mit Pivot im Dreh-/Bewegungspunkt |
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
* **Von jedem Typ**: baut alle 18 Typen auf einmal ins Raster, auf Wunsch mehrere Varianten pro Typ (eine Reihe
  pro Typ). **Alle Typen exportieren** exportiert sie direkt, ohne vorher etwas auszuwählen.
* **Parameter**: Eigenschaften des gewählten Typs festlegen (Häkchen bzw. Auswahl statt „Seed“). Rechts steht, was
  der Seed gewählt hätte. Beim Anhaken startet der Wert dort. **Zurücksetzen** lässt wieder alles würfeln.
* **Stil (alle Typen)**: Größe, Raster, Glow-Farbe, Material, Warnfarbe, Abnutzung, Detail, Icon-Kamera.
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

# Assets mit Script (Tür, Maschine, Ventil …) direkt dorthin, wo AddModel sie lädt
python -m cubegen generate --seed 7 --types machine,door --count 3 --prefix Gen_ \
    --models-dir ../CubeEscape/Assets/Art/Models

# von jedem Typ eins – Modelle mit Script nach Art/Models, Deko automatisch nach Library/<Kategorie>
python -m cubegen generate --seed 7 --prefix Gen_ \
    --models-dir  ../CubeEscape/Assets/Art/Models \
    --library-dir ../CubeEscape/Assets/Art/Models/Library

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
├── models/                       Gen_Crate_000.fbx + Gen_Crate_000.cubegen.json (Teile, Pivots, Script-Werte)
├── icons/                        Icon_Gen_Crate_000.png   (ImageMagick: getrimmt, zentriert, Schatten)
├── previews/                     Rohe Blender-Renders
├── contact_sheet.png             alle Previews mit Namen
├── materials.png                 Material-Übersicht
├── CubeEscape_Generated_42.blend Übersichtsdatei: alle Assets im Raster, Teile heißen <Asset>.<Teil>
└── manifest.json                 Seeds, Dateien, Pivots, Teilenamen, Maße, Dreiecke, Varianten-Infos
```

## Wohin im Unity-Projekt?

| Asset | Ordner | Warum |
|---|---|---|
| bewegt sich / hat Zustände (Tür, Maschine, Generator, Ventil-Rohr, Lampe, Terminal, Lüfter, Item) | `Assets/Art/Models` | `AddModel` lädt `Assets/Art/Models/<Name>.fbx`; der Prefab-Builder braucht eine Rezeptzeile in `ModularBlocks.cs` (Werte stehen in `<Name>.cubegen.json`) |
| reine Deko (`"static": true` in der JSON) | `Assets/Art/Models/Library/<Kategorie>` | `AssetRegistry` registriert sie automatisch als statische Hülle mit BoxCollider |

Mit `--library-dir` (im Add-on: Feld „Bibliothek“) sortiert der Generator das selbst: Modelle ohne Script landen in
`<Bibliothek>/<Kategorie>` (Props, Industrial, Tech, Environment), alle anderen im Modell-Ordner.

Das Präfix (`--prefix Gen_`) verhindert Namenskollisionen mit den handgebauten Modellen. Unity-Importeinstellungen
gelten nur beim ersten Import einer Datei. Eine neu generierte FBX unter demselben Namen behält sie also.

## Animation & Unity-Scripts

Im Spiel gibt es **keine Animation-Clips**: Animationsimport ist abgeschaltet, alles läuft prozedural über Scripts
(`Door`, `Machine`, `Rotator`, `Rotatable`, `SignalLight`, `SignalIndicator` …). Die Prefab-Builder setzen deren
Felder. Der Generator liefert deshalb keine Keyframes, sondern neben jeder FBX eine **`<Name>.cubegen.json`**:

* `parts`: Teile mit Parent, `localPosition` **in Unity-Koordinaten** und Materialien
* `behaviours`: welches vorhandene Script welche Teile steuert, mit den Feldwerten in Unity-Einheiten
* `bounds`, `category`, `pivot`, `seed`; `"static": true` heißt reine Deko

```json
{ "script": "Door",
  "parts":  { "panels": ["Panel", "Panel_B"], "statusLights": ["StatusLight_Front", "StatusLight_Back"],
              "upperFrame": ["Frame_Top"], "colliders": ["Frame_Left", "Frame_Right", "Frame_Top"] },
  "fields": { "openOffset": [1.25, 0.0, 0.0], "speed": 1.8 } }
```

| Typ | Script(s) | Werte (wie in `ModularBlocks.cs`) |
|---|---|---|
| `door` | `Door` | Weg nach Stil und **generierter Größe**: Sliding/Elevator seitlich Blattbreite + 0,05; Heavy/Security −(Höhe + 0,1); Blast +(Höhe + 0,1); Airlock geteilt Blatthöhe + 0,05. Tempo: 3 / 0,9 / 4 / 1,8 / 1,2 / 0,6 m/s |
| `machine` | `Machine` (+ `Rotator` am `Rotor`) | `Glow` startet `M_GlowRed`; `Damage` (nur bei Defekt sichtbar); Rotor-Achse `right`, Tempo nach Größe |
| `generator` | `Machine` + `Rotator` | Rotor-Achse `up`, größere Lüfter drehen langsamer (wie Generator 140 / Generator_Small 260) |
| `pipe` | `Rotatable` (mit Ventil) bzw. `SignalIndicator` | Ventilrad: Achse `forward`, Schritt 90°, 180 °/s, Ziel 2; Glow-Ringe: `M_RobotDark` ↔ `M_GlowCyan` |
| `vent` (mit Lüfter) | `Rotator` | Achse `forward`, 160 °/s (wie Vent_Large) |
| `light` | `SignalLight` | Mast `Steady`, Poller `Pulse`, Rundumleuchte `Rotate` (`Rotor` um Unity-Y) |
| `terminal` | `SignalIndicator` | `M_GlowRed` ↔ `M_GlowCyan` |
| `item` | `ItemPickup` | Pivot in der Mitte, dreht um Welt-Y |

Achsen: Unity = (−Blender-X, Blender-Z, −Blender-Y). Also ist Blender X → `right`, Blender Z → `up` und Blender −Y →
`forward`. Teile, deren Material das Spiel tauscht (`Glow`, `StatusLight_*`, `Screen`), haben genau **ein**
Material, weil `renderer.sharedMaterial` nur Slot 0 ersetzt. Mehrfarbige Deko-LEDs heißen `Lights`.

Für den Unity-Import liegt in [`docs/UNITY_INTEGRATION.md`](docs/UNITY_INTEGRATION.md) ein Prompt, mit dem eine KI
im Spielprojekt einen Editor-Import für diese JSON-Dateien an die vorhandenen Builder anschließen kann.

## Parameter & Stil

Standardmäßig würfelt der Seed alles. Einzelne Eigenschaften lassen sich **festlegen**, ohne dass sich der Rest
der Variante ändert: Ein Parameter würfelt intern immer weiter wie bisher, nur das Ergebnis wird ersetzt. Ohne
Parameter liefern alle Seeds exakt dieselben Modelle wie vorher.

```bash
python -m cubegen params            # alle Parameter (python -m cubegen params door: nur Türen)

# Airlock-Tür mit 2 m Öffnung und langsamerem Öffnen, sonst wie Variante 3 von Seed 42
python -m cubegen generate --seed 42 --pick door:3 --param door.style=airlock \
    --param door.width=2.0 --param door.speed=0.8

# ganzer Batch im gleichen Look
python -m cubegen generate --seed 7 --size L --snap 0.5 --glow cyan --material-style metal \
    --warning none --wear light --detail low
```

**Stil (für alle Typen)**

| Option | Werte | Wirkung |
|---|---|---|
| `--size` | S / M / L | Größen aus dem unteren / mittleren / oberen Drittel der Bereiche |
| `--snap` | z. B. 0.5 | Hauptmaße auf Vielfache runden (Radien: der Durchmesser), passend zum Modulraster |
| `--glow` | cyan / red / orange | feste Farbe für Deko-Glow. Status-Teile (Maschine, Generator, Terminal, Tür) behalten ihre Zustandsfarbe |
| `--material-style` | metal / wall / dark / light | bevorzugtes Körpermaterial, wo es eine Option ist |
| `--warning` | none / always | Warnstreifen und -bänder nie oder immer |
| `--wear` | none / light / heavy | Brocken, lose Platten, abgerissenes Kabel als eigenes Teil `Wear` (verändert das Modell selbst nicht) |
| `--detail` | low / normal / high | low: keine Fasen, weniger Zylinder-Seiten; high: rundere Zylinder |
| `--damage` | intact / damaged / destroyed | Zustand, siehe „Zerstörung & Ruinen“ |
| `--icon-angle`, `--icon-zoom` | z. B. `=-25,15`, 1.3 | Kamera für Previews und Icons (Azimut, Elevation wie die `ICONS`-Tabelle des Spiels) |

**Parameter pro Typ** (`--param TYP.NAME=WERT`, mehrfach möglich)

| Typ | Parameter (Wertebereich; 🔗 = Wert für ein Unity-Script) |
|---|---|
| `door` | `style` (airlock / blast / elevator / heavy / security / sliding), `width` (0.6–8), `height` (1.2–8), `speed` (0.05–20) 🔗 |
| `pillar` | `width` (0.2–3), `height` (3.0 / 4.0), `shape` (square / octagon), `warning_band` (ja/nein) |
| `platform` | `size` (1.0 / 2.0 / 3.0 / 4.0), `shape` (square / octagon), `underside` (frustum / keel), `rail` (ja/nein), `stripes` (ja/nein) |
| `wall` | `length` (2.0 / 4.0), `layout` (tall / split / grid / vent), `lines` (top / both / vertical), `pipe` (ja/nein), `pipe_height` (0.2–2.8), `stripes` (ja/nein) |
| `generator` | `radius` (0.3–3), `height` (0.5–5), `rings` (1–6), `floor_pipes` (ja/nein), `status` (off / on), `rotor_speed` (0–2000) 🔗 |
| `machine` | `width` (0.5–5), `depth` (0.5–5), `height` (0.5–4), `warning_band` (ja/nein), `top` (pistons / stack), `flywheel` (ja/nein), `status` (off / on), `rotor_speed` (0–2000) 🔗 |
| `pipe` | `length` (2.0 / 4.0), `radius` (0.09 / 0.18 / 0.35), `axis_height` (0.2–3), `valve` (ja/nein), `valve_speed` (10–1000) 🔗 |
| `tank` | `radius` (0.2–3), `height` (0.5–6), `legs` (ja/nein), `rings` (0–6), `warning_band` (ja/nein), `ladder` (ja/nein), `top_pipe` (ja/nein), `glow_style` (gauge / ring) |
| `vent` | `width` (0.3–4), `height` (0.3–3), `mount_height` (0.2–3), `fan` (ja/nein), `stripes` (ja/nein), `fan_speed` (0–2000) 🔗 |
| `canister` | `radius` (0.1–1), `height` (0.3–3), `sides` (8 / 10 / 12), `warning_band` (ja/nein), `handle` (ja/nein), `glow_style` (window / ring) |
| `crate` | `width` (0.3–3), `height` (0.2–3), `style` (panels / rims / posts), `stripes` (ja/nein), `hatch` (ja/nein), `glow_pattern` (strips / line) |
| `debris` | `radius` (0.2–3), `chunks` (1–20), `plate` (ja/nein), `cable` (ja/nein) |
| `item` | `kind` (energy_cell / battery / data_chip / fuse), `spin` (0–360) 🔗 |
| `broken_wall` | `length` (2.0 / 4.0), `remaining` (0.1–1), `hole` (ja/nein), `rebar` (ja/nein) |
| `cable_mess` | `cables` (1–12), `sparks` (ja/nein) |
| `crate_pile` | `count` (1–12), `broken` (ja/nein) |
| `fallen_pillar` | `width` (0.2–2), `segments` (1–5), `stump` (ja/nein) |
| `girders` | `count` (1–8), `length` (0.5–8) |
| `rubble_pile` | `radius` (0.3–5), `height` (0.2–3), `chunks` (3–60), `plates` (ja/nein), `rebar` (ja/nein), `cable` (ja/nein) |
| `scrap_heap` | `radius` (0.3–5), `height` (0.2–3), `pieces` (3–50), `gears` (ja/nein) |
| `console` | `width` (0.6–4), `screens` (1 / 2 / 3), `tilt` (0–60), `cables` (ja/nein) |
| `crystal_cluster` | `radius` (0.2–4), `crystals` (1–20), `rubble` (0–12) |
| `light` | `style` (post / bollard / beacon), `height` (0.6–6), `mode` (Steady / Blink / Pulse / Rotate / Status) 🔗 |
| `server_rack` | `width` (0.3–3), `depth` (0.3–3), `height` (0.8–4), `double_sided` (ja/nein), `red_ratio` (0–1) |
| `terminal` | `height` (0.4–2.5), `tilt` (0–60), `extra` (keypad / slot / none), `antenna` (ja/nein), `status` (off / on) |

Bedingte Parameter wirken nur, wenn das Teil existiert (z. B. `machine.rotor_speed` nur mit Schwungrad; mit
`machine.flywheel=true` erzwingst du es). In Rezepten stehen sie unter `"params"` und `"style"`:

```json
{ "seed": 7, "style": { "size": "L", "wear": "light" },
  "params": { "door": { "style": "airlock", "width": 2.0 }, "wall": { "length": 4.0 } },
  "models": { "door": 3, "wall": 4 } }
```

Die festgelegten und gewürfelten Werte stehen in `manifest.json` und in der `<Name>.cubegen.json` (`params`,
`style`). Im Add-on gibt es dafür die Bereiche **Parameter** (Häkchen = festlegen; rechts steht, was der Seed gewählt
hat) und **Stil (alle Typen)**.

## Texturen (optional)

![Oben: Kachel-Texturen · Mitte: Ruinen-Typen · unten: intakt / zerstört im Wechsel](docs/example_textures_ruins.png)

Standard ist **keine Textur**: Die Modelle tragen wie bisher die einfarbigen `M_…`-Materialien. Per Auswahlfeld
(Add-on: „Texturen“, Kommandozeile: `--textures`) gibt es zwei Stufen:

| Stufe | Was passiert | Material in der FBX |
|---|---|---|
| `tiled` (Kachel) | ImageMagick erzeugt nahtlose Kacheltexturen pro Material: gebürstetes Metall mit Kratzern (`M_Metal`), Paneelfugen mit Nieten (`M_Wall`), beschichtetes Metall (`M_RobotDark`), Bodenplatten (`M_Platform`), Riffelblech (`M_Ground`), Lack (`M_RobotBody`), abgeplatzte Warnfarbe (`M_Warning`, `M_HazardOrange`). Die UVs sind eine Box-Projektion in Metern, also **1 Kachel = 1 m** auf jeder Fläche, unverzerrt und über alle Assets einheitlich. | `MT_Metal`, `MT_Wall`, … |
| `baked` (Gebacken) | wie Kachel, dann pro Asset: eigene Atlas-UVs, Blender (Cycles) backt Farbe, Rauheit, Normalen, Metallic und Ambient Occlusion, ImageMagick legt Schmutz in Ecken und Vertiefungen. Rund 5–10 s pro Asset. | `MTA_<Asset>` |

Glow-, Kristall- und Glas-Materialien werden nie texturiert, weil die Scripts des Spiels sie umschalten. Texturierte
Materialien haben **eigene Namen** (`MT_…`, `MTA_…`). Dadurch bleiben deine handgebauten Assets mit `M_…`
unverändert.

```bash
python -m cubegen generate --seed 42 --textures tiled --texture-size 1024 \
    --models-dir ../CubeEscape/Assets/Art/Models --textures-dir ../CubeEscape/Assets/Art/Textures/Generated
python -m cubegen generate --seed 42 --types machine --textures baked --texture-set Lab
```

Pro Material entstehen `<Name>_Albedo.png`, `_Normal.png` (OpenGL/Unity), `_Roughness.png` und
`_MetallicSmoothness.png` (R = Metallic, A = Smoothness, für Unity), dazu `CubeEscape_Textures.json` mit allen
Materialien. `--texture-set NAME` erzeugt eine eigene Variante (eigener Seed, Materialien `MT_<Name>_…`). In
der `<Name>.cubegen.json` stehen die verwendeten Materialien und bei `baked` die Atlas-Dateien. In Unity braucht
es dafür eine kleine Import-Ergänzung, siehe [`docs/UNITY_INTEGRATION.md`](docs/UNITY_INTEGRATION.md).
Im Add-on zeigt die Vorschau die Kachel-Texturen (Viewport-Modus „Material Preview“); gebacken wird beim Export.

## Zerstörung & Ruinen

**Zustand für jeden Typ** (`--damage`, Add-on: „Zustand“). Er hat einen eigenen Zufallsstrom: Die zerstörte
Variante von Seed 42 ist immer die Ruine des intakten Seed 42.

| Zustand | Wirkung |
|---|---|
| `intact` | wie bisher (Standard) |
| `damaged` | Dellen, abgeschlagene Kleinteile liegen am Boden, einzelne Deko-LEDs tot, etwas Schutt. Scripts bleiben. |
| `destroyed` | gezackte Bruchkante, darüberliegende Teile liegen am Boden oder fehlen, Bruchflächen, alle Lichter aus, viel Schutt. **Statisch** (keine Scripts) und damit mit `--library-dir` automatisch in der Bibliothek. |

**Neue Ruinen-Typen** (Kategorie `ruins`, statisch): `rubble_pile` (Schutthaufen), `scrap_heap` (Schrotthaufen),
`broken_wall`, `fallen_pillar`, `girders` (eingestürzte Stahlträger), `crate_pile` (umgekippte und aufgebrochene
Kisten), `cable_mess` (Kabelsalat mit funkenden Enden als `Glow`).

```bash
python -m cubegen generate --seed 7 --types rubble_pile,scrap_heap,cable_mess --count 3
python -m cubegen generate --seed 7 --types machine,console,wall --damage destroyed --library-dir ../CubeEscape/Assets/Art/Models/Library
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

Weitere Schlüssel: `params`, `style`, `scale`, `blend`, `render`, `engine`, `render_size`, `samples`, `icon_size`,
`icon_background`, `icon_azimuth`, `icon_elevation`, `icon_zoom`, `models_dir`, `library_dir`, `icons_dir`, `out`. Kommandozeilen-Optionen überschreiben das Rezept. Beispiele liegen in `recipes/`.

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
├── params.py         Parameter (festlegen statt würfeln) und globaler Stil
├── textures.py       ImageMagick-Kacheltexturen (optional)
├── bake.py           läuft IN Blender: gebackene Atlas-Texturen pro Asset (optional)
├── models/           Modelltypen (props, industrial, tech, environment, ruins) + wear, destruction
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
