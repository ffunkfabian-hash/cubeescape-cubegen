# Roadmap

Stand: 13. Oktober 2026, cubegen **0.18.0 „Chameleon“** veröffentlicht (Tag `v0.18.0`, Release-Zweig `release/0.18.0`,
[VERSION_0.18.0.md](../VERSION_0.18.0.md): Anstriche auf allen Typen, eigenes Thema, Anbauten je Thema); davor 0.17.0
„Prism“ (Anstriche, Variantensets), 0.16.0 „Overdrive“ (macOS-App) und 0.15.0 „Stoppuhr“. 187 registrierte Typen (davon `test_wall_modules` experimentell), macOS-App unter `app/`.
Unity-Integrationsphasen 0–5 sind in Cube Escape übernommen (Phase 5: `464717e`, Doku `f11867e`); die Asset-Wellen
1–3 ([0.11.2](../VERSION_0.11.2.md) bis [0.11.4](../VERSION_0.11.4.md)) sind mit 0.12.0 veröffentlicht, Inhaltsstatus
in [IDEEN.md](../IDEEN.md). Neue Befunde gehören in den Bericht der laufenden Arbeitsversion; veröffentlichte Berichte
bleiben historisch. Die ursprünglichen Qualitätszahlen unten stammen aus dem 0.10.0-Abgleich; neue Nachweise stehen in
den Versionsberichten und im Unity-Systemdoc.
Jede Liste beginnt mit dem Wichtigsten.

## 1. Bekannte Bugs

Alle behoben (0.10.0, siehe [CHANGELOG](../CHANGELOG.md)).

- [x] **Unity-Prüfung lief nicht beim Export.** `cubegen/contract.py` wurde nur in den Tests aufgerufen.
  → `generate` prüft jeden Sidecar, bevor Blender startet, und jede FBX danach; neu: `check --export <Ordner>`.
- [x] **Flackernde Flächen (Z-Fighting) bei 50 Typen**, am stärksten `door` (1,26 m² am `Frame_Top`),
  `vent_shaft`, `window_wall`, `hydroponic_bed`, `floor_grate`.
  → Bündig aufliegende Details werden um 2 mm angehoben; 0 flackernde Flächen in allen Typen und Zuständen.
- [x] **Zu viele Draw Calls (über 16):** `sliding_puzzle` 48, `spider_bot` 23, `conveyor` 21,
  `breakable_platform` 18, `switch_panel` 17.
  → Bewegliche Teile mit 3 Materialien haben jetzt 2; Budget 16 oder 2 pro Teil + 2, statisch pro Material.
- [x] **`window_wall` und `wall_corner` passten nicht zu `foundry` und `lab`** (feste 3 m / 0,5 m, Brüstung
  höchstens 1,5 m). → Höhe und Dicke als Parameter, Brüstung bis 2 m; alle Kits haben eine Eckwand.
- [x] **Add-on:** „Von jedem Typ (129 × n)“ zählte Typen mit, die nicht zur gewählten Familie passen.
  → Zählt und exportiert nur passende Typen.
- [x] **Doku veraltet:** Blender-Version im README; Parametertabelle unvollständig (60 von 129 Typen fehlten).
  → „getestet mit 4.0 und 5.2 LTS“; die Tabelle wird aus der Registry erzeugt (`tools/param_table.py`), ein Test
  hält sie vollständig.
- [x] Add-on: Vorschau, Raster und „Kit bauen“ brachen mit Familie `foundry` oder `lab` ab.
- [x] `door` Stil `airlock`: Die beiden Blätter fuhren in Unity durcheinander hindurch, die Tür blieb zu.
- [x] `archway`: Die Wand über dem Durchgang saß eine halbe Wandstärke hinter den Pfosten; Schlussstein und
  Rahmenleisten ragten in den Durchgang, die Bogenzwickel hatten keinen Collider.
- [x] `solar_panel` (Bodengestell): Die Stützen waren falsch herum bemessen, vorne stachen sie durch die Zellen,
  hinten endeten sie in der Luft.

## 2. Verbesserungen am bestehenden System

- [x] **Unity-Prüfung beim Export** und `cubegen check --export <Ordner>` (mit Bug 1 erledigt).
- [x] **`window_wall` und `wall_corner` mit Höhe, Dicke und Brüstung als Parameter**, Eckwand in allen Kits
  (mit Bug 4 erledigt).
- [x] **Doku aktualisieren:** Blender-Version, vollständige Parametertabelle (mit Bug 6 erledigt).
- [x] **Versionsschalter:** `--generation` (Rezept/Familie `"style": {"generation": 1}`, Add-on „Generation“).
  Generation 1 baut die Modelle von cubegen 0.9.0 bitgleich nach, Generation 2 enthält die Korrekturen für
  flackernde Flächen und Draw Calls, Generation 3 (Standard, 0.10.0) dazu Anker und Collider für jedes massive Teil.
