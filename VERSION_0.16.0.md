# Cubegen 0.16.0 – Overdrive

*ungeprüft: Unity-Abnahme offen* – Generator-Code geändert (Parallelbetrieb, Bilder, Backen, Prüfung) und neue macOS-App.
Unveröffentlicht, Branch `release/0.16.0`; vorherige Version [0.15.0](VERSION_0.15.0.md) (lokal committet, nicht
veröffentlicht). Ab dieser Version tragen Cubegen-Versionen coole englische Namen (Regel in `AGENTS.md`).

## Inhalt

Die restlichen Leistungs-Erfahrungen des Roboter-Generators (Punkte 1–7 des Abgleichs nach 0.15.0) und eine App nach dem
Vorbild des Robot Viewers, die wie das Desktop-Fenster Modelle erzeugt.

### Leistung (Punkte 1–7)

Gemessen am 12. Oktober 2026 auf dem Apple M5 (4 Performance- + 6 Effizienzkerne). Während der Messungen liefen
zeitweise Unity-Prozesse anderer Sitzungen (Last bis 64); Vergleiche deshalb abwechselnd oder als CPU-Zeit, Last je
Messung notiert.

| Punkt | Umsetzung | Messung |
|---|---|---|
| 1 · `--jobs auto` (Standard) | `pipeline.auto_jobs`: bis Kerne − 1, nur so viele, wie sich lohnen (≥ 2 s Arbeit je Prozess, Start ≈ 0,6 s); CPU-Backen höchstens 2, GPU-Arbeit höchstens 3 | Station-Kit gebacken (CPU), 1/2/3/4/6/9 Prozesse: 74/69/70/73/72/77 s – Cycles nutzt schon alle Kerne; 186 Typen Export: 6,1 s (1) → 4,6 s (3); mit Vorschau 38,5 → 33,6 s |
| 2 · ImageMagick parallel | Texturen je Material, Icons je Modell, Kontaktbogen in Blöcken zu 4 Zeilen – je Aufruf ein Thread (`ImageMagick.single_threaded`) | Texturen 512 px: 11,4 → 5,1 s (Last 30); Kontaktbogen 186 Modelle: 20,4 → 2,1 s, pixelgleich; Bildnachlauf 186 Modelle: 16,4 → 4,1 s |
| 3 · Stufen überlappen | Blender-Prozesse starten, während ImageMagick die Kacheltexturen baut (`textures.plan_texture_set`, Bereit-Datei); Texturen und Blender je mit eigener Zeit, `timings.overlap` | 186 Typen, 1024 px: die 8 Prozesse warteten noch 10,7 s – Start, Szene und Materialien liefen in der Texturzeit |
| 4 · Ein Back-Durchgang weniger | Rauheit (rot) und Metall (grün) in einem Emissions-Durchgang (`bake._surface_bake`) | 4 statt 5 Durchgänge; gebackene Karten bytegleich zu 0.15.0 (6 Modelle verglichen) |
| 5 · Messung | `timings.load` (Last bei Start/Ende, Kerne, Warnung über der Kernzahl), `timings.workers` (Modelle und Sekunden je Blender-Prozess), `tools/profile_run.py` (cProfile) | – |
| 6 · `-t 1` ohne Backen | gemessen, nicht übernommen | 186 Typen Export: 2,7/3,2 s mit gegen 2,9/3,3 s ohne; mit Vorschau 21,3/22,1 gegen 22,2/23,1 s – innerhalb der Streuung |
| 7 · Qualitätsprüfung | Hüllquader-Vorfilter vor der Flächenprüfung (nur für Flächen, die sich ein Ebenenfach teilen), Strahl-Ebenen einmal je Teil (`quality.ray_faces`) | `check --count 3`: 3,3 → 2,1 s CPU (−35 %); `test_golden` 8,1 → 7,1 s CPU; Prüf-JSON und 745 erzeugte Dateien bytegleich |

**numpy:** bewusst nicht eingebaut. Die heißen Stellen arbeiten auf kleinen Flächengruppen (Umwandlung in Arrays kostet
mehr, als sie spart), und `fix_z_fighting` bestimmt die Modellgeometrie – eine andere Summationsreihenfolge könnte
Grenzfälle kippen und die Golden-Daten brechen. Robogens Idee (billiger Hüllquader-Test vor der teuren Prüfung) ist in
reinem Python umgesetzt, mit identischem Ergebnis. Ein erster Versuch, die Hüllquader für alle Flächen vorab zu rechnen,
war langsamer (2,5 Mio. `min`/`max`-Aufrufe); sie entstehen jetzt nur bei Bedarf.

### macOS-App (`app/`)

`Cubegen.app` nach dem Vorbild des Robot Viewers (SwiftUI + SceneKit, `swiftc` ohne Xcode-Projekt, universal
arm64 + x86_64, macOS 13+, ad-hoc signiert, 3,5 MB). Erzeugt Modelle wie das Desktop-Fenster `cubegen gui`:

| Bereich | Inhalt |
|---|---|
| Seitenleiste | Modelltypen nach Kategorie (deutsche Namen, ImageMagick-Symbol je Kategorie) mit Filter, Alle/Keine; Familie; Rezept; Seed, Varianten, Ausgabeordner (Finder); Texturen mit Größe, Palette, Backgerät; Stil aus allen Auswahloptionen von `cubegen catalog`; ähnliche Varianten, strikte Prüfung, alles neu, nur OBJ, Blender-Prozesse |
| Aktionen | Vorab prüfen (Qualitätsranking wie das Desktop-Fenster), Assets erzeugen ⌘R, Abbrechen ⌘. |
| Ansicht | 3D (SceneKit, OBJ + MTL) mit Iso/Vorne/Seite/Oben, Drehteller, Boden, Screenshot; Fortschritt aus dem Protokoll; Galerie der Icons; Protokoll |
| Daten | mitgeliefertes cubegen-Paket, Python 3.9+ aus Homebrew/python.org/Kommandozeilenwerkzeugen; Einstellungen bleiben zwischen Starts, der letzte Lauf erscheint wieder |
| Symbole | `app/make_icons.sh`: 22 Symbole und das App-Icon per ImageMagick (keine SF Symbols) |

