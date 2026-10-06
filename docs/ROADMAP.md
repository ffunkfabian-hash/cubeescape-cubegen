# Roadmap

Stand: 6. Oktober 2026, cubegen 0.9.0 plus Korrekturen und Erweiterungen (Phase 3 ohne Raum-Generator) unter
„Unveröffentlicht“ im [CHANGELOG](../CHANGELOG.md).
Zahlen aus `python -m cubegen check` (Seed 42, 10 Varianten pro Typ). Jede Liste beginnt mit dem Wichtigsten.

## 1. Bekannte Bugs

Alle behoben (Unveröffentlicht, siehe [CHANGELOG](../CHANGELOG.md)).

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

## 2. Verbesserungen am bestehenden System

- [x] **Unity-Prüfung beim Export** und `cubegen check --export <Ordner>` (mit Bug 1 erledigt).
- [x] **`window_wall` und `wall_corner` mit Höhe, Dicke und Brüstung als Parameter**, Eckwand in allen Kits
  (mit Bug 4 erledigt).
- [x] **Doku aktualisieren:** Blender-Version, vollständige Parametertabelle (mit Bug 6 erledigt).
- [x] **Versionsschalter:** `--generation` (Rezept/Familie `"style": {"generation": 1}`, Add-on „Generation“).
  Generation 1 baut die Modelle von cubegen 0.9.0 bitgleich nach, Generation 2 (Standard) enthält die
  Korrekturen für flackernde Flächen und Draw Calls.
- [x] **Ein gemeinsamer Vertrag:** `cubegen/contract.json` hält die Regeln des Unity-Imports, `contract.py` liest
  sie, `python -m cubegen contract --out <Datei>` gibt sie an Unity weiter (Unity-Seite: ToDo 17).
- [x] **Add-on:** Typen, die nicht zur gewählten (eigenen) Familie passen, stehen im Typ-Menü mit Warnsymbol und
  Grund; ist so ein Typ gewählt, nennt das Panel den Grund.

## 3. Erweiterungen

Punkte 2–8 und alle vorgeschlagenen Modelltypen erledigt (Unveröffentlicht, siehe [CHANGELOG](../CHANGELOG.md)).

**Funktionen**

1. **Raum- und Level-Generator:** setzt aus den Anschlusspunkten der Familien (`connectors` im Manifest) einen
   ganzen Raum nach Seed zusammen; Ausgabe als Layout-JSON für Unity. *(offen; die Bausteine dafür gibt es jetzt:
   `cubegen/snapping.py` setzt zwei Teile an kompatiblen Anschlüssen aneinander, `families.JOINS` sagt, welche
   Anschlüsse zusammengehören.)*
2. [x] **Einrasten im Blender-Add-on:** Panel „Einrasten“ setzt ein Teil an den nächsten passenden freien Anschluss
   (Steg, Rampe, Tür in Wandöffnung, Rohr, Wandende, Wandabschluss, Sockelleiste, Decke); „Anschlüsse zeigen“ setzt
   Pfeile. Kern: `cubegen/snapping.py`.
3. [x] **Paletten-Modus:** `--textures palette`, ein Material `MP_Palette` mit Farbpaletten-Textur pro Modell, also
   ein Draw Call (Glas und von Scripts umgefärbte Teile behalten ihr Material); `check --palette`.
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

Details zu den Mechaniken in [`UNITY_INTEGRATION.md`](UNITY_INTEGRATION.md).

**Sofort**

1. **Audit-Test aktualisieren:** Er erwartet noch 3 Ablehnungen
   (`CUBEGEN_EXPECT_REJECTED=balance_scale,robot_arm,turret`); diese Pivot-Fehler sind seit 0.8.0 behoben. Mit dem
   aktuellen Stand ohne die Ausnahme neu laufen lassen, erwartet: 0 Ablehnungen.
2. **Neu exportieren und importieren**, sobald die Korrekturen in `main` sind: Luftschleusen (Sidecar) und die
   Typen, deren Geometrie sich für die flackernden Flächen und Draw Calls um 2 mm bzw. im Material geändert hat
   (Liste im CHANGELOG). Gleiche Namen, die Prefabs behalten ihre GUIDs. Wer die bisherigen Dateien behalten will,
   exportiert mit `--generation 1` (bitgleich zu 0.9.0).