- [x] **Ein gemeinsamer Vertrag:** `cubegen/contract.json` hält die Regeln des Unity-Imports, `contract.py` liest
  sie, `python -m cubegen contract --out <Datei>` gibt sie an Unity weiter (Unity-Seite: ToDo 17).
- [x] **Collider-Prüfung:** `cubegen check` und ein Test über alle Typen und Zustände melden massive Geometrie
  außerhalb jedes Colliders (`quality.uncovered_geometry`); die Funde sind behoben.
- [x] **Schnellere Tests:** `tools/run_tests.py` startet drei gleich lange Gruppen parallel, die CI eine pro Job.
- [x] **Add-on:** Typen, die nicht zur gewählten (eigenen) Familie passen, stehen im Typ-Menü mit Warnsymbol und
  Grund; ist so ein Typ gewählt, nennt das Panel den Grund.
- [x] **Schnellere Blender-Läufe** (0.15.0, Erfahrungen aus dem Roboter-Generator): `--textures baked` backt eine
  zusammengefügte Kopie je Asset (eine Cycles-Sitzung je Durchgang statt je Teil; `sliding_puzzle` 3,7 → 1,1 s,
  `conveyor` 2,4 → 1,1 s, Modelle mit 1–3 Teilen unverändert); ImageMagick in den Blender-Workern von `--jobs` mit
  `MAGICK_THREAD_LIMIT=1`. `-t Kerne/Jobs` gemessen und verworfen: Cycles-CPU-Backen wurde langsamer (Station-Kit,
  `--jobs 3`: 50–54 s statt 47–49 s). Ausgabe: Geometrie, Normalen und Golden-Daten unverändert; die gebackene
  Umgebungsverdeckung rauscht minimal anders (Station-Kit, 105 Karten: RMSE im Mittel 0,14 %, höchstens 2,5 %).
- [ ] **Ähnliche Varianten: Signatur toleranter** (gefunden mit der Neural-Engine-Prüfung, 0.14.2): `variety.similar`
  verlangt exakt gleiche Dreieckszahlen; dadurch gelten fast gleich aussehende Varianten als verschieden (Seed 42:
  `Door_003`/`Door_010` – 12 Dreiecke und 7 % Breite Unterschied; `Console_000`/`Console_001`). Toleranz für die
  Dreieckszahl prüfen, deterministisch und vor dem Rendern wie bisher; Golden-Daten von `--unique` gezielt nachziehen.
- [ ] **Doubletten-Bericht (Neural Engine, nur macOS):** einmal über den ganzen Katalog die Vorschauen per Apple Vision
  (Feature Prints) vergleichen und fast gleiche Varianten als Liste ausgeben – ein Prüfwerkzeug, um die Signatur
  (Punkt oben) zu justieren, nie im normalen Lauf und nie als Entscheidung über ausgegebene Varianten (Werte sind
  je Gerät verschieden, Neural Engine 0,0026 gegen CPU 0,0003 für dasselbe Paar). Gemessen: 3,8 ms je Bild,
  36 Vorschauen in 0,1 s. **Zeitregel:** höchstens 1 min für den ganzen Katalog und höchstens eine Sitzung Aufwand;
  kostet es mehr Zeit, wird das Feature nicht umgesetzt.
- [ ] **Icon-Lesbarkeit prüfen (Neural Engine, nur macOS):** ein Aufmerksamkeitsmodell (Vision Saliency) meldet Icons,
  in denen das Modell nicht im Fokus steht oder angeschnitten ist – nur als Hinweis im Kontaktbogen-/Prüfbericht,
  keine Schranke, Linux-Läufe überspringen es. **Zeitregel:** höchstens 5 % mehr Laufzeit von `generate` mit Icons;
  kostet es mehr Zeit, wird das Feature nicht umgesetzt.

Weitere Punkte aus dem Abgleich mit dem Roboter-Generator, aus Cube Escape und der ImageMagick-Prüfung, umgesetzt in
0.15.0 (Messwerte in [VERSION_0.15.0.md](../VERSION_0.15.0.md)):

- [x] **Backen auf der GPU:** `--bake-device auto|cpu|gpu` (Standard `auto`: GPU ab 1024 px, sonst CPU). Gemessen mit
  zusammengefügter Kopie: 512 px CPU 14 s gegen GPU 19 s (10 Modelle), 1024 px CPU 19 s gegen GPU 10 s, 2048 px CPU 73 s
  gegen GPU 27 s (je 4 Modelle); einzeln gebacken war die GPU 3,5-mal langsamer als die CPU. Jedes Gerät liefert bei
  jedem Lauf dieselben Pixel, CPU und GPU unterscheiden sich im Rauschen; das Manifest nennt das Gerät je Modell.
  Cycles-Vorschauen (nur Rückfall ohne OpenGL) bleiben auf der CPU.
- [x] **Gebackene UVs reproduzierbar:** gemessen kein Problem – `smart_project` liefert in Cubegen bei jedem Lauf und
  mit `--jobs` dieselben Karten (bytegleich, auch auf der GPU). Ein Blender-Test hält das fest; kein UV-Cache nötig.
