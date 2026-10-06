# Cube Escape – Model Generator Seed (`cubegen`)

Seed-basierter Low-Poly-Asset-Generator für **Cube Escape**. Ein *Master-Seed* erzeugt reproduzierbar ganze Batches
von Varianten im Stil der Station – Kisten, Kanister, Tanks, Rohre, Maschinen, Generatoren, Konsolen, Terminals,
Server-Racks, Lampen, Kristalle, Trümmer, Türen, Plattformen, Wände, Säulen, Lüftungen und Inventar-Items, dazu
Rätsel-Elemente (Sockel, Sicherungskasten, Ventil, Hebel, Rohr-Puzzle, Laser, Druckplatte, Keypad, Knöpfe,
Zahnradwerk, Kraftfeld, Steckfeld, Scanner, Tresor), Werkzeug-, Hinweis- und Ersatzteil-Items, ein modulares
Bau-Kit (Treppe, Leiter, Steg, Bodenplatte, Fensterwand, Lift, Förderband, Luke, Rolltor, Lüftungsschacht …),
Maschinen, Einrichtung, Roboter und Natur, dazu Fallen (Presse, Sägeblatt, Dampf, Strom), Geräte und
Gameplay-Bausteine (Portal, Phasen- und Bruchplattform, ausfahrbare Brücke, Drehscheibe, Stachelfalle, Becken,
Frachtcontainer) – 129 Typen in 8 Kategorien. **Modellfamilien** (`--family`) erzeugen Bau-Kits, deren Teile über
verbindliche Maße zusammenpassen: Wand und Tür, Treppe und Laufsteg, Rohr und Rohrbogen.

* **Blender CLI** baut die Meshes, exportiert **FBX für Unity** (optional GLB/glTF/OBJ), rendert Previews und
  speichert eine Übersichts-`.blend`.
* **ImageMagick** macht daraus **Inventar-Icons** (`Icon_<Name>.png`), einen **Kontaktbogen** zum Durchsehen und eine
  Material-Übersicht.

Bekannte Bugs, geplante Verbesserungen, Erweiterungen und offene Punkte im Unity-Projekt: [`docs/ROADMAP.md`](docs/ROADMAP.md).

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
| Teilenamen für Unity-Skripte | `Body`, `Glow` (wird umgefärbt, genau ein Material), `Rotor` (dreht), `Wheel` (Ventilrad), `Damage` (Maschine defekt), `Screen`, `Deck`, `Lights` (Deko-LEDs); Türen: `Frame_Left/Right/Top`, `StatusLight_Front/Back`, `Panel` (+ `Panel_B`) – mit Pivot im Dreh-/Bewegungspunkt |
| Icons | `Icon_<Name>.png`, 256 × 256, transparenter Hintergrund |

![Materialien](docs/materials.png)

## Voraussetzungen

