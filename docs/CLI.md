# Kommandozeile (`cubegen`) – Anleitung

Diese Anleitung erklärt die Kommandozeile Schritt für Schritt, von der Installation bis zum fertigen
Unity-Ordner. Alle Optionen auf einen Blick stehen am Ende unter [Alle Optionen](#alle-optionen).

## 1. Installieren

Voraussetzungen: **Python ≥ 3.9**, **[Blender](https://www.blender.org/download/) ≥ 3.6** und
**[ImageMagick](https://imagemagick.org)** (macOS: `brew install imagemagick`). Python-Pakete braucht es keine.

```bash
git clone https://github.com/ffunkfabian-hash/lowpoly_cubeescape_model_generatior.git
cd lowpoly_cubeescape_model_generatior
python3 -m cubegen doctor
```

`doctor` zeigt, ob Blender und ImageMagick gefunden werden und welche Render-Engines laufen. Findet es Blender
nicht, gib den Pfad an (`--blender /Applications/Blender.app/Contents/MacOS/Blender`) oder setze ihn einmal
für die Shell: `export BLENDER=/Applications/Blender.app/Contents/MacOS/Blender`.

Die Desktop-GUI startest du mit `cubegen gui` oder dem installierten Befehl `cubegen-gui`. Sie benötigt Tkinter
(bei manchen Linux-Distributionen als separates `python3-tk`-Paket) und verwendet dieselbe CLI-Pipeline.

Alternativ als Befehl `cubegen` installieren (dann ohne `python3 -m`, aber ohne die Rezepte aus `recipes/`):

```bash
pip install "git+https://github.com/ffunkfabian-hash/lowpoly_cubeescape_model_generatior.git"
cubegen doctor
```

## 2. Die sechs Befehle

| Befehl | Wofür |
|---|---|
| `cubegen gui` | Desktop-Oberfläche für Modellwahl, Rezepte, Qualitäts-Vorabprüfung und Export |
| `python3 -m cubegen generate …` | Modelle erzeugen (FBX, Icons, Kontaktbogen, Übersichts-.blend) |
| `python3 -m cubegen list` | alle Modelltypen nach Kategorie (`--json` für Skripte) |
| `python3 -m cubegen params [TYP]` | Parameter aller Typen bzw. eines Typs, z. B. `params lever` |
| `python3 -m cubegen check` | Qualitätsbericht: Dreiecke, Draw Calls, flackernde Flächen, Collider, Doppelte (Abschnitt 14); `--family` prüft die Passung eines Kits, `--export` einen fertigen Export gegen den Unity-Vertrag |
| `python3 -m cubegen contract` | Der Unity-Importvertrag als JSON (`cubegen/contract.json`); `--out DATEI` schreibt ihn für den Import des Spiels |
| `python3 -m cubegen families` | Modellfamilien mit Maßen, Stil und Kit (`--dims`: alle Maße und welche Parameter sie setzen) |
| `python3 -m cubegen palettes` | Farbpaletten des Paletten-Modus (`--swatches DATEI`: Farbfelder zum Vergleichen) |
| `python3 -m cubegen doctor` | Installation prüfen |

`--help` geht überall: `python3 -m cubegen generate --help`.

## 3. Der erste Lauf

```bash
python3 -m cubegen generate --seed 42 --types crate,socket,drone --count 3
```

Das erzeugt je 3 Varianten von Kiste, Sockel und Drohne in `output/seed_42/`:

```
output/seed_42/
├── models/      Crate_000.fbx, Crate_000.cubegen.json (Teile, Pivots, Script-Werte für Unity) …
├── icons/       Icon_Crate_000.png (256 × 256, transparent)
├── previews/    rohe Blender-Renders
├── contact_sheet.png         alle Previews mit Namen - hier zuerst reinschauen
├── materials.png             Material-Übersicht
├── CubeEscape_Generated_42.blend   alle Assets im Raster
└── manifest.json             Seeds, Dateien, Maße, Dreiecke, Parameter
```

Tipp: Vorher mit `--dry-run` ansehen, was entstehen würde. Das geht in Sekunden und braucht kein Blender:

```bash
python3 -m cubegen generate --seed 42 --types crate,socket,drone --count 3 --dry-run
```

Für eine ausführliche Prüfung ohne Export (ebenfalls ohne Blender) nutze `--validate-only`. Der JSON-Report
enthält je Asset Fehler/Warnungen, Qualitätsstufe, reproduzierbaren Asset-Hash sowie Versions- und Quellcode-Metadaten:

```bash
python3 -m cubegen generate --seed 42 --types crate,door --validate-only --report validation.json
```

`--strict` führt dieselbe Prüfung vor dem Export aus und bricht bei Warnungen ab; Standard bzw. `--relaxed`
erlaubt Warnungen. `--repair-safe` entfernt nur nicht referenzierte leere Mesh-Objekte und protokolliert die
Reparaturen im Report. Es ändert keine Hierarchien oder Behaviour-/Collider-Referenzen.

Jedes Asset im Validierungsreport enthält außerdem einen Qualitätsscore von 0 bis 100, den Rang innerhalb seines
Typs und `similar_to`, falls eine zuvor geplante Variante innerhalb der Ähnlichkeitstoleranz liegt. Score und Rang
fassen Dreiecksbudget, Draw Calls, Z-Fighting und Collider-Abdeckung zusammen; Fehler und Warnungen bleiben separat
ausgewiesen.

### Clutter-/Accessoire-Pass

Für `table`-Assets setzt `--clutter` kleine separate Props auf die explizit freigegebene
Tischfläche. Die Verteilung ist seed-deterministisch; `clean`, `lived-in` und `chaotic`
steuern die Ziel-Dichte. In Rezepten wird dieselbe Einstellung unter `style.clutter`
gesetzt. Der erste Pass unterstützt intakte Tisch- und Labortisch-Varianten; bei
beschädigten Modellen ist Clutter absichtlich nicht erlaubt.

```bash
python3 -m cubegen generate --seed 42 --types table --count 3 \
    --param table.style=table --clutter lived-in --no-render
```

Die Accessoires werden als getrennte `Clutter_*`-Mesh-Objekte in den Export aufgenommen,
nicht mit dem Tisch-Mesh verschmolzen. Die Typen `tool`, `spare_part` und `keycard` können
weiterhin einzeln über `--types` exportiert werden. Platzmangel führt nicht zu
Randüberschreitungen oder Überlappungen: nicht platzierbare Props werden als `skipped` im
Sidecar ausgewiesen.

## 4. Was erzeugt wird: Typen, Anzahl, Varianten

| Option | Beispiel | Wirkung |
|---|---|---|
| `--types` | `--types door,wall,pillar` | nur diese Typen (`--types all` = alle) |
| `--count` | `--count 4` | Varianten pro Typ: `_000` … `_003` |
| `--pick` | `--pick crate:3,door:7` | genau diese Varianten (gleiche Namen und Seeds wie mit `--count`) |
| `--unique` | `--count 12 --unique` | Varianten überspringen, die wie eine frühere aussehen |
| ohne `--types`/`--pick`/Rezept | | je 1 Variante von **allen** Typen |

**Doppelte vermeiden:** Bei manchen Typen (Kamera, Laser-Spiegel, Taschenlampe …) sehen Varianten mit
verschiedenen Seeds fast gleich aus. `--unique` nimmt nur Varianten, die sich von allen vorherigen unterscheiden:
andere Teile, andere Materialien oder Dreiecke, oder Maße, die um mehr als 8 % bzw. 3 cm abweichen.
Die Namen bleiben die ihres Index (`LaserMirror_000`, `_001`, `_002`, `_003`, `_006` …), also lässt sich jede
Variante mit `--pick` genau so wieder bauen. Im Add-on heißt das „Nur unterschiedliche“.

Ablauf in der Praxis: erst viele Varianten ansehen, dann die guten gezielt exportieren.

```bash
# ansehen
python3 -m cubegen generate --seed 7 --types pipe_fitting --count 12 --no-blend
# behalten
python3 -m cubegen generate --seed 7 --pick pipe_fitting:2,pipe_fitting:9 --prefix Gen_
```

## 5. Seeds

* `--seed` ist der **Master-Seed** des ganzen Batches. Zahl oder Text: `--seed 42`, `--seed level-3`.
* Gleiche Kommandozeile = gleiche Dateien. `--count` erhöhen oder Typen hinzufügen ändert keine bestehenden
  Assets (`Crate_002` bleibt `Crate_002`).
* Ohne `--seed` wird gewürfelt; der Seed steht dann in der ersten Zeile der Ausgabe und im `manifest.json`.
* Gleicher Seed = gleiches Modell, auch mit einer anderen Python-Version: Blender (Python 3.11) und die
  Kommandozeile (3.9 bis 3.13) bauen bitgenau dieselben Modelle. Die Tests prüfen das mit Fingerabdrücken
  aller Typen (`tests/golden.json`).

## 6. Eigenschaften festlegen (`--param`)

Normalerweise würfelt der Seed alles. Mit `--param TYP.NAME=WERT` legst du einzelne Eigenschaften fest, der Rest
der Variante bleibt, wie der Seed ihn gemacht hat. Welche Parameter ein Typ hat, zeigt `params`:

```bash
python3 -m cubegen params door
python3 -m cubegen generate --seed 42 --pick door:3 \
    --param door.style=airlock --param door.width=2.0 --param door.speed=0.8
python3 -m cubegen generate --seed 7 --types pipe_fitting --count 6 \
    --param pipe_fitting.kind=elbow --param pipe_fitting.tile=1.0
```

Ja/Nein-Werte: `true/false`, `ja/nein`, `on/off`, `1/0`. Parameter mit 🔗 in der README (bzw. `[Unity]` in
`params`) landen als Script-Werte in der `<Name>.cubegen.json`, z. B. Drehtempo oder Türgeschwindigkeit.

**Varianten vorhandener Typen** sind ebenfalls Parameter. Ohne Angabe bauen sie das bisherige Modell:

| Typ | Parameter | Werte |
|---|---|---|
| `wall` | `opening`, `opening_x` | `door` (Ausschnitt in Rahmengröße der Tür: `door_style`, `door_width`, `door_height`), `window` (`window_width`, `window_height`, `window_sill`, mit Glas), `pipe` (Rohrdurchführung: `duct_radius`, `duct_height`) |
| `wall` | `height`, `thickness` | Wandhöhe und -stärke (Standard 3,0 / 0,5 m) |
| `catwalk` | `shape`, `rail_height` | `corner` (L), `tee`, `cross`, `landing` (Podest), `end` (Endstück mit Abschlussgeländer) |
| `stairs` | `layout` | `landing` (Zwischenpodest), `quarter` (Vierteldrehung), `switchback` (gegenläufig, Wendepodest) |

```bash
python3 -m cubegen generate --seed 7 --types wall --count 3 --param wall.opening=door --param wall.door_width=2.0
python3 -m cubegen generate --seed 7 --types catwalk --param catwalk.shape=tee
```

**Item-IDs:** Items mit `ItemPickup` (`item`, `keycard`, `key`, `tool`, `clue`, `spare_part`, `flashlight`,
`cable_reel`) brauchen im Spiel eine `itemId`, die genau ein `ItemData` bezeichnet. cubegen erfindet keine:

```bash
python3 -m cubegen generate --seed 42 --pick keycard:0 --param keycard.item_id=ITEM_ID_AUS_UNITY
```

## 7. Einheitlicher Look (Stil für alle Typen)

```bash
python3 -m cubegen generate --seed 7 --size L --snap 0.5 --glow cyan --material-style metal \
    --warning none --wear light --detail low
```

**Raum-Thema:** Statt alles einzeln festzulegen, gib dem Raum ein Thema. Das ist ein beliebiger Name, aus dem
Glow-Farbe, Material, Abnutzung und Warnfarbe einmal für alle Modelle gewürfelt werden. So passen alle Teile
eines Raums zusammen:

```bash
python3 -m cubegen generate --seed 7 --theme labor-3 --types crate,machine,pipe,wall --count 4
# theme 'labor-3': glow red, material wall, wear light, warning per asset
python3 -m cubegen generate --seed 7 --theme labor-3 --glow cyan     # einzeln festgelegt geht vor
```

| Option | Werte | Wirkung |
|---|---|---|
| `--theme` | beliebiger Text | würfelt Glow-Farbe, Material, Abnutzung, Warnfarbe einmal für alle |
| `--size` | S / M / L | kleine / mittlere / große Varianten |
| `--snap` | z. B. 0.5 | Hauptmaße auf Vielfache runden (passt ins Modulraster) |
| `--glow` | cyan / red / orange | Deko-Glow in einer Farbe; Status-Lichter behalten ihre Zustandsfarbe |
| `--material-style` | metal / wall / dark / light | bevorzugtes Körpermaterial |
| `--warning` | none / always | Warnstreifen nie oder immer |
| `--wear` | none / light / heavy | Schutt, lose Platten, Kabel um das Modell |
| `--detail` | low / normal / high | weniger oder mehr Polygone |
| `--damage` | intact / damaged / destroyed / fractured | beschädigt, Ruine (statisch, ohne Scripts) oder in Bruchstücke `Fragment_<nn>` zerlegt, die Unity bei Zerstörung herausfallen lässt |
| `--generation` | 1 / 2 / 3 | Modell-Generation (Standard 3 = mit Ankern `Audio_*`/`FX_*` für Ton und Effekte); 2 = ohne Anker, 1 = Modelle wie mit cubegen 0.9.0 exportiert, bitgleich |

**Text auf Modellen** (Parameter, ohne Angabe bleibt alles wie bisher): `--param sign.text=B-12` (Schild mit
Text), `--param door.label=LAB-3` (Raumnummer über der Tür), `--param countdown.text=EVAKUIERUNG`,
`--param "floor_plan.title=DECK 3"`. Erlaubt sind A–Z, Ä Ö Ü, 0–9 und `- + . : / _ ' ! #`.

**Schwenken statt Drehen**: `--param camera.sweep=120` bzw. `--param turret.sweep=120` schwenkt Kamerakopf bzw.
Geschütz um ±60° hin und her (`Rotator.arc`), ohne `speed` mit 30 °/s.

## 8. Modellfamilien und Bau-Kits

Eine **Familie** legt fest, was zusammenpassen muss: Wandhöhe und -stärke, Modullänge, Tür- und
Fensteröffnungen samt Rahmenmaß, Laufstegbreite, Geländer- und Ebenenhöhe, Plattformgröße, Rohrradius und
Achshöhe, dazu Material, Glow, Warnfarbe, Abnutzung, Detailgrad und Texturset. Ein gemeinsamer Seed allein
genügt dafür nicht, die Passung kommt aus den verbindlichen Maßen (`python3 -m cubegen families --dims`
zeigt, welches Maß welche Parameter setzt).

Mitgeliefert: `station`, `foundry`, `lab` und mit Requisiten im Kit `medbay` (Krankenstation), `derelict`
(verlassenes Wrack, beschädigt), `greenhouse` (Gewächshaus) und `reactor` (`python3 -m cubegen families`). Alle
Kits enthalten außerdem Torbogen, Wandabschluss, Sockelleiste, Decken-/Dachmodul und Rampe.

```bash
# A: das ganze Kit (Wände mit Tür/Fenster/Rohr, Tür, Portal, Stegstücke, Treppen, Brücke, Plattformen,
#    Rohre, Becken, Falle, Container) - gleiche Kommandozeile = gleiche Dateien
python3 -m cubegen generate --family station --seed 42 --prefix Gen_
# B: Varianten innerhalb der Familie durchsehen: Details wechseln, Maße und Materialien bleiben
python3 -m cubegen generate --family station --types catwalk,stairs --count 8
# C: ein passendes Teil zu einem vorhandenen Modell (übernimmt dessen Maße und Look)
python3 -m cubegen generate --match output/seed_42/models/Gen_Pipe_003.cubegen.json --types pipe_bend
python3 -m cubegen generate --family station --types door        # die Tür zur Wand der Familie
```

**Eigenes Kit, eigene Familie:** Eine Familie ist ein Rezept mit `"family"` und `"dims"`
(`cubegen/family_data/station.json` als Vorlage; eigene Familien unter `./families/<Name>.json`). Ein Rezept
mit `"family": "station"` baut darauf auf. Was es selbst festlegt (`dims`, `style`, `params`), gilt als
**Abweichung** und steht so im Manifest. Kit-Einträge dürfen eigene Parameter haben:

```json
{
  "family": "station",
  "dims": { "door_width": 2.4 },
  "models": [
    { "type": "wall", "count": 2 },
    { "type": "wall", "pick": [2], "params": { "opening": "door" } },
    { "type": "door", "count": 1 },
    { "type": "keycard", "pick": [0], "params": { "item_id": "ITEM_ID_AUS_UNITY" } }
  ]
}
```

Namen bleiben `<Typ>_<Index>`, Seeds hängen nur von Master-Seed, Typ und Index ab: Neue Teile im Kit
verändern keine bestehenden.

**Prüfen:** `python3 -m cubegen check --family station` setzt die Teile des Kits aneinander und prüft
Breiten, Höhen und Ausrichtung der Anschlüsse, die obere Ebene (`deck_height`), begehbaren Boden über jeder
Fuge (auch an Rampen), dass nichts den Durchgang über der Fuge blockiert, Tür und Portal in der
Wandöffnung (Rahmen = Ausschnitt, lichte Öffnung frei), Rohre durch Durchführungen, Wandabschluss auf der Wand,
Sockelleiste an der Wandfläche, Decke an Decke, und den gemeinsamen Look. `generate --family` schreibt dasselbe ins Manifest (`family.fit`); dazu `family` (Name, Datei, Maße,
Abweichungen) und pro Modell `param_sources` (woher jeder Parameter kommt: `dims.<Maß>`, `family`,
`recipe`, `kit`, `cli`) und `connectors` (Anschlusspunkte in Unity-Koordinaten).

## 9. Direkt ins Unity-Projekt

```bash
python3 -m cubegen generate --seed 7 --prefix Gen_ \
    --models-dir  ../CubeEscape/Assets/Art/Models \
    --library-dir ../CubeEscape/Assets/Art/Models/Library \
    --icons-dir   ../CubeEscape/Assets/Art/Icons
```

* `--models-dir`: Modelle mit Script (Tür, Ventil, Sockel, Drohne …) - dort lädt sie `AddModel`.
* `--library-dir`: reine Deko (`"static": true`) automatisch nach `Library/<Kategorie>`.
* `--prefix Gen_` verhindert Namenskollisionen mit den handgebauten Modellen.
* `--lods`: Deko ohne Script bekommt eine zweite, sparsamere Stufe in derselben FBX (Teile `<Teil>_LOD0` /
  `<Teil>_LOD1`). Unity baut daraus beim Import automatisch eine LODGroup. Die Sparstufe ist dasselbe Modell mit
  `--detail low`, im Median 30 % weniger Dreiecke, bei Wänden bis knapp 70 %. Sie entsteht nur, wenn sie mindestens
  15 % spart. Modelle mit Script bekommen keine, weil sich deren Teile in der Sparstufe nicht mitbewegen würden.
* Jede exportierte FBX wird nach dem Export zurückgelesen und mit ihrer `<Name>.cubegen.json` verglichen
  (Eltern, Pivots, Rotation 0, Vertices). Weicht etwas ab, bricht der Export mit einer Meldung ab, statt eine
  Datei zu schreiben, die Unity ablehnen würde.
* Den Editor-Import für Unity baust du mit dem Prompt aus [`UNITY_INTEGRATION.md`](UNITY_INTEGRATION.md).

## 10. Rezepte (Batches als Datei)

Statt langer Kommandozeilen: eine JSON-Datei. Beispiele liegen in `recipes/`.

```bash
python3 -m cubegen generate --recipe recipes/puzzle_room.json
python3 -m cubegen generate --recipe recipes/building_kit.json --models-dir ../CubeEscape/Assets/Art/Models
```

```json
{
  "_comment": "Level 3, Labor",
  "seed": "level-3",
  "formats": ["fbx"],
  "prefix": "Gen_",
  "unique": true,
  "style": { "theme": "labor-3", "snap": 0.5 },
  "params": { "door": { "style": "airlock", "width": 2.0 } },
  "models": { "door": [0, 7], "wall": 4, "socket": 2 }
}
```

`models` nimmt eine Anzahl (`"wall": 4`) oder bestimmte Varianten (`"door": [0, 7]`, wie `--pick`). Schlüssel,
die mit `_` beginnen, sind Kommentare.

Weitere Schlüssel: `scale`, `blend`, `render`, `engine`, `render_size`, `samples`, `icon_size`,
`icon_background`, `icon_azimuth`, `icon_elevation`, `icon_zoom`, `models_dir`, `library_dir`, `icons_dir`,
`textures`, `texture_size`, `texture_set`, `textures_dir`, `unique`, `lods`, `jobs`, `out`, `family`, `dims`. Optionen auf der
Kommandozeile überschreiben das Rezept (z. B. `--seed`, `--count`, `--models-dir`).

Rezepte werden geprüft: Ein Tippfehler bricht mit einem Hinweis ab, statt still ignoriert zu werden, z. B.
`unknown key 'stlye' (did you mean 'style'?)`.

## 11. Texturen (optional)

```bash
# Kacheltexturen, 1 Kachel = 1 m
python3 -m cubegen generate --seed 42 --textures tiled --texture-size 1024
# pro Asset gebacken (langsamer)
python3 -m cubegen generate --seed 42 --types machine --textures baked
# ein Material mit Farbpalette pro Modell: 1 Draw Call (reines Python, auch mit --no-blender)
python3 -m cubegen generate --seed 42 --textures palette
python3 -m cubegen check --palette        # Draw Calls im Paletten-Modus
# eine andere Farbpalette (schaltet den Paletten-Modus mit ein): Material MP_Palette_Rust
python3 -m cubegen generate --seed 42 --palette rust
python3 -m cubegen palettes --swatches palettes.png   # alle Paletten, eine Zeile Farbfelder pro Palette
```

Ohne `--textures` tragen die Modelle die einfarbigen `M_…`-Materialien des Spiels. Im Paletten-Modus behalten Glas
und Teile, die die Scripts umfärben (Status-Lichter, Glow), ihr eigenes Material. Details in der README.

**Backen auf CPU oder GPU** (`--bake-device auto|cpu|gpu`, Standard `auto`): Cycles backt eine zusammengefügte Kopie
aller Teile eines Assets, eine Sitzung je Durchgang statt je Teil. `auto` nimmt ab 1024 px die GPU (Metal, CUDA …),
darunter die CPU – gemessen in 0.15.0 auf einem Apple M5: 512 px CPU 14 s gegen GPU 19 s, 1024 px CPU 19 s gegen
GPU 10 s, 2048 px CPU 73 s gegen GPU 27 s. CPU und GPU rauschen verschieden; jedes Gerät liefert aber bei jedem Lauf
dieselben Pixel. Das Manifest nennt je Modell das Gerät (`bake_device`).

**Farbpaletten** (`--palette NAME`): `standard` (die Farben des Spiels, `MP_Palette`), `rust`, `frost`, `toxic`,
`medical`, `derelict`, `greenhouse`, `neon`. Alle Paletten haben dieselben Farbzellen, die Modelle sind also
identisch, nur das Material heißt `MP_Palette_<Name>` und hat eigene Bilder (`MP_Palette_<Name>_Albedo.png` …,
`CubeEscape_Palette_<Name>.json`). Mehrere Paletten können im selben Texturordner liegen. Familien bringen eine
passende Palette mit (`foundry` → `rust`, `lab` → `frost`, `reactor` → `toxic`, `medbay` → `medical`, `derelict`
→ `derelict`, `greenhouse` → `greenhouse`); sie gilt nur, wenn der Paletten-Modus gewählt ist
(`--family foundry --textures palette`). In Rezepten und Familien: `"palette": "neon"`.

![Farbpaletten](palettes.png)

## 12. Previews und Icons

| Option | Wirkung |
|---|---|
| `--icon-angle=-25,15` | Kamera: Azimut, Elevation in Grad (Standard 33,31). Bei negativen Werten `=` verwenden |
| `--icon-zoom 1.3` | näher heran |
| `--icon-size 512`, `--icon-bg '#2b2b33'` | Icon-Größe und Hintergrund (Standard transparent) |
| `--render-size 512`, `--samples 64` | Größe und Qualität der Previews |
| `--engine cycles` | Render-Engine; `auto` fällt ohne GPU auf Cycles zurück |
| `--no-render` | keine Previews, Icons, Kontaktbogen (schnell) |

Deckenteile (`ceiling_panel`, `hanging_crystals`, `ceiling_module`) werden automatisch von unten gezeigt.

## 13. Schnell und ohne Blender

```bash
# nur FBX + JSON, schnell
python3 -m cubegen generate --seed 42 --types all --no-render --no-blend
# 4 Blender-Prozesse gleichzeitig
python3 -m cubegen generate --seed 42 --types all --count 3 --jobs 4
# reines Python: OBJ + MTL
python3 -m cubegen generate --seed 42 --types crate --no-blender
```

**Nur Geändertes neu bauen:** Ein erneuter Lauf in denselben Ausgabeordner exportiert und rendert nur Modelle,
die sich geändert haben. Den Ausschlag geben Seed, Parameter, Stil, Ausgabeordner, Formate, Render- und
Textur-Einstellungen, Blender-Version und der cubegen-Code selbst. Unverändertes wird übernommen
(`unchanged since the last run: 240 asset(s)`). Bei Blender-Exporten startet Blender gar nicht erst, wenn keine
Änderungen vorliegen; beim reinen OBJ-Export werden unveränderte Meshes ebenfalls übernommen. `--force` baut
alles neu.

Auch die Bilder entstehen nur bei Bedarf neu: Kacheltexturen, Icons, Kontaktbogen und Material-Übersicht werden
übernommen, wenn ihre Eingaben gleich sind und die Dateien noch genau so auf der Platte liegen
(`textures unchanged`, `icons: 0 new, 6 reused`). Die Schlüssel stehen in `.cubegen_cache.json` im Ausgabe- und im
Texturordner (Unity übergeht Dateien mit Punkt). Alle PNG-Dateien sind bei gleicher Eingabe bytegleich – ImageMagick
schreibt keine Zeitstempel hinein.

**Parallel:** `--jobs 4` startet 4 Blender-Prozesse; ein weiterer baut nur die Übersichts-.blend. Die Modelle sind
Arbeitspakete, das größte zuerst: Jeder Prozess nimmt sich das nächste freie, bis keins mehr übrig ist. ImageMagick
läuft darin mit einem Thread. Das Ergebnis ist dasselbe wie mit einem Prozess. Wie viele sich lohnen, hängt von CPU-Kernen und Render-Engine ab.

**Zeiten:** Jeder Lauf schreibt die Dauer seiner Stufen ins Manifest (`timings`: Planung, Texturen, Blender, Bilder
als Wanduhrzeit; Bauen, Backen, Export, Vorschau aus den Blender-Prozessen summiert) und vergleicht sie mit einem
Budget je Modell (`STAGE_BUDGETS` in `cubegen/pipeline.py`, etwa das Dreifache der Messung von 0.15.0). Eine zu
langsame Stufe meldet `warning: bake took … s, budget … s`, der Lauf bricht nicht ab.

`--no-blender` braucht nur Python (und ImageMagick für die Material-Übersicht). Es entstehen OBJ-Dateien ohne
Pivots, Previews und Icons - gut zum schnellen Ausprobieren.

## 14. Qualität prüfen

```bash
python3 -m cubegen check                      # alle Typen, je 10 Varianten von Seed 42
python3 -m cubegen check --types door,laser_mirror --count 20 --detail high
python3 -m cubegen check --json > quality.json
python3 -m cubegen check --export ../CubeEscape/Assets/Art/Models   # fertiger Export gegen den Unity-Vertrag
```

| Spalte | Bedeutung |
|---|---|
| `tris` / `budget` | höchste Dreieckszahl der Varianten / Budget der Kategorie (bei `--detail high` × 1,5) |
| `draws` | Draw Calls: Materialien pro Objekt, summiert; statische Modelle: ein Material einmal (`*` = über dem Budget: 16, bei vielen beweglichen Teilen 2 pro Teil + 2) |
| `z-fighting` | Flächenpaare, die in derselben Ebene liegen, in dieselbe Richtung zeigen und sich überdecken - sie flackern im Spiel. Gezählt nur, wenn man es sieht (verschiedene Materialien oder Objekte); Unterseiten auf dem Boden zählen nicht |
| `distinct` | wie viele der Varianten sich wirklich unterscheiden (siehe `--unique`) |

Der Befehl endet mit Fehlercode 1, wenn ein Typ sein Dreiecksbudget überschreitet. Flackernde Flächen gibt es
keine mehr: Der Generator hebt bündig aufliegende Details um 2 mm an; die Tests prüfen das für alle Typen und
Zustände.

**Collider:** Unter der Tabelle stehen die Typen mit massiver Geometrie außerhalb jedes Colliders, in die der
Spieler hineinlaufen würde (mit Teil und Ausdehnung). Gezählt werden geschlossene Teile ab 0,05 m³ und 15 cm
Stärke; ein Raster von Punkten im Teil muss in einem Collider liegen (5 cm Toleranz). Nicht gezählt: `Damage`
(nur bei defekter Maschine sichtbar), Türblätter ohne eigene Collider (die Tür-Einrichtung im Spiel gibt sie
ihnen) und bei Plattformen alles unter dem Boden. Die Tests prüfen das für alle Typen und Zustände.

`check --export <Ordner>` liest jede `<Name>.cubegen.json` darunter (mit ihrer FBX) und prüft sie wie der
Unity-Import: Fehler führen zu Fehlercode 1, offene Item-IDs werden nur gemeldet. Der Export selbst prüft das
schon, bevor er Dateien schreibt.

## 15. Probleme lösen

| Meldung / Problem | Lösung |
|---|---|
| `Blender not found` | `--blender PFAD` oder `export BLENDER=PFAD`; `doctor` prüft es |
| `ImageMagick` nicht gefunden | installieren bzw. `--magick /opt/homebrew/bin/magick` |
| `unknown model type` | Schreibweise prüfen: `python3 -m cubegen list` |
| `unknown parameter` / Wert außerhalb | `python3 -m cubegen params TYP` zeigt Namen und Bereiche |
| Previews schwarz / sehr langsam | `--engine cycles --samples 16` oder `--no-render` |
| Blender-Fehler ohne Details | mit `-v` erneut starten, dann steht die Blender-Ausgabe im Terminal |
| `unknown key '…' (did you mean …)` | Tippfehler im Rezept oder in `style` |
| `unknown measure '…'` / `… can't follow …` | Maß-Name in `dims` falsch bzw. ein Typ kann das Maß nicht (z. B. `pipe_radius` 0.4: Rohre gibt es nur mit 0.09 / 0.18 / 0.35 m) |
| `family fit: … don't fit` | die genannten Teile passen nicht zusammen (meist eine Abweichung in `params`/`dims`); Details: `python3 -m cubegen check --family NAME` |
| `… does not match its rig data` | Blender hat eine FBX geschrieben, die nicht zur `.cubegen.json` passt (z. B. eine neue Blender-Version mit geändertem FBX-Export). Bitte mit der Meldung als Issue melden |
| Modell sieht nach einem Update anders aus | sollte nicht passieren (`tests/golden.json`); sonst bitte melden |

## Alle Optionen

`python3 -m cubegen generate …`

| Option | Standard | Bedeutung |
|---|---|---|
| `--seed` | zufällig | Master-Seed (Zahl oder Text) |
| `--recipe` | – | JSON-Rezept |
| `--family` | – | Modellfamilie (Name oder Datei), siehe Abschnitt 8 |
| `--match` | – | passendes Teil zu einem vorhandenen `<Name>.cubegen.json` |
| `--types` | alle | Typen, kommagetrennt, oder `all` |
| `--count` | 1 | Varianten pro Typ |
| `--pick` | – | einzelne Varianten `TYP:INDEX,…` |
| `--unique` | – | ähnlich aussehende Varianten überspringen |
| `--param` | – | `TYP.NAME=WERT`, mehrfach |
| `--theme` | – | Raum-Thema, siehe Abschnitt 7 |
| `--size`, `--snap`, `--glow`, `--material-style`, `--warning`, `--wear`, `--detail`, `--damage`, `--generation` | Seed (Generation: 3) | Stil, siehe Abschnitt 7 |
| `--textures`, `--texture-size`, `--texture-set`, `--textures-dir` | none, 512 | Texturen (none / tiled / baked / palette), siehe Abschnitt 11 |
| `--palette` | standard | Farbpalette im Paletten-Modus (schaltet ihn ein), siehe Abschnitt 11 |
| `--out` | `output/seed_<seed>` | Ausgabeordner |
| `--models-dir`, `--library-dir`, `--icons-dir` | im Ausgabeordner | Zielordner, siehe Abschnitt 8 |
| `--formats` | fbx | `fbx`, `glb`, `gltf`, `obj`, kommagetrennt |
| `--prefix` | – | Namenspräfix, z. B. `Gen_` |
| `--scale` | 1.0 | Skalierung (1 = Meter) |
| `--lods` | – | Sparstufe für statische Modelle (`_LOD0` / `_LOD1`), siehe Abschnitt 8 |
| `--jobs` | 1 | Blender-Prozesse gleichzeitig (Arbeitspakete, größtes Modell zuerst) |
| `--bake-device` | auto | Cycles-Gerät für `--textures baked`: auto (GPU ab 1024 px), cpu, gpu |
| `--force` | – | alles neu bauen statt Unverändertes zu übernehmen |
| `--no-blend` | – | keine Übersichts-.blend |
| `--no-rig-data` | – | keine `<Name>.cubegen.json` |
| `--no-blender` | – | reines Python, nur OBJ |
| `--no-render` | – | keine Previews / Icons / Kontaktbogen |
| `--engine` | auto | auto / workbench / eevee / cycles |
| `--render-size`, `--samples` | 384, 32 | Preview-Größe und Samples |
| `--icon-size`, `--icon-bg` | 256, transparent | Icons |
| `--icon-angle`, `--icon-zoom` | 33,31 / 1 | Kamera für Previews und Icons |
| `--blender`, `--magick` | automatisch | Programmpfade |
| `--dry-run` | – | nur Namen, Seeds und Maße ausgeben |
| `--validate-only` | – | Assets prüfen, Report ausgeben, keinen Export starten |
| `--strict` / `--relaxed` | – | Warnungen als Fehler behandeln / explizit erlauben (Standard: erlaubt) |
| `--repair-safe` | – | nur verwaiste leere Mesh-Objekte entfernen und protokollieren |
| `--report FILE` | – | Build-Manifest bzw. Validierungsreport als JSON schreiben |
| `-v`, `--verbose` | – | Blender-Ausgabe zeigen |
