# Changelog

## 0.27.0 „Fieldbook“ – 2026-10-15

Doku und ein Werkzeug: der Entwicklerhintergrund zieht aus `docs/CLI.md` › 16 in ein eigenes Doc, und
`tools/unity_check.py` hält die Sperre für schwere Läufe bis zum letzten Enkelprozess. Code der Generierung, Geometrie,
Materialien und Sidecars bleiben wie in 0.26.1 (bis auf die Versionsangabe). Bericht: [VERSION_0.27.0.md](VERSION_0.27.0.md).

* **`docs/DEVELOPER.md` neu:** Abschnitte 1–8 (vorher CLI.md 16.1–16.8) wörtlich übernommen; `docs/CLI.md` (Bedienung)
  verlinkt nur noch darauf. Verweise in `AGENTS.md` heißen jetzt „DEVELOPER.md n“.
* **Die Sperre für schwere Läufe hält bis zum letzten Enkelprozess** (gemeinsam mit Cube Escape 0.61.3, Roboter-Generator
  1.20.5 und Toolgen 0.4.0; Befund eines Codex-Reviews von Toolgen 0.4 „Fieldstrip“): Der Unity-Schritt des Checks läuft
  in einer eigenen Prozessgruppe (`run_in_group`), TERM/HUP/INT gehen an die ganze Gruppe, und der Schritt endet erst,
  wenn die Gruppe leer ist. Vorher beendete ein Signal nur den Check selbst – die Sperre war frei, während `verify.sh`
  und Unity weiterliefen. Neue Tests: `tests/test_release_0270.py`.

## 0.26.1 „Stockpile“ – 2026-10-15

Nur Doku: `AGENTS.md` (in jeder Sitzung geladen) von 462 auf 281 Zeilen; Code, Geometrie, Materialien und Sidecars
bleiben wie in 0.26.0 (bis auf die Versionsangabe). Bericht: [VERSION_0.26.1.md](VERSION_0.26.1.md).

* **`AGENTS.md` kürzer:** Versionsliste (steht im Changelog), Messwerte, Begründungen und lange Beispiele aus „Leistung und
  Grenzen“, „Blender-Batch schnell halten“, „Gemeinsamer Cache“, „Variantensets“, „Anstriche“, „macOS-App“, Unity-Check
  (schwerer Lauf, Neural Engine) und GitHub Actions stehen jetzt in `docs/CLI.md` › 16 „Entwicklerhintergrund“; in
  `AGENTS.md` bleiben die Regeln und je ein Verweis (16.x).

## 0.26.0 „Stockpile“ – 2026-10-15

Cache, Werkzeuge und CI; Geometrie, Materialien und Sidecars bleiben wie in 0.25.0 (bis auf die Versionsangabe).
Bericht: [VERSION_0.26.0.md](VERSION_0.26.0.md).

* **Blender-Ergebnisse im gemeinsamen Cache:** Export(e), gebackene und angestrichene Karten und Vorschau eines Modells
  sind eine Einheit im Cache von 0.25.0 – ein neuer Ordner oder Worktree bekommt sie von dort, statt Blender bauen zu
  lassen (Anstrich, sechs Modelle, 512 px: 13,4–15,1 s → 1,8–2,0 s). Schlüssel aus jeder Eingabe des Blender-Workers
  (Auftrag und Spec, Ordner als Rollen, Code ohne Versionszeile, Blender, ImageMagick, Plattform). Nur das FBX ist
  ordnergebunden: der Cache hält es mit `<cubegen:textures>` statt des Texturordners (`cubegen/fbxpath.py`), ein Treffer
  setzt den neuen ein. Weichen nur Formate, Vorschau oder Anstrich-Farben ab, kommt wenigstens das Backen samt
  Atlas-UVs aus dem Cache. `--force` und `CUBEGEN_CACHE=0` wie bisher.
* **GitHub Actions:** ein Job je Lauf – Push auf `main`: Stufe `quick` (vorher vier Jobs, 17–19 min), PR: die ganze
  Suite mit Blender in einem Job, „Run workflow“ mit Wahl `quick`/`standard`/`full`; `app/**` löst keinen Lauf aus.
* **Release-Befehl** `tools/release.py`: Probelauf mit allen Prüfungen (Versionen, Changelog-Datum, saubere Checkouts,
  `main` aktuell, Tag frei, keine Datei über 100 MB, keine Zugangsdaten), `--apply` merged, taggt und pusht atomar.
* Repo-Name `cubeescape-cubegen` in `AGENTS.md`, `README.md`, `docs/CLI.md` und `tools/install.sh`.

## 0.25.0 „Quartermaster“ – 2026-10-15

Test- und Cache-Werkzeuge; Geometrie, Materialien und Sidecars bleiben wie in 0.24.0 (bis auf die Versionsangabe).
Bericht: [VERSION_0.25.0.md](VERSION_0.25.0.md).

* **Gemeinsamer Cache:** Texturen, Icons, Kontaktbogen, Set-Reihen und Material-Übersicht liegen inhaltsadressiert in
  `~/Library/Caches/Cubegen/cache` (Linux `$XDG_CACHE_HOME/cubegen/cache`) – ein neuer Ausgabeordner oder Worktree, die
  App und der Unity-Check bekommen sie von dort. `CUBEGEN_CACHE` verlegt (`0`: aus), `CUBEGEN_CACHE_LIMIT_GB` begrenzt
  (Standard 4, am längsten Unbenutztes zuerst, nichts aus den letzten zwei Stunden). Atomare Schreibvorgänge, keine
  absoluten Pfade in Schlüsseln (der Texturordner fiel heraus), Bildschlüssel hängen am Bildcode statt am ganzen
  Generator, Vorschauen zählen mit ihrem Bildinhalt (Blenders Renderstempel). `.cubegen_cache.json` Format 2 mit
  relativen Pfaden. Einmalige Übernahme der Caches von 0.24.0; `python3 -m cubegen cache` (`--prune`, `--migrate`).
* **Tests ohne Auslassen:** `tools/run_tests.py` führt die Module mit numpy in einer eigenen Gruppe mit einem Python aus,
  das numpy hat (auf dem Mac Blenders), nennt die Interpreter und jeden übersprungenen Test mit Grund; eigene Gruppe
  `pipeline`; jeder Lauf mit eigenem, frischem Cache.
* **Ein schwerer Lauf zur Zeit:** `tools/unity_check.py` wartet vor Unity auf Cube Escapes Sperre
  `~/Library/Caches/CubeEscape/heavy-run.lock` (Cube Escape 0.59), zeigt den Halter, vererbt sie nie;
  `CE_HEAVY_LOCK=0` überspringt.
* `AGENTS.md`: Abschnitte „Gemeinsamer Cache“ und „Aufträge an andere Sitzungen“ (Vorlage), Sperre beim Unity-Check.

## 0.24.0 „Primer“ – 2026-10-14

Zuarbeit für Cube Escape 0.57 Phase 3 „Anstrich“ (Cube Escape `Docs/MATERIALS.md`, Punkte 2, 3, 4, 6, 7).
Bericht: [VERSION_0.24.0.md](VERSION_0.24.0.md).

* **Neutrale Karten für den Umfärbe-Shader (ToDo 27):** `--paint` schreibt je Modell fünf gepackte Karten
  `MTN_<Modell>_W0/W1[/W2]/Fields/Normal.png` – Gewichte der Spielmaterialien (RGB), **Rauschen** (W0.a) und
  **Detail** (W1.a) als Kanal, AO/Kante/oben/Höhe in einem RGBA (`cubegen/neutral.py`). Die fertigen `MTP_`-Karten
  entstehen jetzt aus genau diesen 8-Bit-Werten (höchstens 5/255 anders als 0.23); `paint.compose` bleibt die Formel.
* **Vertrag Version 3:** `textures.neutral`, `textures.weight_layout`, Wurzelschlüssel `paint` (Name oder eigenes
  Thema als Daten), Abschnitte `neutral_maps`, `materials`, `paint_scheme`, `textures`; `--contract 2`/`1` schreiben
  wie bisher (Fixture `tests/fixtures/contract_v2.json`). `cubegen catalog --paints`: die Themen ohne Modellbau.
* **Eigene Materialnamen statt `M_Crystal` (ToDo 28):** `M_Liquid`, `M_Hologram`, `M_Lamp`, `M_Leaf`, `M_Biolume`,
  `M_Signal`, `M_Accent`, `M_Optic` (Werte wie `M_Crystal`) in 20 Typen; `M_Crystal` ist nur noch echter Kristall.
  Golden-Daten dieser Typen neu (nur Namen; mit `--contract 2` bitgleich zu 0.23, Fixture `golden_0230_crystal.json`).
* **Vergleichsbilder:** `tools/paint_reference.py` setzt jedes Thema aus den neutralen Karten eines Laufs ohne
  Blender zusammen (`--check`: bitgleich zu Blenders Karten).
* **Unity-Check:** Prüfsatz `neutral` (Vertrag 3; unter Version 3 erwartet abgelehnt, mit Cube Escapes Version
  angenommen), Vergleichsbilder je Anstrich-Prüfsatz.

## 0.23.0 „Wingman“ – 2026-10-14

* **Agenten-Werkzeuge** (mit Cube Escape 0.56 und dem Roboter-Generator 1.18): Subagents `cg-test-runner` (Tests
  ausführen und berichten, ändert nichts) und `cg-doc-keeper` (Doku auf Endstand, nur Markdown) in `.claude/agents/`,
  Werkzeuge je Agent in `.claude/agent-guard.json`. Gemeinsames Plugin `ce-shared` (privates Repo
  `ffunkfabian-hash/ce-agent-tools`): Force-Push, nacktes `git stash`, Unity auf Checkouts und GitHub Actions kommen
  von dort statt aus eigenen hookify-Dateien. Generator und Ausgabe unverändert.
  Bericht: [VERSION_0.23.0.md](VERSION_0.23.0.md).

## 0.22.0 „Beacon“ – 2026-10-14

Zuarbeit für Cube Escape 0.57 (gemeinsamer Shader-Unterbau) und 0.58 (Cubegen in der Werkbank), nur die Generatorseite.
Bericht: [VERSION_0.22.0.md](VERSION_0.22.0.md).

* **Leuchtkarte im Vertrag (ROADMAP ToDo 26):** `cubegen/contract.json` Version 2 mit Abschnitt `baked_maps`
  (erlaubte und Pflichtkarten, sRGB-Karten, `Emission` ab Version 2, `emission_intensity` 3, eine Datei je Karte).
  Der Sidecar nennt bei `--paint` die Leuchtkarte (`textures.baked.Emission`); `check_sidecar` und `check --export`
  prüfen die Karten samt Dateien. Nur Themen mit Leuchtkanten (`edge_glow` > 0) schreiben die Karte – bisher entstand
  bei Industrial, Clean, Ruin, Organic und Sand eine schwarze Karte, die im GLB eine Textur des Werkbank-Budgets
  belegte. **Rückweg für den heutigen Import:** `generate --contract 1` (Rezeptfeld `contract`), `contract --version
  1`, `check --export … --contract 1`; `tools/unity_check.py` schreibt für die Version, die Cube Escape hält.
* **Manifestformat 2 (ToDo 16, 25, 30, 31):** `format`; `sets[].faces_unity` (geprüfte Anschlussseiten in Unity:
  Richtung und Abstand vom Pivot) und `sets[].bounds`; `models[].set`; `joins` (welche Anschlussarten zusammenpassen);
  `connectors[].moves` (Anschluss auf bewegtem Teil, z. B. ausgefahrene Brücke – fiel bisher weg); `dressings`
  (Anbau-Parameter je Typ, passendes Thema) und `models[].dressing`. Nur Ergänzungen; Format in
  `docs/UNITY_INTEGRATION.md` › „Manifest für Cube Escape“.