* Python ≥ 3.9 (keine weiteren Pakete)
* [Blender](https://www.blender.org) ≥ 3.6 (getestet mit 4.0) – wird über `PATH`, `$BLENDER`, `--blender` oder
  `/Applications/Blender.app/...` gefunden
* [ImageMagick](https://imagemagick.org) 6 (`convert`/`montage`) oder 7 (`magick`)

```bash
# prüft Blender, ImageMagick und die Render-Engines
python -m cubegen doctor
```

## Blender-Add-on (GUI)

Das Add-on ist eine Oberfläche für denselben Generator, im 3D-Viewport unter **Seitenleiste (N) › Cube Escape**:

* **Typ, Master-Seed, Variante**: Pfeile ◀ ▶ blättern, 🔄 würfelt. Die Vorschau entsteht live am Ursprung, mit
  Dreiecken, Maßen und Teilenamen im Panel.
* **Familie & Kit**: Familie wählen (Maße und Look für Vorschau, Raster und Export), **Kit bauen** stellt das
  ganze Kit ins Raster, **Kit exportieren** exportiert es mit gemeinsamem Kontaktbogen und Passungsprüfung.
* **Von jedem Typ**: baut alle 129 Typen auf einmal ins Raster, auf Wunsch mehrere Varianten pro Typ (eine Reihe
  pro Typ). **Alle Typen exportieren** exportiert sie direkt, ohne vorher etwas auszuwählen.
* **Parameter**: Eigenschaften des gewählten Typs festlegen (Häkchen bzw. Auswahl statt „Seed“). Rechts steht, was
  der Seed gewählt hätte. Beim Anhaken startet der Wert dort. **Zurücksetzen** lässt wieder alles würfeln.
* **Stil (alle Typen)**: Raum-Thema, Größe, Raster, Glow-Farbe, Material, Warnfarbe, Abnutzung, Detail,
  Icon-Kamera. Das **Thema** (beliebiger Text) würfelt Glow-Farbe, Material, Abnutzung und Warnfarbe einmal für
  alle Modelle, damit ein Raum zusammenpasst.
* **Varianten-Raster**: z. B. 12 Varianten nebeneinander, beschriftet. Gute Varianten im Viewport anklicken
  (Shift = mehrere) und **Auswahl exportieren**. **Als Vorschau** übernimmt die Variante des aktiven Objekts.
  **Nur unterschiedliche** überspringt Varianten, die wie eine frühere aussehen.
* **Export für Unity**: Modell-, Icon- und Ausgabeordner, Präfix, FBX/GLB/OBJ, Icons + Kontaktbogen, LODs für
  statische Modelle, **Parallel** (mehrere Blender-Prozesse) und **Alles neu bauen** (sonst werden unveränderte
  Modelle übernommen). Der Export läuft im Hintergrund (Blender bleibt bedienbar) und nutzt exakt die Pipeline der
  Kommandozeile. Ein Export aus dem
  Add-on ergibt also dieselben Dateien wie `python -m cubegen generate --seed 42 --pick crate:3 --prefix Gen_`.
  Der Knopf **CLI** kopiert genau diesen Befehl.

**Installieren**

```bash
# baut dist/cubegen_blender_addon.zip
python3 tools/build_addon.py
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

## Herunterladen (macOS / Linux)

```bash
curl -fsSL https://raw.githubusercontent.com/ffunkfabian-hash/lowpoly_cubeescape_model_generatior/HEAD/tools/install.sh | bash
```

Das Script ([`tools/install.sh`](tools/install.sh)) lädt das Projekt nach `~/cubegen` (mit git, sonst als Archiv),
legt den Befehl `cubegen` in `~/.local/bin` an, baut das Blender-Add-on (`~/cubegen/dist/cubegen_blender_addon.zip`)
und prüft Blender und ImageMagick. Erneut ausführen = aktualisieren. Optionen: `--dir ORDNER`, `--branch BRANCH`,
`--no-link` (als `… | bash -s -- --dir ~/tools/cubegen`).

## Schnellstart (Kommandozeile)

Ausführliche Anleitung mit allen Optionen: [`docs/CLI.md`](docs/CLI.md).

Die `#`-Zeilen in den Beispielen sind Kommentare. Die zsh auf dem Mac kennt sie im Terminal nur nach
`setopt interactivecomments`; sonst einfach nur die Befehlszeilen kopieren.

```bash
# alle 129 Typen je 2x, Seed 42 -> output/seed_42/
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

# ein Raum aus einem Guss, nur Varianten, die sich wirklich unterscheiden
python -m cubegen generate --seed 7 --theme labor-3 --types crate,machine,wall --count 6 --unique

# alle Typen, Deko mit Sparstufe (LOD), 4 Blender-Prozesse; erneut ausgeführt baut es nur Geändertes
python -m cubegen generate --seed 42 --count 3 --lods --jobs 4

# Qualitätsbericht: Dreiecke, Draw Calls, flackernde Flächen, Doppelte
python -m cubegen check

# ein Bau-Kit, dessen Teile zusammenpassen (Familien: station, foundry, lab)
python -m cubegen generate --family station --seed 42 --prefix Gen_
python -m cubegen check --family station

# alle Typen
python -m cubegen list
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
| bewegt sich / hat Zustände (Tür, Maschine, Generator, Ventil, Lampe, Terminal, Lüfter, Item, Rätsel-Elemente, Lift, Förderband, Roboter …) | `Assets/Art/Models` | `AddModel` lädt `Assets/Art/Models/<Name>.fbx`; der Prefab-Builder braucht eine Rezeptzeile in `ModularBlocks.cs` (Werte stehen in `<Name>.cubegen.json`) |
| reine Deko (`"static": true` in der JSON) | `Assets/Art/Models/Library/<Kategorie>` | `AssetRegistry` registriert sie automatisch als statische Hülle mit BoxCollider (begehbare Teile wie Treppe oder Steg bringen eigene [Collider](#collider) mit) |

Mit `--library-dir` (im Add-on: Feld „Bibliothek“) sortiert der Generator das selbst: Modelle ohne Script landen in
`<Bibliothek>/<Kategorie>` (Props, Industrial, Tech, Environment, Ruins, Nature …), alle anderen im Modell-Ordner.

Das Präfix (`--prefix Gen_`) verhindert Namenskollisionen mit den handgebauten Modellen. Unity-Importeinstellungen
gelten nur beim ersten Import einer Datei. Eine neu generierte FBX unter demselben Namen behält sie also.

## Modellfamilien & Bau-Kits

![Kit der Familie station: Wände mit Tür-/Fenster-/Rohröffnung, Tür, Portal, Stegstücke, Treppen, Brücke, Plattformen, Rohre, Becken, Falle, Container](docs/example_family_station.png)

Eine Familie (`cubegen/family_data/<Name>.json`) ist ein Rezept mit verbindlichen Maßen (`dims`): Wandhöhe und
-stärke, Modullänge, Tür-/Fensteröffnung mit Rahmenmaß, Laufstegbreite, Geländer- und Ebenenhöhe,
Plattformgröße, Rohrradius und Achshöhe. Dazu kommen Material, Glow, Warnfarbe, Abnutzung, Detailgrad und
Texturset. Eine zentrale Tabelle (`cubegen/families.py`, `python -m cubegen families --dims`) bildet jedes Maß
auf die Parameter aller Typen ab, die ihm folgen. Ein Rezept mit `"family": "station"` baut darauf auf, seine
eigenen Werte gelten als Abweichung und stehen so im Manifest.

* **Gleiches Modell**: gleiche Variante, Parameter und Version = gleiche Dateien.
* **Variante in der Familie**: `--family station --types catwalk --count 8`, Details wechseln, Maße bleiben.
* **Passendes Teil**: `--family station --types door` (Tür zur Wand) oder `--match <Name>.cubegen.json --types
  pipe_bend` (Rohrbogen zu einem vorhandenen Rohr).
* **Passungsprüfung** (`check --family`, auch im Manifest unter `family.fit`): setzt die Teile aneinander und
  prüft Breiten, Höhen, Ausrichtung, begehbaren Boden über jeder Fuge, freien Durchgang, Tür bzw. Portal in
  der Wandöffnung und Rohre durch Durchführungen.
* Anschlusspunkte (`connectors`) und die Herkunft jedes Parameters (`param_sources`) stehen im Manifest. Der
  Sidecar bleibt im Vertrag des Unity-Imports und bekommt keine neuen Felder.

Neue Varianten bestehender Typen sind Parameter: `wall.opening` (`door`, `window`, `pipe`) mit Rahmen- bzw.
Öffnungsmaßen, `wall.height`/`thickness`, `catwalk.shape` (`corner`, `tee`, `cross`, `landing`, `end`),
`stairs.layout` (`landing`, `quarter`, `switchback`). Details in [`docs/CLI.md`](docs/CLI.md), was der
Unity-Import davon nutzt und was dort noch fehlt in [`docs/UNITY_INTEGRATION.md`](docs/UNITY_INTEGRATION.md).

## Reproduzierbarkeit & Qualität

* **Gleicher Seed = gleiches Modell**, auch nach Updates und mit anderer Python-Version. `tests/golden.json`
  enthält Fingerabdrücke aller Typen; der Test schlägt fehl, sobald sich ein Modell ändert. Der Zufall läuft über
  einen eigenen, eingefrorenen Würfel (`StableRandom`), und Summen werden so gerechnet, dass Blenders Python 3.11
  und Python 3.9 bis 3.13 bitgenau dieselben Dateien bauen. CI testet mit 3.9, 3.11 und 3.13.
* **Neue Details ohne alte Seeds zu ändern**: Ein Builder würfelt Neues aus einem eigenen Strom,
  `a.sub("name")`, statt aus `rng`. Sonst würden alle späteren Würfe verrutschen.
* **`python -m cubegen check`** meldet pro Typ die Dreiecke gegen das Budget der Kategorie, Draw Calls,
  flackernde Flächen (Z-Fighting) und wie viele Varianten sich wirklich unterscheiden. Bekannte flackernde
  Flächen bestehender Typen stehen in `tests/quality_baseline.json`. Sie zu beheben würde deren Seeds ändern, also
  passiert das nur bewusst; schlimmer werden darf es nicht, neue Typen dürfen keine haben.
* Absichtlich ein Modell geändert? `python3 tests/golden_cases.py --update` schreibt beide Referenzdateien neu
  (und in den CHANGELOG gehört, welche Seeds anders aussehen).
* **Unity-Vertrag**: `cubegen/contract.py` prüft jeden Sidecar mit den Regeln des Spiel-Imports
  (`Docs/CUBEGEN_IMPORT.md`) und, wo es eine gibt, gegen die echte FBX. Die Tests exportieren alle Typen
  und alle Kits als FBX und prüfen sie damit.
* **Item-IDs**: `--param keycard.item_id=<ID>` schreibt `ItemPickup.fields.itemId`; cubegen erfindet keine IDs.

## Animation & Unity-Scripts

Im Spiel gibt es **keine Animation-Clips**: Animationsimport ist abgeschaltet, alles läuft prozedural über Scripts
(`Door`, `Machine`, `Rotator`, `Rotatable`, `SignalLight`, `SignalIndicator` …). Die Prefab-Builder setzen deren
Felder. Der Generator liefert deshalb keine Keyframes, sondern neben jeder FBX eine **`<Name>.cubegen.json`**:

* `parts`: Teile mit Parent, `localPosition` **in Unity-Koordinaten** und Materialien
* `behaviours`: welches vorhandene Script welche Teile steuert, mit den Feldwerten in Unity-Einheiten
* `bounds`, `category`, `pivot`, `seed`; `"static": true` heißt reine Deko
* `colliders` (nur wo nötig): fertige Kollisionsformen, siehe [Collider](#collider)
* `lods` (nur mit `--lods`, nur statische Modelle): Die FBX enthält jedes Teil als `<Teil>_LOD0` und `<Teil>_LOD1`
  (Unity baut daraus beim Import die LODGroup); `parts` und `colliders` nennen die Teile ohne Endung
* `style`: der Stil, mit dem das Modell gebaut wurde (ein Thema ist darin schon aufgelöst)

Die FBX und ihre `<Name>.cubegen.json` stimmen immer überein: Nach jedem Export liest der Generator die FBX zurück
und vergleicht Eltern, lokale Pivots, Rotation (immer 0) und Vertices. Bei einer Abweichung bricht er ab. (Bis
0.7.0 hatten Teile ab der dritten Ebene, `balance_scale` `Slot_A`/`Slot_B`, `robot_arm` `Arm_Upper`/`Gripper`
und `turret` `Glow`, wegen eines Fehlers in Blenders FBX-Export falsche Pivots und 90° Drehung.)

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
| `keycard` | `ItemPickup` | wie `item` (Karte, Anhänger, Schlüssel) |
| `socket`, `chip_reader`, `battery_bank`, `keypad`, `laser_receiver`, `pressure_plate` | `SignalIndicator` | `Glow` `M_GlowRed` ↔ `M_GlowCyan`; leere Objekte `Slot` / `Slot_<n>` markieren, wo ein eingesetztes Item sitzt |
| `fuse_box` | `Rotatable` + `SignalIndicator` | Deckel `Panel` schwenkt um sein Scharnier (Achse `up`, Schritt `lid_angle`, Ziel 1); `Slot_<n>` = Sicherungen |
| `valve` | `Rotatable` | Rad `Wheel`: Achse `forward`, Schritt 90°, Ziel `steps` (wie das Ventil am Rohr) |
| `lever` | `Rotatable` | Hebel: Achse `right`, 90° auf `positions` Stellungen verteilt; Drehschalter: Achse `forward`, 360° / `positions` |
| `pipe_fitting` | `Rotatable` | `Fitting` dreht um `up` in 90°-Schritten, Ziel `target`; die Anschlüsse in Ruhe stehen in `note` |
| `laser_mirror` | `Rotatable` | `Mirror` ruht auf 45°, dreht um `up` in 45°/90°-Schritten |
| `laser_emitter` | `SignalLight` | leeres Objekt `Beam` = Startpunkt des Strahls (Richtung Unity-forward) |
| `camera`, `antenna` | `Rotator` + `SignalLight` | Kopf `Rotor` dreht um `up` (Kamera standardmäßig `speed` 0 = steht, weil `Rotator` endlos dreht); LED blinkt bzw. pulsiert |
| `ceiling_panel` | `SignalLight` (Licht) bzw. `Rotator` (Lüfter) | Lüfter um `up`; `plain` ist statisch |
| `lift` | `Door` | `Deck` fährt beim „Öffnen“ um `travel` nach oben (`openOffset` = (0, Hub, 0)) |
| `conveyor` | je Rolle ein `Rotator` | `Roller_<n>` drehen um `forward` |
| `pad` | `SignalLight` (+ `Rotator` beim Teleporter) | Teleporter-Ring `Rotor` um `up` |
| `drone` | je Propeller ein `Rotator` + `SignalLight` | `Rotor_<n>` um `up`, benachbarte gegenläufig; Pivot in der Mitte |
| `service_robot` | `SignalLight` (+ `Rotator` für `Head`, wenn `head_speed` > 0) | Augen `Glow` sind Kinder von `Head` |
| `robot_arm` | `SignalIndicator` (+ `Rotator` für `Turret`, wenn `turret_speed` > 0) | Gelenkkette `Turret` → `Arm_Lower` → `Arm_Upper` → `Gripper`, Pivots in den Gelenken |

Achsen: Unity = (−Blender-X, Blender-Z, −Blender-Y). Also ist Blender X → `right`, Blender Z → `up` und Blender −Y →
`forward`. Teile, deren Material das Spiel tauscht (`Glow`, `StatusLight_*`, `Screen`), haben genau **ein**
Material, weil `renderer.sharedMaterial` nur Slot 0 ersetzt. Mehrfarbige Deko-LEDs heißen `Lights`.

Für den Unity-Import liegt in [`docs/UNITY_INTEGRATION.md`](docs/UNITY_INTEGRATION.md) ein Prompt, mit dem eine KI
im Spielprojekt einen Editor-Import für diese JSON-Dateien an die vorhandenen Builder anschließen kann. Ein
zweiter Prompt dort ergänzt die Mechanik, für die das Spiel noch kein Script hat: Item-Sockel, Laser mit Spiegeln,
Druckplatte, Rohr-Puzzle, Kamera-Schwenk, Leiter, Sprung-/Teleporter-Pad, Förderband, Lift-Knöpfe und
Leerlauf-Animationen für Drohne und Roboterarm.

## Collider

Die FBX enthält keine Collider. Für die meisten Modelle reicht die Hülle, die `AssetRegistry` bzw. der Import
anlegt. Bei begehbaren und bewegten Teilen ist sie falsch (Treppe als Block, Steg mit Geländer-Hülle, Luke ohne
Öffnung). Diese Typen schreiben deshalb eigene Formen in die `<Name>.cubegen.json`:

```json
"colliders": [
  { "type": "box", "part": null,    "center": [0, 0.6, 0.1], "size": [1.2, 0.3, 0.21], "rotation": [0, 0, 0, 1] },
  { "type": "box", "part": "Panel", "center": [0, -0.03, -0.5], "size": [1.0, 0.06, 1.0], "rotation": [0, 0, 0, 1] },
  { "type": "mesh", "part": "Deck", "convex": true }
]
```

* `part`: Teil, an dem der Collider hängt und mit dem er sich bewegt (Deckel, Lift-Deck, Kraftfeld …), `null` = Wurzel.
* `center` / `size` in Unity-Koordinaten relativ zum Pivot des Teils; `rotation` = Unity-Quaternion (x, y, z, w).
  Ein `BoxCollider` kann sich nicht drehen: gedrehte Boxen (Rampe, Wendeltreppe) bekommen ein eigenes Kind-Objekt.
* `mesh`: `MeshCollider` auf dem Mesh des Teils (`convex` = Unity bildet die konvexe Hülle).
* Fehlt `colliders`, bleibt alles wie bisher (Hülle). Zerstörte Varianten (`--damage destroyed`) haben keine.

| Typ | Collider |
|---|---|
| `stairs` | eine Box je Stufe; Rampe: schräge Box auf der Fläche + gestapelte Boxen darunter; Geländer als Zaun |
| `spiral_stairs` | eine gedrehte Platte je Stufe, Podest, Mast, Zaun außen |
| `catwalk` | nur die Deck-Platte, Geländer und Stützen einzeln (unter dem Steg bleibt frei) |
| `platform`, `floating_island` | `mesh` (konvex) auf `Deck` bzw. `Island` |
| `floor_tile` | Deck-Platte |
| `hatch`, `floor_grate` | Rahmen und Schachtwände einzeln (der Schacht bleibt offen), Deckel / Rost auf `Panel` |
| `vent_shaft` | Boden, Decke und geschlossene Seiten (innen begehbar), Gitter auf `Grille` |
| `lift` | Sockel, Säulen, Träger, Deck mit Geländer auf `Deck` (fährt mit) |
| `force_field`, `crusher`, `cage` | Rahmen; `Field` / Pressenkopf `Panel` / Käfigtür `Panel` mit eigenem Collider |
| `railing`, `shock_plate`, `saw_blade` | flache Box statt Hülle (Geländer, Bodenplatte + Spulen, Gehäuse + Blatt) |

## Parameter & Stil

Standardmäßig würfelt der Seed alles. Einzelne Eigenschaften lassen sich **festlegen**, ohne dass sich der Rest
der Variante ändert: Ein Parameter würfelt intern immer weiter wie bisher, nur das Ergebnis wird ersetzt. Ohne
Parameter liefern alle Seeds exakt dieselben Modelle wie vorher.

```bash
# alle Parameter (python -m cubegen params door: nur Türen)
python -m cubegen params

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
| `--theme` | beliebiger Text | Raum-Thema: würfelt Glow-Farbe, Material, Abnutzung und Warnfarbe einmal für alle Modelle; einzeln festgelegte Werte gehen vor |
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
| `pillar` | `width` (0.2–3), `height` (3.0 / 4.0), `warning_band` (ja/nein) |
| `platform` | `size` (1.0 / 2.0 / 3.0 / 4.0), `underside` (frustum / keel), `stripes` (ja/nein) |
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
| `battery_bank` | `bays` (1–8), `height` (0.6–3), `filled` (0–8), `status` (off / on) |
| `chip_reader` | `mount_height` (0.5–2.5), `screen` (ja/nein), `keys` (ja/nein), `status` (off / on) |
| `fuse_box` | `slots` (1–6), `mount_height` (0.5–2.5), `lid_angle` (30–180) 🔗, `warning` (ja/nein), `status` (off / on) |
| `keypad` | `layout` (numpad / buttons / big_button), `mount_height` (0.5–2.5), `status` (off / on) |
| `laser_emitter` | `height` (0.3–2), `style` (stand / box), `mode` (Steady / Blink / Pulse) 🔗 |
| `laser_mirror` | `height` (0.3–2), `step` (45 / 90) 🔗, `target` (0–7) 🔗 |
| `laser_receiver` | `height` (0.3–2.5), `mount` (stand / pillar), `status` (off / on) |
| `lever` | `style` (lever / dial), `mount_height` (0.4–2.5), `positions` (2–8), `speed` (10–1000) 🔗 |
| `pipe_fitting` | `kind` (straight / elbow / tee / cross / end), `tile` (0.5–3), `radius` (0.05–0.3), `base` (ja/nein), `target` (0–3) 🔗, `speed` (10–1000) 🔗 |
| `pressure_plate` | `size` (0.4–3), `shape` (square / round), `stripes` (ja/nein), `status` (off / on) |
| `socket` | `kind` (energy_cell / battery), `height` (0.3–1.6), `cables` (ja/nein), `stripes` (ja/nein), `status` (off / on) |
| `valve` | `radius` (0.12–0.6), `mount_height` (0.4–2.5), `pipes` (ja/nein), `steps` (1–8) 🔗, `speed` (10–1000) 🔗 |
| `antenna` | `style` (mast / radar / dish), `height` (0.8–6), `speed` (0–360) 🔗 |
| `camera` | `mount_height` (1–4), `style` (box / dome), `speed` (0–180, Standard 0) 🔗, `mode` (Steady / Blink / Pulse) 🔗 |
| `cable_tray` | `length` (2.0 / 4.0), `mount_height` (0.3–3), `style` (tray / conduit), `cables` (1–10) |
| `catwalk` | `length` (2.0 / 4.0), `width` (1.0 / 2.0), `rails` (both / one / none), `supports` (0–4), `glow` (ja/nein) |
| `ceiling_panel` | `size` (1.0 / 2.0 / 4.0), `style` (light / fan / plain), `mount_height` (2–6), `fan_speed` (0–2000) 🔗 |
| `floor_tile` | `size` (1.0 / 2.0 / 4.0), `style` (grate / plate / hatch / vent), `glow` (ja/nein), `stripes` (ja/nein) |
| `ladder` | `height` (1–6), `width` (0.3–1), `cage` (ja/nein), `hoops` (ja/nein) |
| `lift` | `size` (1–3), `travel` (0.5–4) 🔗, `speed` (0.1–5) 🔗, `rail` (ja/nein) |
| `pad` | `kind` (jump / teleport), `radius` (0.4–2), `mode` (Steady / Pulse / Blink) 🔗, `speed` (0–720) 🔗 |
| `stairs` | `style` (stairs / ramp), `width` (0.6–4), `rise` (0.4–3), `rails` (none / left / both), `glow_edges` (ja/nein), `stripes` (ja/nein) |
| `wall_corner` | `style` (corner / end / tee), `pipe` (ja/nein), `guard` (ja/nein), `glow` (ja/nein) |
| `window_wall` | `length` (2.0 / 4.0), `windows` (single / split / band), `sill` (0.2–1.5), `glow` (ja/nein) |
| `conveyor` | `style` (rollers / belt), `length` (0.8–4), `width` (0.4–1.5), `height` (0.3–1.2), `speed` (0–1000) 🔗 |
| `barrier` | `style` (gate / jersey / cones), `width` (0.8–4), `lights` (ja/nein) |
| `chair` | `armrests` (ja/nein), `back` (high / low), `turn` (-180 bis 180) |
| `cryo_pod` | `pose` (standing / lying), `length` (1.6–3), `occupied` (ja/nein), `frost` (ja/nein) |
| `extinguisher` | `height` (0.3–1), `holder` (none / stand / cabinet) |
| `gas_rack` | `bottles` (1–6), `height` (0.6–1.8), `cage` (ja/nein) |
| `keycard` | `kind` (card / fob / key), `spin` (0–360) 🔗 |
| `locker` | `count` (1–4), `height` (1.2–2.4), `open` (ja/nein), `bench` (ja/nein) |
| `medkit` | `style` (box / cabinet), `mount_height` (0.5–2.5), `cross` (red / cyan / white) |
| `pallet` | `size` (euro / square), `load` (none / crates / sacks / canisters), `straps` (ja/nein) |
| `shelf` | `width` (0.6–3), `height` (0.8–3), `levels` (2–5), `fill` (0–1) |
| `sign` | `symbol` (warning / arrow / exit / electric / number), `size` (0.2–1.5), `mount_height` (0.5–3.5), `lit` (ja/nein) |
| `tool_cart` | `drawers` (1–6), `width` (0.4–1.2), `top` (tools / tray / box) |
| `workbench` | `width` (1–3), `pegboard` (ja/nein), `vise` (ja/nein), `lamp` (ja/nein) |
| `drone` | `rotors` (2 / 3 / 4), `size` (0.3–1.5), `tool` (none / claw / spotlight), `rotor_speed` (0–3000) 🔗, `mode` (Steady / Pulse / Blink) 🔗 |
| `robot_arm` | `reach` (0.8–3), `pose` (rest / reach / up), `gripper` (claw / suction / welder), `turret_speed` (0–180) 🔗 |
| `service_robot` | `drive` (wheels / treads / hover), `height` (0.5–2.2), `arms` (0 / 1 / 2), `antenna` (ja/nein), `head_speed` (0–180) 🔗 |
| `floating_island` | `radius` (0.8–3.5), `depth` (0.6–4), `crystals` (0–10), `glow` (ja/nein) |
| `hanging_crystals` | `mount_height` (2–6), `crystals` (1–12), `length` (0.3–1.8) |
| `rock` | `size` (0.3–4), `boulders` (1–8), `spire` (ja/nein), `crystals` (0–8) |

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

## Rätsel, Bau-Kit, Einrichtung, Roboter & Natur

![Je eine Variante der 44 neuen Typen (Seed 7)](docs/example_new_types.png)

| Kategorie | Typen |
|---|---|
| `puzzle` – Gegenstücke zu den Items und Rätsel-Mechanik | `socket` (Sockel / Ladestation für Energiezelle oder Batterie), `fuse_box` (Sicherungskasten mit Klappdeckel), `chip_reader`, `battery_bank`, `valve` (Wandventil), `lever` (Hebel oder Drehschalter), `pipe_fitting` (Rohr-Puzzle: gerade, Bogen, T, Kreuz, Ende auf 1-m-Kachel), `laser_emitter`, `laser_mirror`, `laser_receiver`, `pressure_plate`, `keypad` |
| `props` | `keycard` (Inventar-Item: Karte, Anhänger, Schlüssel), `locker`, `shelf` (gefülltes Regal), `workbench`, `tool_cart`, `cryo_pod`, `chair`, `gas_rack`, `extinguisher`, `medkit`, `barrier` (Schranke, Betonbarriere, Pylonen), `pallet`, `sign` (Warnung, Pfeil, Exit, Hochspannung, Sektornummer) |
| `environment` – Bau-Kit im Raster der Wandmodule | `stairs` (Treppe / Rampe), `ladder`, `catwalk` (Steg / Brücke), `floor_tile`, `ceiling_panel`, `wall_corner` (Ecke, Ende, T-Stück), `window_wall`, `cable_tray`, `lift`, `pad` (Sprung- / Teleporter-Pad) |
| `industrial`, `tech` | `conveyor` (Rollenbahn / Förderband), `camera` (Überwachungskamera), `antenna` (Mast, Radar, Satellitenschüssel) |
| `robots` | `drone`, `service_robot`, `robot_arm` |
| `nature` | `rock`, `floating_island` (begehbare Oberseite bei z = 0), `hanging_crystals` |

* **Wandmontiert** (`fuse_box`, `chip_reader`, `valve`, `lever`, `keypad`, `camera`, `medkit`, `sign`, `cable_tray`):
  Rückseite an der Wand bei y = +0,1, Pivot am Boden darunter, Höhe über `mount_height`.
* **Decke** (`ceiling_panel`, `hanging_crystals`): hängen auf `mount_height` (Standard 3 m = Wandhöhe). Previews und
  Icons zeigen sie von unten.
* **Begehbar** (`catwalk`, `floor_tile`, `floating_island`): Oberkante bei z = 0 wie die Plattformen.
* **Slots**: `socket`, `chip_reader` (`Slot`), `fuse_box` und `battery_bank` (`Slot_1` …) haben leere Objekte an der
  Stelle, an der das eingesetzte Item sitzen soll.
* Statisch (ohne Script, also mit `--library-dir` in der Bibliothek): Einrichtung, Treppe, Leiter, Steg, Bodenplatte,
  Wandecke, Fensterwand, Kabeltrasse und Natur.

```bash
# ein Rätselraum: Sockel, Sicherungskasten, Rohr-Puzzle, Laser, Keypad
python -m cubegen generate --recipe recipes/puzzle_room.json
python -m cubegen generate --seed 7 --types pipe_fitting --count 8 --param pipe_fitting.tile=1.0
```

## Mehr Rätsel, Items, Bau-Kit, Maschinen, Roboter, Natur & Einrichtung

35 weitere Typen. Die meisten nutzen die vorhandenen Scripts des Spiels, Unity braucht für sie also keinen neuen
Code.

| Kategorie | Typen |
|---|---|
| `puzzle` | `button` (großer Knopf, Not-Aus oder Knopfreihe; `Button` / `Button_<n>` werden eingedrückt), `gear_puzzle` (Zahnradwerk an der Wand: `Gear_<n>` mit `Rotator`, Tempo nach Übersetzung, gegenläufig; optional fehlt ein Rad → `Slot`), `laser_splitter` (drehbares Kristallprisma `Prism`, teilt den Strahl in `Beam_A` / `Beam_B`), `force_field` (Energiefeld oder Laserzaun zwischen zwei Emittern; `Door` fährt `Field` in den Boden), `cable_plug` (Steckfeld mit farbigen Buchsen `Slot_<n>` und losem Kabel `Plug`; die passende Buchse steht in `meta.target_slot`), `scanner` (Hand-, Netzhaut- oder Kartenscanner; `Scan` pulsiert über `SignalLight`), `safe` (Tresor: Tür `Panel` mit Zahlenrad `Wheel` oder Keypad, `Slot` innen) |
| `props` – Inventar-Items (Pivot in der Mitte, `ItemPickup`) | `tool` (Schraubenschlüssel, Brecheisen, Zange, Schraubendreher), `clue` (Tablet, Notizzettel, Datapad, Audio-Log), `spare_part` (Zahnrad, Linse, Kristallsplitter, Ventilrad, Spule; Radius in `meta`) |
| `props` – Einrichtung | `bed` (Pritsche, Etagenbett, Krankenbett mit Monitor), `table` (Tisch, Schreibtisch mit Monitor, rund, Labortisch), `bin` (rund, eckig, Wertstoff-Reihe, Gefahrstoff; Deckel offen, Müll), `toolbox` (Koffer, Werkstattwagen, offen mit Werkzeug) |
| `environment` | `hatch` (Bodenluke, Oberkante bei z = 0, Deckel `Panel` klappt nach oben, rund mit Handrad `Wheel`), `shutter` (Rolltor oder Gitter, `Door` fährt es hoch), `vent_shaft` (begehbarer Lüftungsschacht: gerade, Ecke, T, Kreuz, Ende; optional Gitter `Grille`), `floor_grate` (Gitterrost über einem Schacht mit Rohren / Kabeln / Lichtern, Rost `Panel` herausnehmbar), `bulkhead` (Spant / Rahmen für Korridore, Durchgang entlang Y), `wall_panel` (Wandverkleidung: Konsolen, Rohre, Schränke, Glow-Paneele) |
| `industrial` | `pipe_bend` (Bogen, Bogen nach oben, T, Kreuz – passend zu `pipe`), `fan` (Standlüfter oder Kastenlüfter, `Rotor`), `pump` (Pumpe mit Motor und Kupplung, `Machine`), `transformer` (Trafo mit Kühlrippen und Isolatoren, `Machine`), `reactor_core` (Reaktorkern: Glassäule mit drehendem Kristallkern `Rotor`, `Machine`) |
| `tech` | `hologram` (Holo-Tisch oder -Sockel, drehende Projektion: Globus, Station, Würfel), `monitor_wall` (Bildschirmwand, 1–12 Bildschirme), `intercom` (Gegensprechanlage, Audio oder Video, Ruftaste `Button`) |
| `robots` | `turret` (Wachgeschütz: `Turret` dreht, `Gun` neigt sich, Laservisier), `spider_bot` (Spinnenroboter, Beine `Leg_<n>` mit Pivot an der Hüfte), `android` (Androide, stehend oder kaputt an die Wand gelehnt) |
| `nature` | `plant` (Farn, Leuchtknollen, Stacheln; Topf rund, eckig oder Fels), `hydroponic_bed` (Pflanzbeet mit 1–3 Ebenen und Pflanzenlampe), `stalagmite` (Gruppe, Säule bis zur Decke, mit Kristallspitzen), `mushroom` (Pilzgruppe bis Riesenpilz, leuchtende Lamellen) |

* **Pflanzen**: Das Spiel hat kein grünes Material. Blätter sind deshalb „außerirdisch“: `M_Crystal` (leuchtet
  cyan), `M_HazardOrange` oder `M_Warning`. Welche Farbe der Seed gewählt hat, steht in `meta.leaves`.
* **Wandmontiert** (`button`, `gear_puzzle`, `cable_plug`, `scanner`, `wall_panel`, `monitor_wall`, `intercom`):
  Rückseite an der Wand bei y = +0,1, Pivot am Boden darunter.
* **Begehbar**: `hatch` und `floor_grate` haben die Oberkante bei z = 0, `vent_shaft` hat innen einen Boden (Pivot
  unten).
* **Passende Teile**: `spare_part` (Art `gear`) passt in den `Slot` von `gear_puzzle` (`meta.missing_gear.radius`),
  `tool` und `clue` sind Inventar-Items für eigene Rätsel. Wie sie im Spiel verdrahtet werden, steht in
  [`docs/UNITY_INTEGRATION.md`](docs/UNITY_INTEGRATION.md).
* Statisch (Bibliothek): `vent_shaft`, `floor_grate`, `bulkhead`, `wall_panel`, die Natur-Typen und die Einrichtung.

```bash
# Rätsel-Erweiterung: Knöpfe, Zahnräder, Kraftfeld, Tresor + die passenden Items
python -m cubegen generate --recipe recipes/escape_extras.json
python -m cubegen generate --seed 7 --types gear_puzzle,spare_part --count 4 --param spare_part.kind=gear
```

## Fallen, Rätsel, Bau-Kit, Items & Geräte

17 weitere Typen. Alle nutzen die vorhandenen Scripts (oder sind statisch), die begehbaren haben
[Collider](#collider).

| Kategorie | Typen |
|---|---|
| `puzzle` – Fallen | `crusher` (Presse: `Door` lässt den Kopf `Panel` auf die Bodenplatte fallen, `openOffset` = (0, −Hub, 0)), `saw_blade` (Sägeblatt `Rotor` mit `Rotator` in einem Bodengehäuse, Warnlicht blinkt), `steam_vent` (Bodenrost oder geplatztes Rohr; leeres `Steam` = Partikel-Emitter nach Unity-oben, optional Absperrventil `Wheel`), `shock_plate` (Strom-Bodenplatte mit Glow-Raster und Spulen) |
| `puzzle` – Rätsel | `combination_lock` (Zahlenschloss: 3–5 Ringe `Dial_<n>`, `Rotatable` mit 36°-Schritten, Code in `meta.code`), `sliding_puzzle` (Schieberätsel 3×3 / 4×4: `Tile_<n>`, lösbar gemischt, Anordnung in `meta.layout`, Raster in `meta.pitch_m`), `balance_scale` (Waage: `Beam` neigt sich, Schalen `Pan_A` / `Pan_B` mit `Slot_A` / `Slot_B`), `freq_dial` (Frequenz-Regler: Oszilloskop `Screen`, Knöpfe `Dial_<n>`), `switch_panel` (Schalterpult: Kippschalter `Switch_<n>`, Zielmuster in `meta.pattern`) |
| `environment` – Bau-Kit | `spiral_stairs` (Wendeltreppe 270°/360°/450° mit Handlauf und Podest), `railing` (Geländerstück 1/2/4 m: Stäbe, Holme oder Glas), `cage` (Gitterkäfig, Tür `Panel` schwenkt per `Rotatable` auf, Schloss-Licht `Glow` an der Tür) |
| `props` – Items (`ItemPickup`) | `flashlight` (Taschenlampe oder Laterne), `key` (Bart-, moderner oder Röhrenschlüssel, optional Anhänger), `cable_reel` (Kabelrolle, optional auf Spule) |
| `props` – Geräte (statisch) | `coffee_machine` (auf Theke oder stehend), `vending_machine` (Getränke- / Snackautomat) |

* Schon vorhanden und deshalb nicht neu: T-/Kreuzstück (`pipe_bend`), Luftschleuse (`door` Stil `airlock`),
  Schreibtisch (`table` Stil `desk`), Fass (`canister`), Lochwand (`workbench` mit `pegboard`).
* **Wandmontiert** (`combination_lock`, `sliding_puzzle`, `freq_dial`, `switch_panel`): Rückseite an der Wand bei
  y = +0,1, Pivot am Boden darunter.

```bash
python -m cubegen generate --recipe recipes/traps_riddles.json
```

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
Für Teile an der Decke gibt es `@model(..., pivot="wall", view="below")`: Previews und Icons zeigen sie dann von unten.
Danach `python -m unittest discover -s tests` – die Tests prüfen jeden Typ auf gültige Materialien, nach außen
zeigende Normalen, Pivot-Konvention und Determinismus.

## Projektstruktur

```
cubegen/
├── cli.py            Kommandozeile (generate / list / params / check / families / doctor)
├── families.py       Modellfamilien: Maße, Auflösung, Anschlüsse, Passungsprüfung
├── family_data/      mitgelieferte Familien (station, foundry, lab)
├── contract.py       Sidecar-Vertrag des Unity-Imports (+ Prüfung gegen die FBX)
├── fbxread.py        FBX-Leser (Hierarchie, Transformationen, Vertices) für die Prüfungen
├── quality.py        Qualitätsbericht (Dreiecke, Draw Calls, Z-Fighting)
├── variety.py        ähnliche Varianten erkennen (--unique)
├── pipeline.py       Batch: Seeds -> Blender -> ImageMagick -> manifest.json
├── seeds.py          deterministische Seed-Ableitung
├── geometry.py       reine Python-Geometrie (Box, gefaste Box, Lathe, Zylinder, Prisma …)
├── asset.py          Asset = benannte Objekte mit Pivots / Parents
├── materials.py      M_…-Materialtabelle des Spiels
├── params.py         Parameter (festlegen statt würfeln) und globaler Stil
├── textures.py       ImageMagick-Kacheltexturen (optional)
├── bake.py           läuft IN Blender: gebackene Atlas-Texturen pro Asset (optional)
├── models/           Modelltypen (props, industrial, tech, environment, ruins, puzzle, kit, furniture,
│                     robots, nature, mechanisms, items, structure, machinery, gameplay) + wear, destruction
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