3. **8 offene Item-IDs:** `ItemData` für Akku, Datenchip, Sicherung, Keycards, Werkzeuge und Hinweise festlegen,
   dann im Rezept per `item_id` setzen (cubegen erfindet keine IDs).

**Mit vorhandenen Scripts oder kleinen Ergänzungen**

4. **Zwei-Stellungs-Klappen** für `hatch`, `fuse_box`, `cage`, `safe`: `Rotatable` dreht zyklisch weiter, der
   zweite Klick dreht den Deckel durch den Körper.
5. **Lift über `MovingPlatform`** statt `Door`.
6. **Mitfahren** auf `retractable_bridge` (Verschiebung) und `turntable` (Drehung).
7. **Sockel über `ItemSlot`** (`socket`, `chip_reader`, `battery_bank`, `fuse_box`, `Slot` als Einsetzpunkt);
   Mehrfachsockel ergänzen.
8. **`pressure_plate` an `PressurePlate`** anbinden.

**Neue Mechaniken**

9. **Schadenszonen:** `spike_trap`, `crusher`, `saw_blade`, `steam_vent`, `shock_plate`.
10. **Nur vorbereitet:** `portal_frame`, `phase_platform`, `breakable_platform`, `fluid_basin`.
11. **Laser im Raum** mit Spiegeln und Teiler; Controller für das Rohr-Puzzle.
12. **Weitere Interaktionen:** Knopffolgen, Steckfeld, Scanner, Tresor, Werkzeuge als Schlüssel, Schieberätsel,
    Waage, Frequenz-Regler, Taschenlampe, Leiter, Pads, Förderband, Geschütz, Leerlauf-Animation für Drohne und
    Roboterarm.

**Freigabe und Struktur**

13. **Werkbank-Freigabe** neuer Gameplay-Prefabs im `AssetMetadata`-Vertrag.
14. **LOD-Hüllen prüfen:** Collider nur von LOD0.
15. **Statische Library-Prefabs als Static markieren** (Static Batching): Der Draw-Call-Bericht zählt bei
    statischen Modellen ein Material einmal und geht davon aus.
16. **Import der Anschlusspunkte bzw. des Layout-JSON**, falls der Raum-Generator kommt. Die Anschlussarten und wie
    sie zusammengehören stehen in `cubegen/families.py` (`connectors`, `JOINS`); das Einrasten im Add-on nutzt sie.
17. **Gemeinsamer Vertrag:** Der `CubegenImporter` liest `cubegen_contract.json`
    (`python -m cubegen contract --out <Unity>/Assets/Editor/Cubegen/cubegen_contract.json`) statt eigener
    Listen für Schlüssel, Rollen, Feldtypen und Toleranzen.

**Für die Erweiterungen aus Phase 3** (Details in [`UNITY_INTEGRATION.md`](UNITY_INTEGRATION.md))

18. **Paletten-Material:** einmal `MP_Palette` aus `CubeEscape_Palette.json` anlegen (Albedo, MetallicSmoothness,
    Emission; Filter Point, keine Mipmaps), damit der Import das FBX-Material per Name ersetzt.
19. **Bruchstücke** (`style.damage` = `fractured`): solche Prefabs nicht als Static markieren; bei Zerstörung jedem
    `Fragment_<nn>` einen Rigidbody geben (Collider: konvexe Mesh-Collider aus dem Sidecar).
20. **Anker** `Audio_*` / `FX_*`: `AudioSource` bzw. Partikelsystem nach Namen anhängen (Tabelle in
    `cubegen/models/anchors.py`); beim nächsten Export kommen sie mit Generation 3 automatisch mit.
21. **Schwenken:** prüfen, dass `Rotator.arc` vom Bau-Zustand aus in Richtung `speed` schwenkt (cubegen baut
    `camera.sweep` / `turret.sweep` um −arc/2 vorgedreht); sonst Vorzeichen in `models/common.sweep_rotator` drehen.
22. **Neue Mechaniken:** Schieben (`push_block` auf `pressure_plate`), Folge-Logik (`sequence_panel`,
    `meta.sequence`), Wasserstand (`Fluid_<n>` je Ventilschritt anheben), Laserfarbe durch `laser_filter`,
    Symbolplatten-Prüfung, Kranmagnet, Countdown-Zeit (`meta.seconds_total`), Patrouillenwege und Gangarten für
    `patrol_drone`, `vent_crawler`, `robot_dog`, `mech`.