* Ein Modell ohne gebackenes Material im Modus `baked` (nur Glow, Kristall oder Glas) bekommt keinen `textures`-Eintrag
  mehr – der Import verlangt im Modus `baked` die Karten.
* `.DS_Store` in `.gitignore`.

## 0.21.3 „Monolith“ – 2026-10-14

* **GitHub Actions sparsam:** Nach 14 Tagen Oktober waren 90 % der 2.000 Freiminuten verbraucht (rund 40 min je Lauf
  mit 13 Jobs, Pushes auf PR-Branches liefen doppelt). Jetzt: `push` nur auf `main`, sonst über den PR; ein neuer
  Push bricht den alten Lauf ab; reine Doku löst nichts aus; ein Job je Python-Version mit allen Gruppen parallel;
  ein PR testet Python 3.11 und Blender, die volle Matrix läuft auf `main` und auf Wunsch; `timeout-minutes` je Job.
  Regel global (`~/.claude/CLAUDE.md`) und in `AGENTS.md` („GitHub Actions sparsam“), Hook `actions-sparsam`. Ausgabe unverändert.
  Bericht: [VERSION_0.21.3.md](VERSION_0.21.3.md).

## 0.21.2 „Monolith“ – 2026-10-14

* Test der Kiste mit Kacheln: ImageMagick 6 (GitHub-Runner) schreibt zwei sonst bytegleiche Karten verschieden –
  9 statt 8 Texturen; der Test verlangt 8 nur mit ImageMagick 7, das Budget immer. Ausgabe unverändert.
  Bericht: [VERSION_0.21.2.md](VERSION_0.21.2.md).

## 0.21.1 „Monolith“ – 2026-10-14

* **Texturbudget der Werkbank wie Cube Escape 0.51** (`CubegenTextures`): jede verschiedene (Rolle, Bildinhalt)
  einmal, komprimiert mit 1 Byte je Pixel × 4/3, Metall/Rauheit einmal als Metall-/Glättekarte. Die Kiste mit Kacheln
  in 2048 px (Seed 4242) hat 8 Texturen und 42,7 MB – im Budget; 0.21.0 rechnete 268 MB und warnte. Nur Texturen,
  die ein Material lädt, zählen. Bericht: [VERSION_0.21.1.md](VERSION_0.21.1.md).

## 0.21.0 „Monolith“ – 2026-10-13

Erkenntnisse aus Cube Escape 0.49 „Megastructure“ umgesetzt:

* **Ein Renderer:** `--single-renderer` (CLI, Rezept, App, Desktop-Fenster) macht statische Modelle mit reinen
  Schmuckteilen zu einem Mesh-Objekt mit Untermaterialien – Cube Escape baut sie dann als flache Kopien. Betrifft 53
  von 63 mehrteiligen statischen Typen; zehn behalten Teile mit Bedeutung. Manifest: `renderers` je Modell.
* **Budget der Werkbank in Bytes:** `contract.check_runtime_budget` liest jedes GLB (Bytes, Teile, Materialien,
  Dreiecke, eingebettete Bildgrößen) gegen das Budget von Cube Escape; Warnung beim Erzeugen, `runtime_budget` im
  Manifest, Ausgabe in `check --export`. Fund: Kacheln in 2048 px sprengen den Texturspeicher schon bei einer Kiste.
* **Index statt jede Datei lesen:** Der Cache prüft Größe und Änderungszeit, bevor er eine Datei hasht (Vorschauen,
  geschriebene Bilder).
* **Schritte benennen, Bänder messen:** `timings.steps` im Manifest (Planen, Bauen, Vertrag); `tools/perf_band.py`
  misst feste Arbeitslasten mehrfach mit Lasterkennung und CPU-Zeit.
* **Verzeichnisse statt Suchen:** jedes Modell einmal je Lauf gebaut (vorher dreimal), Set-Mitglieder gruppiert, die
  Flackerprüfung ohne Listensuche, `validate_contract` mit Namensverzeichnis. CPU-Zeit Katalog ohne Blender 4,65 →
  2,57 s, Katalog aus dem Cache 5,91 → 5,02 s.
* Unity-Check: neuer Prüfsatz `single`. Unity-ToDos 32–34. Ausgabe der Modelle ohne die Option unverändert
  (Golden-Daten). Paket, CLI und Add-on auf 0.21.0. Bericht: [VERSION_0.21.0.md](VERSION_0.21.0.md).

## 0.20.0 „Gatekeeper“ – 2026-10-13

* **Unity-Check** `tools/unity_check.py`: acht feste Prüfsätze (Bau-Kit-Sets, Zusatzdetails, Gameplay, Anstrich mit
  Anbauten und Kristallen, eigenes Thema, Kacheln, Schäden, alle Typen als GLB) durch die Tests, die Cube Escape für
  echte Exporte hat – Editor-Import (`CubegenCliIntegrationTests`) und Werkbank-Laufzeit
  (`CubegenRealGenerationTests`), über `verify.sh` in der Testkopie. Bericht `output/unity_check/report.json`.
  Erster Lauf: 254 Modelle, 0 Fehler, knapp 3 min. Fester Schritt jedes Releases (AGENTS.md › Stufe 2).
* Ausgabe der Modelle unverändert (Golden-Daten). Paket, CLI und Add-on auf 0.20.0.
  Bericht: [VERSION_0.20.0.md](VERSION_0.20.0.md).

## 0.19.1 „Kaleidoscope“ – 2026-10-13

* **GitHub Actions wieder grün:** Der Ubuntu-Runner hat ImageMagick 6 – es schrieb Zeitstempel in die PNGs trotz
  `png:exclude-chunks` (Läufe nicht bytegleich), und `magick` fehlt dort. Neu: `imagemagick.strip_png_dates` nach
  jedem Schreiben (unter ImageMagick 7 wirkungslos, bytegleich geprüft); der Bildvergleich im Test nimmt das gefundene
  ImageMagick. Rot war die CI seit 0.17.0. Bericht: [VERSION_0.19.1.md](VERSION_0.19.1.md).

## 0.19.0 „Kaleidoscope“ – 2026-10-13

* **Bau-Kit set-fähig:** Anschlussseiten je Typ (`set_faces`) und festgehaltene Formwahlen (`set_pins`); gewürfelte
  Maße als Parameter ohne Änderung des Zufallsstroms (Boden `depth`, Deckenplatte `thickness`, Kiste `depth`,
  Wandabschluss `overhang`/`cap_height`). Alle 13 Bau-Kit-Typen halten im Set ihren Umriss (0.18: zehn nicht).
  Deckenmodul: Kassettenrippen und Dachfirst ragten 4–5 cm in den Nachbarn – behoben.
* **Anbauten auf Boden, Säule und Steg** (`dressing = ruin | organic`, `cubegen/models/dressing.py`).
* **Kristalle:** facettierter Schliff (`crystal_cut = faceted`; Fels, Schwebeinsel, Hängekristalle, Modulwand) und
  Kristallfarbe je Thema (`crystal_color`, Vorschau, Stiltest, Manifest `paint`).
* **Farbwähler in der App** (`PaintEditor.swift`): eigenes Thema mit Vorschau, gespeichert für `--paint-file`;
  Katalog mit `paint_schemes` und `paint_fields`. `app/test_app.sh`: 25 Prüfungen.
* **Mehr Abwechslung:** Zusatzdetails aus eigenem Zufallsstrom (`cubegen/models/details.py`) für Deckenmodul,
  Warnleuchte, Torbogen, Kamera, Laserspiegel, -empfänger, -teiler und Werkzeug: 6–7 → 9–10 von 10 unterscheidbar.
* **Prüfwerkzeuge:** `tools/vision_report.py` (Neural Engine: Doubletten, Icon-Lesbarkeit; ganzer Katalog in ~10 s),
  GitHub-Job `blender` (Blender 4.5 LTS, Testmodule mit Blender), `app/notarize.sh` (Developer ID nötig).
* Golden-Daten: geändert sind die acht Typen mit Zusatzdetails und das Deckenmodul (Geometrie) sowie Boden,
  Deckenplatte, Kiste und Wandabschluss (nur die neuen Maß-Parameter im Sidecar); alle übrigen unverändert.
  Paket, CLI und Add-on auf 0.19.0. Bericht: [VERSION_0.19.0.md](VERSION_0.19.0.md).

## 0.18.1 „Chameleon“ – 2026-10-13

* **Leuchtschlitz der Modulwand folgt dem Thema:** `test_wall_modules` setzte den Schlitz der Akzentsäule fest auf
  `M_GlowOrange` – ein echter `--paint organic`-Lauf zeigte Orange statt Cyan (der Stiltest färbt Leuchtteile selbst
  um und verdeckte den Fehler). Jetzt nimmt er die Leuchtfarbe des Stils (`--glow`, Thema), ohne Würfelwurf
  (`ParamReader.glow_or`); ohne Vorgabe bleibt er orange. Golden-Daten: nur die Modulwand-Fälle mit Leuchtvorgabe.
  Bericht: [VERSION_0.18.1.md](VERSION_0.18.1.md).

## 0.18.0 „Chameleon“ – 2026-10-13

* **Anstriche auf allen Typen:** geprüft an Boden, Plattform, Säule, Steg, Treppe, Kiste, Tür, Geländer, Decke und
  Modulwand in allen elf Themen ([docs/paint_types_0180.png](docs/paint_types_0180.png)). `M_Ground` ist je Thema ein
  neutraler Grundton statt einer Akzentfarbe (Böden waren orange), die Akzente der Modulwand nutzen `M_HazardOrange`;
  Staub, Moos und Schnee liegen fleckig statt flächig; Toxic dunkler.
* **Eigenes Thema** `--paint-file <Datei.json>` (CLI, Rezept, App, Desktop-Fenster): Name, Grundthema, nur abweichende
  Werte; geprüft wie die eingebauten Themen, im Auftrag an Blender, im Manifest unter `config.paint_scheme`. Beispiel
  `paints/custom_example.json` („Rust Bucket“).
* **Anbauten je Thema** an der Modulwand: `test_wall_modules.dressing = none | ruin | organic` (Rohre und Trümmer,
  Ranken, Steine, Büsche); der Set-Umriss bleibt (45 Varianten geprüft).
* Stiltest: Modelle mit gleichem Parameter, aber anderem Wert bekommen eigene Namen.
* Unity-ToDos 28–30 (Kristallmaterial, Anstriche in der Werkbank, Anbauten im Modell-Browser) in der ROADMAP.
* Golden-Daten: nur `test_wall_modules` geändert. Paket, CLI und Add-on auf 0.18.0.
  Bericht: [VERSION_0.18.0.md](VERSION_0.18.0.md).

## 0.17.0 „Prism“ – 2026-10-13

* **Stiltest Anstriche** (experimentell, `tools/style_test.py`): das Skin-Prinzip des Roboter-Generators für
  Umgebungsmodelle – einmal neutral backen (Gewichtskarten der Spielmaterialien, Umgebungsverdeckung, Kanten,
  „oben“, Detail und Normalen der Kacheltexturen), jeder Anstrich ist Daten (`cubegen/paint.py`: `industrial`,
  `crystal`) und wird in 0,2–0,3 s zusammengesetzt. Vergleich mit dem Konzeptbogen: `docs/style_test_0170.png`.