- [x] **PNG-Dateien bytegleich:** jeder ImageMagick-Aufruf mit `-define png:exclude-chunks=date,time`
  (`imagemagick.REPRODUCIBLE`, auch `bake._magick`); Test: zweimal erzeugen, Bytes vergleichen, keine Zeitstempel.
- [x] **Texturen, Icons, Kontaktbogen und Material-Übersicht cachen:** `cubegen/cache.py`, Schlüssel aus den Eingaben,
  Abgleich der Datei-Hashes; `--force` baut neu. Unveränderter Zweitlauf des Station-Kits (35 Modelle, gebacken):
  8,1 s → 1,4 s; ohne Blender 4,8 s Texturen → 0 s.
- [x] **`--jobs` mit Arbeitspaketen:** Anspruchsdatei je Modell, größtes zuerst (Dreiecke + 100 je Teil), Ergebnisse in
  Spec-Reihenfolge; kein `nice` (kein Prozess hat den kritischen Pfad).
- [x] **Zeitbudget je Stufe und Teststufen:** `manifest.json` › `timings` (Wanduhr je Stufe, Summen aus Blender, Budget,
  zu langsame Stufen) und Warnung im Log; `tools/run_tests.py --tier quick|standard|full` (quick rund 30 s ohne Blender
  und ohne die Durchläufe über alle Typen), vierte Gruppe `params` auch in der CI.

Geprüft und entfallen (0.15.0): Paletten aus Gewichtskarten zusammensetzen – der Paletten-Modus backt nicht (reines
Python, `palette.py`), `--textures baked` backt je Lauf genau eine Palette. EEVEE-Wartezeit durch `BLENDED`-Materialien –
kein Cubegen-Material setzt eine transparente Render-Methode. `foreach_get` als `float32` – nicht verwendet.
Werden Texturvarianten je Palette oder transparente Materialien eingeführt, gelten diese Regeln (AGENTS.md).

Restliche Erfahrungen des Roboter-Generators, umgesetzt in 0.16.0 (Messwerte in
[VERSION_0.16.0.md](../VERSION_0.16.0.md)):

- [x] **`--jobs auto` als Standard:** bis Kerne − 1, nur so viele Prozesse, wie sich lohnen; CPU-Backen höchstens 2,
  GPU-Arbeit höchstens 3.
- [x] **ImageMagick parallel:** Texturen je Material, Icons je Modell, Kontaktbogen in Blöcken (186 Modelle: Bildnachlauf
  16,4 → 4,1 s, Kontaktbogen pixelgleich).
- [x] **Stufen überlappen:** Blender startet, während die Kacheltexturen entstehen.
- [x] **Ein Back-Durchgang weniger:** Rauheit und Metall in einem Durchgang, Karten bytegleich.
- [x] **Messung:** Systemlast, Statistik je Blender-Prozess, `tools/profile_run.py`.
- [x] **`-t 1` ohne Backen:** gemessen, kein Gewinn, nicht übernommen.
- [x] **Qualitätsprüfung schneller:** Hüllquader-Vorfilter und einmal vorbereitete Strahlflächen, 35 % weniger CPU,
  Ergebnis bytegleich; numpy bewusst nicht (Golden-Daten).
- [x] **macOS-App** `app/` (0.16.0): erzeugt Modelle wie das Desktop-Fenster, nach dem Vorbild des Robot Viewers;
  Symbole per ImageMagick, Katalog als einzige Quelle, 17 Prüfungen in `app/test_app.sh`.
- [x] **Stiltest Anstriche** (0.17.0, experimentell): einmal neutral backen, Anstriche als Daten
  zusammensetzen – Ergebnis und offene Richtungsfragen in [VERSION_0.17.0.md](../VERSION_0.17.0.md).
- [x] **Variantensets** (0.17.0): `--set` – alle Varianten eines Typs behalten die Außenmaße der ersten
  (`OUTLINE_PARAMS`, `Param(size=True)`) und unterscheiden sich innen; Manifest `sets` mit `outline_ok`/`deviation_m`
  und Reihenbild `set_<Typ>.png`; Option auch in App und Desktop-Fenster. Regeln für set-fähige Typen: AGENTS.md ›
  „Variantensets“. Prototyp `test_wall_modules` (Modulwand nach dem Konzept, Kristalle `none|some|many`).
- [ ] **Weitere Typen set-fähig machen:** gemessen mit `--set` (Seed 42, 5 Varianten): `wall`, `pillar`,
  `test_wall_modules` halten ihren Umriss; `crate` nicht (Tiefe intern gewürfelt, 3,5 cm), `floor_tile` nicht
  (Oberkante variiert, 4,6 cm). Zuerst die Bau-Kit-Teile (Wand, Boden, Decke, Steg, Geländer), dann Requisiten;
  je Typ Innen-Variation nach dem Muster der Modulwand (Aufteilung, Akzente, Anbauteile, Schilder, seltene Hingucker).
