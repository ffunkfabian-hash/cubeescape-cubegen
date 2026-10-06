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

Alternativ als Befehl `cubegen` installieren (dann ohne `python3 -m`, aber ohne die Rezepte aus `recipes/`):

```bash
pip install "git+https://github.com/ffunkfabian-hash/lowpoly_cubeescape_model_generatior.git"
cubegen doctor
```

## 2. Die vier Befehle

| Befehl | Wofür |
|---|---|
| `python3 -m cubegen generate …` | Modelle erzeugen (FBX, Icons, Kontaktbogen, Übersichts-.blend) |
| `python3 -m cubegen list` | alle 104 Modelltypen nach Kategorie (`--json` für Skripte) |
| `python3 -m cubegen params [TYP]` | Parameter aller Typen bzw. eines Typs, z. B. `params lever` |
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

## 4. Was erzeugt wird: Typen, Anzahl, Varianten

| Option | Beispiel | Wirkung |
|---|---|---|
| `--types` | `--types door,wall,pillar` | nur diese Typen (`--types all` = alle) |
| `--count` | `--count 4` | Varianten pro Typ: `_000` … `_003` |
| `--pick` | `--pick crate:3,door:7` | genau diese Varianten (gleiche Namen und Seeds wie mit `--count`) |
| ohne `--types`/`--pick`/Rezept | | je 1 Variante von **allen** Typen |

Ablauf in der Praxis: erst viele Varianten ansehen, dann die guten gezielt exportieren.

```bash
python3 -m cubegen generate --seed 7 --types pipe_fitting --count 12 --no-blend     # ansehen
python3 -m cubegen generate --seed 7 --pick pipe_fitting:2,pipe_fitting:9 --prefix Gen_   # behalten
```

## 5. Seeds

* `--seed` ist der **Master-Seed** des ganzen Batches. Zahl oder Text: `--seed 42`, `--seed level-3`.
* Gleiche Kommandozeile = gleiche Dateien. `--count` erhöhen oder Typen hinzufügen ändert keine bestehenden
  Assets (`Crate_002` bleibt `Crate_002`).
* Ohne `--seed` wird gewürfelt; der Seed steht dann in der ersten Zeile der Ausgabe und im `manifest.json`.

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

## 7. Einheitlicher Look (Stil für alle Typen)

```bash
python3 -m cubegen generate --seed 7 --size L --snap 0.5 --glow cyan --material-style metal \
    --warning none --wear light --detail low
```

| Option | Werte | Wirkung |
|---|---|---|
| `--size` | S / M / L | kleine / mittlere / große Varianten |
| `--snap` | z. B. 0.5 | Hauptmaße auf Vielfache runden (passt ins Modulraster) |
| `--glow` | cyan / red / orange | Deko-Glow in einer Farbe; Status-Lichter behalten ihre Zustandsfarbe |
| `--material-style` | metal / wall / dark / light | bevorzugtes Körpermaterial |
| `--warning` | none / always | Warnstreifen nie oder immer |
| `--wear` | none / light / heavy | Schutt, lose Platten, Kabel um das Modell |
| `--detail` | low / normal / high | weniger oder mehr Polygone |
| `--damage` | intact / damaged / destroyed | beschädigt bzw. Ruine (statisch, ohne Scripts) |

## 8. Direkt ins Unity-Projekt

```bash
python3 -m cubegen generate --seed 7 --prefix Gen_ \
    --models-dir  ../CubeEscape/Assets/Art/Models \
    --library-dir ../CubeEscape/Assets/Art/Models/Library \
    --icons-dir   ../CubeEscape/Assets/Art/Icons
```

* `--models-dir`: Modelle mit Script (Tür, Ventil, Sockel, Drohne …) - dort lädt sie `AddModel`.
* `--library-dir`: reine Deko (`"static": true`) automatisch nach `Library/<Kategorie>`.
* `--prefix Gen_` verhindert Namenskollisionen mit den handgebauten Modellen.
* Den Editor-Import für Unity baust du mit dem Prompt aus [`UNITY_INTEGRATION.md`](UNITY_INTEGRATION.md).

## 9. Rezepte (Batches als Datei)

Statt langer Kommandozeilen: eine JSON-Datei. Beispiele liegen in `recipes/`.

```bash
python3 -m cubegen generate --recipe recipes/puzzle_room.json
python3 -m cubegen generate --recipe recipes/building_kit.json --models-dir ../CubeEscape/Assets/Art/Models
```