* **Variantensets** `--set` (auch App und Desktop-Fenster): Varianten mit gleichem Umriss und anderem Innenleben,
  Manifest `sets` mit Umrissprüfung, Reihenbild `set_<Typ>.png`; Regeln in AGENTS.md › „Variantensets“.
* Experimenteller Typ `test_wall_modules`: Modulwand nach dem Konzept, als Set gebaut, optional mit Kristallen.
  Golden-Daten: nur dieser Typ neu, alle 186 übrigen unverändert.
* Stiltest: Höhenmaske (Schmutz von unten), gemaltes Kantenlicht, Reihen-Modus `--row`, Parameter je Modell.
* **Anstriche als Ausgabemodus** `--paint` (CLI, App, Desktop-Fenster): elf Themen nach den Wandkonzepten der drei
  Konzeptbögen (Industrial, Clean, Ruin, Crystal, Dark, Organic, Sand, Space, Ice, Toxic, Void), ein neutraler Back je Modell, Unity liest das Ergebnis wie
  `--textures baked` (im echten Import geprüft); Leuchtkarte und neutrale Karten im Manifest für später (ToDo 26/27).
* Normale Ausgabe der bestehenden Typen und Unity-Vertrag unverändert. Paket, CLI und Add-on auf 0.17.0.
  Bericht: [VERSION_0.17.0.md](VERSION_0.17.0.md).

## 0.16.0 „Overdrive“ – 2026-10-12

* **macOS-App** `app/` (`Cubegen.app`, SwiftUI + SceneKit, wie der Robot Viewer gebaut): erzeugt Modelle wie das
  Desktop-Fenster – Typen nach Kategorie, Familie, Rezept, Seed, Varianten, Texturen, Stil aus dem Katalog,
  Optionen, Vorabprüfung mit Ranking, Fortschritt, Protokoll, Galerie, 3D-Ansicht mit Drehteller und Screenshot.
  Symbole und App-Icon per ImageMagick (`app/make_icons.sh`). `app/build.sh`, `app/test_app.sh` (17 Prüfungen).
  Die 3D-Ansicht liest die MTL selbst und zeigt Materialfarben und Kacheltexturen wie die Icons.
* **`--jobs auto` ist Standard:** bis Kerne − 1 Blender-Prozesse, nur so viele, wie sich lohnen (CPU-Backen
  höchstens 2, GPU-Arbeit höchstens 3). Das Blender-Add-on bietet „0 = automatisch“.
* **ImageMagick parallel:** Kacheltexturen je Material, Icons je Modell, Kontaktbogen in Blöcken (pixelgleich;
  186 Modelle 2 statt 20 s). Blender startet schon, während die Texturen entstehen.
* **Backen:** Rauheit und Metall in einem Durchgang (4 statt 5), Karten bytegleich zu 0.15.0.
* **Messung:** Systemlast und Statistik je Blender-Prozess in `timings`, `tools/profile_run.py`.
* **Qualitätsprüfung** 35 % weniger CPU (Hüllquader-Vorfilter, vorbereitete Strahlflächen), Ergebnis bytegleich.
* Gemessen und nicht übernommen: `-t 1` für Blender-Worker ohne Backen; numpy in der Prüfung (Golden-Daten).
* Versionsnamen ab jetzt cool und englisch (Regel in AGENTS.md). Paket, CLI und Add-on auf 0.16.0.
  Bericht: [VERSION_0.16.0.md](VERSION_0.16.0.md).

## 0.15.0 „Stoppuhr“ – 2026-10-12

* **Behoben:** ImageMagick schrieb Zeitstempel in jede PNG (gleiche Pixel, andere Bytes je Lauf). Jetzt läuft jeder
  Aufruf mit `-define png:exclude-chunks=date,time`; gleiche Eingabe ergibt bytegleiche Dateien.
* **Cache für Bilder:** Kacheltexturen, Icons, Kontaktbogen und Material-Übersicht entstehen nur neu, wenn sich ihre
  Eingaben oder die Dateien geändert haben (`.cubegen_cache.json`, `--force` baut neu). Unveränderter Lauf des
  Station-Kits mit gebackenen Texturen: 8,1 → 1,4 s.
* **Backen:** eine zusammengefügte Kopie je Asset statt einer Cycles-Sitzung je Teil (vielteilige Modelle bis zu
  dreimal schneller); neu `--bake-device auto|cpu|gpu`, `auto` = GPU ab 1024 px (dort 1,8- bis 2,7-mal schneller,
  darunter ist die CPU schneller). Das Rauschen der gebackenen Umgebungsverdeckung ändert sich minimal (RMSE im
  Mittel 0,14 %); Geometrie und Golden-Daten unverändert.
* **`--jobs`:** Modelle als Arbeitspakete, größtes zuerst, statt fester Aufteilung; ImageMagick in den Workern mit
  einem Thread. Eine Blender-Thread-Grenze (`-t`) wurde gemessen und verworfen (langsamer).
* **Zeiten:** `manifest.json` › `timings` mit Dauer und Budget je Stufe, Warnung bei zu langsamen Stufen.
* **Teststufen:** `tools/run_tests.py --tier quick|standard|full` (quick rund 30 s ohne Blender),
  `$CUBEGEN_SKIP_BLENDER=1`; vierte Testgruppe `params`, auch in der CI.
* ROADMAP-Kopf auf aktuellen Stand; AGENTS.md › „Blender-Batch schnell halten“ nachgezogen. Paket, CLI und Add-on auf
  0.15.0. Bericht: [VERSION_0.15.0.md](VERSION_0.15.0.md).

## 0.14.2 „Werkstattbuch“ – 2026-10-12

* Prüfung der Neural Engine (gemeinsam mit Roboter-Generator 1.9.2): Vision-Feature-Prints auf der Neural Engine sind
  schnell (3,8 ms je Bild), taugen aber nicht als Prüfschranke – je Gerät andere Werte, Fehler nicht besser getrennt
  als mit einem exakten Pixelvergleich. Nebenbefund: `--unique` übersieht fast gleich aussehende Varianten, weil die
  Signatur exakt gleiche Dreieckszahlen verlangt.
* ROADMAP: drei offene Punkte – Signatur toleranter (deterministisch, ohne Neural Engine), Doubletten-Bericht und
  Icon-Lesbarkeit per Neural Engine als reine Hinweiswerkzeuge, beide mit Zeitregel (kosten sie zu viel Zeit, werden
  sie nicht umgesetzt). AGENTS.md › „Blender-Batch schnell halten“ ergänzt.
* Nur Doku; Generator, Ausgaben und Golden-Daten unverändert. Paket, CLI und Add-on auf 0.14.2.
  Bericht: [VERSION_0.14.2.md](VERSION_0.14.2.md).

## 0.14.1 „Werkstattbuch“ – 2026-10-12

* `CLAUDE.md` importiert `AGENTS.md` – Claude Code lädt die Regeln jetzt in jeder Sitzung (vorher nur Codex).
* AGENTS.md: Abschnitt „Plugins und Hooks (Claude Code)“ – welches Plugin wofür (quick-gate-python, code-review, github,
  engineering, design, unity, hookify, Blender-MCP), abgestimmt mit Cube Escape 0.45.1 und Roboter-Generator 1.9.1.
* Acht hookify-Regeln in `.claude/`: blockieren Unity auf einem Checkout, nacktes `git stash`, Force-Push und Änderungen
  an `output/`; verlangen die Python-Suite vor dem Sitzungsende; warnen bei Git-Veröffentlichung, Golden-Daten und
  Versionsdateien.
* Nur Doku und Agenten-Werkzeuge; Generator, Ausgaben und Golden-Daten unverändert. Paket, CLI und Add-on auf 0.14.1.
  Bericht: [VERSION_0.14.1.md](VERSION_0.14.1.md).

## 0.14.0 „Werkstattbuch“ – 2026-10-12

* AGENTS.md: neuer Abschnitt „Blender-Batch schnell halten“ mit gemessenen Erfahrungen aus dem Roboter-Generator
  (Cycles-Backen je Objekt, lineare Skins, nicht deterministisches UV-Packen, EEVEE-Wartezeit bei `BLENDED`-Materialien,
  Worker mit `-t 1` und `nice`, ImageMagick mit `MAGICK_THREAD_LIMIT=1`, Messwerkzeuge). ROADMAP: offener Punkt
  „Schnellere Blender-Läufe“ mit den Stellen in cubegen.
* Nur Doku; Generator, Ausgaben und Golden-Daten unverändert. Paket, CLI und Add-on auf 0.14.0.
  Bericht: [VERSION_0.14.0.md](VERSION_0.14.0.md).

## 0.13.0 „Patina“ – 2026-10-10

* Desktop-GUI: Auswahl **Texturen** (keine / Kacheln / Kacheln + Gebrauchsspuren / Farbpalette), Texturgröße und
  Farbpalette – dieselben Arten wie `--textures`; Argumente aus `texture_args()` mit Tests (`tests/test_gui_textures.py`).
* AGENTS.md: Abschluss in zwei Stufen (ungeprüft ohne Blender/Unity, abgenommen lokal) mit fester Vorlage für den
  lokalen Test-Prompt; Werkzeuge ImageMagick (auch zum Gestalten) und Blender-Plugin (MCP) als Prüfstand;
  Texturen sind erlaubt (Standard bleibt einfarbig).
* Paket, CLI, Blender-Quell-Add-on und Add-on-ZIP auf 0.13.0. Bericht: [VERSION_0.13.0.md](VERSION_0.13.0.md).

## 0.12.0 – 2026-10-10

* Release der bisher unveröffentlichten Arbeitsstände 0.11.1–0.11.4 (Einträge unten): erste Asset-Welle, zweite und
  dritte Stationswelle, sieben Modell-Kits, Kollisions- und Modellkorrekturen in Generation 3. Historische
  Generationen 1/2 bleiben unverändert.
* Paket, CLI, Blender-Quell-Add-on und Add-on-ZIP auf 0.12.0. Release-Zweig `release/0.12.0`.
* Prüfung: 258 Python-Tests grün (inkl. Blender-Smoke). Bericht: [VERSION_0.12.0.md](VERSION_0.12.0.md).

## 0.11.4 – veröffentlicht mit 0.12.0

* Standardmodelle in Generation 3: hohle Spindfächer mit Ablagen/Kleiderstange, freier Leitereinstieg am Etagenbett mit verbleibender Absturzsicherung, mittige eingefasste Boden-Wartungsdeckel und budgetgerechte Geländerprofile für Stegkreuzungen. Historische Generationen 1/2 erhalten; fünf neue Geometrie-/Kollisionsregressionen. Details: [VERSION_0.11.4.md](VERSION_0.11.4.md).
* Generation 3: offenes Waschbecken statt Metallplatte, erkennbarer hohler Wasserbehälter an der Kaffeemaschine und feste Halterungen für die Statuspfosten der Ausfahrbrücke. Generation 1/2 bleiben unverändert.
* Familienrezepte mit demselben Dateinamen wie eine eingebaute Familie laden für Overlays ohne eigene `dims` wieder deren Maßvertrag. Eigene Familiendefinitionen bleiben möglich.
* Dritte Stationswelle: zwölf weitere Modelle über `recipes/station_wave3.json`; sieben Kits mit je neun passenden Modellen unter `recipes/kits`. Keine neuen Typen oder Gameplay-Skripte.
* Unity: Portalflächen an tatsächliche Rahmenmaße angepasst, Bodenmontage korrigiert; Kategorien-/Kitsuche und gemerkte Kategorien sowie datenbasierte Kitauswahl. Bericht und Abnahme: [VERSION_0.11.4.md](VERSION_0.11.4.md).