- [x] **Anstriche als Ausgabemodus** (0.17.0, Entscheidung des Nutzers): `--paint <Thema>` (CLI, App, Desktop-Fenster)
  backt jedes Modell einmal neutral und setzt das Thema zu einem gebackenen Atlas zusammen – Unity liest ihn heute
  über den Import für `--textures baked` (Material `MTA_<Modell>`). Elf Themen nach den Wandkonzepten der drei
  Konzeptbögen: Industrial, Clean, Ruin, Crystal, Dark, Organic, Sand, Space, Ice, Toxic, Void – zunächst für Wände gedacht. Neutrale Karten liegen für den Shader
  (ToDo 27) unter `Textures/Neutral` bereit.
- [x] **Eigenes Thema („Custom“, Konzeptbogen III)** (0.18.0): `--paint-file <Datei.json>` (auch Rezept, App, Desktop-
  Fenster) – Name, Grundthema, nur abweichende Werte; der Blender-Worker bekommt die Daten im Auftrag. Beispiel
  `paints/custom_example.json`.
- [ ] **Farbwähler für das eigene Thema in der App:** Farben je Spielmaterial und Mengen (Abnutzung, Schmutz, Staub,
  Moos, Kantenleuchten) mit Vorschau eines Anstrichs auf einem neutral gebackenen Modell; speichert die JSON-Datei für
  `--paint-file`. Gegenstück in der Werkbank: Unity-ToDo 29.
- [x] **Anstriche auf weitere Typen** (0.18.0): geprüft an Boden, Plattform, Säule, Steg, Treppe, Kiste, Tür,
  Geländer, Decke in allen elf Themen ([docs/paint_types_0180.png](paint_types_0180.png)); `M_Ground` ist je Thema ein
  neutraler Grundton, Staub/Moos/Schnee fleckig.
- [x] **Fehlende Geometrie je Thema, Modulwand** (0.18.0): `test_wall_modules.dressing` – `ruin` (Rohrstrang mit
  Muffen und Knie, abgerissene Platte, Trümmer), `organic` (Ranken mit Blättern vom Deckel, Steinblöcke, Büsche);
  Umriss bleibt (45 Varianten geprüft). Kristalle gibt es schon (`crystals`).
- [ ] **Anbauten auf weitere Typen:** dasselbe Muster für Boden (Trümmer, Moosflecken als Geometrie), Säule (Ranken),
  Steg (herabhängende Kabel/Ranken); als Parameter `dressing`, nie gewürfelt (Set-Umriss).
- [ ] **Kristallmaterial (Generator-Seite):** `M_Crystal` facettiert und mit eigener Leuchtfarbe je Thema im Manifest;
  das durchscheinende Material selbst entsteht in Unity (ToDo 28).
- [ ] **App weiter:** Notarisierung für die Weitergabe (bisher ad-hoc signiert), Parameter je Typ (`--param`) und
  Familienmaße in der App, Kontaktbogen und Qualitätsbericht als eigene Ansicht.

## 3. Erweiterungen

Punkte 2–8 und alle vorgeschlagenen Modelltypen erledigt (0.10.0, siehe [CHANGELOG](../CHANGELOG.md)).

**Funktionen**

1. **Raum- und Level-Generator:** setzt aus den Anschlusspunkten der Familien (`connectors` im Manifest) einen
   ganzen Raum nach Seed zusammen; Ausgabe als Layout-JSON für Unity. *(offen; die Bausteine dafür gibt es jetzt:
   `cubegen/snapping.py` setzt zwei Teile an kompatiblen Anschlüssen aneinander, `families.JOINS` sagt, welche
   Anschlüsse zusammengehören.)*
2. [x] **Einrasten im Blender-Add-on:** Panel „Einrasten“ setzt ein Teil an den nächsten passenden freien Anschluss
   (Steg, Rampe, Tür in Wandöffnung, Rohr, Wandende, Wandabschluss, Sockelleiste, Decke); „Anschlüsse zeigen“ setzt
   Pfeile. Kern: `cubegen/snapping.py`.
3. [x] **Paletten-Modus:** `--textures palette`, ein Material `MP_Palette` mit Farbpaletten-Textur pro Modell, also
   ein Draw Call (Glas und von Scripts umgefärbte Teile behalten ihr Material); `check --palette`. Dazu sieben
   Farbpaletten (`--palette rust|frost|toxic|medical|derelict|greenhouse|neon`, Material `MP_Palette_<Name>`).
4. [x] **Symmetrisches Schwenken** für `camera` und `turret`: Parameter `sweep`, Rotor um den halben Winkel
   vorgedreht gebaut, `Rotator.arc` = `sweep` (120 = ±60°).
5. [x] **Weitere Familien:** `medbay`, `derelict`, `greenhouse`, `reactor`, jeweils mit Requisiten im Kit; alle
   Kits zusätzlich mit Torbogen, Wandabschluss, Sockelleiste, Decken-/Dachmodul und Rampe.
6. [x] **Zustand `fractured`:** Modell in Bruchstücke `Fragment_<nn>` zerlegt (Voronoi-Schnitte, konvexe
   Mesh-Collider), die Unity bei Zerstörung herausfallen lässt.
