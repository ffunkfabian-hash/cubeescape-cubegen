# Roadmap

Stand: 6. Oktober 2026, cubegen 0.9.0 plus die Korrekturen unter „Unveröffentlicht“ im [CHANGELOG](../CHANGELOG.md).
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

**Funktionen**

1. **Raum- und Level-Generator:** setzt aus den Anschlusspunkten der Familien (`connectors` im Manifest) einen
   ganzen Raum nach Seed zusammen; Ausgabe als Layout-JSON für Unity.
2. **Einrasten im Blender-Add-on:** Kit-Teile rasten an ihren Anschlusspunkten ein.
3. **Paletten-Modus:** ein Material mit Farbpaletten-Textur pro Modell, also ein Draw Call.
4. **Symmetrisches Schwenken** für `camera` und `turret`: Rotor um den halben Winkel vorgedreht gebaut, dann
   schwenkt das vorhandene `Rotator.arc` um ±60°.
5. **Weitere Familien:** `medbay`, `derelict`, `greenhouse`, `reactor`, jeweils mit Requisiten im Kit.
6. **Zustand `fractured`:** Modell in Bruchstücke zerlegt, die Unity bei Zerstörung herausfallen lässt.
7. **Text auf Modellen:** Raumnummern und Beschriftungen (`sign.text=B-12`).
8. **Anker für Ton und Effekte:** leere Teile wie `Audio_Hum`, `FX_Steam`.

**Neue Modelltypen**

| Bereich | Vorschläge |
|---|---|
| Bau-Kit | Rampe, Decken- und Dachmodul, Durchgang / Torbogen, Wandabschluss, Sockelleiste |
| Rätsel | Gewichtsblock zum Schieben (passt zur Druckplatte), Ton- und Farbfolge-Panel, Wasserstand-Rätsel, Farbfilter für Laser, Symbolplatten, Kran / Magnet, Countdown-Anzeige |
| Requisiten | Labor (Mikroskop, Reagenzglas-Ständer, Zentrifuge), Küche / Messe, Waschraum, Lageplan |
| Licht | Flutlicht, Neon- und LED-Leisten, Notbeleuchtung |
| Roboter | Patrouillen-Drohne, Kriecher für Lüftungsschächte, Roboterhund, Industrie-Mech |
| Natur / Alien | Ranken, Kokons, Wurzeln durch Wände, Pilzteppiche, Pfützen |
| Außen / Weltraum | Rettungskapsel, Solarpanel, Asteroid, Fenster mit Planet |
| Ruinen | abgestürzte Kapsel, ausgebrannte Konsole, eingestürzter Steg |

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
16. **Import der Anschlusspunkte bzw. des Layout-JSON**, falls der Raum-Generator kommt.
17. **Gemeinsamer Vertrag:** Der `CubegenImporter` liest `cubegen_contract.json`
    (`python -m cubegen contract --out <Unity>/Assets/Editor/Cubegen/cubegen_contract.json`) statt eigener
    Listen für Schlüssel, Rollen, Feldtypen und Toleranzen.