## 0.11.3 – veröffentlicht mit 0.12.0

* Zweite Stationswelle aus IDEEN.md: reproduzierbares Rezept `recipes/station_wave2.json`, 28 zusätzliche
  Exportmodelle aus vorhandenen Typen für Labor, Versorgung, Sicherheit, Natur, Ruinen und stationäre Roboter.
* Kollision `collapsed_catwalk`: Generation 3 ersetzt die reine Bodenbox durch genaue feste Mesh-Collider
  für Steg/Stützen/Geländer und Schutt. Geometrie und Generation 1/2 unverändert; acht Golden-Digests
  gezielt auf den vollständigen Kollisionsvertrag aktualisiert. Bericht: [VERSION_0.11.3.md](VERSION_0.11.3.md).

## 0.11.2 – 2026-10-09

* Erste Asset-Welle aus IDEEN.md: elf neue Typen `airlock_chamber`, `pipe_rack`, `ceiling_beam`, `pressure_tank`,
  `turbine`, `compressor`, `relay_box`, `diagnostics_port`, `coolant_loop`, `warning_beacon`, `emergency_case`
  (186 Typen). Standardmäßig statische Modelle mit genauen Mesh-Collidern je Teil; Gameplay-Skripte nur über
  ausdrückliche Optionen (`turbine.machine`, `compressor.machine`, `warning_beacon.signal`). Rohr-/Trägeranschlüsse
  (`pipe`, neu `beam_end`) und Klang-/Effektanker ergänzt.
* Varianten statt neuer Typen: `door.variant=iris` (Irisblende, `iris_open`), `hatch.variant=maintenance`
  (Wartungsluke), `keypad.variant=access` (Zugangspanel mit Kartenleser). Stille Optionen: bestehende Seeds bleiben bitgleich.
* Korrektur: Die zehn `test_*`-Prototypen exportierten in Generation 3 eine Gesamtbox über Rohrläufe, U-Kanal und
  Schleifeninneres. Generation 3 nutzt jetzt genaue Mesh-Collider; Generation 1/2 bleiben historisch. Geometrie
  unverändert belegt (alle 270 alten Digests mit eingespielter alter Logik identisch).
* Paket, CLI, Blender-Add-on und ZIP auf 0.11.2; lokales Blender-5.2-Add-on aktualisiert. 0.11.1 wurde nie
  veröffentlicht, sein offener Bericht bleibt erhalten und ist in diesem Stand enthalten.
* Prüfung: 240 Python-Tests grün inkl. Blender-Smoke; 32 echte Wellen-FBX und je zwei Varianten-FBX ohne Ablehnung.
  Unity-Abnahme in Cube Escape. Einzelheiten: [VERSION_0.11.2.md](VERSION_0.11.2.md).

## 0.11.0 – 2026-10-08

* Paket, CLI und Blender-Add-on auf 0.11.0 umgestellt. Unveröffentlichtes 0.10.6-Vorhaben übernommen; historische Prüfbelege bleiben erhalten.
* `cocoon` Seed 1 und `stalagmite` Seed 1: begrenzte Zweiebenenlösung und flächenabhängiger Innenabstand beheben zwei numerische Grenzfälle; nicht plane Flächen umgehen keinen exakten Dreiecks-/Volumennachweis.
* Geschlossene verformte radiale Oberflächen erhalten eine begrenzte, volumengetreue konvexe Partition über unveränderte Außendreiecke. Topologie, innerer Punkt und Raumabdeckung werden geprüft; offene, invertierte oder nicht sicher partitionierbare Netze bleiben fest.
* Generation-3-Fragmente bestehen aus Compound-Parents und getrennten Shard-Collidern; konvexe Hüllen schließen keine Zwischenräume zwischen getrennten Körpern mehr. Nichtkonvexe Shards behalten genaue feste Kollision und brauchen vor dynamischer Freigabe eine Zerlegung.
* Fragment-Z-Fighting-Korrektur verschiebt ganze Körper und erhält deren Konvexität; Fragmentpivots werden vor dem FBX-Export auf das bestehende Sidecarraster quantisiert.
* Der echte FBX-Audit reproduziert und korrigiert den Kryokapsel-Pivotfehler; keine Importtoleranzen gelockert. Historische Generationen 1/2 bleiben unverändert.
* `steam_vent` erhält in Generation 3 den bisher fehlenden `FX_Steam`-Anker für beide Formen und intakte/beschädigte Varianten.
* Fragment-Draw-Calls werden auch im Palettenmodus pro Mesh gezählt. CLI-Hilfe behauptet keine einzelne Draw Call für ein ganzes mehrteiliges Modell.
* Generation-3-Fragmente gewinnen bereits geschlossene konvexe Komponenten aus zusammengesetzten Kastenprofilen zurück. U-/L-/T-/I-Profile und Gitter benötigen keine allgemeine Zerlegung; Teilflächen und Fragmentkörper bleiben erhalten. Offene Schalen und tatsächlich konkave Komponenten bleiben statisch.
* Hohlrohre, einfache Bandringe und Torusformen besitzen genaue Wandsegment-Rezepte für aktuelle Fragmente. Öffnungen bleiben frei, vorhandene Außenflächen bleiben erhalten; die Segmente teilen den bisherigen Fragmentkörper. Ungültige/verformte Rezepte werden abgelehnt; nur eine unabhängig nachgewiesene exakte Partition kann sie ersetzen, sonst behalten sie feste Kollision.
* Einfache konkave Extrusionsprofile erhalten genaue konvexe Teilstücke aus Originalpunkten; benachbarte Stücke werden nur bei konvexer Vereinigung zusammengeführt. Torbögen, Träger und Symbole behalten Aussparungen, Volumen und Materialrollen. Ungültige oder verformte Rezepte werden abgelehnt; ohne unabhängig nachgewiesene exakte Partition bleiben sie statisch. Fragmentkörper und Budgets gelten weiter.
* Profilierte volle Drehkörper und geschlossene Schüsselquerschnitte bekommen genaue Kegelstumpf-/Winkelstücke. Originalvolumen, Außenmaterialien und Vertiefungen bleiben erhalten; bereits konvexe Körper erzeugen keine zusätzlichen Shapes. Nicht plane oder ungültige Rezeptflächen benötigen eine unabhängig nachgewiesene exakte Partition, sonst bleiben sie statisch. Antenne, Kristallsockel und Transformator im festen Prüfsatz zusätzlich konvex.
* Verformte achtpunktige Kästen erhalten eine feste gemeinsame Render-/Kollisionstriangulierung und eine begrenzte konvexe Partition. Außenflächen, Volumen und Materialien bleiben erhalten; konvex triangulierte Körper bleiben ein Shape. Ungültige oder invertierte Kästen erhalten keine dynamische Freigabe.
* Breite kurze Stümpfe in `fallen_pillar` können ihre Oberkante nicht mehr unter die Grundfläche ziehen: Generation 3 begrenzt die Verformung an der tatsächlichen Höhe, bei gleicher Zufallsfolge. Historische Generationen bleiben erhalten; Regression und echte Extremvarianten ergänzt.
* Blender-Export aktualisiert den View-Layer vor der Collection-Auswahl, damit Entfernen/Neuaufbau im selben Prozess keine veralteten Objekteinträge auswählt. Echter Drei-Collection-FBX-Regressionstest ergänzt.
* Unity-ToDo-Liste gegen die integrierten Phasen 0–4 abgeglichen; Phase 5 und verbleibende Modell-/Mechanikfreigaben ausdrücklich getrennt. Auftrag für sofortige Fehlerkorrekturen gilt weiterhin.
* Sichtbare Bruch-Testanlage Z-1 in Cube Escape: zwölf konkrete Profile und 13 Phase-4-Profile mit 0.11.0 neu exportiert; tatsächliche FBX, Iso-/Ego-Buttonzyklen, Cleanup/Reset und Bestandsidentitäten geprüft. Unity-Übernahme als `464717e` per Fast-Forward erfolgt; 891/891 Tests grün, Nachweise im Versionsbericht.
* Prüfbelege und Grenzen: [VERSION_0.11.0.md](VERSION_0.11.0.md). Die geplante 0.10.6 wurde auf Nutzerwunsch in 0.11.0 übernommen. Veröffentlichung des Quellstands über `release/0.11.0`; historische Berichte bleiben erhalten.

## 0.10.5 – 2026-10-08

* Gameplay-Kollisionsprüfung verwendet den tatsächlichen Unity-Vertrag statt einer angenommenen Gesamthülle; fehlende feste Kollision ist ein Fehler.
* Generation 3 ergänzt fehlende Collider pro Teil: genaue feste Meshes erhalten Öffnungen, bewegte Ziele und Kinder bleiben konvex. Eigene Rezepte, Pickups und Generation 1/2 bleiben erhalten.
* Statische und zerstörte Generation-3-Modelle ohne eigene Shapes bekommen genaue nichtkonvexe Mesh-Collider; freie Zwischenräume bleiben frei. Alte Exporte benötigen Reexport/Reimport.
* Dampfventile bekommen Body-/Wheel-Kollision. Feste Mesh-Öffnungen werden auch im Anschlusscheck genau geprüft.
* Generation-3-Kastenkameras schauen 15–30° nach unten; negative Neigung führte zuvor zum Blick in die Luft. Historische Generationen bleiben erhalten.
* Zerstörte Generation-3-Exporte triangulieren zerbrochene Flächen explizit, damit Unity keine nichtplanaren Abschlussflächen und deren Materialrollen verwirft.
* Ursachen, Kompatibilität und Nachweise: `VERSION_0.10.5.md`. Paket, CLI und Blender-Add-on gemeinsam auf 0.10.5 aktualisiert.

## 0.10.4.1 – 2026-10-07

* Neuer seed-deterministischer Clutter-/Accessoire-Pass: `--clutter clean|lived-in|chaotic`
  bzw. `style.clutter` verteilt eigenständige Werkzeug-, Ersatzteil- und Keycard-Meshes auf
  explizit markierten Tischflächen. Props bleiben als eigene `Clutter_*`-Objekte im Export;
  ihre normalen Modelltypen sind weiterhin separat generier- und exportierbar.
* Erste freigegebene Flächen: intakte Tisch- und Labortische. Randabstände, Objektabstände
  und Flächenpassung werden beim Platzieren geprüft; fehlgeschlagene Plätze werden im
  Sidecar als `clutter_pass.skipped` protokolliert. Bestehender Tisch-Kleinkram wird bei
  aktiviertem Pass durch die separat benannten Props ersetzt.
* CLI, Rezept/Style, Blender-Add-on und Paketversion auf 0.10.4.1 aktualisiert.
  Bekannte Grenzen und Prüfstatus stehen in `VERSION_0.10.4.1.md`.

## 0.10.4 – 2026-10-07

* Schwenk-Vorrotation folgt der Richtung bei Kamera und Geschütz; negative Speed-Parameter
  sind zugelassen. Beide Richtungen decken denselben symmetrischen Winkelbereich ab.
* Explizites `speed: 0` bleibt bei Schwenken in Generation 2/3 stehen; impliziter
  30°/s-Sweep und Generation-1-Kompatibilität bleiben erhalten.
* Druckplatten der Generation 3 exportieren feste und bewegte Kollisionsflächen
  (`Body`, `Plate`) für beide Formen; ältere Generationen bleiben unverändert.