7. [x] **Text auf Modellen:** Blockschrift; `sign.text=B-12`, `door.label`, `countdown.text`, `floor_plan.title`.
8. [x] **Anker für Ton und Effekte:** leere Teile wie `Audio_Hum`, `FX_Steam` (Generation 3, Standard).

**Neue Modelltypen** (alle erledigt, jetzt 164 Typen)

| Bereich | Typen |
|---|---|
| Bau-Kit | [x] Rampe `ramp`, [x] Decken- und Dachmodul `ceiling_module`, [x] Durchgang / Torbogen `archway`, [x] Wandabschluss `wall_cap`, [x] Sockelleiste `baseboard` |
| Rätsel | [x] Gewichtsblock `push_block`, [x] Ton- und Farbfolge-Panel `sequence_panel`, [x] Wasserstand-Rätsel `water_level`, [x] Farbfilter für Laser `laser_filter`, [x] Symbolplatten `symbol_plate`, [x] Kran / Magnet `crane`, [x] Countdown-Anzeige `countdown` |
| Requisiten | [x] Labor `lab_device` (Mikroskop, Reagenzglas-Ständer, Zentrifuge), [x] Küche / Messe `galley`, [x] Waschraum `washroom`, [x] Lageplan `floor_plan` |
| Licht | [x] Flutlicht `floodlight`, [x] Neon- und LED-Leisten `light_strip`, [x] Notbeleuchtung `emergency_light` |
| Roboter | [x] Patrouillen-Drohne `patrol_drone`, [x] Kriecher für Lüftungsschächte `vent_crawler`, [x] Roboterhund `robot_dog`, [x] Industrie-Mech `mech` |
| Natur / Alien | [x] Ranken `vines`, [x] Kokons `cocoon`, [x] Wurzeln durch Wände `wall_roots`, [x] Pilzteppiche `fungus_carpet`, [x] Pfützen `puddle` |
| Außen / Weltraum | [x] Rettungskapsel `escape_pod`, [x] Solarpanel `solar_panel`, [x] Asteroid `asteroid`, [x] Fenster mit Planet `planet_window` |
| Ruinen | [x] abgestürzte Kapsel `crashed_pod`, [x] ausgebrannte Konsole `burnt_console`, [x] eingestürzter Steg `collapsed_catwalk` |

## 4. ToDo für Unity

Abgleich mit dem produktiven Unity-Code und `Docs/CUBEGEN_IMPORT.md` vom 8. Oktober 2026.
`[x]` gilt für den ausdrücklich beschriebenen geprüften Umfang; teilweise erledigte
Punkte bleiben offen. Die Nummern 1–22 bleiben als Referenz der Integrationsübergabe erhalten.
Details zu den Mechaniken: [`UNITY_INTEGRATION.md`](UNITY_INTEGRATION.md).

**Export und Bestand (Phasen 0–2)**

- [x] **1 · Audit ohne Ablehnungsausnahmen:** Der echte FBX-Audit erwartet bereits null
  unerwartete Ablehnungen. Phase 4 hat je 175 intakte und zerstörte Quellen ohne Fehler
  geprüft. Die drei Ausnahmen aus 0.7 sind historisch; sie werden nicht mehr gesetzt.
- [x] **2 · Verwendete Bestandsquellen neu exportieren/reimportieren:** Phase 2 hat sieben
  Bestandsmodelle mit Generation 3 aktualisiert und GUIDs, Gameplay-/Modell-fileIDs,
  Katalog-IDs und gespeicherte Overrides geprüft. Neue Phasenprofile erhalten eigene
  Exporte und Physiknachweise. Dies ist kein pauschaler Reexport jeder alten Library-Datei.
  Generation 1 bleibt historisch und ist kein Weg, aktuelle Korrekturen zu übernehmen.
- [x] **3 · Item-Zuordnung klären:** Reale vorhandene `ItemData`-IDs werden per Rezept
  wiederverwendet; sechs Pickup-Prüfvarianten sind geprüft. Die acht offenen IDs waren
  ein alter Batch-Befund, keine acht fehlenden Datensätze. Neue Story-Items und weitere
  Content-Varianten bleiben eigene Aufträge, ohne pauschale Ersatz-ID.

**Interaktionen (Phase 3)**

- [ ] **4 · Zwei-Stellungs-Klappen:** Generischer Vertrag, eckige/runde Luke und
  Mehrfach-Slot-Deckel sind erledigt. Weitere `fuse_box`-/`cage`-/`safe`-/Kapsel-/
  Containerprofile brauchen noch ihre eigene Freigabe; zyklisches Durchdrehen vermeiden.
- [x] **5 · Lift:** Geprüftes Liftprofil verwendet `MovingPlatform` im Modus `Follow`
  mit bewegtem Deck und festem Rahmen, einem Bewegungscontroller.
- [x] **6 · Mitfahren:** Roboter auf Ausfahrbrücke, Lift und Drehscheibe in Iso/Ego,
  beide Richtungen und Abspringen geprüft. Allgemeines Mitfahren kinematischer Kisten
  ist weiterhin offen und nicht Teil dieser Freigabe.