```json
{
  "seed": "level-3",
  "formats": ["fbx"],
  "prefix": "Gen_",
  "style": { "snap": 0.5, "wear": "light" },
  "params": { "door": { "style": "airlock", "width": 2.0 } },
  "models": { "door": 3, "wall": 4, "socket": 2 }
}
```

Weitere Schlüssel: `scale`, `blend`, `render`, `engine`, `render_size`, `samples`, `icon_size`,
`icon_background`, `icon_azimuth`, `icon_elevation`, `icon_zoom`, `models_dir`, `library_dir`, `icons_dir`,
`textures`, `texture_size`, `texture_set`, `textures_dir`, `out`. Optionen auf der Kommandozeile überschreiben
das Rezept (z. B. `--seed`, `--count`, `--models-dir`).

## 10. Texturen (optional)

```bash
python3 -m cubegen generate --seed 42 --textures tiled --texture-size 1024     # Kacheltexturen, 1 Kachel = 1 m
python3 -m cubegen generate --seed 42 --types machine --textures baked          # pro Asset gebacken (langsamer)
```

Ohne `--textures` tragen die Modelle die einfarbigen `M_…`-Materialien des Spiels. Details in der README.

## 11. Previews und Icons

| Option | Wirkung |
|---|---|
| `--icon-angle=-25,15` | Kamera: Azimut, Elevation in Grad (Standard 33,31). Bei negativen Werten `=` verwenden |
| `--icon-zoom 1.3` | näher heran |
| `--icon-size 512`, `--icon-bg '#2b2b33'` | Icon-Größe und Hintergrund (Standard transparent) |
| `--render-size 512`, `--samples 64` | Größe und Qualität der Previews |
| `--engine cycles` | Render-Engine; `auto` fällt ohne GPU auf Cycles zurück |
| `--no-render` | keine Previews, Icons, Kontaktbogen (schnell) |

Deckenteile (`ceiling_panel`, `hanging_crystals`) werden automatisch von unten gezeigt.

## 12. Schnell und ohne Blender

```bash
python3 -m cubegen generate --seed 42 --types all --no-render --no-blend    # nur FBX + JSON, schnell
python3 -m cubegen generate --seed 42 --types crate --no-blender            # reines Python: OBJ + MTL
```

`--no-blender` braucht nur Python (und ImageMagick für die Material-Übersicht). Es entstehen OBJ-Dateien ohne
Pivots, Previews und Icons - gut zum schnellen Ausprobieren.

## 13. Probleme lösen

| Meldung / Problem | Lösung |
|---|---|
| `Blender not found` | `--blender PFAD` oder `export BLENDER=PFAD`; `doctor` prüft es |
| `ImageMagick` nicht gefunden | installieren bzw. `--magick /opt/homebrew/bin/magick` |
| `unknown model type` | Schreibweise prüfen: `python3 -m cubegen list` |
| `unknown parameter` / Wert außerhalb | `python3 -m cubegen params TYP` zeigt Namen und Bereiche |
| Previews schwarz / sehr langsam | `--engine cycles --samples 16` oder `--no-render` |
| Blender-Fehler ohne Details | mit `-v` erneut starten, dann steht die Blender-Ausgabe im Terminal |

## Alle Optionen

`python3 -m cubegen generate …`

| Option | Standard | Bedeutung |
|---|---|---|
| `--seed` | zufällig | Master-Seed (Zahl oder Text) |
| `--recipe` | – | JSON-Rezept |
| `--types` | alle | Typen, kommagetrennt, oder `all` |
| `--count` | 1 | Varianten pro Typ |
| `--pick` | – | einzelne Varianten `TYP:INDEX,…` |
| `--param` | – | `TYP.NAME=WERT`, mehrfach |
| `--size`, `--snap`, `--glow`, `--material-style`, `--warning`, `--wear`, `--detail`, `--damage` | Seed | Stil, siehe Abschnitt 7 |
| `--textures`, `--texture-size`, `--texture-set`, `--textures-dir` | none, 512 | Texturen, siehe Abschnitt 10 |
| `--out` | `output/seed_<seed>` | Ausgabeordner |
| `--models-dir`, `--library-dir`, `--icons-dir` | im Ausgabeordner | Zielordner, siehe Abschnitt 8 |
| `--formats` | fbx | `fbx`, `glb`, `gltf`, `obj`, kommagetrennt |
| `--prefix` | – | Namenspräfix, z. B. `Gen_` |
| `--scale` | 1.0 | Skalierung (1 = Meter) |
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
| `-v`, `--verbose` | – | Blender-Ausgabe zeigen |