* Kamera und Geschütz der Generation 3 erhalten feste und bewegte Mesh-Collider;
  untergeordnete Geschützteile bewegen sich mit, ältere Generationen bleiben unverändert.
* Regressionen, aktualisierte Parameterliste und Cube-Escape-Nachweise: `VERSION_0.10.4.md`.


Paket, CLI und Blender-Add-on sind einheitlich 0.10.4; Add-on-ZIP neu gebaut.
Release-Prüfung: 170/170 Python-Tests grün (135 s), einschließlich Blender-Smoke.
Unity-Phase 3: 859 Tests grün, 16 zusätzliche echte FBX ohne Fehler, neun geprüfte Bilder.

## 0.10.3 – 2026-10-07

* Paket, CLI und eigenständig installierbares Blender-Add-on auf 0.10.3 vereinheitlicht.
  Das Add-on meldete im 0.10.2.5-Paket noch 0.10.2.4. Regression prüft Paketmetadaten,
  CLI-Ausgabe, Add-on-Metadaten und den tatsächlich gebauten ZIP-Inhalt; der echte
  Blender-Smoke prüft auch die installierte Add-on-Version.
* Der Berichtstest für den 0.10.2.2-Validierungsmodus prüft die aktuelle Paketversion
  statt einer festgeschriebenen späteren Patchnummer. Die übrigen Berichtskriterien bleiben erhalten.
* Cube-Escape-Integrationsphase 2 mit 0.10.2.5 dokumentiert: 36 echte FBX-Quellen ohne
  Importfehler, erhaltene IDs/Overrides, sechs explizite Item-Zuordnungen. Kein weiterer
  Generator-Codefehler im gezielten Prüfumfang; Geometrie und Gameplay-Vertrag unverändert.
  Einzelheiten und Abgrenzung der experimentellen Typen: `VERSION_0.10.3.md`.

Prüfung: **166 Python-Tests grün**, einschließlich echtem Blender-/Add-on-Export.
CLI, Paketmetadaten und neu gebautes Add-on-ZIP melden einheitlich 0.10.3.

## 0.10.2.5 – 2026-10-07

* Geometrie-Primitive für Hohlrohre, U-/L-/T-/I-Profile, Keile, Gitter und gerundete Boxen ergänzt.
* `geometry_test` stellt alle acht Formen als renderbare CLI-Demo bereit.
* Zehn experimentelle Gameplay-Prototypen aus `IDEEN.md` integriert; sie sind ausdrücklich nicht Unity-geprüft und
  enthalten keine Puzzle-Logik.

## 0.10.2.4 – 2026-10-07

* Die Desktop-GUI zeigt nach einem Build gerenderte Vorschauen und bietet eine interaktive OBJ-Ansicht mit Drehen und
  Zoomen. Bei Blender-Builds exportiert die GUI dafür zusätzlich OBJ.

## 0.10.2.3 – 2026-10-07

* Vorab- und Qualitätsberichte enthalten pro Variante einen nachvollziehbaren Score, Rang, Qualitätsmetriken und
  Hinweise auf ähnliche Varianten.
* Inkrementelle Builds erkennen unveränderte OBJ-Assets jetzt ebenfalls; `--force` baut sie weiterhin neu.
* Neue Desktop-GUI (`cubegen gui` oder `cubegen-gui`) mit Modellwahl, Rezepten, Vorabprüfung, Ähnlichkeitsfilter
  und Exportstatus.

## 0.10.2.2 – 2026-10-07

* Optionale sichere Asset-Bereinigung entfernt nur unreferenzierte leere Meshes und protokolliert die Eingriffe.
* Qualitätsberichte klassifizieren Assets als `pass`, `warning` oder `error`; `generate --strict` kann vor dem Export
  Warnungen als Fehler behandeln, während `--relaxed` sie ausdrücklich zulässt.
* Family-Checks und Build-Manifeste enthalten eine paarweise Connector-Kompatibilitätsmatrix.
* Build-Manifeste erhalten UTC-Erstellungszeit, Generator-Quellcodehash und SHA-256-Assethashes.
* `generate --validate-only` prüft Assets ohne Blender-Export; `--report FILE` speichert Validierungs- oder
  Build-Reports als JSON. `--dry-run` bleibt unverändert.

## 0.10.2 – 2026-10-07

Historischer Auftrag für Cube-Escape-Integrationsphase 0/1: belegte Cubegen-Fehler sofort
im Generator beheben, Regressionstest ergänzen und hier mit Ursache und Nachprüfung vermerken.
Seit Integrationsphase 2 mit 0.10.2.5 werden neue Befunde gemäß Nutzerauftrag in
`VERSION_0.10.3.md` dokumentiert; die veröffentlichten Korrekturen bleiben unten erhalten.
Dieser Stand enthält auch die unten dokumentierten Phase-0-Korrekturen aus dem
0.10.1-Arbeitsstand. Sie werden gemeinsam im 0.10.2-Pull-Request geprüft; der auf
Nutzerwunsch gesetzte Tag `v0.10.2` verweist auf dessen geprüften Commit.

* Palettenexport: Sidecars enthalten jetzt `textures.mode: palette` und einen relativen Pfad
  zum Standard- oder Farbpalettenmanifest. Zuvor waren nur `MP_Palette…`-Materialnamen
  enthalten; der Unity-Importer konnte die Maps damit nicht zuverlässig auflösen.
  Gemeinsamer Vertrag um den bestehenden Palettenmodus ergänzt. Nach Textur-/Atlasanbindung
  wird der tatsächlich geschriebene Sidecar erneut geprüft. Standard-/Neon-Regression ergänzt.
* Gemeinsamer Rollenvertrag: optionale `body`-Rollen von `Rotatable`, `SignalLight` und
  `SignalIndicator` sind ausdrücklich Einzelteile. Der Unity-Adapter bindet dort einen
  Transform; die bisherige unvollständige Kardinalitätsliste ließ Listen passieren.
  Generator-Regression ergänzt; Add-on-Smoke prüft jetzt auch den Palettenmanifestpfad.

Prüfung: **148 Python-Tests grün**, 167 Sekunden (38 Modell-, 12 Qualitäts-, 98 übrige
Tests), einschließlich echtem Blender-/Add-on-Export. Unity-Adapter mit gemeinsamem Vertrag:
**842 Tests grün**, volle Regression, 361 Sekunden. Echte Standard-/Rostpaletten-FBX:
**8 + 6 Quellen**, beide Import-/Reimport-Batches ohne Fehler; Maps, Renderer/Meshreferenzen,
LOD-Gruppen und Kollision geprüft. Alle **164 vorhandenen 0.10.1-FBX** bestehen ebenfalls
mit dem erweiterten Importer: 82 Gameplay / 74 statisch / 8 offene Item-Zuordnungen / 0 Fehler.
Keine Ablehnungsausnahmen. Generator- und Unity-Berichte im Worktree `f1b1` unter
`QA/Reports/Cubegen0102Phase1`. CLI, Paket und Blender-Add-on melden einheitlich 0.10.2.

## 0.10.1 – historischer Arbeitsstand, 2026-10-07 (in 0.10.2 enthalten)

Korrekturen aus dem echten Cube-Escape-Unity-Audit von Phase 0; die zusätzlichen Phase-1-Korrekturen
sind im veröffentlichten Abschnitt 0.10.2 gesammelt. Neue Befunde ab Phase 2: `VERSION_0.10.3.md`.
Keine Unity-Prüfung durch Ablehnungsausnahmen oder gelockerte Geometrie-/Collider-Prüfungen grün machen.

* `phase_platform` und `portal_frame`: `SignalLight.parts.glow` ist ein einzelner Teilname (`"Glow"`),
  keine Liste. Der bisherige Export wurde vom Unity-Importer mit „JSON-Text erwartet“ abgelehnt.
* `water_level`: Jedes Ventilrad `Wheel_<n>` hat einen eigenen konvexen Mesh-Collider. Die bisherige
  Gesamtbox reichte für mehrere getrennte interaktive `Rotatable`-Ziele nicht aus.
* `hatch`, runde Variante: Auch das Verschlussrad `Wheel` unter `Panel` hat einen eigenen konvexen
  Mesh-Collider. Die erweiterte Prüfung fand die Lücke zusätzlich bei Seed-42-Variante 2 und bei
  einer beschädigten Seed-7-Variante; Deckel-Collider bleiben erhalten.
* `sequence_panel`: Der Sidecar enthält nur die unterstützte Statusleuchte. Die unabhängigen Anzeiger
  für jede Taste bleiben vollständig als `meta.deferred_behaviours` im Manifest erhalten, zusammen
  mit Tastenfarben und Folge. Der aktuelle Unity-Importer erlaubt nur einen `SignalIndicator` je
  Prefab-Root; die spätere Knopffolge braucht ihren eigenen Adapter und ist noch nicht spielbereit.
  Die Paletten-Auflösung schützt auch diese vorbereiteten Tastenlichter vor dem Materialtausch.
* Der gemeinsame Vertrag und Python-Validator prüfen nun Einzelteil-Rollen, erlaubte Behaviour-
  Wiederholungen und explizite Collider an mehreren interaktiven Drehzielen. Regressionstests
  reproduzieren die zuvor übersehenen Ablehnungen.
* Modellnamen, Seeds, Meshes, Pivots, Materialien und Folgedaten bleiben erhalten. Sidecar-Rezepte
  und Collider sind absichtlich korrigiert, auch bei Generation 1/2; deren Geometrie bleibt erhalten.
  Golden-Referenzen ausschließlich für die fünf betroffenen Typen aktualisiert.

Prüfung: **147 Python-Tests grün** (38 Modell-, 12 Qualitäts-/Golden-, 97 übrige Tests; 159 Sekunden).
Echter Seed-42-FBX-/Unity-Batch aller 164 Typen ohne Ablehnungsausnahmen: **82 Gameplay / 74 statisch /
8 offene Item-Zuordnungen / 0 Fehler**, ein EditMode-Batchtest grün in 76,70 Sekunden Testzeit.
Zusätzlich sechs intakte/beschädigte Luke-FBX: **6 Gameplay / 0 Fehler**, ein EditMode-Batchtest grün
in 1,67 Sekunden. Vergleich gegen unverändertes `c9fde3b`: **135 Geometriefälle unverändert**.
Die erste vollständige Python-Prüfung fand den zusätzlichen Luke-Fehler; nach dessen Korrektur
wurde die vollständige Suite wiederholt. Prüfberichte im Cube-Escape-Worktree `2586` unter
`QA/Reports/Cubegen0100Phase0` und `QA/Reports/Cubegen0101Phase0`; Phase 0 wartet auf Abnahme.
Am Phase-0-Abschluss waren Versionsangaben auf 0.10.1 angehoben und beide Repositories
uncommittiert. Es gab keinen eigenen 0.10.1-Tag oder Release; die Korrekturen sind in 0.10.2 enthalten.

## 0.10.0 – 2026-10-06

Roadmap Phase 3 (Erweiterungen) ohne den Raum- und Level-Generator: Einrasten im Add-on, Paletten-Modus mit acht
Farbpaletten, symmetrisches Schwenken, vier neue Familien mit Requisiten, Zustand `fractured`, Text auf Modellen,
Anker für Ton und Effekte, 35 neue Typen (jetzt 164). Dazu die Prüfung, dass Collider die Geometrie abdecken,
Korrekturen an `archway` und `solar_panel` und schnellere Tests. Standard ist Modell-Generation 3; `--generation 1`
baut die Modelle von 0.9.0 bitgleich nach, `--generation 2` den Stand vor den Ankern.