Kommandozeilen-Modi für Tests (wie `RobotViewer --snapshot`): `--version`, `--catalog`, `--print-args`, `--run`,
`--snapshot`, `--ui-snapshot`.

## Prüfung

- `python3 -m unittest discover -s tests`: **281 Tests grün**, keiner übersprungen (Blender 5.2.2, ImageMagick 7.1.2),
  373 s bei Last 7–11, am 12. Oktober 2026. Neu: `tests/test_release_0160.py` (8 Tests).
- `app/test_app.sh`: **17 von 17 grün** – Version von App und Paket, Katalog über das mitgelieferte Paket,
  Kommandozeile gegen Fixtures, Fehlermeldung ohne Auswahl, Textur-Argumente gleich `cubegen.gui.texture_args`
  (5 Fälle), 3D-Snapshot (Modell deckt > 5 % des Bildes), Fenster offscreen, ImageMagick-Symbol je Kategorie, Lauf
  mit Blender über den Prozess-Runner der App (FBX, OBJ, Vorschau, Icon, Fortschritt 2/2), Materialfarben einer
  Blender-OBJ in der 3D-Ansicht, Lauf ohne Blender, Vorabprüfung mit Ranking.
- Sichtprüfung: Fenster per `--ui-snapshot` (1470 × 956, 1280 × 800) und 3D-Ansicht per `--snapshot` angesehen;
  korrigiert: gemischtes Erscheinungsbild (Seitenleiste ohne Hintergrund), englische Kategorie- und Optionsnamen,
  leere Auswahllisten (`theme`, `snap`) ausgeblendet.
- Nach dem ersten Test von Hand (Nutzer) korrigiert: **3D-Ansicht ohne Farben** – Blenders MTL setzt `Ka 1 1 1`
  (weißes Umgebungslicht wusch alles aus), und ModelIO verändert die linearen Farben beim Laden (Warnorange
  0,17 → 0,125); die App liest die MTL jetzt selbst (`Kd`, `Ke`, `map_Kd`), rechnet nach sRGB um und zeigt Farben
  und Kacheltexturen wie die Icons. **Typenliste mittig** – jedes Kästchen war nur so breit wie sein Name und wurde
  in der Gruppe zentriert; jetzt linksbündig. **Abgeschnittene Knöpfe** („Dre…“) – Drehteller, Boden, Protokoll
  und Screenshot sind Symbolknöpfe mit Tooltip.
- Bytegleichheit: gebackene Karten und Kacheltexturen gegen 0.15.0, Prüf-JSON und 745 erzeugte Dateien gegen den
  Stand vor der Prüf-Optimierung, Kontaktbogen am Stück gegen Blöcke (1–50 Bilder).

## Grenzen

- Zeiten unter wechselnder Fremdlast (Unity-Shader-Compiler anderer Sitzungen); als Größenordnung verwenden.
- Die App ist ad-hoc signiert (nicht notarisiert): auf einem anderen Mac beim ersten Start per Rechtsklick › Öffnen.
- Die interaktive Bedienung (Klicks im Fenster) ist nicht automatisiert geprüft; die Testmodi decken Start, Lauf,
  Ergebnis und Darstellung ab.
- Unity-Import in der Cube-Escape-Testkopie steht aus (Stufe 2).

## Lokaler Test (Stufe 2)

```text
Abnahme und Release nach Cubegen-AGENTS.md (Stufe 2):
Branch: release/0.16.0 · Version: 0.16.0 „Overdrive“ · PR: noch keiner (Branch nicht gepusht)
Tag: v0.16.0 · Release-Branch: release/0.16.0 · Umfang: Abnahme und Release (0.15.0 „Stoppuhr“ ist enthalten)
Vor dem Merge noch offen:
- Unity-Import in der Cube-Escape-Testkopie: Station-Kit mit --textures baked (512 px) und eine Auswahl mit Kacheltexturen 1024 px neu exportieren, importieren, Materialien/Texturen und Wiederimport ohne Fehler
- App von Hand: output/app/Cubegen.app öffnen, Typen wählen, Assets erzeugen, Galerie und 3D-Ansicht, Vorab prüfen, Abbrechen
- Sichtprüfung: Kontaktbogen und gebackene Karten gegen 0.14.2
Abnahme: eigener Worktree; volle Python-Suite mit Blender und ImageMagick ohne übersprungene Tests, app/test_app.sh, echte
Exporte der geänderten Typen, Sichtprüfung, Import und Physik in der Cube-Escape-Testkopie, Berichte VERSION_0.15.0.md und
VERSION_0.16.0.md auf Endstand, Vermerk „ungeprüft“ entfernen, committen, Branch pushen.
Stopp: Bleibt etwas rot oder ist eine Richtungsfrage offen – anhalten und fragen, nicht releasen.
Release: Datum statt „unveröffentlicht“, git merge --no-ff in main, Tag, Push von main, Release-Branch und Tag ohne --force.
Abschlussbericht auf Deutsch: was geändert wurde, wie geprüft (Tests, Anzahl, Ergebnis), Merge-, Tag- und PR-Stand mit Links, was offen ist.
```
