# Roadmap

**Arbeitsstand 0.11.3 (9. Oktober 2026, unveröffentlicht):** Zweite Stationswelle mit 28 Modellen;
Generation-3-Kollision des eingestürzten Stegs vervollständigt. Gemeinsame funktionale Kategorien
in Cube Escape einschließlich Labor/Medizin, Lager/Fracht, Werkstatt, Aufenthalt/Alltag und Notfall/Schutz.
Prüfbelege: [VERSION_0.11.3.md](../VERSION_0.11.3.md), Inhaltsstatus: [IDEEN.md](../IDEEN.md).

Stand: 10. Oktober 2026, cubegen **0.12.0** (Release-Zweig `release/0.12.0`; enthält 0.11.1–0.11.4, vorherige veröffentlichte Version 0.11.0); 186 registrierte Typen,
einschließlich elf experimenteller Ergänzungen und der elf Typen der ersten Asset-Welle ([0.11.2](../VERSION_0.11.2.md)). Unity-Integrationsphasen 0–4 sind in
Cube Escape integriert (`847d90f`); Phase 5 ist mit `464717e` und Dokumentation
`f11867e` in Unity-main übernommen. Fehlerkorrekturen aus Phase 5 sind in
[0.11.0](../VERSION_0.11.0.md) dokumentiert; das geplante 0.10.6-Vorhaben ist
übernommen. Neue Befunde gehören in den nächsten unveröffentlichten Versionsbericht.
Veröffentlichte Berichte bleiben historisch.
Die ursprünglichen Qualitätszahlen unten stammen aus dem 0.10.0-Abgleich;
neue Nachweise stehen in den Versionsberichten und im Unity-Systemdoc.
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

## 5. Nächste Vorschläge

1. **Raum- und Level-Generator** (Erweiterung 1, siehe oben).
2. **Mehr Abwechslung:** Bei 39 Typen sind von 10 Varianten nicht alle unterscheidbar (`cubegen check`, Spalte
   `distinct`), am wenigsten bei `ceiling_module` (6/10) sowie `archway`, `camera`, `laser_mirror`,
   `laser_receiver`, `laser_splitter` und `tool` (je 7/10).
3. **Draw Calls:** `sliding_puzzle` (33) und `conveyor` (21) liegen im Budget pro beweglichem Teil, sind aber
   teuer; Teile zusammenlegen oder für sie den Paletten-Modus empfehlen.
4. **Blender in der CI:** Die 7 Blender-Tests (Add-on-Rauchtest, FBX-Export) laufen auf GitHub nicht; ein eigener
   Job mit Blender würde das Add-on bei jedem Push prüfen.