### Einrasten im Blender-Add-on

* Neues Panel „Einrasten“: **Einrasten** setzt das Teil des aktiven Objekts an den nächsten passenden freien
  Anschluss eines anderen Teils (ausgewählte Teile, sonst alle gebauten): Stegende an Stegende, Rampe an Steg oder
  Plattform, Tür bzw. Portal in die Wandöffnung, Rohr an Rohr bzw. durch die Durchführung, Wandende an Wandende,
  Wandabschluss auf die Wand, Sockelleiste an die Wandfläche, Deckenmodul an Deckenmodul. Das Teil dreht nur um die
  Hochachse; belegte Anschlüsse werden übersprungen, wiederholtes Einrasten baut Ketten. **Anschlüsse zeigen** setzt
  Pfeile an alle Anschlusspunkte, **Reichweite** begrenzt die Suche.
* Kern in reinem Python (`cubegen/snapping.py`, getestet ohne Blender); welche Anschlussarten wie zusammengehören
  (gegenüber oder gleich ausgerichtet), steht in `families.JOINS` neben den Passungsregeln `families.RULES`.
* Neue Anschlüsse: Wände, Fensterwände und Torbögen haben `wall_top` (oben) und `face` (beide Wandflächen),
  `ramp` (`floor_walk` unten, `ramp_top` oben), `ceiling_module` (`ceiling`, vier Kanten), `wall_cap` (`cap`,
  `cap_end`), `baseboard` (`trim`, `trim_end`). Neue Passungsregeln: Wandabschluss auf der Wand (Stärke, Höhe, die
  Wand ist ein ganzes Vielfaches des Abschlusses), Sockelleiste an der Wandfläche, Rampe an Steg/Plattform, Decke an
  Decke, Abschluss an Abschluss, Leiste an Leiste.

### Paletten-Modus (`--textures palette`)

* Ein Material `MP_Palette` pro Modell, also ein Draw Call: Alle Farben des Spiels liegen als 16-px-Zellen in einer
  64 × 64-Palettentextur, jede Fläche zeigt mit ihren UVs auf die Mitte ihrer Zelle (Punktfilterung). Dazu
  Metallic/Smoothness- und Emissionsbild und `CubeEscape_Palette.json`. Reines Python (eigener PNG-Schreiber), auch mit
  `--no-blender` (OBJ/MTL).
* Glas und Teile, deren Material die Scripts umschalten (`SignalIndicator.renderers`, `Machine.glow`,
  `SignalLight.glow`, `Rotatable.glow`, `Door.statusLights`), behalten ihr Material. Statische Modelle: 1 Draw Call
  (2 mit Glas). `check --palette` zählt die Draw Calls so. Add-on: Texturen „Palette“, auch in der Vorschau.
* Der Sidecar nennt `MP_Palette` als Material der Teile; sein Schema bleibt unverändert (kein `textures`-Eintrag,
  den der Unity-Vertrag nicht kennt). Das Manifest beschreibt die Palette unter `textures`.

### Symmetrisches Schwenken für `camera` und `turret`

* Neuer Parameter `sweep` (Grad, 0 = aus): Der Kamerakopf (`Rotor`) bzw. das Geschütz (`Turret` mit `Gun` und
  `Glow`) wird um den halben Winkel vorgedreht gebaut, `Rotator.arc` = `sweep` schwenkt es dann gleichmäßig nach
  beiden Seiten (120 = ±60°); ohne `speed` mit 30 °/s. Die Kamera-LED wird dabei Kind des Kopfes und schwenkt mit.
  Ohne `sweep` bleiben beide Typen unverändert.

### Vier neue Familien mit Requisiten

* `medbay` (Krankenstation), `derelict` (verlassenes Wrack, Stil `damage` damaged, starke Abnutzung),
  `greenhouse` (Gewächshaus), `reactor` (Reaktor) - jeweils mit Bau-Kit und Requisiten im Kit (Liegen,
  Laborgeräte, Waschraum, Schilder mit Text; Wracks, Bewuchs; Pflanzen, Wasser, Solarpanel; Reaktorkern, Trafo,
  Kran, Countdown …). Passungsprüfung über drei Seeds ohne Befund.
* Die Kits von `station`, `lab` und `foundry` enthalten zusätzlich Torbogen, Wandabschluss, Sockelleiste,
  Decken-/Dachmodul und Rampe (neue Teile, bestehende unverändert).
* Neues Maß `ceiling_thickness` (Deckenstärke); `wall_height`, `wall_thickness`, `module`, `door_width`,
  `door_height`, `walk_width` gelten auch für die neuen Bau-Kit-Typen.

### Zustand `fractured`

* `--damage fractured` (Add-on: Zustand „Bruchstücke“): Das Modell sieht intakt aus, besteht aber aus 4-12
  Bruchstücken `Fragment_<nn>`. Voronoi-Zellen um einige Seed-Punkte zerschneiden jede konvexe Grundform (Boxen,
  gefaste Boxen, Zylinder), die Schnittflächen tragen das Bruchmaterial; andere Formen gehen ganz an die Zelle ihrer
  Mitte. Jedes Bruchstück hat seinen Pivot in der Mitte und einen konvexen Mesh-Collider; das Volumen bleibt
  erhalten, keine flackernden Flächen. Statisch (keine Scripts) bis Unity es zerstört.

### Text auf Modellen

* Low-Poly-Blockschrift (`cubegen/models/lettering.py`: A-Z, Ä Ö Ü, 0-9, `- + . : / _ ' ! #`).
* `sign.text` (Schild mit Text statt Symbol, so breit wie der Text), `door.label` (Raumnummer über der Tür, eigenes
  statisches Teil `Label`), `countdown.text`, `floor_plan.title`. Ohne Angabe bleiben alle Modelle unverändert.

### Anker für Ton und Effekte (Generation 3)

* Neue Modell-Generation 3 (Standard): Maschinen, Türen, Lifte, Fallen, Roboter, Geräte und viele neue Typen
  bekommen leere Teile für Unity - `Audio_Hum`, `Audio_Door`, `Audio_Servo`, `Audio_Beep`, `Audio_Alarm` … und
  `FX_Steam`, `FX_Sparks`, `FX_Smoke`, `FX_Dust`, `FX_Muzzle`, `FX_Spores` … (`cubegen/models/anchors.py`). Ein Anker
  ist Kind des Teils, auf dem er sitzt, und bewegt sich mit ihm. Zerstörte Modelle haben `FX_Smoke`, Bruchstücke keine.
* Die Geometrie bleibt exakt wie in Generation 2; `--generation 2` baut die bisherigen Modelle bitgleich nach
  (geprüft: alle Fingerabdrücke der Generationen 1 und 2 unverändert).
* **Geänderte Modelle in Generation 3** (neue leere Teile, Geometrie gleich): `breakable_platform`, `cable_mess`,
  `camera`, `coffee_machine`, `console`, `conveyor`, `crusher`, `cryo_pod`, `crystal_cluster`, `door`, `drone`,
  `fan`, `fluid_basin`, `force_field`, `gear_puzzle`, `generator`, `hanging_crystals`, `hologram`, `intercom`,
  `keypad`, `lift`, `machine`, `monitor_wall`, `mushroom`, `pad`, `phase_platform`, `pipe`, `portal_frame`, `pump`,
  `reactor_core`, `retractable_bridge`, `robot_arm`, `saw_blade`, `scanner`, `server_rack`, `service_robot`,
  `shock_plate`, `shutter`, `spider_bot`, `spike_trap`, `steam_vent`, `terminal`, `transformer`, `turntable`,
  `turret`, `vending_machine`, `vent`; alle Typen ab Zustand `destroyed` (`FX_Smoke`).
* **Behoben in Generation 3**: Beschädigte Modelle (`--damage damaged`) schlagen von Teilen, aus denen Unity
  Collider baut (`Door.colliders`, `Machine.body` …), nichts mehr ab. Bisher konnte ein Stück von `Frame_Top` auf
  dem Boden liegen; die Hülle des Rahmens reichte dann quer durch die Türöffnung. Beschädigte Varianten dieser Typen
  sehen dadurch etwas anders aus: `cargo_container`, `crusher`, `door`, `force_field`, `generator`, `lift`,
  `machine`, `pump`, `reactor_core`, `shutter`, `transformer`.

### Schnellere Tests und CI

* `tools/run_tests.py` teilt die Tests in drei etwa gleich lange Gruppen (`models`, `quality`, `rest`) und startet
  sie parallel: rund 2 statt 6½ Minuten. `--list` zeigt die Gruppen; ein Testmodul, das keine Gruppe nennt, läuft
  in `rest`, ein neues geht also nie verloren.
* Die CI startet pro Python-Version (3.9, 3.11, 3.13) eine Gruppe pro Job, 9 Jobs parallel statt 3 nacheinander
  laufender Gesamtläufe. Die Jobs heißen jetzt `test (<Python>, <Gruppe>)`.

### Farbpaletten für den Paletten-Modus

* Sieben neue Farbpaletten neben `standard` (den Farben des Spiels): `rust` (Gießerei: Brauntöne, Bernstein-Glow),
  `frost` (Kryo: Eisblau, Weiß), `toxic` (Reaktor: Grüngrau, Säuregrün), `medical` (Krankenstation: Weiß, Mint),
  `derelict` (Wrack: ausgeblichen, schwaches Licht), `greenhouse` (Moosgrün, Erde, warmes Licht), `neon` (Violett,
  Magenta, Cyan). `palette.COLOR_PALETTES`; Bild: `docs/palettes.png`.
* `generate --palette NAME` (schaltet `--textures palette` ein), in Rezepten und Familien `"palette": NAME`, im
  Add-on „Farbpalette“ (Standard: die Palette der Familie). Neuer Befehl `cubegen palettes` (`--swatches DATEI`:
  eine Zeile Farbfelder pro Palette).
* Alle Paletten teilen die Farbzellen: Die Modelle sind gleich, nur das Material heißt `MP_Palette_<Name>` mit
  eigenen Bildern und `CubeEscape_Palette_<Name>.json` (mehrere Paletten passen in einen Texturordner). Glas und von
  Scripts umgefärbte Teile behalten wie bisher ihr `M_…`-Material. `standard` bleibt `MP_Palette`.
* Familien bringen eine passende Palette mit, die nur im Paletten-Modus gilt (bisherige Exporte bleiben gleich):
  `foundry` → `rust`, `lab` → `frost`, `reactor` → `toxic`, `medbay` → `medical`, `derelict` → `derelict`,
  `greenhouse` → `greenhouse`.

### Behoben: `solar_panel` - Stützen falsch herum

* Beim Unterbau `frame` waren die Stützen genau umgekehrt bemessen: Die Fläche steigt nach hinten (+Y) an, die
  vorderen Stützen waren aber die langen - sie stachen durch die Zellen, die hinteren endeten in der Luft. Jetzt
  enden alle vier an der Unterseite der Fläche (auch bei 60° Neigung); ein Test prüft das. Die Statusleuchte hing
  beim Bodengestell frei in der Luft, jetzt sitzt sie am vorderen rechten Bein.

### Prüfung: Collider decken die Geometrie ab