- [ ] **7 · Sockel:** Einzel-/Mehrfachslots, `ItemSlot`/`ItemSlotSignal`, UND-Ausgang,
  Deckelzugang und Teil-IDs sind für die geprüften Sockelmodelle umgesetzt. Weitere
  Modellprofile und eine Spielerlevel-Freigabe für Inventar-Sockel bleiben offen.
- [x] **8 · Druckplatte:** Eckige/runde Varianten an `PressurePlate` angeschlossen;
  Gewicht, Roboter, Mehrfach-Collider, Teleport, Haltezeit und Einsinken geprüft.

**Gefahren, Plattformen und spätere Rätsel**

- [x] **9 · Schadenszonen:** Stacheln, Presse, Säge, zwei Dampfventile und Stromplatte
  verwenden vorhandene Hazard-Zustände und geprüfte aktive Schadensvolumen.
- [x] **10 · Vorbereitete Modelle:** 13 ausdrücklich authorierte Phase-4-Profile für
  Gefahren, Phasen-/Bruchplattform, Wasser/Schlamm und feste Wand-/Bodenportale sind
  spielbereit. Weitere Typ-/Parameterformen benötigen weiterhin eigene Abnahmen.
- [ ] **11 · Raumlaser und Rohr-Puzzle:** Separate spätere Aufträge; Raumstrahlen und
  Terminal-Laser bleiben verschiedene Systeme.
- [ ] **12 · Weitere Interaktionen:** Knopffolgen, Steckfeld, Scanner, Schlösser,
  Waage, Frequenz, Leiter/Pads, Förderband, Geschütz und Idle-Animationen einzeln planen.

**Freigabe und Importfundament (Phase 1 und je Mechanik)**

- [x] **13 · Werkbank-Freigabe:** `AssetMetadata` ist die ausdrückliche Freigabe für
  geprüfte Profile; Eigenschaften/Defaults, Ports, Interaktivität und Lichtlimits sind
  geprüft. Ein Sidecar schaltet kein unbekanntes Gameplay frei. Neue Mechaniken folgen
  diesem Vertrag; Inventar-Sockel bleiben bewusst außerhalb der Spielerlevel-Whitelist.
- [x] **14 · LOD-Kollision:** Kollisionsquellen ausschließlich aus LOD0;
  automatische LODGroup, Wechsel und freier Raum sind geprüft.
- [x] **15 · Static Batching:** Nur fest authorierte Dekoration mit `static-batching`-
  Tag darf markiert werden. Im aktiven GPU-Resident-Drawer-Profil keine automatische
  Markierung; bewegte, brechende und flüssige Varianten bleiben dynamisch. Messung im
  Rückfallrenderer: 130 → 80 normale Draw Calls. Keine angenommene Kostenfreiheit für
  alle statischen Modelle und keine automatische Kombination von Werkbankinstanzen.
- [ ] **16 · Anschlüsse/Layout-JSON:** Manifestadapter und Raumgenerator bleiben offen.
- [x] **17 · Gemeinsamer Vertrag:** Unity lädt und validiert den exportierten
  `cubegen_contract.json`; C#-Adapter bleiben die feste Komponentenfreigabe.
- [x] **18 · Palette:** Standard-/Rostpaletten und je Manifest-GUID getrennte
  URP-Materialien mit richtigen Textur-/Filtereinstellungen sind umgesetzt und geprüft.

**Effekte/Zerstörung (Phase 5) und Erweiterungen**

- [x] **19 · Bruchstücke:** Für zwölf ausdrücklich authorierte Generation-3-Profile
  umgesetzt und geprüft: Compound-Fragmente, vorhandener Bruch-/Reset-Lebenszyklus,
  Aufräumen sowie Objekt- und globale Physikbudgets. Der Hüllenfehler, die Pivot-
  Rundung und die Z-Fighting-Folge gehören jetzt zum 0.11.0-Stand. Weitere
  Modellprofile bleiben eigene Freigaben; nichtkonvexe Shards bleiben statisch.
  Erste gezielte Nacharbeit gewinnt vorhandene konvexe Körper aus Kastenprofilen
  zurück: sieben Typen profitieren ohne weitere Rigidbodies; im Seed-42-Prüfsatz
  bleiben 32 statt 34 Quellen mit nichtkonvexen Shapes. Details im 0.11.0-Bericht.
  Der anschließende Rohr-/Ring-Schritt reduziert den geprüften Stand weiter auf
  20 Quellen; zwölf weitere Typen sind vollständig konvex. Physikbudgets gelten
  weiter, zusätzliche Shapes sind keine kostenlose Rendering-/Physikerweiterung.
  Die dritte Nacharbeit für konkave Extrusionsprofile ergänzt fünf vollständige
  Quellen (Torbogen, Träger, Symbolplatten, Pilzteppich, Pfütze): im selben Prüfsatz
  bleiben 15 Quellen. 210 Generator-Tests und acht echte FBX-Importe grün;
  Aussparungen, Bewegung, Pause und insgesamt 30 serialisierte Resets an drei
  isolierten Profilen geprüft. Details und Abschlussregression in `VERSION_0.11.0.md`.
  Alle 15 verbleibenden Quellen nach Ursache untersucht; gezielte Drehprofil-
  Nacharbeit macht Antenne, Kristallsockel und Transformator zusätzlich konvex.
  Im selben Prüfsatz bleiben zwölf Quellen mit verformten Flächen offen.
  215 Generator-Tests, sechs echte FBX-Importe und Physik-/Resetnachweise grün.
  Körperzahl unverändert; zusätzliche Shapes bleiben innerhalb der geprüften Budgets.
  Die anschließende Kasten-Nacharbeit ergänzt `broken_wall`, `burnt_console` und
  `fallen_pillar`: im selben Prüfsatz verbleiben neun radiale Quellen.
  Nicht plane Vierecke bekommen eindeutige gemeinsame Render-/Collider-Dreiecke.
  Körperzahl steigt im Prüfsatz nicht; 222 Generator-Tests und acht echte FBX-
  Importe grün. Invertierte breite Säulenstümpfe sofort für Generation 3 korrigiert.
  Abschließend ergänzt die radiale Partition alle neun verbleibenden Quellen:
  **9 → 0**, insgesamt **34 → 0** im festen 175-Typen-Prüfsatz, 166 Digests gegenüber
  dem Kasten-Schritt unverändert. 36 aktuelle Seed-Fälle konvex; 227 Generator-Tests,
  14 echte FBX und Physik-/Reset-/Bildnachweise grün. Kein pauschales Versprechen für
  beliebige Parameter; offene/ungeeignete Netze bleiben statisch. Lokales Blender-
  Add-on und CLI jetzt 0.11.0, alte Exporte benötigen Neugenerierung. Weitere
  Gameplayprofile bleiben eigene Freigaben. Abschlussbelege und Grenzen im
  [0.11.0-Bericht](../VERSION_0.11.0.md).
  Sichtbare Bruch-Testanlage Z-1 mit zwölf konkreten Profilen ergänzt: je Station
  BRUCH/RESET, Fall über Fangboden, bestehende E/F-Bedienung und V-Ansichtswechsel.
  Alle zwölf Stationen in Iso/Ego zweimal einschließlich Reset nach Cleanup
  gespielt; 25 tatsächliche FBX der Bruch-/Phase-4-Profile mit 0.11.0 neu exportiert,
  geprüft und reimportiert. Übernahme des geprüften Unity-Standes in main ist
  erfolgt: `464717e` per Fast-Forward, 891/891 Unity-Tests grün (406 s).
  Abschlussstatus und Grenzen im Versionsbericht.
- [x] **20 · Audio-/FX-Anker:** Zustandsabhängige Adapter mit vorhandenen Loop-Clips
  und FX, echte Dampfanker, Servo-/Maschinen-/Portalanker und Wiederimport ohne doppelte
  Quellen sind für den geprüften Umfang umgesetzt. Weitere Mechaniken erhalten erst bei
  ihrer eigenen Freigabe eine funktionale Zuordnung.
- [x] **21 · Schwenken:** Kamera und Geschütz mit beiden Vorzeichen und Stillstand
  gegen echte FBX-Geometrie geprüft. Generation-3-Kastenkameras seit 0.10.5 nach unten
  geneigt; historische Generationen bleiben getrennt. Kein Schuss-/Schadensvertrag.
- [ ] **22 · Erweiterungsmodelle:** Schiebeblock, Knopffolge, Wasserstand,
  Laserfilter, Symbolplatten, Kran, Countdown, Patrouillen/Gangarten bleiben eigene
  Aufgaben. Datenabhängige Rätsel benötigen vorher validierten Manifestzugriff:
  `meta.sequence`, `meta.seconds_total` usw. stehen nicht im Sidecar.

- [x] **23 · Erste Asset-Welle (0.11.2):** elf neue Typen und drei Varianten aus IDEEN.md, 32 statische
  Modelle in Cube Escape über die Registry freigegeben und nach Funktion einsortiert (Modell-Browser).
- [ ] **24 · Gameplay der ersten Welle:** Schleusenzyklus (`airlock_chamber`), Irismechanik (`door.variant=iris`),
  Maschinenvertrag für `turbine`/`compressor`, Signalsäule als Lampe, Wartungsluke (Hinge) und Zugangspanel
  (Keypad) brauchen je einen eigenen Gameplay-Vertrag in Cube Escape.
- [ ] **25 · Variantensets im Modell-Browser** (Wunsch des Nutzers, 0.17.0): Das Manifest nennt Sets (`sets`: Name, Typ,
  Mitglieder, festgehaltene Maße, `outline_ok`). Im Modell-Browser der Werkbank als eine Gruppe zeigen (Reihenbild
  statt einzelner Kacheln), beim Platzieren die Mitglieder abwechseln oder zufällig wählen, damit nebeneinander
  gestellte Teile sich nicht wiederholen; `outline_ok = false` sichtbar machen (Teile schließen nicht sauber an).
  Mit den vorhandenen Modellsets der Werkbank abstimmen (gleiche Datenhaltung, keine zweite Sammlung).