* `cubegen check` meldet massive Geometrie, die kein Collider abdeckt - der Spieler liefe hinein
  (`quality.uncovered_geometry`): jedes geschlossene Teil ab 0,05 m³ und 15 cm Stärke, ein Punktraster im Teil gegen
  die Kollisionsformen, die der Unity-Import baut (`families.collision_boxes`). Ausgenommen: `Damage`, Türblätter
  ohne eigene Collider, bei Plattformen alles unter dem Boden. Ein Test prüft alle Typen in allen Zuständen.
* Gefunden und behoben (neue Typen): `archway` - die Bogenzwickel über dem Durchgang hatten keinen Collider (jetzt
  eine Treppe aus Boxen über dem Bogen, nie im Durchgang); `ramp` - flache Rampen hatten unter der Gehfläche nur die
  dünne Schrägbox (jetzt Schichten von höchstens 0,2 m); `ceiling_module` - Träger, Lüftungskasten, Abluftrohr und
  Dachschrägen bekommen Collider.
* **Behoben in Generation 3** (Generation 1 und 2 unverändert): `crusher` - Hydraulikzylinder auf dem Querträger;
  `floating_island` - Kristalle auf der Oberseite; `stairs` Stil `ramp` - Füllung unter der Schräge wie bei `ramp`;
  beschädigte Modelle (`--damage damaged`) - ein abgeschlagenes Teil, groß genug zum Hineinlaufen, bekommt einen
  Box-Collider, wenn das Modell eigene Collider hat, sonst bleibt es dran (`cargo_container`, `ceiling_module`,
  `crusher`, `escape_pod`, `reactor_core`).

### Neue Typen (jetzt 164)

* Bau-Kit: `ramp`, `ceiling_module`, `archway`, `wall_cap`, `baseboard`.
* Rätsel: `push_block`, `sequence_panel`, `water_level`, `laser_filter`, `symbol_plate`, `crane`, `countdown`.
* Requisiten: `lab_device` (Mikroskop, Reagenzglas-Ständer, Zentrifuge), `galley` (Küche, Messe, Kühlschrank),
  `washroom` (Waschbecken, WC, Dusche), `floor_plan` (Lageplan).
* Licht: `floodlight` (mit echter Lichtquelle über `SignalLight.lightPosition`/`range`/`intensity`),
  `light_strip`, `emergency_light`.
* Roboter: `patrol_drone`, `vent_crawler`, `robot_dog`, `mech`.
* Natur / Alien: `vines`, `cocoon`, `wall_roots`, `fungus_carpet`, `puddle`; Weltraum: `escape_pod`,
  `solar_panel`, `asteroid`, `planet_window`; Ruinen: `crashed_pod`, `burnt_console`, `collapsed_catwalk`.
* Alle mit Unity-Vertrag geprüft (Sidecar und echte FBX), ohne flackernde Flächen, im Dreiecks- und Draw-Call-Budget,
  in allen Zuständen. Rezept: `recipes/phase3_rooms.json`.

### Modell-Generationen

* `--generation 1|2` (Rezept/Familie `"style": {"generation": 1}`, Add-on „Generation“, Standard 2): Korrekturen,
  die bestehende Seeds verändern, gelten erst ab ihrer Generation. Generation 1 baut die Modelle von cubegen 0.9.0
  bitgleich nach (geprüft gegen die Fingerabdrücke von 0.9.0, alle Typen; nur die korrigierte Verdrahtung der
  Luftschleuse bleibt). Generation 2 enthält die Korrekturen für flackernde Flächen und Draw Calls (unten).
* Der Sidecar nennt die Generation unter `style.generation`. `--match` baut ein vorhandenes Modell in seiner
  Generation nach; Sidecars ohne diesen Eintrag stammen aus Generation 1.

### Gemeinsamer Vertrag mit dem Unity-Import

* `cubegen/contract.json` enthält die Regeln des Unity-Imports (Schlüssel, Rollen, Feldtypen, Regeln, Collider,
  Toleranzen, Dateigrenzen); `contract.py` liest sie von dort. Neu geprüft: höchstens 4 MiB, 64 Ebenen, keine
  doppelten Schlüssel.
* `python -m cubegen contract --out <Datei>` gibt dieselbe Datei an den Unity-Import weiter.

### Add-on: Typ-Menü

* Typen, die nicht zur gewählten Familie passen, stehen im Typ-Menü mit Warnsymbol und Grund; das Panel nennt
  den Grund, wenn so ein Typ gewählt ist.

### Unity-Prüfung bei jedem Export

* `cubegen/contract.py` lief bisher nur in den Tests. Jetzt prüft `generate` alle Sidecars mit den Regeln des
  Unity-Imports, bevor Blender startet: Ein Verstoß bricht den Export mit allen Fundstellen ab, offene Item-IDs
  stehen als Hinweis im Log. Nach dem Export wird jede FBX gegen ihren Sidecar geprüft (Pivots, Bounds).
* Neu: `python -m cubegen check --export <Ordner>` prüft einen fertigen Export-Ordner (Fehlercode 1 bei Fehlern).

### Keine flackernden Flächen mehr

* Liegt ein Detail (Warnstreifen, Glow-Leiste, Paneel, Rahmen) bündig auf einer anderen Fläche mit anderem
  Material oder an einem anderen Teil, hebt `generate_asset` die kleinere Fläche um 2 mm entlang ihrer Normale an
  (`quality.fix_z_fighting`). Danach: 0 flackernde Flächen in allen 129 Typen, intakt, beschädigt, zerstört, mit
  Abnutzung und in allen Detailstufen. Abnutzung verändert das Modell weiterhin nicht.
* **Geänderte Modelle** (Aussehen gleich, Vertices um 2 mm verschoben, die Dateien ändern sich): die 50 Typen, die
  0.9.0 mit flackernden Flächen gemeldet hat - `balance_scale`, `battery_bank`, `bed`, `bin`, `broken_wall`,
  `bulkhead`, `button`, `cable_plug`, `cable_tray`, `cage`, `camera`, `console`, `crate`, `crate_pile`,
  `cryo_pod`, `door`, `drone`, `extinguisher`, `fallen_pillar`, `floor_grate`, `force_field`, `gear_puzzle`,
  `hatch`, `hydroponic_bed`, `keycard`, `ladder`, `laser_mirror`, `laser_splitter`, `lift`, `locker`, `medkit`,
  `pad`, `pipe_fitting`, `plant`, `pump`, `scanner`, `service_robot`, `shutter`, `socket`, `spiral_stairs`,
  `steam_vent`, `table`, `tool_cart`, `valve`, `vending_machine`, `vent_shaft`, `wall`, `wall_panel`,
  `window_wall`, `workbench` - und einzelne beschädigte, zerstörte oder abgenutzte Varianten weiterer Typen.

### Draw Calls

* Bewegliche Teile mit drei Materialien haben jetzt zwei: Die Punkte der Schiebeplatten (`sliding_puzzle`) tragen
  die Zeilenfarbe, die Hüften von `spider_bot` das dunkle Material der Beine, Risse auf einer markierten
  Bruchplatte (`breakable_platform`) die Warnfarbe. Diese drei Typen sehen dadurch leicht anders aus.
* Das Budget berücksichtigt, dass einzeln bewegliche Teile in Unity nicht zusammengefasst werden können:
  16 pro Modell oder 2 pro Teil + 2, Abnutzung kommt hinzu; statische Modelle zählen ein Material einmal (Static
  Batching). Kein Typ überschreitet es, in keinem Zustand.

### `window_wall` und `wall_corner` folgen den Familien

* Neue Parameter `height` und `thickness` (wie bei `wall`; ohne Angabe bitgleich wie bisher), `window_wall.sill`
  bis 2 m, die Fensteroberkante folgt der Wandhöhe. `wall_height`, `wall_thickness` und `window_sill` der Familie
  gelten jetzt auch für sie, `foundry` (4 m) und `lab` (0,3 m) können sie verwenden.
* Jedes Kit hat eine Eckwand (`wall_corner`, Anschlüsse an den Wandseiten; Passungsprüfung ohne Befund).

### Add-on und Doku

* Add-on: „Von jedem Typ“ und „Alle Typen exportieren“ zählen nur Typen, die zur gewählten Familie passen.
* README: Parametertabelle aller Typen, erzeugt aus der Registry (`tools/param_table.py --write`; ein Test meldet,
  wenn sie veraltet); Blender „getestet mit 4.0 und 5.2 LTS“.

### Behoben: Luftschleuse öffnet sich in Unity nicht

* Bei `door` Stil `airlock` (oben/unten geteilt) stand das untere Blatt zuerst in `panels`. Unity bewegt das
  zweite Blatt um `-openOffset`: Das untere fuhr nach oben, das obere nach unten, beide durcheinander hindurch,
  die Öffnung blieb zu. Jetzt steht das obere Blatt (`Panel_B`) zuerst. Geometrie und Teilenamen sind
  unverändert, nur der Sidecar ändert sich. Mit 0.9.0 exportierte Luftschleusen bitte neu erzeugen.
* `cubegen/contract.py` prüft jetzt, dass zwei Türblätter auseinanderfahren (mit `secondOffset` oder dessen
  Standard).
* Dokumentiert (`docs/UNITY_INTEGRATION.md`): Klappen von `hatch`, `fuse_box`, `cage` und `safe` brauchen in
  Unity einen Zwei-Stellungs-Modus, das vorhandene `Rotatable` dreht zyklisch weiter.

### Behoben: Add-on mit Familie `foundry` oder `lab`

* Mit gewählter Familie `foundry` oder `lab` brachen Vorschau, Raster, „Von jedem Typ“ und „Kit bauen“ im Add-on
  ab (`window_wall can't follow window_sill = 1.6` bzw. `fixed wall_thickness`). Das Add-on hat die Maße der
  Familie auf alle 129 Typen angewandt statt nur auf die Typen, die gebaut werden; `window_wall` und
  `wall_corner` haben feste Maße und können diesen beiden Familien nicht folgen. Die Kommandozeile war nicht
  betroffen.
* Jetzt folgen nur die gebauten Typen den Maßen. „Von jedem Typ“ lässt Typen aus, die nicht zur Familie passen,
  und nennt sie; ein einzelner solcher Typ in der Vorschau meldet den Grund, statt einen Traceback zu zeigen.
* Neu: `families.misfits(dims, types)` liefert die Typen, die bestimmten Maßen nicht folgen können, mit Grund.

### Behoben: `archway` – Wand über dem Durchgang nach hinten versetzt

* Das Wandstück über dem Bogen saß eine halbe Wandstärke hinter den Pfosten (y 0 … t statt −t/2 … t/2): vorn
  eine Stufe, hinten stand es über, Rahmenleisten und Schlussstein hingen vorn frei vor der Wand, und der
  Collider über dem Durchgang passte nicht zur Geometrie. Jetzt ist die Wand vorn und hinten bündig, bei allen
  Bogenformen. Mit diesem Stand exportierte `Archway`-Modelle bitte neu erzeugen; Generation 1 ist nicht
  betroffen (den Typ gab es in 0.9.0 noch nicht).
* Der Schlussstein (`round`, `pointed`) hing 5,5 cm unter den Scheitel in den Durchgang, jetzt sitzt er auf dem
  Scheitel. Die Rahmenleisten lagen mittig auf der Kante und standen 6 cm in die Öffnung, jetzt liegen sie ganz
  auf der Wandfläche. Ein Test hält den Bogen bündig mit den Pfosten und den Durchgang frei.

## 0.9.0 – 2026-10-06

### Modellfamilien und Bau-Kits