- [ ] **26 · Leuchtkarte für gebackene Anstriche** (0.17.0): `--paint` schreibt eine `Emission`-Karte (Crystal: blaue,
  Dark: rote Leuchtkanten), der Unity-Vertrag kennt sie bei `baked` noch nicht – sie steht nur im Manifest
  (`models[].baked.Emission`). Import: `Emission` als erlaubte baked-Map, `_EmissionMap` setzen; Vertrag
  (`contract.json`) und `CubegenMaterials.cs` gemeinsam ändern.
- [ ] **27 · Shader mit Umfärbung (Cube-Escape-Variante, später)** – Empfehlung aus 0.17.0, vom Nutzer so beschlossen:
  erst fertige Karten (umgesetzt), dann ein URP-Shader, der dieselben neutralen Karten zur Laufzeit umfärbt.
  Warum: Speicher wächst nicht mit der Zahl der Themen (1024 px: fertige Karten ≈ 5 MB je Modell **und** Thema –
  20 Wandteile × 6 Themen ≈ 640 MB; neutral ≈ 6 MB je Modell für alle Themen ≈ 120 MB), Themenwechsel zur Laufzeit
  (Level-Thema, Story-Verfall, Spielerwahl in der Werkbank), passt zum geplanten Masken-Shader der Roboter-Skins.
  Vorbereitet: `Textures/Neutral/<Modell>_W<n>.png` (Gewichte, drei Spielmaterialien je RGB, Reihenfolge im Manifest
  `models[].weight_layout`), `_AO`, `_Edge`, `_Up`, `_Height`, `_Diffuse` (Detail der Kacheln), `_Normal`; die Formel
  in `cubegen/paint.py` (`compose`, `detail_map`) ist die Referenz – Shader und Generator müssen gleich aussehen
  (Vergleichsbild). Offen: Rauschen im Shader (Textur oder prozedural), Packen der Masken (AO/Kante/oben/Höhe in
  einem RGBA), Rückfall für niedrige Grafikstufen (fertige Karten), Laufzeitpfad GLB. Eigene Themen (0.18.0) stehen
  als vollständige Daten im Manifest (`config.paint_scheme`) – der Shader braucht dieselben Schlüssel als Parameter.
- [ ] **28 · Echtes Kristallmaterial** (0.18.0, Konzept „04 Crystal“): `M_Crystal` ist heute eine flache Leuchtfarbe.
  In Unity ein URP-Material für Kristall-Teile (durchscheinend/Fresnel, facettierte Normalen, innerer Schimmer, Farbe
  aus dem Thema bzw. `--glow`), zugeordnet über den Materialnamen wie Glas; Kollision unverändert. Mit ToDo 26
  (Leuchtkarte) abstimmen, damit Kristall und Leuchtkanten dieselbe Farbe tragen.
- [ ] **29 · Anstriche in der Werkbank** (0.18.0): Die Laufzeit-Generation (`CubegenJobRunner`) bietet heute keinen
  Anstrich. Auswahl „Anstrich“ aus `cubegen catalog --json` (`paints`), eigenes Thema mit Farbwählern (Farben je
  Spielmaterial, Mengen 0–1, Leuchtfarbe cyan/rot/orange) als JSON in den Benutzerdaten, Übergabe per
  `--paint`/`--paint-file`. Vorher prüfen, ob der GLB-Laufzeitpfad gebackene Karten (`MTA_`) lesen kann; sonst zuerst
  dort ergänzen. Einstellungen nur über die Werkbank-Regeln (Hilfethema pflegen).
- [ ] **30 · Anbauten je Thema im Modell-Browser** (0.18.0): `test_wall_modules` mit `dressing=ruin|organic` und
  `crystals` als Varianten eines Sets anzeigen (ToDo 25); experimenteller Typ – erst nach Freigabe als Standardset.

## 5. Nächste Vorschläge

1. **Raum- und Level-Generator** (Erweiterung 1, siehe oben).
2. **Mehr Abwechslung:** Bei 39 Typen sind von 10 Varianten nicht alle unterscheidbar (`cubegen check`, Spalte
   `distinct`), am wenigsten bei `ceiling_module` (6/10) sowie `archway`, `camera`, `laser_mirror`,
   `laser_receiver`, `laser_splitter` und `tool` (je 7/10).
3. **Draw Calls:** `sliding_puzzle` (33) und `conveyor` (21) liegen im Budget pro beweglichem Teil, sind aber
   teuer; Teile zusammenlegen oder für sie den Paletten-Modus empfehlen.
4. **Blender in der CI:** Die 7 Blender-Tests (Add-on-Rauchtest, FBX-Export) laufen auf GitHub nicht; ein eigener
   Job mit Blender würde das Add-on bei jedem Push prüfen.