* Eine Familie ist ein Rezept mit `"family"` und verbindlichen Maßen `"dims"`: Wandhöhe und -stärke,
  Modullänge, Tür-Stil und -Öffnung, Fenster, Laufstegbreite, Geländer- und Ebenenhöhe, Plattformgröße,
  Rohrradius und -achshöhe. `cubegen/families.py` bildet jedes Maß zentral auf die Parameter aller Typen ab,
  die ihm folgen. Typen mit fest eingebautem Maß werden abgelehnt, statt still nicht zu passen.
* Mitgeliefert: `station`, `foundry`, `lab` (`cubegen/family_data/`), jeweils mit Kit aus 28–29 Teilen.
* `--family NAME|DATEI` erzeugt das Kit oder mit `--types`/`--count` Varianten in der Familie. Rezepte mit
  `"family": "<Name>"` bauen darauf auf, ihre Werte sind dokumentierte Abweichungen. `--match
  <Name>.cubegen.json` erzeugt passende Ergänzungen zu einem vorhandenen Modell, das selbst mitgeprüft wird.
* Kit-Einträge dürfen eigene `params` haben (`{"type": "wall", "pick": [1], "params": {"opening": "door"}}`).
  Namen und Seeds bleiben `<Typ>_<Index>`, neue Teile ändern keine bestehenden.
* Passungsprüfung (`check --family`, Manifest `family.fit`): Breiten, Höhen, Ausrichtung, obere Ebene,
  begehbarer Boden über jeder Fuge (auch an Rampen), freier Durchgang, Tür/Portal in der Wandöffnung, Rohre
  durch Durchführungen, gemeinsamer Look. 0 von über 15 000 geprüften Fugen fehlerhaft (3 Familien, 3 Seeds,
  je 4 Varianten); absichtliche Abweichungen werden erkannt.
* Manifest: `family` (Name, Datei, Maße, Abweichungen, Passung), pro Modell `param_sources` und
  `connectors` (Unity-Koordinaten). Der Sidecar bekommt keine neuen Felder.
* `families` listet Familien und Maße. Add-on: Panel „Familie & Kit“ mit Kit bauen und Kit exportieren.

### Neue Typen (jetzt 129)

* `portal_frame`, `phase_platform`, `retractable_bridge`, `turntable`, `breakable_platform`, `spike_trap`,
  `fluid_basin`, `cargo_container`: bewegte und schaltbare Teile getrennt mit Pivot, explizite Collider,
  Öffnungen und Innenräume frei. Vorhandene Scripts nur, wo sie die Funktion abbilden (`Rotatable` für Drehscheibe
  und Containertüren, `Door` für Brücke und Stacheln, `SignalLight` für Portal- und Phasen-Glow); was in
  Unity noch fehlt, steht in `docs/UNITY_INTEGRATION.md`.

### Neue Varianten vorhandener Typen

* `wall`: `opening` `door`/`window`/`pipe` (Ausschnitt mit Rahmen, eigene Collider, Durchgang frei),
  `height`, `thickness`. `catwalk.shape`: L, T, Kreuz, Podest, Endstück; `rail_height`. `stairs.layout`:
  Zwischenpodest, Vierteldrehung, gegenläufig mit Wendepodest.
* Ohne diese Parameter sind alle Modelle bitgleich zu 0.8.0 (Fingerabdrücke). Der reale FBX-Export aller 121
  Bestandstypen × 2 Varianten wurde mit 0.8.0 verglichen: keine Änderung an FBX oder Sidecar.

### Unity-Vertrag

* `cubegen/contract.py` prüft jeden Sidecar mit den Regeln des Spiel-Imports (`Docs/CUBEGEN_IMPORT.md`) und
  gegen die FBX: Pivots auf 1 cm, Bounds, Rollen, Felder, Collider. Der Audit aus dem Spiel (Seed 42, alle
  Typen) ergibt 0 Ablehnungen und genau 8 offene Item-Zuordnungen.
* Neu: `item_id` für die 8 `ItemPickup`-Typen schreibt `fields.itemId`, nur wenn angegeben.
* Behoben: `--lods` schrieb das unbekannte Wurzelfeld `lods` und Teilenamen ohne `_LOD`-Endung (der Import hätte
  abgelehnt); jetzt stehen die Teile so im Sidecar wie in der FBX.
* Behoben: `pipe` mit Ventil konnte auf ein fehlendes `Glow` verweisen (26 von 300 Seeds); zerstörte
  `balance_scale`/`robot_arm`/`service_robot`/`turret` hatten verwaiste Kindteile (Blender-Export schlug fehl).

## 0.8.0 – 2026-10-06

### Behoben: Pivots von Teilen ab der dritten Ebene in der FBX

* Teile, deren Eltern-Teil selbst ein Eltern-Teil hat, hatten in der FBX eine falsche lokale Position und eine
  Drehung von 90° um X. Ursache ist Blenders FBX-Export mit `bake_space_transform`: Er rechnet die
  Achsen-Umrechnung ab der zweiten Ebene doppelt. Betroffen waren genau die drei Typen mit solchen Teilen:
  `balance_scale` (`Slot_A`, `Slot_B`), `robot_arm` (`Arm_Upper`, `Gripper`) und `turret` (`Glow`). Unity hat diese
  Modelle zu Recht abgelehnt. Die `.cubegen.json` war richtig, die FBX falsch.
* Der Export berechnet diese Matrizen jetzt selbst. Alle anderen Objekte behalten den Wert des Exporters, deren
  FBX ändern sich nicht.
* Neu: Nach jedem FBX-Export liest cubegen die Datei zurück (`cubegen/fbxread.py`, reines Python) und vergleicht
  Eltern, lokale Pivots, Rotation, Skalierung und Vertices mit dem Modell. Bei einer Abweichung bricht der Export
  ab, statt eine Datei zu schreiben, die nicht zur `.cubegen.json` passt.
* **Neu exportieren**: Wer `balance_scale`, `robot_arm` oder `turret` mit 0.7.0 exportiert hat, sollte sie neu
  erzeugen (gleiche Seeds, gleiche Namen).

### Gleicher Seed = gleiches Modell, garantiert

* `tests/golden.json`: Fingerabdrücke aller 121 Typen (9 Seed-/Stil-Fälle). Der Test schlägt fehl, sobald sich ein
  Modell ändert. Absichtlich geändert: `python3 tests/golden_cases.py --update`.
* Python 3.12 rechnet `sum()` von Kommazahlen genauer als 3.11. Dadurch hatten manche Flächen mit Python 3.12+
  eine andere Startecke als in Blender (3.11): gleiche Form, aber andere Dateien. Jetzt bauen Python 3.9 bis 3.13
  bitgenau die Modelle von Blender bzw. 0.7.0.
* `StableRandom`: Pythons Zufallsfunktionen außer `random()` dürfen sich zwischen Versionen ändern. cubegen nutzt
  jetzt eingefrorene Kopien, gleiche Ergebnisse wie bisher.
* `a.sub("name")`: eigener Zufallsstrom für neue Details in einem Builder, damit sie bestehende Seeds nicht
  verschieben.
* CI testet mit Python 3.9, 3.11 und 3.13.

### Neu

* `--unique` (Rezept `"unique"`, Add-on „Nur unterschiedliche“): überspringt Varianten, die wie eine frühere
  aussehen. Bei Seed 42 waren z. B. nur 7 der ersten 12 `laser_mirror` verschieden.
* `--theme TEXT` (Rezept `style.theme`, Add-on „Thema“): Raum-Thema, würfelt Glow-Farbe, Material, Abnutzung und
  Warnfarbe einmal für alle Modelle. Einzeln festgelegte Werte gehen vor.
* `--lods` (Rezept `"lods"`, Add-on): statische Modelle bekommen eine Sparstufe in derselben FBX
  (`<Teil>_LOD0` / `<Teil>_LOD1`, Unity baut die LODGroup beim Import); im Median 30 % weniger Dreiecke.
* Inkrementell: Ein erneuter Lauf in denselben Ausgabeordner baut nur geänderte Modelle neu; Blender startet gar
  nicht, wenn sich nichts geändert hat. `--force` baut alles neu.
* `--jobs N` (Add-on „Parallel“): N Blender-Prozesse gleichzeitig.
* `python -m cubegen check`: Qualitätsbericht mit Dreiecken gegen Budget, Draw Calls, flackernden Flächen
  (Z-Fighting) und Anzahl unterschiedlicher Varianten. Alle Typen liegen im Budget. 50 Typen haben flackernde
  Flächen, z. B. bündig aufliegende Warnstreifen und Leuchtringe. Sie zu beheben würde bestehende Seeds ändern; sie
  stehen in `tests/quality_baseline.json`, und der Test verhindert, dass es schlimmer wird.
* Rezepte werden geprüft: Tippfehler geben einen Fehler mit Vorschlag (`unknown key 'stlye' (did you mean
  'style'?)`) statt still ignoriert zu werden. `models` nimmt auch Varianten-Listen (`"door": [0, 7]`), Schlüssel
  mit `_` sind Kommentare.

### Kompatibilität

* Gleiche Seeds liefern dieselben Modelle wie 0.7.0. Ausnahme sind die FBX der drei oben genannten Typen, die
  jetzt korrekt sind.
* `<Name>.cubegen.json`: `style` enthält jetzt den aufgelösten Stil (mit Thema und `wear`), neu ist optional
  `lods`. `manifest.json`: neu `build_key` pro Modell.
* Mit `--lods` heißen die Objekte statischer Modelle in der FBX `<Teil>_LOD0` / `_LOD1`. Ohne `--lods` ändert
  sich nichts.
* `ItemPickup` schreibt weiterhin nur `spin`. Eine Spiel-ID (`itemId`) für die 8 Item-Typen kennt nur das
  Unity-Projekt; die Zuordnung bleibt dort.

## 0.7.0 – 2026-10-06

### Neu: Collider

* `<Name>.cubegen.json` enthält bei begehbaren und bewegten Typen `"colliders"`: Boxen (Unity-Koordinaten,
  Quaternion-Rotation) oder konvexe Mesh-Collider, optional an einem Teil, mit dem sie sich bewegen.
* Mit Collidern: `stairs` (Stufen bzw. Rampe + Geländer), `catwalk` (nur Deck, Geländer, Stützen), `platform`,
  `floating_island` (konvex), `floor_tile`, `hatch`, `floor_grate` (Schacht bleibt offen, Deckel / Rost auf
  `Panel`), `vent_shaft` (innen begehbar), `lift` (Deck fährt mit), `force_field` (`Field`).
* Ohne `colliders` bleibt alles wie bisher (Hülle). Zerstörte Varianten haben keine.
* `docs/UNITY_INTEGRATION.md`: der Import-Prompt nutzt `colliders` – auch für statische Modelle über `AssetRegistry`.

### Neu: 17 Typen (jetzt 121)

* Fallen: `crusher`, `saw_blade`, `steam_vent`, `shock_plate`
* Rätsel: `combination_lock`, `sliding_puzzle`, `balance_scale`, `freq_dial`, `switch_panel`
* Bau-Kit: `spiral_stairs`, `railing`, `cage`
* Items: `flashlight`, `key`, `cable_reel`
* Geräte: `coffee_machine`, `vending_machine`
* Rezept `recipes/traps_riddles.json`; Interaktions-Prompt um Mechaniken 19–23 erweitert.

### Kompatibilität

* Gleiche Seeds liefern dieselben Modelle wie 0.5.0; neue Typen ändern keine bestehenden Assets.

## Frühere Versionen

Siehe Git-Historie (0.5.0: 104 Typen, Parameter & Stil, Texturen, Zerstörung, Blender-Add-on).
